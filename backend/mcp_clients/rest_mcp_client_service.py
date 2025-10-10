import aiohttp
import logging

logger = logging.getLogger(__name__)

class RESTMCPClientService:
    """REST-based MCP Client that uses static configuration."""

    def __init__(self, base_url: str, tools: list[dict]):
        self.base_url = base_url.rstrip("/")
        self.tools = tools

    async def list_tools(self):
        """Return statically defined tools with metadata."""
        return self.tools

    async def list_resources(self):
        """REST MCP servers may not have resource listings."""
        return []

    async def call_tool(self, tool_name: str, payload: dict):
        """
        Call a REST MCP tool.
        Expected payload:
        {
            "tool": "get_weather_forecast",
            "parameters": {...}
        }
        """
        # Handle case where the caller already passes 'tool' key
        if "tool" in payload:
            tool_name = payload["tool"]
            params = payload.get("parameters", {})
        else:
            params = payload  # fallback for backward compatibility

        # Find matching tool definition
        tool = next((t for t in self.tools if t["name"] == tool_name), None)
        if not tool:
            raise ValueError(f"Tool `{tool_name}` not found in REST MCP configuration")

        endpoint = tool.get("endpoint")
        method = tool.get("method", "POST").upper()
        url = f"{self.base_url}{endpoint}"

        logger.info(f"[RESTMCP] Calling {tool_name} -> {url} ({method})")

        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(url, json=params) as resp:
                    result = await resp.json()
            else:
                async with session.get(url, params=params) as resp:
                    result = await resp.json()

        return {
            "tool": tool_name,
            "endpoint": url,
            "method": method,
            "response": result,
        }
