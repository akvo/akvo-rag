import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import select

from models.base import Base
from models.knowledge_base import KnowledgeBase
from models.document import Document
from models.document_chunk import DocumentChunk
from models.processing_task import ProcessingTask
from core.exceptions import SecurityValidationError


@pytest.fixture
async def async_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    # Seed Knowledge Base
    async with session_factory() as session:
        kb = KnowledgeBase(
            id=1,
            name="Test KB",
            description="Knowledge Base for Ingestion Tests",
            embedding_model="text-embedding-3-small",
            embedding_dim=1536,
        )
        session.add(kb)
        await session.commit()

    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_ingestion_processor_success(
    async_test_db, mock_openai_client, mock_chroma_client
):
    from ingestion.processor import IngestionProcessor

    mock_minio = MagicMock()
    # Mock get_object to return sample text stream
    sample_text = (
        b"This is the first sentence for vector ingestion.\n\n"
        b"This is the second paragraph."
    )
    mock_response = MagicMock()
    mock_response.read.return_value = sample_text
    mock_minio.get_object.return_value = mock_response

    processor = IngestionProcessor(
        minio_client=mock_minio,
        openai_client=mock_openai_client,
        chroma_client=mock_chroma_client,
    )

    payload = {
        "document_id": "doc-uuid-1",
        "kb_id": 1,
        "minio_bucket": "documents",
        "minio_key": "kb_1/doc-uuid-1_sample.txt",
        "filename": "sample.txt",
        "file_size": len(sample_text),
        "content_type": "text/plain",
    }

    async with async_test_db() as session:
        await processor.process_document(payload, session)

    # Assert document record created and INDEXED in DB
    async with async_test_db() as session:
        doc_stmt = select(Document).where(Document.file_name == "sample.txt")
        res = await session.execute(doc_stmt)
        doc = res.scalar_one_or_none()
        assert doc is not None
        assert doc.status == "INDEXED"

        # Assert chunks inserted
        chunks_stmt = select(DocumentChunk).where(
            DocumentChunk.document_id == doc.id
        )
        chunks_res = await session.execute(chunks_stmt)
        chunks = chunks_res.scalars().all()
        assert len(chunks) >= 1

        # Assert processing task marked COMPLETED
        task_stmt = select(ProcessingTask).where(
            ProcessingTask.document_id == doc.id
        )
        task_res = await session.execute(task_stmt)
        task = task_res.scalar_one_or_none()
        assert task is not None
        assert task.status == "COMPLETED"


@pytest.mark.asyncio
async def test_ingestion_processor_cross_tenant_rejection(
    async_test_db, mock_openai_client, mock_chroma_client
):
    from ingestion.processor import IngestionProcessor

    mock_minio = MagicMock()
    processor = IngestionProcessor(
        minio_client=mock_minio,
        openai_client=mock_openai_client,
        chroma_client=mock_chroma_client,
    )

    # Cross-tenant: payload requests kb_id=2 but minio_key points to kb_1
    payload = {
        "document_id": "doc-uuid-attack",
        "kb_id": 2,
        "minio_bucket": "documents",
        "minio_key": "kb_1/doc_secret.pdf",
        "filename": "secret.pdf",
    }

    with pytest.raises(SecurityValidationError) as exc_info:
        async with async_test_db() as session:
            await processor.process_document(payload, session)

    assert "Invalid S3 key prefix" in str(exc_info.value)
    mock_minio.get_object.assert_not_called()


@pytest.mark.asyncio
async def test_ingestion_processor_empty_content_failure(
    async_test_db, mock_openai_client, mock_chroma_client
):
    from ingestion.processor import IngestionProcessor

    mock_minio = MagicMock()
    mock_response = MagicMock()
    mock_response.read.return_value = b"   \n  \t  "
    mock_minio.get_object.return_value = mock_response

    processor = IngestionProcessor(
        minio_client=mock_minio,
        openai_client=mock_openai_client,
        chroma_client=mock_chroma_client,
    )

    payload = {
        "document_id": "doc-uuid-empty",
        "kb_id": 1,
        "minio_bucket": "documents",
        "minio_key": "kb_1/empty.txt",
        "filename": "empty.txt",
    }

    async with async_test_db() as session:
        await processor.process_document(payload, session)

    # Assert document record is marked FAILED/ERROR
    async with async_test_db() as session:
        doc_stmt = select(Document).where(Document.file_name == "empty.txt")
        res = await session.execute(doc_stmt)
        doc = res.scalar_one_or_none()
        assert doc is not None
        assert doc.status in ("FAILED", "ERROR")

        task_stmt = select(ProcessingTask).where(
            ProcessingTask.document_id == doc.id
        )
        task_res = await session.execute(task_stmt)
        task = task_res.scalar_one_or_none()
        assert task is not None
        assert task.status == "FAILED"
        assert "No extractable text" in str(task.error_message)


@pytest.mark.asyncio
async def test_ingestion_processor_batch_embedding_split(
    async_test_db, mock_chroma_client
):
    from ingestion.processor import IngestionProcessor

    mock_openai = MagicMock()
    mock_openai.embeddings = MagicMock()
    mock_openai.embeddings.create = AsyncMock(
        side_effect=lambda input, model: MagicMock(
            data=[MagicMock(embedding=[0.01] * 1536) for _ in input]
        )
    )

    mock_minio = MagicMock()
    large_text = (
        "Paragraph sentence line content data information.\n\n" * 50
    ).encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = large_text
    mock_minio.get_object.return_value = mock_response

    processor = IngestionProcessor(
        minio_client=mock_minio,
        openai_client=mock_openai,
        chroma_client=mock_chroma_client,
        chunk_size=50,
        chunk_overlap=10,
        batch_size=5,
    )

    payload = {
        "document_id": "doc-large-1",
        "kb_id": 1,
        "minio_bucket": "documents",
        "minio_key": "kb_1/large.txt",
        "filename": "large.txt",
    }

    async with async_test_db() as session:
        await processor.process_document(payload, session)

    # Embeddings API should be called in multiple batches
    assert mock_openai.embeddings.create.call_count > 1


@pytest.mark.asyncio
async def test_ingestion_worker_event_loop_and_shutdown():
    import fakeredis.aioredis
    from ingestion.worker import IngestionWorker

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch(
        "ingestion.worker.redis.from_url", return_value=fake_redis
    ), patch("ingestion.worker.Minio"), patch(
        "ingestion.worker.AsyncOpenAI"
    ), patch(
        "ingestion.worker.chromadb.HttpClient"
    ):

        worker = IngestionWorker()
        worker.redis_client = fake_redis

        # Mock processor
        worker.processor = MagicMock()
        worker.processor.process_document = AsyncMock()

        # Enqueue sample task
        payload = {
            "document_id": "test-123",
            "kb_id": 1,
            "minio_bucket": "documents",
            "minio_key": "kb_1/doc.pdf",
            "filename": "doc.pdf",
        }
        await fake_redis.rpush("document_ingestion", json.dumps(payload))

        # Start worker in background task
        worker_task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.05)

        # Stop worker
        await worker.shutdown()
        await worker_task

        # Verify task was dequeued and processed
        assert worker.processor.process_document.called
        assert not worker.running


@pytest.mark.asyncio
async def test_ingestion_worker_malformed_json_handling():
    import fakeredis.aioredis
    from ingestion.worker import IngestionWorker

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch(
        "ingestion.worker.redis.from_url", return_value=fake_redis
    ), patch("ingestion.worker.Minio"), patch(
        "ingestion.worker.AsyncOpenAI"
    ), patch(
        "ingestion.worker.chromadb.HttpClient"
    ):

        worker = IngestionWorker()
        worker.redis_client = fake_redis
        worker.processor = MagicMock()
        worker.processor.process_document = AsyncMock()

        # Enqueue malformed JSON
        await fake_redis.rpush("document_ingestion", "INVALID_NOT_JSON")

        worker_task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.05)
        await worker.shutdown()
        await worker_task

        # Worker should not crash, process_document should not be called
        assert not worker.processor.process_document.called
