"""Tests for ad-hoc GEO query tooling and routes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from opencmo import storage
from opencmo.tools import geo_ask, geo_providers
from opencmo.tools.geo_ask import (
    GeoAskResponse,
    _select_providers,
    ask_platforms,
    list_available_platforms,
)
from opencmo.tools.geo_providers import GeoProvider, GeoProviderResult

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from opencmo.web.app import app

# ---------------------------------------------------------------------------
# Helpers — stub providers we can drop into the registry for deterministic tests
# ---------------------------------------------------------------------------


class _StubProvider(GeoProvider):
    """Minimal provider whose _check_single_query returns a fixed result."""

    status = "enabled"
    requires_auth = False
    auth_env_vars: list[str] = []

    def __init__(self, name: str, result: GeoProviderResult | None = None, exc: Exception | None = None):
        self.name = name
        self._result = result
        self._exc = exc
        self.last_brand: str | None = None
        self.last_query: str | None = None
        self.last_aliases: list[str] | None = None

    @property
    def is_enabled(self) -> bool:
        return True

    def provider_identity(self) -> tuple:
        return ("stub", self.name)

    async def check_visibility(self, brand_name: str, category: str) -> GeoProviderResult:
        return await self._check_single_query(brand_name, "stub query")

    async def _check_single_query(self, brand_name: str, query: str) -> GeoProviderResult:
        self.last_brand = brand_name
        self.last_query = query
        self.last_aliases = geo_providers._current_aliases()
        if self._exc is not None:
            raise self._exc
        return self._result  # type: ignore[return-value]


def _make_result(name: str, *, mentioned: bool = True, snippet: str = "hi") -> GeoProviderResult:
    return GeoProviderResult(
        platform=name,
        mentioned=mentioned,
        mention_count=1 if mentioned else 0,
        position_pct=12.5 if mentioned else None,
        content_snippet=snippet,
        error=None,
        query="anything",
        source_status="ok",
    )


@pytest.fixture
def stub_registry(monkeypatch):
    """Replace the global registry with a list we control per-test."""
    registry: list[GeoProvider] = []
    monkeypatch.setattr(geo_providers, "GEO_PROVIDER_REGISTRY", registry)
    monkeypatch.setattr(geo_ask, "GEO_PROVIDER_REGISTRY", registry)
    return registry


# ---------------------------------------------------------------------------
# ask_platforms — happy path / error capture / parallelism
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_provider_success(stub_registry):
    stub = _StubProvider("StubA", result=_make_result("StubA", snippet="found it"))
    stub_registry.append(stub)

    response = await ask_platforms("BrandX", "where to find?")
    assert isinstance(response, GeoAskResponse)
    assert response.query == "where to find?"
    assert len(response.results) == 1
    res = response.results[0]
    assert res.platform == "StubA"
    assert res.mentioned is True
    assert res.mention_count == 1
    assert res.position_pct == 12.5
    assert res.content_snippet == "found it"
    assert res.source_status == "ok"
    assert res.error is None
    assert res.duration_ms >= 0
    assert stub.last_brand == "BrandX"
    assert stub.last_query == "where to find?"


@pytest.mark.asyncio
async def test_provider_exception_captured(stub_registry):
    bad = _StubProvider("BadProv", exc=RuntimeError("kaboom"))
    stub_registry.append(bad)

    response = await ask_platforms("BrandX", "q")
    assert len(response.results) == 1
    res = response.results[0]
    assert res.platform == "BadProv"
    assert res.source_status == "error"
    assert res.error is not None and "kaboom" in res.error
    assert res.mentioned is False


@pytest.mark.asyncio
async def test_multiple_providers_run_in_parallel(stub_registry):
    a = _StubProvider("StubA", result=_make_result("StubA"))
    b = _StubProvider("StubB", result=_make_result("StubB", mentioned=False))
    stub_registry.extend([a, b])

    response = await ask_platforms("BrandX", "q")
    platforms = {r.platform for r in response.results}
    assert platforms == {"StubA", "StubB"}
    assert response.total_duration_ms >= 0


@pytest.mark.asyncio
async def test_unknown_platform_raises_value_error(stub_registry):
    stub_registry.append(_StubProvider("StubA", result=_make_result("StubA")))
    with pytest.raises(ValueError) as exc:
        await ask_platforms("BrandX", "q", platform_names=["DoesNotExist"])
    assert "DoesNotExist" in str(exc.value)


@pytest.mark.asyncio
async def test_aliases_propagated_via_contextvar(stub_registry):
    stub = _StubProvider("StubA", result=_make_result("StubA"))
    stub_registry.append(stub)

    pre_token = geo_providers.set_brand_aliases(["sentinel-before"])
    try:
        await ask_platforms("BrandX", "q", aliases=["alpha", "beta"])
        # Inside the call, the provider should have observed the aliases we passed in.
        assert stub.last_aliases == ["alpha", "beta"]
        # ask_platforms must restore the prior aliases before returning.
        assert geo_providers._current_aliases() == ["sentinel-before"]
    finally:
        geo_providers.reset_brand_aliases(pre_token)


@pytest.mark.asyncio
async def test_query_lang_detection(stub_registry):
    stub_registry.append(_StubProvider("StubA", result=_make_result("StubA")))

    en = await ask_platforms("BrandX", "best web scraping tools")
    assert en.query_lang == "en"

    zh = await ask_platforms("BrandX", "有哪些好用的工具？")
    assert zh.query_lang == "zh"


# ---------------------------------------------------------------------------
# _select_providers / list_available_platforms
# ---------------------------------------------------------------------------


def test_select_providers_returns_all_when_none(stub_registry):
    stub_registry.extend([
        _StubProvider("StubA", result=_make_result("StubA")),
        _StubProvider("StubB", result=_make_result("StubB")),
    ])
    selected, unknown = _select_providers(None)
    assert {p.name for p in selected} == {"StubA", "StubB"}
    assert unknown == []


def test_select_providers_case_insensitive(stub_registry):
    stub_registry.append(_StubProvider("StubA", result=_make_result("StubA")))
    selected, unknown = _select_providers(["stuba"])
    assert [p.name for p in selected] == ["StubA"]
    assert unknown == []


def test_select_providers_reports_unknown(stub_registry):
    stub_registry.append(_StubProvider("StubA", result=_make_result("StubA")))
    selected, unknown = _select_providers(["StubA", "Nope"])
    assert [p.name for p in selected] == ["StubA"]
    assert unknown == ["Nope"]




def test_select_providers_deduplicates_case_insensitive(stub_registry):
    stub_registry.append(_StubProvider("StubA", result=_make_result("StubA")))
    selected, unknown = _select_providers(["StubA", "stuba", " StubA "])
    assert [p.name for p in selected] == ["StubA"]
    assert unknown == []


def test_select_providers_non_string_is_unknown(stub_registry):
    stub_registry.append(_StubProvider("StubA", result=_make_result("StubA")))
    selected, unknown = _select_providers(["StubA", 123])
    assert [p.name for p in selected] == ["StubA"]
    assert unknown == ["123"]
def test_list_available_platforms_reports_status(stub_registry):
    stub_registry.append(_StubProvider("StubA", result=_make_result("StubA")))
    items = list_available_platforms()
    assert len(items) == 1
    item = items[0]
    assert item["name"] == "StubA"
    assert item["enabled"] is True
    assert item["requires_auth"] is False
    assert item["auth_env_vars"] == []


# ---------------------------------------------------------------------------
# HTTP router tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test.db"
    with patch.object(storage, "_DB_PATH", db_path):
        with TestClient(app) as test_client:
            yield test_client


def _seed_project(brand: str = "Acme", url: str = "https://acme.test") -> int:
    return asyncio.run(storage.ensure_project(brand, url, "saas"))


def test_geo_platforms_endpoint_returns_list(client):
    pid = _seed_project()
    resp = client.get(f"/api/v1/projects/{pid}/geo/platforms")
    assert resp.status_code == 200
    body = resp.json()
    assert "platforms" in body
    names = {p["name"] for p in body["platforms"]}
    # The real registry should always contain at least Perplexity + the two new ones.
    assert {"Perplexity", "MetaSo", "360 AI"}.issubset(names)


def test_geo_platforms_endpoint_404(client):
    resp = client.get("/api/v1/projects/99999/geo/platforms")
    assert resp.status_code == 404


def test_geo_ask_endpoint_success(client):
    pid = _seed_project()
    fake_response = GeoAskResponse(
        query="hi",
        results=[],
        total_duration_ms=12,
        query_lang="en",
    )
    with patch(
        "opencmo.tools.geo_ask.ask_platforms",
        new=AsyncMock(return_value=fake_response),
    ):
        resp = client.post(
            f"/api/v1/projects/{pid}/geo/ask",
            json={"query": "hi", "platforms": ["Perplexity"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "hi"
    assert body["total_duration_ms"] == 12
    assert body["query_lang"] == "en"
    assert body["results"] == []


def test_geo_ask_endpoint_404(client):
    resp = client.post(
        "/api/v1/projects/99999/geo/ask",
        json={"query": "hi"},
    )
    assert resp.status_code == 404


def test_geo_ask_endpoint_empty_query(client):
    pid = _seed_project()
    resp = client.post(
        f"/api/v1/projects/{pid}/geo/ask",
        json={"query": "   "},
    )
    assert resp.status_code == 400
    assert "query" in resp.json()["error"]


def test_geo_ask_endpoint_invalid_json(client):
    pid = _seed_project()
    resp = client.post(
        f"/api/v1/projects/{pid}/geo/ask",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_geo_ask_endpoint_unknown_platform(client):
    pid = _seed_project()
    with patch(
        "opencmo.tools.geo_ask.ask_platforms",
        new=AsyncMock(side_effect=ValueError("Unknown platforms: ['Nope']")),
    ):
        resp = client.post(
            f"/api/v1/projects/{pid}/geo/ask",
            json={"query": "hi", "platforms": ["Nope"]},
        )
    assert resp.status_code == 400
    assert "Unknown platforms" in resp.json()["error"]


def test_geo_ask_endpoint_platforms_must_be_list(client):
    pid = _seed_project()
    resp = client.post(
        f"/api/v1/projects/{pid}/geo/ask",
        json={"query": "hi", "platforms": "not-a-list"},
    )
    assert resp.status_code == 400


def test_geo_ask_endpoint_platforms_max_entries(client):
    pid = _seed_project()
    resp = client.post(
        f"/api/v1/projects/{pid}/geo/ask",
        json={"query": "hi", "platforms": ["Perplexity"] * 21},
    )
    assert resp.status_code == 400
    assert "max 20" in resp.json()["error"]


def test_geo_ask_endpoint_platforms_must_be_non_empty_strings(client):
    pid = _seed_project()
    resp = client.post(
        f"/api/v1/projects/{pid}/geo/ask",
        json={"query": "hi", "platforms": ["Perplexity", "", 123]},
    )
    assert resp.status_code == 400
    assert "non-empty strings" in resp.json()["error"]


def test_geo_ask_endpoint_platforms_deduped_before_call(client):
    pid = _seed_project()
    fake_response = GeoAskResponse(query="hi", results=[], total_duration_ms=1, query_lang="en")
    with patch(
        "opencmo.tools.geo_ask.ask_platforms",
        new=AsyncMock(return_value=fake_response),
    ) as ask_mock:
        resp = client.post(
            f"/api/v1/projects/{pid}/geo/ask",
            json={"query": "hi", "platforms": ["Perplexity", "perplexity", "  Perplexity  "]},
        )
    assert resp.status_code == 200
    assert ask_mock.await_count == 1
    assert ask_mock.await_args.kwargs["platform_names"] == ["Perplexity"]
