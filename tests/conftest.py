"""Shared test isolation fixtures."""

import os

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
    # Settings endpoints intentionally update these defaults; restore them even
    # when a test changes os.environ directly rather than through monkeypatch.
    runtime_defaults = {name: os.environ.get(name) for name in
                        ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENCMO_MODEL_DEFAULT')}
    for key in EXTERNAL_PROVIDER_KEYS:
        monkeypatch.delenv(key, raising=False)
    try:
        yield
    finally:
        llm.reset_request_keys(token)
        for name, value in runtime_defaults.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
