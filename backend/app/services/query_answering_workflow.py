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

def ensure_documents(context_data):
    """Convert plain dicts or other data into a list of LangChain Documents."""
    logger.debug(f"[ensure_documents] Received context_data type={type(context_data)}")

    if not context_data:
        logger.info("[ensure_documents] Empty context_data, returning [].")
        return []

    # Already Document objects
    if isinstance(context_data, list) and all(hasattr(d, "page_content") for d in context_data):
        logger.debug("[ensure_documents] Already list of Document objects.")
        return context_data

    # Single dict
    if isinstance(context_data, dict):
        logger.debug("[ensure_documents] Single dict detected, wrapping in Document.")
        text = json.dumps(context_data, indent=2, ensure_ascii=False)
        return [Document(page_content=text, metadata={"source": "mcp_rest_result"})]

    # List of dicts
    if isinstance(context_data, list) and all(isinstance(d, dict) for d in context_data):
        logger.debug(f"[ensure_documents] List of {len(context_data)} dicts detected.")
        docs = []
        for idx, item in enumerate(context_data):
            try:
                text = json.dumps(item, indent=2, ensure_ascii=False)
                docs.append(Document(page_content=text, metadata={"source": "mcp_rest_result", "index": idx}))
            except Exception as e:
                logger.warning(f"[ensure_documents] Failed to serialize item {idx}: {e}")
        return docs

    # Fallback
    logger.debug("[ensure_documents] Fallback: converting to string.")
    return [Document(page_content=str(context_data), metadata={"source": "mcp_rest_result"})]

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
        scope = await agent.scope_query(
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


async def post_processing_node(state):
    """Extract and normalize MCP tool result into Document list format."""
    logger.info("[post_processing_node] Starting post-processing of MCP result...")

    try:
        mcp_result = state.get("mcp_result")
        if not mcp_result:
            logger.warning("[post_processing_node] No mcp_result found in state.")
            state["context"] = []
            return state

        # --- Try decode Knowledge Base (base64 encoded) context ---
        try:
            b64_text = mcp_result.content[0].text
            b64 = json.loads(b64_text)
            logger.debug("[post_processing_node] Detected KB/Chroma-style base64 context.")
            contexts = decode_mcp_context(base64_context=b64.get("context", ""))
            state["context"] = ensure_documents(contexts)
            logger.info("[post_processing_node] Successfully decoded base64 context.")
            return state

        except Exception as e:
            logger.debug(f"[post_processing_node] Not a base64 KB context: {e}")

        # --- Otherwise, assume it's a REST MCP JSON result ---
        json_result = None

        if isinstance(mcp_result, dict):
            logger.debug("[post_processing_node] Detected dict-based MCP result.")
            json_result = mcp_result

        elif hasattr(mcp_result, "content"):
            try:
                text = getattr(mcp_result.content[0], "text", "")
                logger.debug(f"[post_processing_node] Parsing .content text: {text[:200]}...")
                json_result = json.loads(text)
                logger.info("[post_processing_node] Parsed REST MCP JSON result successfully.")
            except Exception as e:
                logger.warning(f"[post_processing_node] Failed to parse REST MCP result as JSON: {e}")
                json_result = {"raw_text": str(mcp_result)}

        else:
            logger.warning("[post_processing_node] Unknown MCP result type, wrapping as string.")
            json_result = {"raw_text": str(mcp_result)}

        # Normalize result to Document list
        docs = ensure_documents(json_result)
        state["context"] = docs
        logger.info(f"[post_processing_node] Generated {len(docs)} Document(s) from MCP result.")

    except Exception as e:
        logger.exception(f"[post_processing_node] Unexpected error during processing: {e}")
        state["context"] = []

    return state


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
