"""Knowledge library and retrieval APIs. Account ids always come from authentication."""
from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from opencmo import storage
from opencmo.rag import ingestion, providers, store
from opencmo.rag.config import RagSettings, get_settings
from opencmo.rag.fetching import fetch_public_url
from opencmo.rag.parsing import MAX_BYTES
from opencmo.rag.retrieval import retrieve
from opencmo.rag.types import RetrievalRequest
from opencmo.web.auth import get_request_account_id, normalize_external_https_url

router = APIRouter(prefix="/api/v1")


class ImportDocument(BaseModel):
    project_id: int | None = None
    document_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    text: str = ""
    url: str = ""
    scope: str = "project"
    external_use: bool = False
    tags: list[str] = Field(default_factory=list, max_length=30)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    purpose: str = "internal"
    source_types: list[str] = Field(default_factory=list, max_length=8)
    date_from: date | None = None
    date_to: date | None = None


async def require_doc(request: Request, document_id: str):
    account = await get_request_account_id(request)
    doc = await store.document(account, document_id)
    if not doc:
        raise HTTPException(404, "document_not_found")
    return account, doc


@router.get("/knowledge/documents")
async def documents(request: Request, project_id: int | None = None, offset: int = 0, limit: int = 50):
    account = await get_request_account_id(request)
    if project_id is not None and not await storage.get_project(project_id, account_id=account):
        raise HTTPException(404, "project_not_found")
    return await store.rows("""SELECT d.*, (SELECT count(*) FROM rag_versions v WHERE v.document_id=d.id) version_count
        FROM rag_documents d WHERE account_id=? AND deleted=0 AND (scope='account' OR project_id=?)
        ORDER BY updated_at DESC,id LIMIT ? OFFSET ?""", (account, project_id, min(max(limit, 1), 100), max(offset, 0)))


@router.post("/knowledge/documents")
async def import_document(request: Request):
    account = await get_request_account_id(request)
    try:
        if "multipart/form-data" in request.headers.get("content-type", ""):
            async with request.form(max_files=1, max_fields=12) as form:
                upload = form.get("file")
                if upload is None or not hasattr(upload, "read"):
                    raise ValueError("file_required")
                data = await upload.read(MAX_BYTES + 1)
                result = await ingestion.create_document(account,
                    project_id=int(form["project_id"]) if form.get("project_id") else None,
                    title=str(form.get("title") or upload.filename or "Document"),
                    data=data, mime=upload.content_type or "text/plain", filename=upload.filename or "document.txt",
                    kind="file", scope=str(form.get("scope", "project")),
                    external_use=str(form.get("external_use", "false")).lower() == "true",
                    document_id=str(form["document_id"]) if form.get("document_id") else None)
        else:
            body = ImportDocument.model_validate(await request.json())
            data, mime, filename = body.text.encode(), "text/plain", "document.txt"
            source_key = None
            if body.url:
                data, mime, final_url = await asyncio.wait_for(fetch_public_url(body.url), 30)
                filename = {'application/pdf': 'page.pdf', 'text/plain': 'page.txt', 'text/markdown': 'page.md'}.get(mime, 'page.html')
                source_key = f"url:{body.project_id}:{body.scope}:{body.url}"
            result = await ingestion.create_document(account, project_id=body.project_id, title=body.title,
                data=data, mime=mime, filename=filename, kind="url" if body.url else "text",
                scope=body.scope, external_use=body.external_use, tags=body.tags, source_key=source_key,
                source_url=final_url if body.url else "", document_id=body.document_id)
    except (ValueError, asyncio.TimeoutError) as exc:
        return JSONResponse({"error": str(exc) or "import_timeout"}, status_code=400)
    return JSONResponse(result, status_code=202)


@router.get("/knowledge/documents/{document_id}")
async def document_detail(document_id: str, request: Request):
    account, doc = await require_doc(request, document_id)
    doc["versions"] = await store.rows("""SELECT id,number,mime,parser_version,created_at,length(text) text_length
                                        FROM rag_versions WHERE document_id=? ORDER BY number DESC""", (document_id,))
    doc["task"] = await store.one("""SELECT t.task_id,t.status FROM background_tasks t JOIN rag_task_owners o ON o.task_id=t.task_id
        WHERE o.account_id=? AND json_extract(t.payload_json,'$.document_id')=? ORDER BY t.id DESC LIMIT 1""", (account, document_id))
    return doc


@router.get("/knowledge/documents/{document_id}/versions/{version_id}")
async def version_detail(document_id: str, version_id: str, request: Request):
    await require_doc(request, document_id)
    version = await store.one("""SELECT id,number,mime,text,blocks_json,created_at FROM rag_versions
                                WHERE id=? AND document_id=?""", (version_id, document_id))
    if not version:
        raise HTTPException(404, "version_not_found")
    version["chunks"] = await store.rows("""SELECT c.id,c.level,c.parent_id,c.start_offset,c.end_offset,c.heading,c.page
        FROM rag_chunks c JOIN rag_generations g ON g.id=c.generation_id
        WHERE g.version_id=? ORDER BY c.start_offset,c.level""", (version_id,))
    return version


@router.get("/knowledge/documents/{document_id}/versions/{version_id}/original")
async def download_original(document_id: str, version_id: str, request: Request):
    await require_doc(request, document_id)
    version = await store.one("SELECT * FROM rag_versions WHERE id=? AND document_id=?", (version_id, document_id))
    if not version:
        raise HTTPException(404, "version_not_found")
    path = ingestion.safe_file(version["original_path"])
    if not path.exists():
        raise HTTPException(404, "original_not_available")
    return FileResponse(path, filename=Path(path).name, media_type="application/octet-stream")


@router.patch("/knowledge/documents/{document_id}")
async def update_document(document_id: str, request: Request):
    account, doc = await require_doc(request, document_id)
    body = await request.json()
    scope = body.get("scope", doc["scope"])
    if 'external_use' in body and not isinstance(body['external_use'], bool):
        raise HTTPException(400, 'invalid_document_metadata')
    if scope not in {"project", "account"} or (scope == "project" and doc["project_id"] is None):
        raise HTTPException(400, "invalid_document_scope")
    title = str(body.get("title", doc["title"])).strip()[:300]
    tags = body.get("tags", json.loads(doc["tags_json"]))
    if not title or not isinstance(tags, list) or len(tags) > 30 or not all(isinstance(t, str) for t in tags):
        raise HTTPException(400, "invalid_document_metadata")
    await store.execute("""UPDATE rag_documents SET title=?,scope=?,external_use=?,tags_json=?,updated_at=datetime('now')
        WHERE id=? AND account_id=?""", (title, scope, int(body.get("external_use", bool(doc["external_use"]))),
                                       json.dumps(tags, ensure_ascii=False), document_id, account))
    task = await ingestion.enqueue(account, "refresh", project_id=doc["project_id"], document_id=document_id)
    return {"ok": True, "task_id": task["task_id"]}


@router.delete("/knowledge/documents/{document_id}")
async def delete_document(document_id: str, request: Request):
    account, doc = await require_doc(request, document_id)
    await store.execute("UPDATE rag_documents SET deleted=1,status='deleted' WHERE id=? AND account_id=?", (document_id, account))
    task = await ingestion.enqueue(account, "cleanup", project_id=doc["project_id"], document_id=document_id)
    return {"ok": True, "task_id": task["task_id"]}


@router.post("/knowledge/documents/{document_id}/reindex")
async def reindex_document(document_id: str, request: Request):
    account, doc = await require_doc(request, document_id)
    version = await store.one('SELECT * FROM rag_versions WHERE document_id=? ORDER BY number DESC LIMIT 1', (document_id,))
    path = ingestion.safe_file(version['original_path'])
    if not path.exists():
        raise HTTPException(404, 'original_not_available')
    return await ingestion.create_document(account, project_id=doc['project_id'], document_id=document_id,
        title=doc['title'], data=path.read_bytes(), mime=version['mime'], filename=path.name,
        scope=doc['scope'], kind=doc['kind'], external_use=bool(doc['external_use']),
        generated=bool(doc['generated']), force_version=True, created_at=version['created_at'])


@router.post("/projects/{project_id}/knowledge/backfill-reports")
async def backfill_reports(project_id: int, request: Request):
    account = await get_request_account_id(request)
    if not await storage.get_project(project_id, account_id=account):
        raise HTTPException(404, "project_not_found")
    task = await ingestion.enqueue(account, "backfill", project_id=project_id)
    return {"task_id": task["task_id"]}


@router.post("/projects/{project_id}/knowledge/search")
async def search(project_id: int, body: SearchRequest, request: Request):
    account = await get_request_account_id(request)
    try:
        result = await retrieve(RetrievalRequest(account, project_id, body.query, purpose=body.purpose,
            source_types=body.source_types, date_from=body.date_from.isoformat() if body.date_from else None,
            date_to=body.date_to.isoformat() if body.date_to else None))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return result.to_dict()


@router.get("/knowledge/citations/{citation_id}")
async def citation_detail(citation_id: str, request: Request):
    value = await store.citation(await get_request_account_id(request), citation_id)
    if not value:
        raise HTTPException(404, "source_no_longer_available")
    return value


@router.get("/knowledge/settings")
async def settings_get(request: Request):
    account = await get_request_account_id(request)
    value = (await get_settings(account)).public()
    value["index"] = await store.one("""SELECT active_profile_id,pending_profile_id FROM rag_account_state
                                      WHERE account_id=?""", (account,))
    value['rebuild'] = await store.one("""SELECT t.task_id,t.status,t.error_json FROM background_tasks t
        JOIN rag_task_owners o ON o.task_id=t.task_id WHERE o.account_id=? AND json_extract(t.payload_json,'$.operation')='rebuild'
        ORDER BY t.id DESC LIMIT 1""", (account,))
    return value


async def candidate_settings(account: int, body: dict) -> RagSettings:
    old = await get_settings(account)
    allowed = set(RagSettings.model_fields)
    values = old.model_dump()
    values.update({k: v for k, v in body.items() if k in allowed})
    settings = RagSettings.model_validate(values)
    for name in ("embedding_base_url", "rerank_base_url"):
        from urllib.parse import urlsplit
        parsed = urlsplit(getattr(settings, name))
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('invalid_provider_base_url')
        setattr(settings, name, normalize_external_https_url(getattr(settings, name), field_name=name))
    return settings


@router.post("/knowledge/settings")
async def settings_save(request: Request):
    account = await get_request_account_id(request)
    body = await request.json()
    try:
        old = await get_settings(account)
        settings = await candidate_settings(account, body)
    except ValueError:
        raise HTTPException(400, "invalid_rag_settings") from None
    await storage.set_account_setting(account, "RAG_CONFIG", settings.model_dump_json())
    if settings.enabled and not old.enabled:
        from datetime import datetime, timezone
        await storage.set_account_setting(account, 'RAG_ENABLED_AT', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
    reindex_keys = ("embedding_base_url", "embedding_model", "embedding_api_key", "parent_tokens", "child_tokens", "overlap_tokens")
    task = None
    if settings.enabled and settings.embedding_api_key and (not await store.active_profile(account) or
            any(getattr(old, k) != getattr(settings, k) for k in reindex_keys)):
        import hashlib
        revision = hashlib.sha256(settings.model_dump_json().encode()).hexdigest()[:24]
        task = await ingestion.enqueue(account, "rebuild", version_id=revision)
    return {**settings.public(), "task_id": task["task_id"] if task else None}


@router.post("/knowledge/settings/test")
async def settings_test(request: Request):
    account = await get_request_account_id(request)
    try:
        settings = await candidate_settings(account, await request.json())
        vector = await providers.embed(["OpenCMO 测试 knowledge"], settings, account_id=account)
        ranks = await providers.rerank("营销案例", ["营销增长案例", "天气预报"], settings, account_id=account)
        return {"ok": True, "dimensions": len(vector[0]), "rerank_results": len(ranks)}
    except Exception as exc:
        code = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        return JSONResponse({"ok": False, "error": code}, status_code=400)


@router.post('/knowledge/rebuild')
async def rebuild_library(request: Request):
    account = await get_request_account_id(request)
    settings = await get_settings(account)
    if not settings.enabled or not settings.embedding_api_key:
        raise HTTPException(400, 'rag_not_configured')
    task = await ingestion.enqueue(account, 'rebuild')
    return {'task_id': task['task_id']}
