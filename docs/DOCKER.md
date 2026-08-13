# Docker deployment

OpenCMO ships as a single Docker container designed to slot in behind an
existing nginx-on-host TLS terminator. This is the recommended deployment
path; the legacy `rsync + systemd + venv` flow is kept around only as a
rollback target.

## What's in the image

- Python 3.12-slim base
- All optional extras installed (`opencmo[all,browser]`) — including
  `playwright` so crawl4ai's scan fallback paths work without a separate
  `playwright install` on the host
- Chromium browser baked in via `playwright install --with-deps chromium`
- Frontend bundle built in a stage-1 Node container and copied into
  `/app/frontend/dist`
- Non-root user (`opencmo`, uid 1000)
- `tini` as PID 1 for clean signal handling

## What lives outside the image

| Thing | Where on host | Where in container |
|---|---|---|
| SQLite DB + state | `/opt/OpenCMO/data/` | `/data/` |
| Secrets / API keys | `/opt/OpenCMO/.env` | env vars |
| TLS certs + nginx | host filesystem | n/a |

## Quick start (fresh server)

```bash
# 1. Prerequisites
apt-get install -y docker.io docker-compose-plugin
git clone https://github.com/study8677/OpenCMO /opt/OpenCMO
cd /opt/OpenCMO

# 2. Populate secrets
cp .env.example .env
$EDITOR .env   # set OPENAI_API_KEY etc.

# 3. Pre-create the data dir so the bind mount is owned correctly
mkdir -p data
chown 1000:1000 data

# 4. Build + start
docker compose up -d --build

# 5. Verify
curl -fsS http://127.0.0.1:8081/api/v1/health
docker compose ps    # should show (healthy)
```

Then point nginx at `127.0.0.1:8081` (see `/etc/nginx/sites-enabled/aidcmo.conf`
on the production box for the existing pattern — it's unchanged from the
systemd era).

## Day-to-day operations

```bash
# Tail logs
docker compose logs -f opencmo

# Restart after a config change in .env
docker compose up -d

# Pull new source + rebuild + restart (typical deploy)
git pull && docker compose up -d --build

# Stop everything (data preserved in ./data)
docker compose down

# Inspect health status
docker compose ps
docker inspect --format='{{.State.Health.Status}}' opencmo
```

## Deploying from a local checkout

`deploy/docker-deploy.sh` rsyncs the current working tree to newyork and
runs the build+restart there:

```bash
./deploy/docker-deploy.sh           # build + restart + health probe
./deploy/docker-deploy.sh --no-build # restart only (config-only changes)
./deploy/docker-deploy.sh --logs     # also tail logs after deploy
```

It excludes the host-owned `data/`, `.venv/`, `frontend/node_modules/`,
and `frontend/dist/` so the server's persistent state and build caches
are never clobbered.

## Migrating from systemd

If the box was previously running OpenCMO under systemd (the legacy
`/etc/systemd/system/opencmo.service` unit that invoked
`/opt/OpenCMO/.venv/bin/uvicorn opencmo.web.app:app --host 0.0.0.0 --port 8081`),
follow this sequence:

```bash
# On newyork, as root:
cd /opt/OpenCMO

# 1. Snapshot the DB before touching anything.
mkdir -p data
cp -a ~/.opencmo/data.db data/data.db
chown -R 1000:1000 data

# 2. Stop the old service. Disable it so it won't fight for port 8081
#    on the next reboot — but leave the unit file in place for rollback.
systemctl stop opencmo
systemctl disable opencmo

# 3. Start the container. First build takes ~3 minutes because of the
#    Chromium download; subsequent builds reuse cached layers.
docker compose up -d --build

# 4. Verify nginx can reach the new backend.
curl -fsS http://127.0.0.1:8081/api/v1/health
curl -fsSL -o /dev/null -w "%{http_code}\n" https://www.aidcmo.com/app/

# 5. Tail for the first few minutes to catch anything weird.
docker compose logs -f opencmo
```

### Rollback

```bash
docker compose down
systemctl enable --now opencmo
# nginx config didn't change — traffic flows again instantly.
```

If you also need to revert the DB (because the container schema migrated
it forward), restore the snapshot you took in step 1:

```bash
cp -a data/data.db ~/.opencmo/data.db
chown root:root ~/.opencmo/data.db
```

## Tuning

### Different host port

Edit `docker-compose.yml`:

```yaml
ports:
  - "127.0.0.1:8082:8081"   # left side = host, right side = container
```

…and update the nginx upstream to match.

### Persistent data elsewhere

Bind a different host path:

```yaml
volumes:
  - /var/lib/opencmo:/data
```

### CPU / memory limits

Add a `deploy.resources` block. Useful if the box runs other services
(it does — `sub2api` is on 8080 already):

```yaml
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: 2g
```

### Custom model providers (NVIDIA, DeepSeek, Ollama)

These flow through `.env` — see `.env.example` for the env-var names.
No image change needed.

## Common issues

**`Cannot connect to the Docker daemon`** — `systemctl start docker` then
`usermod -aG docker $USER` and re-login if you don't want to `sudo`.

**Container restart loop** — usually a config typo. Tail logs:
`docker compose logs --tail=200 opencmo`. The most common cause is a
missing `OPENAI_API_KEY` (or equivalent) in `.env`.

**Healthcheck never goes green** — uvicorn started but DB init failed.
Check `data/` permissions (`chown -R 1000:1000 data`) and look for
`PermissionError` in the logs.

**Browser-backed scans fail with `BrowserType.launch executable doesn't
exist`** — only happens if someone rebuilt the image with `--no-cache`
and the `playwright install` step failed silently. Inspect the build
log and rerun. The Dockerfile no longer suppresses errors from this step.

**Old `~/.opencmo/data.db` not picked up** — verify the bind mount path
in `docker-compose.yml` matches where you copied the DB to. The default
is `./data/data.db` on the host (relative to where `docker compose` is
run, i.e. `/opt/OpenCMO/data/data.db`).
