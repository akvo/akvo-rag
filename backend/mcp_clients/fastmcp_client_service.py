import asyncio
import logging
import random
import httpx
from typing import Optional, Any
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from anyio import BrokenResourceError
from httpx import HTTPStatusError

logger = logging.getLogger(__name__)


class FastMCPClientService:
    """
    Robust MCP client with:
    - Auto-reconnect
    - Repeated-400 detection
    - Exponential retry with jitter
    - Stuck-stream recovery
    """

    def __init__(
        self,
        server_url: str,
        api_key: Optional[str] = None,
        max_retries: int = 5,
        retry_delay: float = 5.0,
    ):
        self.server_url = server_url
        self.api_key = api_key
        self.auth_value = f"API-Key {self.api_key}" if self.api_key else None
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._400_streak = 0
        self._create_transport()

    def _create_transport(self):
        logger.info("🔄 Creating new MCP transport client...")
        self.transport = StreamableHttpTransport(url=self.server_url)
        self.transport.client = httpx.AsyncClient(
            headers={
                "Connection": "keep-alive",
                "Keep-Alive": "timeout=3600, max=10000",
            },
            timeout=httpx.Timeout(300.0),
        )

    async def _make_client(self) -> Client:
        return Client(self.transport, auth=self.auth_value)

    async def _retry_operation(
        self, operation_name: str, func, *args, **kwargs
    ) -> Any:
        """Retry wrapper with 400, timeout, and hang protection."""
        self._400_streak = getattr(self, "_400_streak", 0)

        for attempt in range(1, self.max_retries + 1):
            try:
                async with await self._make_client() as client:
                    # Timeout each tool run so we don't hang forever
                    result = await asyncio.wait_for(func(client, *args, **kwargs), timeout=120)
                    self._400_streak = 0
                    return result

            except asyncio.TimeoutError:
                logger.warning(f"⏳ [{operation_name}] timed out — rebuilding transport")
                self._create_transport()

            except HTTPStatusError as e:
                code = getattr(e.response, "status_code", None)
                if code == 400:
                    self._400_streak += 1
                    logger.warning(f"⚠️ [{operation_name}] got 400 Bad Request (streak={self._400_streak})")
                    if self._400_streak >= 2:
                        logger.error("🚨 Consecutive 400s — forcing transport rebuild")
                        self._400_streak = 0
                        self._create_transport()
                else:
                    logger.error(f"❌ [{operation_name}] HTTP error {code}: {e}")
                    raise

            except BrokenResourceError:
                logger.warning(f"⚠️ [{operation_name}] BrokenResourceError — reconnecting")
                self._create_transport()

            except httpx.TransportError as e:
                logger.warning(f"⚠️ [{operation_name}] Transport error: {e}")
                self._create_transport()

            except Exception as e:
                # Defensive catch for post-writer or stream teardown errors
                msg = str(e)
                if "Bad Request" in msg or "post_writer" in msg:
                    self._400_streak += 1
                    logger.warning(f"⚠️ [{operation_name}] stream teardown 400 (streak={self._400_streak})")
                    if self._400_streak >= 2:
                        logger.error("🚨 Consecutive stream 400s — resetting transport hard")
                        self._400_streak = 0
                        self._create_transport()
                else:
                    logger.exception(f"❌ Unexpected error in {operation_name}: {e}")
                    raise

            # Exponential backoff with jitter
            delay = min(self.retry_delay * attempt * (1 + random.random()), 10.0)
            logger.info(f"🔁 Retrying {operation_name} in {delay:.1f}s (attempt {attempt}/{self.max_retries})...")
            await asyncio.sleep(delay)

        raise RuntimeError(
            f"❌ {operation_name} failed after {self.max_retries} attempts"
        )

    # ---- Public API ----
    async def ping(self):
        return await self._retry_operation("ping", lambda c: c.ping())

    async def list_tools(self):
        return await self._retry_operation("list_tools", lambda c: c.list_tools())

    async def list_resources(self):
        return await self._retry_operation("list_resources", lambda c: c.list_resources())

    async def read_resource(self, uri: str):
        return await self._retry_operation("read_resource", lambda c: c.read_resource(uri))

    async def call_tool(self, tool_name: str, param: Optional[dict] = None):
        return await self._retry_operation(
            "call_tool", lambda c: c.call_tool(tool_name, param or {})
        )
