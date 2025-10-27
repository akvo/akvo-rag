import json
import base64
import logging
from typing import TypedDict, Dict, Any, List, Optional

from langgraph.graph import StateGraph
from langchain_core.documents import Document
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain.chains.combine_documents import create_stuff_documents_chain

from app.services.llm.llm_factory import LLMFactory
from mcp_clients.mcp_client_manager import MCPClientManager
from app.services.scoping_agent import ScopingAgent

# ---------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------
# Graph State Definition
# ---------------------------------------------------------------------
class GraphState(TypedDict, total=False):
    query: str
    chat_history: List[Dict[str, str]]
    contextualize_prompt_str: str
    qa_prompt_str: str
    contextual_query: str
    scope: Dict[str, Any]
    mcp_result: Any
    context: list
    answer: str
    error: Optional[str]

# ---------------------------------------------------------------------
# Helper: Decode Base64 MCP Context
# ---------------------------------------------------------------------
def decode_mcp_context(base64_context: str) -> List[Document]:
    """Decode Base64-encoded MCP context safely."""
    if not base64_context:
        return []
    try:
        decoded = base64.b64decode(base64_context).decode()
        context_dict = json.loads(decoded)
        items = context_dict.get("context", [])
        if not isinstance(items, list):
            return []
        return [
            Document(
                page_content=item.get("page_content", ""),
                metadata=item.get("metadata", {}),
            )
            for item in items
        ]
    except Exception as e:
        logger.warning(f"Failed to decode MCP context: {e}")
        return []

# ---------------------------------------------------------------------
# Reuse LLM instance
# ---------------------------------------------------------------------
llm_instance = LLMFactory.create()

# ---------------------------------------------------------------------
# Workflow Nodes
# ---------------------------------------------------------------------

async def contextualize_node(state: GraphState) -> GraphState:
    """Contextualize user query using LLM."""
    try:
        contextualize_prompt = ChatPromptTemplate.from_messages([
            ("system", state["contextualize_prompt_str"]),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])
        chain = contextualize_prompt | llm_instance

        result = await chain.ainvoke(
            {"chat_history": state["chat_history"], "input": state["query"]}
        )

        contextual_query = result.content.strip()
        logger.info(f"Contextualized query: {contextual_query}")
        return {**state, "contextual_query": contextual_query}

    except Exception as e:
        logger.exception(f"contextualize_node failed: {e}")
        return {**state, "error": str(e)}


async def scoping_node(state: GraphState) -> GraphState:
    """Determine the MCP tool scope using ScopingAgent."""
    try:
        agent = ScopingAgent()
        scope = agent.scope_query(
            query=state["contextual_query"],
            scope=state.get("scope", {}),
        )
        logger.info(f"Scope determined: {scope}")
        return {**state, "scope": scope}

    except Exception as e:
        logger.exception(f"scoping_node failed: {e}")
        return {**state, "error": str(e)}


async def run_mcp_tool_node(state: GraphState) -> GraphState:
    """Run the MCP tool using the determined scope."""
    try:
        manager = MCPClientManager()
        scope = state.get("scope", {})

        result = await manager.run_tool(
            server_name=scope.get("server_name"),
            tool_name=scope.get("tool_name"),
            param=scope.get("input", {}),
        )

        logger.info("MCP tool executed successfully.")
        return {**state, "mcp_result": result}

    except Exception as e:
        logger.exception(f"run_mcp_tool_node failed: {e}")
        return {**state, "error": str(e)}


async def post_processing_node(state: GraphState) -> GraphState:
    """Decode context from MCP tool result."""
    try:
        mcp_content = state["mcp_result"].content[0].text
        parsed = json.loads(mcp_content)
        contexts = decode_mcp_context(parsed.get("context", ""))
        logger.info(f"Decoded {len(contexts)} context documents.")
        return {**state, "context": contexts}

    except Exception as e:
        logger.warning(f"Failed to post-process MCP result: {e}")
        return {**state, "context": [], "error": str(e)}


async def response_generation_node(state: GraphState):
    """Stream the final LLM-generated response."""
    try:
        qa_prompt = ChatPromptTemplate.from_messages([
            ("system", state["qa_prompt_str"]),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ])

        document_prompt = PromptTemplate.from_template("\n\n- {page_content}\n\n")

        qa_chain = create_stuff_documents_chain(
            llm=llm_instance,
            prompt=qa_prompt,
            document_prompt=document_prompt,
            document_variable_name="context",
        )

        full_response = ""
        async for chunk in qa_chain.astream({
            "input": state["contextual_query"],
            "context": state.get("context", []),
            "chat_history": state.get("chat_history", []),
        }):
            if isinstance(chunk, str):
                full_response += chunk
                safe_chunk = chunk.replace("\n", "\\n")
                yield f'0:"{safe_chunk}"\n'

        yield {**state, "answer": full_response}

    except Exception as e:
        logger.exception(f"response_generation_node failed: {e}")
        yield {"type": "error", "error": str(e), "state": state}


# ---------------------------------------------------------------------
# Build Workflow Graph
# ---------------------------------------------------------------------
workflow = StateGraph(GraphState)
workflow.add_node("contextualize", contextualize_node)
workflow.add_node("scope", scoping_node)
workflow.add_node("run_mcp", run_mcp_tool_node)
workflow.add_node("post_process", post_processing_node)
workflow.add_node("generate", response_generation_node)

workflow.set_entry_point("contextualize")
workflow.add_edge("contextualize", "scope")
workflow.add_edge("scope", "run_mcp")
workflow.add_edge("run_mcp", "post_process")
workflow.add_edge("post_process", "generate")

query_answering_workflow = workflow.compile()
