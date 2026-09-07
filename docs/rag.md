# Knowledge library and RAG

OpenCMO can retrieve evidence from project documents, historical reports and account-shared case studies. The same service supplies chat, report sections and promotional content.

## Start

Install the optional RAG dependencies (included in the all extra), build the frontend, and run Qdrant:

    pip install -e ".[all]"
    cd frontend
    npm ci
    npm run build
    cd ..
    docker compose --profile rag up -d qdrant
    opencmo-web

Copy .env.example to .env before using Compose. Alternatively, run the whole application with:

    docker compose --profile rag up -d --build

The RAG Compose profile adds Qdrant 1.19.1 with a persistent volume. Its host port binds to localhost. Set OPENCMO_QDRANT_API_KEY in .env to configure the same authentication key on both the app and Qdrant. RAG remains disabled per account until enabled in the knowledge settings. Existing installations can run without the RAG profile.

In a project, open **Knowledge library → Models and retrieval**:

1. Configure Embedding and Rerank base URLs, model names and keys.
2. Test both connections, enable retrieval, and save.
3. Upload a document, paste text, import a public URL, or import historical reports.
4. Wait until documents show Ready.
5. Ask a question in chat or inspect results in Test retrieval.

The preset uses https://api.siliconflow.cn/v1 with BAAI/bge-m3 and BAAI/bge-reranker-v2-m3. The protocol is OpenAI-compatible embeddings and a rerank endpoint returning results containing index and relevance_score. Model credentials are stored per account, not in the global model registry. Tenant-configured URLs must be HTTPS base URLs without user info, query parameters or fragments.

A connection test makes model API requests. Saving an embedding/splitting change queues a rebuild. The old index remains active until the replacement is ready.

## Scope and use

- Documents are private to their project by default.
- Account sharing explicitly makes a source available to other projects in the same account. It never shares with another account.
- Public-facing use is a separate flag. Content generation only retrieves sources with that flag enabled.
- Private documents become unavailable when their project is deleted. Account-shared documents can survive their originating project.
- Revocation/deletion affects new retrieval and source access immediately. Existing generated conversation text is retained; revoked evidence is not reused as new chat context.
- AI-generated reports are labelled as generated analysis. They are not presented as independently verified observations.

Chat modes:

| Mode | Behavior |
| --- | --- |
| auto | Retrieve when enabled; clearly distinguish general advice when sources are missing. |
| only | Answer from knowledge evidence; no agent tools/handoffs; return an insufficient-evidence response when no passages are found. |
| off | Use the existing chat behavior without knowledge retrieval. |

Quoted passages carry citation links. Clicking a link displays the authorized original text with the passage highlighted. Citation provenance persists across conversation reloads and report/draft storage. Source offsets refer to Unicode code points in normalized text; the frontend converts them for JavaScript string indexing.

## Ingestion and indexing

Supported inputs: text PDF, DOCX, Markdown, TXT, pasted text and individual public web pages. The file limit is 25 MiB; PDFs are limited to 500 pages. Image-only PDFs require OCR and are rejected with a clear status. OCR, PPT and Excel are not included.

Original files, normalized text and version records are stored separately. PDF page numbers, heading paths, table context and exact text offsets are retained where available. Public URL imports validate resolved IP addresses and every redirect; fetching does not load arbitrary browser subresources.

The splitter uses document structure followed by recursive paragraph/line/sentence/word boundaries:

| Setting | Default |
| --- | ---: |
| Parent passage budget | 1,536 tokens |
| Child passage budget | 384 tokens |
| Child overlap | 64 tokens |
| Maximum parents returned | 6 |
| Knowledge context budget | 6,000 tokens |

Token budgets use cl100k_base consistently. Provider input limits are checked separately. Children are indexed for retrieval; parents supply surrounding context. Source quotes always refer to original normalized spans, not synthetic heading prefixes.

SQLite is authoritative for document ownership, active versions, passages and citations. FTS5 indexes normalized English terms and Jieba-segmented Chinese text. Qdrant stores dense child vectors with indexed account, project, scope, purpose and date/type metadata.

Indexing runs in the existing worker with progress events, cancellation and retries. Account leases serialize index changes across worker processes. Duplicate uploads are idempotent. Manual document reindexing creates a shadow version so failed updates keep the old source available.

Completed Human Reports are indexed automatically after RAG is enabled. Import historical reports queues their indexing; that batch finishing does not mean every document has finished embedding. Agent Briefs are not separately indexed.

## Retrieval

The service preserves the original query and can resolve references from up to three recent conversation rounds. It adds at most two alternative queries. Failure to rewrite falls back to the original question.

| Lane | Default limit | Implementation |
| --- | ---: | --- |
| Dense | 30 | Qdrant; query variants merged within the lane |
| Lexical | 30 | SQLite FTS5/BM25 over passage text |
| Title/entity | 20 | Indexed matches restricted to titles, heading paths and tags |

All lanes apply scope and use restrictions. SQL revalidates candidate ownership and active versions after remote calls. Title/entity retrieval uses an inverted index instead of scanning every passage.

Candidates are deduplicated, fused with equal-weight reciprocal rank fusion, and sent to reranking:

    RRF score = sum(1 / (60 + rank)), with ranks starting at 1
    50 fused candidates → rerank → up to 8 qualifying passages → up to 6 parents

The initial rerank threshold is 0.2 and must be calibrated for the configured model. The default retrieval deadline is 10 seconds, with at most 2 seconds for rewriting and 4 seconds for reranking. Failed lanes remain visible in diagnostics; rerank failure uses the fused ranking and marks the result degraded.

Chat and report integrations keep retrieved text separate from trusted instructions. Direct quotes and citation identifiers are checked after marketing rewriting. This structural validation does not replace human review of whether an inference is actually supported.

## APIs

All endpoints use existing authentication. Account identity is derived by the server.

| Endpoint | Purpose |
| --- | --- |
| GET/POST /api/v1/knowledge/documents | List visible sources; upload multipart or import JSON text/URL |
| GET/PATCH/DELETE /api/v1/knowledge/documents/{id} | Inspect versions, update metadata or revoke a source |
| GET /api/v1/knowledge/documents/{id}/versions/{version} | Normalized source and chunk preview |
| GET /api/v1/knowledge/documents/{id}/versions/{version}/original | Authorized original-file download |
| POST /api/v1/knowledge/documents/{id}/reindex | Reparse/reindex through a new version |
| POST /api/v1/projects/{id}/knowledge/backfill-reports | Queue historical report imports |
| POST /api/v1/projects/{id}/knowledge/search | Retrieval diagnostics, ranked candidates and citations |
| GET /api/v1/knowledge/citations/{id} | Authorized citation and original text |
| GET/POST /api/v1/knowledge/settings | Read masked configuration or update account settings |
| POST /api/v1/knowledge/settings/test | Test embedding and rerank protocols |
| POST /api/v1/knowledge/rebuild | Queue a complete account rebuild |
| Existing task APIs | Inspect/cancel indexing jobs and stream progress |

The chat endpoint accepts optional rag_mode. Its SSE stream adds retrieval progress and final citations, retrieval_id and rag_status. Existing requests remain valid.

## Operations

Environment controls:

| Variable | Default |
| --- | --- |
| OPENCMO_RAG_ENABLED | 1: master switch; each account still opts in |
| OPENCMO_QDRANT_URL | http://127.0.0.1:6333; Compose uses http://qdrant:6333 |
| OPENCMO_QDRANT_API_KEY | Unset |
| OPENCMO_QDRANT_PREFIX | opencmo; use a unique prefix for each independent app/database deployment |
| OPENCMO_RAG_STORAGE_PATH | knowledge/ next to the SQLite database |
| OPENCMO_RAG_MAX_DOCUMENTS | 10,000 per account |
| OPENCMO_RAG_MAX_CHUNKS | 500,000 active child passages per account |
| OPENCMO_KNOWLEDGE_CONCURRENCY | 1 per worker; account leases also serialize across workers |

Every six hours, the enabled scheduler queues cleanup for enabled accounts: deleted sources, stale incomplete generations and orphan points in known account collections. It also repairs missed report-enqueue events after the account enabled RAG. If scheduling is disabled, cleanup can be invoked through the ingestion maintenance function.

Back up the SQLite database consistently (SQLite online backup or stop the app first), original-file directory and operator configuration. The SQLite backup includes account credentials and needs the same access protection as the live database. Qdrant snapshots are optional accelerators; vectors can be reconstructed from originals. After restoring a database without Qdrant data, use Rebuild the entire library.

Query traces retain timing, ranks, warnings and query hashes rather than full query text. Embedding/rerank events store reported token usage when supplied and a separate local input-token estimate; these are not a billing ledger. Knowledge tasks do not serialize provider keys into their payloads.

For 500,000 passages, reserve space on both the database disk and the vector-storage disk. The measured test run used about 3.60 GiB for SQLite and peaked at about 17.1 GiB Qdrant working set during indexing; allow memory and disk headroom beyond the steady-state footprint. See the validation report for the exact test scope.

## Evaluation

The committed fictional corpus contains 40 documents and 120 Chinese/English questions, split into development and holdout sets.

Validate its structure:

    python -m opencmo.rag.evaluate --validate

Run wiring-only ablations on an isolated Qdrant and a NEW database:

    python -m opencmo.rag.evaluate --synthetic --db output/eval-new.db --output output/evaluation.json

For a real model evaluation, configure RAG_EMBEDDING_API_KEY and RAG_RERANK_API_KEY in the process environment. Optional RAG_EMBEDDING_BASE_URL, RAG_EMBEDDING_MODEL, RAG_RERANK_BASE_URL and RAG_RERANK_MODEL override the preset. Configure the normal chat model too if evaluating query rewriting.

    python -m opencmo.rag.evaluate --live --db output/eval-live-new.db --output output/evaluation-live.json

Live mode exits unsuccessfully when the holdout gate is not met: Recall@20 ≥ 0.90, nDCG@10 ≥ 0.80, exact quote locations, and no degraded holdout requests. Synthetic execution is explicitly labelled and cannot pass that quality gate. Unanswerable questions also need answer-level review.

Capacity testing generates synthetic vectors/documents and calls real SQLite/Qdrant, without model APIs:

    python -m opencmo.rag.capacity --db /large-test-disk/capacity-new.db --qdrant-url http://127.0.0.1:6333 --grpc-port 6334 --documents 10000 --chunks-per-doc 50 --dimensions 1024 --queries 50 --concurrency 5 --output output/capacity.json

Use an isolated test server. The command checks estimated local free space; separately verify the Qdrant storage disk. It never overwrites an existing database. Model API latency is not included in its results.

Run API/parser/retrieval tests with the optional native-server check:

    OPENCMO_RAG_TEST_QDRANT=http://127.0.0.1:6333 pytest tests/test_rag.py

The native-server test uses unique collections and deletes only its own collection. Its model calls are still mocked; it verifies the database engine and authorization, not embedding quality.
