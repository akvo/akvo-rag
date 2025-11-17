from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    username: str
    is_active: bool = False
    is_superuser: bool = False


class Approver(BaseModel):
    id: int
    email: EmailStr
    username: str

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDataResponse(UserResponse):
    approver: Optional[Approver] = None
    approved_at: Optional[datetime] = None

    @field_validator('approver', mode='before')
    @classmethod
    def validate_approver(cls, v: Any) -> Optional[dict]:
        if v is None:
            return None
        # If it's already a dict, return it
        if isinstance(v, dict):
            return v
        # If it's a SQLAlchemy model, extract only needed fields
        if hasattr(v, 'id'):
            return {
                'id': v.id,
                'email': v.email,
                'username': v.username
            }
        return None


class UserPagination(BaseModel):
    total: int
    page: int
    size: int
    data: list[UserDataResponse]
