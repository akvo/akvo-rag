import re
import json
import logging

from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.services.llm.llm_factory import LLMFactory
from app.services.prompt_service import PromptService
from app.db.session import SessionLocal
from mcp_clients.multi_mcp_client_manager import MultiMCPClientManager

logger = logging.getLogger(__name__)


class QueryDispatcher:

    def __init__(self):
        self.manager = MultiMCPClientManager()

    async def dispatch(
        self, scoping_result: Dict[str, Any], chat_history: List[dict] = []
    ) -> Dict[str, Any]:
        if (
            isinstance(scoping_result, dict)
            and "server_name" in scoping_result
        ):
            payload = scoping_result
        elif isinstance(scoping_result, dict) and "messages" in scoping_result:
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
            db = SessionLocal()
            prompt_service = PromptService(db=db)
            llm = LLMFactory.create()

            contextualize_prompt_str = (
                prompt_service.get_full_contextualize_prompt()
            )
            contextualize_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", contextualize_prompt_str),
                    MessagesPlaceholder("chat_history"),
                    ("human", "{input}"),
                ]
            )

            pl_input = payload.get("input", {})
            user_query = pl_input.get("query", "")
            if "text_query" in pl_input:
                user_query = pl_input["text_query"]

            # Generate stand-alone question
            chain = contextualize_prompt | llm
            standalone_question = await chain.ainvoke(
                {"chat_history": chat_history, "input": user_query}
            )

            if "query" in pl_input:
                payload["input"]["query"] = standalone_question.content.strip()
            if "text_query" in pl_input:
                payload["input"][
                    "text_query"
                ] = standalone_question.content.strip()

        except Exception as e:
            logger.error(
                f"Contextualization failed, using original query. Error: {e}"
            )

        finally:
            db.close()

        # --- Call MCP tool ---
        try:
            server_name = payload["server_name"]
            tool_name = payload["tool_name"]
            param = payload.get("input", {})

            result = await self.manager.run_tool(
                server_name=server_name,
                tool_name=tool_name,
                param=param,
            )

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
        try:
            base64_context = result.content[0].text
            base64_context = json.loads(base64_context)
            return base64_context.get("context", "")
        except Exception as e:
            logger.error(f"Post-processing error: {e}")
            return ""
