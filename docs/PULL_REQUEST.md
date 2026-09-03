## Summary

Enriches the `KnowledgeBase` and `Document` SQLAlchemy models in `vector-kb-mcp/models/` with public-sector governance metadata attributes, PostgreSQL extensible `JSONB` attributes with GIN indexing, and implements a strict runtime **1536-dimensional embedding validation guard** to prevent vector database index corruption and enable authoritative LLM citations.

**Issue Link:** [#120](https://github.com/akvo/akvo-rag/issues/120)  
**Task Code:** `TASK-DB-202`  
**Feature Spec:** [`docs/features/006_db_202_metadata_enrichment_and_embedding_guard_spec.md`](docs/features/006_db_202_metadata_enrichment_and_embedding_guard_spec.md)  
**LLD Reference:** [`docs/lld/container_based_rag_platform_lld.md`](docs/lld/container_based_rag_platform_lld.md) (Sections 6, 8, 9)  
**Target Base Branch:** `feature/118-d9-db-201-port-vector-kb-sqlalchemy-models-into-vector-kb-mcpmodels`

---

## What Changes Were Made?

### 1. Model Schema Enrichment (`vector-kb-mcp/models/`)
* **`KnowledgeBase`**:
  * Added `embedding_model` (`String(100)`, default `"text-embedding-3-small"`, `server_default="text-embedding-3-small"`).
  * Added `embedding_dim` (`Integer`, default `1536`, `server_default="1536"`).
* **`Document`**:
  * Added governance metadata columns:
    * `doc_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)`
    * `issuing_authority: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)`
    * `effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)`
    * `doc_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)`
    * `jurisdiction: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)`
    * `metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)`
  * Added table indexes:
    * `Index("idx_vkb_doc_authority", "issuing_authority")`
    * `Index("idx_vkb_doc_type", "knowledge_base_id", "doc_type")`
    * `Index("idx_vkb_doc_metadata_gin", "metadata_", postgresql_using="gin")`

### 2. Custom Exceptions & Dimension Guard (`vector-kb-mcp/core/`)
* **`vector-kb-mcp/core/exceptions.py`**:
  * Created `VectorMCPException` and `EmbeddingDimensionMismatchError(kb_id, expected_dim, actual_dim, model)`.
* **`vector-kb-mcp/core/guards.py`**:
  * Created reusable `validate_embedding_dimension(embedding, expected_dim=1536, kb_id=0, model=...)`.
* **`vector-kb-mcp/retriever/chroma_retriever.py`**:
  * Added `expected_dim: int = 1536` configuration to `ChromaRetriever`.
  * Integrated pre-flight embedding validation in `_embed_query` before dispatching vector searches to ChromaDB.

### 3. Centralized Shared Test Fixtures (`vector-kb-mcp/tests/`)
* **`vector-kb-mcp/tests/conftest.py`**:
  * Centralized `db_session` in-memory SQLite fixture with SQLite foreign key PRAGMA enforcement.
* **`vector-kb-mcp/tests/test_metadata_guard.py`**:
  * Added 9 comprehensive unit tests verifying embedding configuration defaults, metadata persistence, legacy null compatibility, exception message formatting, and positive/negative dimension guard assertions.
* **`vector-kb-mcp/tests/test_models.py` & `test_integration_models.py`**:
  * Updated model tests and verified live PostgreSQL 17 GIN index and JSONB filtering.

---

## Backward Compatibility & Legacy Data Safety

* **Zero Migration Breakage**: All governance fields on `Document` are `nullable=True`, allowing legacy unannotated documents to migrate smoothly.
* **Seamless Dimension Defaults**: `KnowledgeBase.embedding_dim` defaults to `1536` with `server_default="1536"`, aligning with all legacy OpenAI vectors currently stored in ChromaDB.

---

## Verification & Quality Gates

| Verification Gate | Result | Command |
|---|:---:|---|
| **Flake8 Linting** | **PASS** (0 errors / 0 warnings) | `docker exec akvo-rag-vector-kb-mcp-1 python -m flake8 .` |
| **Unit Tests** | **PASS** (49 unit tests) | `docker exec akvo-rag-vector-kb-mcp-1 python -m pytest tests/ -k "not integration"` |
| **Live Integration Tests** | **PASS** (3 integration tests) | `cd vector-kb-mcp && ./test-integration.sh` |
| **Overall Coverage** | **97%** (100% on models, core, retriever) | `cd vector-kb-mcp && ./test.sh` |

---

## Requester Checklist (Akvo Guidelines)
- [x] Issue number included in PR title: `[#120]`
- [x] Tested against live PostgreSQL 17 container and SQLite in-memory test runner
- [x] Code coverage exceeds project mandate (>80%, achieved 97% overall / 100% on touched modules)
- [x] Conventional Commit format used across all 3 atomic commits
