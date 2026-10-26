import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from models.base import Base
from models.knowledge_base import KnowledgeBase
from handlers.doc_handlers import (
    handle_register_doc,
    handle_ingest_doc,
    handle_delete_doc,
    handle_preview_doc,
    handle_get_tasks,
)


@pytest.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    with patch("handlers.doc_handlers.get_db_session") as mock_db, patch(
        "ingestion.processor.get_db_session"
    ) as mock_proc_db, patch("db.session.get_db_session") as mock_core_db:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _mock_session():
            session = session_factory()
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

        mock_db.side_effect = _mock_session
        mock_proc_db.side_effect = _mock_session
        mock_core_db.side_effect = _mock_session

        # Seed KB
        async with _mock_session() as s:
            kb = KnowledgeBase(
                id=1,
                name="Test KB",
                description="KB for ingestion tests",
                embedding_model="text-embedding-3-small",
                embedding_dim=1536,
            )
            s.add(kb)

        yield session_factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_handle_register_doc(in_memory_db):
    res = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "sample.txt",
            "file_path": "kb_1/sample.txt",
            "file_size": 1024,
            "content_type": "text/plain",
            "file_hash": "abc123hash",
        }
    )
    assert res["status"] == "uploaded"
    assert res["file_name"] == "sample.txt"
    assert res["document_id"] is not None
    assert res["upload_id"] is not None


@pytest.mark.asyncio
async def test_handle_ingest_doc(in_memory_db):
    # 1. Register doc
    reg = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "guide.txt",
            "file_path": "kb_1/guide.txt",
            "file_size": 50,
            "content_type": "text/plain",
            "file_hash": "hash_guide",
        }
    )
    doc_id = reg["document_id"]

    # 2. Mock storage & retriever
    mock_retriever = MagicMock()
    mock_retriever.embed_texts = AsyncMock(return_value=[[0.1] * 1536])
    mock_retriever.upsert_collection_chunks = AsyncMock()

    with patch("handlers.doc_handlers.storage_service") as mock_storage:
        mock_storage.download_file_bytes.return_value = (
            b"This is a test paragraph for knowledge base document ingestion.\n"  # noqa
            b"It contains multiple sentences that will be parsed and chunked."
        )

        res = await handle_ingest_doc(
            {
                "document_id": doc_id,
                "kb_id": 1,
                "chunk_size": 100,
                "chunk_overlap": 20,
            },
            retriever=mock_retriever,
        )

        assert res["status"] == "completed"
        assert res["total_chunks"] >= 1
        assert mock_retriever.embed_texts.called
        assert mock_retriever.upsert_collection_chunks.called


@pytest.mark.asyncio
async def test_handle_ingest_doc_task_id_fallback(in_memory_db):
    # 1. Register doc
    reg = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "guide2.txt",
            "file_path": "kb_1/guide2.txt",
            "file_size": 50,
            "content_type": "text/plain",
            "file_hash": "hash_guide_2",
        }
    )
    task_id = reg["task_id"]

    mock_retriever = MagicMock()
    mock_retriever.embed_texts = AsyncMock(return_value=[[0.1] * 1536])
    mock_retriever.upsert_collection_chunks = AsyncMock()

    with patch("handlers.doc_handlers.storage_service") as mock_storage:
        mock_storage.download_file_bytes.return_value = (
            b"Fallback ingestion test text."
        )

        res = await handle_ingest_doc(
            {
                "upload_id": task_id,
                "task_id": task_id,
                "kb_id": 1,
            },
            retriever=mock_retriever,
        )

        assert res["status"] == "completed"
        assert res["document_id"] is not None


@pytest.mark.asyncio
async def test_handle_preview_doc(in_memory_db):
    reg = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "preview.txt",
            "file_path": "kb_1/preview.txt",
            "file_size": 30,
            "content_type": "text/plain",
            "file_hash": "hash_prev",
        }
    )
    doc_id = reg["document_id"]

    with patch("handlers.doc_handlers.storage_service") as mock_storage:
        mock_storage.download_file_bytes.return_value = (
            b"Preview chunk text content."
        )
        preview = await handle_preview_doc({"document_ids": [doc_id]})

        assert doc_id in preview
        assert preview[doc_id]["total_chunks"] >= 1
        assert len(preview[doc_id]["chunks"]) >= 1


@pytest.mark.asyncio
async def test_handle_get_tasks_polling_format(in_memory_db):
    reg = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "task_doc.txt",
            "file_path": "kb_1/task_doc.txt",
            "file_size": 10,
            "content_type": "text/plain",
            "file_hash": "hash_task",
        }
    )
    task_id = reg["task_id"]

    tasks_res = await handle_get_tasks(
        {"kb_id": 1, "task_ids": [task_id, 999]}
    )
    assert task_id in tasks_res
    assert tasks_res[task_id]["status"] == "pending"
    assert 999 in tasks_res
    assert tasks_res[999]["status"] == "completed"


@pytest.mark.asyncio
async def test_handle_delete_doc(in_memory_db):
    reg = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "to_delete.txt",
            "file_path": "kb_1/to_delete.txt",
            "file_size": 20,
            "content_type": "text/plain",
            "file_hash": "hash_del",
        }
    )
    doc_id = reg["document_id"]

    mock_retriever = MagicMock()
    mock_retriever.delete_document_chunks = AsyncMock()

    with patch("handlers.doc_handlers.storage_service") as mock_storage:
        mock_storage.delete_file.return_value = True

        res = await handle_delete_doc(
            {"document_id": doc_id, "kb_id": 1},
            retriever=mock_retriever,
        )

        assert res["status"] == "deleted"
        assert res["doc_id"] == doc_id
        mock_storage.delete_file.assert_called_once_with("kb_1/to_delete.txt")
        mock_retriever.delete_document_chunks.assert_called_once_with(
            collection_name="kb_1", document_id=doc_id
        )

        # Delete non-existent document
        res_nonexistent = await handle_delete_doc(
            {"document_id": 99999, "kb_id": 1},
            retriever=mock_retriever,
        )
        assert res_nonexistent["status"] == "deleted"


@pytest.mark.asyncio
async def test_handle_preview_doc_fallbacks_and_direct_paths(in_memory_db):
    reg = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "preview_fallback.txt",
            "file_path": "kb_1/preview_fallback.txt",
            "file_size": 30,
            "content_type": "text/plain",
            "file_hash": "hash_fb",
        }
    )
    doc_id = reg["document_id"]

    # 1. Download exception triggers fallback preview text
    with patch("handlers.doc_handlers.storage_service") as mock_storage:
        mock_storage.download_file_bytes.side_effect = Exception("Storage error")
        preview = await handle_preview_doc({"document_ids": [doc_id]})
        assert doc_id in preview
        assert "Extracted text preview" in preview[doc_id]["chunks"][0]["content"]

    # 2. Preview with direct file_paths
    with patch("handlers.doc_handlers.storage_service") as mock_storage:
        mock_storage.download_file_bytes.return_value = b"Direct file path content."
        preview_direct = await handle_preview_doc(
            {"kb_id": 1, "file_paths": ["kb_1/direct.txt"]}
        )
        assert "kb_1/direct.txt" in preview_direct
        assert len(preview_direct["kb_1/direct.txt"]["chunks"]) >= 1

    # 3. Preview with direct file_paths failing
    with patch("handlers.doc_handlers.storage_service") as mock_storage:
        mock_storage.download_file_bytes.side_effect = Exception("Direct path failed")
        preview_fail = await handle_preview_doc(
            {"kb_id": 1, "file_paths": ["kb_1/fail.txt"]}
        )
        assert "kb_1/fail.txt" not in preview_fail


@pytest.mark.asyncio
async def test_handle_get_tasks_extended_scenarios(in_memory_db):
    reg = await handle_register_doc(
        {
            "kb_id": 1,
            "file_name": "ext_task.txt",
            "file_path": "kb_1/uuid-abc-123_ext_task.txt",
            "file_size": 10,
            "content_type": "text/plain",
            "file_hash": "hash_ext",
        }
    )
    task_id = reg["task_id"]

    # 1. Get tasks by kb_id list
    kb_tasks = await handle_get_tasks({"kb_id": 1})
    assert "tasks" in kb_tasks
    assert isinstance(kb_tasks["tasks"], list)

    # 2. Get tasks with string UUID matching file_path
    str_tasks = await handle_get_tasks(
        {"kb_id": 1, "task_ids": ["uuid-abc-123", "nonexistent-uuid-999"]}
    )
    assert "uuid-abc-123" in str_tasks
    assert str_tasks["uuid-abc-123"]["status"] in ("pending", "indexed")
    assert "nonexistent-uuid-999" in str_tasks
    assert str_tasks["nonexistent-uuid-999"]["status"] == "completed"

