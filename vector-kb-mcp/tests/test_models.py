from datetime import datetime
import pytest
from sqlalchemy import create_engine, select, event, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from models import (
    Base,
    KnowledgeBase,
    Document,
    DocumentChunk,
    ProcessingTask,
)


@pytest.fixture
def db_session():
    """
    Create an isolated in-memory SQLite database session for unit testing.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Enable SQLite foreign key constraint enforcement
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_table_creation(db_session: Session):
    """Test all vector-kb-mcp tables are created with proper metadata."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()

    assert "vkb_knowledge_bases" in tables
    assert "vkb_documents" in tables
    assert "vkb_document_chunks" in tables
    assert "vkb_processing_tasks" in tables


def test_knowledge_base_crud_and_defaults(db_session: Session):
    """Test KnowledgeBase creation, default values, and timestamps."""
    kb = KnowledgeBase(
        name="agri_manuals",
        description="Agricultural manuals and guidelines",
    )
    db_session.add(kb)
    db_session.commit()
    db_session.refresh(kb)

    assert kb.id is not None
    assert kb.name == "agri_manuals"
    assert kb.description == "Agricultural manuals and guidelines"
    assert kb.is_active is True
    assert isinstance(kb.created_at, datetime)
    assert isinstance(kb.updated_at, datetime)


def test_document_creation_and_relationships(db_session: Session):
    """Test Document creation linked to KnowledgeBase."""
    kb = KnowledgeBase(name="water_standards")
    db_session.add(kb)
    db_session.commit()

    doc = Document(
        knowledge_base_id=kb.id,
        file_name="water_quality_2024.pdf",
        file_path="uploads/water_standards/water_quality_2024.pdf",
        file_size=1048576,
        content_type="application/pdf",
        file_hash="a" * 64,
        status="PENDING",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.id is not None
    assert doc.knowledge_base_id == kb.id
    assert doc.file_name == "water_quality_2024.pdf"
    assert doc.knowledge_base.name == "water_standards"
    assert len(kb.documents) == 1
    assert kb.documents[0].id == doc.id


def test_document_unique_constraint(db_session: Session):
    """Test unique constraint on (knowledge_base_id, file_name)."""
    kb = KnowledgeBase(name="unique_kb")
    db_session.add(kb)
    db_session.commit()

    doc1 = Document(
        knowledge_base_id=kb.id,
        file_name="duplicate.pdf",
        file_path="uploads/doc1.pdf",
        file_size=100,
        content_type="application/pdf",
        file_hash="b" * 64,
    )
    db_session.add(doc1)
    db_session.commit()

    doc2 = Document(
        knowledge_base_id=kb.id,
        file_name="duplicate.pdf",
        file_path="uploads/doc2.pdf",
        file_size=200,
        content_type="application/pdf",
        file_hash="c" * 64,
    )
    db_session.add(doc2)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_chunk_creation_and_metadata(db_session: Session):
    """Test DocumentChunk with deterministic hash PK and JSON metadata."""
    kb = KnowledgeBase(name="chunk_kb")
    db_session.add(kb)
    db_session.commit()

    doc = Document(
        knowledge_base_id=kb.id,
        file_name="sample.pdf",
        file_path="uploads/sample.pdf",
        file_size=5000,
        content_type="application/pdf",
        file_hash="d" * 64,
    )
    db_session.add(doc)
    db_session.commit()

    chunk_id = "e" * 64
    chunk = DocumentChunk(
        id=chunk_id,
        kb_id=kb.id,
        document_id=doc.id,
        chunk_index=0,
        file_name=doc.file_name,
        chunk_metadata={"page_number": 1, "section": "Introduction"},
        content_hash="f" * 64,
    )
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    assert chunk.id == chunk_id
    assert chunk.chunk_metadata == {
        "page_number": 1,
        "section": "Introduction",
    }
    assert chunk.knowledge_base.name == "chunk_kb"
    assert chunk.document.file_name == "sample.pdf"
    assert len(doc.chunks) == 1


def test_processing_task_creation(db_session: Session):
    """Test ProcessingTask tracking asynchronous jobs with UUID task_id."""
    kb = KnowledgeBase(name="task_kb")
    db_session.add(kb)
    db_session.commit()

    doc = Document(
        knowledge_base_id=kb.id,
        file_name="task_doc.pdf",
        file_path="uploads/task_doc.pdf",
        file_size=1000,
        content_type="application/pdf",
        file_hash="1" * 64,
    )
    db_session.add(doc)
    db_session.commit()

    task = ProcessingTask(
        knowledge_base_id=kb.id,
        document_id=doc.id,
        task_id="9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
        job_type="INGEST_DOCUMENT",
        status="PROCESSING",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.id is not None
    assert task.task_id == "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
    assert task.status == "PROCESSING"
    assert task.error_message is None
    assert task.knowledge_base.name == "task_kb"
    assert task.document.file_name == "task_doc.pdf"


def test_cascade_delete_knowledge_base(db_session: Session):
    """Test deleting KnowledgeBase cascades to documents, chunks, tasks."""
    kb = KnowledgeBase(name="cascade_kb")
    db_session.add(kb)
    db_session.commit()

    doc = Document(
        knowledge_base_id=kb.id,
        file_name="cascade_doc.pdf",
        file_path="uploads/cascade_doc.pdf",
        file_size=1000,
        content_type="application/pdf",
        file_hash="2" * 64,
    )
    db_session.add(doc)
    db_session.commit()

    chunk = DocumentChunk(
        id="3" * 64,
        kb_id=kb.id,
        document_id=doc.id,
        chunk_index=0,
        file_name=doc.file_name,
        chunk_metadata={"page": 1},
        content_hash="4" * 64,
    )
    db_session.add(chunk)

    task = ProcessingTask(
        knowledge_base_id=kb.id,
        document_id=doc.id,
        task_id="task-uuid-cascade",
        job_type="INGEST_DOCUMENT",
        status="COMPLETED",
    )
    db_session.add(task)
    db_session.commit()

    # Save IDs before deletion
    kb_id = kb.id
    doc_id = doc.id
    chunk_id = chunk.id
    task_pk = task.id

    # Delete the KnowledgeBase
    db_session.delete(kb)
    db_session.commit()

    # Verify all children are deleted
    stmt_kb = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    stmt_doc = select(Document).where(Document.id == doc_id)
    stmt_chunk = select(DocumentChunk).where(DocumentChunk.id == chunk_id)
    stmt_task = select(ProcessingTask).where(ProcessingTask.id == task_pk)

    assert db_session.scalars(stmt_kb).first() is None
    assert db_session.scalars(stmt_doc).first() is None
    assert db_session.scalars(stmt_chunk).first() is None
    assert db_session.scalars(stmt_task).first() is None


def test_document_deletion_set_null_on_processing_task(db_session: Session):
    """Test deleting document sets processing_task.document_id to NULL."""
    kb = KnowledgeBase(name="null_task_kb")
    db_session.add(kb)
    db_session.commit()

    doc = Document(
        knowledge_base_id=kb.id,
        file_name="null_doc.pdf",
        file_path="uploads/null_doc.pdf",
        file_size=1000,
        content_type="application/pdf",
        file_hash="5" * 64,
    )
    db_session.add(doc)
    db_session.commit()

    task = ProcessingTask(
        knowledge_base_id=kb.id,
        document_id=doc.id,
        task_id="task-uuid-null",
        job_type="INGEST_DOCUMENT",
        status="COMPLETED",
    )
    db_session.add(task)
    db_session.commit()

    doc_id = doc.id
    task_pk = task.id

    # Delete the Document only
    db_session.delete(doc)
    db_session.commit()

    # Verify doc is gone, but task still exists with document_id = NULL
    stmt_doc = select(Document).where(Document.id == doc_id)
    stmt_task = select(ProcessingTask).where(ProcessingTask.id == task_pk)

    assert db_session.scalars(stmt_doc).first() is None
    refreshed_task = db_session.scalars(stmt_task).first()
    assert refreshed_task is not None
    assert refreshed_task.document_id is None
    assert refreshed_task.knowledge_base_id == kb.id
