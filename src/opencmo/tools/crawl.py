import asyncio
import html
import re

from agents import function_tool
from crawl4ai import AsyncWebCrawler

from opencmo.tools.browser_pool import browser_slot
from opencmo.tools.deep_search_trace import get_cached, record_trace, set_cached


def _extract_markdown(result) -> str:
    """Safely extract markdown string from CrawlResult.

    result.markdown may be str, None, or MarkdownGenerationResult.
    """
    md = result.markdown
    if md is None:
        return ""
    if isinstance(md, str):
        return md
    # MarkdownGenerationResult — prefer .raw_markdown, fallback to str()
    if hasattr(md, "raw_markdown"):
        return md.raw_markdown or ""
    return str(md)


def _extract_html_metadata(raw_html: str) -> str:
    """Extract a small, structured fallback context from HTML metadata."""
    if not raw_html:
        return ""

    patterns = (
        ("Page title", r"<title[^>]*>(.*?)</title>"),
        ("Meta description", r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']'),
        ("Open Graph title", r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']'),
        ("Open Graph description", r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']'),
        ("Twitter title", r'<meta[^>]+name=["\']twitter:title["\'][^>]+content=["\'](.*?)["\']'),
        ("Twitter description", r'<meta[^>]+name=["\']twitter:description["\'][^>]+content=["\'](.*?)["\']'),
    )

    lines: list[str] = []
    seen_values: set[str] = set()
    for label, pattern in patterns:
        match = re.search(pattern, raw_html, re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        value = html.unescape(" ".join(match.group(1).split())).strip()
        if not value or value in seen_values:
            continue
        lines.append(f"{label}: {value}")
        seen_values.add(value)

    return "\n".join(lines)


async def fetch_url_content(
    url: str,
    *,
    max_chars: int | None = None,
    tavily_extract_depth: str = "advanced",
) -> tuple[str, str]:
    """Fetch page content with Tavily-first fallback to crawl4ai."""
    payload = {
        "url": url,
        "max_chars": max_chars,
        "tavily_extract_depth": tavily_extract_depth,
    }
    cached = get_cached("crawl_website", "fetch_url_content", payload)
    if isinstance(cached, dict) and "content" in cached and "source" in cached:
        content = str(cached["content"])
        source = str(cached["source"])
        record_trace(
            tool="crawl_website",
            action="fetch_url_content",
            payload=payload,
            provider=source,
            cache_hit=True,
            output=content,
        )
        return content, source

    from opencmo.tools.tavily_helper import tavily_extract

    content = await tavily_extract(
        url,
        extract_depth=tavily_extract_depth,
        format="markdown",
    )
    source = "tavily"

    if not content:
        async def _crawl():
            async with browser_slot():
                async with AsyncWebCrawler() as crawler:
                    return await crawler.arun(url=url)

        result = await asyncio.wait_for(_crawl(), timeout=90)
        content = _extract_markdown(result)
        source = "crawl4ai"
        if not content.strip():
            content = _extract_html_metadata(getattr(result, "html", "") or "")
            if content.strip():
                source = "html_meta"

    if max_chars is not None and len(content) > max_chars:
        content = content[:max_chars]

    set_cached(
        "crawl_website",
        "fetch_url_content",
        payload,
        {"content": content, "source": source},
    )
    record_trace(
        tool="crawl_website",
        action="fetch_url_content",
        payload=payload,
        provider=source,
        output=content,
    )
    return content, source


@function_tool
async def crawl_website(url: str) -> str:
    """Crawl a website and return its content as markdown.

    Args:
        url: The URL of the website to crawl.
    """
    try:
        content, _source = await fetch_url_content(url)
        if len(content) > 10000:
            content = content[:10000] + "\n\n... [content truncated at 10000 characters]"
        return content
    except Exception as e:
        return f"Failed to crawl {url}: {e}"
