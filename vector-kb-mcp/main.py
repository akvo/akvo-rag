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
from retriever.chroma_retriever import ChromaRetriever

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
            "list_knowledge_bases": self._handle_list_kbs_stub,
            "get_knowledge_base": self._handle_get_kb_stub,
            "create_knowledge_base": self._handle_create_kb_stub,
            "update_knowledge_base": self._handle_update_kb_stub,
            "delete_knowledge_base": self._handle_delete_kb_stub,
            "list_documents": self._handle_list_docs_stub,
            "get_document": self._handle_get_doc_stub,
            "get_processing_tasks": self._handle_get_tasks_stub,
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

    # Stubs for Phase 2 DB model integration
    async def _handle_list_kbs_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"knowledge_bases": []}

    async def _handle_get_kb_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"id": args.get("kb_id"), "status": "ACTIVE"}

    async def _handle_create_kb_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": "created", "kb_id": 1}

    async def _handle_update_kb_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": "updated"}

    async def _handle_delete_kb_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": "deleted"}

    async def _handle_list_docs_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"documents": []}

    async def _handle_get_doc_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"document": {}}

    async def _handle_get_tasks_stub(
        self, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"tasks": []}

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
