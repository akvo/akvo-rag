import re
import json
import asyncio

from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import TypedDict, Dict, Any

from app.services.llm.llm_factory import LLMFactory
from app.services.prompt_service import PromptService
from app.db.session import SessionLocal
from mcp_clients.multi_mcp_client_manager import MultiMCPClientManager
from app.models.chat import Chat, Message
from app.services.scoping_agent.scoping_agent import scoping_agent
from app.services.response_generator import decode_mcp_context


class GraphState(TypedDict):
    chat_id: int
    query: str
    contextual_query: str
    scope: Dict[str, Any]
    mcp_result: Any
    context: list
    answer: str


def get_chat_history(chat_id: int) -> list:
    """Retrieve the last n messages from the chat history."""
    db = SessionLocal()

    chat = db.query(Chat).filter(Chat.id == chat_id).first()

    if not chat:
        raise ValueError(f"Chat with ID {chat_id} not found.")

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    db.close()

    return (
        [
            {"role": message.role, "content": message.content}
            for message in messages
        ]
        if messages
        else []
    )


def contextualize_node(state: GraphState) -> GraphState:
    """Contextualize the user query using a prompt and LLM."""

    db = SessionLocal()
    prompt_service = PromptService(db=db)
    chat_history = get_chat_history(chat_id=state.get("chat_id", None))

    llm = LLMFactory.create()

    contextualize_prompt_str = prompt_service.get_full_contextualize_prompt()
    contextualize_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_prompt_str),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    chain = contextualize_prompt | llm

    result = chain.invoke(
        {"chat_history": chat_history, "input": state["query"]}
    )
    db.close()

    state["contextual_query"] = result.content.strip()
    return state


async def scoping_node(state: GraphState) -> GraphState:
    """
    Determine the scope for the MCP tool based on the contextualized query.
    """
    agent = await scoping_agent()

    payload = {}
    scoping_result = await agent.ainvoke({"messages": [state["query"]]})
    scoping_result = scoping_result.get("messages", [{}])[-1]
    if scoping_result:
        content_str = scoping_result.content.strip()
        match = re.search(r"```json\s*(.*?)\s*```", content_str, re.S)
        if match:
            content_str = match.group(1).strip()
        else:
            content_str = content_str.strip()
        payload = json.loads(content_str)

    state["scope"] = {
        "server_name": payload.get("server_name", None),
        "tool_name": payload.get("tool_name", None),
        "input": payload.get("input", {}),
    }
    return state


async def run_mcp_tool_node(state: GraphState) -> GraphState:
    """Run the MCP tool with the determined scope and input parameters."""

    manager = MultiMCPClientManager()
    scope = state["scope"]
    result = await manager.run_tool(
        server_name=scope["server_name"],
        tool_name=scope["tool_name"],
        param=scope.get("input", {}),
    )
    state["mcp_result"] = result
    return state


def post_processing_node(state: GraphState) -> GraphState:
    """Post-process the result from the MCP tool to extract context."""
    try:
        b64_text = state["mcp_result"].content[0].text
        b64 = json.loads(b64_text)
        contexts = decode_mcp_context(base64_context=b64.get("context", ""))
        state["context"] = contexts
    except Exception:
        state["context"] = ""
    return state


def response_generation_node(state: GraphState) -> GraphState:
    """
    Generate a response using the LLM based on the context and user query.
    """
    print(len(state["context"]), "context found")

    llm = LLMFactory.create()
    prompt = f"""
    You are a helpful assistant.
    User question: {state["query"]}
    Context: {state["context"]}
    Please answer the question using the context above.
    """
    result = llm.invoke(prompt)
    state["answer"] = result.content.strip()
    return state


# Build the graph
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

app = workflow.compile()

# Run example
if __name__ == "__main__":

    async def main():
        chat_id = 1  # Example chat ID
        initial_state = {
            "chat_id": chat_id,
            "query": "Explain about Kenya climate based on the context.",
        }
        final_state = await app.ainvoke(initial_state)
        print("FINAL ANSWER:", final_state["answer"])

    asyncio.run(main())
