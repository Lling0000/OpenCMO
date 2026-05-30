# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenCMO is an open-source AI Chief Marketing Officer — a multi-agent system for indie hackers and startups. It monitors SEO/GEO/SERP/Community metrics, generates platform-specific content, and visualizes competitive landscapes via an interactive 3D knowledge graph.

## Architecture

**Full-stack: Python backend + React TypeScript frontend**

- **Backend** (`src/opencmo/`): FastAPI + openai-agents framework, SQLite storage
- **Frontend** (`frontend/`): React 19 SPA with Vite, Tailwind CSS 4, TanStack Query, Three.js
- **Entry points**: `opencmo` (CLI chatbot), `opencmo-web` (web dashboard on port 8080)

### Backend layers

- `agents/cmo.py` — Orchestrator with 40+ tools; delegates to 25+ specialist agents via `agent.as_tool()`. Two routing strategies: single-platform handoff (deep interaction) vs multi-channel tool calls (collects all outputs via campaign runs)
- `agents/*.py` — Platform experts + intelligence agents. Each is a standalone `Agent()` with `name`, `instructions`, `tools`, and `model=get_model("agent_name")`
- `tools/*.py` — Crawling, search (WebSearchTool → Tavily fallback → crawl4ai scrape), SEO audit, SERP tracking, GEO detection, community scraping, publishing
- `service.py` — Business logic bridge used by both CLI and Web: monitor CRUD, multi-agent URL analysis (3-round debate → JSON strategy), competitor discovery, approval workflow
- `storage.py` — Async SQLite (WAL mode, foreign keys) with 27+ tables. No ORM — raw aiosqlite with dict rows. Schema auto-created; migrations via `ALTER TABLE` + try/except. DB path: `OPENCMO_DB_PATH` or `~/.opencmo/data.db`
- `web/app.py` — FastAPI routes: REST API at `/api/v1/`, SPA serving at `/app/`, SSE chat streaming. Token auth via Bearer header or cookie (public prefixes: `/static/`, `/api/v1/auth/`, `/api/v1/health`)
- `config.py` — Model resolution cascade: `OPENCMO_MODEL_{AGENT}` > `OPENCMO_MODEL_DEFAULT` > `'gpt-4o'`. Returns `OpenAIChatCompletionsModel` for custom `OPENAI_BASE_URL` providers. `apply_runtime_settings()` loads API keys from DB settings table into `os.environ`
- `scheduler.py` — APScheduler (optional dep, graceful fallback). `run_scheduled_scan()` executes SEO/GEO/Community/SERP independently, not through agent framework
- `graph_expansion.py` — Wave-based BFS discovery of competitors and keywords. Heartbeat-tracked (60s stale window), backpressure via `MAX_OPS_PER_WAVE=20`
- `web/task_registry.py` — In-memory (not persisted) OrderedDict, max 100 tasks. Wraps async scan workflows with progress tracking
- `web/chat_sessions.py` — SQLite-backed chat history. Auto-titling from first message. Max 20 messages per session (truncated)
- `reports.py` — Report generation with two audiences: `human` (6-phase pipeline) and `agent` (single LLM call). Data aggregation uses parallel `asyncio.gather()` for 14+ database queries
- `report_pipeline.py` — Multi-agent deep report pipeline (6 phases): Reflection → Insight Distiller → Outline Planner → Section Writers → Section Grader → Report Synthesizer. Uses `asyncio.Semaphore` to limit concurrent LLM calls (`_MAX_CONCURRENT_LLM_CALLS = 5`)
- `llm.py` — Centralized LLM client with per-request key isolation via ContextVar. Solves BYOK concurrency bug. Key resolution: ContextVar → os.environ → DB settings. Includes retry logic with exponential backoff
- `background/` — Background task queue system for long-running operations (scans, reports). Tasks have status tracking and progress events

### Frontend layers

- `pages/` — Route-level components (Dashboard, SEO, GEO, SERP, Community, Graph, Chat, Approvals, Monitors)
- `components/` — Organized by domain: `charts/` (recharts + react-force-graph-3d), `chat/` (SSE streaming), `monitors/`, `auth/`, `layout/`, `dashboard/`, `project/`
- `hooks/` — TanStack Query hooks per domain (`useProjects`, `useSeoData`, `useGraphData`, etc.). Stale time 30s, retry 1. `useChat` manages local state + SSE via async generator
- `api/client.ts` — `apiFetch()` adds Bearer token, dispatches `opencmo:unauthorized` on 401. Domain modules export typed wrappers around `apiJson()`
- `i18n/` — React context-based EN/ZH/JA/KO/ES translations
- Routing: React Router v7 at base `/app`. Provider stack: QueryClient → I18n → Auth → Router

### Key patterns

- **Agent tool vs handoff**: `.as_tool()` returns output to orchestrator; `handoff()` transfers control for direct user conversation
- **Optional deps with graceful fallback**: scheduler, web, publish, geo-premium, tavily all degrade gracefully if not installed
- **SSE chat protocol**: `POST /api/v1/chat` streams events — `delta` (text), `agent` (handoff), `tool_called`, `tool_output`, `final_output`
- **Provider-adaptive search**: Native WebSearchTool for OpenAI, Tavily if key present, crawl4ai Google scrape as last resort
- **Approval-first publishing**: Content queued with exact payload for human review; publish only after explicit approve. `OPENCMO_AUTO_PUBLISH=1` gates actual API calls
- **Settings table as runtime config**: Web UI settings panel writes to SQLite KV store; `apply_runtime_settings()` loads them into env vars at startup
- **Custom provider compatibility**: Disables OpenAI tracing for non-OpenAI providers to avoid 401 noise
- **Frontend proxies `/api` to `http://127.0.0.1:8080` in dev (vite.config.ts)
- **Report generation optimization**: Data aggregation parallelized with `asyncio.gather()`. LLM concurrency limited to 5 simultaneous calls via `asyncio.Semaphore`. Grader threshold at 3.5/5.0 with max 1 retry to balance quality and speed
- **BYOK (Bring Your Own Key)**: Per-request API keys isolated via ContextVar in `llm.py`. Never use `os.environ` for request-scoped keys to avoid concurrency bugs

## Commands

### Setup

```bash
pip install -e ".[all]"   # Install with all optional deps
crawl4ai-setup             # Initialize crawler (required once)
cp .env.example .env       # Configure API keys
```

### Backend

```bash
opencmo                    # Interactive CLI chatbot
opencmo-web                # Web dashboard (http://localhost:8080/app)
```

### Frontend

```bash
cd frontend
npm install
npm run dev                # Dev server at localhost:5173
npm run build              # Production build (tsc -b && vite build)
```

### Tests

```bash
pytest tests/              # Run all tests
pytest tests/test_web.py   # Run single test file
pytest tests/ -k "test_seo" # Run tests matching pattern
```

Tests use temp SQLite DBs (via `tmp_path`), reset in-memory state (task registry, chat sessions), and mock all external APIs. No real API integration tests.

## Environment Variables

Required: `OPENAI_API_KEY` (or equivalent for chosen provider)

Key optional variables — see `.env.example` for full list:
- `OPENCMO_MODEL_DEFAULT` / `OPENCMO_MODEL_{AGENT}` — model selection (cascade: per-agent > default > gpt-4o)
- `OPENAI_BASE_URL` — custom API provider (NVIDIA, DeepSeek, Ollama, etc.)
- `OPENCMO_DB_PATH` — SQLite database location (default: `~/.opencmo/data.db`)
- `OPENCMO_WEB_TOKEN` — dashboard auth token
- `ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY` — extended GEO platforms
- `TAVILY_API_KEY` — structured web search
- `DATAFORSEO_LOGIN/PASSWORD` — SERP tracking
- `OPENCMO_AUTO_PUBLISH=1` + Reddit/Twitter credentials — auto-publishing
- `OPENCMO_SMTP_*` + `OPENCMO_REPORT_EMAIL` — email reports

## Performance Optimization Guidelines

When optimizing report generation or other LLM-heavy workflows:

1. **Always parallelize independent operations** — Use `asyncio.gather()` for database queries and LLM calls that don't depend on each other
2. **Limit concurrent LLM calls** — Use `asyncio.Semaphore` to prevent API rate limiting (current limit: 5 concurrent calls in `report_pipeline.py`)
3. **Never hardcode API credentials in test scripts** — Use environment variables or `.env` files. Test scripts with hardcoded keys must never be committed
4. **Benchmark before and after** — Measure timing for each phase to validate optimizations. Track both performance and quality metrics (report length, section count, pass rate)
5. **Balance quality and speed** — Grader thresholds and retry counts directly impact both. Current settings: `_GRADER_PASS_THRESHOLD = 3.5`, `_MAX_GRADER_RETRIES = 1`

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
- **Browser-backed scans**: SEO/context fallback paths use `crawl4ai`/Playwright. The Docker image installs the Chromium binary during build (`playwright install --with-deps chromium`), so containers work out of the box. For the legacy systemd path, fresh servers need `playwright install chromium` manually or scans fail with `BrowserType.launch` executable errors.
- **Deployment**: Production runs in Docker. The host runs `docker compose up -d` from `/opt/OpenCMO`; the legacy systemd unit (`opencmo.service`) is disabled but left in place for rollback. See `docs/DOCKER.md` for the full migration story.
- **Local testing**: Don't `npm run dev` / `opencmo-web` locally for verification. The user's laptop is not the deployment target and the local environment doesn't mirror production. Verify on `newyork` via SSH + curl. Local `npm run build` and `pytest` are fine (no runtime dependency on prod topology).

## Deployment (newyork — aidcmo.com)

### Default path: Docker

```bash
./deploy/docker-deploy.sh                 # rsync + docker compose build + up -d + health probe
./deploy/docker-deploy.sh --no-build      # config-only change (skip image rebuild)
./deploy/docker-deploy.sh --logs          # tail container logs after deploy
```

Manual equivalent:

```bash
# Sync source (excludes data/, .env, frontend/dist — those live on the server)
rsync -avz --delete \
  --exclude '.git' --exclude '.venv' \
  --exclude 'frontend/node_modules' --exclude 'frontend/dist' \
  --exclude 'data/' --exclude '.env' --exclude '.env.*' \
  ./ root@192.3.16.77:/opt/OpenCMO/

ssh newyork "cd /opt/OpenCMO && docker compose up -d --build"
```

### Health + log checks

```bash
ssh newyork "cd /opt/OpenCMO && docker compose ps"          # container + (healthy) status
ssh newyork "cd /opt/OpenCMO && docker compose logs -f --tail=100 opencmo"
ssh newyork "ss -ltnp | grep -E ':80|:443|:8081'"           # nginx + container ports
curl -sL -o /dev/null -w '%{http_code}\n' https://www.aidcmo.com/app/
```

### Rollback to systemd (emergency only)

```bash
ssh newyork "cd /opt/OpenCMO && docker compose down && systemctl enable --now opencmo"
# Nginx upstream is unchanged (127.0.0.1:8081) so traffic resumes instantly.
# DB: container reads /opt/OpenCMO/data/data.db; systemd reads ~/.opencmo/data.db.
# If the schema migrated forward under Docker, `cp /opt/OpenCMO/data/data.db ~/.opencmo/data.db` before starting systemd.
```

### Legacy frontend-only deploy (still valid for tiny UI tweaks)

The Docker image bakes the frontend in at build time. To ship UI changes without a full image rebuild you can still rsync the bundle into the container's build context and rebuild:

```bash
cd frontend && npm run build
rsync -avz --delete frontend/dist/ root@192.3.16.77:/opt/OpenCMO/frontend/dist/
ssh newyork "cd /opt/OpenCMO && docker compose up -d --build"
```

### BWG (optional fallback / proxy only)

```bash
ssh bwg "systemctl status nginx --no-pager"
```

## Coding Conventions

- **Python**: snake_case, 4-space indent, type hints where useful, line length 120 (ruff)
- **TypeScript**: strict mode, PascalCase components, useX hooks, double quotes
- **Commits**: `feat:` / `fix:` / `docs:` prefix, short imperative subject
- **i18n**: All user-facing strings via translation keys (EN/ZH/JA/KO/ES). Never hardcode.
- **Secrets**: `.env` or settings UI only. Never commit API keys or `.db` files.
