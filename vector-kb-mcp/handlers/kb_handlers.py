from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.session import get_db_session
from models.knowledge_base import KnowledgeBase
from models.document import Document
from handlers.serializers import serialize_kb


async def handle_list_kbs(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all knowledge bases or filter by IDs/search term."""
    async with get_db_session() as session:
        stmt = (
            select(KnowledgeBase)
            .options(
                selectinload(KnowledgeBase.documents).selectinload(
                    Document.processing_tasks
                )
            )
            .order_by(KnowledgeBase.id.asc())
        )

        if "kb_ids" in args and args["kb_ids"]:
            stmt = stmt.where(KnowledgeBase.id.in_(args["kb_ids"]))
        if "search" in args and args["search"]:
            stmt = stmt.where(KnowledgeBase.name.ilike(f"%{args['search']}%"))

        res = await session.execute(stmt)
        kbs = res.scalars().all()
        return {"knowledge_bases": [serialize_kb(kb) for kb in kbs]}


async def handle_get_kb(args: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch a single knowledge base by ID."""
    kb_id = args.get("kb_id")
    if not kb_id:
        return {"error": "Missing kb_id", "knowledge_base": None}

    async with get_db_session() as session:
        stmt = (
            select(KnowledgeBase)
            .options(
                selectinload(KnowledgeBase.documents).selectinload(
                    Document.processing_tasks
                )
            )
            .where(KnowledgeBase.id == kb_id)
        )
        res = await session.execute(stmt)
        kb = res.scalar_one_or_none()
        if not kb:
            return {
                "error": "Knowledge base not found",
                "knowledge_base": None,
            }
        return {"knowledge_base": serialize_kb(kb)}


async def handle_create_kb(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new knowledge base."""
    name = args.get("name", "New Knowledge Base")
    description = args.get("description", "")
    model = args.get("embedding_model", "text-embedding-3-small")
    dim = args.get("embedding_dim", 1536)

    async with get_db_session() as session:
        kb = KnowledgeBase(
            name=name,
            description=description,
            embedding_model=model,
            embedding_dim=dim,
            is_active=True,
        )
        session.add(kb)
        await session.flush()
        await session.refresh(kb, ["documents"])
        return {
            "knowledge_base": serialize_kb(kb),
            "status": "created",
            "kb_id": kb.id,
        }


async def handle_update_kb(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing knowledge base."""
    kb_id = args.get("kb_id")
    if not kb_id:
        return {"error": "Missing kb_id"}

    async with get_db_session() as session:
        stmt = (
            select(KnowledgeBase)
            .options(selectinload(KnowledgeBase.documents))
            .where(KnowledgeBase.id == kb_id)
        )
        res = await session.execute(stmt)
        kb = res.scalar_one_or_none()
        if not kb:
            return {"error": "Knowledge base not found"}

        if "name" in args and args["name"] is not None:
            kb.name = args["name"]
        if "description" in args and args["description"] is not None:
            kb.description = args["description"]
        if "is_active" in args and args["is_active"] is not None:
            kb.is_active = args["is_active"]
        await session.flush()
        return {
            "knowledge_base": serialize_kb(kb),
            "status": "updated",
        }


async def handle_delete_kb(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a knowledge base by ID."""
    kb_id = args.get("kb_id")
    if not kb_id:
        return {"error": "Missing kb_id"}

    async with get_db_session() as session:
        stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        res = await session.execute(stmt)
        kb = res.scalar_one_or_none()
        if kb:
            await session.delete(kb)
        return {"status": "deleted", "kb_id": kb_id}
