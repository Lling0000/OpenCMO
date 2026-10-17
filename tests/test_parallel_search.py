"""Exercise agent dispatch through the real HTTP MCP transport, without live APIs."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from agents import Model, ModelResponse, RunConfig, Runner, Usage
from agents.mcp import server as mcp_server
from agents.tool_context import ToolContext
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

from opencmo import llm
from opencmo.tools import parallel_search as backend
from opencmo.tools.search import web_search

# Agents supports both major MCP SDK versions, with matching HTTP clients.
if getattr(mcp_server, "MCP_V2", False):
    import httpx2 as httpx
else:
    import httpx

SOURCE_URL = "https://example.org/market?category=ai&lang=zh#growth"
SEARCH_TEXT = json.dumps({"results": [{
    "title": "Market research", "url": SOURCE_URL, "excerpts": ["A useful market signal."],
}]})


@pytest.fixture(autouse=True)
def search_settings(monkeypatch):
    monkeypatch.delenv("OPENCMO_SEARCH_PROVIDER", raising=False)
    token = llm.set_current_account_settings({})
    try:
        yield
    finally:
        llm.reset_current_account_settings(token)


@pytest.fixture
def mcp_transport(monkeypatch):
    """Keep SDK discovery, protocol handling and serialization real."""
    state = {"requests": [], "sse": False, "error": None, "content": SEARCH_TEXT,
             "started": asyncio.Event()}

    async def handle(request):
        assert str(request.url) == backend.MCP_URL
        assert request.headers["user-agent"] == backend.USER_AGENT
        assert "authorization" not in request.headers
        if request.method != "POST":
            return httpx.Response(405)
        payload = json.loads(request.content)
        state["requests"].append(payload)
        method = payload["method"]
        if method == "server/discover":
            # MCP v2 probes before falling back to the legacy HTTP handshake.
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"],
                                           "error": {"code": -32601, "message": "Method not found"}})
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": payload["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "Search fixture", "version": "1.0"},
            }
        elif method == "tools/list":
            result = {"tools": [{
                "name": "web_search", "description": "Search sources",
                "inputSchema": {"type": "object", "properties": {
                    "objective": {"type": "string"},
                    "search_queries": {"type": "array", "items": {"type": "string"}},
                }, "required": ["objective", "search_queries"]},
            }]}
        else:
            assert method == "tools/call"
            assert payload["params"]["name"] == "web_search"
            error = state["error"]
            if error == "timeout":
                raise httpx.ReadTimeout("fixture timeout", request=request)
            if error == "http":
                return httpx.Response(503)
            if error == "malformed":
                return httpx.Response(200, text="broken", headers={"content-type": "application/json"})
            if error == "cancel":
                state["started"].set()
                await asyncio.Event().wait()
            result = {"isError": error == "tool", "content": [
                {"type": "text", "text": state["content"]},
            ]}
        response = {"jsonrpc": "2.0", "id": payload["id"], "result": result}
        if state["sse"]:
            return httpx.Response(200, text="event: message\ndata: " + json.dumps(response) + "\n\n",
                                  headers={"content-type": "text/event-stream"})
        return httpx.Response(200, json=response)

    def client_factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth,
                                 transport=httpx.MockTransport(handle))

    original = backend.MCPServerStreamableHttp

    def make_server(**kwargs):
        kwargs["params"]["httpx_client_factory"] = client_factory
        return original(**kwargs)

    monkeypatch.setattr(backend, "MCPServerStreamableHttp", make_server)
    return state


async def invoke(query="AI market research"):
    arguments = json.dumps({"query": query})
    context = ToolContext(context=None, tool_name="web_search", tool_call_id="search-test",
                          tool_arguments=arguments)
    return await web_search.on_invoke_tool(context, arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize("sse", [False, True])
async def test_parallel_dispatches_http_mcp_and_preserves_sources(monkeypatch, mcp_transport, sse):
    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", "parallel")
    monkeypatch.setenv("PARALLEL_API_KEY", "unused-ambient-key")
    mcp_transport["sse"] = sse
    query = "AI growth & 市场 research"
    result = await invoke(query)
    assert SOURCE_URL in result
    assert "A useful market signal." in result
    calls = mcp_transport["requests"]
    assert [p["method"] for p in calls if p["method"] != "server/discover"] == [
        "initialize", "notifications/initialized", "tools/list", "tools/call",
    ]
    assert calls[-1]["params"]["arguments"] == {"objective": query, "search_queries": [query]}


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", [None, "auto"])
async def test_existing_tavily_default_is_preserved(monkeypatch, mcp_transport, provider):
    from opencmo.tools import tavily_helper

    if provider:
        monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", provider)
    monkeypatch.setenv("TAVILY_API_KEY", "configured-key")
    search = AsyncMock(return_value=[tavily_helper.TavilyResult("Tavily source", SOURCE_URL, "Snippet")])
    monkeypatch.setattr(tavily_helper, "tavily_search", search)
    assert "Tavily source" in await invoke()
    search.assert_awaited_once()
    assert not mcp_transport["requests"]


@pytest.mark.asyncio
async def test_fresh_no_search_key_keeps_google_fallback(monkeypatch, mcp_transport):
    import crawl4ai

    from opencmo.tools import tavily_helper

    monkeypatch.setenv("OPENAI_BASE_URL", "https://model.example/v1")
    monkeypatch.setattr(tavily_helper, "tavily_search", AsyncMock(return_value=None))
    crawl = AsyncMock(return_value=SimpleNamespace(markdown="Google search results"))
    crawler = AsyncMock()
    crawler.__aenter__.return_value.arun = crawl
    monkeypatch.setattr(crawl4ai, "AsyncWebCrawler", lambda: crawler)
    assert await invoke() == "Google search results"
    assert crawl.await_args.kwargs["url"].startswith("https://www.google.com/search?")
    assert not mcp_transport["requests"]


@pytest.mark.asyncio
async def test_saved_choice_and_request_override(monkeypatch, mcp_transport):
    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", "none")
    saved = llm.set_current_account_settings({"OPENCMO_SEARCH_PROVIDER": "parallel"})
    try:
        assert SOURCE_URL in await invoke()
        mcp_transport["requests"].clear()
        override = llm.set_request_keys({"OPENCMO_SEARCH_PROVIDER": "none"})
        try:
            assert await invoke() == "Web search is disabled."
            assert not mcp_transport["requests"]
        finally:
            llm.reset_request_keys(override)
    finally:
        llm.reset_current_account_settings(saved)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["none", "unknown"])
async def test_disabled_and_invalid_choices_do_not_search(monkeypatch, mcp_transport, provider):
    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", provider)
    result = await invoke()
    assert "disabled" in result or "Unknown" in result
    assert not mcp_transport["requests"]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", ["tool", "http", "malformed", "timeout"])
async def test_explicit_parallel_failure_never_switches_provider(monkeypatch, mcp_transport, error):
    from opencmo.tools import tavily_helper

    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", "parallel")
    mcp_transport["error"] = error
    monkeypatch.setattr(backend, "_TIMEOUT_SECONDS", 0.2)
    fallback = AsyncMock(side_effect=AssertionError("Provider switched"))
    monkeypatch.setattr(tavily_helper, "tavily_search", fallback)
    assert await invoke() == "Parallel web search failed. Please try again later."
    fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_result(monkeypatch, mcp_transport):
    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", "parallel")
    mcp_transport["content"] = ""
    assert await invoke() == "No search results found."


@pytest.mark.asyncio
async def test_cancellation_propagates(monkeypatch, mcp_transport):
    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", "parallel")
    mcp_transport["error"] = "cancel"
    task = asyncio.create_task(invoke())
    await asyncio.wait_for(mcp_transport["started"].wait(), timeout=2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=2)


@pytest.mark.asyncio
async def test_overall_deadline_cancels_work(monkeypatch):
    finished = asyncio.Event()

    async def stalled(query):
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()

    monkeypatch.setattr(backend, "_search", stalled)
    monkeypatch.setattr(backend, "_TIMEOUT_SECONDS", 0.01)
    with pytest.raises(asyncio.TimeoutError):
        await backend.parallel_search("market research")
    assert finished.is_set()


class _ScriptedModel(Model):
    """Scripted model fixture; does not make an inference API request."""

    def __init__(self, *, permission=False):
        self.calls = 0
        self.permission = permission

    async def get_response(self, *args, **kwargs):
        tools = kwargs["tools"]
        if self.permission:
            assert not tools
        elif self.calls == 0:
            assert any(tool.name == "web_search" for tool in tools)
            self.calls += 1
            return ModelResponse(output=[ResponseFunctionToolCall(
                type="function_call", name="web_search", call_id="search-1", id="search-1",
                arguments=json.dumps({"query": "AI market research"}),
            )], usage=Usage(), response_id="first")
        else:
            outputs = [i for i in kwargs["input"] if isinstance(i, dict) and i.get("type") == "function_call_output"]
            assert outputs and SOURCE_URL in outputs[-1]["output"]
            assert "A useful market signal." in outputs[-1]["output"]
        self.calls += 1
        return ModelResponse(output=[ResponseOutputMessage(
            type="message", id="answer", role="assistant", status="completed",
            content=[ResponseOutputText(type="output_text", text="Research consumed.", annotations=[])],
        )], usage=Usage(), response_id="last")

    async def stream_response(self, *args, **kwargs):
        raise NotImplementedError
        yield


@pytest.mark.asyncio
async def test_cmo_runner_consumes_search_result(monkeypatch, mcp_transport):
    from opencmo.agents.cmo import cmo_agent

    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", "parallel")
    registered = next(t for t in cmo_agent.tools if getattr(t, "name", None) == "web_search")
    assert registered is web_search
    model = _ScriptedModel()
    agent = cmo_agent.clone(model=model, tools=[registered], handoffs=[])
    result = await Runner.run(agent, "Research AI markets", run_config=RunConfig(tracing_disabled=True))
    assert result.final_output == "Research consumed."
    assert model.calls == 2
    assert any(p["method"] == "tools/call" for p in mcp_transport["requests"])


@pytest.mark.asyncio
async def test_sdk_tool_permission_is_preserved(monkeypatch, mcp_transport):
    from opencmo.agents.cmo import cmo_agent

    monkeypatch.setenv("OPENCMO_SEARCH_PROVIDER", "parallel")
    monkeypatch.setattr(web_search, "is_enabled", False)
    agent = cmo_agent.clone(model=_ScriptedModel(permission=True), tools=[web_search], handoffs=[])
    await Runner.run(agent, "Research AI markets", run_config=RunConfig(tracing_disabled=True))
    assert not mcp_transport["requests"]
