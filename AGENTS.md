# AGENTS.md

## Repository ownership and GitHub identity

- Current repository owner and maintainer: **Ling (`Lling0000`)**.
- Canonical repository: **https://github.com/Lling0000/OpenCMO**. Use this owner for GitHub API calls, issues, PRs, badges, source links and GitHub statistics.
- This checkout is intentionally operated with the `Lling0000` GitHub account. When working under `/Users/fanjingwen/Projects/Lling0000`, use that directory's `.gh-config`, not the default GitHub account. Source `../use-gh.sh` from this repo before Git/GitHub operations, or invoke `../use-gh.sh <gh arguments>`.
- Commit identity for this checkout: `Lling0000 <263957495+Lling0000@users.noreply.github.com>`. Verify the active GitHub login and Git author before writing commits or PRs.
- The repository ownership and this account choice are established. Do not reopen ownership questions merely because older commits or historical contributor credits name another account.
- Preserve historical commits and individual contributor credit. Historical authorship does not change the current repository owner or maintainer.
- For complex tasks, use subagents with medium reasoning effort.

## Architecture at a Glance

See [architecture.md](docs/architecture.md) for the component diagram, runtime boundaries and data flows, and [optimization-review.md](docs/optimization-review.md) for implemented improvements and remaining priorities.

```
Frontend (React 19 + Vite)  ←→  FastAPI /api/v1/  ←→  SQLite (WAL)
                                      ↓
                              Background Worker
                                      ↓
                    ┌─────── 6-Stage Monitoring Pipeline ───────┐
                    │ 1. Context Build (crawl + 3-role AI debate)│
                    │ 2. Signal Collect (SEO/GEO/Community/SERP) │
                    │ 3. Signal Normalize                        │
                    │ 4. Domain Review (4 AI analysts)           │
                    │ 5. Strategy Synthesis                      │
                    │ 6. Persist & Publish                       │
                    └────────────────────────────────────────────┘
```

## Phase 1 Repositioning (2026-04-28)

The public site (`aidcmo.com`) has been repositioned from **"B2B email leads + SEO/GEO services"** to **"open-source AI growth tools, audits delivered by humans"**. Branch: `feat/repositioning-phase-1` (commit `17d9208`).

### What changed

- **Public routes**: `/services` (skeleton) + `/hosted` (waitlist) are new. The old `/b2b-leads`, `/sample-data`, `/data-policy`, `/seo-geo` routes are **deleted from the SPA** and 301-redirected server-side (locale-preserving, GET + HEAD).
- **`PublicServicePage` kinds reduced from 6 → 2**: only `open-source` and `contact` remain. Type union narrowed in `frontend/src/pages/PublicServicePage.tsx`.
- **i18n**: `service.b2b.*`, `service.sample.*`, `service.policy.*`, `service.seoGeo.*` namespaces deleted across 5 locales. New: `landing.builtInOpen.*`, `landing.hosted.*`, `service.audit.*`. `landing.hero*` / `landing.meta*` rewritten. ja/ko/es rely on auto EN-fallback (no new keys added there).
- **Path helpers** in `frontend/src/content/marketing.ts`: `getB2BLeadsPath` / `getSampleDataPath` / `getDataPolicyPath` / `getSeoGeoPath` are now `@deprecated` wrappers that return `/services` or `/`. Slated for removal once any remaining callers in non-marketing surfaces are gone (grep `getB2B|getSampleData|getDataPolicy|getSeoGeo`).
- **`PublicSiteHeader` primary CTA**: target switched from `/sample-data` → `/services`.
- **Server-side SEO** (`web/app.py`): `_HOME_STATIC_SITE_COPY_BY_LOCALE`, `_SERVICE_PAGE_METADATA_BY_PATH`, `_build_home_json_ld`, and home-route metadata literals all rewritten. `frontend/public/sitemap.xml` and `llms.txt` cleaned.

### New schema (registered in `_SCHEMA` constant in `storage/_db.py`)

```sql
CREATE TABLE waitlist (
    email TEXT PRIMARY KEY, source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE github_stats_cache (
    key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at REAL NOT NULL
);
```

### New endpoints (registered inline in `web/app.py` before the SPA catch-all)

- `POST /api/v1/waitlist` — `{ email, source? }`. Pydantic `Literal["home_inline","hosted_page"]` for source. Helper layer in `storage/waitlist.py`.
- `GET /api/v1/github-stats` — returns `{ stars, contributors, last_commit_iso, fetched_at }`. Cache: L1 in-process memory + L2 SQLite, both 24h TTL, `asyncio.Lock` single-flight. Implementation: `web/github_stats.py`. Uses public wrappers `get_github_token()` and `github_get_with_headers()` in `tools/github_api.py` (the existing `_github_get` keeps its raise-on-error contract; new public wrapper swallows failures and returns `(None, headers)`).
- **No app-layer rate limit** on `/waitlist`; nginx `limit_req zone=waitlist rate=5r/m burst=3` is the gate (must be configured at deploy time — see Phase 2 follow-ups).

### New marketing components / pages

- `frontend/src/components/marketing/BuiltInOpen.tsx` — GitHub stats card. **Strict null-fallback**: any one of `stars`/`contributors`/`last_commit_iso` is null → render fallback link only.
- `frontend/src/components/marketing/HostedWaitlist.tsx` — email form, two variants (`inline` for home page, `page` for `/hosted`). variant ↔ source mapping enforced.
- `frontend/src/pages/ServicesPage.tsx` — Phase 1 skeleton (hero + CTA + placeholder note). Phase 2 will expand to 7-section IA per `new-positioning.md` § 1.2.
- `frontend/src/pages/HostedWaitlistPage.tsx` — wraps `HostedWaitlist` with `variant="page"`.

### 301 redirect map (`web/app.py`, before catch-all line ~1380)

```
/b2b-leads      → /services       (locale-preserved: /en/services, /zh/services)
/sample-data    → /services
/data-policy    → /                (locale-preserved: /en, /zh)
/seo-geo        → /services
```

12 routes total (4 paths × 3 locales). Both GET and HEAD methods. Factory function `_make_redirect(target)` avoids closure late-binding. Tests in `tests/test_redirects.py`.

### Phase 2 follow-ups (not yet done)

- Configure nginx `limit_req` for `/api/v1/waitlist` on newyork (snippet documented in `implementation-plan.md` §D.1.5; not yet applied to live nginx config).
- Manual batch email when hosted version ships: `SELECT email FROM waitlist;`. **Before sending**: configure SPF / DKIM / DMARC on aidcmo.com (`implementation-plan.md` §F.4 checklist).
- Translate ja/ko/es properly (currently EN-fallback for all repositioning copy).
- Expand `/services` from skeleton to full 7-section IA.
- Delete the 4 deprecated path helpers in `marketing.ts` once external link audits confirm zero remaining callers.
- Real social-proof quotes (Linux.do / HN / X) — only when user supplies source URLs.

### Reference docs (uncommitted yet — see branch root)

- `current-state.md` — pre-Phase-1 [WORKS]/[STUB]/[MISSING] code audit.
- `new-positioning.md` — locked hero / meta / footer copy + 19 decisions.
- `implementation-plan.md` — full B.0 - B.9 + tests + deploy steps after 3 Codex review rounds.

---

## Key Directories

| Path | Role |
|------|------|
| `src/opencmo/agents/` | 25+ specialist agents (CMO orchestrator + platform experts). Names must be ASCII — no Chinese. |
| `src/opencmo/tools/` | Crawl, search, SEO audit, GEO detection, community providers, SERP tracking |
| `src/opencmo/services/` | Domain services: intelligence (AI debate), approval, monitoring |
| `src/opencmo/background/` | Worker + executor registry (scan, report, graph expansion) |
| `src/opencmo/rag/` | Account/project knowledge ingestion, hybrid retrieval, context budgets and source citations. |
| `src/opencmo/storage/` | Async SQLite, 30+ tables, no ORM |
| `src/opencmo/web/` | FastAPI app, routers, SSE chat, BYOK middleware |
| `src/opencmo/llm.py` | Centralized LLM client: ContextVar isolation, retry + backoff, model resolution |
| `frontend/src/` | React SPA: pages/, components/, hooks/ (TanStack Query), api/, i18n/ (EN/ZH/JA/KO/ES) |

## Critical Patterns

- **LLM calls**: Always use `llm.chat_completion_messages()` for retry. Never call `client.chat.completions.create()` directly.
- **Agent names**: ASCII only (`Zhihu Expert`, not `知乎专家`). openai-agents generates `transfer_to_{name}` tool names.
- **Timestamps**: SQLite stores UTC. Frontend must use `utcDate()` from `utils/time.ts` to parse.
- **Community search**: Tavily → crawl4ai Google scrape fallback. Skip category queries when category is placeholder `"auto"`.
- **BYOK**: Per-request API keys via `X-User-Keys` header → ContextVar. Background tasks capture and restore keys.
- **SPA routing**: No `AnimatePresence key={pathname}` in AppShell — causes full remount and breaks query cache.
- **Production topology**: Primary production is `newyork` (`192.3.16.77`). OpenCMO runs behind nginx on `80/443`, proxied to local `127.0.0.1:8081`. Nginx config: `/etc/nginx/sites-enabled/aidcmo.conf`.
- **Nginx security headers**: `Strict-Transport-Security` + `X-Frame-Options: DENY` configured in `aidcmo.conf`.
- **Port allocation**: Do not assume production app port is `8080`. `8080` is occupied by `sub2api` on `newyork`; OpenCMO uses `8081`.
- **BWG role**: `BWG` is no longer the primary OpenCMO host. Treat it as a lightweight box, temporary reverse proxy, or fallback node unless explicitly re-promoted.
- **Browser-backed scans**: SEO/context fallback paths use `crawl4ai`/Playwright. Fresh servers need browser binaries installed, or scans will fail with `BrowserType.launch` executable errors.

## Commands

```bash
# Backend
pip install -e ".[all]"        # Install
opencmo-web                    # Run locally (port 8080 by default)
pytest tests/                  # Test
ruff check src/ tests/         # Lint

# Frontend
cd frontend && npm install
npm run dev                    # Dev (port 5173, proxies /api → 8080)
npm run build                  # Prod build

# Deploy frontend assets to New York
cd frontend && npm run build   # Build locally (avoid server-side frontend builds)
rsync -avz --delete frontend/dist/ root@192.3.16.77:/opt/OpenCMO/frontend/dist/

# Deploy backend code to New York
rsync -avz --delete \
  --exclude '.git' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' \
  --exclude '.venv' \
  ./ root@192.3.16.77:/opt/OpenCMO/
ssh newyork "cd /opt/OpenCMO && source .venv/bin/activate && pip install -e . -q && systemctl restart opencmo"

# New York service / runtime checks
ssh newyork "systemctl status opencmo --no-pager"
ssh newyork "journalctl -u opencmo -n 200 --no-pager"
ssh newyork "ss -ltnp | grep -E ':80|:443|:8081'"

# Install Playwright browsers on New York when scan workers need them
ssh newyork "cd /opt/OpenCMO && .venv/bin/playwright install chromium"

# BWG is optional fallback / proxy only
ssh bwg "systemctl status nginx --no-pager"
```

## Coding Conventions

- **Python**: snake_case, 4-space indent, type hints where useful, line length 120 (ruff)
- **TypeScript**: strict mode, PascalCase components, useX hooks, double quotes
- **Commits**: `feat:` / `fix:` / `docs:` prefix, short imperative subject
- **i18n**: All user-facing strings via translation keys (EN/ZH/JA/KO/ES). Never hardcode.
- **Secrets**: `.env` or settings UI only. Never commit API keys or `.db` files.
