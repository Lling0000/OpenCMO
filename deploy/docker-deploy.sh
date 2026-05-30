#!/usr/bin/env bash
# deploy/docker-deploy.sh — push the current working tree to newyork and
# (re)build the Docker container in place.
#
# Usage:
#   ./deploy/docker-deploy.sh                    # build + restart
#   ./deploy/docker-deploy.sh --no-build         # restart only (config-only change)
#   ./deploy/docker-deploy.sh --logs             # tail logs after deploy
#
# Pre-requisites on the server (one-time):
#   - Docker + Docker Compose plugin installed
#   - /opt/OpenCMO/.env populated with provider keys (copy from the legacy
#     systemd setup if migrating)
#   - /opt/OpenCMO/data/ directory exists (or symlink to a backup location)
#
# Pre-requisites locally:
#   - `ssh newyork ...` works (key auth, the alias resolves to root@192.3.16.77)

set -euo pipefail

HOST="${OPENCMO_DEPLOY_HOST:-newyork}"
REMOTE_DIR="${OPENCMO_DEPLOY_DIR:-/opt/OpenCMO}"
DO_BUILD=1
TAIL_LOGS=0

for arg in "$@"; do
  case "$arg" in
    --no-build) DO_BUILD=0 ;;
    --logs)     TAIL_LOGS=1 ;;
    -h|--help)
      sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
echo "→ syncing $ROOT → $HOST:$REMOTE_DIR"

# Exclude everything the container builds for itself, plus host-only state
# (venv, node_modules, the host's ./data dir which we never want to overwrite),
# plus the on-server secrets (`.env`) which are gitignored locally and would
# otherwise be wiped by `--delete`.
rsync -avz --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'frontend/dist/' \
  --exclude 'data/' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '.DS_Store' \
  --exclude '.claude/' \
  ./ "$HOST:$REMOTE_DIR/"

REMOTE_CMD=""
if [ "$DO_BUILD" -eq 1 ]; then
  echo "→ building image on $HOST"
  REMOTE_CMD="cd $REMOTE_DIR && docker compose build && docker compose up -d"
else
  echo "→ restarting container on $HOST (no rebuild)"
  REMOTE_CMD="cd $REMOTE_DIR && docker compose up -d"
fi

# `docker compose up -d` is idempotent: it recreates the container only if
# config/image changed. So a `--no-build` invocation after a config-only
# change is the fastest path back to a clean container.
ssh "$HOST" "$REMOTE_CMD"

echo "→ verifying health"
# Give uvicorn a beat to bind + serve. Retry rather than sleep-and-pray.
for i in 1 2 3 4 5 6 7 8 9 10; do
  if ssh "$HOST" "curl -fsS http://127.0.0.1:8081/api/v1/health >/dev/null"; then
    echo "✓ healthy after ${i} attempt(s)"
    break
  fi
  if [ "$i" -eq 10 ]; then
    echo "✗ never became healthy — dumping last 60 log lines:" >&2
    ssh "$HOST" "cd $REMOTE_DIR && docker compose logs --tail=60 opencmo" >&2 || true
    exit 1
  fi
  sleep 2
done

echo "→ done. Public probe:"
curl -sS -o /dev/null -w "  https://www.aidcmo.com/app/ → HTTP %{http_code}\n" -L https://www.aidcmo.com/app/

if [ "$TAIL_LOGS" -eq 1 ]; then
  ssh "$HOST" "cd $REMOTE_DIR && docker compose logs -f --tail=50 opencmo"
fi
