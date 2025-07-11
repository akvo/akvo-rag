from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.prompt import PromptNameEnum
from datetime import datetime


class UserInfo(BaseModel):
    id: int
    email: Optional[str] = None

    class Config:
        orm_mode = True


class PromptVersionBase(BaseModel):
    content: str = Field(..., example="Your system prompt here")
    activation_reason: Optional[str] = None


class PromptCreate(PromptVersionBase):
    name: PromptNameEnum


class PromptUpdate(PromptVersionBase):
    pass


class ReactivatePromptRequest(BaseModel):
    reactivation_reason: Optional[str] = None


class PromptVersionResponse(BaseModel):
    id: int
    version_number: int
    content: str
    is_active: bool
    updated_at: datetime
    activation_reason: Optional[str]
    activated_by_user: Optional[UserInfo]

    class Config:
        orm_mode = True


class PromptResponse(BaseModel):
    name: PromptNameEnum
    active_version: Optional[PromptVersionResponse]
    all_versions: Optional[List[PromptVersionResponse]] = []

    class Config:
        orm_mode = True
