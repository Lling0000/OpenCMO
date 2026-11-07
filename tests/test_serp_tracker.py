"""Tests for SERP tracker — provider, storage, trends."""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Use a temporary DB for tests."""
    from opencmo import storage
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(storage, "_DB_PATH", db_path)
    return db_path


# ---------------------------------------------------------------------------
# Provider tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serp_provider_crawl_failure():
    """Crawl failure returns position=None + error string, doesn't raise."""
    from opencmo.tools.serp_tracker import CrawlSerpProvider

    provider = CrawlSerpProvider()
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client_cls.return_value = mock_client

        result = await provider.check_ranking("test query", "example.com")

    assert result.position is None
    assert result.error is not None
    assert "Connection refused" in result.error
    assert result.provider == "crawl"


@pytest.mark.asyncio
async def test_serp_provider_success_found():
    """Provider finds target domain in results."""
    from opencmo.tools.serp_tracker import CrawlSerpProvider

    provider = CrawlSerpProvider()
    fake_html = '''
    <a href="/url?q=https://other.com/page1">Other</a>
    <a href="/url?q=https://example.com/article">Target</a>
    <a href="/url?q=https://another.com/page">Another</a>
    '''
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await provider.check_ranking("test", "example.com")

    assert result.position == 2
    assert result.url_found == "https://example.com/article"
    assert result.error is None


@pytest.mark.asyncio
async def test_serp_provider_success_not_found():
    """Provider correctly reports not-found (no matching domain)."""
    from opencmo.tools.serp_tracker import CrawlSerpProvider

    provider = CrawlSerpProvider()
    fake_html = '<a href="/url?q=https://other.com/page">Other</a>'
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await provider.check_ranking("test", "example.com")

    assert result.position is None
    assert result.url_found is None
    assert result.error is None


@pytest.mark.asyncio
async def test_check_ranking_falls_back_to_crawl_on_provider_error(monkeypatch):
    """A Tavily quota/rate error should not be persisted if crawl fallback succeeds."""
    from opencmo.tools import serp_tracker
    from opencmo.tools.serp_tracker import SerpResult

    calls: list[str] = []

    class FakeTavilyProvider:
        name = "tavily"

        @property
        def is_enabled(self):
            return True

        async def check_ranking(self, keyword, target_domain, num_results=20):
            calls.append(self.name)
            return SerpResult(
                position=None,
                url_found=None,
                total_results=0,
                provider=self.name,
                error="This request exceeds your plan's set usage limit.",
            )

    class FakeCrawlProvider:
        name = "crawl"

        @property
        def is_enabled(self):
            return True

        async def check_ranking(self, keyword, target_domain, num_results=20):
            calls.append(self.name)
            return SerpResult(
                position=3,
                url_found="https://example.com/page",
                total_results=10,
                provider=self.name,
                error=None,
            )

    monkeypatch.setattr(
        serp_tracker,
        "SERP_PROVIDER_REGISTRY",
        [FakeTavilyProvider(), FakeCrawlProvider()],
    )

    result = await serp_tracker._check_ranking("test keyword", "example.com")

    assert calls == ["tavily", "crawl"]
    assert result.provider == "crawl"
    assert result.position == 3
    assert result.error is None


# ---------------------------------------------------------------------------
# Storage tests (tracked_keywords + serp_snapshots)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tracked_keywords_crud(tmp_db):
    """Add, list, remove tracked keywords."""
    from opencmo import storage

    pid = await storage.ensure_project("Test", "https://example.com", "saas")

    kw_id = await storage.add_tracked_keyword(pid, "python web scraping")
    assert kw_id > 0

    keywords = await storage.list_tracked_keywords(pid)
    assert len(keywords) == 1
    assert keywords[0]["keyword"] == "python web scraping"

    # Duplicate should be ignored
    await storage.add_tracked_keyword(pid, "python web scraping")
    keywords = await storage.list_tracked_keywords(pid)
    assert len(keywords) == 1

    ok = await storage.remove_tracked_keyword(kw_id)
    assert ok
    keywords = await storage.list_tracked_keywords(pid)
    assert len(keywords) == 0


@pytest.mark.asyncio
async def test_serp_snapshot_crud(tmp_db):
    """Save and query SERP snapshots with provider + error columns."""
    from opencmo import storage

    pid = await storage.ensure_project("Test", "https://example.com", "saas")
    await storage.add_tracked_keyword(pid, "test keyword")

    snap_id = await storage.save_serp_snapshot(
        pid, "test keyword", 5, "https://example.com/page", "crawl", None
    )
    assert snap_id > 0

    history = await storage.get_serp_history(pid, "test keyword", limit=10)
    assert len(history) == 1
    assert history[0]["position"] == 5
    assert history[0]["provider"] == "crawl"
    assert history[0]["error"] is None


@pytest.mark.asyncio
async def test_serp_snapshot_error_vs_not_ranked(tmp_db):
    """Distinguish error (error IS NOT NULL) from not-ranked (position IS NULL, error IS NULL)."""
    from opencmo import storage

    pid = await storage.ensure_project("Test", "https://example.com", "saas")

    # Error case
    await storage.save_serp_snapshot(pid, "kw1", None, None, "crawl", "Connection refused")
    # Not ranked case
    await storage.save_serp_snapshot(pid, "kw2", None, None, "crawl", None)

    h1 = await storage.get_serp_history(pid, "kw1")
    h2 = await storage.get_serp_history(pid, "kw2")

    assert h1[0]["error"] == "Connection refused"
    assert h1[0]["position"] is None

    assert h2[0]["error"] is None
    assert h2[0]["position"] is None


@pytest.mark.asyncio
async def test_serp_trends_with_data(tmp_db):
    """get_serp_trends returns markdown table when data exists."""
    from opencmo import storage
    from opencmo.tools.serp_tracker import _get_serp_trends_impl

    pid = await storage.ensure_project("Test", "https://example.com", "saas")
    await storage.add_tracked_keyword(pid, "test kw")
    await storage.save_serp_snapshot(pid, "test kw", 3, "https://example.com", "crawl", None)

    result = await _get_serp_trends_impl(pid)
    assert "test kw" in result
    assert "#3" in result


@pytest.mark.asyncio
async def test_serp_trends_no_data(tmp_db):
    """get_serp_trends returns 'no data' when empty."""
    from opencmo import storage
    from opencmo.tools.serp_tracker import _get_serp_trends_impl

    pid = await storage.ensure_project("Test", "https://example.com", "saas")
    result = await _get_serp_trends_impl(pid)
    assert "No tracked keywords" in result


@pytest.mark.asyncio
async def test_track_project_keywords_derives_domain(tmp_db):
    """track_project_keywords uses domain from project.url."""
    from opencmo import storage
    from opencmo.tools.serp_tracker import track_project_keywords

    pid = await storage.ensure_project("Test", "https://www.example.com/path", "saas")
    await storage.add_tracked_keyword(pid, "test")

    with patch("opencmo.tools.serp_tracker._check_ranking") as mock_check:
        from opencmo.tools.serp_tracker import SerpResult

        mock_check.return_value = SerpResult(
            position=1, url_found="https://example.com", total_results=10, provider="crawl", error=None
        )
        await track_project_keywords(pid)

        # Should have called with domain derived from www.example.com → example.com
        mock_check.assert_called_once_with("test", "example.com")


def test_get_active_provider_default():
    """Default provider is CrawlSerpProvider."""
    from opencmo.tools.serp_tracker import _get_active_provider

    provider = _get_active_provider()
    assert provider.name == "crawl"


def test_dataforseo_provider_stub_is_never_enabled(monkeypatch):
    """DataForSeoProvider remains a visible stub, not an active provider."""
    from opencmo.tools.serp_tracker import DataForSeoProvider

    monkeypatch.setenv("DATAFORSEO_LOGIN", "test")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "test")
    provider = DataForSeoProvider()
    assert provider.status == "stub"
    assert not provider.is_enabled


def test_dataforseo_stub_does_not_preempt_active_provider(monkeypatch):
    """DataForSeoProvider should not win provider resolution while it is a stub."""
    from opencmo.tools import serp_tracker
    from opencmo.tools.serp_tracker import DataForSeoProvider

    class FakeCrawlProvider:
        name = "crawl"

        @property
        def is_enabled(self):
            return True

    monkeypatch.setenv("DATAFORSEO_LOGIN", "test")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "test")
    monkeypatch.setattr(
        serp_tracker,
        "SERP_PROVIDER_REGISTRY",
        [DataForSeoProvider(), FakeCrawlProvider()],
    )

    provider = serp_tracker._get_active_provider()
    assert provider.name == "crawl"


def test_tavily_provider_client_uses_current_byok_key(monkeypatch):
    """Tavily client should be created from the current ContextVar key, not ambient env."""
    from opencmo import llm
    from opencmo.tools.serp_tracker import TavilySerpProvider

    keys: list[str] = []

    class FakeTavilyClient:
        def __init__(self, api_key):
            keys.append(api_key)

    monkeypatch.setitem(sys.modules, "tavily", SimpleNamespace(AsyncTavilyClient=FakeTavilyClient))
    provider = TavilySerpProvider()

    token = llm.set_request_keys({"TAVILY_API_KEY": "byok-1"})
    try:
        provider._get_client(llm.get_key("TAVILY_API_KEY", ""))
    finally:
        llm.reset_request_keys(token)

    token = llm.set_request_keys({"TAVILY_API_KEY": "byok-2"})
    try:
        provider._get_client(llm.get_key("TAVILY_API_KEY", ""))
    finally:
        llm.reset_request_keys(token)

    assert keys == ["byok-1", "byok-2"]


@pytest.mark.asyncio
async def test_cloro_provider_ranking(monkeypatch):
    """cloro SERP provider reads organicResults and skips empty and /goto links."""
    from opencmo import llm
    from opencmo.tools.serp_tracker import CloroSerpProvider

    payload = {
        "success": True,
        "result": {
            "organicResults": [
                {"position": 1, "title": "Other", "link": "https://competitor.com/a"},
                {"position": 2, "title": "Redirect", "link": "https://www.google.com/goto?url=CAESZw"},
                {"position": 3, "title": "Empty", "link": ""},
                {"position": 4, "title": "Ours", "link": "https://www.example.com/page"},
            ],
            "peopleAlsoAsk": [],
            "relatedSearches": [],
        },
    }
    calls: list = []

    class FakeResponse:
        status_code = 200

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

    token = llm.set_request_keys({"CLORO_API_KEY": "byok-cloro"})
    try:
        with patch("httpx.AsyncClient", FakeClient):
            provider = CloroSerpProvider()
            assert provider.is_enabled
            result = await provider.check_ranking("web scraping", "example.com", num_results=20)
    finally:
        llm.reset_request_keys(token)

    assert calls[0]["url"] == "https://api.cloro.dev/v1/monitor/google"
    assert calls[0]["json"] == {"query": "web scraping", "country": "US", "pages": 2}
    assert result.position == 4
    assert result.url_found == "https://www.example.com/page"
    assert result.total_results == 2
    assert result.error is None


def test_cloro_provider_disabled_without_key():
    from opencmo.tools.serp_tracker import CloroSerpProvider

    assert not CloroSerpProvider().is_enabled
