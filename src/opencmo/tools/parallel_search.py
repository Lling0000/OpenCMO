"""Anonymous Parallel Search MCP through the Agents SDK's HTTP transport."""

from __future__ import annotations

import asyncio

from agents.mcp import MCPServerStreamableHttp

MCP_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "OpenCMO/0.1.0 (https://github.com/Lling0000/OpenCMO)"
_TIMEOUT_SECONDS = 30


async def _search(query: str) -> str:
    async with MCPServerStreamableHttp(
        name="Parallel Search",
        params={
            "url": MCP_URL,
            "headers": {"User-Agent": USER_AGENT},
            "timeout": _TIMEOUT_SECONDS,
            "sse_read_timeout": _TIMEOUT_SECONDS,
        },
        client_session_timeout_seconds=_TIMEOUT_SECONDS,
    ) as server:
        await server.list_tools()
        result = await server.call_tool(
            "web_search", {"objective": query, "search_queries": [query]},
        )
        # MCP SDK v2 uses snake_case; v1 exposes the JSON field name.
        if getattr(result, "is_error", False) or getattr(result, "isError", False):
            raise RuntimeError("Parallel Search MCP returned an error")
        # Preserve source URLs and excerpts in the model-visible tool result.
        text = "\n\n".join(item.text for item in result.content if item.type == "text")
        return text if text.strip() else "No search results found."


async def parallel_search(query: str) -> str:
    """Return search excerpts, bounding discovery and execution together."""
    # Older Agents/MCP transports cancel their owning task on HTTP failures.
    # Keep that internal cancellation distinct from a user canceling this tool.
    task = asyncio.create_task(_search(query))
    try:
        done, _ = await asyncio.wait({task}, timeout=_TIMEOUT_SECONDS)
        if not done:
            raise asyncio.TimeoutError("Parallel search timed out")
        if task.cancelled():
            raise RuntimeError("Parallel search transport was interrupted")
        return task.result()
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
