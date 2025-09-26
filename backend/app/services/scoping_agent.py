import json
import logging
import re
from typing import Dict, Any, Optional

import jsonschema
from app.services.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# TODO :: How we handle if kb_ids already provided
# Scoping agent can't talk with other KBs if kb_ids already provided


def _extract_json(raw_output: str) -> str:
    """
    Extract JSON from raw LLM output, even if wrapped in markdown fences.
    """
    fenced = re.search(r"```(?:json)?(.*?)```", raw_output, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return raw_output.strip()


class ScopingAgent:
    """
    Scoping agent that loads discovery data and asks an LLM
    to choose the right MCP server, tool, and parameters.
    """

    def __init__(
        self,
        discovery_file: str = "mcp_discovery.json",
    ):
        self.discovery_file = discovery_file
        self.llm = LLMFactory.create()

    def load_discovery_data(self) -> Dict[str, Any]:
        """Load cached discovery data from JSON file."""
        try:
            with open(self.discovery_file, "r") as f:
                data = json.load(f)
                info = "[ScopingAgent] Discovery data loaded from"
                logger.info(f"{info} {self.discovery_file}")
                return data
        except FileNotFoundError:
            err = "[ScopingAgent] Discovery file"
            logger.error(f"{err} {self.discovery_file} not found")
            raise

    async def _ask_llm(
        self,
        query: str,
        discovery_data: Dict[str, Any],
        scope: Optional[Dict[str, Any]] = {},
    ) -> Dict[str, Any]:
        """
        Ask LLM to decide which server, tool, and input parameters to use.
        """

        # Check if knowledge_base_ids already provided
        # Retrieve KB IDs from scope
        knowledge_base_ids = scope.get("knowledge_base_ids", [])

        kb_instruction = (
            "Use ONLY the provided knowledge_base_ids and do NOT choose new IDs."
            if knowledge_base_ids
            else "No KB IDs provided; select appropriately."
        )

        # Prepare servers_info
        servers_info = []
        for server_name, resources in discovery_data.get(
            "resources", {}
        ).items():
            server_desc = next(
                (
                    r["description"]
                    for r in resources
                    if r["uri"].endswith("server_info")
                ),
                "No description provided",
            )
            tools = discovery_data.get("tools", {}).get(server_name, [])
            servers_info.append(
                {
                    "server_name": server_name,
                    "server_description": server_desc,
                    "tools": tools,
                    "resources": resources,
                }
            )

        # System prompt header
        system_prompt = f"""
            You are a strict scoping agent. Your task is to choose the best MCP server, the appropriate tool, and construct the input JSON for the tool according to its inputSchema.
            {kb_instruction}
        """

        # System prompt rule
        system_prompt += """
            Follow these rules strictly:
            1. Always respond with a single valid JSON object with exactly these keys:
            {
                "server_name": "...",
                "tool_name": "...",
                "input": { ... } // must match the tool's inputSchema
            }

            2. Never return anything outside this JSON object.
            - Do NOT include markdown, code fences, explanations, or comments.
            - Do NOT return only part of the keys.
            - Do NOT hallucinate tool or server names; use only the provided servers_info.

            3. Ensure all required keys in the tool's inputSchema are present in "input".
            4. If a parameter is optional, include it only if necessary.
            5. Do NOT hallucinate tool names or server names. Only use names present in the provided servers_info.
            6. The "input" must always be a valid JSON object according to the tool's inputSchema.

            Here is the query and servers_info:

            Query: {query}
            Servers Info: {servers_info}

            Respond ONLY with the JSON object following the format above.
            """

        user_prompt = {
            "query": query,
            "servers_info": servers_info,
            "provided_kb_ids": knowledge_base_ids,  # explicitly pass KB IDs
        }

        resp = await self.llm.ainvoke(
            [
                ("system", system_prompt),
                ("user", json.dumps(user_prompt)),
            ]
        )

        raw_output = getattr(resp, "content", None) or str(resp)
        logger.info(f"[ScopingAgent] Raw LLM output: {raw_output}")

        try:
            cleaned = _extract_json(raw_output)
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"[ScopingAgent] Failed to parse LLM output: {e}")
            # Fallback default
            fallback = {
                "server_name": "knowledge_bases_mcp",
                "tool_name": "query_knowledge_base",
                "input": {
                    "query": query,
                    "knowledge_base_ids": knowledge_base_ids,
                },
            }
            logger.warning(
                f"[ScopingAgent] Falling back to default: {fallback}"
            )
            return fallback

    def _validate_input(
        self,
        discovery_data: Dict[str, Any],
        server_name: str,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> bool:
        """Validate the tool input against its schema using jsonschema."""
        tools = discovery_data.get("tools", {}).get(server_name, [])
        tool = next((t for t in tools if t["name"] == tool_name), None)

        if not tool:
            raise ValueError(
                f"Tool {tool_name} not found for server {server_name}"
            )

        schema = tool.get("inputSchema", {})
        try:
            jsonschema.validate(instance=tool_input, schema=schema)
            return True
        except jsonschema.ValidationError as e:
            logger.error(
                f"[ScopingAgent] Input validation failed: {e.message}"
            )
            return False

    async def scope_query(
        self, query: str, scope: Optional[Dict[str, Any]] = {}
    ) -> Dict[str, Any]:
        """
        Determine scope for MCP tool execution using LLM + schema validation.
        """
        discovery_data = self.load_discovery_data()
        suggestion = await self._ask_llm(query, discovery_data, scope)

        if not suggestion:
            raise ValueError(
                "[ScopingAgent] LLM did not return a valid suggestion"
            )

        server_name = suggestion.get("server_name")
        tool_name = suggestion.get("tool_name")
        tool_input = suggestion.get("input", {})

        if not self._validate_input(
            discovery_data, server_name, tool_name, tool_input
        ):
            raise ValueError(
                "[ScopingAgent] Suggested input is invalid according to schema"
            )

        info = "[ScopingAgent] Scoped query"
        info += (
            f" {query} -> {server_name}.{tool_name} with input {tool_input}"
        )
        logger.info(info)

        return suggestion
