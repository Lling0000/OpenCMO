"""Settings API router.

Per-account multi-tenant credentials. Each authenticated user reads/writes
keys under their own account; account A never sees account B's values.

For dev/test mode where no session is attached, ``get_request_account_id``
falls back to the admin account so the API stays usable in open mode.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from opencmo import storage
from opencmo.web.auth import get_request_account_id, normalize_external_https_url

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)


def _mask_key(key: str) -> str:
    if len(key) > 8:
        return f"{key[:3]}...{key[-4:]}"
    return "***" if key else ""


_ALL_SETTING_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENCMO_MODEL_DEFAULT",
    # Reddit
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD",
    "OPENCMO_AUTO_PUBLISH",
    # Twitter
    "TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET",
    # GEO
    "ANTHROPIC_API_KEY", "GOOGLE_AI_API_KEY", "MOONSHOT_API_KEY", "DASHSCOPE_API_KEY",
    "DEEPSEEK_API_KEY", "ZHIPU_API_KEY", "DOUBAO_API_KEY", "OPENCMO_GEO_CHATGPT",
    "CLORO_API_KEY",
    # SEO
    "PAGESPEED_API_KEY", "GOOGLE_GSC_CREDENTIALS", "GOOGLE_GSC_SITE_URL",
    # Search (Tavily)
    "TAVILY_API_KEY",
    # GitHub
    "GITHUB_TOKEN",
    # SERP
    "DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD",
    # Email
    "OPENCMO_SMTP_HOST", "OPENCMO_SMTP_PORT", "OPENCMO_SMTP_USER", "OPENCMO_SMTP_PASS",
    "OPENCMO_REPORT_EMAIL",
)


async def _account_value(account_id: int, key: str) -> str:
    """Return the per-account value (no env / no system fallback)."""
    return (await storage.get_account_setting(account_id, key)) or ""


@router.get("/settings")
async def api_v1_settings_get(request: Request):
    account_id = await get_request_account_id(request)

    async def get(name: str) -> str:
        return await _account_value(account_id, name)

    # OPENAI_API_KEY is unified — server-provided. Fall back to env so the
    # status badge reflects "LLM is available" even when the account hasn't
    # (and shouldn't need to) save its own.
    api_key = await get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    base_url = await get("OPENAI_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "")
    model = await get("OPENCMO_MODEL_DEFAULT") or os.environ.get("OPENCMO_MODEL_DEFAULT", "")
    # Reddit
    reddit_cid = await get("REDDIT_CLIENT_ID")
    reddit_secret = await get("REDDIT_CLIENT_SECRET")
    reddit_user = await get("REDDIT_USERNAME")
    reddit_pass = await get("REDDIT_PASSWORD")
    auto_publish = await get("OPENCMO_AUTO_PUBLISH")
    # Twitter
    twitter_api_key = await get("TWITTER_API_KEY")
    twitter_api_secret = await get("TWITTER_API_SECRET")
    twitter_access_token = await get("TWITTER_ACCESS_TOKEN")
    twitter_access_secret = await get("TWITTER_ACCESS_SECRET")
    # GEO platforms
    anthropic_key = await get("ANTHROPIC_API_KEY")
    google_ai_key = await get("GOOGLE_AI_API_KEY")
    moonshot_key = await get("MOONSHOT_API_KEY")
    dashscope_key = await get("DASHSCOPE_API_KEY")
    deepseek_key = await get("DEEPSEEK_API_KEY")
    zhipu_key = await get("ZHIPU_API_KEY")
    doubao_key = await get("DOUBAO_API_KEY")
    cloro_key = await get("CLORO_API_KEY")
    geo_chatgpt = await get("OPENCMO_GEO_CHATGPT")
    # SEO
    pagespeed_key = await get("PAGESPEED_API_KEY")
    gsc_credentials = await get("GOOGLE_GSC_CREDENTIALS")
    gsc_site_url = await get("GOOGLE_GSC_SITE_URL")
    # Search (Tavily)
    tavily_key = await get("TAVILY_API_KEY")
    # GitHub
    github_token = await get("GITHUB_TOKEN")
    # SERP
    dataforseo_login = await get("DATAFORSEO_LOGIN")
    dataforseo_pass = await get("DATAFORSEO_PASSWORD")
    # Email (per-account)
    smtp_host = await get("OPENCMO_SMTP_HOST")
    smtp_port = await get("OPENCMO_SMTP_PORT")
    smtp_user = await get("OPENCMO_SMTP_USER")
    smtp_pass = await get("OPENCMO_SMTP_PASS")
    report_email = await get("OPENCMO_REPORT_EMAIL")

    # System SMTP is considered active when the current account hasn't
    # configured its own SMTP credentials, but the admin account / env has.
    user_smtp_configured = bool(smtp_host and smtp_user and smtp_pass)
    system_smtp_active = False
    if not user_smtp_configured:
        system_host = await storage.get_system_setting("OPENCMO_SMTP_HOST") or os.environ.get("OPENCMO_SMTP_HOST")
        system_user = await storage.get_system_setting("OPENCMO_SMTP_USER") or os.environ.get("OPENCMO_SMTP_USER")
        system_pass = await storage.get_system_setting("OPENCMO_SMTP_PASS") or os.environ.get("OPENCMO_SMTP_PASS")
        system_smtp_active = bool(system_host and system_user and system_pass)

    return JSONResponse({
        "api_key_set": bool(api_key),
        "api_key_masked": _mask_key(api_key),
        "base_url": base_url,
        "model": model,
        # Reddit
        "reddit_configured": bool(reddit_cid and reddit_secret and reddit_user and reddit_pass),
        "reddit_username": reddit_user,
        "auto_publish": auto_publish == "1",
        # Twitter
        "twitter_configured": bool(twitter_api_key and twitter_api_secret and twitter_access_token and twitter_access_secret),
        "twitter_api_key_masked": _mask_key(twitter_api_key),
        # GEO
        "anthropic_key_set": bool(anthropic_key),
        "anthropic_key_masked": _mask_key(anthropic_key),
        "google_ai_key_set": bool(google_ai_key),
        "google_ai_key_masked": _mask_key(google_ai_key),
        "moonshot_key_set": bool(moonshot_key),
        "moonshot_key_masked": _mask_key(moonshot_key),
        "dashscope_key_set": bool(dashscope_key),
        "dashscope_key_masked": _mask_key(dashscope_key),
        "deepseek_key_set": bool(deepseek_key),
        "deepseek_key_masked": _mask_key(deepseek_key),
        "zhipu_key_set": bool(zhipu_key),
        "zhipu_key_masked": _mask_key(zhipu_key),
        "doubao_key_set": bool(doubao_key),
        "doubao_key_masked": _mask_key(doubao_key),
        "cloro_key_set": bool(cloro_key),
        "cloro_key_masked": _mask_key(cloro_key),
        "geo_chatgpt_enabled": geo_chatgpt == "1",
        # SEO
        "pagespeed_key_set": bool(pagespeed_key),
        "pagespeed_key_masked": _mask_key(pagespeed_key),
        "gsc_credentials_set": bool(gsc_credentials),
        "gsc_site_url": gsc_site_url,
        # Search (Tavily)
        "tavily_key_set": bool(tavily_key),
        "tavily_key_masked": _mask_key(tavily_key),
        # GitHub
        "github_token_set": bool(github_token),
        "github_token_masked": _mask_key(github_token),
        # SERP
        "dataforseo_configured": bool(dataforseo_login and dataforseo_pass),
        "dataforseo_login": dataforseo_login,
        # Email
        "email_configured": user_smtp_configured,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "report_email": report_email,
        "system_smtp_active": system_smtp_active,
    })


@router.post("/settings")
async def api_v1_settings_save(request: Request):
    """Save credentials onto the current user's account.

    Any authenticated user (or, in dev mode, the implicit admin fallback)
    can save their own account's settings — there's no admin gate.
    """
    body = await request.json()
    account_id = await get_request_account_id(request)
    for key in _ALL_SETTING_KEYS:
        val = body.get(key)
        if val is None:
            continue
        val = val.strip() if isinstance(val, str) else str(val)
        if val and key == "OPENAI_BASE_URL":
            try:
                val = normalize_external_https_url(val, field_name=key)
            except ValueError as exc:
                return JSONResponse(
                    {"error": str(exc), "error_code": "invalid_setting"},
                    status_code=422,
                )
        if val:
            await storage.set_account_setting(account_id, key, val)
            # Keep env var in sync for the legacy global cascade. Only the
            # admin account's saves should leak into the process-wide env —
            # otherwise account B writing to env would shadow account A.
            try:
                admin_id = await storage.get_admin_account_id()
            except Exception:
                admin_id = None
            if admin_id is not None and int(admin_id) == int(account_id):
                os.environ[key] = val
        else:
            await storage.delete_account_setting(account_id, key)
            try:
                admin_id = await storage.get_admin_account_id()
            except Exception:
                admin_id = None
            if admin_id is not None and int(admin_id) == int(account_id):
                os.environ.pop(key, None)
    return JSONResponse({"ok": True})
