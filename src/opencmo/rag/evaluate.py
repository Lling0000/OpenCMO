"""Run reproducible RAG ablations. Synthetic mode is NOT semantic quality evidence.

python -m opencmo.rag.evaluate --validate
python -m opencmo.rag.evaluate --live --db output/eval-new.db --output output/evaluation.json
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import statistics
import uuid
from pathlib import Path

from opencmo.rag.types import RetrievalRequest


def validate_dataset(data: dict):
    docs = {d["id"] for d in data["documents"]}
    assert len(docs) == len(data["documents"]), "duplicate document ids"
    assert len(data["questions"]) >= 100, "at least 100 questions required"
    assert {q["split"] for q in data["questions"]} == {"development", "holdout"}
    assert {"en", "zh"} <= {q["language"] for q in data["questions"]}
    assert all(set(q["relevant"]) <= docs for q in data["questions"])
    assert len({q["id"] for q in data["questions"]}) == len(data["questions"])


def ranking_metrics(actual: list[str], relevant: list[str]) -> dict:
    if not relevant:
        return {"unanswerable_has_candidates": bool(actual)}
    relevant_set = set(relevant)
    recall = len(set(actual[:20]) & relevant_set) / len(relevant_set)
    dcg = sum((1 / math.log2(i + 2)) for i, doc in enumerate(actual[:10]) if doc in relevant_set)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(10, len(relevant_set))))
    return {"recall_at_20": recall, "ndcg_at_10": dcg / ideal if ideal else 0}


async def synthetic_embed(texts, settings, **_kwargs):
    """Token hash vectors exclusively for wiring tests, never for model quality claims."""
    from opencmo.rag.text import lexical_terms
    result = []
    for text in texts:
        vector = [0.001] * 64
        for term in lexical_terms(text):
            vector[int(hashlib.sha256(term.encode()).hexdigest(), 16) % 64] += 1
        result.append(vector)
    return result


async def synthetic_rerank(query, documents, _settings, **_kwargs):
    from opencmo.rag.text import lexical_terms
    terms = set(lexical_terms(query))
    return sorted([(i, min(.99, len(terms & set(lexical_terms(text))) / max(1, len(terms))))
                   for i, text in enumerate(documents)], key=lambda r: -r[1])


async def run(args, data):
    from opencmo import storage
    from opencmo.rag import ingestion, providers, retrieval, store
    from opencmo.rag.config import RagSettings
    path = Path(args.db).resolve()
    if path.exists():
        raise ValueError("Use a NEW evaluation database; never point this command at production data.")
    if args.live and not (os.environ.get("RAG_EMBEDDING_API_KEY") and os.environ.get("RAG_RERANK_API_KEY")):
        raise ValueError("Live evaluation requires RAG_EMBEDDING_API_KEY and RAG_RERANK_API_KEY.")
    path.parent.mkdir(parents=True, exist_ok=True)
    storage._DB_PATH = path
    os.environ["OPENCMO_RAG_STORAGE_PATH"] = str(path.parent / (path.stem + "-sources"))
    os.environ["OPENCMO_QDRANT_PREFIX"] = "eval_" + uuid.uuid4().hex[:12]
    settings = RagSettings(enabled=True,
        embedding_api_key=os.environ.get("RAG_EMBEDDING_API_KEY", "synthetic"),
        rerank_api_key=os.environ.get("RAG_RERANK_API_KEY", "synthetic"),
        embedding_base_url=os.environ.get("RAG_EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"),
        embedding_model=os.environ.get("RAG_EMBEDDING_MODEL", "BAAI/bge-m3"),
        rerank_base_url=os.environ.get("RAG_RERANK_BASE_URL", "https://api.siliconflow.cn/v1"),
        rerank_model=os.environ.get("RAG_RERANK_MODEL", "BAAI/bge-reranker-v2-m3"))
    if args.synthetic:
        providers.embed = synthetic_embed
        providers.rerank = synthetic_rerank
        async def original_query(request):
            return [request.query]
        retrieval.plan_queries = original_query
    _, account = await storage.create_user_with_account("evaluation@example.test", uuid.uuid4().hex)
    account_id = account["id"]
    await storage.set_account_setting(account_id, "RAG_CONFIG", settings.model_dump_json())
    project = await storage.ensure_project("RAG evaluation", "https://evaluation.example.test", "evaluation", account_id=account_id)
    mappings = {}
    for i, doc in enumerate(data["documents"]):
        item = await ingestion.create_document(account_id, project_id=project, title=doc["title"],
            data=doc["text"].encode(), filename="case.md", mime="text/markdown", source_key="eval:" + doc["id"],
            created_at=doc["date"] + " 00:00:00", external_use=True)
        await ingestion.ingest(account_id, item["document_id"], item["version_id"])
        mappings[item["document_id"]] = doc["id"]
        if (i + 1) % 10 == 0:
            print(json.dumps({"indexed_documents": i + 1}), flush=True)
    variants = {
        "bm25": (("bm25",), False), "dense": (("dense",), False),
        "fusion": (("dense", "bm25", "entity"), False),
        "fusion_rerank": (("dense", "bm25", "entity"), True),
    }
    outcomes = []
    for variant, (lanes, use_reranker) in variants.items():
        for question in data["questions"]:
            request = RetrievalRequest(account_id, project, question["query"], lanes=lanes, use_reranker=use_reranker)
            result = await retrieval.retrieve(request)
            ranked = list(dict.fromkeys(mappings[r["document_id"]] for r in result.ranking))
            correct_quotes = 0
            for citation in result.citations:
                original = await store.citation(account_id, citation.id)
                correct_quotes += bool(original and original["source_text"][citation.start:citation.end] == citation.quote)
            outcomes.append({"variant": variant, "question": question["id"], "split": question["split"],
                "category": question["category"], **ranking_metrics(ranked, question["relevant"]),
                "citations": len(result.citations), "valid_citations": correct_quotes,
                "timings": result.timings, "warnings": result.warnings})
        print(json.dumps({"completed_variant": variant}), flush=True)
    summaries = []
    for variant in variants:
        for split in ("development", "holdout"):
            rows = [r for r in outcomes if r["variant"] == variant and r["split"] == split]
            scored = [r for r in rows if "recall_at_20" in r]
            citation_count = sum(r["citations"] for r in rows)
            summary = {"variant": variant, "split": split,
                "recall_at_20": statistics.mean(r["recall_at_20"] for r in scored),
                "ndcg_at_10": statistics.mean(r["ndcg_at_10"] for r in scored),
                "quote_accuracy": sum(r["valid_citations"] for r in rows) / citation_count if citation_count else None,
                "queries_with_degradation": sum(bool(r["warnings"]) for r in rows)}
            summaries.append(summary)
    holdout = next(s for s in summaries if s['variant'] == 'fusion_rerank' and s['split'] == 'holdout')
    provider_failures = any(any(w.startswith(('dense_unavailable', 'rerank_unavailable')) for w in r['warnings']) for r in outcomes)
    output = {"mode": "live" if args.live else "synthetic_wiring_only",
        "semantic_quality_verified": bool(args.live and not provider_failures),
        'quality_gate_passed': bool(args.live and holdout['recall_at_20'] >= .9 and holdout['ndcg_at_10'] >= .8
                                   and holdout['quote_accuracy'] == 1 and not holdout['queries_with_degradation']),
        "note": "Synthetic scores must not be used to claim Recall/nDCG acceptance for actual models. Unanswerable queries require answer-level review.",
        "settings": settings.public(), "documents": len(mappings), "questions": len(data["questions"]),
        "summary": summaries, "results": outcomes}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mode": output["mode"], "output": args.output, "summary": summaries}, ensure_ascii=False))
    await providers.close_clients()
    if args.live and not output['quality_gate_passed']:
        raise ValueError('Live quality gate did not pass; inspect the saved evaluation report.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(Path(__file__).resolve().parents[3] / "tests/fixtures/rag_evaluation.json"))
    parser.add_argument("--validate", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--synthetic", action="store_true")
    parser.add_argument("--db")
    parser.add_argument("--output", default="output/rag-evaluation.json")
    args = parser.parse_args()
    data = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    validate_dataset(data)
    if args.validate or not (args.live or args.synthetic):
        print(json.dumps({"documents": len(data["documents"]), "questions": len(data["questions"]), "valid": True}))
        return
    if not args.db:
        parser.error("--db must name a new isolated database")
    try:
        asyncio.run(run(args, data))
    except ValueError as exc:
        parser.exit(2, str(exc) + "\n")

if __name__ == "__main__":
    main()
