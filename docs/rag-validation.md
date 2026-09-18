# RAG validation

Local verification performed on 2026-09-07/08. No production deployment was performed.

## Automated checks

- Full backend suite: **700 passed, 3 skipped**. The skipped cases are legacy Jinja2 routes.
- RAG suite: **37 passed**, including an actual Qdrant server test.
- Ruff: passed.
- Frontend TypeScript and Vite production build: passed; the existing large-bundle advisory remains.
- Browser: desktop and 390-pixel mobile layouts, document upload, retrieval, model configuration, source preview, centered citation dialog and Unicode/emoji source offsets passed with no page errors.
- GitHub CI passed for Python 3.11, Python 3.12 and the frontend. A subsequent tracing hardening change also passed 123 targeted tests locally.

Tests cover parent/child budgets and exact spans, PDF pages and image-only rejection, DOCX tables, HTML cleanup, URL restrictions, tenant/project isolation, sharing revocation, outbound-use restrictions, tombstones, shadow versions, profile migration failure, rebuilding a missing vector collection, account index leases, orphan reconciliation, persisted citations and non-reuse of revoked evidence.

The broader suite needed test isolation fixes: asynchronous worker completion now waits for completion instead of a 50 ms sleep; route tests avoid unintended live scans; settings tests restore environment defaults. Windows file reads explicitly use UTF-8.

Model calls in automated and browser tests are fixtures. An actual Qdrant engine test is not evidence that the configured embedding model meets semantic quality targets.

The existing Trustabl workflow remains gated on findings in unchanged tools, including timeout detection, dynamic outbound URLs and email-report idempotency. Its file-specific findings did not point to files changed by the RAG implementation. RAG-backed generation explicitly disables hosted SDK tracing; this does not constitute a security audit of every existing tool.

## Capacity result

An isolated native Qdrant 1.19.1 instance and SQLite were tested with synthetic documents/vectors.

| Measurement | Result |
| --- | ---: |
| Documents | 10,000 |
| Child passages | 500,000 |
| Vector dimensions | 1,024 |
| Concurrent retrievals | 5 |
| Sample retrievals | 50 |
| Indexing time | 873.7 seconds |
| Ingestion throughput | 572.3 child passages/second |
| Retrieval P50 | 62 ms |
| Retrieval P95 | 2,828 ms |
| SQLite size | 3,867,803,648 bytes |
| Qdrant status | green |
| Indexed vectors | 499,200; remaining points are searchable in the smaller segment |
| Qdrant peak working set | Approximately 17.1 GiB |

Environment: Windows host with 32 logical processors and approximately 31.3 GiB physical memory; Qdrant search threads configured to 4. The same Qdrant process also hosted small UI/evaluation collections, so the process memory figure is not a per-collection measurement.

Latency combines dense, BM25 and title/entity retrieval, including cold initialization in the sample. It excludes embedding, query-rewrite and rerank API latency. It is not an end-to-end chat latency claim.

An earlier Docker-backed run stopped at approximately 425,000 passages with an underlying storage I/O error. That run is not reported as a capacity pass. The completed run used a separate test disk with adequate free space. The capacity tool now checks estimated local disk requirements and documents the need to check the vector-storage disk separately.

## Evaluation corpus

The committed corpus contains **40 fictional documents and 120 Chinese/English questions**, split into development and holdout sets. The ablation runner completed BM25, dense, fusion and fusion-plus-rerank runs in synthetic wiring mode.

These synthetic scores are deliberately not used to claim Recall@20 or nDCG@10 acceptance for real models. No actual Embedding/Rerank credentials were available during this implementation. **Real model quality remains unverified.**

To evaluate it, configure the provider credentials and run live evaluation as described in [the RAG guide](rag.md). Live evaluation records degradation and fails its quality gate when holdout thresholds are not met.
