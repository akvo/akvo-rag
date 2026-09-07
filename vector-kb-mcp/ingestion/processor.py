import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.exceptions import DocumentProcessingError, SecurityValidationError
from models.document import Document
from models.document_chunk import DocumentChunk
from models.processing_task import ProcessingTask
from parser import parse_file_bytes
from chunker import TextChunker, DocumentChunkDTO
from storage.minio_storage import (
    MinioStorageService,
    storage_service as default_storage,
)
from retriever.chroma_retriever import ChromaRetriever

logger = logging.getLogger("vector-kb-mcp.ingestion.processor")


class IngestionProcessor:
    """
    Unified, DRY document ingestion pipeline processor.
    Handles streaming MinIO download, text parsing, deterministic chunking,
    batch embedding generation, ChromaDB vector upsertion, and atomic
    PostgreSQL 17 state management.
    """

    def __init__(
        self,
        minio_client: Optional[Any] = None,
        openai_client: Optional[AsyncOpenAI] = None,
        chroma_client: Optional[Any] = None,
        retriever: Optional[ChromaRetriever] = None,
        storage_service: Optional[MinioStorageService] = None,
        embedding_model: str = "text-embedding-3-small",
        expected_dim: int = 1536,
        batch_size: int = 100,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.storage = storage_service or default_storage
        if minio_client is not None:
            self.storage = MinioStorageService(client_override=minio_client)

        self.openai = openai_client
        self.chroma = chroma_client
        self.embedding_model = embedding_model
        self.expected_dim = expected_dim
        self.batch_size = batch_size
        self.chunker = TextChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        if retriever is not None:
            self.retriever = retriever
        elif chroma_client is not None and openai_client is not None:
            self.retriever = ChromaRetriever(
                chroma_client=chroma_client,
                openai_client=openai_client,
                embedding_model=embedding_model,
                expected_dim=expected_dim,
            )
        else:
            self.retriever = None

    async def process_document(
        self, task_payload: Dict[str, Any], db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Execute end-to-end ingestion on a task payload or RPC argument dict.
        """
        doc_id_raw = (
            task_payload.get("document_id")
            or task_payload.get("doc_id")
            or task_payload.get("id")
        )
        upload_id = task_payload.get("upload_id") or task_payload.get(
            "task_id"
        )
        kb_id_raw = task_payload.get("kb_id")
        bucket = task_payload.get("minio_bucket", "documents")
        key = task_payload.get("minio_key") or task_payload.get(
            "file_path", ""
        )
        filename = task_payload.get("filename") or task_payload.get(
            "file_name", ""
        )
        content_type = task_payload.get(
            "content_type", "application/octet-stream"
        )
        file_size = task_payload.get("file_size", 0)

        # 1. Resolve / Create Document Record in DB
        doc = await self._resolve_document(
            db=db,
            doc_id_raw=doc_id_raw,
            upload_id=upload_id,
            kb_id_raw=kb_id_raw,
            filename=filename,
            key=key,
            file_size=file_size,
            content_type=content_type,
        )
        if not doc:
            raise DocumentProcessingError(
                "Document could not be found or created."
            )

        kb_id = doc.knowledge_base_id
        filename = doc.file_name
        key = doc.file_path

        # 2. Security Check: Cross-Tenant Key Prefix Isolation
        expected_prefix = f"kb_{kb_id}/"
        if not key.startswith(expected_prefix):
            raise SecurityValidationError(
                f"Invalid S3 key prefix '{key}' for KB #{kb_id}. "
                f"Expected prefix '{expected_prefix}'"
            )

        task = await self._resolve_task(
            db=db,
            doc=doc,
            upload_id=upload_id,
            task_id_raw=str(
                task_payload.get("task_id") or doc_id_raw or doc.id
            ),
        )

        doc.status = "PROCESSING"
        task.status = "PROCESSING"
        await db.commit()

        try:
            # 3. Stream Download File from MinIO
            raw_bytes = await asyncio.to_thread(
                self.storage.download_file_bytes, key, bucket
            )
            if not raw_bytes:
                raise DocumentProcessingError(
                    f"Downloaded zero bytes from MinIO for key '{key}'"
                )

            # Security Check: File Size Ceiling (50MB)
            if len(raw_bytes) > 50 * 1024 * 1024:
                raise DocumentProcessingError(
                    f"File '{filename}' exceeds maximum allowed size of 50MB"
                )

            doc.file_hash = hashlib.sha256(raw_bytes).hexdigest()
            doc.file_size = len(raw_bytes)

            # 4. Extract Text via Appropriate Parser
            parsed_doc = await self._parse_file_bytes(raw_bytes, filename)

            # Check if any extractable text was found
            has_text = any(p.text and p.text.strip() for p in parsed_doc.pages)
            if not has_text:
                raise DocumentProcessingError(
                    f"No extractable text found in '{filename}'"
                )

            # Security Check: Extracted Text Ceiling (25MB)
            total_text_len = sum(len(p.text) for p in parsed_doc.pages)
            if total_text_len > 25 * 1024 * 1024:
                raise DocumentProcessingError(
                    f"Extracted text from '{filename}' exceeds 25MB safety ceiling"  # noqa
                )

            # 5. Split Text into Deterministic Chunks
            chunks: List[DocumentChunkDTO] = self.chunker.chunk_document(
                parsed_doc, kb_id=kb_id
            )
            if not chunks:
                raise DocumentProcessingError(
                    f"No text chunks generated for '{filename}'"
                )

            # 6. Generate Batch Embeddings & Upsert to ChromaDB
            await self._embed_and_upsert_chunks(
                kb_id=kb_id,
                doc_id=doc.id,
                chunks=chunks,
                filename=filename,
            )

            # 7. Atomically Persist Chunks and Update Status in PostgreSQL 17
            await db.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == doc.id
                )
            )

            for c in chunks:
                db_chunk = DocumentChunk(
                    id=c.chunk_id,
                    kb_id=kb_id,
                    document_id=doc.id,
                    chunk_index=c.chunk_index,
                    file_name=filename,
                    chunk_metadata={
                        **c.metadata,
                        "document_id": doc.id,
                    },
                    content_hash=c.content_hash,
                )
                db.add(db_chunk)

            doc.status = "INDEXED"
            current_meta = doc.metadata_ or {}
            current_meta["chunk_count"] = len(chunks)
            current_meta["total_pages"] = parsed_doc.total_pages
            doc.metadata_ = current_meta

            task.status = "COMPLETED"
            task.error_message = None
            await db.commit()

            logger.info(
                "Document %d ('%s') successfully indexed with %d chunks.",
                doc.id,
                filename,
                len(chunks),
            )
            return {
                "status": "completed",
                "document_id": doc.id,
                "kb_id": kb_id,
                "total_chunks": len(chunks),
                "file_name": filename,
            }

        except Exception as exc:
            logger.error(
                "Ingestion failed for document '%s' (KB %d): %s",
                filename,
                kb_id,
                exc,
                exc_info=True,
            )
            await db.rollback()
            # Reload / set FAILED state
            try:
                db.add(doc)
                db.add(task)
                doc.status = "FAILED"
                task.status = "FAILED"
                task.error_message = str(exc)[:1024]
                await db.commit()
            except Exception as commit_err:
                logger.warning(
                    "Failed to save error status to DB: %s", commit_err
                )
            return {
                "status": "failed",
                "document_id": doc.id,
                "kb_id": kb_id,
                "error": str(exc),
            }

    async def _resolve_document(
        self,
        db: AsyncSession,
        doc_id_raw: Any,
        upload_id: Any,
        kb_id_raw: Any,
        filename: str,
        key: str,
        file_size: int,
        content_type: str,
    ) -> Optional[Document]:
        """Find existing document or create a new row."""
        doc = None
        if isinstance(doc_id_raw, int) or (
            isinstance(doc_id_raw, str) and doc_id_raw.isdigit()
        ):
            stmt = select(Document).where(Document.id == int(doc_id_raw))
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()

        if not doc and upload_id:
            try:
                task_stmt = select(ProcessingTask).where(
                    ProcessingTask.id == int(upload_id)
                )
                task_res = await db.execute(task_stmt)
                pt = task_res.scalar_one_or_none()
                if pt and pt.document_id:
                    doc_stmt = select(Document).where(
                        Document.id == pt.document_id
                    )
                    doc_res = await db.execute(doc_stmt)
                    doc = doc_res.scalar_one_or_none()
            except (ValueError, TypeError):
                pass

        kb_id = (
            int(kb_id_raw)
            if kb_id_raw
            else (doc.knowledge_base_id if doc else 0)
        )

        if not doc and key and kb_id:
            stmt = select(Document).where(
                Document.knowledge_base_id == kb_id,
                Document.file_path == key,
            )
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()

        if not doc and filename and kb_id:
            stmt = select(Document).where(
                Document.knowledge_base_id == kb_id,
                Document.file_name == filename,
            )
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()

        if not doc and kb_id:
            final_key = key or f"kb_{kb_id}/{filename}"
            doc = Document(
                knowledge_base_id=kb_id,
                file_name=filename or "document.pdf",
                file_path=final_key,
                file_size=file_size,
                content_type=content_type,
                file_hash=hashlib.sha256(
                    (filename or "doc").encode()
                ).hexdigest(),
                status="PROCESSING",
            )
            db.add(doc)
            await db.flush()

        return doc

    async def _resolve_task(
        self,
        db: AsyncSession,
        doc: Document,
        upload_id: Any,
        task_id_raw: str,
    ) -> ProcessingTask:
        """Find existing processing task or create a new row."""
        task = None
        if upload_id:
            try:
                task_stmt = select(ProcessingTask).where(
                    ProcessingTask.id == int(upload_id)
                )
                task_res = await db.execute(task_stmt)
                task = task_res.scalar_one_or_none()
            except (ValueError, TypeError):
                pass

        if not task:
            stmt = (
                select(ProcessingTask)
                .where(
                    ProcessingTask.document_id == doc.id,
                    ProcessingTask.job_type == "INGEST_DOCUMENT",
                )
                .order_by(ProcessingTask.id.desc())
            )
            res = await db.execute(stmt)
            task = res.scalars().first()

        if not task:
            task = ProcessingTask(
                knowledge_base_id=doc.knowledge_base_id,
                document_id=doc.id,
                task_id=task_id_raw,
                job_type="INGEST_DOCUMENT",
                status="PROCESSING",
            )
            db.add(task)
            await db.flush()

        return task

    async def _parse_file_bytes(self, raw_bytes: bytes, filename: str):
        """Parse raw bytes via centralized parser helper."""
        return await parse_file_bytes(raw_bytes, filename)

    async def _embed_and_upsert_chunks(
        self,
        kb_id: int,
        doc_id: int,
        chunks: List[DocumentChunkDTO],
        filename: str,
    ) -> None:
        """Embed text chunks and upsert vectors into ChromaDB."""
        if not chunks:
            return

        if self.retriever is None:
            raise DocumentProcessingError(
                "Retriever is not configured for embedding generation."
            )

        chunk_texts = [c.content for c in chunks]
        all_embeddings: List[List[float]] = []

        # Sliced batch embedding
        for i in range(0, len(chunk_texts), self.batch_size):
            batch = chunk_texts[i : i + self.batch_size]  # noqa
            batch_embs = await self.retriever.embed_texts(batch)
            all_embeddings.extend(batch_embs)

        collection_name = f"kb_{kb_id}"
        await self.retriever.upsert_collection_chunks(
            collection_name=collection_name,
            ids=[c.chunk_id for c in chunks],
            embeddings=all_embeddings,
            documents=chunk_texts,
            metadatas=[
                {
                    **c.metadata,
                    "document_id": doc_id,
                    "file_name": filename,
                    "kb_id": kb_id,
                }
                for c in chunks
            ],
        )
