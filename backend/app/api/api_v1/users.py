"""
Created on Nov 14, 2025
API endpoints for user management only accessible by admin users.
GET: List users with pagination and filter by active status.
PATCH: Update toggle user's active status.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User
from app.schemas.user import UserResponse, UserPagination
from app.db.session import get_db
from app.api.api_v1.auth import get_current_user

router = APIRouter()


@router.get("", response_model=UserPagination)
def read_users(
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 10,
    is_active: bool = None,
    search: str = None,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve users with pagination. Admin access required.
    Args:
        page: Page number (1-indexed)
        size: Number of items per page
        is_active: Filter by active status
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )

    query = db.query(User)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            User.email.ilike(f"%{search}%") |
            User.username.ilike(f"%{search}%")
        )

    total = query.count()
    # Calculate offset from page number (1-indexed)
    skip = (page - 1) * size
    users = query.offset(skip).limit(size).all()

    return UserPagination(
        total=total,
        page=page,
        size=size,
        data=users
    )


@router.patch("/{user_id}/toggle-active", response_model=UserResponse)
def toggle_user_active_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Toggle a user's active status. Admin access required.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/toggle-superuser", response_model=UserResponse)
def toggle_user_superuser_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Toggle a user's superuser status. Admin access required.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resource"
        )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=400, detail="Cannot change own superuser status"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=400, detail=(
                "Cannot change superuser status of inactive user"
            )
        )

    user.is_superuser = not user.is_superuser
    db.commit()
    db.refresh(user)
    return user
