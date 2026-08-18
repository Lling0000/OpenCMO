"""Web search tool — Tavily-first, with OpenAI WebSearchTool or crawl4ai fallback."""

import logging

from agents import function_tool

from opencmo.tools.browser_pool import browser_slot
from opencmo.tools.deep_search_trace import get_cached, record_trace, set_cached

logger = logging.getLogger(__name__)


@function_tool
async def web_search(query: str) -> str:
    """Search the web for real-time information.

    Args:
        query: The search query string.
    """
    payload = {"query": query, "max_results": 5}
    cached = get_cached("web_search", "search", payload)
    if cached is not None:
        record_trace(
            tool="web_search",
            action="search",
            payload=payload,
            provider="cache",
            cache_hit=True,
            output=cached,
        )
        return str(cached)

    try:
        from opencmo.tools.tavily_helper import tavily_search

        results = await tavily_search(query, max_results=5, search_depth="basic")
        if results:
            parts = []
            for result in results:
                parts.append(f"### {result.title}\n{result.url}\n\n{result.snippet}")
            output = "\n\n---\n\n".join(parts)
            set_cached("web_search", "search", payload, output)
            record_trace(
                tool="web_search",
                action="search",
                payload=payload,
                provider="tavily",
                output=output,
                metadata={"result_count": len(results)},
            )
            return output
    except Exception as exc:
        record_trace(
            tool="web_search",
            action="search",
            payload=payload,
            provider="tavily",
            error=str(exc),
        )
        logger.debug("Tavily search failed, trying fallback: %s", exc)

    # 2. Fallback: OpenAI built-in web search (native provider only)
    from opencmo.config import is_custom_provider

    if not is_custom_provider():
        try:
            from agents import WebSearchTool

            _openai_ws = WebSearchTool()
            # WebSearchTool.on_invoke_tool expects a RunContextWrapper + raw JSON string
            import json

            result = await _openai_ws.on_invoke_tool(
                None, json.dumps({"query": query}),
            )
            if result:
                set_cached("web_search", "search", payload, result)
                record_trace(
                    tool="web_search",
                    action="search",
                    payload=payload,
                    provider="openai_web_search",
                    output=result,
                )
                return result
        except Exception as exc:
            record_trace(
                tool="web_search",
                action="search",
                payload=payload,
                provider="openai_web_search",
                error=str(exc),
            )
            logger.debug("OpenAI WebSearchTool fallback failed: %s", exc)

    # 3. Final fallback: crawl4ai Google scrape
    try:
        from crawl4ai import AsyncWebCrawler

        from opencmo.tools.crawl import _extract_markdown

        url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num=5"
        async with browser_slot():
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
        content = _extract_markdown(result)
        output = content[:4000] if content else "No search results found."
        set_cached("web_search", "search", payload, output)
        record_trace(
            tool="web_search",
            action="search",
            payload=payload,
            provider="crawl4ai_google",
            output=output,
        )
        return output
    except Exception as e:
        output = f"Web search failed: {e}. Try using other available tools instead."
        record_trace(
            tool="web_search",
            action="search",
            payload=payload,
            provider="crawl4ai_google",
            output=output,
            error=str(e),
        )
        return output
