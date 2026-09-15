import argparse
import asyncio
import logging
import os
import signal
from typing import Optional

from core.config import settings
from worker import VectorMCPWorker
from ingestion.worker import IngestionWorker

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [vector-kb-mcp] %(message)s",
)
logger = logging.getLogger("vector-kb-mcp")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Vector Knowledge Base MCP Microservice Worker"
    )
    parser.add_argument(
        "--mode",
        choices=["query", "ingest", "all"],
        default=os.environ.get("WORKER_MODE", "all"),
        help="Worker operational mode: query (RPC), ingest (doc), or all",
    )
    args, _ = parser.parse_known_args()
    return args


async def async_main(mode: str = "all"):
    logger.info("Starting vector-kb-mcp in mode: '%s'", mode)

    rpc_worker: Optional[VectorMCPWorker] = None
    ingestion_worker: Optional[IngestionWorker] = None
    tasks = []

    if mode in ("query", "all"):
        rpc_worker = VectorMCPWorker()
        await rpc_worker.initialize()
        tasks.append(rpc_worker.run())

    if mode in ("ingest", "all"):
        shared_retriever = rpc_worker.retriever if rpc_worker else None
        ingestion_worker = IngestionWorker(retriever=shared_retriever)
        await ingestion_worker.initialize()
        tasks.append(ingestion_worker.run())

    loop = asyncio.get_running_loop()

    def handle_signal():
        logger.info("Received termination signal.")
        if rpc_worker:
            asyncio.create_task(rpc_worker.shutdown())
        if ingestion_worker:
            asyncio.create_task(ingestion_worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        if tasks:
            await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        shutdown_coros = []
        if rpc_worker:
            shutdown_coros.append(rpc_worker.shutdown())
        if ingestion_worker:
            shutdown_coros.append(ingestion_worker.shutdown())
        if shutdown_coros:
            await asyncio.gather(*shutdown_coros, return_exceptions=True)


def main():
    """CLI entrypoint for vector-kb-mcp microservice."""
    args = parse_args()
    try:
        asyncio.run(async_main(mode=args.mode))
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()

__all__ = [
    "VectorMCPWorker",
    "IngestionWorker",
    "main",
    "async_main",
    "parse_args",
]
