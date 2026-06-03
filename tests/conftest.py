"""Shared test isolation fixtures."""

import pytest

EXTERNAL_PROVIDER_KEYS = (
    "TAVILY_API_KEY",
    "TAVILY_MCP_URL",
    "TAVILY_MCP_TOKEN",
    "YOUTUBE_API_KEY",
    "TWITTER_BEARER_TOKEN",
    "DATAFORSEO_LOGIN",
    "DATAFORSEO_PASSWORD",
    "XUEQIU_COOKIE",
)


@pytest.fixture(autouse=True)
def _isolate_external_provider_keys(monkeypatch):
    """Keep tests from enabling live community/SERP providers via local env."""
    from opencmo import llm

    token = llm.set_request_keys({})
    for key in EXTERNAL_PROVIDER_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_TRACE", "0")
    monkeypatch.delenv("OPENCMO_DEEP_SEARCH_CACHE", raising=False)
    monkeypatch.delenv("OPENCMO_DEEP_SEARCH_DIR", raising=False)
    try:
        yield
    finally:
        llm.reset_request_keys(token)
