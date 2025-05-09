from typing import List, Any, Optional
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


class ExtendKnowledgeBaseResponse(KnowledgeBaseResponse):
    is_superuser: Optional[bool] = False


@router.get("", response_model=List[ExtendKnowledgeBaseResponse])
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
        db.query(KnowledgeBase, User.is_superuser)
        .join(User, KnowledgeBase.user_id == User.id, isouter=True)
        .filter(or_(
            KnowledgeBase.user_id == current_user.id,
            KnowledgeBase.user_id.in_(super_user_ids)
        ))
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for kb, is_superuser in knowledge_bases:
        kb_data = ExtendKnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            documents=kb.documents or [],
            is_superuser=is_superuser,
        )
        results.append(kb_data)

    return results


@router.get("/{kb_id}", response_model=ExtendKnowledgeBaseResponse)
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
    kb_data = (
        db.query(KnowledgeBase, User.is_superuser)
        .join(User, KnowledgeBase.user_id == User.id, isouter=True)
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

    kb, is_superuser = kb_data
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    result = ExtendKnowledgeBaseResponse(
        id=kb.id,
        user_id=kb.user_id,
        name=kb.name,
        description=kb.description,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
        documents=kb.documents or [],
        is_superuser=is_superuser,
    )

    return result
