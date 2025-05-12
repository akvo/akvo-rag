from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging

from app import models, schemas
from app.db.session import get_db
from app.services.api_key import APIKeyService
from app.api.api_v1.auth import get_current_user


router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("", response_model=List[schemas.APIKey])
def read_api_keys(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
) -> Any:
    """
    Retrieve API keys.
    """
    api_keys = APIKeyService.get_api_keys(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return api_keys


@router.post("", response_model=schemas.APIKey)
def create_api_key(
    *,
    db: Session = Depends(get_db),
    api_key_in: schemas.APIKeyCreate,
    current_user: models.User = Depends(get_current_user),
) -> Any:
    """
    Create new API key.
    """
    api_key = APIKeyService.create_api_key(
        db=db, user_id=current_user.id, name=api_key_in.name
    )
    logger.info(f"API key created: {api_key.key} for user {current_user.id}")
    return api_key
