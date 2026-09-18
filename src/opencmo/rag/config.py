"""Validated per-account configuration; no global ai_models credentials."""
from __future__ import annotations

import hashlib
import json
import os

from pydantic import BaseModel, Field, model_validator

from opencmo import storage


class RagSettings(BaseModel):
    enabled: bool = False
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"
    embedding_api_key: str = ""
    embedding_max_tokens: int = Field(default=8192, ge=128, le=131072)
    rerank_base_url: str = "https://api.siliconflow.cn/v1"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_api_key: str = ""
    parent_tokens: int = Field(default=1536, ge=128, le=8192)
    child_tokens: int = Field(default=384, ge=64, le=2048)
    overlap_tokens: int = Field(default=64, ge=0, le=512)
    dense_limit: int = Field(default=30, ge=1, le=100)
    lexical_limit: int = Field(default=30, ge=1, le=100)
    entity_limit: int = Field(default=20, ge=1, le=100)
    fusion_limit: int = Field(default=50, ge=1, le=100)
    rerank_limit: int = Field(default=8, ge=1, le=30)
    rerank_min_score: float = Field(default=0.2, ge=0, le=1)
    max_parents: int = Field(default=6, ge=1, le=20)
    context_tokens: int = Field(default=6000, ge=512, le=24000)
    query_timeout: float = Field(default=10, ge=1, le=60)
    rewrite_timeout: float = Field(default=2, ge=0.1, le=10)
    rerank_timeout: float = Field(default=4, ge=0.1, le=20)

    @model_validator(mode="after")
    def limits(self):
        self.embedding_api_key = self.embedding_api_key.strip()
        self.rerank_api_key = self.rerank_api_key.strip()
        if self.child_tokens > self.parent_tokens or self.overlap_tokens >= self.child_tokens:
            raise ValueError("overlap_tokens < child_tokens <= parent_tokens is required")
        if self.child_tokens + 256 > self.embedding_max_tokens:
            raise ValueError("Embedding input limit must allow child tokens and title overhead")
        return self

    def public(self) -> dict:
        result = self.model_dump(exclude={"embedding_api_key", "rerank_api_key"})
        for name in ("embedding_api_key", "rerank_api_key"):
            result[f"{name}_set"] = bool(getattr(self, name))
        return result

    def fingerprint(self, dimensions: int) -> str:
        identity = {
            "url": self.embedding_base_url.rstrip("/"), "model": self.embedding_model,
            "dimensions": dimensions, "parser": "1", "tokenizer": "cl100k_base",
            "parent": self.parent_tokens, "child": self.child_tokens, "overlap": self.overlap_tokens,
        }
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]


async def get_settings(account_id: int) -> RagSettings:
    raw = await storage.get_account_setting(account_id, "RAG_CONFIG")
    settings = RagSettings.model_validate_json(raw) if raw else RagSettings()
    if os.environ.get("OPENCMO_RAG_ENABLED", "1").lower() in {"0", "false", "off"}:
        settings.enabled = False
    return settings


def configured(settings: RagSettings) -> bool:
    return bool(settings.enabled and settings.embedding_api_key and settings.rerank_api_key)


def document_limit() -> int:
    return int(os.environ.get("OPENCMO_RAG_MAX_DOCUMENTS", "10000"))


def chunk_limit() -> int:
    return int(os.environ.get("OPENCMO_RAG_MAX_CHUNKS", "500000"))
