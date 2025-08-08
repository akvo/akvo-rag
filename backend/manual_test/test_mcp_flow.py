import asyncio
import uuid

from langchain_core.messages import AIMessage, HumanMessage

from app.services.scoping_agent.scoping_agent import scoping_agent
from app.services.query_dispatcher import (
    QueryDispatcher,
)
from app.services.response_generator import (
    generate_response_from_context,
)
from app.db.session import SessionLocal
from app.models.chat import Chat, Message


async def run_flow(user_input: str):
    db = SessionLocal()

    # current chat ID static: 135
    chat_id = 135
    chat = db.query(Chat).filter(Chat.id == chat_id).first()

    if not chat:
        raise ValueError(f"Chat with ID {chat_id} not found.")

    # Generate last n message in backend
    new_messages_id = uuid.uuid4()
    messages = {"id": new_messages_id, "messages": []}
    # limit last n messages
    all_history_messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    for message in all_history_messages:
        messages["messages"].append(
            {
                "role": message.role,
                "content": message.content,
            }
        )
    if not all_history_messages:
        messages["messages"].append({"role": "user", "content": user_input})
        print(messages, "generate n last message")
    # EOL generate last n message in backend

    # Ambil chat_history dari payload (jika ada)
    chat_history = []
    for msg in messages.get("messages", []):
        if msg["role"] == "user":
            chat_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            # if include __LLM_RESPONSE__, only use the last part
            if "__LLM_RESPONSE__" in msg["content"]:
                msg["content"] = msg["content"].split("__LLM_RESPONSE__")[-1]
            chat_history.append(AIMessage(content=msg["content"]))

    agent = await scoping_agent()

    scoping_result = await agent.ainvoke({"messages": [user_input]})

    print("\n=== SCOPING RESULT ===")
    print(scoping_result)

    dispatcher = QueryDispatcher()
    dispatch_result = await dispatcher.dispatch(scoping_result)

    # print("\n=== DISPATCH RESULT ===")
    # print(dispatch_result)

    async for chunk in generate_response_from_context(
        query=user_input,
        tool_contexts=[dispatch_result["processed_result"]],
        db=db,
        chat_id=chat_id,
        chat_history=chat_history,
    ):
        print(chunk, "123")

    return dispatch_result


if __name__ == "__main__":
    query = "Tell me about information on plastic waste management!"
    asyncio.run(run_flow(user_input=query))

# python -m manual_test.test_mcp_flow
