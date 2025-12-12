import json
import aiohttp
import logging

logger = logging.getLogger(__name__)

class RESTMCPClientService:
    """REST-based MCP Client that uses static configuration."""

    def __init__(self, base_url: str, tools: list[dict]):
        self.base_url = base_url.rstrip("/")
        self.tools = tools
        self.is_rest = True  # Used by MCPClientManager

    async def list_tools(self):
        """Return statically defined tools with metadata."""
        return self.tools

    async def list_resources(self):
        """REST MCP servers may not have resource listings."""
        return []

    async def call_tool(self, tool_name: str, params: dict):
        """
        Support both:
        {"input": {...}}  ← ScopingAgent format
        """
        logger.info(
            f"[RESTMCPClientService] call_tool: {tool_name} with params: {params}")

        # find tool definition
        tool = next((t for t in self.tools if t["name"] == tool_name), None)
        if not tool:
            raise ValueError(f"Tool `{tool_name}` not found in REST MCP configuration")

        endpoint = tool.get("endpoint")
        method = tool.get("method", "POST").upper()
        url = f"{self.base_url}{endpoint}"

        # agMCP payload format
        payload = {
            "tool": tool_name,
            "parameters": params or {}
        }
        json_payload = json.dumps(payload)

        logger.info(
            f"[RESTMCPClientService] Calling {method} {url} with payload: {payload}"
        )

        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(
                    url, data=json_payload, headers=headers
                ) as resp:
                    result = await resp.json()
                    logger.info(f"[RESTMCPClientService] Response: {result}")
            else:
                async with session.get(
                    url, params=payload["parameters"], headers=headers
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json()

        logger.info(f"[RESTMCPClientService] Response: {result}")
        return result
