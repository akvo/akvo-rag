from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.chat import Chat, ChatKnowledgeBase

from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
)
from app.api.api_v1.auth import get_current_user


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
