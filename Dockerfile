# Stage 1: Build frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e ".[all]"
# Install system deps for Chromium (used by crawl4ai), then set up crawl4ai
RUN playwright install-deps chromium \
    && crawl4ai-setup || true
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
VOLUME ["/data"]
ENV OPENCMO_DB_PATH=/data/data.db
EXPOSE 8080
CMD ["opencmo-web"]
