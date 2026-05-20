"""Centralized LLM client management with per-request key isolation.

Solves the BYOK (Bring Your Own Key) concurrency bug where os.environ
was used as shared mutable state across concurrent requests.

Key resolution priority (sync ``get_key`` — used by tools that can't await):
    1. ContextVar (per-request BYOK keys, set by BYOK middleware)
    2. os.environ (from .env or system environment)

Key resolution priority (async ``get_key_async`` — used by web routes):
    1. ContextVar (per-request BYOK keys, set by BYOK middleware)
    2. Per-account row in ``account_settings`` for the account_id ContextVar
       (set by ``session_context_middleware``)
    3. os.environ (for router-default keys, applied early)
    4. Legacy global ``settings`` table (system fallback, via ``get_system_setting``)
    5. os.environ (final fallback)

Usage:
    from opencmo import llm

    # In BYOK middleware — inject per-request keys:
    token = llm.set_request_keys({"OPENAI_API_KEY": "sk-user-xxx"})
    try:
        await call_next(request)
    finally:
        llm.reset_request_keys(token)

    # In the session-context middleware — bind the active account:
    acct_token = llm.set_current_account_id(account["id"])
    try:
        await call_next(request)
    finally:
        llm.reset_current_account_id(acct_token)

    # Anywhere in the codebase — read a key safely:
    api_key = llm.get_key("OPENAI_API_KEY")

    # Get an OpenAI client scoped to the current request:
    client = await llm.get_openai_client()

    # Unified chat completion call:
    text = await llm.chat_completion(system_prompt, user_prompt)
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from contextvars import ContextVar, Token
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_MODEL_DEFAULT = "gpt-5.4"
_ENV_PRIORITY_KEYS = frozenset({
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENCMO_MODEL_DEFAULT",
})
_ACCOUNT_SCOPED_SECRET_KEYS = frozenset({
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME",
    "REDDIT_PASSWORD",
    "TWITTER_API_KEY",
    "TWITTER_API_SECRET",
    "TWITTER_ACCESS_TOKEN",
    "TWITTER_ACCESS_SECRET",
})

# ---------------------------------------------------------------------------
# ContextVar — per-request key isolation (asyncio Task-local)
# ---------------------------------------------------------------------------

_request_keys: ContextVar[dict[str, str]] = ContextVar("request_keys", default={})
_current_account_id: ContextVar[int | None] = ContextVar("current_account_id", default=None)
# Snapshot of the active account's account_settings rows, populated by the
# session middleware so synchronous ``get_key`` callers (publishers, SMTP) can
# see per-account values without an awaitable DB lookup.
_current_account_settings: ContextVar[dict[str, str]] = ContextVar(
    "current_account_settings", default={}
)


def set_request_keys(keys: dict[str, str]) -> Token:
    """Set per-request API keys. Called by BYOK middleware.

    Returns a Token that MUST be passed to reset_request_keys() in a finally block.
    """
    # Filter to only valid non-empty string values
    clean = {k: v.strip() for k, v in keys.items() if isinstance(v, str) and v.strip()}
    return _request_keys.set(clean)


def reset_request_keys(token: Token) -> None:
    """Restore the previous ContextVar state. Called in finally block."""
    _request_keys.reset(token)


def get_request_keys() -> dict[str, str]:
    """Return the current per-request API keys context. Used to capture state for background tasks."""
    return _request_keys.get({}).copy()


def set_current_account_id(account_id: int | None) -> Token:
    """Bind the active account id to this asyncio Task for the duration of the request.

    Used by the web middleware so per-account settings lookups in
    ``get_key_async`` resolve to the right tenant. Background workers must
    capture the queueing account id and restore it before executing a job.

    Returns a Token that MUST be passed to reset_current_account_id().
    """
    value = int(account_id) if account_id else None
    return _current_account_id.set(value)


def reset_current_account_id(token: Token) -> None:
    """Restore the previous account_id ContextVar state."""
    _current_account_id.reset(token)


def get_current_account_id() -> int | None:
    """Return the bound account id, or ``None`` when no account is in scope."""
    return _current_account_id.get(None)


def set_current_account_settings(settings: dict[str, str]) -> Token:
    """Cache the active account's settings dict so sync ``get_key`` can read them.

    The web middleware calls ``storage.list_account_settings`` once per request
    and stores the result here. Sync code paths (e.g. SMTP, Reddit publisher)
    can then call ``llm.get_key`` and transparently see per-account values
    without needing to await the DB.

    Returns a Token that MUST be passed to ``reset_current_account_settings``.
    """
    clean: dict[str, str] = {}
    for key, value in (settings or {}).items():
        if isinstance(value, str) and value.strip():
            clean[str(key)] = value
    return _current_account_settings.set(clean)


def reset_current_account_settings(token: Token) -> None:
    """Restore the previous account settings ContextVar state."""
    _current_account_settings.reset(token)


def get_current_account_settings() -> dict[str, str]:
    """Return a copy of the active account's cached settings dict."""
    return _current_account_settings.get({}).copy()



# ---------------------------------------------------------------------------
# Key resolution — ContextVar > env/.env > DB for router defaults
# ---------------------------------------------------------------------------


def get_key(name: str, default: str | None = None) -> str | None:
    """Get a configuration key value with proper isolation.

    Resolution order:
        1. ContextVar (per-request BYOK keys)
        2. Per-account settings snapshot bound by middleware
        3. os.environ (from .env or system)
        4. ``default``

    Note: the legacy global ``settings`` table is NOT consulted here because
    this function is synchronous. ``get_key_async`` performs that DB read.
    """
    # 1. ContextVar (per-request)
    request = _request_keys.get({})
    val = request.get(name)
    if val:
        return val

    # 2. Snapshot of the active account's account_settings rows (sync-safe)
    account_settings = _current_account_settings.get({})
    val = account_settings.get(name)
    if val:
        return val

    # 3. Sensitive account-scoped secrets must fail closed to avoid
    # cross-account credential bleed through process-global env.
    if name in _ACCOUNT_SCOPED_SECRET_KEYS:
        return default

    # 4. os.environ
    val = os.environ.get(name)
    if val:
        return val

    return default


async def get_key_async(name: str, default: str | None = None) -> str | None:
    """Get a configuration key with multi-tenant DB fallback (async version).

    Resolution order:
        1. ContextVar (per-request BYOK keys)
        2. Per-account settings snapshot bound by middleware
        3. ``account_settings`` row keyed off the current account_id ContextVar
        4. os.environ (router-default keys are checked here early via
           ``_ENV_PRIORITY_KEYS``; all other keys hit env at step 6)
        5. System-level fallback (admin account row → legacy ``settings`` table)
        6. os.environ (final fallback)
        7. ``default``
    """
    # 1. ContextVar (per-request)
    request = _request_keys.get({})
    val = request.get(name)
    if val:
        return val

    # 2. Snapshot of the active account's account_settings rows
    account_settings = _current_account_settings.get({})
    val = account_settings.get(name)
    if val:
        return val

    # 3. Live DB lookup for the bound account, in case the snapshot is empty
    account_id = _current_account_id.get(None)
    if account_id:
        try:
            from opencmo import storage
            val = await storage.get_account_setting(account_id, name)
            if val:
                return val
        except Exception:
            pass

    # 4. Sensitive account-scoped secrets must not fall through to system/env.
    if name in _ACCOUNT_SCOPED_SECRET_KEYS:
        return default

    # 5. For core router defaults, prefer env/.env over persisted DB settings.
    if name in _ENV_PRIORITY_KEYS:
        val = os.environ.get(name)
        if val:
            return val

    # 6. System fallback (admin account → legacy settings table)
    try:
        from opencmo import storage
        val = await storage.get_system_setting(name)
        if val:
            return val
    except Exception:
        pass  # DB may not be initialized yet

    # 7. os.environ
    val = os.environ.get(name)
    if val:
        return val

    return default


# ---------------------------------------------------------------------------
# OpenAI client factory — creates a client for the current request scope
# ---------------------------------------------------------------------------


async def get_openai_client() -> Any:
    """Get an AsyncOpenAI client configured for the current request.

    Uses ContextVar keys if available, falls back to env/DB.
    A new client is created each time because different requests may
    have different API keys (BYOK).
    """
    from openai import AsyncOpenAI

    api_key = await get_key_async("OPENAI_API_KEY")
    base_url = await get_key_async("OPENAI_BASE_URL")

    base_url = normalize_base_url(base_url)

    model = await get_model()
    logger.debug("LLM client: model=%s, base_url=%s", model, base_url or "OpenAI Default")

    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url or None,
    )


def normalize_base_url(base_url: str | None) -> str | None:
    """Normalize OpenAI-compatible endpoints to the form expected by SDK clients."""
    if not base_url:
        return None

    normalized = base_url.strip().rstrip("/")
    if not normalized:
        return None

    # OpenAI official endpoints already route correctly without an explicit /v1 suffix.
    skip_v1_domains = {"api.openai.com", "api.anthropic.com"}
    from urllib.parse import urlparse

    host = urlparse(normalized).hostname or ""
    if host in skip_v1_domains or normalized.endswith("/v1"):
        return normalized
    if normalized.count("/") <= 2:
        return f"{normalized}/v1"
    return normalized


async def get_model(purpose: str = "default") -> str:
    """Get the model name for a given purpose.

    Resolution: OPENCMO_MODEL_{PURPOSE} > OPENCMO_MODEL_DEFAULT > 'gpt-5.4'
    """
    if purpose and purpose != "default":
        specific = await get_key_async(f"OPENCMO_MODEL_{purpose.upper()}")
        if specific:
            return specific
    return (await get_key_async("OPENCMO_MODEL_DEFAULT")) or _MODEL_DEFAULT


# ---------------------------------------------------------------------------
# Unified chat completion — single entry point for all LLM calls
# ---------------------------------------------------------------------------


_MAX_RETRIES = 8
_RETRY_BACKOFF = [2, 5, 10, 20, 30, 60, 120, 300]  # seconds


def _extract_retry_delay_seconds(exc: Exception) -> float | None:
    """Best-effort parse of provider retry hints from exception text."""
    text = str(exc)
    patterns = [
        r"reset_seconds['\"]?\s*:\s*(\d+)",
        r"Retry-After['\"]?\s*:\s*(\d+)",
        r"retryDelay['\"]?\s*:\s*['\"]?([0-9.]+)s['\"]?",
        r"quotaResetDelay['\"]?\s*:\s*['\"]?([0-9.]+)s['\"]?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


async def _call_with_retry(coro_factory, *, timeout: float | None = None) -> Any:
    """Call an LLM coroutine with retry + exponential backoff."""
    for attempt in range(_MAX_RETRIES):
        try:
            coro = coro_factory()
            if timeout:
                resp = await asyncio.wait_for(coro, timeout=timeout)
            else:
                resp = await asyncio.wait_for(coro, timeout=120)
            return resp
        except Exception as exc:
            if attempt < _MAX_RETRIES - 1:
                provider_wait = _extract_retry_delay_seconds(exc)
                if provider_wait is not None:
                    wait = provider_wait
                else:
                    wait = _RETRY_BACKOFF[min(attempt, len(_RETRY_BACKOFF) - 1)]
                logger.warning("LLM call failed (attempt %d/%d): %s — retrying in %ds",
                               attempt + 1, _MAX_RETRIES, exc, wait)
                await asyncio.sleep(wait)
            else:
                raise


async def chat_completion(
    system: str,
    user: str,
    *,
    temperature: float = 0.7,
    timeout: float | None = None,
    model_override: str | None = None,
) -> str:
    """Unified LLM chat completion call with automatic retry.

    Args:
        system: System prompt.
        user: User prompt.
        temperature: Sampling temperature.
        timeout: Optional timeout in seconds.
        model_override: Override the model name (skips get_model lookup).

    Returns:
        The assistant's response content as a string.
    """
    client = await get_openai_client()
    model = model_override or await get_model()

    def make_coro():
        return client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

    resp = await _call_with_retry(make_coro, timeout=timeout)
    return _extract_content(resp)


def _extract_content(resp: Any) -> str:
    """Extract text from a chat completion response.

    Handles MiniMax-style responses where content may be null/empty
    and the actual text lives in reasoning_content.
    """
    msg = resp.choices[0].message
    content = msg.content
    if not content:
        # MiniMax / TeamoRouter: text may be in reasoning_content
        content = getattr(msg, "reasoning_content", None) or ""
    return content.strip()


async def chat_completion_messages(
    messages: list[dict],
    *,
    temperature: float = 0.7,
    timeout: float | None = None,
    model_override: str | None = None,
    max_tokens: int | None = None,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> str:
    """LLM chat completion with custom message list.

    For cases where the caller needs more than system+user (e.g. multi-turn).
    """
    if api_key_override is not None or base_url_override is not None:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key_override if api_key_override is not None else await get_key_async("OPENAI_API_KEY"),
            base_url=base_url_override if base_url_override is not None else await get_key_async("OPENAI_BASE_URL"),
        )
    else:
        client = await get_openai_client()
    model = model_override or await get_model()

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    def make_coro():
        return client.chat.completions.create(**kwargs)

    resp = await _call_with_retry(make_coro, timeout=timeout)
    return _extract_content(resp)


async def chat_completion_with_failover(
    role: str,
    *,
    messages: list[dict] | None = None,
    system: str | None = None,
    user: str | None = None,
    temperature: float = 0.7,
    timeout: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """LLM chat completion with multi-model failover by role.

    Looks up ai_models rows for ``role`` ordered by failover_priority ASC,
    then attempts each enabled candidate in turn. Per-attempt retry uses
    the existing exponential backoff inside chat_completion_messages.

    A candidate is skipped (and we move to the next) when:
        - claim_quota returns False (disabled or daily_limit reached), or
        - chat_completion_messages raises after exhausting its retries.

    If no ai_models rows exist for the role, falls back to the standard
    single-model chat_completion_messages path so existing callers keep
    working during incremental adoption.

    Raises:
        ValueError: when both ``messages`` and ``system``/``user`` are absent.
        RuntimeError: when every model was skipped due to exhausted quotas.
        Exception: the last exception raised by an LLM provider when every
            candidate failed for non-quota reasons.
    """
    if messages is None:
        if system is None or user is None:
            raise ValueError(
                "chat_completion_with_failover requires either messages=[...] "
                "or both system=... and user=..."
            )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    from opencmo.storage.ai_models import claim_quota, list_ai_models

    candidates = await list_ai_models(role=role, enabled_only=True)
    if not candidates:
        return await chat_completion_messages(
            messages,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
        )

    last_exc: Exception | None = None
    any_attempted = False
    for candidate in candidates:
        claimed = await claim_quota(candidate["id"])
        if not claimed:
            logger.warning(
                "ai_models id=%s name=%r skipped — quota exhausted or disabled",
                candidate["id"],
                candidate.get("name"),
            )
            continue
        any_attempted = True
        try:
            return await chat_completion_messages(
                messages,
                temperature=temperature,
                timeout=timeout,
                max_tokens=max_tokens,
                model_override=candidate["model_id"],
                api_key_override=candidate.get("api_key") or None,
                base_url_override=candidate.get("base_url") or None,
            )
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "ai_models id=%s name=%r failed: %s — failing over to next",
                candidate["id"],
                candidate.get("name"),
                exc,
            )
            continue

    if not any_attempted:
        raise RuntimeError(
            f"All ai_models for role={role!r} skipped — daily quota exhausted"
        )
    assert last_exc is not None
    raise last_exc
