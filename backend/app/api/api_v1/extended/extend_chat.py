from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.user import User
from app.models.chat import Chat, ChatKnowledgeBase

from app.schemas.chat import ChatCreate, ChatResponse, CreateMessagePayload
from app.api.api_v1.auth import get_current_user
from app.services.chat_mcp_service import stream_mcp_response

router = APIRouter()


@router.post("", response_model=ChatResponse)
def create_chat(
    *,
    db: Session = Depends(get_db),
    chat_in: ChatCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    chat = Chat(
        title=chat_in.title,
        user_id=current_user.id,
    )
    # Convert raw KB IDs into ChatKnowledgeBase objects
    chat.knowledge_bases = [
        ChatKnowledgeBase(knowledge_base_id=kb_id)
        for kb_id in chat_in.knowledge_base_ids
    ]

    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("", response_model=List[ChatResponse])
def get_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return chats


@router.post("/{chat_id}/messages/mcp_integration")
async def create_message_mcp_integration(
    *,
    db: Session = Depends(get_db),
    chat_id: int,
    messages: CreateMessagePayload,
    current_user: User = Depends(get_current_user)
) -> StreamingResponse:
    chat = (
        db.query(Chat)
        .options(joinedload(Chat.knowledge_bases))
        .filter(Chat.id == chat_id, Chat.user_id == current_user.id)
        .first()
    )
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = messages.model_dump()
    last_message = messages["messages"][-1]
    if last_message["role"] != "user":
        raise HTTPException(
            status_code=400, detail="Last message must be from user"
        )

    knowledge_base_ids = [
        ckb.knowledge_base_id for ckb in chat.knowledge_bases
    ]

    async def response_stream():
        async for chunk in stream_mcp_response(
            query=last_message["content"],
            messages=messages,
            knowledge_base_ids=knowledge_base_ids,
            chat_id=chat_id,
            db=db,
        ):
            yield chunk

    return StreamingResponse(
        response_stream(),
        media_type="text/event-stream",
        headers={"x-vercel-ai-data-stream": "v1"},
    )
