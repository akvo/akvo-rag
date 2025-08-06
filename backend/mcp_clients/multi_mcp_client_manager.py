from typing import Dict, Optional
from mcp_clients.mcp_client_service import MCPClientService


class MultiMCPClientManager:
    def __init__(self, server_urls: Dict[str, str]):
        """
        server_urls = {
            "image_rag": "http://localhost:8600/mcp",
            "text_analysis": "http://localhost:8700/mcp"
        }
        """
        self.services = {
            name: MCPClientService(url) for name, url in server_urls.items()
        }

    async def ping_all(self):
        results = {}
        for name, service in self.services.items():
            try:
                await service.ping()
                results[name] = "ok"
            except Exception as e:
                print(f"Error ping server {name}: {e}")
        return results

    async def get_all_tools(self):
        all_tools = {}
        for name, service in self.services.items():
            try:
                tools = await service.list_tools()
                all_tools[name] = tools
            except Exception as e:
                print(f"Error listing tools for {name}: {e}")
        return all_tools

    async def run_tool(
        self, server_name: str, tool_name: str, param: Optional[dict] = {}
    ):
        if server_name not in self.services:
            raise ValueError(f"Server `{server_name}` not found.")
        return await self.services[server_name].call_tool(tool_name, param)
