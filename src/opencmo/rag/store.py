"""SQLite is authoritative for access, active versions and citation provenance."""
from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from dataclasses import asdict

import aiosqlite

from opencmo.rag.text import fts_query
from opencmo.rag.types import RetrievalRequest, RetrievalResult
from opencmo.storage._db import get_db


@asynccontextmanager
async def database():
    db = await get_db()
    db.row_factory = aiosqlite.Row
    try:
        yield db
    except BaseException:
        await db.rollback()
        raise
    finally:
        await db.close()

async def rows(sql: str, params=()) -> list[dict]:
    async with database() as db:
        return [dict(r) for r in await (await db.execute(sql, params)).fetchall()]

async def one(sql: str, params=()) -> dict | None:
    found = await rows(sql, params)
    return found[0] if found else None

async def execute(sql: str, params=()) -> None:
    async with database() as db:
        await db.execute(sql, params)
        await db.commit()

def visibility(request: RetrievalRequest) -> tuple[str, list]:
    clause = "d.account_id=? AND d.deleted=0 AND (d.scope='account' OR d.project_id=?)"
    params = [request.account_id, request.project_id]
    if request.purpose == "content":
        clause += " AND d.external_use=1"
    if request.source_types:
        clause += " AND d.kind IN (" + ",".join("?" for _ in request.source_types) + ")"
        params.extend(request.source_types)
    if request.date_from:
        clause += " AND substr(v.created_at,1,10)>=?"
        params.append(request.date_from)
    if request.date_to:
        clause += " AND substr(v.created_at,1,10)<=?"
        params.append(request.date_to)
    return clause, params

JOIN = """
 FROM rag_chunks c JOIN rag_generations g ON g.id=c.generation_id
 JOIN rag_documents d ON d.id=g.document_id JOIN rag_versions v ON v.id=g.version_id
 JOIN rag_account_state s ON s.account_id=d.account_id
"""
ACTIVE = "g.status='ready' AND g.profile_id=s.active_profile_id AND g.version_id=d.active_version_id"
COLUMNS = """c.*, d.id AS document_id, d.title, d.generated, d.kind, d.tags_json, d.source_url,
 v.id AS version_id, v.created_at, g.profile_id, d.scope, d.external_use, d.account_id, d.project_id"""

async def hydrate(ids: list[str], request: RetrievalRequest) -> list[dict]:
    if not ids:
        return []
    acl, params = visibility(request)
    return await rows("SELECT " + COLUMNS + JOIN + " WHERE " + ACTIVE + " AND " + acl +
                      " AND c.id IN (" + ",".join("?" for _ in ids) + ")", params + ids)

async def lexical_search(query: str, request: RetrievalRequest, limit: int) -> list[dict]:
    match = fts_query(query)
    if not match:
        return []
    acl, params = visibility(request)
    return await rows("SELECT " + COLUMNS + ",bm25(rag_fts,0,3,1) AS score " + JOIN +
                      " JOIN rag_fts ON rag_fts.chunk_id=c.id WHERE " + ACTIVE + " AND " + acl +
                      " AND rag_fts MATCH ? ORDER BY score LIMIT ?", params + [match, limit])

async def entity_search(query: str, request: RetrievalRequest, limit: int) -> list[dict]:
    match = fts_query(query)
    if not match:
        return []
    acl, params = visibility(request)
    # The title column indexes document title, heading path and entity tags.
    # Restrict this lane to that column, using its inverted index instead of an
    # O(number-of-passages) instr scan for every request.
    return await rows('SELECT ' + COLUMNS + ',bm25(rag_fts,0,3,0) AS score ' + JOIN +
                      ' JOIN rag_fts ON rag_fts.chunk_id=c.id WHERE ' + ACTIVE + ' AND ' + acl +
                      ' AND rag_fts MATCH ? ORDER BY score LIMIT ?', params + ['title : (' + match + ')', limit])

async def document(account_id: int, document_id: str, *, include_deleted=False) -> dict | None:
    return await one("SELECT * FROM rag_documents WHERE account_id=? AND id=?" +
                     ("" if include_deleted else " AND deleted=0 AND NOT(scope='project' AND project_id IS NULL)"), (account_id, document_id))

async def active_profile(account_id: int) -> dict | None:
    return await one("""SELECT p.* FROM rag_profiles p JOIN rag_account_state s ON s.active_profile_id=p.id
                        WHERE s.account_id=?""", (account_id,))

async def profile_settings(profile: dict):
    from opencmo import storage
    from opencmo.rag.config import RagSettings
    raw = await storage.get_account_setting(profile["account_id"], f"RAG_PROFILE_{profile['id']}")
    if not raw:
        raise ValueError("profile_configuration_missing")
    return RagSettings.model_validate_json(raw)

async def save_retrieval(request: RetrievalRequest, result: RetrievalResult) -> None:
    # Traces contain timings/rankings but not the raw query or candidate documents.
    trace = result.to_dict()
    trace.pop("context", None)
    trace["hits"] = [{k: v for k, v in h.items() if k != "text"} for h in trace["hits"]]
    trace.pop("citations", None)
    async with database() as db:
        await db.execute("""INSERT INTO rag_retrievals(id,account_id,project_id,purpose,query_hash,result_json)
                            VALUES(?,?,?,?,?,?)""",
                         (result.retrieval_id, request.account_id, request.project_id, request.purpose,
                          hashlib.sha256(request.query.encode()).hexdigest(), json.dumps(trace, ensure_ascii=False)))
        for citation in result.citations:
            await db.execute("INSERT INTO rag_citations VALUES(?,?,?,?,?,?)",
                             (citation.id, result.retrieval_id, citation.document_id, citation.version_id,
                              citation.chunk_id, json.dumps(asdict(citation), ensure_ascii=False)))
        await db.commit()

async def citation(account_id: int, citation_id: str, *, include_source=True) -> dict | None:
    text_column = 'v.text' if include_source else "substr(v.text,json_extract(c.data_json,'$.start')+1,json_extract(c.data_json,'$.end')-json_extract(c.data_json,'$.start'))"
    row = await one('SELECT c.data_json,r.project_id,r.purpose,' + text_column + """ AS text FROM rag_citations c
        JOIN rag_retrievals r ON r.id=c.retrieval_id JOIN rag_documents d ON d.id=c.document_id
        JOIN rag_versions v ON v.id=c.version_id
        WHERE c.id=? AND r.account_id=? AND d.account_id=? AND d.deleted=0
        AND (d.scope='account' OR d.project_id=r.project_id)
        AND (r.purpose!='content' OR d.external_use=1)""", (citation_id, account_id, account_id))
    if not row:
        return None
    item = json.loads(row["data_json"])
    observed = row['text'][item['start']:item['end']] if include_source else row['text']
    if observed != item["quote"]:
        return None
    if include_source:
        item["source_text"] = row["text"]
    return item

async def put_message_evidence(session_id: str, content: str, retrieval_id: str):
    await execute("INSERT OR REPLACE INTO rag_message_evidence VALUES(?,?,?)",
                  (session_id, hashlib.sha256(content.encode()).hexdigest(), retrieval_id))

async def message_evidence(account_id: int, session_id: str, content: str) -> dict:
    row = await one("""SELECT r.* FROM rag_message_evidence e JOIN rag_retrievals r ON r.id=e.retrieval_id
        JOIN chat_sessions s ON s.id=e.session_id WHERE e.session_id=? AND e.message_key=?
        AND r.account_id=? AND s.account_id=?""",
        (session_id, hashlib.sha256(content.encode()).hexdigest(), account_id, account_id))
    if not row:
        return {}
    refs = await rows("SELECT id FROM rag_citations WHERE retrieval_id=?", (row["id"],))
    citations = []
    available = 0
    for ref in refs:
        value = await citation(account_id, ref["id"], include_source=False)
        if value:
            available += 1
            if value['url'] in content:
                citations.append(value)
    return {"citations": citations, "retrieval_id": row["id"], "rag_status": json.loads(row["result_json"])["status"],
            'all_sources_available': available == len(refs)}
