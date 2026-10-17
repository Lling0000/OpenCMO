"""Tests for debuggable deep-search tracing and caching."""

import json


def test_record_trace_writes_jsonl(tmp_path, monkeypatch):
    import opencmo.tools.deep_search_trace as trace

    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_TRACE", "1")
    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_DIR", str(tmp_path))

    event = trace.record_trace(
        tool="web_search",
        action="search",
        payload={"query": "OpenCMO competitors"},
        provider="tavily",
        output="A long but useful search result",
    )

    lines = trace.trace_path().read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["id"] == event["id"]
    assert stored["tool"] == "web_search"
    assert stored["action"] == "search"
    assert stored["payload"]["query"] == "OpenCMO competitors"
    assert stored["provider"] == "tavily"
    assert stored["output_preview"] == "A long but useful search result"


def test_cache_round_trip_requires_opt_in(tmp_path, monkeypatch):
    import opencmo.tools.deep_search_trace as trace

    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_DIR", str(tmp_path))
    payload = {"query": "OpenCMO"}

    trace.set_cached("web_search", "search", payload, "cached result")
    assert trace.get_cached("web_search", "search", payload) is None

    monkeypatch.setenv("OPENCMO_DEEP_SEARCH_CACHE", "1")
    trace.set_cached("web_search", "search", payload, "cached result")
    assert trace.get_cached("web_search", "search", payload) == "cached result"
