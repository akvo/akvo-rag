from typing import Optional
from .fastmcp_client_service import FastMCPClientService
from app.core.config import settings


DEFAULT_MCP_SERVERS = {
    "knowledge_bases_mcp": {
        "url": settings.KNOWLEDGE_BASES_MCP,
        "api_key": settings.KNOWLEDGE_BASES_API_KEY,
    },
}


class MCPClientManager:
    """Manager for multiple MCP servers (fastmcp.Server and other MCP)."""

    def __init__(self):
        self.services = {}
        for name, cfg in DEFAULT_MCP_SERVERS.items():
            url = cfg.get("url")
            api_key = cfg.get("api_key")

            if not url:
                raise ValueError(f"MCP server URL not defined for {name}")

            self.services[name] = FastMCPClientService(url, api_key=api_key)

    async def ping_all(self):
        results = {}
        for name, service in self.services.items():
            if isinstance(service, FastMCPClientService):
                try:
                    await service.ping()
                    results[name] = "ok"
                except Exception as e:
                    results[name] = f"error: {e}"
            else:
                results[name] = "not supported"
        return results

    async def get_all_tools(self):
        all_tools = {}
        for name, service in self.services.items():
            if isinstance(service, FastMCPClientService):
                try:
                    tools = await service.list_tools()
                    all_tools[name] = tools
                except Exception as e:
                    all_tools[name] = f"error: {e}"
            else:
                all_tools[name] = "use documentation/config"
        return all_tools

    async def get_all_resources(self):
        all_resources = {}
        for name, service in self.services.items():
            if isinstance(service, FastMCPClientService):
                try:
                    resources = await service.list_resources()
                    all_resources[name] = resources
                except Exception as e:
                    all_resources[name] = f"error: {e}"
            else:
                all_resources[name] = "not supported"
        return all_resources

    async def read_resource(self, server_name: str, uri: str):
        if server_name not in self.services:
            raise ValueError(f"Server `{server_name}` not found.")

        service = self.services[server_name]
        if not isinstance(service, FastMCPClientService):
            raise ValueError(
                f"Server `{server_name}` does not support read_resource."
            )
        return await service.read_resource(uri)

    async def run_tool(
        self, server_name: str, tool_name: str, param: Optional[dict] = None
    ):
        if server_name not in self.services:
            raise ValueError(f"Server `{server_name}` not found.")
        return await self.services[server_name].call_tool(
            tool_name, param or {}
        )
