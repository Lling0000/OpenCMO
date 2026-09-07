"""Generation integration; evidence is transient input and persisted output provenance."""
from __future__ import annotations

import contextvars
import functools
import inspect
import json
import re
from dataclasses import asdict, dataclass, field

from opencmo import storage
from opencmo.rag import store
from opencmo.rag.config import get_settings
from opencmo.rag.retrieval import evidence_prompt, retrieve, validate_output
from opencmo.rag.types import RetrievalRequest, RetrievalResult


@dataclass
class GenerationContext:
    account_id: int
    project_id: int
    purpose: str
    results: list[RetrievalResult] = field(default_factory=list)
    next_label: int = 1


_current: contextvars.ContextVar[GenerationContext | None] = contextvars.ContextVar("rag_generation", default=None)


def content_request(message: str) -> bool:
    return bool(re.search(r"(?i)\b(write|draft|rewrite|post|tweet|copywriting|publish|launch copy|article)\b|文案|写|发帖|推文|发布|笔记|公众号", message))


def with_knowledge(purpose: str):
    def decorate(function):
        signature = inspect.signature(function)
        @functools.wraps(function)
        async def wrapped(*args, **kwargs):
            values = signature.bind_partial(*args, **kwargs).arguments
            project_id = values.get("project_id")
            project = await storage.get_project(project_id) if project_id else None
            context = None
            if project and project.get("account_id") and (await get_settings(project["account_id"])).enabled:
                context = GenerationContext(project["account_id"], project_id, purpose)
            token = _current.set(context)
            try:
                return await function(*args, **kwargs)
            finally:
                _current.reset(token)
        return wrapped
    return decorate


async def section_evidence(query: str) -> str:
    context = _current.get()
    if context is None:
        return ""
    try:
        result = await retrieve(RetrievalRequest(context.account_id, context.project_id, query, purpose=context.purpose))
        mapping = {}
        for citation in result.citations:
            mapping[citation.label] = f"K{context.next_label}"
            citation.label = mapping[citation.label]
            context.next_label += 1
        result.context = re.sub(r"\[(K\d+)\]", lambda m: "[" + mapping.get(m[1], m[1]) + "]", result.context)
        context.results.append(result)
        async with store.database() as db:
            for citation in result.citations:
                await db.execute("UPDATE rag_citations SET data_json=? WHERE id=?",
                                 (json.dumps(asdict(citation), ensure_ascii=False), citation.id))
            await db.commit()
        return evidence_prompt(result)
    except Exception:
        return "Knowledge retrieval is unavailable. Do not claim to have consulted historical documents."


async def finalize_generation(text: str) -> tuple[str, dict]:
    context = _current.get()
    if context is None or not context.results:
        return text, {}
    combined = RetrievalResult("combined", citations=[c for r in context.results for c in r.citations])
    text, citations = await validate_output(text, combined, context.account_id)
    return text, {"citations": citations, "retrieval_ids": [r.retrieval_id for r in context.results],
                  "rag_warnings": list(dict.fromkeys(w for r in context.results for w in r.warnings))}


def safe_handoff_filter(message: str, context: str):
    # All run items may contain derived private facts, not only the source block.
    def filter_input(data):
        from dataclasses import replace
        history = (
            {"role": "system", "content": context},
            {"role": "user", "content": message},
        )
        return replace(data, input_history=history, pre_handoff_items=(), new_items=())
    return filter_input


def no_evidence_message(locale: str) -> str:
    return {
        "zh": "当前知识库中未找到足够的相关原文，无法依据资料回答。请补充资料或调整问题。",
        "ja": "ナレッジベースに十分な根拠が見つかりませんでした。資料を追加するか質問を変更してください。",
        "ko": "지식 베이스에서 충분한 근거를 찾지 못했습니다. 자료를 추가하거나 질문을 수정해 주세요.",
        "es": "No encontré evidencia suficiente en la base de conocimiento. Añade documentos o ajusta la pregunta.",
    }.get(locale, "I could not find sufficient source evidence in the knowledge base. Add documents or refine the question.")


async def filter_chat_history(account_id: int, session_id: str, history: list[dict], purpose: str,
                              session_project: int | None, current_project: int | None) -> list[dict]:
    """Retain visible conversation, without reusing revoked or cross-project evidence."""
    if purpose == "content" or session_project != current_project:
        return []
    result = []
    for item in history:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            continue
        if item["role"] == "assistant" and isinstance(item.get("content"), str):
            evidence = await store.message_evidence(account_id, session_id, item["content"])
            if evidence and not evidence["all_sources_available"]:
                continue
        result.append(item)
    return result
