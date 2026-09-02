import pytest
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import select

from core.config import settings
from models import (
    Base,
    KnowledgeBase,
    Document,
    DocumentChunk,
    ProcessingTask,
)


@pytest.mark.asyncio
async def test_live_postgresql_schema_and_cascade_integration():
    """Verify models against live PostgreSQL 17 container via asyncpg."""
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async with engine.begin() as conn:
            # Create all tables on PostgreSQL 17
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        pytest.skip(
            f"Live PostgreSQL not reachable ({exc}); "
            "skipping integration test."
        )

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # 1. Insert KnowledgeBase
        kb = KnowledgeBase(
            name="pg17_live_kb",
            description="Integration test Knowledge Base on PostgreSQL 17",
        )
        session.add(kb)
        await session.commit()
        await session.refresh(kb)

        assert kb.id is not None

        # 2. Insert Document
        doc = Document(
            knowledge_base_id=kb.id,
            file_name="pg17_doc.pdf",
            file_path="minio/pg17_doc.pdf",
            file_size=2048,
            content_type="application/pdf",
            file_hash="p" * 64,
            status="INDEXED",
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.id is not None

        # 3. Insert DocumentChunk with native JSONB
        chunk = DocumentChunk(
            id="c" * 64,
            kb_id=kb.id,
            document_id=doc.id,
            chunk_index=0,
            file_name=doc.file_name,
            chunk_metadata={
                "page": 1,
                "section": "PostgreSQL 17 Integration",
                "authority": "Akvo RAG Platform",
            },
            content_hash="h" * 64,
        )
        session.add(chunk)

        # 4. Insert ProcessingTask
        task = ProcessingTask(
            knowledge_base_id=kb.id,
            document_id=doc.id,
            task_id="pg17-task-uuid-live",
            job_type="INGEST_DOCUMENT",
            status="COMPLETED",
        )
        session.add(task)
        await session.commit()

        # 5. Query and verify JSONB extraction
        result = await session.execute(
            select(DocumentChunk).where(DocumentChunk.id == "c" * 64)
        )
        fetched_chunk = result.scalar_one()
        assert fetched_chunk.chunk_metadata["authority"] == "Akvo RAG Platform"

        # 6. Verify Cascade Deletion on Live Postgres
        kb_id = kb.id
        doc_id = doc.id
        chunk_id = chunk.id
        task_pk = task.id

        await session.delete(kb)
        await session.commit()

        res_kb = await session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        res_doc = await session.execute(
            select(Document).where(Document.id == doc_id)
        )
        res_chunk = await session.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )
        res_task = await session.execute(
            select(ProcessingTask).where(ProcessingTask.id == task_pk)
        )

        assert res_kb.scalar_one_or_none() is None
        assert res_doc.scalar_one_or_none() is None
        assert res_chunk.scalar_one_or_none() is None
        assert res_task.scalar_one_or_none() is None

    # Cleanup test tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
