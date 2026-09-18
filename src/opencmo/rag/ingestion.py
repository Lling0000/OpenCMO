"""Durable ingestion, version activation, report backfill and index repair."""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from opencmo import storage
from opencmo.background import service as background
from opencmo.rag import providers, store
from opencmo.rag.config import RagSettings, chunk_limit, configured, document_limit, get_settings
from opencmo.rag.parsing import MAX_BYTES, parse_bytes
from opencmo.rag.splitting import split_document
from opencmo.rag.text import lexical_terms, tokens, truncate
from opencmo.rag.types import ParsedDocument, TextBlock


def file_root() -> Path:
    from opencmo.storage import _db
    return Path(os.environ.get("OPENCMO_RAG_STORAGE_PATH", _db._DB_PATH.parent / "knowledge")).resolve()


def safe_file(relative: str) -> Path:
    root = file_root()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("invalid_storage_path")
    return path


async def enqueue(account_id: int, operation: str, *, project_id=None, document_id=None, version_id=None):
    payload = {"operation": operation, "account_id": account_id, "_account_id": account_id,
               "document_id": document_id, "version_id": version_id}
    task = await background.enqueue_task(kind="knowledge", project_id=project_id, payload=payload,
        dedupe_key=f"knowledge:{account_id}:{operation}:{document_id or project_id}:{version_id}", max_attempts=3)
    await store.execute("INSERT OR IGNORE INTO rag_task_owners VALUES(?,?)", (task["task_id"], account_id))
    return task


async def create_document(account_id: int, *, project_id: int | None, title: str, data: bytes,
                          mime="text/plain", filename="document.txt", kind="text", scope="project",
                          external_use=False, tags=None, source_key=None, source_url="", document_id=None,
                          generated=False, created_at=None, force_version=False) -> dict:
    if scope not in {"project", "account"} or (scope == "project" and project_id is None):
        raise ValueError("invalid_document_scope")
    if project_id is not None and not await storage.get_project(project_id, account_id=account_id):
        raise ValueError("project_not_found")
    if not data or len(data) > MAX_BYTES:
        raise ValueError("empty_or_oversized_document")
    if kind == 'file' and Path(filename).suffix.lower() not in {'.pdf', '.docx', '.md', '.markdown', '.txt', '.html', '.htm'}:
        raise ValueError('unsupported_document_type')
    content_hash = hashlib.sha256(data).hexdigest()
    key = source_key or f"upload:{project_id}:{scope}:{content_hash}"
    async with store.database() as db:
        await db.execute("BEGIN IMMEDIATE")
        if document_id:
            row = await (await db.execute("SELECT * FROM rag_documents WHERE id=? AND account_id=? AND deleted=0",
                                          (document_id, account_id))).fetchone()
            if not row:
                raise ValueError("document_not_found")
        else:
            row = await (await db.execute("SELECT * FROM rag_documents WHERE account_id=? AND source_key=? AND deleted=0",
                                          (account_id, key))).fetchone()
        if row:
            document_id = row["id"]
            same = await (await db.execute("SELECT id FROM rag_versions WHERE document_id=? AND content_hash=? ORDER BY number DESC LIMIT 1",
                                           (document_id, content_hash))).fetchone()
            if same and not force_version:
                await db.commit()
                return {"document_id": document_id, "version_id": same["id"], "duplicate": True}
        else:
            count = (await (await db.execute("SELECT count(*) FROM rag_documents WHERE account_id=? AND deleted=0", (account_id,))).fetchone())[0]
            if count >= document_limit():
                raise ValueError("document_quota_exceeded")
            document_id = str(uuid.uuid4())
            # Tombstones retain unique keys until cleanup; use a new key after explicit deletion.
            existing = await (await db.execute("SELECT id FROM rag_documents WHERE account_id=? AND source_key=?", (account_id, key))).fetchone()
            if existing:
                await db.execute("UPDATE rag_documents SET source_key=source_key || ':deleted:' || id WHERE id=? AND deleted=1", (existing['id'],))
            await db.execute("""INSERT INTO rag_documents(id,account_id,project_id,scope,external_use,title,kind,
                              source_key,source_url,tags_json,generated) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (document_id, account_id, project_id, scope, int(external_use), title[:300], kind, key, source_url,
                 json.dumps(tags or [], ensure_ascii=False), int(generated)))
        number = (await (await db.execute("SELECT coalesce(max(number),0)+1 FROM rag_versions WHERE document_id=?", (document_id,))).fetchone())[0]
        version_id = str(uuid.uuid4())
        extension = Path(filename).suffix.lower()
        if extension not in {".pdf", ".docx", ".md", ".txt", ".markdown", ".html", ".htm"}:
            extension = ".txt"
        relative = f"{account_id}/{document_id}/{version_id}{extension}"
        path = safe_file(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        await db.execute("INSERT INTO rag_versions(id,document_id,number,content_hash,original_path,mime) VALUES(?,?,?,?,?,?)",
                         (version_id, document_id, number, content_hash, relative, mime))
        if created_at:
            await db.execute("UPDATE rag_versions SET created_at=? WHERE id=?", (created_at, version_id))
        await db.execute("UPDATE rag_documents SET status='queued',error='',updated_at=datetime('now') WHERE id=?", (document_id,))
        await db.commit()
    task = await enqueue(account_id, "ingest", project_id=project_id, document_id=document_id, version_id=version_id)
    return {"document_id": document_id, "version_id": version_id, "task_id": task["task_id"], "duplicate": False}


async def ensure_profile(account_id: int, settings: RagSettings) -> dict:
    probe = await providers.embed(["OpenCMO knowledge index"], settings, attempts=3, account_id=account_id)
    dimensions = len(probe[0])
    fingerprint = settings.fingerprint(dimensions)
    profile_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"opencmo:{account_id}:{fingerprint}"))
    collection = f"{os.environ.get('OPENCMO_QDRANT_PREFIX', 'opencmo')}_rag_{fingerprint}"
    await providers.vectors.ensure(collection, dimensions, force=True)
    await store.execute("""INSERT OR IGNORE INTO rag_profiles(id,account_id,fingerprint,dimensions,collection_name)
                           VALUES(?,?,?,?,?)""", (profile_id, account_id, fingerprint, dimensions, collection))
    # Profile snapshots stay in the account's credential store, never task payloads or API responses.
    await storage.set_account_setting(account_id, f"RAG_PROFILE_{profile_id}", settings.model_dump_json())
    await store.execute("INSERT OR IGNORE INTO rag_account_state(account_id) VALUES(?)", (account_id,))
    return await store.one("SELECT * FROM rag_profiles WHERE id=?", (profile_id,))


async def ingest(account_id: int, document_id: str, version_id: str, *, profile=None, activate=True, emit=None, force_vectors=False):
    doc = await store.document(account_id, document_id)
    if not doc:
        return
    version = await store.one("SELECT * FROM rag_versions WHERE id=? AND document_id=?", (version_id, document_id))
    if not version:
        raise ValueError("version_not_found")
    settings = await get_settings(account_id)
    if not configured(settings):
        raise ValueError("rag_not_configured")
    async def progress(phase, summary):
        if emit:
            await emit(event_type="progress", phase=phase, status="running", summary=summary)
    await store.execute("UPDATE rag_documents SET status='indexing',error='' WHERE id=?", (document_id,))
    await progress("parsing", "Parsing document")
    if version["text"]:
        parsed = ParsedDocument(version["text"], [TextBlock(**b) for b in json.loads(version["blocks_json"])])
    else:
        path = safe_file(version["original_path"])
        parsed = await asyncio.to_thread(parse_bytes, path.read_bytes(), version["mime"], path.name)
        await store.execute("UPDATE rag_versions SET text=?,blocks_json=? WHERE id=? AND text=''",
                            (parsed.text, json.dumps([asdict(b) for b in parsed.blocks]), version_id))
    profile = profile or await store.active_profile(account_id) or await ensure_profile(account_id, settings)
    await providers.vectors.ensure(profile['collection_name'], profile['dimensions'])
    index_settings = await store.profile_settings(profile)
    generation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{version_id}:{profile['id']}"))
    existing = await store.one("SELECT * FROM rag_generations WHERE id=?", (generation_id,))
    if not existing or existing["status"] != "ready" or force_vectors:
        await progress("splitting", "Building parent and child passages")
        chunks = await asyncio.to_thread(split_document, parsed, generation_id, index_settings)
        children = [c for c in chunks if c.level == "child"]
        if not children:
            raise ValueError("empty_document")
        indexed_texts = await asyncio.to_thread(lambda: [
            (c.id, ' '.join(lexical_terms(doc['title'] + ' ' + c.heading + ' ' + doc['tags_json'])),
             ' '.join(lexical_terms(c.prefix + '\n' + c.text))) for c in children])
        async with store.database() as db:
            await db.execute("BEGIN IMMEDIATE")
            used = (await (await db.execute("""SELECT count(*) FROM rag_chunks c JOIN rag_generations g ON g.id=c.generation_id
                 JOIN rag_documents d ON d.id=g.document_id JOIN rag_account_state s ON s.account_id=d.account_id
                 WHERE d.account_id=? AND d.deleted=0 AND c.level='child' AND g.profile_id=s.active_profile_id
                 AND g.version_id=d.active_version_id AND d.id!=?""", (account_id, document_id))).fetchone())[0]
            if used + len(children) > chunk_limit():
                raise ValueError("chunk_quota_exceeded")
            await db.execute("""INSERT OR IGNORE INTO rag_generations(id,document_id,version_id,profile_id,config_json)
                VALUES(?,?,?,?,?)""", (generation_id, document_id, version_id, profile["id"], json.dumps(index_settings.public())))
            await db.execute("DELETE FROM rag_fts WHERE chunk_id IN (SELECT id FROM rag_chunks WHERE generation_id=?)", (generation_id,))
            await db.execute("DELETE FROM rag_chunks WHERE generation_id=?", (generation_id,))
            await db.executemany("INSERT INTO rag_chunks VALUES(?,?,?,?,?,?,?,?,?,?)",
                [(c.id, generation_id, c.parent_id, c.level, c.start, c.end, c.text, c.heading, c.page, c.prefix) for c in chunks])
            await db.executemany('INSERT INTO rag_fts(chunk_id,title,body) VALUES(?,?,?)', indexed_texts)
            await db.commit()
        for offset in range(0, len(children), 16):
            if not await store.document(account_id, document_id):
                return
            batch = children[offset:offset + 16]
            texts = [truncate(doc["title"] + "\n" + c.heading, 96) + "\n" +
                     truncate(c.prefix, 128) + "\n" + c.text for c in batch]
            if any(tokens(t) > index_settings.embedding_max_tokens for t in texts):
                raise ValueError("embedding_input_limit")
            vectors = await providers.embed(texts, index_settings, attempts=3, account_id=account_id)
            if any(len(v) != profile["dimensions"] for v in vectors):
                raise ValueError("embedding_dimensions_changed")
            await providers.vectors.upsert(profile["collection_name"], [{
                "id": c.id, "vector": vector, "payload": {
                    "account_id": str(account_id), "project_id": doc["project_id"] or 0, "scope": doc["scope"],
                    "external_use": bool(doc["external_use"]), "document_id": doc["id"], "generation_id": generation_id,
                    'source_kind': doc['kind'], 'source_date': version['created_at'].replace(' ', 'T').rstrip('Z') + 'Z',
                }} for c, vector in zip(batch, vectors)])
            await progress("embedding", f"Indexed {min(offset + 16, len(children))}/{len(children)} passages")
        await store.execute("UPDATE rag_generations SET status='ready' WHERE id=?", (generation_id,))
    if activate:
        async with store.database() as db:
            # Out-of-order retries must never replace a newer document version.
            await db.execute("""UPDATE rag_documents SET active_version_id=?,status='ready',error='',updated_at=datetime('now')
                WHERE id=? AND deleted=0 AND (active_version_id IS NULL OR
                (SELECT number FROM rag_versions WHERE id=active_version_id)<=(SELECT number FROM rag_versions WHERE id=?))""",
                (version_id, document_id, version_id))
            await db.execute("UPDATE rag_account_state SET active_profile_id=coalesce(active_profile_id,?) WHERE account_id=?",
                             (profile["id"], account_id))
            await db.execute("UPDATE rag_profiles SET status='ready' WHERE id=?", (profile["id"],))
            await db.commit()
    return generation_id


async def rebuild(account_id: int, emit=None):
    settings = await get_settings(account_id)
    if not configured(settings):
        raise ValueError("rag_not_configured")
    profile = await ensure_profile(account_id, settings)
    await store.execute("UPDATE rag_account_state SET pending_profile_id=? WHERE account_id=?", (profile["id"], account_id))
    docs = await store.rows("""SELECT d.id,(SELECT v.id FROM rag_versions v WHERE v.document_id=d.id ORDER BY number DESC LIMIT 1) version_id
                              FROM rag_documents d WHERE d.account_id=? AND d.deleted=0""", (account_id,))
    for doc in docs:
        await ingest(account_id, doc["id"], doc["version_id"], profile=profile, activate=False, emit=emit, force_vectors=True)
    async with store.database() as db:
        for doc in docs:
            await db.execute("""UPDATE rag_documents SET active_version_id=?,status='ready',error=''
                WHERE id=? AND deleted=0""", (doc["version_id"], doc["id"]))
        await db.execute("UPDATE rag_account_state SET active_profile_id=?,pending_profile_id=NULL WHERE account_id=?",
                         (profile["id"], account_id))
        await db.execute("UPDATE rag_profiles SET status='ready' WHERE id=?", (profile["id"],))
        await db.commit()


async def import_report(report: dict):
    project = await storage.get_project(report["project_id"])
    if not project or report["audience"] != "human" or report["generation_status"] != "completed" or not report["content"].strip():
        return None
    account_id = project["account_id"]
    if not configured(await get_settings(account_id)):
        return None
    return await create_document(account_id, project_id=project["id"],
        title=f"{project['brand_name']} · {report['kind']} · v{report['version']} · {report['created_at']}",
        data=report["content"].encode(), mime="text/markdown", filename="report.md", kind="report",
        source_key=f"report:{report['id']}", generated=True, created_at=report["created_at"])


async def backfill(account_id: int, project_id: int, emit=None):
    if not await storage.get_project(project_id, account_id=account_id):
        raise ValueError("project_not_found")
    cursor = 0
    while True:
        batch = await store.rows("""SELECT id FROM reports WHERE project_id=? AND audience='human'
            AND generation_status='completed' AND id>? ORDER BY id LIMIT 100""", (project_id, cursor))
        if not batch:
            break
        for row in batch:
            await import_report(await storage.get_report(row["id"]))
            cursor = row["id"]
        if emit:
            await emit(event_type="progress", phase="backfill", status="running", summary=f"Imported reports through {cursor}")


async def cleanup(account_id: int):
    # Private documents whose project was deleted must be tombstoned too.
    await store.execute("UPDATE rag_documents SET deleted=1 WHERE account_id=? AND scope='project' AND project_id IS NULL", (account_id,))
    docs = await store.rows("SELECT * FROM rag_documents WHERE account_id=? AND deleted=1", (account_id,))
    profiles = await store.rows("SELECT * FROM rag_profiles WHERE account_id=?", (account_id,))
    for doc in docs:
        for profile in profiles:
            await providers.vectors.delete(profile["collection_name"], account_id, "document_id", [doc["id"]])
        versions = await store.rows("SELECT original_path FROM rag_versions WHERE document_id=?", (doc["id"],))
        async with store.database() as db:
            await db.execute("""DELETE FROM rag_fts WHERE chunk_id IN
                (SELECT c.id FROM rag_chunks c JOIN rag_generations g ON g.id=c.generation_id WHERE g.document_id=?)""", (doc["id"],))
            await db.execute("DELETE FROM rag_generations WHERE document_id=?", (doc["id"],))
            await db.commit()
        for version in versions:
            safe_file(version["original_path"]).unlink(missing_ok=True)
    # Failed generations are safe to discard and can be deterministically rebuilt.
    stale = await store.rows("""SELECT g.id,p.collection_name FROM rag_generations g JOIN rag_profiles p ON p.id=g.profile_id
        WHERE p.account_id=? AND g.status='building' AND g.created_at<datetime('now','-1 day')""", (account_id,))
    for gen in stale:
        await providers.vectors.delete(gen["collection_name"], account_id, "generation_id", [gen["id"]])
        async with store.database() as db:
            await db.execute("DELETE FROM rag_fts WHERE chunk_id IN (SELECT id FROM rag_chunks WHERE generation_id=?)", (gen["id"],))
            await db.execute("DELETE FROM rag_generations WHERE id=?", (gen["id"],))
            await db.commit()
    # Reconcile points that survived a DB rollback, interrupted deletion or restore.
    # Only inspect this account's known collections; never delete foreign points.
    for profile in profiles:
        offset = None
        while True:
            ids, offset = await providers.vectors.scroll_ids(profile['collection_name'], account_id, offset)
            if ids:
                known = await store.rows('SELECT c.id FROM rag_chunks c JOIN rag_generations g ON g.id=c.generation_id '
                    'JOIN rag_documents d ON d.id=g.document_id WHERE d.account_id=? AND d.deleted=0 AND g.profile_id=? '
                    'AND c.id IN (' + ','.join('?' for _ in ids) + ')', [account_id, profile['id']] + [str(i) for i in ids])
                valid_ids = {r['id'] for r in known}
                await providers.vectors.delete_ids(profile['collection_name'], account_id, [i for i in ids if str(i) not in valid_ids])
            if offset is None:
                break


async def _execute_knowledge_task(ctx):
    payload = ctx.task["payload"]
    account_id = int(payload["account_id"])
    operation = payload["operation"]
    try:
        if operation == "ingest":
            await ingest(account_id, payload["document_id"], payload["version_id"], emit=ctx.emit)
        elif operation == "rebuild":
            await rebuild(account_id, emit=ctx.emit)
        elif operation == "backfill":
            await backfill(account_id, ctx.task["project_id"], emit=ctx.emit)
        elif operation == "cleanup":
            await cleanup(account_id)
        elif operation == "refresh":
            doc = await store.document(account_id, payload["document_id"])
            if doc:
                profiles = await store.rows("SELECT * FROM rag_profiles WHERE account_id=?", (account_id,))
                for profile in profiles:
                    await providers.vectors.update_metadata(profile["collection_name"], account_id, doc["id"],
                        {"scope": doc["scope"], "external_use": bool(doc["external_use"])})
                chunks = await store.rows("SELECT c.id,c.heading FROM rag_chunks c JOIN rag_generations g ON g.id=c.generation_id WHERE g.document_id=? AND c.level='child'", (doc["id"],))
                async with store.database() as db:
                    for chunk in chunks:
                        title = " ".join(lexical_terms(doc["title"] + " " + chunk["heading"] + " " + doc["tags_json"]))
                        await db.execute("UPDATE rag_fts SET title=? WHERE chunk_id=?", (title, chunk["id"]))
                    await db.commit()
        else:
            raise ValueError("unknown_knowledge_operation")
        await ctx.complete({"operation": operation, "document_id": payload.get("document_id")})
    except Exception as exc:
        # Only safe codes reach task events; provider exceptions never log request bodies/keys.
        code = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__
        if payload.get("document_id"):
            await store.execute("UPDATE rag_documents SET status='failed',error=? WHERE id=? AND account_id=?",
                                (code[:200], payload["document_id"], account_id))
        elif operation == 'rebuild':
            await store.execute("UPDATE rag_documents SET status=CASE WHEN active_version_id IS NULL THEN 'failed' ELSE 'ready' END,error=? WHERE account_id=? AND status='indexing'", (code[:200], account_id))
        raise RuntimeError(code[:200]) from None


async def schedule_maintenance():
    """Reconcile only enabled accounts, without globally exposing task ownership."""
    accounts = await store.rows("SELECT account_id FROM account_settings WHERE key='RAG_CONFIG'")
    for row in accounts:
        account_id = row["account_id"]
        if not (await get_settings(account_id)).enabled:
            continue
        await enqueue(account_id, "cleanup")
        enabled_at = await storage.get_account_setting(account_id, "RAG_ENABLED_AT")
        if not enabled_at:
            continue
        # Repair report enqueue failures after enabling RAG, not an unsolicited full-history backfill.
        reports = await store.rows("""SELECT r.id FROM reports r JOIN projects p ON p.id=r.project_id
            WHERE p.account_id=? AND r.audience='human' AND r.generation_status='completed'
            AND r.created_at>=? AND NOT EXISTS(SELECT 1 FROM rag_documents d
                WHERE d.account_id=? AND d.source_key='report:' || r.id) ORDER BY r.id LIMIT 100""",
            (account_id, enabled_at, account_id))
        for report in reports:
            await import_report(await storage.get_report(report["id"]))


@contextlib.asynccontextmanager
async def index_lease(account_id: int, task_id: str):
    """Serialize all account index changes even when multiple web workers run."""
    owner = asyncio.current_task()
    while True:
        now = time.time()
        async with store.database() as db:
            await db.execute("""INSERT INTO rag_index_leases(account_id,task_id,expires_at) VALUES(?,?,?)
                ON CONFLICT(account_id) DO UPDATE SET task_id=excluded.task_id,expires_at=excluded.expires_at
                WHERE rag_index_leases.expires_at<? OR rag_index_leases.task_id=?""",
                (account_id, task_id, now + 60, now, task_id))
            await db.commit()
            row = await (await db.execute("SELECT task_id FROM rag_index_leases WHERE account_id=?", (account_id,))).fetchone()
        if row and row["task_id"] == task_id:
            break
        await asyncio.sleep(.5)
    async def renew():
        try:
            while True:
                await asyncio.sleep(15)
                async with store.database() as db:
                    cursor = await db.execute("UPDATE rag_index_leases SET expires_at=? WHERE account_id=? AND task_id=?",
                                              (time.time() + 60, account_id, task_id))
                    await db.commit()
                    if cursor.rowcount != 1:
                        if owner:
                            owner.cancel()
                        return
        except asyncio.CancelledError:
            raise
        except Exception:
            if owner:
                owner.cancel()
    renewal = asyncio.create_task(renew())
    try:
        yield
    finally:
        renewal.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await renewal
        await store.execute("DELETE FROM rag_index_leases WHERE account_id=? AND task_id=?", (account_id, task_id))


async def run_knowledge_executor(ctx):
    account_id = int(ctx.task['payload']['account_id'])
    account = await storage.get_account(account_id)
    if not account or account['status'] != 'active':
        raise ValueError('account_disabled')
    try:
        async with index_lease(account_id, ctx.task["task_id"]):
            await _execute_knowledge_task(ctx)
    except asyncio.CancelledError:
        document_id = ctx.task['payload'].get('document_id')
        if document_id:
            await store.execute("UPDATE rag_documents SET status=CASE WHEN active_version_id IS NULL THEN 'cancelled' ELSE 'ready' END,error='indexing_interrupted' WHERE id=? AND account_id=? AND deleted=0", (document_id, account_id))
        raise
