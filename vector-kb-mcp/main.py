import asyncio
import dataclasses
import json
import logging
import signal
from typing import Any, Awaitable, Callable, Dict, Optional

import chromadb
from openai import AsyncOpenAI
import redis.asyncio as redis

from core.config import Settings, settings as default_settings
from db.migrator import run_vkb_migrations
from db.session import get_db_session
from models.knowledge_base import KnowledgeBase
from models.document import Document
from models.processing_task import ProcessingTask
from retriever.chroma_retriever import ChromaRetriever
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Setup logging
logging.basicConfig(
    level=getattr(logging, default_settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [vector-kb-mcp] %(message)s",
)
logger = logging.getLogger("vector-kb-mcp")


class VectorMCPWorker:
    def __init__(self, settings_override: Optional[Settings] = None):
        self.settings: Settings = settings_override or default_settings
        self.running: bool = False
        self._run_task: Optional[asyncio.Task] = None
        self.redis_client: Optional[redis.Redis] = None
        self.chroma_client: Optional[Any] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self.retriever: Optional[ChromaRetriever] = None
        self.tool_handlers: Dict[
            str, Callable[[Dict[str, Any]], Awaitable[Any]]
        ] = {}

    async def initialize(self, skip_connection_init: bool = False):
        """
        Initialize connections, auto-run migrations, and register
        tool handlers.
        """
        logger.info("Initializing vector-kb-mcp worker...")

        if not skip_connection_init:
            # 1. Run database auto-migrations
            try:
                run_vkb_migrations(db_url=self.settings.DATABASE_URL)
            except Exception as e:
                logger.error("Database auto-migration failed: %s", e)
                raise

            # 2. Initialize Redis connection
            if self.redis_client is None:
                self.redis_client = redis.from_url(
                    self.settings.REDIS_URL, decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Connected to Redis: %s", self.settings.REDIS_URL)

            # 2. Initialize Chroma client
            if self.chroma_client is None:
                self.chroma_client = chromadb.HttpClient(
                    host=self.settings.CHROMA_HOST,
                    port=self.settings.CHROMA_PORT,
                )
                logger.info(
                    "Connected to ChromaDB: %s:%d",
                    self.settings.CHROMA_HOST,
                    self.settings.CHROMA_PORT,
                )

            # 3. Initialize OpenAI client
            if self.openai_client is None:
                self.openai_client = AsyncOpenAI(
                    api_key=self.settings.OPENAI_API_KEY
                )

        # 4. Initialize ChromaRetriever if clients are present
        if (
            self.retriever is None
            and self.chroma_client
            and self.openai_client
        ):
            self.retriever = ChromaRetriever(
                chroma_client=self.chroma_client,
                openai_client=self.openai_client,
                embedding_model=self.settings.DEFAULT_EMBEDDING_MODEL,
            )

        # 5. Register tool handlers
        self.tool_handlers = {
            "query_knowledge_base": self._handle_query_kb,
            "list_knowledge_bases": self._handle_list_kbs,
            "get_knowledge_base": self._handle_get_kb,
            "create_knowledge_base": self._handle_create_kb,
            "update_knowledge_base": self._handle_update_kb,
            "delete_knowledge_base": self._handle_delete_kb,
            "list_documents": self._handle_list_docs,
            "get_document": self._handle_get_doc,
            "get_processing_tasks": self._handle_get_tasks,
        }
        logger.info("Registered %d tool handlers.", len(self.tool_handlers))

    # --- Tool Handlers ---
    async def _handle_query_kb(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self.retriever:
            raise RuntimeError("ChromaRetriever is not initialized")

        query = args.get("query", "")
        kb_ids = args.get("kb_ids", [])
        top_k = args.get("top_k", 4)
        score_threshold = args.get("score_threshold")

        chunks = await self.retriever.search(
            query=query,
            kb_ids=kb_ids,
            top_k=top_k,
            score_threshold=score_threshold,
        )

        formatted_chunks = [
            (
                dataclasses.asdict(c)
                if dataclasses.is_dataclass(c)
                else c.__dict__
            )
            for c in chunks
        ]
        return {"chunks": formatted_chunks}

    @staticmethod
    def _serialize_kb(kb: KnowledgeBase) -> Dict[str, Any]:
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

    @staticmethod
    def _serialize_doc(doc: Document) -> Dict[str, Any]:
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

    async def _handle_list_kbs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        async with get_db_session() as session:
            stmt = (
                select(KnowledgeBase)
                .options(selectinload(KnowledgeBase.documents))
                .order_by(KnowledgeBase.id.asc())
            )

            if "kb_ids" in args and args["kb_ids"]:
                stmt = stmt.where(KnowledgeBase.id.in_(args["kb_ids"]))
            if "search" in args and args["search"]:
                stmt = stmt.where(
                    KnowledgeBase.name.ilike(f"%{args['search']}%")
                )

            res = await session.execute(stmt)
            kbs = res.scalars().all()
            return {"knowledge_bases": [self._serialize_kb(kb) for kb in kbs]}

    async def _handle_get_kb(self, args: Dict[str, Any]) -> Dict[str, Any]:
        kb_id = args.get("kb_id")
        if not kb_id:
            return {"error": "Missing kb_id", "knowledge_base": None}

        async with get_db_session() as session:
            stmt = (
                select(KnowledgeBase)
                .options(selectinload(KnowledgeBase.documents))
                .where(KnowledgeBase.id == kb_id)
            )
            res = await session.execute(stmt)
            kb = res.scalar_one_or_none()
            if not kb:
                return {
                    "error": "Knowledge base not found",
                    "knowledge_base": None,
                }
            return {"knowledge_base": self._serialize_kb(kb)}

    async def _handle_create_kb(self, args: Dict[str, Any]) -> Dict[str, Any]:
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
                "knowledge_base": self._serialize_kb(kb),
                "status": "created",
                "kb_id": kb.id,
            }

    async def _handle_update_kb(self, args: Dict[str, Any]) -> Dict[str, Any]:
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
                "knowledge_base": self._serialize_kb(kb),
                "status": "updated",
            }

    async def _handle_delete_kb(self, args: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _handle_list_docs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        kb_id = args.get("kb_id")
        async with get_db_session() as session:
            stmt = select(Document).order_by(Document.id.desc())
            if kb_id:
                stmt = stmt.where(Document.knowledge_base_id == kb_id)
            res = await session.execute(stmt)
            docs = res.scalars().all()
            return {"documents": [self._serialize_doc(doc) for doc in docs]}

    async def _handle_get_doc(self, args: Dict[str, Any]) -> Dict[str, Any]:
        doc_id = args.get("document_id") or args.get("id")
        if not doc_id:
            return {"error": "Missing document_id", "document": None}

        async with get_db_session() as session:
            stmt = select(Document).where(Document.id == doc_id)
            res = await session.execute(stmt)
            doc = res.scalar_one_or_none()
            if not doc:
                return {"error": "Document not found", "document": None}
            return {"document": self._serialize_doc(doc)}

    async def _handle_get_tasks(self, args: Dict[str, Any]) -> Dict[str, Any]:
        kb_id = args.get("kb_id")
        async with get_db_session() as session:
            stmt = select(ProcessingTask).order_by(ProcessingTask.id.desc())
            if kb_id:
                stmt = stmt.where(ProcessingTask.knowledge_base_id == kb_id)
            res = await session.execute(stmt)
            tasks = res.scalars().all()
            return {
                "tasks": [
                    {
                        "id": t.id,
                        "task_id": t.task_id,
                        "knowledge_base_id": t.knowledge_base_id,
                        "document_id": t.document_id,
                        "task_type": t.task_type,
                        "status": t.status,
                        "progress_percentage": t.progress_percentage,
                        "current_step": t.current_step,
                        "error_message": t.error_message,
                        "created_at": (
                            t.created_at.isoformat() if t.created_at else None
                        ),
                        "completed_at": (
                            t.completed_at.isoformat()
                            if t.completed_at
                            else None
                        ),
                    }
                    for t in tasks
                ]
            }

    # --- Event Loop ---
    async def run(self):
        """Run the main async Redis worker event loop."""
        self.running = True
        self._run_task = asyncio.current_task()
        logger.info(
            "Listening for tool requests on queue: '%s'...",
            self.settings.REQUEST_QUEUE,
        )

        while self.running:
            try:
                if not self.redis_client:
                    break

                # Non-blocking pop with 1s timeout to allow shutdown checks
                item = await self.redis_client.blpop(
                    self.settings.REQUEST_QUEUE, timeout=1
                )
                if not item:
                    continue

                _, raw_payload = item
                asyncio.create_task(self._process_message(raw_payload))

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.running:
                    logger.error(
                        "Error in worker event loop: %s", e, exc_info=True
                    )
                    await asyncio.sleep(0.5)

    async def _process_message(self, raw_payload: str):
        """Process a single JSON-RPC tool request payload."""
        try:
            msg = json.loads(raw_payload)
        except Exception as e:
            logger.error(
                "Failed to parse incoming JSON payload: %s (Error: %s)",
                raw_payload,
                e,
            )
            return

        correlation_id = msg.get("correlation_id")
        if not correlation_id:
            logger.error("Missing correlation_id in payload: %s", raw_payload)
            return

        tool_name = (
            msg.get("tool_name") or msg.get("tool") or "query_knowledge_base"
        )
        args = msg.get("arguments", {})
        response_queue = (
            msg.get("response_queue")
            or f"{self.settings.RESPONSE_PREFIX}:{correlation_id}"
        )

        handler = self.tool_handlers.get(tool_name)
        if not handler:
            response = {
                "status": "error",
                "error": f"Unknown tool: '{tool_name}'",
            }
        else:
            try:
                result = await handler(args)
                response = {"status": "ok", "data": result}
            except Exception as ex:
                logger.error(
                    "Error executing handler for tool '%s': %s",
                    tool_name,
                    ex,
                    exc_info=True,
                )
                response = {"status": "error", "error": str(ex)}

        # Send response back via correlation key
        if self.redis_client:
            try:
                await self.redis_client.rpush(
                    response_queue, json.dumps(response)
                )
                await self.redis_client.expire(
                    response_queue, self.settings.RESPONSE_TTL_SECONDS
                )
            except Exception as e:
                logger.error(
                    "Failed to push response to '%s': %s", response_queue, e
                )

    async def shutdown(self):
        """Gracefully shutdown the worker and close connections."""
        logger.info("Initiating graceful shutdown...")
        self.running = False
        if (
            self._run_task
            and not self._run_task.done()
            and self._run_task != asyncio.current_task()
        ):
            self._run_task.cancel()
        if self.redis_client:
            try:
                if hasattr(self.redis_client, "aclose"):
                    await self.redis_client.aclose()
                else:
                    await self.redis_client.close()
            except Exception as e:
                logger.debug("Error closing redis client: %s", e)
        logger.info("Shutdown complete.")


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    worker = VectorMCPWorker()

    def handle_signal():
        logger.info("Received termination signal.")
        loop.create_task(worker.shutdown())

    # Register signal handlers for clean SIGTERM / SIGINT handling
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except (NotImplementedError, RuntimeError):
            # Fallback for non-main thread execution
            pass

    try:
        loop.run_until_complete(worker.initialize())
        loop.run_until_complete(worker.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
