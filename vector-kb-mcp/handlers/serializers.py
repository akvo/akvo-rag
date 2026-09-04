from typing import Any, Dict
from models.knowledge_base import KnowledgeBase
from models.document import Document
from models.processing_task import ProcessingTask


def serialize_kb(kb: KnowledgeBase) -> Dict[str, Any]:
    """Serialize a KnowledgeBase SQLAlchemy model instance to dictionary."""
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "is_active": kb.is_active,
        "embedding_model": kb.embedding_model,
        "embedding_dim": kb.embedding_dim,
        "created_at": (
            kb.created_at.isoformat() if kb.created_at else None
        ),
        "updated_at": (
            kb.updated_at.isoformat() if kb.updated_at else None
        ),
        "documents": [
            {
                "id": doc.id,
                "file_name": doc.file_name,
                "file_path": doc.file_path,
                "file_size": doc.file_size,
                "content_type": doc.content_type,
                "status": doc.status,
                "created_at": (
                    doc.created_at.isoformat() if doc.created_at else None
                ),
            }
            for doc in (kb.documents or [])
        ],
    }


def serialize_doc(doc: Document) -> Dict[str, Any]:
    """Serialize a Document SQLAlchemy model instance to dictionary."""
    return {
        "id": doc.id,
        "knowledge_base_id": doc.knowledge_base_id,
        "file_name": doc.file_name,
        "file_path": doc.file_path,
        "file_size": doc.file_size,
        "content_type": doc.content_type,
        "file_hash": doc.file_hash,
        "status": doc.status,
        "doc_version": doc.doc_version,
        "issuing_authority": doc.issuing_authority,
        "effective_date": (
            doc.effective_date.isoformat() if doc.effective_date else None
        ),
        "doc_type": doc.doc_type,
        "jurisdiction": doc.jurisdiction,
        "metadata": doc.metadata_,
        "created_at": (
            doc.created_at.isoformat() if doc.created_at else None
        ),
        "updated_at": (
            doc.updated_at.isoformat() if doc.updated_at else None
        ),
    }


def serialize_task(task: ProcessingTask) -> Dict[str, Any]:
    """Serialize a ProcessingTask SQLAlchemy model instance to dictionary."""
    return {
        "id": task.id,
        "task_id": task.task_id,
        "knowledge_base_id": task.knowledge_base_id,
        "document_id": task.document_id,
        "job_type": task.job_type,
        "status": task.status,
        "error_message": task.error_message,
        "created_at": (
            task.created_at.isoformat() if task.created_at else None
        ),
        "updated_at": (
            task.updated_at.isoformat() if task.updated_at else None
        ),
    }

