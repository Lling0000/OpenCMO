"""Authentication and request-safety helpers for the web app."""

from __future__ import annotations

import hmac
import ipaddress
import os
import re
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse

from opencmo import storage

PUBLIC_API_PATHS = frozenset({
    "/api/v1/auth/signup",
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
    "/api/v1/auth/me",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/resend-code",
    "/api/v1/github-stats",
    "/api/v1/health",
    "/api/v1/site/stats",
    "/api/v1/waitlist",
})

_PROJECT_API_RE = re.compile(r"^/api/v1/projects/(\d+)(?:/|$)")
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

PROTECTED_DOC_PATHS = frozenset({
    "/docs",
    "/redoc",
    "/openapi.json",
})


def get_web_token() -> str:
    """Return the configured admin token, or an empty string in open/dev mode."""
    return os.environ.get("OPENCMO_WEB_TOKEN", "").strip()


def is_auth_enabled() -> bool:
    return bool(get_web_token())


def requires_workspace_auth(path: str, method: str = "GET") -> bool:
    if not is_auth_enabled():
        return False
    if path in PUBLIC_API_PATHS:
        return False
    if path in PROTECTED_DOC_PATHS:
        return True
    if path.startswith("/api/v1/"):
        return True
    if path.startswith("/legacy"):
        return True
    return False


def request_has_valid_bearer(request: Request) -> bool:
    token = get_web_token()
    if not token:
        return False
    auth_header = request.headers.get("Authorization", "")
    scheme, _, value = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return False
    return hmac.compare_digest(value.strip(), token)


def validate_web_token(candidate: str) -> bool:
    token = get_web_token()
    return bool(token) and hmac.compare_digest((candidate or "").strip(), token)


def is_session_auth_enforced() -> bool:
    value = os.environ.get("OPENCMO_REQUIRE_SESSION_AUTH", "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    secret = os.environ.get("OPENCMO_COOKIE_SECRET", "").strip()
    return bool(secret and secret != "replace-me")


def requires_session_auth(path: str) -> bool:
    if path in PUBLIC_API_PATHS:
        return False
    if path.startswith("/api/v1/"):
        return True
    if path.startswith("/legacy"):
        return True
    return False


def _request_origin_host(request: Request) -> str:
    return (request.headers.get("host") or request.url.netloc or "").split(",", 1)[0].lower()


def has_valid_same_origin(request: Request) -> bool:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    candidate = origin or referer
    if not candidate:
        return True
    parsed = urlparse(candidate)
    return parsed.netloc.lower() == _request_origin_host(request)


async def attach_request_context(request: Request) -> dict | None:
    token = request.cookies.get(storage.SESSION_COOKIE_NAME, "")
    context = await storage.get_session_context(token)
    request.state.current_user = context["user"] if context else None
    request.state.current_account = context["account"] if context else None
    request.state.is_admin = bool(context and context["is_admin"])
    return context


def get_current_user(request: Request) -> dict | None:
    return getattr(request.state, "current_user", None)


def get_current_account(request: Request) -> dict | None:
    return getattr(request.state, "current_account", None)


async def get_request_account_id(request: Request) -> int:
    account = get_current_account(request)
    if account:
        return int(account["id"])
    return await storage.get_admin_account_id()


def get_request_user_id(request: Request) -> int | None:
    user = get_current_user(request)
    return int(user["id"]) if user else None


def is_admin_request(request: Request) -> bool:
    return bool(getattr(request.state, "is_admin", False))


async def reject_cross_account_project(request: Request) -> JSONResponse | None:
    match = _PROJECT_API_RE.match(request.url.path)
    if not match:
        return None
    project_id = int(match.group(1))
    account_id = await get_request_account_id(request)
    project = await storage.get_project(project_id, account_id=account_id)
    if not project:
        return JSONResponse({"error": "Not found"}, status_code=404)
    request.state.current_project = project
    return None


def csrf_rejection(request: Request) -> JSONResponse | None:
    if request.method in _SAFE_METHODS:
        return None
    if not request.cookies.get(storage.SESSION_COOKIE_NAME):
        return None
    if has_valid_same_origin(request):
        return None
    return JSONResponse({"error": "CSRF check failed", "error_code": "csrf_failed"}, status_code=403)


def _host_is_blocked(host: str) -> bool:
    normalized = host.strip().lower().rstrip(".")
    if normalized in {"localhost", "0", "0.0.0.0"}:
        return True
    if normalized.endswith(".localhost") or normalized.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return any((
        ip.is_loopback,
        ip.is_link_local,
        ip.is_private,
        ip.is_multicast,
        ip.is_reserved,
        ip.is_unspecified,
    ))


def normalize_external_https_url(value: str, *, field_name: str = "url") -> str:
    """Validate a user-supplied external HTTPS base URL.

    The value is used by server-side provider clients, so reject obvious SSRF
    targets and plaintext protocols. Hostname DNS resolution is intentionally
    not performed here to keep request handling deterministic.
    """
    cleaned = (value or "").strip().rstrip("/")
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme != "https":
        raise ValueError(f"{field_name} must use https")
    if not parsed.hostname or _host_is_blocked(parsed.hostname):
        raise ValueError(f"{field_name} host is not allowed")
    return cleaned
