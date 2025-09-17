import json
import base64

from typing import TypedDict, Dict, Any, List
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


class GraphState(TypedDict):
    query: str
    chat_history: List[Dict[str, str]]
    contextualize_prompt_str: str
    qa_prompt_str: str
    contextual_query: str
    scope: Dict[str, Any]
    mcp_result: Any
    context: list
    answer: str


def decode_mcp_context(base64_context: str) -> List[Document]:
    """
    Decode Base64-encoded MCP context into a list of LangChain Documents.
    """
    decoded = base64.b64decode(base64_context).decode()
    context_dict = json.loads(decoded)
    return [
        Document(
            page_content=item["page_content"],
            metadata=item.get("metadata", {}),
        )
        for item in context_dict.get("context", [])
    ]


def contextualize_node(state: GraphState) -> GraphState:
    """Contextualize the user query using LLM + provided prompt."""
    llm = LLMFactory.create()

    contextualize_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", state["contextualize_prompt_str"]),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    chain = contextualize_prompt | llm

    result = chain.invoke(
        {"chat_history": state["chat_history"], "input": state["query"]}
    )

    state["contextual_query"] = result.content.strip()
    return state


async def scoping_node(state: GraphState) -> GraphState:
    """Determine the scope (server, tool, input) using ScopingAgent."""
    agent = ScopingAgent()

    # For now we assume KB ID is already known and passed in input
    kb_id = state.get("scope", {}).get("kb_id", None)
    if not kb_id:
        raise ValueError("KB ID is required in state['scope']")
    kb_id = int(kb_id)

    scope = agent.scope_query(query=state["contextual_query"], kb_id=kb_id)
    state["scope"] = scope
    return state


async def run_mcp_tool_node(state: GraphState) -> GraphState:
    """Run the MCP tool using the determined scope."""
    manager = MCPClientManager()
    scope = state["scope"]

    result = await manager.run_tool(
        server_name=scope["server_name"],
        tool_name=scope["tool_name"],
        param=scope.get("input", {}),
    )
    state["mcp_result"] = result
    return state


def post_processing_node(state: GraphState) -> GraphState:
    """Extract context from MCP tool result."""
    try:
        b64_text = state["mcp_result"].content[0].text
        b64 = json.loads(b64_text)
        contexts = decode_mcp_context(base64_context=b64.get("context", ""))
        state["context"] = contexts
    except Exception:
        state["context"] = []
    return state


async def response_generation_node(state: GraphState):
    """Generate final response using LLM, streaming supported."""
    llm = LLMFactory.create()

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", state["qa_prompt_str"]),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    document_prompt = PromptTemplate.from_template("\n\n- {page_content}\n\n")

    qa_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=qa_prompt,
        document_prompt=document_prompt,
        document_variable_name="context",
    )

    full_response = ""
    async for chunk in qa_chain.astream(
        {
            "input": state["contextual_query"],
            "context": state["context"],
            "chat_history": state["chat_history"],
        }
    ):
        if isinstance(chunk, str):
            full_response += chunk
            escaped = chunk.replace('"', '\\"').replace("\n", "\\n")
            yield f'0:"{escaped}"\n'

    state["answer"] = full_response
    yield state


# Build workflow graph
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
