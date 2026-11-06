"""GEO provider architecture for multi-platform AI visibility scanning."""

from __future__ import annotations

import asyncio
import contextvars
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import quote_plus

from crawl4ai import AsyncWebCrawler

from opencmo.tools.browser_pool import browser_slot
from opencmo.tools.crawl import _extract_markdown

# ---------------------------------------------------------------------------
# Conditional imports for API-based providers
# ---------------------------------------------------------------------------

try:
    import anthropic

    _HAS_ANTHROPIC = True
except ImportError:
    anthropic = None
    _HAS_ANTHROPIC = False

try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        import google.generativeai as genai

    _HAS_GENAI = True
except ImportError:
    genai = None
    _HAS_GENAI = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class GeoProviderResult:
    platform: str
    mentioned: bool
    mention_count: int
    position_pct: float | None  # first mention position %, None if not mentioned
    content_snippet: str  # <=snippet_chars
    error: str | None
    query: str = ""  # which query produced this result
    # "ok" | "empty" | "blocked" | "error" — distinguishes "no mention" from "couldn't observe".
    # Crawl providers return "blocked"/"empty" when the response is a captcha/JS shell,
    # so they shouldn't deflate the visibility denominator.
    source_status: str = "ok"


@dataclass
class GeoAggregatedResult:
    """Aggregated result from multiple queries on one provider."""
    platform: str
    mentioned: bool             # True if mentioned in ANY query
    total_mention_count: int    # sum of all mentions across queries
    best_position_pct: float | None  # best (lowest) position %
    per_query_results: list[GeoProviderResult]
    error: str | None
    source_status: str = "ok"   # worst-case across per_query_results (ok > empty > blocked > error)


_BLOCKED_MARKERS = (
    "captcha", "verify you are human", "cloudflare",
    "access denied", "rate limit", "too many requests",
    "are you a robot", "403 forbidden",
)


def _classify_crawl_content(content: str) -> str:
    """Return 'ok' | 'empty' | 'blocked' for a crawl provider's response body.

    Markers are checked first so a short anti-bot page (e.g. a 403 captcha
    stub under 200 chars) gets ``blocked`` instead of being absorbed into
    ``empty`` and looking like a transient miss.
    """
    if not content:
        return "empty"
    lowered = content.lower()
    if any(marker in lowered for marker in _BLOCKED_MARKERS):
        return "blocked"
    if len(content.strip()) < 200:
        return "empty"
    return "ok"


def _classify_api_content(content: str) -> str:
    """Return 'ok' | 'empty' | 'blocked' for an API provider response."""
    if not content or not content.strip():
        return "empty"
    lowered = content.lower()
    if any(marker in lowered for marker in _BLOCKED_MARKERS):
        return "blocked"
    return "ok"


_STATUS_RANK = {"ok": 0, "empty": 1, "blocked": 2, "error": 3}


def _aggregate_source_status(statuses: list[str]) -> str:
    """Roll per-query statuses up to the platform.

    A platform counts as ``ok`` if *any* of its queries succeeded — one captcha
    in the bunch must not poison the whole platform's visibility scoring.
    Otherwise pick the worst observed status to surface the dominant failure.
    """
    if not statuses:
        return "error"
    if any(s == "ok" for s in statuses):
        return "ok"
    return max(statuses, key=lambda s: _STATUS_RANK.get(s, 3))


# Backward-compat alias — older callers (and tests) referenced the old name.
_worst_source_status = _aggregate_source_status


# ---------------------------------------------------------------------------
# Query templates
# ---------------------------------------------------------------------------

_QUERY_TEMPLATES_EN = [
    "What are the best {category} tools and platforms?",
    "Can you recommend some {category} alternatives?",
    "{brand_name} vs competitors in {category}",
    "{brand_name} review",
    "{category} comparison 2026",
]

_QUERY_TEMPLATES_CN = [
    "有哪些好用的{category}工具和平台？",
    "可以推荐几款{category}的替代方案吗？",
    "{brand_name}和{category}领域的竞争对手相比怎么样？",
    "{brand_name} 评测",
    "2026 年 {category} 对比",
]

_QUERY_TEMPLATES = _QUERY_TEMPLATES_EN  # backward-compat alias

_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")


def _looks_cjk(*texts: str) -> bool:
    """Return True if any of the given strings contains CJK characters."""
    return any(_CJK_RE.search(t or "") for t in texts)


def _get_query_templates(brand_name: str, category: str) -> list[str]:
    """Generate query list based on scrape depth and brand/category language."""
    from opencmo.scrape_config import get_scrape_profile
    profile = get_scrape_profile()
    pool = _QUERY_TEMPLATES_CN if _looks_cjk(brand_name, category) else _QUERY_TEMPLATES_EN
    n = min(profile.geo_query_templates, len(pool))
    templates = pool[:n]
    return [
        t.format(brand_name=brand_name, category=category)
        for t in templates
    ]


def _get_snippet_chars() -> int:
    from opencmo.scrape_config import get_scrape_profile
    return get_scrape_profile().geo_content_snippet_chars


def _get_request_delay() -> float:
    from opencmo.scrape_config import get_scrape_profile
    return get_scrape_profile().request_delay_seconds


_API_QUERY_TEMPLATE = (
    "What are the best {category} tools? List the top options with brief descriptions."
)


# ---------------------------------------------------------------------------
# Shared text analysis helper
# ---------------------------------------------------------------------------


def _normalize_match_text(text: str) -> str:
    """Lowercase + collapse whitespace; preserves CJK characters."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _match_brand_in_text(
    content: str,
    primary: str,
    aliases: list[str] | None = None,
) -> tuple[bool, int, float | None]:
    """Match a brand by primary name + aliases with word-boundary safety.

    ASCII candidates use \\b regex word boundaries to avoid 'Apple'→'Pineapple'
    false positives. CJK candidates fall back to literal substring (since \\b
    doesn't fire between CJK chars). Position is the earliest match across all
    candidates.
    """
    if not content or not primary:
        return False, 0, None
    candidates = [c for c in [primary, *(aliases or [])] if c and c.strip()]
    content_norm = _normalize_match_text(content)
    if not content_norm:
        return False, 0, None

    total_count = 0
    first_pos: int | None = None
    seen_norm: set[str] = set()
    for cand in candidates:
        cand_norm = _normalize_match_text(cand)
        if not cand_norm or cand_norm in seen_norm:
            continue
        seen_norm.add(cand_norm)
        if _CJK_RE.search(cand_norm):
            pattern = re.escape(cand_norm)
        else:
            pattern = r"(?<![a-z0-9])" + re.escape(cand_norm) + r"(?![a-z0-9])"
        for m in re.finditer(pattern, content_norm):
            total_count += 1
            if first_pos is None or m.start() < first_pos:
                first_pos = m.start()

    mentioned = total_count > 0
    position_pct: float | None = None
    if first_pos is not None:
        position_pct = round(first_pos / len(content_norm) * 100, 1)
    return mentioned, total_count, position_pct


# Per-task contextvar so providers see the project's aliases without threading
# them through every call site. asyncio.create_task copies context, so concurrent
# scans in different tasks see their own value.
_aliases_var: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "geo_brand_aliases", default=None
)


def set_brand_aliases(aliases: list[str] | None) -> contextvars.Token:
    """Set aliases for the current scan; returns a token for restoration."""
    return _aliases_var.set(list(aliases) if aliases else [])


def reset_brand_aliases(token: contextvars.Token) -> None:
    _aliases_var.reset(token)


def _current_aliases() -> list[str]:
    return _aliases_var.get() or []


def _analyze_text(content: str, brand_name: str) -> tuple[bool, int, float | None]:
    """Match against the brand and any aliases set on the current task context.

    Aliases are propagated via :func:`set_brand_aliases` so providers don't have
    to thread them through every internal call.
    """
    return _match_brand_in_text(content, brand_name, _current_aliases())


def compute_share_of_voice(
    snippets: list[str],
    brand_name: str,
    brand_aliases: list[str] | None,
    competitors: list[tuple[str, list[str]]],
) -> dict | None:
    """Compute brand vs competitor mention share across all snippets.

    Returns None when there's no competitor list to compare against.
    """
    if not competitors:
        return None
    text_blobs = [s for s in snippets if s]
    if not text_blobs:
        return None

    brand_count = 0
    for blob in text_blobs:
        _, c, _ = _match_brand_in_text(blob, brand_name, brand_aliases)
        brand_count += c

    competitor_counts: list[tuple[str, int]] = []
    for name, aliases in competitors:
        comp_count = 0
        for blob in text_blobs:
            _, c, _ = _match_brand_in_text(blob, name, aliases)
            comp_count += c
        competitor_counts.append((name, comp_count))

    total = brand_count + sum(c for _, c in competitor_counts)
    if total == 0:
        return {
            "brand": {"name": brand_name, "mentions": 0, "share": 0.0},
            "competitors": [
                {"name": n, "mentions": 0, "share": 0.0}
                for n, _ in competitor_counts
            ],
            "total_mentions": 0,
        }
    return {
        "brand": {
            "name": brand_name,
            "mentions": brand_count,
            "share": round(brand_count / total, 3),
        },
        "competitors": [
            {
                "name": n,
                "mentions": c,
                "share": round(c / total, 3),
            }
            for n, c in competitor_counts
        ],
        "total_mentions": total,
    }


# ---------------------------------------------------------------------------
# ABC
# ---------------------------------------------------------------------------


class GeoProvider(ABC):
    name: str
    status: str  # "enabled" | "disabled"
    requires_auth: bool
    auth_env_vars: list[str]

    @property
    def is_enabled(self) -> bool:
        if self.status == "disabled":
            return False
        if self.requires_auth:
            from opencmo import llm
            return all(llm.get_key(v) for v in self.auth_env_vars)
        return True

    def provider_identity(self) -> tuple:
        """Stable key for cross-provider dedup.

        Two providers with the same identity hit the same backend with the same
        prompt path; only one should run. Default is unique per class.
        """
        return ("provider", type(self).__name__)

    @abstractmethod
    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult: ...

    async def check_visibility_multi(
        self, brand_name: str, category: str
    ) -> GeoAggregatedResult:
        """Run check_visibility across multiple query templates and aggregate."""
        queries = _get_query_templates(brand_name, category)
        results: list[GeoProviderResult] = []

        for i, query in enumerate(queries):
            try:
                result = await self._check_single_query(brand_name, query)
                results.append(result)
            except Exception as e:
                results.append(GeoProviderResult(
                    platform=self.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet="",
                    error=str(e),
                    query=query,
                    source_status="error",
                ))

            if i < len(queries) - 1:
                delay = _get_request_delay()
                if delay > 0:
                    await asyncio.sleep(delay)

        # Aggregate
        any_mentioned = any(r.mentioned for r in results)
        total_mentions = sum(r.mention_count for r in results)
        positions = [r.position_pct for r in results if r.position_pct is not None]
        best_pos = min(positions) if positions else None
        errors = [r.error for r in results if r.error]
        agg_status = _aggregate_source_status([r.source_status for r in results])

        return GeoAggregatedResult(
            platform=self.name,
            mentioned=any_mentioned,
            total_mention_count=total_mentions,
            best_position_pct=best_pos,
            per_query_results=results,
            error="; ".join(errors) if errors else None,
            source_status=agg_status,
        )

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        """Override in subclasses to check a single query."""
        # Default: call check_visibility (backward compat for API providers)
        return await self.check_visibility(brand_name, query)


# ---------------------------------------------------------------------------
# Default LLM provider — uses whatever model the user already configured
# ---------------------------------------------------------------------------


class DefaultLLMProvider(GeoProvider):
    """GEO provider that queries the user's configured default LLM.

    Always enabled because OpenCMO requires an LLM to function at all.
    Uses opencmo.llm.chat_completion_messages() so it respects BYOK keys,
    custom base URLs, and per-request ContextVar isolation.
    """

    name = "Default LLM"
    status = "enabled"
    requires_auth = False
    auth_env_vars: list[str] = []

    @property
    def is_enabled(self) -> bool:
        return True

    def provider_identity(self) -> tuple:
        return ("user-configured-llm",)

    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult:
        query = _API_QUERY_TEMPLATE.format(category=category)
        return await self._check_single_query(brand_name, query)

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        snippet_chars = _get_snippet_chars()
        try:
            from opencmo import llm

            content = await llm.chat_completion_messages(
                [{"role": "user", "content": query}],
                max_tokens=1024,
            )
            content = content or ""
            status = _classify_api_content(content)
            if status != "ok":
                return GeoProviderResult(
                    platform=self.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet=content[:snippet_chars],
                    error=None,
                    query=query,
                    source_status=status,
                )
            mentioned, mention_count, position_pct = _analyze_text(
                content, brand_name
            )
            return GeoProviderResult(
                platform=self.name,
                mentioned=mentioned,
                mention_count=mention_count,
                position_pct=position_pct,
                content_snippet=content[:snippet_chars],
                error=None,
                query=query,
                source_status="ok",
            )
        except Exception as e:
            return GeoProviderResult(
                platform=self.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=str(e),
                query=query,
                source_status="error",
            )


# ---------------------------------------------------------------------------
# Crawl-based providers
# ---------------------------------------------------------------------------


class _CrawlSearchProvider(GeoProvider):
    """Shared base for AI-search providers we hit by scraping the public web UI.

    Subclasses provide ``name`` and ``search_url_template`` (with a ``{q}``
    placeholder for the URL-encoded query). Everything else — URL build,
    browser slot, crawl, markdown extract, content classification, brand
    match, error capture — is unified here so each new front-end addition is
    a ~5-line subclass.
    """

    status = "enabled"
    requires_auth = False
    auth_env_vars: list[str] = []
    search_url_template: str = ""

    def _build_url(self, query: str) -> str:
        return self.search_url_template.format(q=quote_plus(query))

    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult:
        query = f"有哪些好用的{category}工具" if _looks_cjk(brand_name, category) else f"best {category} tools"
        return await self._check_single_query(brand_name, query)

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        snippet_chars = _get_snippet_chars()
        url = self._build_url(query)
        try:
            async with browser_slot():
                async with AsyncWebCrawler() as crawler:
                    crawl_result = await crawler.arun(url=url)
                    content = _extract_markdown(crawl_result)
                    status = _classify_crawl_content(content)
                    if status != "ok":
                        return GeoProviderResult(
                            platform=self.name,
                            mentioned=False,
                            mention_count=0,
                            position_pct=None,
                            content_snippet=content[:snippet_chars],
                            error=None,
                            query=query,
                            source_status=status,
                        )
                    mentioned, mention_count, position_pct = _analyze_text(
                        content, brand_name
                    )
                    return GeoProviderResult(
                        platform=self.name,
                        mentioned=mentioned,
                        mention_count=mention_count,
                        position_pct=position_pct,
                        content_snippet=content[:snippet_chars],
                        error=None,
                        query=query,
                        source_status="ok",
                    )
        except Exception as e:
            return GeoProviderResult(
                platform=self.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=str(e),
                query=query,
                source_status="error",
            )


class PerplexityProvider(_CrawlSearchProvider):
    name = "Perplexity"
    search_url_template = "https://www.perplexity.ai/search?q={q}"


class YouDotComProvider(_CrawlSearchProvider):
    name = "You.com"
    search_url_template = "https://you.com/search?q={q}"


class MetaSoProvider(_CrawlSearchProvider):
    name = "MetaSo"
    search_url_template = "https://metaso.cn/?q={q}"


class ThreeSixtyAISearchProvider(_CrawlSearchProvider):
    name = "360 AI"
    search_url_template = "https://www.so.com/s?q={q}"


# ---------------------------------------------------------------------------
# API-based providers
# ---------------------------------------------------------------------------


class ChatGPTProvider(GeoProvider):
    name = "ChatGPT"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["OPENAI_API_KEY"]

    @property
    def is_enabled(self) -> bool:
        from opencmo import llm
        return (
            llm.get_key("OPENCMO_GEO_CHATGPT") == "1"
            and bool(llm.get_key("OPENAI_API_KEY"))
        )

    def provider_identity(self) -> tuple:
        # Same backend as DefaultLLMProvider — both go through llm.chat_completion_messages
        # with the user's configured base/key/model.
        return ("user-configured-llm",)

    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult:
        query = _API_QUERY_TEMPLATE.format(category=category)
        return await self._check_single_query(brand_name, query)

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        snippet_chars = _get_snippet_chars()
        try:
            from opencmo import llm

            content = await llm.chat_completion_messages(
                messages=[
                    {
                        "role": "user",
                        "content": query,
                    }
                ],
                model_override=await llm.get_model(),
                max_tokens=1024,
            )
            content = content or ""
            status = _classify_api_content(content)
            if status != "ok":
                return GeoProviderResult(
                    platform=self.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet=content[:snippet_chars],
                    error=None,
                    query=query,
                    source_status=status,
                )
            mentioned, mention_count, position_pct = _analyze_text(
                content, brand_name
            )
            return GeoProviderResult(
                platform=self.name,
                mentioned=mentioned,
                mention_count=mention_count,
                position_pct=position_pct,
                content_snippet=content[:snippet_chars],
                error=None,
                query=query,
                source_status="ok",
            )
        except Exception as e:
            return GeoProviderResult(
                platform=self.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=str(e),
                query=query,
                source_status="error",
            )


class ClaudeProvider(GeoProvider):
    name = "Claude"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["ANTHROPIC_API_KEY"]

    @property
    def is_enabled(self) -> bool:
        if not _HAS_ANTHROPIC:
            return False
        from opencmo import llm
        return bool(llm.get_key("ANTHROPIC_API_KEY"))

    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult:
        query = _API_QUERY_TEMPLATE.format(category=category)
        return await self._check_single_query(brand_name, query)

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        snippet_chars = _get_snippet_chars()
        try:
            from opencmo import llm
            client = anthropic.AsyncAnthropic(
                api_key=llm.get_key("ANTHROPIC_API_KEY"),
            )
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": query,
                    }
                ],
            )
            content = response.content[0].text if response.content else ""
            content = content or ""
            status = _classify_api_content(content)
            if status != "ok":
                return GeoProviderResult(
                    platform=self.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet=content[:snippet_chars],
                    error=None,
                    query=query,
                    source_status=status,
                )
            mentioned, mention_count, position_pct = _analyze_text(
                content, brand_name
            )
            return GeoProviderResult(
                platform=self.name,
                mentioned=mentioned,
                mention_count=mention_count,
                position_pct=position_pct,
                content_snippet=content[:snippet_chars],
                error=None,
                query=query,
                source_status="ok",
            )
        except Exception as e:
            return GeoProviderResult(
                platform=self.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=str(e),
                query=query,
                source_status="error",
            )


class GeminiProvider(GeoProvider):
    name = "Gemini"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["GOOGLE_AI_API_KEY"]

    @property
    def is_enabled(self) -> bool:
        if not _HAS_GENAI:
            return False
        from opencmo import llm
        return bool(llm.get_key("GOOGLE_AI_API_KEY"))

    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult:
        query = _API_QUERY_TEMPLATE.format(category=category)
        return await self._check_single_query(brand_name, query)

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        snippet_chars = _get_snippet_chars()
        try:
            from opencmo import llm
            genai.configure(api_key=llm.get_key("GOOGLE_AI_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = await model.generate_content_async(query)
            content = response.text or ""
            status = _classify_api_content(content)
            if status != "ok":
                return GeoProviderResult(
                    platform=self.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet=content[:snippet_chars],
                    error=None,
                    query=query,
                    source_status=status,
                )
            mentioned, mention_count, position_pct = _analyze_text(
                content, brand_name
            )
            return GeoProviderResult(
                platform=self.name,
                mentioned=mentioned,
                mention_count=mention_count,
                position_pct=position_pct,
                content_snippet=content[:snippet_chars],
                error=None,
                query=query,
                source_status="ok",
            )
        except Exception as e:
            return GeoProviderResult(
                platform=self.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=str(e),
                query=query,
                source_status="error",
            )


# ---------------------------------------------------------------------------
# OpenAI-compatible Chinese AI providers
# ---------------------------------------------------------------------------

_CN_API_QUERY_TEMPLATE = (
    "有哪些好用的{category}工具？列出最推荐的几个，并简要介绍各自的特点。"
)


class _OpenAICompatibleProvider(GeoProvider):
    """Base for providers that expose an OpenAI-compatible chat API."""

    api_key_env: str
    base_url: str
    model_name: str

    @property
    def is_enabled(self) -> bool:
        from opencmo import llm
        return bool(llm.get_key(self.api_key_env))

    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult:
        query = _CN_API_QUERY_TEMPLATE.format(category=category)
        return await self._check_single_query(brand_name, query)

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        snippet_chars = _get_snippet_chars()
        try:
            from opencmo import llm

            content = await llm.chat_completion_messages(
                messages=[{"role": "user", "content": query}],
                model_override=self.model_name,
                max_tokens=1024,
                api_key_override=llm.get_key(self.api_key_env),
                base_url_override=self.base_url,
            )
            content = content or ""
            status = _classify_api_content(content)
            if status != "ok":
                return GeoProviderResult(
                    platform=self.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet=content[:snippet_chars],
                    error=None,
                    query=query,
                    source_status=status,
                )
            mentioned, mention_count, position_pct = _analyze_text(
                content, brand_name
            )
            return GeoProviderResult(
                platform=self.name,
                mentioned=mentioned,
                mention_count=mention_count,
                position_pct=position_pct,
                content_snippet=content[:snippet_chars],
                error=None,
                query=query,
                source_status="ok",
            )
        except Exception as e:
            return GeoProviderResult(
                platform=self.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=str(e),
                query=query,
                source_status="error",
            )


class KimiProvider(_OpenAICompatibleProvider):
    name = "Kimi"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["MOONSHOT_API_KEY"]
    api_key_env = "MOONSHOT_API_KEY"
    base_url = "https://api.moonshot.cn/v1"
    model_name = "moonshot-v1-8k"


class QwenProvider(_OpenAICompatibleProvider):
    name = "Qwen"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["DASHSCOPE_API_KEY"]
    api_key_env = "DASHSCOPE_API_KEY"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model_name = "qwen-turbo"


class DeepSeekProvider(_OpenAICompatibleProvider):
    name = "DeepSeek"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["DEEPSEEK_API_KEY"]
    api_key_env = "DEEPSEEK_API_KEY"
    base_url = "https://api.deepseek.com"
    model_name = "deepseek-chat"


class ZhipuProvider(_OpenAICompatibleProvider):
    name = "Zhipu GLM"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["ZHIPU_API_KEY"]
    api_key_env = "ZHIPU_API_KEY"
    base_url = "https://open.bigmodel.cn/api/paas/v4"
    model_name = "glm-4-flash"


class DoubaoProvider(_OpenAICompatibleProvider):
    name = "Doubao"
    status = "disabled"
    requires_auth = True
    auth_env_vars = ["DOUBAO_API_KEY"]
    api_key_env = "DOUBAO_API_KEY"
    base_url = "https://ark.cn-beijing.volces.com/api/v3"
    model_name = "doubao-1-5-lite-32k"


# ---------------------------------------------------------------------------
# cloro providers: answers from the ChatGPT, Gemini and Google AI Mode web apps
# ---------------------------------------------------------------------------

CLORO_API_BASE = "https://api.cloro.dev/v1/monitor"


class _CloroProvider(GeoProvider):
    """Base for providers that read consumer AI answers through the cloro API.

    The model API providers above return what the model says without the
    consumer app's web search. cloro returns the answer that the web app shows
    to a user. Docs: https://cloro.dev/docs?utm_source=opencmo&utm_medium=byok
    """

    status = "disabled"
    requires_auth = True
    auth_env_vars = ["CLORO_API_KEY"]
    engine: str  # cloro monitor endpoint: "chatgpt" | "gemini" | "aimode"

    @property
    def is_enabled(self) -> bool:
        from opencmo import llm
        return bool(llm.get_key("CLORO_API_KEY"))

    async def check_visibility(
        self, brand_name: str, category: str
    ) -> GeoProviderResult:
        query = _API_QUERY_TEMPLATE.format(category=category)
        return await self._check_single_query(brand_name, query)

    async def _check_single_query(
        self, brand_name: str, query: str
    ) -> GeoProviderResult:
        snippet_chars = _get_snippet_chars()
        try:
            import httpx

            from opencmo import llm

            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    f"{CLORO_API_BASE}/{self.engine}",
                    headers={"Authorization": f"Bearer {llm.get_key('CLORO_API_KEY')}"},
                    json={"prompt": query, "country": llm.get_key("CLORO_COUNTRY") or "US"},
                )
            data = resp.json()
            if resp.status_code >= 400 or not data.get("success"):
                err = data.get("error") or {}
                raise RuntimeError(f"cloro HTTP {resp.status_code}: {err.get('code', '')} {err.get('message', '')}")
            content = (data.get("result") or {}).get("text") or ""
            status = _classify_api_content(content)
            if status != "ok":
                return GeoProviderResult(
                    platform=self.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet=content[:snippet_chars],
                    error=None,
                    query=query,
                    source_status=status,
                )
            mentioned, mention_count, position_pct = _analyze_text(
                content, brand_name
            )
            return GeoProviderResult(
                platform=self.name,
                mentioned=mentioned,
                mention_count=mention_count,
                position_pct=position_pct,
                content_snippet=content[:snippet_chars],
                error=None,
                query=query,
                source_status="ok",
            )
        except Exception as e:
            return GeoProviderResult(
                platform=self.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=str(e),
                query=query,
                source_status="error",
            )


class CloroChatGPTProvider(_CloroProvider):
    name = "ChatGPT (cloro)"
    engine = "chatgpt"


class CloroGeminiProvider(_CloroProvider):
    name = "Gemini (cloro)"
    engine = "gemini"


class CloroAIModeProvider(_CloroProvider):
    name = "Google AI Mode (cloro)"
    engine = "aimode"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def get_enabled_providers(
    registry: list[GeoProvider] | None = None,
) -> list[GeoProvider]:
    """Return enabled providers with cross-provider duplicates collapsed.

    When two providers share the same `provider_identity()` (e.g. DefaultLLM
    and ChatGPT both routing through the user's configured OpenAI-compatible
    endpoint), keep the one the user opted into explicitly (status='disabled'
    + currently is_enabled) and drop the always-on one.
    """
    if registry is None:
        registry = GEO_PROVIDER_REGISTRY
    enabled = [p for p in registry if p.is_enabled]
    by_identity: dict[tuple, GeoProvider] = {}
    for p in enabled:
        provider_identity = getattr(p, "provider_identity", None)
        if callable(provider_identity):
            ident = provider_identity()
        else:
            ident = ("provider", type(p).__name__, getattr(p, "name", ""))
        existing = by_identity.get(ident)
        if existing is None:
            by_identity[ident] = p
            continue
        # Collision: prefer the explicit opt-in (status='disabled' but currently enabled
        # via env flag) over the always-on default.
        if getattr(existing, "status", None) == "enabled" and getattr(p, "status", None) == "disabled":
            by_identity[ident] = p
    return list(by_identity.values())


GEO_PROVIDER_REGISTRY: list[GeoProvider] = [
    DefaultLLMProvider(),
    PerplexityProvider(),
    YouDotComProvider(),
    ChatGPTProvider(),
    ClaudeProvider(),
    GeminiProvider(),
    KimiProvider(),
    QwenProvider(),
    DeepSeekProvider(),
    ZhipuProvider(),
    DoubaoProvider(),
    MetaSoProvider(),
    ThreeSixtyAISearchProvider(),
    CloroChatGPTProvider(),
    CloroGeminiProvider(),
    CloroAIModeProvider(),
]
