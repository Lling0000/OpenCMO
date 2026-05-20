"""Shared Tavily helpers for search and URL extraction."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TavilyResult:
    """A single search result from Tavily."""
    title: str
    url: str
    snippet: str


def tavily_available() -> bool:
    """Return True if either Tavily MCP or the official Tavily API is configured."""
    from opencmo import llm
    return bool(_tavily_mcp_config() or llm.get_key("TAVILY_API_KEY"))


def _tavily_mcp_config() -> tuple[str, str] | None:
    from opencmo import llm

    url = (llm.get_key("TAVILY_MCP_URL") or "").strip()
    token = (llm.get_key("TAVILY_MCP_TOKEN") or "").strip()
    if not url or not token:
        return None
    return url, token


def _decode_mcp_response(text: str) -> dict[str, Any]:
    """Decode JSON-RPC over streamable HTTP/SSE into a response object."""
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if not payload or payload == "[DONE]":
            continue
        return json.loads(payload)
    return json.loads(text)


def _mcp_content_payload(result: dict[str, Any]) -> Any:
    """Return the useful payload from an MCP tools/call result."""
    if result.get("isError"):
        content = result.get("content") or []
        message = ""
        if content and isinstance(content[0], dict):
            message = str(content[0].get("text") or "")
        raise RuntimeError(message or "Tavily MCP tool returned an error")

    structured = result.get("structuredContent")
    if structured is not None:
        return structured

    for item in result.get("content") or []:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return None


async def _mcp_tool_call(name: str, arguments: dict[str, Any]) -> Any:
    config = _tavily_mcp_config()
    if not config:
        return None

    import httpx

    url, token = config
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": arguments,
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()

    decoded = _decode_mcp_response(response.text)
    if decoded.get("error"):
        raise RuntimeError(decoded["error"])
    return _mcp_content_payload(decoded.get("result") or {})


def _parse_search_results(response: dict[str, Any] | None) -> list[TavilyResult]:
    results: list[TavilyResult] = []
    if not isinstance(response, dict):
        return results
    for item in response.get("results", []):
        if not isinstance(item, dict):
            continue
        results.append(TavilyResult(
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            snippet=str(item.get("content") or item.get("snippet") or ""),
        ))
    return results


async def _mcp_search(
    query: str,
    *,
    max_results: int,
    search_depth: str,
    topic: str,
) -> list[TavilyResult] | None:
    payload = await _mcp_tool_call("tavily_search", {
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "topic": topic,
    })
    results = _parse_search_results(payload)
    return results if results else None


async def _mcp_extract(
    url: str,
    *,
    extract_depth: str,
    format: str,
) -> str | None:
    payload = await _mcp_tool_call("tavily_extract", {
        "urls": [url],
        "extract_depth": extract_depth,
        "format": format,
    })
    if isinstance(payload, dict):
        for item in payload.get("results", []):
            if not isinstance(item, dict):
                continue
            content = _extract_result_content(item)
            if content:
                return content
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    return None


async def tavily_search(
    query: str,
    *,
    max_results: int = 5,
    search_depth: str = "basic",
    topic: str = "general",
) -> list[TavilyResult] | None:
    """Perform a Tavily search and return structured results.

    Returns None if Tavily is not configured or the search fails,
    allowing callers to fall back to their existing logic.
    """
    if _tavily_mcp_config():
        try:
            result = await _mcp_search(
                query,
                max_results=max_results,
                search_depth=search_depth,
                topic=topic,
            )
            if result:
                return result
        except Exception as exc:
            logger.warning("Tavily MCP search failed for %r: %s", query, exc)

    from opencmo import llm
    if not llm.get_key("TAVILY_API_KEY"):
        return None

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=llm.get_key("TAVILY_API_KEY", ""))
        response = await client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            topic=topic,
        )

        return _parse_search_results(response)

    except Exception as exc:
        logger.warning("Tavily search failed for %r: %s", query, exc)
        return None


def _extract_result_content(result: dict) -> str:
    """Normalize Tavily extract payloads into plain string content."""
    content = result.get("raw_content") or result.get("content") or ""
    if not isinstance(content, str):
        content = str(content)
    return content.strip()


async def tavily_extract(
    url: str,
    *,
    extract_depth: str = "basic",
    format: str = "markdown",
) -> str | None:
    """Extract page content from a URL via Tavily.

    Returns None when Tavily is unavailable, extraction fails, or the response
    contains no usable content so callers can fall back to crawl-based fetching.
    """
    if _tavily_mcp_config():
        try:
            content = await _mcp_extract(url, extract_depth=extract_depth, format=format)
            if content:
                return content
        except Exception as exc:
            logger.warning("Tavily MCP extract failed for %r: %s", url, exc)

    from opencmo import llm
    if not llm.get_key("TAVILY_API_KEY"):
        return None

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=llm.get_key("TAVILY_API_KEY"))
        response = await client.extract(
            urls=[url],
            extract_depth=extract_depth,
            format=format,
        )
        results = response.get("results", []) if isinstance(response, dict) else []
        for item in results:
            if not isinstance(item, dict):
                continue
            content = _extract_result_content(item)
            if content:
                return content
        return None
    except Exception as exc:
        logger.warning("Tavily extract failed for %r: %s", url, exc)
        return None
