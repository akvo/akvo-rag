import asyncio
import logging
import signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vector-kb-mcp")


async def main():
    logger.info("Starting vector-kb-mcp service placeholder...")
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info("vector-kb-mcp ready and listening.")
    await stop_event.wait()
    logger.info("vector-kb-mcp shutting down gracefully.")


if __name__ == "__main__":
    asyncio.run(main())
