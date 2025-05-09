from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from requests.exceptions import RequestException

from app.core import security
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

import logging

router = APIRouter()

logger = logging.getLogger(__name__)


# Support set user as super user
@router.post("/register", response_model=UserResponse)
def register(
    *, db: Session = Depends(get_db), user_in: UserCreate
) -> Any:
    """
    Register a new user.
    """
    try:
        # Check if user with this email exists
        user = db.query(User).filter(User.email == user_in.email).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="A user with this email already exists.",
            )

        # Check if user with this username exists
        user = db.query(User).filter(User.username == user_in.username).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail="A user with this username already exists.",
            )

        # Create new user
        user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=security.get_password_hash(user_in.password),
            is_superuser=user_in.is_superuser,
            is_active=user_in.is_active
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except RequestException as e:
        msg = "Network error or server is unreachable. Please try again later."
        raise HTTPException(
            status_code=503,
            detail=msg,
        ) from e
