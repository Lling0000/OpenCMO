<div align="center">
  <img src="assets/logo.png" alt="OpenCMO" width="80" />
  <h1>OpenCMO</h1>
  <p><strong>Your open-source AI growth workspace.</strong></p>
  <p>Understand where your product is discovered, what people say about it,<br />and which growth actions to take next.</p>
  <p>
    <a href="README.md">English</a> · <a href="README_zh.md">中文</a> · <a href="README_ja.md">日本語</a> · <a href="README_ko.md">한국어</a> · <a href="README_es.md">Español</a>
  </p>
  <p>
    <a href="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml"><img src="https://github.com/Lling0000/OpenCMO/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/React-19-149ECA?logo=react&amp;logoColor=white" alt="React 19" />
    <img src="https://img.shields.io/badge/Models-BYOK-7C3AED" alt="Bring your own model keys" />
  </p>
  <p><a href="#what-opencmo-does">Overview</a> · <a href="#quick-start">Quick start</a> · <a href="docs/rag.md">Knowledge &amp; RAG</a> · <a href="docs/configuration.md">Configuration</a></p>
</div>

<p align="center">
  <img src="assets/readme-overview.svg" alt="OpenCMO workflow: project, monitoring, shared context, AI analysis, human review" width="100%" />
</p>

## What OpenCMO does

OpenCMO is a self-hosted AI Chief Marketing Officer for founders, open-source maintainers and small product teams. It connects search visibility, community conversations, competitor research and your own documents in one project workspace.

Start with a product URL. OpenCMO builds the project context, collects signals, and uses specialist agents to turn them into reports, content drafts and prioritized recommendations. Scheduled scans help you follow changes over time; an approval queue keeps publishing decisions in your hands.

| Capability | What you can do |
| --- | --- |
| **SEO & search rankings** | Audit technical site health, check AI-crawler accessibility and follow keyword rankings over time. |
| **AI-search visibility (GEO)** | Inspect brand mentions and citations through supported AI providers; coverage depends on configured integrations. |
| **Community & competitors** | Find relevant discussions, track mentions and explore competitors, keywords and discussions in a knowledge graph. |
| **Knowledge library (RAG)** | Retrieve from your documents and historical reports, with source citations in chat, reports and drafts. |
| **Reports & AI chat** | Generate strategic reports and weekly summaries, get a Human Readout and Agent Brief, or discuss findings with project-aware agents. |
| **Content & approvals** | Prepare content and outreach drafts, review proposed actions and enable supported publishing integrations when ready. |

**Bring your own model.** Configure OpenAI or an OpenAI-compatible endpoint, a model with tool-calling support, and an API key. Optional search, community and publishing integrations extend the workspace as you need them.

Direct publishing supports Reddit and Twitter/X when platform credentials and `OPENCMO_AUTO_PUBLISH=1` are configured. Other outreach outputs remain drafts for review.

## From one URL to a working plan

1. **Build context** — crawl the product URL and analyze its brand, category, keywords and competitors.
2. **Collect signals** — gather SEO, AI-search, keyword-ranking and community data through available providers.
3. **Review together** — normalize the results, then let specialist agents analyze each domain and synthesize priorities.
4. **Produce outputs** — save findings, generate reports and briefs, and prepare actions for review.
5. **Keep monitoring** — schedule daily, weekly or monthly scans and compare new results with earlier runs.

The monitoring pipeline has six stages: context building → signal collection → normalization → domain review → strategy synthesis → persistence. Reports, chat and drafts reuse the project context rather than requiring you to explain the product each time.

## Quick start

### Docker Compose

Docker builds the web interface and backend together. Install Docker with Compose, then:

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY` to your model provider's key. For a compatible provider, also set `OPENAI_BASE_URL` and `OPENCMO_MODEL_DEFAULT`; examples are in the [configuration guide](docs/configuration.md).

```bash
docker compose up -d --build
```

Open **[http://localhost:8080](http://localhost:8080)**, create a project from its URL, and run the first scan. Model settings are also available in the web interface.

<details>
<summary><strong>Run from source</strong> — Python 3.10+ and Node.js 20+</summary>

```bash
git clone https://github.com/Lling0000/OpenCMO.git
cd OpenCMO
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
crawl4ai-setup
cp .env.example .env
```

Configure the model key in `.env`, then build the frontend and start the server:

```bash
cd frontend
npm ci
npm run build
cd ..
opencmo-web
```

Open `http://localhost:8080`. The frontend build is required for the web interface.

</details>

### Your first project

- Add the product or repository URL and review the detected project context.
- Run a scan and inspect search, community and competitor findings.
- Ask AI chat to explain a finding or generate a strategic report.
- Add source documents if you want answers grounded in your own knowledge.
- Review drafts and recommendations, then schedule the next scan.

## Knowledge grounded in your sources

The optional knowledge library accepts text PDFs, DOCX, Markdown, TXT, pasted text, public web pages and historical reports. It combines **Qdrant dense retrieval, BM25, title/entity recall, rank fusion and reranking**, then brings surrounding context and source citations into generated outputs.

```bash
# Enable the app and the optional vector database.
docker compose --profile rag up -d --build
```

In **Knowledge library → Models and retrieval**, configure your embedding and rerank providers, test the connections and enable retrieval. Upload a source and wait for indexing to finish before querying it.

Documents are private to a project by default. Account sharing and permission to use a source in public-facing content are separate settings. See the [RAG guide](docs/rag.md) for setup, permissions, APIs and provider evaluation.

## Architecture & development

| Layer | Stack |
| --- | --- |
| Web interface | React 19 · TypeScript · Vite · TanStack Query |
| API & orchestration | FastAPI · OpenAI Agents SDK |
| Background work | Scan, report, graph-expansion and knowledge-indexing workers |
| Storage & retrieval | SQLite / FTS5 · optional Qdrant |
| Collection | Crawl4AI · search and platform-specific providers |

```text
frontend/src/              Web interface, project views and settings
src/opencmo/agents/         CMO and specialist agents
src/opencmo/tools/          Crawling, search, audits and platform integrations
src/opencmo/services/       Project intelligence and approval workflows
src/opencmo/background/     Task execution and progress
src/opencmo/rag/            Ingestion, hybrid retrieval and source citations
src/opencmo/storage/        SQLite persistence
src/opencmo/web/            API routes and authentication
```

<details>
<summary><strong>Development commands</strong></summary>

After installing the source dependencies:

```bash
pip install pytest pytest-asyncio ruff
pytest tests/
ruff check src/ tests/

cd frontend
npm ci
npm run dev
```

The Vite development server runs at `http://localhost:5173` and proxies API requests to the backend on port `8080`.

</details>

## Documentation

- [Configuration](docs/configuration.md) — model providers and optional integrations.
- [Deployment](docs/deployment.md) — hosting, persistent storage and backups.
- [Knowledge & RAG](docs/rag.md) — document ingestion, retrieval and citations.
- [RAG validation](docs/rag-validation.md) — test scope, capacity measurements and evaluation status.
- [Contributing](CONTRIBUTING.md) — development workflow and contribution credit.

Maintained by **[Ling (`Lling0000`)](https://github.com/Lling0000)**. Historical contributions are recorded in [CONTRIBUTORS.md](CONTRIBUTORS.md).

## Community

[LINUX DO](https://linux.do/) — Where enthusiasts gather
