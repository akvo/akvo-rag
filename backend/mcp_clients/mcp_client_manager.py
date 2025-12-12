# mcp_client_manager.py
from typing import Optional, Dict, Any
from app.core.config import settings
from .fastmcp_client_service import FastMCPClientService
from .rest_mcp_client_service import RESTMCPClientService
from .mcp_servers_config import DEFAULT_MCP_SERVERS
from mcp_clients.utils.filter_tool_config import (
    get_free_tools,
    get_all_tools,
    get_tools_summary
)

class MCPClientManager:
    """Manager for multiple MCP servers (FastMCP and REST MCPs)."""

    def __init__(self, use_only_free_weather_tools: Optional[bool] = None):
        """
        Initialize MCP Client Manager.

        Args:
            use_only_free_weather_tools: If True, only register weather tools that don't
                                        require API keys. If None, uses the setting from
                                        settings.USE_ONLY_FREE_WEATHER_MCP_TOOLS
        """
        self.services = {}
        # Use provided argument or fall back to settings
        if use_only_free_weather_tools is None:
            use_only_free_weather_tools = settings.USE_ONLY_FREE_WEATHER_MCP_TOOLS

        self.use_only_free_weather_tools = use_only_free_weather_tools

        for name, cfg in DEFAULT_MCP_SERVERS.items():
            url = cfg.get("url")
            api_key = cfg.get("api_key")
            mcp_type = cfg.get("type", "fastmcp")

            if not url:
                raise ValueError(f"MCP server URL not defined for {name}")

            if mcp_type == "fastmcp":
                self.services[name] = FastMCPClientService(url, api_key=api_key)
            elif mcp_type == "rest":
                # For weather_mcp, choose which tools to register based on setting
                if name == "weather_mcp" and use_only_free_weather_tools:
                    tools = get_free_tools(name)
                else:
                    tools = get_all_tools(name)

                self.services[name] = RESTMCPClientService(url, tools)
            else:
                raise ValueError(
                    f"Unsupported MCP type `{mcp_type}` for {name}"
                )

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

    def get_tools_info(self) -> Dict[str, Any]:
        """
        Get information about registered tools for each server.
        This shows what tools are available in the manager based on configuration.
        """
        info = {}
        for name in DEFAULT_MCP_SERVERS.keys():
            server_type = DEFAULT_MCP_SERVERS[name].get("type")
            if server_type == "rest":
                summary = get_tools_summary(name)
                if name == "weather_mcp":
                    summary["registered_mode"] = (
                        "free_only" if self.use_only_free_weather_tools else "all"
                    )
                    summary["setting"] = "USE_ONLY_FREE_WEATHER_MCP_TOOLS"
                    summary["setting_value"] = self.use_only_free_weather_tools
                else:
                    summary["registered_mode"] = "all"
                info[name] = summary
            else:
                info[name] = {
                    "type": server_type,
                    "note": "Tool registration handled by FastMCP protocol"
                }
        return info

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
            raise ValueError(
                f"Server `{server_name}` does not support resource reading."
            )
        return await service.read_resource(uri)

    async def run_tool(
        self, server_name: str, tool_name: str, param: Optional[dict] = None
    ):
        """
        Execute a tool on the given MCP server.

        Note: If the tool requires an API key that's not configured on the
        weather MCP server, the call will fail at the server level.
        """
        if server_name not in self.services:
            raise ValueError(f"Server `{server_name}` not found.")
        service = self.services[server_name]
        if not hasattr(service, "call_tool"):
            raise ValueError(
                f"Server `{server_name}` does not support running tools."
            )
        return await service.call_tool(tool_name, param or {})
