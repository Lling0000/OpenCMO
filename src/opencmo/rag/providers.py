"""Configurable embedding/reranking APIs and Qdrant, with bounded requests."""
from __future__ import annotations

import asyncio
import math
import os
import time
import weakref

import httpx

from opencmo.rag.config import RagSettings
from opencmo.rag.text import tokens
from opencmo.rag.types import RetrievalRequest


async def record_usage(account_id, role: str, model: str, texts: list[str], data: dict, elapsed: float):
    if account_id is None:
        return
    from opencmo import storage
    reported = {}
    meta = data.get('meta')
    for container in (data.get('usage'), data.get('tokens'), meta.get('tokens') if isinstance(meta, dict) else None):
        if isinstance(container, dict):
            reported.update({k: v for k, v in container.items() if k in {'prompt_tokens', 'completion_tokens', 'total_tokens', 'input_tokens', 'output_tokens'}
                             and isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 10**15 and math.isfinite(v)})
    try:
        await storage.record_usage_event(account_id, 'rag_' + role, metadata={'model': model,
            'input_tokens_estimate': sum(tokens(text) for text in texts), 'reported_tokens': reported, 'duration_ms': elapsed * 1000})
    except Exception:
        # Telemetry must not discard successful model output.
        import logging
        logging.getLogger(__name__).warning('RAG usage event could not be saved')

_http_clients = weakref.WeakKeyDictionary()

def http_client(base: str, key: str):
    clients = _http_clients.setdefault(asyncio.get_running_loop(), {})
    identity = (base.rstrip('/'), key)
    if identity not in clients:
        clients[identity] = httpx.AsyncClient(timeout=15, follow_redirects=False)
    return clients[identity]


async def api_post(base: str, endpoint: str, key: str, payload: dict, timeout: float = 15, attempts: int = 1) -> dict:
    for attempt in range(attempts):
        try:
            response = await http_client(base, key).post(base.rstrip("/") + "/" + endpoint,
                headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {429, 500, 502, 503, 504} or attempt + 1 >= attempts:
                raise RuntimeError(f"{endpoint}_http_{exc.response.status_code}") from None
        except (httpx.HTTPError, ValueError):
            if attempt + 1 >= attempts:
                raise RuntimeError(f"{endpoint}_unavailable") from None
        await asyncio.sleep(min(4, 0.5 * (2 ** attempt)))
    raise RuntimeError(f"{endpoint}_unavailable")

async def embed(texts: list[str], settings: RagSettings, *, attempts=1, account_id=None) -> list[list[float]]:
    if not settings.embedding_api_key:
        raise ValueError("embedding_not_configured")
    if not texts or any(not x.strip() or tokens(x) > settings.embedding_max_tokens for x in texts):
        raise ValueError("invalid_embedding_input")
    started = time.monotonic()
    data = await api_post(settings.embedding_base_url, "embeddings", settings.embedding_api_key,
                          {"model": settings.embedding_model, "input": texts, "encoding_format": "float"},
                          attempts=attempts)
    entries = sorted(data.get("data", []), key=lambda x: x.get("index", -1))
    if len(entries) != len(texts) or [e.get("index") for e in entries] != list(range(len(texts))):
        raise ValueError("invalid_embedding_response")
    vectors = [e["embedding"] for e in entries]
    if not vectors or not vectors[0] or any(len(v) != len(vectors[0]) or not any(v) or
        not all(isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) for x in v) for v in vectors):
        raise ValueError("invalid_embedding_dimensions")
    await record_usage(account_id, 'embedding', settings.embedding_model, texts, data, time.monotonic() - started)
    return vectors

async def rerank(query: str, documents: list[str], settings: RagSettings, *, account_id=None) -> list[tuple[int, float]]:
    if not settings.rerank_api_key:
        raise ValueError("rerank_not_configured")
    started = time.monotonic()
    data = await api_post(settings.rerank_base_url, "rerank", settings.rerank_api_key,
        {"model": settings.rerank_model, "query": query, "documents": documents, "top_n": len(documents),
         "return_documents": False}, timeout=settings.rerank_timeout)
    found = []
    for row in data.get("results", []):
        index, score = row.get("index"), row.get("relevance_score")
        if not isinstance(index, int) or not 0 <= index < len(documents) or not isinstance(score, (float, int)) or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("invalid_rerank_response")
        found.append((index, float(score)))
    if len({i for i, _ in found}) != len(found) or not found:
        raise ValueError("invalid_rerank_response")
    await record_usage(account_id, 'rerank', settings.rerank_model, [query, *documents], data, time.monotonic() - started)
    return sorted(found, key=lambda x: x[1], reverse=True)

class VectorStore:
    def __init__(self):
        self._clients = weakref.WeakKeyDictionary()
        self._ensured = weakref.WeakKeyDictionary()

    def client(self):
        from qdrant_client import AsyncQdrantClient
        clients = self._clients.setdefault(asyncio.get_running_loop(), {})
        url = os.environ.get('OPENCMO_QDRANT_URL', 'http://127.0.0.1:6333')
        key = os.environ.get('OPENCMO_QDRANT_API_KEY') or None
        if (url, key) not in clients:
            clients[(url, key)] = AsyncQdrantClient(url=url, api_key=key, timeout=5, check_compatibility=False)
        return clients[(url, key)]

    async def release(self, client):
        # Connections are owned by this event loop, not by a single search.
        if client not in self._clients.get(asyncio.get_running_loop(), {}).values():
            await client.close()

    async def close(self):
        self._ensured.pop(asyncio.get_running_loop(), None)
        for client in self._clients.pop(asyncio.get_running_loop(), {}).values():
            await client.close()

    async def ensure(self, collection: str, dimensions: int, *, force=False):
        from qdrant_client import models
        ready = self._ensured.setdefault(asyncio.get_running_loop(), set())
        identity = (os.environ.get('OPENCMO_QDRANT_URL'), collection, dimensions)
        if identity in ready and not force:
            return
        client = self.client()
        try:
            if not await client.collection_exists(collection):
                try:
                    await client.create_collection(collection, vectors_config=models.VectorParams(
                        size=dimensions, distance=models.Distance.COSINE, on_disk=True))
                except Exception:
                    if not await client.collection_exists(collection):
                        raise
            info = await client.get_collection(collection)
            if getattr(info.config.params.vectors, 'size', None) != dimensions:
                raise ValueError('collection_dimensions_mismatch')
            for field, schema in (("account_id", models.PayloadSchemaType.KEYWORD),
                                  ("scope", models.PayloadSchemaType.KEYWORD),
                                  ("project_id", models.PayloadSchemaType.INTEGER),
                                  ("external_use", models.PayloadSchemaType.BOOL),
                                  ("document_id", models.PayloadSchemaType.KEYWORD),
                                  ("generation_id", models.PayloadSchemaType.KEYWORD),
                                  ('source_kind', models.PayloadSchemaType.KEYWORD),
                                  ('source_date', models.PayloadSchemaType.DATETIME)):
                if field not in info.payload_schema:
                    await client.create_payload_index(collection, field, schema, wait=True)
            ready.add(identity)
        finally:
            await self.release(client)

    async def upsert(self, collection: str, points: list[dict]):
        from qdrant_client import models
        client = self.client()
        try:
            await client.upsert(collection, [models.PointStruct(**p) for p in points], wait=True)
        except Exception as exc:
            if getattr(exc, 'status_code', None) == 404:
                ready = self._ensured.get(asyncio.get_running_loop(), set())
                ready.difference_update({item for item in ready if item[1] == collection})
            raise
        finally:
            await self.release(client)

    async def search(self, profile: dict, vector: list[float], request: RetrievalRequest, limit: int) -> list[str]:
        from qdrant_client import models
        client = self.client()
        def match(key, value):
            return models.FieldCondition(key=key, match=models.MatchValue(value=value))
        scope = [match("scope", "account")]
        if request.project_id is not None:
            scope.append(match("project_id", request.project_id))
        conditions = [match("account_id", str(request.account_id)), models.Filter(should=scope)]
        if request.purpose == "content":
            conditions.append(match("external_use", True))
        if request.source_types:
            conditions.append(models.FieldCondition(key='source_kind', match=models.MatchAny(any=request.source_types)))
        if request.date_from or request.date_to:
            conditions.append(models.FieldCondition(key='source_date', range=models.DatetimeRange(
                gte=request.date_from + 'T00:00:00Z' if request.date_from else None,
                lte=request.date_to + 'T23:59:59.999999Z' if request.date_to else None)))
        try:
            result = await client.query_points(profile["collection_name"], query=vector,
                query_filter=models.Filter(must=conditions), limit=limit, with_payload=False)
            return [str(p.id) for p in result.points]
        finally:
            await self.release(client)

    async def delete(self, collection: str, account_id: int, field: str, values: list[str]):
        from qdrant_client import models
        client = self.client()
        try:
            if await client.collection_exists(collection):
                await client.delete(collection, models.FilterSelector(filter=models.Filter(must=[
                    models.FieldCondition(key="account_id", match=models.MatchValue(value=str(account_id))),
                    models.FieldCondition(key=field, match=models.MatchAny(any=values)),
                ])), wait=True)
        finally:
            await self.release(client)

    async def scroll_ids(self, collection: str, account_id: int, offset=None):
        from qdrant_client import models
        client = self.client()
        try:
            if not await client.collection_exists(collection):
                return [], None
            points, next_offset = await client.scroll(collection, limit=256, offset=offset,
                scroll_filter=models.Filter(must=[models.FieldCondition(key='account_id', match=models.MatchValue(value=str(account_id)))]),
                with_payload=False, with_vectors=False)
            return [point.id for point in points], next_offset
        finally:
            await self.release(client)

    async def delete_ids(self, collection: str, account_id: int, ids: list):
        from qdrant_client import models
        if not ids:
            return
        client = self.client()
        try:
            await client.delete(collection, models.FilterSelector(filter=models.Filter(must=[
                models.FieldCondition(key='account_id', match=models.MatchValue(value=str(account_id))),
                models.HasIdCondition(has_id=ids),
            ])), wait=True)
        finally:
            await self.release(client)

    async def update_metadata(self, collection: str, account_id: int, document_id: str, payload: dict):
        from qdrant_client import models
        client = self.client()
        try:
            if await client.collection_exists(collection):
                await client.set_payload(collection, payload, points=models.Filter(must=[
                    models.FieldCondition(key="account_id", match=models.MatchValue(value=str(account_id))),
                    models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
                ]), wait=True)
        finally:
            await self.release(client)

vectors = VectorStore()

async def close_clients():
    await vectors.close()
    for client in _http_clients.pop(asyncio.get_running_loop(), {}).values():
        await client.aclose()
