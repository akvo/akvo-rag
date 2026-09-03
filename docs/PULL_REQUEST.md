# [#117] feat(vector-kb): Phase 2 - Unified Database Schema Isolation & Metadata Hardening

## Summary

This Pull Request delivers **Phase 2 (Milestone D9: Unified Database Schema Isolation & Metadata Hardening)**, merging all completed and tested Phase 2 deliverables into the `phase-1` base branch (`phase-1/107-rag-improvement-d8-phase-1-environment-orchestration-monorepo-setup-vector-microservice`).

Phase 2 consolidates the `vector-kb-mcp` persistence layer into the unified PostgreSQL 17 database (`akvo_rag`), enforces complete schema isolation with `vkb_` table prefixes and dedicated `alembic_version_vkb` migration tracking, adds public-sector governance metadata and strict 1536-dim vector embedding guards, and delivers a robust asyncpg database engine with an automated legacy data migration CLI.

- **Milestone / Issue Link:** [#117](https://github.com/akvo/akvo-rag/issues/117)
- **Base Branch:** `phase-1/107-rag-improvement-d8-phase-1-environment-orchestration-monorepo-setup-vector-microservice`
- **Head Branch:** `phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening`
- **LLD Reference:** [`docs/lld/container_based_rag_platform_lld.md`](https://github.com/akvo/akvo-rag/blob/phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening/docs/lld/container_based_rag_platform_lld.md) (Sections 6, 8, 9)
- **Manual QA Guide:** [`docs/qa/qa-guide-phase-2-unified-database-schema-isolation-metadata-hardening.md`](https://github.com/akvo/akvo-rag/blob/phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening/docs/qa/qa-guide-phase-2-unified-database-schema-isolation-metadata-hardening.md)

---

## What Changes Were Made? (Sub-Feature Breakdown)

### 1. DB-201: Modernized SQLAlchemy 2.0 Models (`vector-kb-mcp/models/`)
* **Issue Link:** [#118](https://github.com/akvo/akvo-rag/issues/118) | **Spec:** [`docs/features/005_db_201_vector_kb_sqlalchemy_models_spec.md`](https://github.com/akvo/akvo-rag/blob/phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening/docs/features/005_db_201_vector_kb_sqlalchemy_models_spec.md)
* Ported declarative SQLAlchemy 2.0 mapped models from the legacy standalone repository:
  * `KnowledgeBase` (`vkb_knowledge_bases`): Tenant/user isolation, chunk size/overlap configuration.
  * `Document` (`vkb_documents`): File tracking, hash validation, composite unique constraints (`knowledge_base_id`, `file_hash`).
  * `DocumentChunk` (`vkb_document_chunks`): Text chunk store with ChromaDB vector UUID tracking and token counting.
  * `ProcessingTask` (`vkb_processing_tasks`): Ingestion status tracking (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) with Celery/Redis decoupling.
* Enforced `vkb_` table isolation prefixes across all tables, primary keys, and foreign keys.

### 2. DB-202: Governance Metadata & 1536-Dim Embedding Guard (`vector-kb-mcp/core/`, `models/`)
* **Issue Link:** [#120](https://github.com/akvo/akvo-rag/issues/120) | **Spec:** [`docs/features/006_db_202_metadata_enrichment_and_embedding_guard_spec.md`](https://github.com/akvo/akvo-rag/blob/phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening/docs/features/006_db_202_metadata_enrichment_and_embedding_guard_spec.md)
* **Metadata Enrichment**:
  * Enriched `KnowledgeBase` with `embedding_model` and `embedding_dim` (defaulting to `text-embedding-3-small` and `1536`).
  * Enriched `Document` with governance metadata (`doc_version`, `issuing_authority`, `effective_date`, `doc_type`, `jurisdiction`) and PostgreSQL `JSONB` extensible metadata with GIN indexing (`idx_vkb_doc_metadata_gin`).
* **Vector Dimension Guard**:
  * Added `EmbeddingDimensionMismatchError` and `VectorMCPException` in `vector-kb-mcp/core/exceptions.py`.
  * Added runtime validator `validate_embedding_dimension` in `vector-kb-mcp/core/guards.py`.
  * Hardened `ChromaRetriever` to validate embedding query dimensions prior to dispatching vector similarity searches.

### 3. DB-203: Service-Owned Alembic Migrations (`vector-kb-mcp/alembic/`)
* **Issue Link:** [#122](https://github.com/akvo/akvo-rag/issues/122) | **Spec:** [`docs/features/007_db_203_service_owned_alembic_migrations_spec.md`](https://github.com/akvo/akvo-rag/blob/phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening/docs/features/007_db_203_service_owned_alembic_migrations_spec.md)
* Configured isolated Alembic migration environment inside `vector-kb-mcp/alembic.ini` and `env.py`.
* Isolated version tracking to dedicated table:
  ```python
  version_table = "alembic_version_vkb"
  ```
* Implemented `include_object` filter in `env.py` preventing Alembic from scanning or dropping non-`vkb_` tables (such as `backend/` application tables).
* Authored initial baseline migration `001_initial_vkb_schema.py` covering all 4 tables, foreign keys, indexes, and GIN JSONB indexes.

### 4. DB-204: Asyncpg Session Manager & Legacy Migration CLI (`vector-kb-mcp/db/`, `cli/`)
* **Issue Link:** [#124](https://github.com/akvo/akvo-rag/issues/124) | **Spec:** [`docs/features/008_db_204_postgres_adapter_and_legacy_data_migration_cli_spec.md`](https://github.com/akvo/akvo-rag/blob/phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening/docs/features/008_db_204_postgres_adapter_and_legacy_data_migration_cli_spec.md)
* **Async PostgreSQL Session Manager (`vector-kb-mcp/db/session.py`)**:
  * SQLAlchemy 2.0 `create_async_engine` with `asyncpg` driver and connection pooling (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`).
  * `get_async_session()` context manager with automatic rollback and lifecycle management.
  * Multi-driver URL normalizer supporting both standard PostgreSQL connections and asyncpg dialects.
* **Automated Legacy Migration CLI (`vector-kb-mcp/cli/migrate_legacy_data.py`)**:
  * Idempotent ETL pipeline reading from legacy MySQL or standalone PostgreSQL databases and inserting into `vkb_` tables.
  * Conflict resolution (`ON CONFLICT DO NOTHING`), batch chunk streaming (`--batch-size`), and non-destructive dry run simulation (`--dry-run`).
  * Automatic metadata transformation, default backfilling (`embedding_dim=1536`), and JSON to JSONB normalization.

---

## Why Were These Changes Made?

1. **Eliminate Microservice Coupling & Schema Conflicts**: Option C consolidates backend and vector microservices onto PostgreSQL 17. Isolating tables to `vkb_` and Alembic tracking to `alembic_version_vkb` prevents schema collision and allows independent deployment and migration lifecycles.
2. **Prevent Vector Index Corruption**: Mismatched embedding dimensions degrade retrieval quality and cause silent vector search failures. Enforcing runtime dimension validation at the MCP gateway guarantees index integrity.
3. **High Concurrency & Async Readiness**: Moving `vector-kb-mcp` to native `asyncpg` enables high-throughput Redis RPC request handling without blocking the Python event loop.
4. **Zero-Downtime Legacy Data Portability**: The migration CLI enables immediate, automated transition of existing knowledge bases, documents, and chunks from previous standalone deployments into the unified monorepo infrastructure.

---

## Verification & Quality Gates

### Automated Test Suite Summary

All unit, integration, and live container tests pass with zero failures:

| Verification Gate | Target | Result | Command |
|---|:---:|:---:|---|
| **Flake8 Linting** | 0 warnings/errors | **PASS** (0 errors) | `docker exec akvo-rag-vector-kb-mcp-1 python -m flake8 .` |
| **Total Test Suite** | 100% pass | **PASS** (69 passed in 5.52s) | `docker exec akvo-rag-vector-kb-mcp-1 pytest tests/` |
| **Total Code Coverage** | >= 80% (Akvo mandate) | **97% Overall Coverage** | `docker exec akvo-rag-vector-kb-mcp-1 pytest tests/ --cov=.` |
| **Models & DB Coverage** | 100% | **100%** | `tests/test_models.py`, `tests/test_db_and_migrator.py` |
| **Live Postgres 17 Test** | Schema & Cascade pass | **PASS** | `tests/test_integration_models.py` |
| **Alembic Migration Test** | Upgrade/Downgrade pass | **PASS** | `tests/test_migrations.py` |
| **Chroma & Redis Tests** | RPC & vector pass | **PASS** | `tests/test_integration_chroma.py`, `tests/test_integration_redis_worker.py` |

### Detailed Coverage Breakdown

```text
Name                                         Stmts   Miss  Cover   Missing
--------------------------------------------------------------------------
alembic/env.py                                  64      9    86%   38-50, 92-93, 102, 128
alembic/versions/001_initial_vkb_schema.py      35      0   100%
chunker/__init__.py                              3      0   100%
chunker/hashing.py                              10      0   100%
chunker/text_chunker.py                         35      0   100%
cli/__init__.py                                  2      0   100%
cli/migrate_legacy_data.py                     136     12    91%   58, 70, 114, 119-124, 233-234, 327
core/__init__.py                                 4      0   100%
core/config.py                                  21      0   100%
core/exceptions.py                               9      0   100%
core/guards.py                                   7      0   100%
db/__init__.py                                   2      0   100%
db/session.py                                   23      0   100%
main.py                                        143     22    85%
models/__init__.py                               6      0   100%
models/base.py                                   8      0   100%
models/document.py                              27      0   100%
models/document_chunk.py                        20      0   100%
models/knowledge_base.py                        16      0   100%
models/processing_task.py                       17      0   100%
parser/__init__.py                              15      0   100%
parser/base.py                                  18      1    94%
parser/docx_parser.py                           14      0   100%
parser/pdf_parser.py                            18      0   100%
parser/text_parser.py                           14      0   100%
retriever/__init__.py                            3      0   100%
retriever/chroma_retriever.py                   49      0   100%
retriever/models.py                             14      0   100%
tests/conftest.py                               60      0   100%
tests/test_chunker.py                           52      0   100%
tests/test_db_and_migrator.py                  191      0   100%
tests/test_integration_chroma.py                35      4    89%
tests/test_integration_models.py                60      2    97%
tests/test_integration_redis_worker.py          40      4    90%
tests/test_metadata_guard.py                    94      0   100%
tests/test_migrations.py                       139      9    94%
tests/test_models.py                           138      0   100%
tests/test_parser.py                           106      0   100%
tests/test_redis_worker.py                     174      0   100%
tests/test_retriever.py                         55      0   100%
--------------------------------------------------------------------------
TOTAL                                         1877     63    97%
```

---

## Requester Checklist (Akvo Developer Guidelines)

- [x] **PR Title Standard**: Follows `[#117] feat(vector-kb): Phase 2 - Unified Database Schema Isolation & Metadata Hardening`
- [x] **Branch Naming**: Target base branch is `phase-1/107-rag-improvement-d8-phase-1-environment-orchestration-monorepo-setup-vector-microservice`
- [x] **Test Coverage Gate**: Minimum 80% coverage mandate satisfied (achieved **97%** overall coverage across `vector-kb-mcp`)
- [x] **Code Quality**: Clean Flake8 linting with zero warnings/errors
- [x] **Documentation & Specs Aligned**: Feature specifications `005`, `006`, `007`, `008` under `docs/features/` updated to `IMPLEMENTED`
- [x] **Zero Hardcoded Secrets**: All configuration sourced from environment variables (`DATABASE_URL`, `REDIS_URL`, `CHROMA_HOST`)
