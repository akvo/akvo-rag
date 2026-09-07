import asyncio
import logging
import signal

from core.config import settings
from worker import VectorMCPWorker
from ingestion.worker import IngestionWorker

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [vector-kb-mcp] %(message)s",
)
logger = logging.getLogger("vector-kb-mcp")


async def async_main():
    rpc_worker = VectorMCPWorker()
    await rpc_worker.initialize()

    # Reuse the initialized retriever and
    # client connections for IngestionWorker
    ingestion_worker = IngestionWorker(retriever=rpc_worker.retriever)
    await ingestion_worker.initialize()

    loop = asyncio.get_running_loop()

    def handle_signal():
        logger.info("Received termination signal.")
        asyncio.create_task(rpc_worker.shutdown())
        asyncio.create_task(ingestion_worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        await asyncio.gather(rpc_worker.run(), ingestion_worker.run())
    except asyncio.CancelledError:
        pass
    finally:
        await asyncio.gather(
            rpc_worker.shutdown(),
            ingestion_worker.shutdown(),
            return_exceptions=True,
        )


def main():
    """CLI entrypoint for vector-kb-mcp microservice."""
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()

__all__ = ["VectorMCPWorker", "IngestionWorker", "main"]
