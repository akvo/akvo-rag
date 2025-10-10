import asyncio
import logging
import httpx
from typing import Optional, Any
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from anyio import BrokenResourceError
from httpx import HTTPStatusError

logger = logging.getLogger(__name__)


class FastMCPClientService:
    """
    - Client for MCP servers built with fastmcp.
    - Server using API-Key auth.
    - Includes auto-reconnect and retry logic for resilience.
    """

    def __init__(
        self,
        server_url: str,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ):
        self.server_url = server_url
        self.api_key = api_key
        self.auth_value = f"API-Key {self.api_key}" if self.api_key else None
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Create persistent transport + client
        self.transport = StreamableHttpTransport(url=self.server_url)
        self.transport.client = httpx.AsyncClient(
            headers={
                "Connection": "keep-alive",
                "Keep-Alive": "timeout=3600, max=10000",
            },
            timeout=httpx.Timeout(900.0),
        )

    async def _make_client(self) -> Client:
        return Client(self.transport, auth=self.auth_value)

    async def _retry_operation(self, operation_name: str, func, *args, **kwargs) -> Any:
        """Generic retry wrapper for MCP operations."""
        for attempt in range(1, self.max_retries + 1):
            try:
                async with await self._make_client() as client:
                    return await func(client, *args, **kwargs)
            except (
                BrokenResourceError, HTTPStatusError, httpx.TransportError
            ) as e:
                logger.warning(
                    f"⚠️ [{operation_name}] failed with {type(e).__name__}: {e}"
                )
                if attempt < self.max_retries:
                    delay = self.retry_delay * attempt
                    logger.info(f"🔁 Retrying {operation_name} in {delay}s (attempt {attempt}/{self.max_retries})...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ {operation_name} failed after {self.max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger.exception(f"❌ Unexpected error in {operation_name}: {e}")
                raise

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
