"""Community monitoring tools — scan_community + fetch_discussion_detail."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from urllib.parse import urlparse

from agents import function_tool

from opencmo.tools.browser_pool import browser_slot
from opencmo.tools.community_providers import (
    PROVIDER_REGISTRY,
    DisabledProvider,
    DiscussionHit,
    ProviderError,
    QuerySpec,
    ScanResult,
    SearchQueryPlan,
    SuggestedQuery,
    _truncate,
)
from opencmo.tools.community_query_planner import build_query_plan
from opencmo.tools.community_scoring import rescore_hits

# ---------------------------------------------------------------------------
# Stub query templates (brand / category / current_year placeholders)
# ---------------------------------------------------------------------------

_STUB_QUERIES: dict[str, list[dict]] = {
    "linkedin": [
        {"query": '"{brand}" site:linkedin.com', "reason": "stub — no public search API"},
    ],
    "producthunt": [
        {"query": '"{brand}" site:producthunt.com', "reason": "stub — requires API token"},
    ],
    "blog": [
        {"query": '"{brand}" review OR alternative OR vs', "reason": "stub — no unified API"},
        {"query": "best {category} tools {current_year}", "reason": "stub — category discovery"},
    ],
}

_EXTERNAL_SEARCH_DOMAINS: dict[str, list[str]] = {
    "reddit": ["reddit.com"],
    "hackernews": ["news.ycombinator.com"],
    "devto": ["dev.to"],
    "youtube": ["youtube.com", "youtu.be"],
    "twitter": ["x.com", "twitter.com"],
    "bluesky": ["bsky.app"],
    "linkedin": ["linkedin.com"],
    "producthunt": ["producthunt.com"],
    "blog": [],
    "v2ex": ["v2ex.com"],
    "weibo": ["weibo.com", "m.weibo.cn"],
    "bilibili": ["bilibili.com"],
    "xueqiu": ["xueqiu.com"],
    "xiaohongshu": ["xiaohongshu.com"],
    "wechat": ["mp.weixin.qq.com"],
    "douyin": ["douyin.com"],
}

_INTENT_PRIORITY = {
    "direct_mention": 0,
    "competitor_mention": 1,
    "opportunity": 2,
}

_SOURCE_KIND_PRIORITY = {
    "post": 0,
    "comment": 1,
    "external_search": 2,
}


def _render_stub_queries(
    provider_name: str, brand_name: str, category: str,
) -> list[SuggestedQuery]:
    templates = _STUB_QUERIES.get(provider_name, [])
    year = str(datetime.now().year)
    out: list[SuggestedQuery] = []
    for t in templates:
        q = t["query"].replace("{brand}", brand_name).replace("{category}", category).replace("{current_year}", year)
        out.append(SuggestedQuery(
            platform=provider_name,
            provider=provider_name,
            query=q,
            reason=t["reason"],
        ))
    return out


def _has_tavily() -> bool:
    from opencmo.tools.tavily_helper import tavily_available

    return tavily_available()


def _format_site_query(query: str, domains: list[str]) -> str:
    if not domains:
        return query
    domain_part = " OR ".join(f"site:{domain}" for domain in domains)
    return f"{query} {domain_part}"


def _pick_external_specs(provider_name: str, plan: SearchQueryPlan) -> list[QuerySpec]:
    specs = plan.provider_queries.get(provider_name, [])
    if not specs:
        return []
    direct = [spec for spec in specs if spec.intent_type == "direct_mention"]
    opportunity = [spec for spec in specs if spec.intent_type != "direct_mention"]
    return direct[:2] + opportunity[:2]


async def _crawl4ai_site_search(
    query: str, domains: list[str], max_results: int = 5,
) -> list[dict]:
    """Google site-search via crawl4ai, returns [{url, title, content}, ...]."""
    try:
        import re as _re

        from crawl4ai import AsyncWebCrawler
    except ImportError:
        return []

    site_filter = " OR ".join(f"site:{d}" for d in domains) if domains else ""
    full_query = f"{query} {site_filter}".strip().replace(" ", "+")
    search_url = f"https://www.google.com/search?q={full_query}&num={max_results}"

    try:
        async with browser_slot():
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=search_url)
        md = result.markdown if hasattr(result, "markdown") else ""
        if not md:
            return []
        # Parse markdown links from Google results
        entries: list[dict] = []
        for m in _re.finditer(r'\[([^\]]+)\]\((https?://[^\)]+)\)', md):
            title, url = m.group(1), m.group(2)
            if "google.com" in url:
                continue
            if domains and not any(d in url for d in domains):
                continue
            entries.append({"url": url, "title": title, "content": ""})
            if len(entries) >= max_results:
                break
        return entries
    except Exception:
        return []


async def _search_external_platform(
    provider_name: str,
    specs: list[QuerySpec],
) -> tuple[list[DiscussionHit], list[str]]:
    if not specs:
        return [], []

    domains = _EXTERNAL_SEARCH_DOMAINS.get(provider_name, [])
    hits: list[DiscussionHit] = []
    errors: list[str] = []
    use_tavily = _has_tavily()

    for spec in specs:
        results: list[dict] = []

        # Try Tavily first
        if use_tavily:
            try:
                from opencmo.tools.tavily_helper import tavily_search

                tavily_results = await tavily_search(
                    _format_site_query(spec.query, domains),
                    max_results=5,
                    search_depth="basic",
                )
                results = [
                    {"url": item.url, "title": item.title, "content": item.snippet}
                    for item in (tavily_results or [])
                ]
            except Exception as exc:
                errors.append(f"external {provider_name} {spec.source}: {exc}")

        # Fallback to crawl4ai Google scrape if Tavily unavailable or returned nothing
        if not results:
            results = await _crawl4ai_site_search(spec.query, domains)

        for result in results:
            url = result.get("url", "")
            title = result.get("title", "")
            content = result.get("content", "")
            if not url or (not title and not content):
                continue
            match_reason = spec.reason or f"Matched the external fallback query '{spec.query}'."
            hits.append(DiscussionHit(
                platform=provider_name,
                title=title or content.split("\n")[0][:120],
                url=url,
                engagement_score=None,
                raw_score=None,
                comments_count=None,
                age_days=None,
                author=urlparse(url).hostname or "",
                detail_id=url,
                extra_param_1="",
                extra_param_2="",
                preview=content[:300] if content else "",
                source=f"external_search:{spec.source}",
                intent_type=spec.intent_type,
                match_reason=match_reason,
                matched_query=spec.query,
                matched_terms=list(spec.matched_terms),
                confidence=max(0.2, min(0.92, spec.confidence - 0.1)),
                source_kind="external_search",
            ))

    deduped: dict[str, DiscussionHit] = {}
    for hit in hits:
        existing = deduped.get(hit.detail_id)
        if existing is None or hit.confidence > existing.confidence:
            deduped[hit.detail_id] = hit
    return list(deduped.values()), errors


def _should_use_external_fallback(provider_name: str, hits: list[DiscussionHit]) -> bool:
    if provider_name in {"linkedin", "producthunt", "blog", "xiaohongshu", "wechat", "douyin"}:
        return True
    if not hits:
        return True
    if provider_name in {"reddit", "hackernews", "devto", "v2ex"}:
        return not any(hit.intent_type == "direct_mention" for hit in hits)
    return False


def _sort_hits(hits: list[DiscussionHit]) -> None:
    hits.sort(
        key=lambda hit: (
            _INTENT_PRIORITY.get(hit.intent_type, 9),
            -(hit.confidence or 0.0),
            -(hit.engagement_score or 0),
            _SOURCE_KIND_PRIORITY.get(hit.source_kind, 9),
            -(hit.raw_score or 0),
            hit.platform,
            hit.detail_id,
        )
    )


# ---------------------------------------------------------------------------
# Output trimming
# ---------------------------------------------------------------------------

def _get_output_budget() -> int:
    from opencmo.scrape_config import get_scrape_profile
    return get_scrape_profile().output_budget_chars


_MAX_PROVIDER_ERRORS = 5
_MAX_ERRORS_PER_PROVIDER = 2
_MIN_TRIMMED_HITS = 3


def _cap_provider_errors(provider_errors: list[ProviderError]) -> list[ProviderError]:
    capped: list[ProviderError] = []
    for provider_error in provider_errors[:_MAX_PROVIDER_ERRORS]:
        capped.append(ProviderError(
            provider=provider_error.provider,
            errors=[_truncate(error, 200) for error in provider_error.errors[:_MAX_ERRORS_PER_PROVIDER]],
        ))
    return capped


def _trim_scan_result(sr: ScanResult) -> ScanResult:
    """Trim ScanResult to fit within output budget. Mutates and returns sr."""
    budget = _get_output_budget()
    serialized = json.dumps(asdict(sr), ensure_ascii=False)
    if len(serialized) <= budget:
        return sr

    # Step 1: cap provider errors before sacrificing discussion hits.
    sr.provider_errors = _cap_provider_errors(sr.provider_errors)
    serialized = json.dumps(asdict(sr), ensure_ascii=False)
    if len(serialized) <= budget:
        return sr

    # Step 2: shorten all previews to 100 chars.
    for h in sr.hits:
        h.preview = _truncate(h.preview, 100)
    serialized = json.dumps(asdict(sr), ensure_ascii=False)
    if len(serialized) <= budget:
        return sr

    # Step 3: remove lowest-engagement hits, but preserve a minimal result set.
    sr.hits.sort(key=lambda h: ((h.engagement_score or 0), (h.raw_score or 0)), reverse=True)
    while len(serialized) > budget and len(sr.hits) > _MIN_TRIMMED_HITS:
        sr.hits.pop()
        serialized = json.dumps(asdict(sr), ensure_ascii=False)

    return sr


# ---------------------------------------------------------------------------
# scan_community
# ---------------------------------------------------------------------------


async def _scan_community_impl(
    brand_name: str,
    category: str,
    *,
    tracked_keywords: list[str] | None = None,
    competitor_names: list[str] | None = None,
    competitor_keywords: list[str] | None = None,
    canonical_url: str | None = None,
    locale: str | None = None,
    query_plan: SearchQueryPlan | None = None,
) -> str:
    """Core scan logic — called by the function_tool wrapper and tests."""
    result = ScanResult()
    plan = query_plan or build_query_plan(
        brand_name=brand_name,
        category=category,
        tracked_keywords=tracked_keywords,
        competitor_names=competitor_names,
        competitor_keywords=competitor_keywords,
        canonical_url=canonical_url,
        locale=locale,
    )

    for provider in PROVIDER_REGISTRY:
        if not provider.is_enabled:
            # Disabled / stub → generate suggested queries + record
            result.disabled_providers.append(DisabledProvider(
                name=provider.name,
                reason=f"stub — {provider.status}" if provider.status == "stub" else "disabled",
            ))
            result.suggested_queries.extend(
                _render_stub_queries(provider.name, brand_name, category),
            )
            if _should_use_external_fallback(provider.name, []):
                fallback_hits, fallback_errors = await _search_external_platform(
                    provider.name,
                    _pick_external_specs(provider.name, plan),
                )
                result.hits.extend(fallback_hits)
                if fallback_errors:
                    result.provider_errors.append(ProviderError(
                        provider=provider.name,
                        errors=fallback_errors,
                    ))
            continue

        # Enabled provider → call search
        try:
            pr = await provider.search(brand_name, category, query_plan=plan)
        except Exception as exc:
            result.provider_errors.append(ProviderError(
                provider=provider.name,
                errors=[str(exc)],
            ))
            continue

        # Merge all hits (no truncation — trimming happens later at output)
        result.hits.extend(pr.hits)

        # Collect errors
        if pr.errors:
            result.provider_errors.append(ProviderError(
                provider=provider.name,
                errors=pr.errors,
            ))

        # Collect suggested queries
        result.suggested_queries.extend(pr.suggested_queries)

        if _should_use_external_fallback(provider.name, pr.hits):
            fallback_hits, fallback_errors = await _search_external_platform(
                provider.name,
                _pick_external_specs(provider.name, plan),
            )
            result.hits.extend(fallback_hits)
            if fallback_errors:
                result.provider_errors.append(ProviderError(
                    provider=provider.name,
                    errors=fallback_errors,
                ))

    # Deduplicate suggested_queries by (platform, query)
    seen_sq: set[tuple[str, str]] = set()
    unique_sq: list[SuggestedQuery] = []
    for sq in result.suggested_queries:
        key = (sq.platform, sq.query)
        if key not in seen_sq:
            seen_sq.add(key)
            unique_sq.append(sq)
    result.suggested_queries = unique_sq

    # Deduplicate hits globally after native + external merging.
    deduped_hits: dict[tuple[str, str], DiscussionHit] = {}
    for hit in result.hits:
        key = (hit.platform, hit.detail_id)
        existing = deduped_hits.get(key)
        if existing is None or (hit.confidence, hit.raw_score or 0) > (existing.confidence, existing.raw_score or 0):
            deduped_hits[key] = hit
    result.hits = list(deduped_hits.values())

    # Rescore with multi-signal composite scoring
    query = f"{brand_name} {category}"
    from opencmo.scrape_config import get_scrape_profile
    profile = get_scrape_profile()
    halflife = getattr(profile, "scoring_recency_halflife_days", 23.0)
    convergence_threshold = getattr(profile, "scoring_convergence_threshold", 0.5)
    rescore_hits(result.hits, query, halflife_days=halflife, convergence_threshold=convergence_threshold)

    _sort_hits(result.hits)

    # Trim to fit output budget
    result = _trim_scan_result(result)
    envelope = asdict(result)
    envelope["query_plan"] = {
        "provider_queries": {
            provider: [asdict(spec) for spec in specs]
            for provider, specs in plan.provider_queries.items()
        },
        "platform_targeting": plan.platform_targeting,
    }
    envelope["coverage_summary"] = {
        "direct_mentions": sum(1 for hit in result.hits if hit.intent_type == "direct_mention"),
        "opportunity_threads": sum(1 for hit in result.hits if hit.intent_type == "opportunity"),
        "external_fallback_hits": sum(1 for hit in result.hits if hit.source_kind == "external_search"),
    }

    return json.dumps(envelope, ensure_ascii=False)


@function_tool
async def scan_community(brand_name: str, category: str) -> str:
    """Scan Reddit, Hacker News, Dev.to, YouTube, Bluesky, Twitter/X and other platforms for brand/category discussions.

    Returns a structured JSON envelope with hits, disabled platforms, errors, and
    suggested web-search queries for platforms without free API access.

    Args:
        brand_name: The brand or product name to search for.
        category: The product category for broader search context.
    """
    return await _scan_community_impl(brand_name, category)


# ---------------------------------------------------------------------------
# fetch_discussion_detail
# ---------------------------------------------------------------------------

# Build provider lookup once
_PROVIDER_MAP = {p.name: p for p in PROVIDER_REGISTRY}


@function_tool
async def fetch_discussion_detail(
    platform: str,
    detail_id: str,
    extra_param_1: str = "",
    extra_param_2: str = "",
) -> str:
    """Fetch full post content and top comments for a discussion.

    Use the platform, detail_id, extra_param_1 and extra_param_2 values
    directly from scan_community results.

    Args:
        platform: The platform name (e.g. "reddit", "hackernews", "devto").
        detail_id: The post/story/article ID from scan_community results.
        extra_param_1: Platform-specific parameter (e.g. subreddit name for Reddit). Empty if not needed.
        extra_param_2: Reserved for future platforms. Currently always empty.
    """
    provider = _PROVIDER_MAP.get(platform)
    if provider is None:
        return json.dumps({"ok": False, "error": "platform_not_found"})

    if "detail" not in provider.capabilities:
        return json.dumps({"ok": False, "error": "detail_not_supported"})

    # Build a minimal DiscussionHit for the provider
    hit = DiscussionHit(
        platform=platform,
        title="",
        url="",
        engagement_score=0,
        raw_score=0,
        comments_count=0,
        age_days=0,
        author="",
        detail_id=detail_id,
        extra_param_1=extra_param_1,
        extra_param_2=extra_param_2,
        preview="",
        source="",
    )

    try:
        detail = await provider.fetch_detail(hit)
    except Exception:
        return json.dumps({"ok": False, "error": "fetch_failed"})

    if detail is None:
        return json.dumps({"ok": False, "error": "not_found"})

    # Enforce limits
    detail.full_content = _truncate(detail.full_content, 2000)
    detail.comments = detail.comments[:10]
    for c in detail.comments:
        c["text"] = _truncate(c.get("text", ""), 500)

    return json.dumps({"ok": True, "detail": asdict(detail)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# analyze_community_patterns
# ---------------------------------------------------------------------------


@function_tool
async def analyze_community_patterns(brand_name: str, category: str) -> str:
    """Analyze engagement patterns across tracked discussions over time.

    Returns trending topics, engagement growth leaders, posting patterns,
    and platform distribution based on historical discussion snapshots.

    Args:
        brand_name: The brand or product name.
        category: The product category for context.
    """
    try:
        from opencmo import storage

        projects = await storage.list_projects()
        project = next((p for p in projects if p["brand_name"] == brand_name), None)
        if not project:
            return f"No tracked data for '{brand_name}'. Run a community scan first to start tracking."

        discussions = await storage.get_tracked_discussions(project["id"])
        if not discussions:
            return f"No tracked discussions for '{brand_name}'. Run a community scan first."

        # Platform distribution
        platform_counts: dict[str, int] = {}
        for d in discussions:
            platform_counts[d["platform"]] = platform_counts.get(d["platform"], 0) + 1

        lines = [
            f"# Community Pattern Analysis: {brand_name}",
            f"**Category**: {category}\n",
            "## Overview",
            f"- Total tracked discussions: {len(discussions)}",
            f"- Platforms: {', '.join(f'{k} ({v})' for k, v in sorted(platform_counts.items()))}",
            "",
            "## Top Discussions by Engagement\n",
            "| Platform | Title | Score | Comments | Last Checked |",
            "|----------|-------|-------|----------|--------------|",
        ]

        # Top 10 by engagement
        sorted_disc = sorted(
            discussions,
            key=lambda d: (d.get("engagement_score") or 0),
            reverse=True,
        )[:10]

        for d in sorted_disc:
            title = d["title"][:60] + ("..." if len(d["title"]) > 60 else "")
            score = d.get("raw_score") or "—"
            comments = d.get("comments_count") or "—"
            lines.append(
                f"| {d['platform']} | [{title}]({d['url']}) | {score} | {comments} | {d['last_checked_at'][:10]} |"
            )

        # Engagement velocity — discussions with growing scores
        lines.append("\n## Engagement Velocity\n")
        growing = []
        for d in discussions:
            snapshots = await storage.get_discussion_snapshots(d["id"])
            if len(snapshots) >= 2:
                first = snapshots[0]["engagement_score"]
                last = snapshots[-1]["engagement_score"]
                delta = last - first
                if delta > 0:
                    growing.append((d, delta, len(snapshots)))

        if growing:
            growing.sort(key=lambda x: x[1], reverse=True)
            for d, delta, n_snaps in growing[:5]:
                lines.append(f"- **{d['title'][:50]}** ({d['platform']}): +{delta} engagement over {n_snaps} snapshots")
        else:
            lines.append("*Not enough historical data to detect trends. Run scans over multiple days.*")

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to analyze patterns: {e}"
