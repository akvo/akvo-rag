from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.prompt import PromptNameEnum
from datetime import datetime


class PromptVersionBase(BaseModel):
    content: str = Field(..., example="Your system prompt here")
    activation_reason: Optional[str] = None


class PromptCreate(PromptVersionBase):
    name: PromptNameEnum


class PromptUpdate(PromptVersionBase):
    pass


class PromptVersionResponse(BaseModel):
    version_number: int
    content: str
    is_active: bool
    updated_at: datetime
    activation_reason: Optional[str]

    class Config:
        orm_mode = True


class PromptResponse(BaseModel):
    name: PromptNameEnum
    active_version: Optional[PromptVersionResponse]
    all_versions: Optional[List[PromptVersionResponse]] = []

    class Config:
        orm_mode = True
