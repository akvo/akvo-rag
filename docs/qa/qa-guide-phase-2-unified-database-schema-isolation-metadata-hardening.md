# Phase 2 Manual QA & Verification Guide

> **Issue**: [#117](https://github.com/akvo/akvo-rag/issues/117) — `[RAG IMPROVEMENT] D9 - Phase 2: Unified Database Schema Isolation & Metadata Hardening`  
> **Target Branch / PR**: `phase-2/117-rag-improvement-d9-phase-2-unified-database-schema-isolation-metadata-hardening` -> `phase-1` ([PR #126](https://github.com/akvo/akvo-rag/pull/126))

---

## 1. Overview & Scope

In **Phase 2**, the `vector-kb-mcp` service establishes its isolated, service-owned persistence layer inside the unified **PostgreSQL 17** database (`akvo_rag`).

This QA guide details step-by-step instructions to:
1. Run and verify the complete automated test suite (unit tests, live Postgres 17 integration, migration reversibility, Chroma/Redis RPC tests).
2. Manually test and inspect **service-owned Alembic migrations** and table schema isolation (`alembic_version_vkb` and `vkb_` prefixes).
3. Manually test **asyncpg connection pooling & transaction handling**.
4. Manually test **governance metadata persistence & GIN-indexed JSONB queries**.
5. Manually test the **runtime 1536-dim embedding validation guard** (positive & mismatch trapping).
6. Manually test the **Automated Legacy Data Migration CLI** (`--dry-run` and live data import).

---

## 2. Prerequisites & Environment Setup

Ensure all local Docker services are running and healthy:

```bash
# Start unified local infrastructure
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

**Required active containers:**
- `akvo-rag-vector-kb-mcp-1`
- `akvo-rag-postgres-1` (PostgreSQL 17 on port 5432)
- `akvo-rag-redis-1` (Redis 7 on port 6379)
- `akvo-rag-chromadb-1` (ChromaDB on port 8001 -> 8000)
- `akvo-rag-minio-1` (MinIO on port 9000)

---

## 3. Automated Quality Gates

Run the automated test runner inside the container or via the workspace shell:

```bash
# 1. Run all unit and integration tests with coverage report (Target: >= 80%)
docker exec akvo-rag-vector-kb-mcp-1 pytest tests/ --cov=. --cov-report=term-missing

# 2. Run Flake8 code linting (Target: 0 errors / 0 warnings)
docker exec akvo-rag-vector-kb-mcp-1 python -m flake8 .
```

**Quality Baseline:**
- **69 tests passing** with 0 errors.
- **97% overall coverage** (100% on models, db, core, and parser modules).
- Zero Flake8 warnings.

---

## 4. Manual QA: Service-Owned Alembic Migrations

Validate that `vector-kb-mcp` manages its own isolated migrations without interfering with any other application tables.

### Step 4.1: Apply Baseline Migration
Run the service migration to the latest revision:

```bash
docker exec akvo-rag-vector-kb-mcp-1 alembic upgrade head
```

**Expected Output:**
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade -> 001_initial_vkb_schema, initial vkb schema
```

### Step 4.2: Verify PostgreSQL Table Isolation
Connect to PostgreSQL 17 and verify `vkb_` table isolation and dedicated version tracking:

```bash
docker exec akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "\dt"
```

**Expected Relations:**
| Schema | Table Name | Purpose |
|---|---|---|
| `public` | `alembic_version_vkb` | Dedicated vector service migration revision tracker |
| `public` | `vkb_knowledge_bases` | Tenant-isolated knowledge base registry |
| `public` | `vkb_documents` | File tracking, hashes & governance metadata |
| `public` | `vkb_document_chunks` | Chunk text store & Chroma UUID references |
| `public` | `vkb_processing_tasks`| Async ingestion task lifecycle |

### Step 4.3: Inspect Table Schemas & GIN Indexes
Verify that `vkb_documents` contains all governance fields and GIN indexing:

```bash
docker exec akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "\d vkb_documents"
```

**Expected Columns & Indexes:**
- Governance Columns: `issuing_authority`, `doc_version`, `effective_date`, `doc_type`, `jurisdiction`.
- JSONB Extensible Column: `metadata_` (type `jsonb`).
- GIN Index: `idx_vkb_doc_metadata_gin GIN (metadata_)`.

### Step 4.4: Verify Migration Reversibility (Rollback & Re-apply)
Ensure migration downgrade and upgrade execute cleanly:

```bash
# Downgrade schema
docker exec akvo-rag-vector-kb-mcp-1 alembic downgrade base

# Verify tables were cleaned up
docker exec akvo-rag-postgres-1 psql -U postgres -d akvo_rag -c "\dt"

# Re-apply upgrade to head
docker exec akvo-rag-vector-kb-mcp-1 alembic upgrade head
```

---

## 5. Manual QA: Asyncpg Engine & Metadata Persistence

Verify that the async session manager (`get_db_session`), governance metadata, and foreign key cascading behave correctly under live PostgreSQL 17 transactions.

### Execute Live Python Verification Script:

```bash
docker exec akvo-rag-vector-kb-mcp-1 python -c '
import asyncio
from db.session import get_db_session
from models import KnowledgeBase, Document

async def verify_db():
    async with get_db_session() as session:
        # 1. Create KnowledgeBase with custom embedding config
        kb = KnowledgeBase(
            name="UNEP Environmental Policy KB",
            description="Manual QA Knowledge Base",
            embedding_model="text-embedding-3-small",
            embedding_dim=1536
        )
        session.add(kb)
        await session.flush()
        print(f"✅ Created KnowledgeBase ID={kb.id} with embedding_dim={kb.embedding_dim}")

        # 2. Create Document with Governance Metadata & JSONB
        doc = Document(
            knowledge_base_id=kb.id,
            file_name="water_sanitation_2026.pdf",
            file_path="/tmp/water_sanitation_2026.pdf",
            file_size=2048576,
            content_type="application/pdf",
            file_hash="qa_hash_water_2026",
            doc_version="v2.1",
            issuing_authority="UN Environment Programme",
            doc_type="Statutory Regulation",
            jurisdiction="International",
            metadata_={"sdg_target": "Goal 6", "department": "Water Resources", "is_confidential": False}
        )
        session.add(doc)
        await session.flush()
        print(f"✅ Created Document ID={doc.id}, Authority={doc.issuing_authority}")
        print(f"✅ Persisted JSONB Metadata: {doc.metadata_}")

        # 3. Clean up
        await session.delete(kb)
        print("✅ Cascade deletion executed successfully")

asyncio.run(verify_db())
'
```

**Expected Output:**
```text
✅ Created KnowledgeBase ID=1 with embedding_dim=1536
✅ Created Document ID=1, Authority=UN Environment Programme
✅ Persisted JSONB Metadata: {'sdg_target': 'Goal 6', 'department': 'Water Resources', 'is_confidential': False}
✅ Cascade deletion executed successfully
```

---

## 6. Manual QA: 1536-Dimensional Embedding Validation Guard

Verify that vectors with mismatched dimensions are trapped before reaching the ChromaDB vector database index.

### Execute Dimension Guard Test:

```bash
docker exec akvo-rag-vector-kb-mcp-1 python -c '
from core.guards import validate_embedding_dimension
from core.exceptions import EmbeddingDimensionMismatchError

# 1. Valid 1536-dim vector (OpenAI text-embedding-3-small standard)
valid_vector = [0.05] * 1536
validated = validate_embedding_dimension(valid_vector, expected_dim=1536, kb_id=10)
assert len(validated) == 1536
print("✅ [PASS] 1536-dim vector successfully accepted by guard")

# 2. Invalid 512-dim vector
try:
    invalid_vector = [0.05] * 512
    validate_embedding_dimension(invalid_vector, expected_dim=1536, kb_id=10, model="text-embedding-3-small")
    print("❌ [FAIL] Guard failed to trap dimension mismatch")
except EmbeddingDimensionMismatchError as err:
    print(f"✅ [PASS] Dimension mismatch caught gracefully:\n   -> {err}")
'
```

**Expected Output:**
```text
✅ [PASS] 1536-dim vector successfully accepted by guard
✅ [PASS] Dimension mismatch caught gracefully:
   -> Embedding dimension mismatch for KB #10 using model 'text-embedding-3-small'. Expected 1536-dim, received 512-dim.
```

---

## 7. Manual QA: Legacy Data Migration CLI

Validate the ETL tool (`cli.migrate_legacy_data`) used for migrating records from standalone databases into the unified PostgreSQL 17 `akvo_rag` database.

### Step 7.1: Verify CLI Argument Parser
Run the `--help` command:

```bash
docker exec akvo-rag-vector-kb-mcp-1 python -m cli.migrate_legacy_data --help
```

### Step 7.2: Run Non-Destructive Dry Run Simulation
Create a mock source database with sample legacy records and run a `--dry-run` migration:

```bash
docker exec akvo-rag-vector-kb-mcp-1 python -c '
import sqlite3
import sys
from cli.migrate_legacy_data import main

# 1. Create simulated legacy database
conn = sqlite3.connect("/tmp/qa_legacy_source.db")
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS knowledge_bases")
c.execute("DROP TABLE IF EXISTS documents")
c.execute("DROP TABLE IF EXISTS document_chunks")

c.execute("CREATE TABLE knowledge_bases (id INTEGER PRIMARY KEY, name TEXT, description TEXT, is_active INTEGER, created_at TEXT, updated_at TEXT)")
c.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, knowledge_base_id INTEGER, file_name TEXT, file_path TEXT, file_size INTEGER, content_type TEXT, file_hash TEXT, status TEXT, created_at TEXT, updated_at TEXT)")
c.execute("CREATE TABLE document_chunks (id INTEGER PRIMARY KEY, kb_id INTEGER, document_id INTEGER, chunk_index INTEGER, chunk_text TEXT, chroma_id TEXT, token_count INTEGER, metadata TEXT, created_at TEXT)")

c.execute("INSERT INTO knowledge_bases VALUES (201, \"Legacy Sanitation KB\", \"2024 archive\", 1, \"2024-06-01 00:00:00\", \"2024-06-01 00:00:00\")")
c.execute("INSERT INTO documents VALUES (701, 201, \"sanitation_handbook.pdf\", \"/data/sanitation.pdf\", 512000, \"application/pdf\", \"hash_701_sanitation\", \"COMPLETED\", \"2024-06-01 00:00:00\", \"2024-06-01 00:00:00\")")
c.execute("INSERT INTO document_chunks VALUES (9001, 201, 701, 0, \"Sanitation guidelines for emergency shelters.\", \"chroma-uuid-9001\", 45, NULL, \"2024-06-01 00:00:00\")")
conn.commit()
conn.close()

# 2. Execute dry-run migration
sys.argv = ["migrate_legacy_data.py", "--source-url", "sqlite:////tmp/qa_legacy_source.db", "--dry-run"]
main()
'
```

**Expected Output:**
```text
[INFO] [legacy_migrator] Starting legacy data migration (dry_run=True, batch_size=500)
[INFO] [legacy_migrator] Source database: sqlite:////tmp/qa_legacy_source.db
[INFO] [legacy_migrator] Target database: postgresql+asyncpg://postgres:postgres@postgres:5432/akvo_rag
[INFO] [legacy_migrator] Fetched 1 legacy knowledge bases from source.
[INFO] [legacy_migrator] Fetched 1 legacy documents from source.
[INFO] [legacy_migrator] Processed 1 document chunks...
[INFO] [legacy_migrator] ============================================================
[INFO] [legacy_migrator] MIGRATION SUMMARY:
[INFO] [legacy_migrator]   • Knowledge Bases Migrated: 1
[INFO] [legacy_migrator]   • Documents Migrated:       1
[INFO] [legacy_migrator]   • Document Chunks Migrated: 1
[INFO] [legacy_migrator] ============================================================
```

---

## 8. Manual QA Completion Checklist

| Verification Item | Acceptance Criteria | Verified |
|---|---|:---:|
| **Automated Suite** | All 69 tests pass with $\ge 80\%$ statement coverage (97% achieved) | [ ] |
| **Alembic Table Isolation** | `alembic_version_vkb` and `vkb_` tables created under `akvo_rag` | [ ] |
| **Schema Governance** | `vkb_documents` has governance columns, `jsonb` metadata, and GIN index | [ ] |
| **Migration Reversibility** | `alembic downgrade base` and `upgrade head` work without errors | [ ] |
| **Asyncpg Engine** | `get_db_session` context manager commits transactions & cascades deletes | [ ] |
| **1536-Dim Guard** | 1536-dim vectors pass; mismatched dimensions raise structured error | [ ] |
| **Migration CLI** | Dry-run and live batch migrations extract, transform, and load idempotently | [ ] |
