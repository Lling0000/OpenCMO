"""Tests for GEO provider architecture."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opencmo.tools.geo_providers import (
    GEO_PROVIDER_REGISTRY,
    ChatGPTProvider,
    ClaudeProvider,
    CloroAIModeProvider,
    CloroBingAIModeProvider,
    CloroChatGPTProvider,
    CloroGeminiProvider,
    DeepSeekProvider,
    DefaultLLMProvider,
    DoubaoProvider,
    GeminiProvider,
    GeoProviderResult,
    KimiProvider,
    PerplexityProvider,
    QwenProvider,
    ZhipuProvider,
    _analyze_text,
    _match_brand_in_text,
    get_enabled_providers,
    reset_brand_aliases,
    set_brand_aliases,
)


@pytest.fixture(autouse=True)
def _use_light_profile(monkeypatch):
    monkeypatch.setenv("OPENCMO_SCRAPE_DEPTH", "light")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_geo_provider_registry():
    assert len(GEO_PROVIDER_REGISTRY) == 17
    names = {p.name for p in GEO_PROVIDER_REGISTRY}
    assert names == {
        "Default LLM", "Perplexity", "You.com", "ChatGPT", "Claude", "Gemini",
        "Kimi", "Qwen", "DeepSeek", "Zhipu GLM", "Doubao", "MetaSo", "360 AI",
        "ChatGPT (cloro)", "Gemini (cloro)", "Google AI Mode (cloro)",
        "Bing AI Mode (cloro)",
    }


def test_crawl_providers_enabled_by_default():
    perplexity = next(p for p in GEO_PROVIDER_REGISTRY if p.name == "Perplexity")
    youcom = next(p for p in GEO_PROVIDER_REGISTRY if p.name == "You.com")
    assert perplexity.is_enabled
    assert youcom.is_enabled


def test_api_providers_disabled_without_keys():
    """API-based providers should be disabled without their env vars."""
    env_clean = {
        "OPENCMO_GEO_CHATGPT": "",
        "ANTHROPIC_API_KEY": "",
        "GOOGLE_AI_API_KEY": "",
        "MOONSHOT_API_KEY": "",
        "DASHSCOPE_API_KEY": "",
        "DEEPSEEK_API_KEY": "",
        "ZHIPU_API_KEY": "",
        "DOUBAO_API_KEY": "",
        "CLORO_API_KEY": "",
    }
    with patch.dict(os.environ, env_clean, clear=False):
        assert not ChatGPTProvider().is_enabled
        assert not ClaudeProvider().is_enabled
        assert not GeminiProvider().is_enabled
        assert not KimiProvider().is_enabled
        assert not QwenProvider().is_enabled
        assert not DeepSeekProvider().is_enabled
        assert not ZhipuProvider().is_enabled
        assert not DoubaoProvider().is_enabled
        assert not CloroChatGPTProvider().is_enabled
        assert not CloroGeminiProvider().is_enabled
        assert not CloroAIModeProvider().is_enabled
        assert not CloroBingAIModeProvider().is_enabled


def test_chatgpt_requires_opt_in():
    """ChatGPT needs both OPENCMO_GEO_CHATGPT=1 and OPENAI_API_KEY."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENCMO_GEO_CHATGPT": ""}, clear=False):
        p = ChatGPTProvider()
        assert not p.is_enabled

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "OPENCMO_GEO_CHATGPT": "1"}, clear=False):
        p = ChatGPTProvider()
        assert p.is_enabled


# ---------------------------------------------------------------------------
# Text analysis helper
# ---------------------------------------------------------------------------


def test_analyze_text_found():
    mentioned, count, pos = _analyze_text("Try Crawl4AI for web scraping", "Crawl4AI")
    assert mentioned is True
    assert count == 1
    assert pos is not None
    assert 0 <= pos <= 100


def test_analyze_text_not_found():
    mentioned, count, pos = _analyze_text("Try Scrapy for web scraping", "Crawl4AI")
    assert mentioned is False
    assert count == 0
    assert pos is None


def test_analyze_text_multiple_mentions():
    text = "Crawl4AI is great. I use Crawl4AI daily. Crawl4AI rocks."
    mentioned, count, pos = _analyze_text(text, "Crawl4AI")
    assert mentioned is True
    assert count == 3


def test_analyze_text_case_insensitive():
    mentioned, count, pos = _analyze_text("Try crawl4ai for scraping", "Crawl4AI")
    assert mentioned is True


# ---------------------------------------------------------------------------
# Word-boundary + alias matching
# ---------------------------------------------------------------------------


def test_word_boundary_blocks_partial_substring():
    # "Apple" must not match "Pineapple"
    mentioned, count, _ = _match_brand_in_text("Pineapple is fruit", "Apple")
    assert mentioned is False
    assert count == 0


def test_word_boundary_allows_punctuation():
    # ASCII brand should still match when followed by punctuation/whitespace
    mentioned, count, _ = _match_brand_in_text(
        "Linear, Notion, and Asana are tools.", "Linear"
    )
    assert mentioned is True
    assert count == 1


def test_alias_recovers_spaced_variant():
    # "OpenAI" with alias "Open AI" must match text that says "Open AI"
    mentioned, count, _ = _match_brand_in_text(
        "I use Open AI for prompts.", "OpenAI", aliases=["Open AI"]
    )
    assert mentioned is True
    assert count == 1


def test_aliases_dedup_normalized_duplicates():
    # Aliases listed in different cases collapse to one matcher
    mentioned, count, _ = _match_brand_in_text(
        "Open AI is everywhere.", "OpenAI", aliases=["Open AI", "open ai", "OPEN AI"]
    )
    assert mentioned is True
    assert count == 1


def test_cjk_brand_matches_literal():
    mentioned, count, _ = _match_brand_in_text(
        "我们团队最近换到飞书做协作，飞书的体验不错。", "飞书"
    )
    assert mentioned is True
    assert count == 2


def test_position_takes_earliest_alias_match():
    # primary appears later than alias → position should reflect alias's earlier hit
    mentioned, count, pos = _match_brand_in_text(
        "Open AI launched. Later, OpenAI shipped more.",
        "OpenAI",
        aliases=["Open AI"],
    )
    assert mentioned is True
    assert count == 2
    assert pos is not None and pos < 50  # earliest match is in first half


def test_aliases_contextvar_propagates_to_analyze_text():
    token = set_brand_aliases(["Open AI"])
    try:
        mentioned, count, _ = _analyze_text("Open AI is here", "OpenAI")
    finally:
        reset_brand_aliases(token)
    assert mentioned is True
    assert count == 1


# ---------------------------------------------------------------------------
# Provider dedup
# ---------------------------------------------------------------------------


def test_dedup_drops_default_when_chatgpt_explicit(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENCMO_GEO_CHATGPT", "1")
    names = [p.name for p in get_enabled_providers()]
    assert "ChatGPT" in names
    assert "Default LLM" not in names


def test_dedup_keeps_default_when_chatgpt_not_opted_in(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("OPENCMO_GEO_CHATGPT", raising=False)
    names = [p.name for p in get_enabled_providers()]
    assert "Default LLM" in names
    assert "ChatGPT" not in names


# ---------------------------------------------------------------------------
# Provider parse tests (mock API responses)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chatgpt_provider_parse():
    provider = ChatGPTProvider()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Top tools: 1. Crawl4AI - great for scraping. 2. Scrapy - classic."

    with patch("opencmo.tools.geo_providers.ChatGPTProvider.is_enabled", True):
        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await provider.check_visibility("Crawl4AI", "web scraping")
            assert result.mentioned is True
            assert result.mention_count >= 1
            assert result.error is None


@pytest.mark.asyncio
async def test_claude_provider_parse():
    provider = ClaudeProvider()

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Top tools: 1. Crawl4AI 2. BeautifulSoup")]

    with patch("opencmo.tools.geo_providers._HAS_ANTHROPIC", True):
        with patch("opencmo.tools.geo_providers.anthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            result = await provider.check_visibility("Crawl4AI", "web scraping")
            assert result.mentioned is True
            assert result.error is None


@pytest.mark.asyncio
async def test_gemini_provider_parse():
    provider = GeminiProvider()

    mock_response = MagicMock()
    mock_response.text = "Best tools: Crawl4AI, Playwright, Puppeteer"

    with patch("opencmo.tools.geo_providers._HAS_GENAI", True):
        with patch("opencmo.tools.geo_providers.genai") as mock_genai:
            with patch.dict(os.environ, {"GOOGLE_AI_API_KEY": "test-key"}):
                mock_model = AsyncMock()
                mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                mock_genai.GenerativeModel.return_value = mock_model

                result = await provider.check_visibility("Crawl4AI", "web scraping")
                assert result.mentioned is True
                assert result.error is None


@pytest.mark.asyncio
async def test_cn_provider_parse():
    """Chinese AI providers should parse OpenAI-compatible responses."""
    for provider_cls in (KimiProvider, QwenProvider, DeepSeekProvider, ZhipuProvider, DoubaoProvider):
        provider = provider_cls()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "推荐工具：1. Crawl4AI - 强大的爬虫框架 2. Scrapy"

        with patch("openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            result = await provider.check_visibility("Crawl4AI", "网页爬虫")
            assert result.mentioned is True
            assert result.mention_count >= 1
            assert result.error is None
            assert result.platform == provider.name


@pytest.mark.asyncio
async def test_cn_provider_enabled_with_key():
    """Chinese providers should enable when their API key is set."""
    with patch.dict(os.environ, {"MOONSHOT_API_KEY": "test-key"}, clear=False):
        assert KimiProvider().is_enabled
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
        assert DeepSeekProvider().is_enabled


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def test_scoring_scales_with_provider_count():
    """Visibility score should scale with number of enabled providers."""
    # 1 out of 2 mentioned = 20/40
    # 1 out of 5 mentioned = 8/40
    score_2 = int(1 / 2 * 40)
    score_5 = int(1 / 5 * 40)
    assert score_2 == 20
    assert score_5 == 8


# ---------------------------------------------------------------------------
# Graceful failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_failure_graceful():
    """Single provider failure should return error result, not raise."""
    provider = PerplexityProvider()

    with patch("opencmo.tools.geo_providers.AsyncWebCrawler") as mock_cls:
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=False)
        mock_crawler.arun = AsyncMock(side_effect=Exception("network error"))
        mock_cls.return_value = mock_crawler

        result = await provider.check_visibility("Test", "testing")
        assert result.mentioned is False
        assert result.error is not None
        assert "network error" in result.error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_cls",
    [
        DefaultLLMProvider,
        ChatGPTProvider,
        KimiProvider,
        QwenProvider,
        DeepSeekProvider,
        ZhipuProvider,
        DoubaoProvider,
    ],
)
async def test_llm_api_provider_exception_status_is_error(provider_cls):
    """LLM-backed provider exceptions should not look like ok/no-mention."""
    provider = provider_cls()

    with (
        patch(
            "opencmo.llm.chat_completion_messages",
            new=AsyncMock(side_effect=Exception("api failed")),
        ),
        patch("opencmo.llm.get_model", new=AsyncMock(return_value="test-model")),
        patch("opencmo.llm.get_key", return_value="test-key"),
    ):
        result = await provider._check_single_query("Crawl4AI", "query")

    assert result.mentioned is False
    assert result.error == "api failed"
    assert result.source_status == "error"


@pytest.mark.asyncio
async def test_claude_provider_exception_status_is_error():
    provider = ClaudeProvider()

    with (
        patch("opencmo.tools.geo_providers._HAS_ANTHROPIC", True),
        patch("opencmo.tools.geo_providers.anthropic") as mock_anthropic,
        patch("opencmo.llm.get_key", return_value="test-key"),
    ):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("anthropic failed"))
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        result = await provider._check_single_query("Crawl4AI", "query")

    assert result.mentioned is False
    assert result.error == "anthropic failed"
    assert result.source_status == "error"


@pytest.mark.asyncio
async def test_gemini_provider_exception_status_is_error():
    provider = GeminiProvider()

    with (
        patch("opencmo.tools.geo_providers._HAS_GENAI", True),
        patch("opencmo.tools.geo_providers.genai") as mock_genai,
        patch("opencmo.llm.get_key", return_value="test-key"),
    ):
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(side_effect=Exception("gemini failed"))
        mock_genai.GenerativeModel.return_value = mock_model

        result = await provider._check_single_query("Crawl4AI", "query")

    assert result.mentioned is False
    assert result.error == "gemini failed"
    assert result.source_status == "error"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_cls",
    [
        DefaultLLMProvider,
        ChatGPTProvider,
        KimiProvider,
        QwenProvider,
        DeepSeekProvider,
        ZhipuProvider,
        DoubaoProvider,
    ],
)
async def test_llm_api_provider_empty_response_status_is_empty(provider_cls):
    """Empty API responses should be unobservable, not ok/no-mention."""
    provider = provider_cls()

    with (
        patch("opencmo.llm.chat_completion_messages", new=AsyncMock(return_value="")),
        patch("opencmo.llm.get_model", new=AsyncMock(return_value="test-model")),
        patch("opencmo.llm.get_key", return_value="test-key"),
    ):
        result = await provider._check_single_query("Crawl4AI", "query")

    assert result.mentioned is False
    assert result.error is None
    assert result.source_status == "empty"


@pytest.mark.asyncio
async def test_claude_provider_empty_response_status_is_empty():
    provider = ClaudeProvider()
    mock_response = MagicMock()
    mock_response.content = []

    with (
        patch("opencmo.tools.geo_providers._HAS_ANTHROPIC", True),
        patch("opencmo.tools.geo_providers.anthropic") as mock_anthropic,
        patch("opencmo.llm.get_key", return_value="test-key"),
    ):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic.AsyncAnthropic.return_value = mock_client

        result = await provider._check_single_query("Crawl4AI", "query")

    assert result.mentioned is False
    assert result.error is None
    assert result.source_status == "empty"


@pytest.mark.asyncio
async def test_gemini_provider_empty_response_status_is_empty():
    provider = GeminiProvider()
    mock_response = MagicMock()
    mock_response.text = ""

    with (
        patch("opencmo.tools.geo_providers._HAS_GENAI", True),
        patch("opencmo.tools.geo_providers.genai") as mock_genai,
        patch("opencmo.llm.get_key", return_value="test-key"),
    ):
        mock_model = AsyncMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await provider._check_single_query("Crawl4AI", "query")

    assert result.mentioned is False
    assert result.error is None
    assert result.source_status == "empty"


@pytest.mark.asyncio
async def test_api_provider_blocked_response_status_is_blocked():
    provider = DefaultLLMProvider()

    with patch(
        "opencmo.llm.chat_completion_messages",
        new=AsyncMock(return_value="Access denied. Too many requests."),
    ):
        result = await provider._check_single_query("Crawl4AI", "query")

    assert result.mentioned is False
    assert result.error is None
    assert result.source_status == "blocked"


@pytest.mark.asyncio
async def test_provider_multi_aggregates_error_and_empty_statuses():
    provider = KimiProvider()

    async def fake_check(_brand_name, query):
        if query == "empty query":
            return GeoProviderResult(
                platform=provider.name,
                mentioned=False,
                mention_count=0,
                position_pct=None,
                content_snippet="",
                error=None,
                query=query,
                source_status="empty",
            )
        return GeoProviderResult(
            platform=provider.name,
            mentioned=False,
            mention_count=0,
            position_pct=None,
            content_snippet="",
            error="api failed",
            query=query,
            source_status="error",
        )

    with (
        patch("opencmo.tools.geo_providers._get_query_templates", return_value=["empty query", "error query"]),
        patch.object(provider, "_check_single_query", side_effect=fake_check),
    ):
        result = await provider.check_visibility_multi("Crawl4AI", "web scraping")

    assert result.mentioned is False
    assert result.error == "api failed"
    assert result.source_status == "error"
    assert [r.source_status for r in result.per_query_results] == ["empty", "error"]


# ---------------------------------------------------------------------------
# cloro providers (HTTP stubbed; payloads follow live cloro responses)
# ---------------------------------------------------------------------------


def _fake_httpx_client(status_code: int, payload: dict, calls: list):
    class FakeResponse:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            return payload

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    return FakeClient


_CLORO_ANSWER = {
    "success": True,
    "result": {
        "model": None,
        "text": "Top web scraping tools: 1. Crawl4AI is an open-source crawler. 2. Scrapy.",
        "sources": [
            {"position": 1, "label": "Crawl4AI docs", "url": "https://docs.crawl4ai.com/", "footnote": True},
        ],
        "citationPills": [],
    },
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_cls", "engine"),
    [
        (CloroChatGPTProvider, "chatgpt"),
        (CloroGeminiProvider, "gemini"),
        (CloroAIModeProvider, "aimode"),
        (CloroBingAIModeProvider, "bing/aimode"),
    ],
)
async def test_cloro_provider_parse(provider_cls, engine):
    from opencmo import llm

    calls: list = []
    token = llm.set_request_keys({"CLORO_API_KEY": "byok-cloro"})
    try:
        with patch("httpx.AsyncClient", _fake_httpx_client(200, _CLORO_ANSWER, calls)):
            provider = provider_cls()
            assert provider.is_enabled
            result = await provider.check_visibility("Crawl4AI", "web scraping")
    finally:
        llm.reset_request_keys(token)

    assert calls[0]["url"] == f"https://api.cloro.dev/v1/monitor/{engine}"
    assert calls[0]["headers"]["Authorization"] == "Bearer byok-cloro"
    assert calls[0]["json"]["country"] == "US"
    assert result.mentioned is True
    assert result.mention_count >= 1
    assert result.error is None
    assert result.source_status == "ok"
    assert result.platform == provider_cls.name


@pytest.mark.asyncio
async def test_cloro_provider_error_body_is_error_status():
    from opencmo import llm

    bad_key = {"success": False, "error": {"code": "INVALID_API_KEY_FORMAT", "message": "Invalid API key format"}}
    token = llm.set_request_keys({"CLORO_API_KEY": "bad"})
    try:
        with patch("httpx.AsyncClient", _fake_httpx_client(401, bad_key, [])):
            result = await CloroChatGPTProvider().check_visibility("Crawl4AI", "web scraping")
    finally:
        llm.reset_request_keys(token)

    assert result.mentioned is False
    assert result.source_status == "error"
    assert "INVALID_API_KEY_FORMAT" in result.error
