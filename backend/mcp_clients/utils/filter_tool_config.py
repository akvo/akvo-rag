from typing import List, Dict, Any
from mcp_clients.mcp_servers_config import DEFAULT_MCP_SERVERS


def get_free_tools(server_name: str = "weather_mcp") -> List[Dict[str, Any]]:
    """
    Get all tools that don't require API keys (can be used without configuration).

    Args:
        server_name: Name of the MCP server (default: "weather_mcp")

    Returns:
        List of free tools
    """
    if server_name not in DEFAULT_MCP_SERVERS:
        raise ValueError(f"Server '{server_name}' not found in config")

    server_config = DEFAULT_MCP_SERVERS[server_name]

    # For non-REST servers, return empty list
    if server_config.get("type") != "rest":
        return []

    all_tools = server_config.get("tools", [])

    # Return only tools that don't require API keys
    return [
        tool for tool in all_tools
        if not tool.get("api_key_required", False)
    ]


def get_tools_by_api_requirement(
    server_name: str = "weather_mcp",
    require_api_key: bool = False
) -> List[Dict[str, Any]]:
    """
    Filter tools based on API key requirement.

    Args:
        server_name: Name of the MCP server (default: "weather_mcp")
        require_api_key: If True, return tools that need API keys.
                        If False, return tools that don't need API keys.

    Returns:
        List of filtered tools
    """
    if server_name not in DEFAULT_MCP_SERVERS:
        raise ValueError(f"Server '{server_name}' not found in config")

    server_config = DEFAULT_MCP_SERVERS[server_name]

    if server_config.get("type") != "rest":
        return []

    all_tools = server_config.get("tools", [])

    return [
        tool for tool in all_tools
        if tool.get("api_key_required", False) == require_api_key
    ]


def get_all_tools(server_name: str = "weather_mcp") -> List[Dict[str, Any]]:
    """
    Get all tools for a server (both free and paid).

    Args:
        server_name: Name of the MCP server (default: "weather_mcp")

    Returns:
        List of all tools
    """
    if server_name not in DEFAULT_MCP_SERVERS:
        raise ValueError(f"Server '{server_name}' not found in config")

    server_config = DEFAULT_MCP_SERVERS[server_name]

    if server_config.get("type") != "rest":
        return []

    return server_config.get("tools", [])


def get_tools_summary(server_name: str = "weather_mcp") -> Dict[str, Any]:
    """
    Get a summary of tool availability for a server.

    Args:
        server_name: Name of the MCP server (default: "weather_mcp")

    Returns:
        Dict with tool statistics and categorization
    """
    all_tools = get_all_tools(server_name)
    free_tools = get_free_tools(server_name)
    paid_tools = get_tools_by_api_requirement(server_name, require_api_key=True)

    # Group paid tools by required API key
    tools_by_api_key = {}
    for tool in paid_tools:
        api_key_name = tool.get("api_key_name", "Unknown")
        if api_key_name not in tools_by_api_key:
            tools_by_api_key[api_key_name] = []
        tools_by_api_key[api_key_name].append(tool["name"])

    return {
        "server_name": server_name,
        "total_tools": len(all_tools),
        "free_tools": {
            "count": len(free_tools),
            "names": [t["name"] for t in free_tools]
        },
        "paid_tools": {
            "count": len(paid_tools),
            "by_api_key": tools_by_api_key
        }
    }