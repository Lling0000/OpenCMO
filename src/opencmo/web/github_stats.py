"""Cached GitHub repo stats for the marketing site Built-in-open block.

Cache layers:
  L1 = in-process memory dict (avoids SQLite hit on hot path)
  L2 = SQLite ``github_stats_cache`` table (survives restarts)
  Both honor the same 24h TTL. asyncio.Lock prevents thundering herd
  when memory cold-starts and multiple requests race.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Optional, TypedDict

from opencmo.storage import get_cached_github_stats, set_cached_github_stats

# Note: ``get_github_token`` is NOT imported here — token resolution is
# done inside ``github_get_with_headers``. Importing it would trip Ruff F401.
from opencmo.tools.github_api import github_get_with_headers

_REPO = "Lling0000/OpenCMO"
_CACHE_KEY = f"repo:{_REPO}"
_CACHE_TTL_SEC = 24 * 3600

# L1: in-process memory.  Tuple = (epoch_seconds, payload).
_mem_cache: dict[str, tuple[float, dict]] = {}
# Single-flight lock: prevents N concurrent cold-start requests from
# all hitting GitHub simultaneously after deploy/restart.
_fetch_lock = asyncio.Lock()


class GitHubStats(TypedDict):
    stars: Optional[int]
    contributors: Optional[int]
    last_commit_iso: Optional[str]
    fetched_at: Optional[str]


def _empty_stats() -> GitHubStats:
    return {
        "stars": None,
        "contributors": None,
        "last_commit_iso": None,
        "fetched_at": None,
    }


def _read_mem(now: float) -> Optional[dict]:
    cached = _mem_cache.get(_CACHE_KEY)
    if cached and now - cached[0] < _CACHE_TTL_SEC:
        return cached[1]
    return None


async def _fetch_repo() -> Optional[dict]:
    """Returns the repo JSON, or None on any failure."""
    body, _headers = await github_get_with_headers(f"/repos/{_REPO}")
    if isinstance(body, dict):
        return body
    return None


async def _fetch_contributor_count() -> Optional[int]:
    """Parses contributor count from ``Link`` header rel='last'.

    Edge cases:
      * 0 contributors → API returns []; len → 0
      * 1 page (≤ per_page) → no Link header; len → actual count
      * Many pages → Link header present; rel='last' page number = count
    """
    body, headers = await github_get_with_headers(
        f"/repos/{_REPO}/contributors",
        params={"per_page": 1, "anon": "true"},
    )
    if body is None:
        return None
    link = headers.get("Link", "") or headers.get("link", "")
    for part in link.split(","):
        if 'rel="last"' in part:
            m = re.search(r"[?&]page=(\d+)", part)
            if m:
                return int(m.group(1))
    # No Link header → response body is the full list
    return len(body) if isinstance(body, list) else None


async def get_github_stats() -> GitHubStats:
    """Public entry. Returns fresh-or-cached stats, or empty on failure."""
    now = time.time()

    # L1 fast path
    cached = _read_mem(now)
    if cached is not None:
        return cached  # type: ignore[return-value]

    # Single-flight: only one fetcher at a time after cold start
    async with _fetch_lock:
        # Re-check L1 after acquiring lock (someone may have populated it)
        cached = _read_mem(now)
        if cached is not None:
            return cached  # type: ignore[return-value]

        # L2: SQLite cache (survives process restart)
        sqlite_cached = await get_cached_github_stats(_CACHE_KEY, _CACHE_TTL_SEC)
        if sqlite_cached is not None:
            _mem_cache[_CACHE_KEY] = (now, sqlite_cached)
            return sqlite_cached  # type: ignore[return-value]

        # Cold path: hit GitHub
        repo, contrib = await asyncio.gather(_fetch_repo(), _fetch_contributor_count())

        # Bugfix from Codex review: do NOT cache partial failures.
        # Spec (new-positioning.md): any API failure → return all-null
        # without poisoning the 24h cache window.
        if repo is None or contrib is None:
            return _empty_stats()

        stats: GitHubStats = {
            "stars": repo.get("stargazers_count"),
            "contributors": contrib,
            "last_commit_iso": repo.get("pushed_at"),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        }
        _mem_cache[_CACHE_KEY] = (now, stats)
        await set_cached_github_stats(_CACHE_KEY, dict(stats))
        return stats
