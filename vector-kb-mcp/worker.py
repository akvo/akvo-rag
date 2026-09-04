import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

import chromadb
from openai import AsyncOpenAI
import redis.asyncio as redis

from core.config import Settings, settings as default_settings
from db.migrator import run_vkb_migrations
from handlers import (
    build_tool_handlers,
    serialize_kb,
    serialize_doc,
    serialize_task,
)
from retriever.chroma_retriever import ChromaRetriever

logger = logging.getLogger("vector-kb-mcp")


class VectorMCPWorker:
    """
    Queue-backed MCP microservice worker.
    Consumes JSON-RPC tool requests from Redis queues and dispatches them
    to domain handlers.
    """

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

    # Backward-compatible static references
    _serialize_kb = staticmethod(serialize_kb)
    _serialize_doc = staticmethod(serialize_doc)
    _serialize_task = staticmethod(serialize_task)

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

            # 3. Initialize Chroma client
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

            # 4. Initialize OpenAI client
            if self.openai_client is None:
                self.openai_client = AsyncOpenAI(
                    api_key=self.settings.OPENAI_API_KEY
                )

            # 5. Ensure MinIO bucket exists
            try:
                from storage.minio_storage import storage_service

                storage_service.ensure_bucket()
                logger.info("MinIO documents bucket initialized.")
            except Exception as e:
                logger.warning("MinIO bucket initialization notice: %s", e)

        # 5. Initialize ChromaRetriever if clients are present
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

        # 6. Register tool handlers from modular registry
        self.tool_handlers = build_tool_handlers(
            retriever_getter=lambda: self.retriever
        )
        logger.info("Registered %d tool handlers.", len(self.tool_handlers))

    async def _handle_query_kb(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch query_knowledge_base tool handler."""
        if "query_knowledge_base" not in self.tool_handlers:
            self.tool_handlers = build_tool_handlers(
                retriever_getter=lambda: self.retriever
            )
        return await self.tool_handlers["query_knowledge_base"](args)

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
        if not self.running and self.redis_client is None:
            return
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
            self.redis_client = None
        logger.info("Shutdown complete.")
