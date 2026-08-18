"""Structured tracing and optional caching for deep-search tool calls."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


DEFAULT_PREVIEW_CHARS = 600


def _is_disabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"0", "false", "off", "no"}


def tracing_enabled() -> bool:
    return not _is_disabled(os.getenv("OPENCMO_DEEP_SEARCH_TRACE"))


def cache_enabled() -> bool:
    return os.getenv("OPENCMO_DEEP_SEARCH_CACHE", "").strip().lower() in {"1", "true", "on", "yes"}


def _state_dir() -> Path:
    custom_dir = os.getenv("OPENCMO_DEEP_SEARCH_DIR")
    if custom_dir:
        return Path(custom_dir).expanduser()
    return Path.home() / ".opencmo" / "deep_search"


def trace_path() -> Path:
    return _state_dir() / "trace.jsonl"


def cache_path() -> Path:
    return _state_dir() / "cache.json"


def _json_default(value: Any) -> str:
    return str(value)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)


def cache_key(tool: str, action: str, payload: dict[str, Any]) -> str:
    raw = _stable_json({"tool": tool, "action": action, "payload": payload})
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def summarize_text(text: Any, *, max_chars: int = DEFAULT_PREVIEW_CHARS) -> str:
    if text is None:
        return ""
    collapsed = " ".join(str(text).split())
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[:max_chars] + "..."


def record_trace(
    *,
    tool: str,
    action: str,
    payload: dict[str, Any],
    provider: str | None = None,
    cache_hit: bool = False,
    output: Any = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one structured deep-search event to the JSONL trace."""
    event = {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "tool": tool,
        "action": action,
        "provider": provider,
        "cache_hit": cache_hit,
        "payload": payload,
        "output_preview": summarize_text(output),
        "output_chars": len(str(output)) if output is not None else 0,
        "error": error,
        "metadata": metadata or {},
    }
    if not tracing_enabled():
        return event

    path = trace_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def _load_cache() -> dict[str, Any]:
    path = cache_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_cached(tool: str, action: str, payload: dict[str, Any]) -> Any | None:
    if not cache_enabled():
        return None
    key = cache_key(tool, action, payload)
    entry = _load_cache().get(key)
    if not isinstance(entry, dict):
        return None
    return entry.get("value")


def set_cached(tool: str, action: str, payload: dict[str, Any], value: Any) -> None:
    if not cache_enabled():
        return
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _load_cache()
    data[cache_key(tool, action, payload)] = {
        "stored_at": time.time(),
        "tool": tool,
        "action": action,
        "payload": payload,
        "value": value,
    }
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, sort_keys=True, indent=2)
    tmp_path.replace(path)
