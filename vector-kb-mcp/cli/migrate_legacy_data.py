import argparse
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from models import KnowledgeBase, Document, DocumentChunk
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [legacy_migrator] %(message)s",
)
logger = logging.getLogger("legacy_migrator")


class LegacyDataMigrator:
    """
    Idempotent ETL migration pipeline to extract legacy knowledge bases,
    documents, and chunks from standalone PostgreSQL or MySQL databases,
    transform schemas, and load them into unified PostgreSQL 17 (vkb_ tables).
    """

    def __init__(
        self,
        source_url: str,
        target_url: str = settings.DATABASE_URL,
        batch_size: int = 500,
        dry_run: bool = False,
        source_engine: Any = None,
        target_engine: Optional[AsyncEngine] = None,
    ):
        self.source_url = source_url
        self.target_url = target_url
        self.batch_size = batch_size
        self.dry_run = dry_run
        self.source_engine = source_engine or create_engine(source_url)
        self.target_engine: AsyncEngine = target_engine or create_async_engine(
            target_url
        )

    def _build_insert_stmt(self, model: Any, values: Dict[str, Any]):
        """
        Build dialect-aware ON CONFLICT DO NOTHING insert statement.
        Supports both PostgreSQL (production) and SQLite (testing).
        """
        dialect_name = self.target_engine.dialect.name
        if dialect_name == "postgresql":
            return (
                pg_insert(model)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["id"])
            )
        elif dialect_name == "sqlite":
            return (
                sqlite_insert(model)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["id"])
            )
        else:
            return (
                pg_insert(model)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["id"])
            )

    async def migrate_all(self) -> Dict[str, int]:
        """
        Execute full migration sequence in topological dependency order.
        Returns summary count dictionary.
        """
        logger.info(
            "Starting legacy data migration (dry_run=%s, batch_size=%d)",
            self.dry_run,
            self.batch_size,
        )
        logger.info("Source database: %s", self.source_url)
        logger.info("Target database: %s", self.target_url)

        kb_count = await self.migrate_knowledge_bases()
        doc_count = await self.migrate_documents()
        chunk_count = await self.migrate_chunks()

        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY:")
        logger.info("  • Knowledge Bases Migrated: %d", kb_count)
        logger.info("  • Documents Migrated:       %d", doc_count)
        logger.info("  • Document Chunks Migrated: %d", chunk_count)
        logger.info("=" * 60)

        return {
            "knowledge_bases": kb_count,
            "documents": doc_count,
            "document_chunks": chunk_count,
        }

    @staticmethod
    def _sanitize_null_bytes(val: Any) -> Any:
        """
        Recursively remove null bytes (\x00 / \u0000) from strings,
        dicts, and lists to satisfy PostgreSQL UTF-8 text/JSONB constraints.
        """
        if isinstance(val, str):
            return val.replace("\x00", "").replace("\u0000", "")
        elif isinstance(val, dict):
            return {
                LegacyDataMigrator._sanitize_null_bytes(k): (
                    LegacyDataMigrator._sanitize_null_bytes(v)
                )
                for k, v in val.items()
            }
        elif isinstance(val, list):
            return [
                LegacyDataMigrator._sanitize_null_bytes(item) for item in val
            ]
        return val

    @staticmethod
    def _parse_datetime(dt_val: Any) -> Optional[datetime]:
        """
        Safely convert string or raw timestamps into timezone-aware datetime.
        """
        if dt_val is None:
            return None
        if isinstance(dt_val, datetime):
            return dt_val
        if isinstance(dt_val, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
            except Exception:
                try:
                    return datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return None
        return None

    async def migrate_knowledge_bases(self) -> int:
        """Extract legacy knowledge bases and load into vkb_knowledge_bases."""
        with self.source_engine.connect() as conn:
            query = text("SELECT * FROM knowledge_bases ORDER BY id ASC")
            rows = conn.execute(query).mappings().all()

        logger.info(
            "Fetched %d legacy knowledge bases from source.", len(rows)
        )
        if self.dry_run or not rows:
            return len(rows)

        async with AsyncSession(self.target_engine) as session:
            for row in rows:
                values = {
                    "id": row["id"],
                    "name": self._sanitize_null_bytes(row["name"]),
                    "description": self._sanitize_null_bytes(
                        row.get("description")
                    ),
                    "is_active": True,
                    "embedding_model": "text-embedding-3-small",
                    "embedding_dim": 1536,
                    "created_at": self._parse_datetime(row.get("created_at")),
                    "updated_at": self._parse_datetime(row.get("updated_at")),
                }
                # Filter out None values for timestamps so server_default works
                values = {
                    k: v
                    for k, v in values.items()
                    if v is not None or k in ("description",)
                }
                stmt = self._build_insert_stmt(KnowledgeBase, values)
                await session.execute(stmt)
            await session.commit()

        return len(rows)

    async def migrate_documents(self) -> int:
        """Extract legacy documents and load into vkb_documents."""
        with self.source_engine.connect() as conn:
            query = text("SELECT * FROM documents ORDER BY id ASC")
            rows = conn.execute(query).mappings().all()

        logger.info("Fetched %d legacy documents from source.", len(rows))
        if self.dry_run or not rows:
            return len(rows)

        async with AsyncSession(self.target_engine) as session:
            for row in rows:
                kb_id = row.get("knowledge_base_id") or row.get("kb_id")
                values = {
                    "id": row["id"],
                    "knowledge_base_id": kb_id,
                    "file_name": self._sanitize_null_bytes(row["file_name"]),
                    "file_path": self._sanitize_null_bytes(row["file_path"]),
                    "file_size": row["file_size"],
                    "content_type": self._sanitize_null_bytes(
                        row.get("content_type")
                    ),
                    "file_hash": row["file_hash"],
                    "status": "INDEXED",
                    "doc_version": None,
                    "issuing_authority": None,
                    "doc_type": "LEGACY",
                    "jurisdiction": None,
                    "metadata_": None,
                    "created_at": self._parse_datetime(row.get("created_at")),
                    "updated_at": self._parse_datetime(row.get("updated_at")),
                }
                values = {
                    k: v
                    for k, v in values.items()
                    if v is not None
                    or k
                    in (
                        "doc_version",
                        "issuing_authority",
                        "jurisdiction",
                        "metadata_",
                    )
                }
                stmt = self._build_insert_stmt(Document, values)
                await session.execute(stmt)
            await session.commit()

        return len(rows)

    async def migrate_chunks(self) -> int:
        """Stream legacy chunks in batches and load to vkb_document_chunks."""
        with self.source_engine.connect() as conn:
            query = text("SELECT * FROM document_chunks ORDER BY id ASC")
            result = conn.execute(query)
            total = 0

            while True:
                rows = result.fetchmany(self.batch_size)
                if not rows:
                    break

                if not self.dry_run:
                    async with AsyncSession(self.target_engine) as session:
                        for row in rows:
                            m = row._mapping
                            # Safely parse JSON metadata
                            chunk_metadata = m.get("chunk_metadata")
                            if isinstance(chunk_metadata, str):
                                try:
                                    chunk_metadata = json.loads(chunk_metadata)
                                except Exception:
                                    chunk_metadata = {"raw": chunk_metadata}
                            elif not isinstance(chunk_metadata, dict):
                                chunk_metadata = {}

                            chunk_metadata = self._sanitize_null_bytes(
                                chunk_metadata
                            )

                            kb_id = m.get("kb_id") or m.get(
                                "knowledge_base_id"
                            )
                            content_hash = m.get("hash") or m.get(
                                "content_hash"
                            )

                            values = {
                                "id": str(m["id"]),
                                "kb_id": kb_id,
                                "document_id": m["document_id"],
                                "chunk_index": m.get("chunk_index", 0),
                                "file_name": self._sanitize_null_bytes(
                                    m.get("file_name", "")
                                ),
                                "chunk_metadata": chunk_metadata,
                                "content_hash": content_hash,
                                "created_at": self._parse_datetime(
                                    m.get("created_at")
                                ),
                            }
                            values = {
                                k: v
                                for k, v in values.items()
                                if v is not None
                            }
                            stmt = self._build_insert_stmt(
                                DocumentChunk, values
                            )
                            await session.execute(stmt)
                        await session.commit()

                total += len(rows)
                logger.info("Processed %d document chunks...", total)

            return total


def build_arg_parser() -> argparse.ArgumentParser:
    """Build and configure command line argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Migrate legacy standalone Vector KB data into unified "
            "PostgreSQL 17 (vkb_ tables)"
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--source-url",
        dest="source_url",
        help=(
            "Source connection URL "
            "(postgresql://... or mysql+pymysql://...)"
        ),
    )
    source_group.add_argument(
        "--source-mysql-url",
        dest="source_url",
        help="Source MySQL connection URL (mysql+pymysql://...)",
    )
    parser.add_argument(
        "--target-pg-url",
        default=settings.DATABASE_URL,
        help="Target PostgreSQL URL (postgresql+asyncpg://...)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch chunk insert size (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform extraction without modifying target database",
    )
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    migrator = LegacyDataMigrator(
        source_url=args.source_url,
        target_url=args.target_pg_url,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    asyncio.run(migrator.migrate_all())


if __name__ == "__main__":
    main()
