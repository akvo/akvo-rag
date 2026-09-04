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


async def async_main():
    worker = VectorMCPWorker()
    loop = asyncio.get_running_loop()

    def handle_signal():
        logger.info("Received termination signal.")
        asyncio.create_task(worker.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        await worker.initialize()
        await worker.run()
    except asyncio.CancelledError:
        pass
    finally:
        await worker.shutdown()


def main():
    """CLI entrypoint for vector-kb-mcp microservice."""
    try:
        asyncio.run(async_main())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()

__all__ = ["VectorMCPWorker", "main"]
