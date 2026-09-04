from typing import Any, Dict
from sqlalchemy import select

from db.session import get_db_session
from models.document import Document
from models.processing_task import ProcessingTask
from handlers.serializers import serialize_doc, serialize_task


async def handle_list_docs(args: Dict[str, Any]) -> Dict[str, Any]:
    """List documents for a knowledge base."""
    kb_id = args.get("kb_id")
    async with get_db_session() as session:
        stmt = select(Document).order_by(Document.id.desc())
        if kb_id:
            stmt = stmt.where(Document.knowledge_base_id == kb_id)
        res = await session.execute(stmt)
        docs = res.scalars().all()
        return {"documents": [serialize_doc(doc) for doc in docs]}


async def handle_get_doc(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get single document metadata by ID."""
    doc_id = args.get("document_id") or args.get("id")
    if not doc_id:
        return {"error": "Missing document_id", "document": None}

    async with get_db_session() as session:
        stmt = select(Document).where(Document.id == doc_id)
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return {"error": "Document not found", "document": None}
        return {"document": serialize_doc(doc)}


async def handle_get_tasks(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get processing tasks list."""
    kb_id = args.get("kb_id")
    async with get_db_session() as session:
        stmt = select(ProcessingTask).order_by(ProcessingTask.id.desc())
        if kb_id:
            stmt = stmt.where(ProcessingTask.knowledge_base_id == kb_id)
        res = await session.execute(stmt)
        tasks = res.scalars().all()
        return {"tasks": [serialize_task(task) for task in tasks]}
