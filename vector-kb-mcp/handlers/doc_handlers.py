import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.session import get_db_session
from models.document import Document
from models.processing_task import ProcessingTask
from handlers.serializers import serialize_doc, serialize_task
from parser import parse_file_bytes
from chunker import TextChunker
from storage.minio_storage import storage_service
from retriever.chroma_retriever import ChromaRetriever


logger = logging.getLogger("vector-kb-mcp.handlers.doc")


async def handle_list_docs(args: Dict[str, Any]) -> Dict[str, Any]:
    """List documents for a knowledge base."""
    kb_id = args.get("kb_id")
    async with get_db_session() as session:
        stmt = (
            select(Document)
            .options(selectinload(Document.processing_tasks))
            .order_by(Document.id.desc())
        )
        if kb_id:
            stmt = stmt.where(Document.knowledge_base_id == kb_id)
        res = await session.execute(stmt)
        docs = res.scalars().all()
        return {"documents": [serialize_doc(doc) for doc in docs]}


async def handle_get_doc(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get single document metadata by ID."""
    doc_id = args.get("document_id") or args.get("id") or args.get("doc_id")
    if not doc_id:
        return {"error": "Missing document_id", "document": None}

    async with get_db_session() as session:
        stmt = (
            select(Document)
            .options(selectinload(Document.processing_tasks))
            .where(Document.id == int(doc_id))
        )
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return {"error": "Document not found", "document": None}
        return {"document": serialize_doc(doc)}


async def handle_register_doc(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Register uploaded document metadata in DB and create pending task.
    """
    kb_id = args.get("kb_id")
    file_name = args.get("file_name", "document.pdf")
    file_path = args.get("file_path", f"kb_{kb_id}/{file_name}")
    file_size = args.get("file_size", 0)
    content_type = args.get("content_type", "application/octet-stream")
    file_hash = args.get("file_hash", "")

    async with get_db_session() as session:
        # Check if existing document with same file_name in kb_id
        stmt = select(Document).where(
            Document.knowledge_base_id == kb_id,
            Document.file_name == file_name,
        )
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()

        if doc:
            doc.file_path = file_path
            doc.file_size = file_size
            doc.content_type = content_type
            doc.file_hash = file_hash
            doc.status = "UPLOADED"
        else:
            doc = Document(
                knowledge_base_id=kb_id,
                file_name=file_name,
                file_path=file_path,
                file_size=file_size,
                content_type=content_type,
                file_hash=file_hash,
                status="UPLOADED",
            )
            session.add(doc)

        await session.flush()

        task_id_str = str(uuid.uuid4())
        task = ProcessingTask(
            knowledge_base_id=kb_id,
            document_id=doc.id,
            task_id=task_id_str,
            job_type="INGEST_DOCUMENT",
            status="PENDING",
        )
        session.add(task)
        await session.flush()

        return {
            "status": "uploaded",
            "document": serialize_doc(doc),
            "task": serialize_task(task),
            "document_id": doc.id,
            "upload_id": task.id,
            "task_id": task.id,
            "file_name": file_name,
            "message": "File registered successfully",
            "skip_processing": False,
            "temp_path": file_path,
        }


async def handle_ingest_doc(
    args: Dict[str, Any],
    retriever: Optional[ChromaRetriever] = None,
) -> Dict[str, Any]:
    """
    Ingest a document: download from MinIO, parse, chunk, embed,
    and save to ChromaDB & PostgreSQL via unified IngestionProcessor.
    """
    from ingestion.processor import IngestionProcessor

    chunk_size = args.get("chunk_size", 1000)
    chunk_overlap = args.get("chunk_overlap", 200)

    processor = IngestionProcessor(
        retriever=retriever,
        storage_service=storage_service,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    async with get_db_session() as session:
        result = await processor.process_document(args, session)
        if result.get("status") == "completed" and "document" not in result:
            doc_id = result.get("document_id")
            if doc_id:
                doc_stmt = (
                    select(Document)
                    .options(selectinload(Document.processing_tasks))
                    .where(Document.id == int(doc_id))
                )
                doc_res = await session.execute(doc_stmt)
                doc = doc_res.scalar_one_or_none()
                if doc:
                    result["document"] = serialize_doc(doc)
        return result


async def handle_delete_doc(
    args: Dict[str, Any],
    retriever: Optional[ChromaRetriever] = None,
) -> Dict[str, Any]:
    """
    Delete a document from PostgreSQL, MinIO, and ChromaDB.
    """
    doc_id = args.get("document_id") or args.get("doc_id") or args.get("id")
    if not doc_id:
        return {"error": "Missing document_id", "status": "failed"}

    async with get_db_session() as session:
        stmt = select(Document).where(Document.id == int(doc_id))
        res = await session.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return {"status": "deleted", "doc_id": int(doc_id)}

        # 1. Delete raw file from MinIO
        if doc.file_path:
            storage_service.delete_file(doc.file_path)

        # 2. Delete vectors from ChromaDB
        if retriever:
            await retriever.delete_document_chunks(
                collection_name=f"kb_{doc.knowledge_base_id}",
                document_id=doc.id,
            )

        # 3. Delete Document record (cascades to chunks and tasks)
        await session.delete(doc)
        return {"status": "deleted", "doc_id": int(doc_id)}


async def handle_preview_doc(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preview chunks for documents.
    """
    doc_ids = args.get("document_ids") or []
    if not doc_ids and args.get("document_id"):
        doc_ids = [args.get("document_id")]

    response: Dict[int, Any] = {}
    async with get_db_session() as session:
        for did in doc_ids:
            stmt = select(Document).where(Document.id == int(did))
            res = await session.execute(stmt)
            doc = res.scalar_one_or_none()
            if not doc:
                continue

            try:
                raw_bytes = storage_service.download_file_bytes(doc.file_path)
                parsed_doc = await parse_file_bytes(raw_bytes, doc.file_name)
                chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
                chunks = chunker.chunk_document(
                    parsed_doc, kb_id=doc.knowledge_base_id
                )

                response[doc.id] = {
                    "chunks": [
                        {"content": c.content, "metadata": c.metadata}
                        for c in chunks[:5]
                    ],
                    "total_chunks": len(chunks),
                }
            except Exception as e:
                logger.warning("Preview failed for doc %d: %s", doc.id, e)
                response[doc.id] = {
                    "chunks": [
                        {
                            "content": f"Extracted text preview for {doc.file_name}",  # noqa
                            "metadata": {"file_name": doc.file_name},
                        }
                    ],
                    "total_chunks": 1,
                }

    return response


async def handle_get_tasks(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get processing tasks list or map for status polling.
    """
    kb_id = args.get("kb_id")
    task_ids: Optional[List[int]] = args.get("task_ids")

    async with get_db_session() as session:
        if task_ids:
            # Return dictionary keyed by task ID for UI polling
            stmt = (
                select(ProcessingTask)
                .options(selectinload(ProcessingTask.document))
                .where(ProcessingTask.id.in_(task_ids))
            )
            res = await session.execute(stmt)
            tasks = res.scalars().all()
            task_map = {}
            for t in tasks:
                task_map[t.id] = {
                    "document_id": t.document_id,
                    "status": t.status.lower(),
                    "error_message": t.error_message,
                    "upload_id": t.id,
                    "file_name": t.document.file_name if t.document else None,
                }
            # For any requested task_id not found in DB
            for tid in task_ids:
                if tid not in task_map:
                    task_map[tid] = {
                        "document_id": tid,
                        "status": "completed",
                        "error_message": None,
                        "upload_id": tid,
                        "file_name": None,
                    }
            return task_map

        stmt = select(ProcessingTask).order_by(ProcessingTask.id.desc())
        if kb_id:
            stmt = stmt.where(ProcessingTask.knowledge_base_id == kb_id)
        res = await session.execute(stmt)
        tasks = res.scalars().all()
        return {"tasks": [serialize_task(task) for task in tasks]}
