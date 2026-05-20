"""SERP ranking tracker — pluggable provider architecture."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from agents import function_tool

if TYPE_CHECKING:
    from tavily import AsyncTavilyClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SerpResult:
    position: int | None
    url_found: str | None
    total_results: int
    provider: str
    error: str | None


def _domain_matches(domain: str, target: str) -> bool:
    """Match a SERP result's domain against the project's target domain.

    Strict equality plus subdomain support, so ``ai.com`` no longer matches
    ``openai.com`` (the old ``target in domain`` substring check).
    """
    if not domain or not target:
        return False
    return domain == target or domain.endswith("." + target)


# ---------------------------------------------------------------------------
# Provider ABC
# ---------------------------------------------------------------------------


class SerpProvider(ABC):
    name: str

    @property
    def is_enabled(self) -> bool:
        return True

    @abstractmethod
    async def check_ranking(
        self, keyword: str, target_domain: str, num_results: int = 0
    ) -> SerpResult: ...


# ---------------------------------------------------------------------------
# CrawlSerpProvider — crawl4ai Google search (default)
# ---------------------------------------------------------------------------


class CrawlSerpProvider(SerpProvider):
    name = "crawl"

    async def check_ranking(
        self, keyword: str, target_domain: str, num_results: int = 0
    ) -> SerpResult:
        if num_results <= 0:
            from opencmo.scrape_config import get_scrape_profile
            num_results = get_scrape_profile().serp_num_results
        try:
            from urllib.parse import quote_plus

            import httpx

            search_url = f"https://www.google.com/search?q={quote_plus(keyword)}&num={num_results}"
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                follow_redirects=True,
                timeout=15,
            ) as client:
                resp = await client.get(search_url)
                resp.raise_for_status()
                html = resp.text

            # Simple link extraction from Google results
            import re

            links: list[str] = []
            # Match href="/url?q=..." pattern used by Google
            for m in re.finditer(r'href="/url\?q=(https?://[^&"]+)', html):
                url = m.group(1)
                if "google.com" not in url:
                    links.append(url)
            # Also match direct href="https://..." in result blocks
            for m in re.finditer(r'<a href="(https?://[^"]+)"[^>]*data-', html):
                url = m.group(1)
                if "google.com" not in url and url not in links:
                    links.append(url)

            target = target_domain.lower().removeprefix("www.")
            for i, link in enumerate(links[:num_results]):
                domain = urlparse(link).netloc.lower().removeprefix("www.")
                if _domain_matches(domain, target):
                    return SerpResult(
                        position=i + 1,
                        url_found=link,
                        total_results=len(links),
                        provider=self.name,
                        error=None,
                    )

            return SerpResult(
                position=None,
                url_found=None,
                total_results=len(links),
                provider=self.name,
                error=None,
            )

        except Exception as exc:
            return SerpResult(
                position=None,
                url_found=None,
                total_results=0,
                provider=self.name,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# DataForSeoProvider — stub (status="stub")
# ---------------------------------------------------------------------------


class DataForSeoProvider(SerpProvider):
    name = "dataforseo"
    status = "stub"
    status_reason = "DataForSEO SERP provider is not implemented yet"

    @property
    def is_enabled(self) -> bool:
        # Keep the stub visible in the registry without allowing credentials or
        # provider ordering to select a non-functional provider for live checks.
        return False

    async def check_ranking(
        self, keyword: str, target_domain: str, num_results: int = 20
    ) -> SerpResult:
        return SerpResult(
            position=None,
            url_found=None,
            total_results=0,
            provider=self.name,
            error=self.status_reason,
        )


# ---------------------------------------------------------------------------
# TavilySerpProvider — Tavily search API
# ---------------------------------------------------------------------------


class TavilySerpProvider(SerpProvider):
    name = "tavily"

    def __init__(self) -> None:
        self._client: AsyncTavilyClient | None = None
        self._client_api_key: str | None = None

    def _get_client(self, api_key: str) -> AsyncTavilyClient:
        if self._client is None or self._client_api_key != api_key:
            from tavily import AsyncTavilyClient as _AsyncTavilyClient

            self._client = _AsyncTavilyClient(api_key=api_key)
            self._client_api_key = api_key
        return self._client

    @property
    def is_enabled(self) -> bool:
        from opencmo.tools.tavily_helper import tavily_available

        return tavily_available()

    async def check_ranking(
        self, keyword: str, target_domain: str, num_results: int = 20
    ) -> SerpResult:
        try:
            from opencmo.tools.tavily_helper import tavily_search

            results = await tavily_search(keyword, max_results=num_results)
            if results is None:
                return SerpResult(
                    position=None,
                    url_found=None,
                    total_results=0,
                    provider=self.name,
                    error="Tavily unavailable",
                )

            target = target_domain.lower().removeprefix("www.")
            for i, item in enumerate(results):
                url = item.url
                domain = urlparse(url).netloc.lower().removeprefix("www.")
                if _domain_matches(domain, target):
                    return SerpResult(
                        position=i + 1,
                        url_found=url,
                        total_results=len(results),
                        provider=self.name,
                        error=None,
                    )

            return SerpResult(
                position=None,
                url_found=None,
                total_results=len(results),
                provider=self.name,
                error=None,
            )

        except Exception as exc:
            return SerpResult(
                position=None,
                url_found=None,
                total_results=0,
                provider=self.name,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Registry & provider resolution
# ---------------------------------------------------------------------------

SERP_PROVIDER_REGISTRY: list[SerpProvider] = [
    TavilySerpProvider(),
    CrawlSerpProvider(),
    DataForSeoProvider(),
]


def _get_active_provider() -> SerpProvider:
    """Return the first enabled provider from registry."""
    for p in SERP_PROVIDER_REGISTRY:
        if p.is_enabled:
            return p
    return CrawlSerpProvider()


def _get_crawl_provider() -> SerpProvider:
    """Return the configured crawl provider, or a fresh fallback instance."""
    for provider in SERP_PROVIDER_REGISTRY:
        if provider.name == "crawl":
            return provider
    return CrawlSerpProvider()


# ---------------------------------------------------------------------------
# Core implementation
# ---------------------------------------------------------------------------


async def _check_ranking(keyword: str, target_domain: str) -> SerpResult:
    """Run a single SERP check with the active provider."""
    from opencmo.scrape_config import get_scrape_profile
    profile = get_scrape_profile()
    provider = _get_active_provider()
    result = await provider.check_ranking(keyword, target_domain, num_results=profile.serp_num_results)
    if not result.error or provider.name == "crawl":
        return result

    fallback = _get_crawl_provider()
    fallback_result = await fallback.check_ranking(keyword, target_domain, num_results=profile.serp_num_results)
    if not fallback_result.error:
        logger.warning(
            "SERP provider %s failed for %r; used crawl fallback instead: %s",
            provider.name,
            keyword,
            result.error,
        )
        return fallback_result

    return SerpResult(
        position=None,
        url_found=None,
        total_results=0,
        provider=fallback_result.provider,
        error=f"{provider.name} failed: {result.error}; crawl fallback failed: {fallback_result.error}",
    )


async def track_project_keywords(project_id: int) -> str:
    """Track all keywords for a project. Called by scheduler."""
    from opencmo import storage

    project = await storage.get_project(project_id)
    if not project:
        return f"Project {project_id} not found"

    domain = urlparse(project["url"]).netloc.removeprefix("www.")
    keywords = await storage.list_tracked_keywords(project_id)

    if not keywords:
        return f"No tracked keywords for project {project_id}"

    results = []
    for kw in keywords:
        result = await _check_ranking(kw["keyword"], domain)
        await storage.save_serp_snapshot(
            project_id,
            kw["keyword"],
            result.position,
            result.url_found,
            result.provider,
            result.error,
        )
        if result.error:
            results.append(f"  {kw['keyword']}: error — {result.error}")
        elif result.position:
            results.append(f"  {kw['keyword']}: #{result.position} ({result.url_found})")
        else:
            results.append(f"  {kw['keyword']}: not ranked in top 20")

    return f"SERP tracking for {project['brand_name']}:\n" + "\n".join(results)


async def _get_serp_trends_impl(project_id: int) -> str:
    """Return markdown table of SERP history for a project."""
    from opencmo import storage

    project = await storage.get_project(project_id)
    if not project:
        return f"Project {project_id} not found"

    keywords = await storage.list_tracked_keywords(project_id)
    if not keywords:
        return f"No tracked keywords for project {project_id}"

    lines = [f"## SERP Trends for {project['brand_name']}\n"]
    lines.append("| Keyword | Latest Position | Previous | Trend | Last Checked |")
    lines.append("|---------|----------------|----------|-------|-------------|")

    for kw in keywords:
        history = await storage.get_serp_history(project_id, kw["keyword"], limit=5)
        if not history:
            lines.append(f"| {kw['keyword']} | no data | — | — | — |")
            continue

        latest = history[0]
        if latest["error"]:
            pos_str = "unavailable"
            trend = "—"
        elif latest["position"] is None:
            pos_str = "not ranked"
            trend = "—"
        else:
            pos_str = f"#{latest['position']}"
            # Compare with previous
            if len(history) > 1 and history[1]["position"] and not history[1]["error"]:
                delta = history[1]["position"] - latest["position"]
                if delta > 0:
                    trend = f"+{delta}"
                elif delta < 0:
                    trend = str(delta)
                else:
                    trend = "="
            else:
                trend = "new"

        prev_str = "—"
        if len(history) > 1:
            prev = history[1]
            if prev["error"]:
                prev_str = "err"
            elif prev["position"] is None:
                prev_str = "n/r"
            else:
                prev_str = f"#{prev['position']}"

        lines.append(
            f"| {kw['keyword']} | {pos_str} | {prev_str} | {trend} | {latest['checked_at'][:16]} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent-facing tools
# ---------------------------------------------------------------------------


@function_tool
async def check_keyword_ranking(keyword: str, url: str) -> str:
    """Check where a URL's domain ranks on Google for a keyword. One-time query, not persisted.

    Args:
        keyword: The search keyword to check.
        url: The website URL (domain is derived from this).
    """
    domain = urlparse(url).netloc.removeprefix("www.")
    result = await _check_ranking(keyword, domain)

    if result.error:
        return f"SERP check failed: {result.error}"
    elif result.position:
        return (
            f"**{domain}** ranks **#{result.position}** for '{keyword}'\n"
            f"URL: {result.url_found}\n"
            f"(checked {result.total_results} results via {result.provider})"
        )
    else:
        return (
            f"**{domain}** is **not ranked** in top 20 for '{keyword}'\n"
            f"(checked {result.total_results} results via {result.provider})"
        )


@function_tool
async def get_serp_trends(project_id: int) -> str:
    """Get SERP ranking trends for a project's tracked keywords.

    Args:
        project_id: The project ID to get trends for.
    """
    return await _get_serp_trends_impl(project_id)
