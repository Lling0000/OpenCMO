"""Tests for Tavily MCP proxy support."""

import json

import pytest


class _FakeResponse:
    def __init__(self, payload: dict):
        self.text = "event: message\ndata: " + json.dumps(payload) + "\n\n"

    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    def __init__(self, calls: list[dict], payload: dict, **_: object):
        self._calls = calls
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(self, url: str, *, json: dict, headers: dict):
        self._calls.append({"url": url, "json": json, "headers": headers})
        return _FakeResponse(self._payload)


@pytest.mark.asyncio
async def test_tavily_search_uses_mcp_proxy(monkeypatch):
    from opencmo.tools.tavily_helper import tavily_search

    calls: list[dict] = []
    tool_payload = {
        "results": [
            {
                "title": "OpenCMO",
                "url": "https://www.aidcmo.com/",
                "content": "AI CMO command center",
            }
        ]
    }
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(tool_payload)}]},
    }
    monkeypatch.setenv("TAVILY_MCP_URL", "https://tavily.example.test/mcp")
    monkeypatch.setenv("TAVILY_MCP_TOKEN", "secret-token")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    import httpx

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(calls, rpc_payload, **kwargs),
    )

    results = await tavily_search("OpenCMO", max_results=1)

    assert results is not None
    assert results[0].title == "OpenCMO"
    assert results[0].url == "https://www.aidcmo.com/"
    assert calls[0]["url"] == "https://tavily.example.test/mcp"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret-token"
    assert calls[0]["json"]["params"]["name"] == "tavily_search"
    assert calls[0]["json"]["params"]["arguments"]["query"] == "OpenCMO"


@pytest.mark.asyncio
async def test_tavily_extract_uses_mcp_proxy(monkeypatch):
    from opencmo.tools.tavily_helper import tavily_extract

    calls: list[dict] = []
    tool_payload = {
        "results": [
            {
                "url": "https://www.aidcmo.com/",
                "raw_content": "# OpenCMO\n\nAI growth tools.",
            }
        ]
    }
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(tool_payload)}]},
    }
    monkeypatch.setenv("TAVILY_MCP_URL", "https://tavily.example.test/mcp")
    monkeypatch.setenv("TAVILY_MCP_TOKEN", "secret-token")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    import httpx

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(calls, rpc_payload, **kwargs),
    )

    content = await tavily_extract("https://www.aidcmo.com/", extract_depth="advanced")

    assert content == "# OpenCMO\n\nAI growth tools."
    assert calls[0]["json"]["params"]["name"] == "tavily_extract"
    assert calls[0]["json"]["params"]["arguments"]["urls"] == ["https://www.aidcmo.com/"]
    assert calls[0]["json"]["params"]["arguments"]["extract_depth"] == "advanced"
