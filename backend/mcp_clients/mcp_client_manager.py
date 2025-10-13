from typing import Optional, Dict, Any
from .fastmcp_client_service import FastMCPClientService
from .rest_mcp_client_service import RESTMCPClientService
from .mcp_servers_config import DEFAULT_MCP_SERVERS


class MCPClientManager:
    """Manager for multiple MCP servers (FastMCP and REST MCPs)."""

    def __init__(self):
        self.services = {}
        for name, cfg in DEFAULT_MCP_SERVERS.items():
            url = cfg.get("url")
            api_key = cfg.get("api_key")
            mcp_type = cfg.get("type", "fastmcp")

            if not url:
                raise ValueError(f"MCP server URL not defined for {name}")

            if mcp_type == "fastmcp":
                self.services[name] = FastMCPClientService(url, api_key=api_key)
            elif mcp_type == "rest":
                self.services[name] = RESTMCPClientService(
                    url, cfg.get("tools", [])
                )
            else:
                raise ValueError(
                    f"Unsupported MCP type `{mcp_type}` for {name}")

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
                results[name] = "not supported"  # REST MCPs may not have ping
        return results

    async def get_all_tools(self) -> Dict[str, Any]:
        """Retrieve tool lists from all MCP servers (FastMCP + REST)."""
        all_tools = {}
        for name, service in self.services.items():
            try:
                tools = await service.list_tools()
                all_tools[name] = tools
            except Exception as e:
                all_tools[name] = f"error: {e}"
        return all_tools

    async def get_all_resources(self) -> Dict[str, Any]:
        """Retrieve resources from all MCP servers (FastMCP only, REST optional)."""
        all_resources = {}
        for name, service in self.services.items():
            try:
                resources = await service.list_resources()
                all_resources[name] = resources
            except Exception as e:
                all_resources[name] = f"error: {e}"
        return all_resources

    async def read_resource(self, server_name: str, uri: str):
        """Read a resource from an MCP server if supported."""
        if server_name not in self.services:
            raise ValueError(f"Server `{server_name}` not found.")

        service = self.services[server_name]
        if not hasattr(service, "read_resource"):
            raise ValueError(f"Server `{server_name}` does not support resource reading.")

        return await service.read_resource(uri)

    async def run_tool(
        self, server_name: str, tool_name: str, param: Optional[dict] = None
    ):
        """Execute a tool on the given MCP server."""
        if server_name not in self.services:
            raise ValueError(f"Server `{server_name}` not found.")

        service = self.services[server_name]
        if not hasattr(service, "call_tool"):
            raise ValueError(f"Server `{server_name}` does not support running tools.")

        return await service.call_tool(tool_name, param or {})
