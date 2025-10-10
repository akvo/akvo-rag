import aiohttp
from typing import Any, Dict, List


class RESTMCPClientService:
    """Adapter for non-FastMCP servers exposing REST POST endpoints."""

    def __init__(self, base_url: str, tools: List[Dict[str, Any]]):
        self.base_url = base_url.rstrip("/")
        self.tools = tools

    async def list_tools(self):
        # Maybe later can check, if static tools provided use static
        # then if not, try to fetch from server (if supported)
        return self.tools

    async def list_resources(self):
        # Optional — return static or empty
        return []

    async def call_tool(self, tool_name: str, params: Dict[str, Any]):
        tool = next((t for t in self.tools if t["name"] == tool_name), None)
        if not tool:
            raise ValueError(f"Tool `{tool_name}` not found")

        url = f"{self.base_url}{tool['endpoint']}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=params) as resp:
                resp.raise_for_status()
                return await resp.json()
