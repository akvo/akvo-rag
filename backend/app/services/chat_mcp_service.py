import json
import base64
import logging
from sqlalchemy.orm import Session
from app.models import Message
from app.services.prompt_service import PromptService
from app.services.system_settings_service import SystemSettingsService
from app.services.query_answering_workflow import query_answering_workflow

logger = logging.getLogger(__name__)


async def stream_mcp_response(
    query: str,
    messages: dict,
    knowledge_base_ids: list,
    chat_id: int,
    db: Session,
    max_history_length: int = 10,
):
    """
    Stream a response from the MCP-integrated workflow.
    Combines serialized context + answer in one SSE chunk for frontend parsing.
    Persists final response to DB.
    """
    if not knowledge_base_ids:
        raise ValueError("No knowledge_base_ids provided for this chat.")

    prompt_service = PromptService(db=db)
    settings_service = SystemSettingsService(db=db)
    # Get global top_k setting and use it for vector retrieval
    top_k = settings_service.get_top_k()

    # Load chat history from DB only if messages length <= 1
    if len(messages.get("messages", [])) <= 1:
        chat_history_query = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())  # chronological order
            .limit(max_history_length)
            .all()
        )
        chat_history = [
            {"role": m.role, "content": m.content} for m in chat_history_query
        ]
    else:
        # Use messages passed from frontend, limited to last max_history_length
        chat_history = messages.get("messages", [])[-max_history_length:]

    # Build prompts
    contextualize_prompt = prompt_service.get_full_contextualize_prompt()
    qa_prompt = prompt_service.get_full_qa_strict_prompt()

    # Initial workflow state
    initial_state = {
        "query": query,
        "chat_history": chat_history,
        "contextualize_prompt_str": contextualize_prompt,
        "qa_prompt_str": qa_prompt,
        "scope": {"knowledge_base_ids": knowledge_base_ids, "top_k": top_k},
    }

    # Stream workflow events
    async for event in query_answering_workflow.astream_events(
        initial_state, stream_mode="values"
    ):
        if (
            event["event"] == "on_chain_stream"
            and event.get("name") == "generate"
        ):
            data = event.get("data", {})
            chunk = data.get("chunk", "")
            if chunk:
                yield f"data: {chunk}\n\n"

    # Get final state to include context + answer
    final_state = await query_answering_workflow.ainvoke(initial_state)

    # Combine serialized context + answer for final persistence and streaming
    full_response = ""

    # Serialize context documents
    if final_state.get("context"):
        serializable_context = [
            {
                "page_content": doc.page_content.replace('"', '\\"'),
                "metadata": doc.metadata,
            }
            for doc in final_state["context"]
        ]
        escaped_context = json.dumps({"context": serializable_context})
        base64_context = base64.b64encode(escaped_context.encode()).decode()
        separator = "__LLM_RESPONSE__"
        full_response += base64_context + separator
        yield f'0:"{base64_context}{separator}"\n'

    # Append final answer
    if final_state.get("answer"):
        answer_chunk = final_state["answer"]
        full_response += answer_chunk
        escaped_chunk = answer_chunk.replace('"', '\\"').replace("\n", "\\n")
        yield f'0:"{escaped_chunk}"\n'

    # Persist both context + answer
    db.add_all(
        [
            Message(content=query, role="user", chat_id=chat_id),
            Message(content=full_response, role="assistant", chat_id=chat_id),
        ]
    )
    db.commit()

    logger.info(f"[Chat {chat_id}] Messages persisted with MCP integration")
