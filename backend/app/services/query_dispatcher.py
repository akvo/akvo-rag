import re
import json
import logging

from typing import Dict, Any
from langchain_core.messages import AIMessage
from mcp_clients.multi_mcp_client_manager import MultiMCPClientManager

logger = logging.getLogger(__name__)


class QueryDispatcher:

    def __init__(self):
        self.manager = MultiMCPClientManager()

    async def dispatch(self, scoping_result: Dict[str, Any]) -> Dict[str, Any]:
        if (
            isinstance(scoping_result, dict)
            and "server_name" in scoping_result
        ):
            payload = scoping_result
        elif isinstance(scoping_result, dict) and "messages" in scoping_result:
            # Ambil AIMessage terakhir
            ai_msg = next(
                (
                    m
                    for m in scoping_result["messages"]
                    if isinstance(m, AIMessage)
                ),
                None,
            )
            if not ai_msg:
                raise ValueError("No AIMessage found in scoping_result.")
            content_str = ai_msg.content
            # Hilangkan wrapper ```json ... ```
            match = re.search(r"```json\s*(.*?)\s*```", content_str, re.S)
            if match:
                content_str = match.group(1)
            payload = json.loads(content_str)
        else:
            raise ValueError("Scoping result format not recognized.")

        if not all(k in payload for k in ("server_name", "tool_name")):
            raise ValueError(
                "Scoping result must include server_name and tool_name"
            )

        try:
            server_name = payload["server_name"]
            tool_name = payload["tool_name"]
            param = payload.get("input", {})
            # Call MCP tool via manager
            result = await self.manager.run_tool(
                server_name=server_name,
                tool_name=tool_name,
                param=param,
            )

            # Optional: post-processing
            processed_result = self._post_process(result)

            return {
                "success": True,
                "server_name": server_name,
                "tool_name": tool_name,
                "raw_result": result,
                "processed_result": processed_result,
            }

        except Exception as e:
            logger.exception(
                f"Error calling MCP tool {server_name}.{tool_name}"
            )
            return {
                "success": False,
                "error": str(e),
                "server_name": server_name,
                "tool_name": tool_name,
            }

    def _post_process(self, result: Any) -> Any:
        if isinstance(result, dict) and "answer" in result:
            return {"answer": result["answer"]}
        return result
