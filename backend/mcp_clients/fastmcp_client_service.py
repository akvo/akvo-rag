from typing import Optional
from fastmcp import Client


class FastMCPClientService:
    """Client for MCP servers built with fastmcp.Server using API-Key auth."""

    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.server_url = server_url
        self.api_key = api_key
        # Prepare auth string
        self.auth_value = f"API-Key {self.api_key}" if self.api_key else None

    async def ping(self):
        async with Client(self.server_url, auth=self.auth_value) as client:
            return await client.ping()

    async def list_tools(self):
        async with Client(self.server_url, auth=self.auth_value) as client:
            return await client.list_tools()

    async def list_resources(self):
        async with Client(self.server_url, auth=self.auth_value) as client:
            return await client.list_resources()

    async def read_resource(self, uri: str):
        async with Client(self.server_url, auth=self.auth_value) as client:
            return await client.read_resource(uri)

    async def call_tool(self, tool_name: str, param: Optional[dict] = None):
        async with Client(self.server_url, auth=self.auth_value) as client:
            return await client.call_tool(tool_name, param or {})
