import json
import asyncio
import logging
from typing import Dict, Any

from mcp_clients.mcp_client_manager import MCPClientManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def to_serializable(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable formats.
    - Pydantic models -> dict
    - Lists/Tuples -> list
    - Dict -> dict with serialized values
    - AnyUrl/other -> str
    """
    if hasattr(obj, "dict"):  # Pydantic model
        return obj.dict()
    if isinstance(obj, (list, tuple)):
        return [to_serializable(o) for o in obj]
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    return str(obj)  # fallback


class MCPDiscoveryManager:
    """
    Handles discovery of MCP tools and resources,
    and saves the results into a JSON file.
    """

    def __init__(self, discovery_file: str = "mcp_discovery.json"):
        self.discovery_file = discovery_file

    async def discover_and_save(self) -> None:
        """Discover all MCP tools and resources, then save to JSON file."""
        manager = MCPClientManager()

        all_tools_info = await manager.get_all_tools()
        all_resources_info = await manager.get_all_resources()

        discovery_data: Dict[str, Any] = {"tools": {}, "resources": {}}

        # Tools
        for server_name, tool_list in all_tools_info.items():
            if isinstance(tool_list, list):
                formatted_tools = []
                for tool in tool_list:
                    if isinstance(tool, dict):
                        formatted_tools.append({
                            "name": tool.get("name"),
                            "description": tool.get("description"),
                            "inputSchema": to_serializable(tool.get("inputSchema")),
                            "endpoint": tool.get("endpoint"),
                            "method": tool.get("method", "POST"),
                        })
                    else:
                        # assume FastMCP Pydantic model
                        formatted_tools.append({
                            "name": getattr(tool, "name", None),
                            "description": getattr(tool, "description", None),
                            "inputSchema": to_serializable(getattr(tool, "inputSchema", None)),
                        })
                discovery_data["tools"][server_name] = formatted_tools
            else:
                discovery_data["tools"][server_name] = {"error": str(tool_list)}

        # Resources
        for server_name, resource_list in all_resources_info.items():
            if isinstance(resource_list, list):
                formatted_resources = []
                for r in resource_list:
                    if isinstance(r, dict):
                        formatted_resources.append({
                            "uri": to_serializable(r.get("uri")),
                            "name": r.get("name"),
                            "description": r.get("description"),
                        })
                    else:
                        formatted_resources.append({
                            "uri": to_serializable(getattr(r, "uri", None)),
                            "name": getattr(r, "name", None),
                            "description": getattr(r, "description", None),
                        })
                discovery_data["resources"][server_name] = formatted_resources
            else:
                discovery_data["resources"][server_name] = {"error": str(resource_list)}

        with open(self.discovery_file, "w") as f:
            json.dump(discovery_data, f, indent=2)

        logger.info(f"[MCP] Discovery data written to {self.discovery_file}")


if __name__ == "__main__":

    async def main():
        manager = MCPDiscoveryManager()
        await manager.discover_and_save()

    asyncio.run(main())
