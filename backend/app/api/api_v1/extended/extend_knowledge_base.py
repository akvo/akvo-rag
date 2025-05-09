from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user
from app.models.knowledge import KnowledgeBase, Document
from app.schemas.knowledge import (
    KnowledgeBaseResponse,
)

from sqlalchemy import or_

from app.api.api_v1.extended.util.util_user import get_super_user_ids

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("", response_model=List[KnowledgeBaseResponse])
def get_knowledge_bases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """
    Retrieve knowledge bases.
    - include knowledge base created by super user
    """
    super_user_ids = get_super_user_ids(db=db)
    knowledge_bases = (
        db.query(KnowledgeBase)
        .filter(or_(
            KnowledgeBase.user_id == current_user.id,
            KnowledgeBase.user_id.in_(super_user_ids)
        ))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return knowledge_bases


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get knowledge base by ID.
    - include knowledge base created by super user
    """
    from sqlalchemy.orm import joinedload

    super_user_ids = get_super_user_ids(db=db)
    kb = (
        db.query(KnowledgeBase)
        .options(
            joinedload(KnowledgeBase.documents)
            .joinedload(Document.processing_tasks)
        )
        .filter(KnowledgeBase.id == kb_id)
        .filter(or_(
            KnowledgeBase.user_id == current_user.id,
            KnowledgeBase.user_id.in_(super_user_ids)
        ))
        .first()
    )

    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    return kb
