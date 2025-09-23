import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ScopingAgent:
    """
    Simplified scoping agent that loads discovery data from file
    and selects tools/resources for queries.
    """

    def __init__(self, discovery_file: str = "mcp_discovery.json"):
        self.discovery_file = discovery_file

    def load_discovery_data(self) -> Dict[str, Any]:
        """Load cached discovery data from JSON file."""
        try:
            with open(self.discovery_file, "r") as f:
                data = json.load(f)
                err = "[ScopingAgent] Discovery data loaded from"
                logger.info(f"{err} {self.discovery_file}")
                return data
        except FileNotFoundError:
            err = "[ScopingAgent] Discovery file"
            logger.error(f" {err} {self.discovery_file} not found")
            raise

    def scope_query(
        self, query: str, scope: Optional[Dict[str, Any]] = {}
    ) -> Dict[str, Any]:
        """
        Determine scope for MCP tool execution.
        Uses `query_knowledge_base` tool and allows multiple kb_ids.
        """
        discovery_data = self.load_discovery_data()

        server_name = "knowledge_bases_mcp"
        tool_name = "query_knowledge_base"

        tools = discovery_data.get("tools", {}).get(server_name, [])
        if not any(t["name"] == tool_name for t in tools):
            err = f"[ScopingAgent] Tool {tool_name} not found"
            logger.error(f"{err} for server {server_name}")
            raise ValueError(f"Tool {tool_name} not found in discovery data.")

        info = f"[ScopingAgent] Scoped query '{query}'"
        logger.info(f"{info} to {server_name}.{tool_name}")

        input_param = scope
        input_param["query"] = query

        return {
            "server_name": server_name,
            "tool_name": tool_name,
            "input": input_param,
        }
