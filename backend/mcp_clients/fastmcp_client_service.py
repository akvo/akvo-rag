import httpx

from typing import Optional
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


class FastMCPClientService:
    """Client for MCP servers built with fastmcp.Server using API-Key auth."""

    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.transport = StreamableHttpTransport(url=server_url)
        self.transport.client = httpx.AsyncClient(
            headers={
                "Connection": "keep-alive",
                "Keep-Alive": "timeout=3600, max=10000",
            },
            timeout=httpx.Timeout(900.0),
        )
        # auth
        self.api_key = api_key
        self.auth_value = f"API-Key {self.api_key}" if self.api_key else None

    async def _make_client(self):
        return Client(self.transport, auth=self.auth_value)

    async def ping(self):
        async with await self._make_client() as client:
            return await client.ping()

    async def list_tools(self):
        async with await self._make_client() as client:
            return await client.list_tools()

    async def list_resources(self):
        async with await self._make_client() as client:
            return await client.list_resources()

    async def read_resource(self, uri: str):
        async with await self._make_client() as client:
            return await client.read_resource(uri)

    async def call_tool(self, tool_name: str, param: Optional[dict] = None):
        async with await self._make_client() as client:
            return await client.call_tool(tool_name, param or {})
