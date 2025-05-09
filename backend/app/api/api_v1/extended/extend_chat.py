from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.chat import Chat
from app.models.knowledge import KnowledgeBase
from app.schemas.chat import (
    ChatCreate,
    ChatResponse,
)
from app.api.api_v1.auth import get_current_user

from sqlalchemy import or_
from app.api.api_v1.extended.util.util_user import get_super_user_ids


router = APIRouter()


@router.post("", response_model=ChatResponse)
def create_chat(
    *,
    db: Session = Depends(get_db),
    chat_in: ChatCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    # Verify knowledge bases exist and belong to user
    # - include knowledge base created by super user
    super_user_ids = get_super_user_ids(db=db)
    knowledge_bases = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.id.in_(chat_in.knowledge_base_ids),
        ).filter(or_(
            KnowledgeBase.user_id == current_user.id,
            KnowledgeBase.user_id.in_(super_user_ids)
        ))
        .all()
    )
    if len(knowledge_bases) != len(chat_in.knowledge_base_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more knowledge bases not found"
        )

    chat = Chat(
        title=chat_in.title,
        user_id=current_user.id,
    )
    chat.knowledge_bases = knowledge_bases

    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


@router.get("", response_model=List[ChatResponse])
def get_chats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return chats
