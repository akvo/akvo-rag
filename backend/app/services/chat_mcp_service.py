import logging
from sqlalchemy.orm import Session
from app.models import Message
from app.services.prompt_service import PromptService
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
    Handles both streaming chunks and final persistence to DB.
    """
    prompt_service = PromptService(db=db)

    # Load chat history from DB only if messages length <= 1
    if len(messages.get("messages", [])) <= 1:
        chat_history_query = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .limit(max_history_length)
            .all()
        )
        # reverse to chronological order
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in reversed(chat_history_query)
        ]
    else:
        # Use messages passed from frontend, limited to last max_history_length
        chat_history = messages.get("messages", [])[-max_history_length:]

    contextualize_prompt = prompt_service.get_full_contextualize_prompt()
    qa_prompt = prompt_service.get_full_qa_strict_prompt()

    initial_state = {
        "query": query,
        "chat_history": chat_history,
        "contextualize_prompt_str": contextualize_prompt,
        "qa_prompt_str": qa_prompt,
        "scope": {"knowledge_base_ids": knowledge_base_ids},
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

    # Get final state to save messages
    final_state = await query_answering_workflow.ainvoke(initial_state)

    # Persist user and assistant messages
    db.add_all(
        [
            Message(content=query, role="user", chat_id=chat_id),
            Message(
                content=final_state["answer"],
                role="assistant",
                chat_id=chat_id,
            ),
        ]
    )
    db.commit()

    logger.info(f"[Chat {chat_id}] Messages persisted with MCP integration")
