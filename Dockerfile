# syntax=docker/dockerfile:1.7

# ────────────────────────────────────────────────────────────────────────────
# Stage 1 — build the frontend bundle (Node 20, alpine for size)
# ────────────────────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Cache dependency layer separately from source. Use `npm ci` (lockfile-aware,
# reproducible) when the lockfile exists; fall back to `npm install` if it
# doesn't so the repo stays buildable without a commit-locked lockfile.
COPY frontend/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci --silent; else npm install --silent; fi

COPY frontend/ ./
RUN npm run build

# ────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python runtime + Playwright Chromium baked in
# ────────────────────────────────────────────────────────────────────────────
# Use a slim base. Playwright's Python package downloads its own browser
# binaries; we install OS-level deps separately and then download Chromium.
FROM python:3.12-slim AS runtime

# System packages: certificates for outbound TLS, curl for HEALTHCHECK,
# tini for proper PID-1 signal forwarding, and the libraries Chromium
# needs at runtime (added by `playwright install-deps`).
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps in a cache-friendly order: project metadata first
# (so requirement changes don't bust the source-copy layer), then source.
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the app with EVERY runtime extra plus the `browser` extra so that
# playwright is present for crawl4ai's scan fallback paths. The previous
# Dockerfile installed `[all]` which excludes `browser` — scans then crashed
# with "BrowserType.launch executable doesn't exist".
RUN pip install --no-cache-dir -e ".[all,browser]"

# Install Chromium + its OS-level deps in one go. `--with-deps` runs apt
# under the hood to add the missing shared libs (libnss3, libatk-1.0-0, …).
# This pulls ~280 MB but means every scan path works on a fresh container.
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Run crawl4ai's post-install (downloads its own models/templates). It
# previously had `|| true` which masked real failures — let it fail loudly.
RUN crawl4ai-setup

# Pull the pre-built frontend bundle from stage 1 into the location the
# FastAPI app serves static files from.
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Non-root user. Playwright stores its browser cache under HOME so we point
# it at the user's home and give the user ownership of /app and /data.
RUN useradd --create-home --shell /bin/bash --uid 1000 opencmo \
    && mkdir -p /data \
    && chown -R opencmo:opencmo /app /data \
    && cp -r /root/.cache/ms-playwright /home/opencmo/.cache/ms-playwright 2>/dev/null || true \
    && chown -R opencmo:opencmo /home/opencmo/.cache 2>/dev/null || true
USER opencmo

# Persistent state lives under /data. The default DB path matches.
VOLUME ["/data"]
ENV OPENCMO_DB_PATH=/data/data.db \
    OPENCMO_WEB_HOST=0.0.0.0 \
    OPENCMO_WEB_PORT=8081 \
    PLAYWRIGHT_BROWSERS_PATH=/home/opencmo/.cache/ms-playwright

EXPOSE 8081

# Healthcheck — same endpoint nginx-on-host probes when it hands off traffic.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${OPENCMO_WEB_PORT}/api/v1/health" || exit 1

# tini handles SIGTERM properly so `docker compose down` is fast and clean.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run uvicorn directly so the port is configurable via env. The `opencmo-web`
# console script hard-codes port=8080 in its signature, which is why we
# bypass it here.
CMD ["sh", "-c", "uvicorn opencmo.web.app:app --host ${OPENCMO_WEB_HOST} --port ${OPENCMO_WEB_PORT}"]
