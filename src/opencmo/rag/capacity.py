"""Capacity test using real Qdrant/SQLite and synthetic documents/vectors.

No model API calls. Measures engine throughput/latency, not semantic quality.
The database must not exist. Qdrant collection names are unique per run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
import statistics
import time
import uuid
from pathlib import Path

import numpy as np
from qdrant_client import AsyncQdrantClient, models


async def run(args):
    from opencmo import storage
    from opencmo.rag import providers, store
    from opencmo.rag.config import RagSettings
    from opencmo.rag.types import RetrievalRequest
    path = Path(args.db).resolve()
    if path.exists():
        raise ValueError("Capacity tests require a new, isolated database.")
    path.parent.mkdir(parents=True, exist_ok=True)
    estimate = int(args.documents * args.chunks_per_doc * (args.dimensions * 4 * 5 + 9000) * 1.5) + 256 * 1024 * 1024
    if shutil.disk_usage(path.parent).free < estimate:
        raise ValueError(f'Insufficient local disk space: reserve at least {estimate / 1024**3:.1f} GiB; also check the Qdrant storage disk.')
    storage._DB_PATH = path
    os.environ["OPENCMO_QDRANT_URL"] = args.qdrant_url
    _, account = await storage.create_user_with_account("capacity@example.test", uuid.uuid4().hex)
    account_id = account["id"]
    project = await storage.ensure_project("Capacity", "https://capacity.example.test", "benchmark", account_id=account_id)
    collection = "opencmo_capacity_" + uuid.uuid4().hex[:12]
    profile = {"id": str(uuid.uuid4()), "account_id": account_id, "dimensions": args.dimensions,
               "collection_name": collection}
    client = AsyncQdrantClient(url=args.qdrant_url, grpc_port=args.grpc_port, prefer_grpc=True, timeout=120,
                              api_key=os.environ.get('OPENCMO_QDRANT_API_KEY') or None)
    await providers.vectors.ensure(collection, args.dimensions)
    await store.execute("INSERT INTO rag_profiles(id,account_id,fingerprint,dimensions,collection_name,status) VALUES(?,?,?,?,?,'ready')",
                        (profile["id"], account_id, collection, args.dimensions, collection))
    await store.execute("INSERT INTO rag_account_state(account_id,active_profile_id) VALUES(?,?)", (account_id, profile["id"]))
    rng = np.random.default_rng(42)
    started = time.monotonic()
    vector_samples = {}
    query_indices = set(random.Random(42).sample(range(args.documents), min(args.queries, args.documents)))
    base = ("A marketing team investigated acquisition channels, onboarding friction, trial conversion, "
            "retention and customer feedback. The report links observed changes to dated source records "
            "and recommends experiments without asserting unsupported causation. ") * 6
    indexed = 0
    try:
        for number in range(args.documents):
            key = f"customer{number:06d}"
            doc_id, version_id, generation_id = (str(uuid.uuid4()) for _ in range(3))
            paragraphs = [f"{key} passage{part:03d}. {base}" for part in range(args.chunks_per_doc)]
            full = "\n\n".join(paragraphs)
            title = f"{key} marketing case study"
            points, chunks = [], []
            offset = 0
            parent_id = None
            base_vector = rng.normal(size=args.dimensions).astype(np.float32)
            for part, text in enumerate(paragraphs):
                if part % 4 == 0:
                    parent_id = str(uuid.uuid4())
                    parent_text = "\n\n".join(paragraphs[part:part + 4])
                    chunks.append((parent_id, generation_id, None, "parent", offset, offset + len(parent_text), parent_text, title, None, ""))
                child_id = str(uuid.uuid4())
                chunks.append((child_id, generation_id, parent_id, "child", offset, offset + len(text), text, title, None, ""))
                vector = (base_vector + rng.normal(0, .02, size=args.dimensions).astype(np.float32)).tolist()
                if part == 0 and number in query_indices:
                    vector_samples[key] = vector
                points.append(models.PointStruct(id=child_id, vector=vector, payload={
                    "account_id": str(account_id), "project_id": project, "scope": "project",
                    "external_use": False, "document_id": doc_id, "generation_id": generation_id}))
                offset += len(text) + 2
            async with store.database() as db:
                await db.execute("""INSERT INTO rag_documents(id,account_id,project_id,title,kind,source_key,active_version_id,status)
                    VALUES(?,?,?,?,?,?,?,'ready')""", (doc_id, account_id, project, title, "synthetic", key, version_id))
                await db.execute("""INSERT INTO rag_versions(id,document_id,number,content_hash,original_path,mime,text)
                    VALUES(?,?,1,?,'synthetic','text/plain',?)""", (version_id, doc_id, key, full))
                await db.execute("INSERT INTO rag_generations(id,document_id,version_id,profile_id,status,config_json) VALUES(?,?,?,?,'ready',?)",
                                 (generation_id, doc_id, version_id, profile["id"], RagSettings().model_dump_json()))
                await db.executemany("INSERT INTO rag_chunks VALUES(?,?,?,?,?,?,?,?,?,?)", chunks)
                await db.executemany("INSERT INTO rag_fts(chunk_id,title,body) VALUES(?,?,?)",
                                     [(c[0], title.lower(), c[6].lower()) for c in chunks if c[3] == "child"])
                await db.commit()
            await client.upsert(collection, points, wait=True)
            indexed += len(points)
            if (number + 1) % 250 == 0:
                print(json.dumps({"documents": number + 1, "children": indexed,
                                  "elapsed_seconds": round(time.monotonic() - started, 1)}), flush=True)
        ingestion_seconds = time.monotonic() - started
        # Wait a bounded time for optimizer/index construction. Report actual readiness.
        deadline = time.monotonic() + args.optimizer_wait
        info = await client.get_collection(collection)
        while str(info.status).lower() != "green" and time.monotonic() < deadline:
            await asyncio.sleep(5)
            info = await client.get_collection(collection)
        latencies = []
        semaphore = asyncio.Semaphore(args.concurrency)
        async def search(key, vector):
            async with semaphore:
                request = RetrievalRequest(account_id, project, key)
                start = time.monotonic()
                async def timed(name, call):
                    checkpoint = time.monotonic()
                    value = await call
                    return name, (time.monotonic() - checkpoint) * 1000, len(value)
                values = await asyncio.gather(
                    timed("dense", providers.vectors.search(profile, vector, request, 30)),
                    timed("bm25", store.lexical_search(key, request, 30)),
                    timed("entity", store.entity_search(key, request, 20)),
                )
                latencies.append({"total_ms": (time.monotonic() - start) * 1000,
                                  **{name + "_ms": duration for name, duration, _ in values},
                                  "hits": {name: count for name, _, count in values}})
        await asyncio.gather(*(search(key, vector) for key, vector in vector_samples.items()))
        values = sorted(row["total_ms"] for row in latencies)
        disk = sum(p.stat().st_size for p in path.parent.glob(path.name + "*") if p.is_file())
        result = {"mode": "synthetic_capacity_real_engines", "semantic_quality_verified": False,
            "documents": args.documents, "child_chunks": indexed, "dimensions": args.dimensions,
            "concurrency": args.concurrency, "queries": len(latencies), "qdrant_collection": collection,
            "qdrant_status": str(info.status), "indexed_vectors_count": info.indexed_vectors_count,
            "ingestion_seconds": ingestion_seconds, "chunks_per_second": indexed / ingestion_seconds,
            "sqlite_bytes": disk, "retrieval_p50_ms": statistics.median(values),
            "retrieval_p95_ms": values[min(len(values)-1, int(.95 * len(values)))],
            "model_api_ms": None, "note": "No embedding, rewriting or rerank API latency is represented.",
            "latencies": latencies}
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "latencies"}), flush=True)
    finally:
        await client.close()
        await providers.close_clients()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--qdrant-url", default="http://127.0.0.1:6337")
    parser.add_argument("--grpc-port", type=int, default=6338)
    parser.add_argument("--documents", type=int, default=10000)
    parser.add_argument("--chunks-per-doc", type=int, default=50)
    parser.add_argument("--dimensions", type=int, default=1024)
    parser.add_argument("--queries", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--optimizer-wait", type=int, default=300)
    parser.add_argument("--output", default="output/rag-capacity.json")
    args = parser.parse_args()
    if min(args.documents, args.chunks_per_doc, args.dimensions, args.queries, args.concurrency) < 1:
        parser.error("sizes must be positive")
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
