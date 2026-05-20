"""Ad-hoc GEO query — run a single user-supplied query across selected providers."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from opencmo.tools.geo_providers import (
    GEO_PROVIDER_REGISTRY,
    GeoProvider,
    GeoProviderResult,
    _looks_cjk,
    get_enabled_providers,
    reset_brand_aliases,
    set_brand_aliases,
)


@dataclass
class GeoAskPlatformResult:
    platform: str
    mentioned: bool
    mention_count: int
    position_pct: float | None
    content_snippet: str
    source_status: str
    error: str | None
    duration_ms: int


@dataclass
class GeoAskResponse:
    query: str
    results: list[GeoAskPlatformResult]
    total_duration_ms: int
    query_lang: str  # "en" | "zh"


def _select_providers(platform_names: list[str] | None) -> tuple[list[GeoProvider], list[str]]:
    """Return (selected_providers, unknown_names).

    If platform_names is None or empty → return all enabled providers.
    Else filter by name; unknown names are returned so the caller can 404.
    """
    enabled = get_enabled_providers()
    if not platform_names:
        return enabled, []
    enabled_by_name = {p.name: p for p in enabled}
    case_map = {p.name.lower(): p for p in enabled}
    selected: list[GeoProvider] = []
    unknown: list[str] = []
    seen: set[str] = set()
    for name in platform_names:
        if not isinstance(name, str):
            unknown.append(str(name))
            continue
        normalized = name.strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        prov = enabled_by_name.get(normalized) or case_map.get(key)
        if prov is None:
            unknown.append(normalized)
        else:
            selected.append(prov)
    return selected, unknown


async def ask_platforms(
    brand_name: str,
    query: str,
    platform_names: list[str] | None = None,
    aliases: list[str] | None = None,
) -> GeoAskResponse:
    """Run one query across selected (or all enabled) providers in parallel."""
    providers, unknown = _select_providers(platform_names)
    if unknown:
        raise ValueError(f"Unknown platforms: {unknown}")

    start = time.perf_counter()
    aliases_token = set_brand_aliases(aliases)
    try:
        async def _run_one(provider: GeoProvider) -> GeoAskPlatformResult:
            t0 = time.perf_counter()
            try:
                r: GeoProviderResult = await provider._check_single_query(brand_name, query)
                return GeoAskPlatformResult(
                    platform=r.platform,
                    mentioned=r.mentioned,
                    mention_count=r.mention_count,
                    position_pct=r.position_pct,
                    content_snippet=r.content_snippet or "",
                    source_status=r.source_status,
                    error=r.error,
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )
            except Exception as exc:
                return GeoAskPlatformResult(
                    platform=provider.name,
                    mentioned=False,
                    mention_count=0,
                    position_pct=None,
                    content_snippet="",
                    source_status="error",
                    error=str(exc),
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                )

        results = await asyncio.gather(*(_run_one(p) for p in providers))
    finally:
        reset_brand_aliases(aliases_token)

    total_ms = int((time.perf_counter() - start) * 1000)
    return GeoAskResponse(
        query=query,
        results=list(results),
        total_duration_ms=total_ms,
        query_lang="zh" if _looks_cjk(query) else "en",
    )


def list_available_platforms() -> list[dict]:
    """Return name + status snapshot for the UI's platform picker."""
    enabled_names = {p.name for p in get_enabled_providers()}
    return [
        {
            "name": p.name,
            "enabled": p.name in enabled_names,
            "requires_auth": p.requires_auth,
            "auth_env_vars": list(getattr(p, "auth_env_vars", []) or []),
        }
        for p in GEO_PROVIDER_REGISTRY
    ]
