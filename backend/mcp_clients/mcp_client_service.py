from fastmcp import Client
from typing import Optional


class MCPClientService:
    def __init__(self, server_url: str):
        self.server_url = server_url

    async def ping(self):
        async with Client(self.server_url) as client:
            # Ping the server to check if it's reachable
            return await client.ping()

    async def list_tools(self):
        async with Client(self.server_url) as client:
            # List available tools on the server
            return await client.list_tools()

    async def list_resources(self):
        async with Client(self.server_url) as client:
            # List available tools on the server
            return await client.list_resources()

    async def read_resource(self, uri: str):
        async with Client(self.server_url) as client:
            # Read a specific resource by its URI
            return await client.read_resource(uri)

    async def call_tool(self, tool_name: str, param: Optional[dict] = {}):
        async with Client(self.server_url) as client:
            # Call a specific tool with the provided arguments
            return await client.call_tool(tool_name, param)
