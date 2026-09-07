import asyncio
import json
import logging
from typing import Optional, Any
from minio import Minio
from openai import AsyncOpenAI
import chromadb
import redis.asyncio as redis

from core.config import Settings, settings as default_settings
from db.session import get_db_session
from ingestion.processor import IngestionProcessor

logger = logging.getLogger("vector-kb-mcp.ingestion.worker")


class IngestionWorker:
    """
    Dedicated background Redis worker consuming document ingestion tasks
    from the 'document_ingestion' queue.
    """

    def __init__(
        self,
        settings_override: Optional[Settings] = None,
        processor: Optional[IngestionProcessor] = None,
        retriever: Optional[Any] = None,
    ):
        self.settings: Settings = settings_override or default_settings
        self.running: bool = False
        self._run_task: Optional[asyncio.Task] = None
        self.redis_client: Optional[redis.Redis] = None
        self.minio_client: Optional[Minio] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self.chroma_client: Optional[Any] = None
        self.retriever = retriever
        self.processor: Optional[IngestionProcessor] = processor

    async def initialize(self, skip_connection_init: bool = False):
        """
        Initialize client connections and the IngestionProcessor.
        """
        logger.info("Initializing IngestionWorker...")
        if not skip_connection_init:
            if self.redis_client is None:
                self.redis_client = redis.from_url(
                    self.settings.REDIS_URL, decode_responses=True
                )
                await self.redis_client.ping()

            if self.processor is None and self.retriever is None:
                if self.minio_client is None:
                    self.minio_client = Minio(
                        endpoint=self.settings.MINIO_ENDPOINT,
                        access_key=self.settings.MINIO_ACCESS_KEY,
                        secret_key=self.settings.MINIO_SECRET_KEY,
                        secure=self.settings.MINIO_SECURE,
                    )

                if self.openai_client is None:
                    self.openai_client = AsyncOpenAI(
                        api_key=self.settings.OPENAI_API_KEY
                    )

                if self.chroma_client is None:
                    self.chroma_client = chromadb.HttpClient(
                        host=self.settings.CHROMA_HOST,
                        port=self.settings.CHROMA_PORT,
                    )

        if self.processor is None:
            if self.retriever is not None:
                self.processor = IngestionProcessor(
                    retriever=self.retriever,
                    embedding_model=self.settings.DEFAULT_EMBEDDING_MODEL,
                )
            elif (
                self.minio_client and self.openai_client and self.chroma_client
            ):
                self.processor = IngestionProcessor(
                    minio_client=self.minio_client,
                    openai_client=self.openai_client,
                    chroma_client=self.chroma_client,
                    embedding_model=self.settings.DEFAULT_EMBEDDING_MODEL,
                )

        logger.info("IngestionWorker initialization complete.")

    async def run(self):
        """
        Continuous async event loop listening on the ingestion queue.
        """
        self.running = True
        self._run_task = asyncio.current_task()
        logger.info(
            "IngestionWorker listening on queue '%s'...",
            self.settings.INGESTION_QUEUE,
        )

        while self.running:
            try:
                if not self.redis_client:
                    break

                # Pop task with 1s timeout to allow clean shutdown checks
                item = await self.redis_client.blpop(
                    self.settings.INGESTION_QUEUE, timeout=1
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
                        "Error in IngestionWorker event loop: %s",
                        e,
                        exc_info=True,
                    )
                    await asyncio.sleep(0.5)

    async def _process_message(self, raw_payload: str):
        """Deserialize payload and execute ingestion in DB session."""
        try:
            payload = json.loads(raw_payload)
        except Exception as e:
            logger.error(
                "IngestionWorker failed to parse JSON task: %s (Error: %s)",
                raw_payload,
                e,
            )
            return

        if not isinstance(payload, dict):
            logger.error(
                "IngestionWorker received non-dict payload: %s", raw_payload
            )
            return

        doc_id = payload.get("document_id")
        kb_id = payload.get("kb_id")
        logger.info(
            "IngestionWorker starting task for doc '%s' (KB %s)",
            doc_id,
            kb_id,
        )

        if not self.processor:
            logger.error("IngestionProcessor is not initialized.")
            return

        try:
            async with get_db_session() as session:
                await self.processor.process_document(payload, session)
        except Exception as e:
            logger.error(
                "Unhandled error processing ingestion task for doc '%s': %s",
                doc_id,
                e,
                exc_info=True,
            )

    async def shutdown(self):
        """Gracefully stop the worker and release resources."""
        if not self.running and self.redis_client is None:
            return

        logger.info("IngestionWorker initiating graceful shutdown...")
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
                logger.debug("Error closing Redis in IngestionWorker: %s", e)
            self.redis_client = None

        logger.info("IngestionWorker stopped gracefully.")
