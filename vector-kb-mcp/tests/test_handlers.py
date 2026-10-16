from datetime import date, datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from handlers.serializers import (
    serialize_kb,
    serialize_doc,
    serialize_task,
)
from handlers.query_handlers import handle_query_kb
from models.knowledge_base import KnowledgeBase
from models.document import Document
from models.processing_task import ProcessingTask


def test_serialize_kb():
    kb = KnowledgeBase(
        id=1,
        name="Test KB",
        description="A test knowledge base",
        is_active=True,
        embedding_model="text-embedding-3-small",
        embedding_dim=1536,
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
    )
    kb.documents = []
    data = serialize_kb(kb)
    assert data["id"] == 1
    assert data["name"] == "Test KB"
    assert data["embedding_dim"] == 1536
    assert data["documents"] == []


def test_serialize_doc():
    doc = Document(
        id=10,
        knowledge_base_id=1,
        file_name="report.pdf",
        file_path="kb_1/report.pdf",
        file_size=1024,
        content_type="application/pdf",
        file_hash="a" * 64,
        status="INDEXED",
        doc_version="1.0",
        issuing_authority="Akvo",
        effective_date=date(2026, 1, 1),
        doc_type="STANDARD",
        jurisdiction="Global",
        metadata_={"department": "WASH"},
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    data = serialize_doc(doc)
    assert data["id"] == 10
    assert data["file_name"] == "report.pdf"
    assert data["issuing_authority"] == "Akvo"
    assert data["metadata"] == {"department": "WASH"}


def test_serialize_task():
    task = ProcessingTask(
        id=5,
        task_id="task-123",
        knowledge_base_id=1,
        document_id=10,
        job_type="INGEST_DOCUMENT",
        status="COMPLETED",
        error_message=None,
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
    )
    data = serialize_task(task)
    assert data["id"] == 5
    assert data["task_id"] == "task-123"
    assert data["job_type"] == "INGEST_DOCUMENT"
    assert data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_handle_query_kb_uninitialized_retriever():
    with pytest.raises(
        RuntimeError, match="ChromaRetriever is not initialized"
    ):
        await handle_query_kb({"query": "water"}, retriever=None)


@pytest.mark.asyncio
async def test_handle_query_kb_success():
    mock_retriever = MagicMock()
    mock_chunk = MagicMock()
    mock_chunk.__dict__ = {
        "chunk_id": "c1",
        "text": "Water sanitation",
        "score": 0.95,
    }
    mock_retriever.search = AsyncMock(return_value=[mock_chunk])

    res = await handle_query_kb(
        {"query": "sanitation", "kb_ids": [1], "top_k": 3},
        retriever=mock_retriever,
    )
    assert "chunks" in res
    assert len(res["chunks"]) == 1
    assert res["chunks"][0]["chunk_id"] == "c1"
