# Feature Specification: PostgreSQL Async Adapter & Legacy Data Migration CLI

> **Feature ID:** `008_db_204_postgres_adapter_and_legacy_data_migration_cli_spec`  
> **Task Ref:** `TASK-DB-204`  
> **Target Branch:** `epic/rag-monorepo-mcp`  
> **Status:** `PROPOSED (Under Review)`  
> **Estimated Effort:** `2.0 hrs (Vibe-Coding) / 1.5 days (Traditional)`  
> **Author:** Antigravity Architect / Database & Backend Specialist  
> **Source Repository:** `vector-knowledge-base-mcp-server` (`/Users/galihpratama/Sites/vector-knowledge-base-mcp-server`)  
> **Upstream Reference:** [docs/lld/container_based_rag_platform_lld.md](file:///Users/galihpratama/Sites/akvo-rag/docs/lld/container_based_rag_platform_lld.md) (Sections 6, 8, 9)

---

## 1. Overview & 5W1H Requirements Discovery

### 1.1 Problem Statement
The legacy `vector-knowledge-base-mcp-server` relied on synchronous MySQL database connections (`pymysql`/`mysqlconnector`) with low concurrency connection pools. In the new Option C architecture, `vector-kb-mcp` requires a high-performance **async PostgreSQL database engine (`asyncpg`)** to support concurrent Redis RPC requests without blocking the event loop.

Furthermore, existing knowledge base deployments contain legacy MySQL records across `knowledge_bases`, `documents`, and `document_chunks`. An automated, idempotent **ETL Data Migration CLI** is required to migrate legacy records into PostgreSQL 17 `vkb_` tables without data loss or ID corruption.

### 1.2 5W1H Discovery Lens

| Dimension | Specification |
|---|---|
| **Who** | `vector-kb-mcp` async handlers, ingestion workers, and DevOps migration engineers. |
| **What** | Implement an async PostgreSQL session engine (`asyncpg`, connection pooling, transaction context managers) and an idempotent CLI tool to extract legacy MySQL data and load it into PostgreSQL 17 `vkb_` tables. |
| **Where** | `vector-kb-mcp/db/` (`session.py`, `base.py`), `vector-kb-mcp/cli/` (`migrate_legacy_data.py`, `__init__.py`). |
| **When** | **Phase 2, Step 4** — concluding Phase 2 database infrastructure before moving to Phase 3 Redis RPC bridge. |
| **Why** | Guarantees non-blocking async DB operations under high load and provides a deterministic, zero-downtime path to port existing knowledge bases into PostgreSQL 17. |
| **How** | SQLAlchemy 2.0 `create_async_engine`, `async_sessionmaker`, `asyncpg`, and a multi-threaded batch ETL CLI with `--dry-run` and `--batch-size` flags. |

---

## 2. Architecture & Data Flow Design

### 2.1 ETL Data Migration Pipeline

```mermaid
graph TD
    subgraph LegacySource["Legacy MySQL Source Database"]
        LKB[("knowledge_bases")]
        LDOC[("documents")]
        LCHUNK[("document_chunks")]
    end

    subgraph ETLScript["CLI Tool: python -m cli.migrate_legacy_data"]
        Extractor["1. Extractor<br/>(Batch read via PyMySQL / SQLAlchemy)"]
        Transformer["2. Transformer<br/>- Map table names to vkb_*<br/>- Add embedding_dim = 1536<br/>- Convert JSON to JSONB<br/>- Clean Celery artifacts"]
        Loader["3. Loader<br/>(Async batch insert with ON CONFLICT DO NOTHING)"]
    end

    subgraph TargetPostgres["Target PostgreSQL 17 Database: akvo_rag"]
        TKB[("vkb_knowledge_bases")]
        TDOC[("vkb_documents")]
        TCHUNK[("vkb_document_chunks")]
    end

    LegacySource --> Extractor
    Extractor --> Transformer
    Transformer --> Loader
    Loader --> TargetPostgres
```

---

## 3. Detailed Technical Specifications

### 3.1 Async PostgreSQL Session Manager (`vector-kb-mcp/db/session.py`)

```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from core.config import settings

# Initialize high-performance async engine with asyncpg
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Thread-safe async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager providing transaction-managed DB sessions with auto-rollback."""
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

---

### 3.2 Automated Legacy Data Migration CLI (`vector-kb-mcp/cli/migrate_legacy_data.py`)

```python
import argparse
import asyncio
import logging
from typing import Dict, Any, List
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.dialects.postgresql import insert

from models import KnowledgeBase, Document, DocumentChunk
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("legacy_migrator")

class LegacyDataMigrator:
    def __init__(self, source_url: str, target_url: str, batch_size: int = 500, dry_run: bool = False):
        self.source_url = source_url
        self.target_url = target_url
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.source_engine = create_engine(source_url)
        self.target_engine = create_async_engine(target_url)

    async def migrate_all(self):
        logger.info(f"Starting legacy migration (dry_run={self.dry_run}, batch_size={self.batch_size})")
        
        kb_count = await self.migrate_knowledge_bases()
        doc_count = await self.migrate_documents()
        chunk_count = await self.migrate_chunks()
        
        logger.info("=" * 50)
        logger.info("MIGRATION SUMMARY:")
        logger.info(f"  • Knowledge Bases Migrated: {kb_count}")
        logger.info(f"  • Documents Migrated:       {doc_count}")
        logger.info(f"  • Document Chunks Migrated: {chunk_count}")
        logger.info("=" * 50)

    async def migrate_knowledge_bases(self) -> int:
        with self.source_engine.connect() as conn:
            rows = conn.execute(text("SELECT id, name, description, created_at, updated_at FROM knowledge_bases")).mappings().all()

        logger.info(f"Fetched {len(rows)} legacy knowledge bases")
        if self.dry_run or not rows:
            return len(rows)

        async with AsyncSession(self.target_engine) as session:
            for row in rows:
                stmt = insert(KnowledgeBase).values(
                    id=row["id"],
                    name=row["name"],
                    description=row.get("description"),
                    is_active=True,
                    embedding_model="text-embedding-3-small",
                    embedding_dim=1536,
                    created_at=row.get("created_at"),
                    updated_at=row.get("updated_at")
                ).on_conflict_do_nothing(index_elements=["id"])
                await session.execute(stmt)
            await session.commit()
        return len(rows)

    async def migrate_documents(self) -> int:
        with self.source_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT id, knowledge_base_id, file_name, file_path, file_size, content_type, file_hash, "
                "created_at, updated_at FROM documents"
            )).mappings().all()

        logger.info(f"Fetched {len(rows)} legacy documents")
        if self.dry_run or not rows:
            return len(rows)

        async with AsyncSession(self.target_engine) as session:
            for row in rows:
                stmt = insert(Document).values(
                    id=row["id"],
                    knowledge_base_id=row["knowledge_base_id"],
                    file_name=row["file_name"],
                    file_path=row["file_path"],
                    file_size=row["file_size"],
                    content_type=row["content_type"],
                    file_hash=row["file_hash"],
                    status="INDEXED",
                    doc_version=None,
                    issuing_authority=None,
                    doc_type="LEGACY",
                    created_at=row.get("created_at"),
                    updated_at=row.get("updated_at")
                ).on_conflict_do_nothing(index_elements=["id"])
                await session.execute(stmt)
            await session.commit()
        return len(rows)

    async def migrate_chunks(self) -> int:
        with self.source_engine.connect() as conn:
            result = conn.execute(text("SELECT id, kb_id, document_id, file_name, chunk_metadata, hash, created_at FROM document_chunks"))
            total = 0
            while True:
                rows = result.fetchmany(self.batch_size)
                if not rows:
                    break
                
                if not self.dry_run:
                    async with AsyncSession(self.target_engine) as session:
                        for row in rows:
                            m = row._mapping
                            stmt = insert(DocumentChunk).values(
                                id=m["id"],
                                kb_id=m["kb_id"],
                                document_id=m["document_id"],
                                chunk_index=0,
                                file_name=m["file_name"],
                                chunk_metadata=m.get("chunk_metadata") or {},
                                content_hash=m["hash"],
                                created_at=m.get("created_at")
                            ).on_conflict_do_nothing(index_elements=["id"])
                            await session.execute(stmt)
                        await session.commit()
                total += len(rows)
                logger.info(f"Migrated {total} chunks...")
            return total

def main():
    parser = argparse.ArgumentParser(description="Migrate legacy MySQL vector KB data to PostgreSQL 17")
    parser.add_argument("--source-mysql-url", required=True, help="MySQL source connection URL (mysql+pymysql://...)")
    parser.add_argument("--target-pg-url", default=settings.DATABASE_URL, help="PostgreSQL target URL (postgresql+asyncpg://...)")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch chunk insert size")
    parser.add_argument("--dry-run", action="store_true", help="Perform extraction without writing to PostgreSQL")
    
    args = parser.parse_args()
    migrator = LegacyDataMigrator(
        source_url=args.source_mysql_url,
        target_url=args.target_pg_url,
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    asyncio.run(migrator.migrate_all())

if __name__ == "__main__":
    main()
```

---

## 4. Verification & Quality Gates

### 4.1 CLI Execution Commands

1. **Dry-Run Validation Test:**
   ```bash
   python -m cli.migrate_legacy_data \
     --source-mysql-url "mysql+pymysql://user:pass@host:3306/legacy_db" \
     --dry-run
   # Assert: Connects, counts records across tables, and exits 0 without writing.
   ```

2. **Full Batch Migration Execution:**
   ```bash
   python -m cli.migrate_legacy_data \
     --source-mysql-url "mysql+pymysql://user:pass@host:3306/legacy_db" \
     --batch-size 1000
   # Assert: Exits 0, all records inserted with ON CONFLICT DO NOTHING idempotency.
   ```

3. **Data Integrity & Consistency Assertion:**
   ```sql
   -- Verify KB and document count match source
   SELECT COUNT(*) FROM vkb_knowledge_bases;
   SELECT COUNT(*) FROM vkb_documents;
   SELECT COUNT(*) FROM vkb_document_chunks;
   ```

---

## 5. Subtask Estimation & Breakdown

| Subtask ID | Description | Target Files | Vibe Est. | Trad. Est. | Confidence |
|---|---|---|:---:|:---:|:---:|
| `SUB-204.1` | Build async PostgreSQL session manager (`get_db_session`, connection pooling) | `vector-kb-mcp/db/session.py` `[NEW]` | 0.5 hr | 0.3 day | High (99%) |
| `SUB-204.2` | Implement CLI data migration script (`cli/migrate_legacy_data.py`) | `vector-kb-mcp/cli/migrate_legacy_data.py` `[NEW]` | 0.8 hr | 0.5 day | High (98%) |
| `SUB-204.3` | Implement unit tests for async session lifecycle, rollback, and ETL batching | `vector-kb-mcp/tests/test_db_and_migrator.py` `[NEW]` | 0.4 hr | 0.4 day | High (95%) |
| `SUB-204.4` | Test CLI execution with `--dry-run` and live `--batch-size` options | CLI validation | 0.3 hr | 0.3 day | High (98%) |
| **TOTAL** | | | **2.0 hrs** | **1.5 days** | **High** |

---

## 6. Definition of Done (DoD)

- [ ] `vector-kb-mcp/db/session.py` provides non-blocking `get_db_session()` with connection pooling.
- [ ] `migrate_legacy_data.py` CLI supports `--source-mysql-url`, `--dry-run`, and `--batch-size`.
- [ ] Migration execution is fully idempotent (`ON CONFLICT DO NOTHING`) and preserves legacy primary keys and relationships.
- [ ] Automated tests in `test_db_and_migrator.py` pass with zero errors.
