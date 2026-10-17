"""Tests for the debuggable deep-search planning loop."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
import importlib

import pytest


@pytest.mark.asyncio
async def test_run_deep_search_traces_search_read_loop(tmp_path, monkeypatch):
    import opencmo.tools.deep_search_trace as trace
    from opencmo.tools.deep_search import run_deep_search

    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_TRACE", "1")
    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_DIR", str(tmp_path))

    search_mock = AsyncMock(
        return_value=[
            SimpleNamespace(
                title="Example",
                url="https://example.com/pricing",
                snippet="Pricing and competitor context",
            )
        ]
    )
    fetch_mock = AsyncMock(return_value=("# Pricing page\nEnterprise details", "tavily"))

    monkeypatch.setattr("opencmo.tools.tavily_helper.tavily_search", search_mock)
    monkeypatch.setattr("opencmo.tools.crawl.fetch_url_content", fetch_mock)

    result = await run_deep_search("Example pricing", max_depth=2)

    assert result["max_depth"] == 2
    assert len(result["steps"]) == 2
    assert result["steps"][0]["read_url"] == "https://example.com/pricing"
    assert "Step 1: Example pricing" in result["summary"]
    assert "Read source: tavily" in result["summary"]
    assert search_mock.await_count == 2
    assert fetch_mock.await_count == 2

    events = [line for line in trace.trace_path().read_text(encoding="utf-8").splitlines()]
    assert any('"tool": "deep_search"' in line and '"action": "search"' in line for line in events)
    assert any('"tool": "deep_search"' in line and '"action": "read"' in line for line in events)
    assert any('"tree"' in line for line in events)


@pytest.mark.asyncio
async def test_run_deep_search_clamps_depth(monkeypatch):
    from opencmo.tools.deep_search import run_deep_search

    search_mock = AsyncMock(return_value=[])
    monkeypatch.setattr("opencmo.tools.tavily_helper.tavily_search", search_mock)

    result = await run_deep_search("OpenCMO", max_depth=99)

    assert result["max_depth"] == 5
    assert len(result["steps"]) == 5


def test_cli_breakpoint_can_override_query(monkeypatch):
    deep_search_module = importlib.import_module("opencmo.tools.deep_search")
    from opencmo.tools.deep_search import DeepSearchStep

    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_BREAKPOINTS", "1")
    monkeypatch.setattr(deep_search_module.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "replacement query")

    override = deep_search_module._maybe_cli_breakpoint(
        DeepSearchStep(depth=1, query="original", thought="test")
    )

    assert override == "replacement query"
