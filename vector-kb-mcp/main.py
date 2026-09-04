import asyncio
import logging
import signal

from core.config import settings
from worker import VectorMCPWorker

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [vector-kb-mcp] %(message)s",
)
logger = logging.getLogger("vector-kb-mcp")


def main():
    """CLI entrypoint for vector-kb-mcp microservice."""
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

__all__ = ["VectorMCPWorker", "main"]
