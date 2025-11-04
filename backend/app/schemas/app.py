from typing import List, Optional
from pydantic import BaseModel, HttpUrl, field_validator
from datetime import datetime

from app.models.app import AppStatus


class KnowledgeBaseItem(BaseModel):
    knowledge_base_id: int
    is_default: bool

    class Config:
        from_attributes = True


class AppRegisterRequest(BaseModel):
    app_name: str
    domain: str
    default_chat_prompt: Optional[str] = ""
    chat_callback: str
    upload_callback: str
    callback_token: Optional[str] = None

    @field_validator("chat_callback", "upload_callback")
    @classmethod
    def validate_https_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("Callback URLs must use HTTPS")
        return v


class AppRegisterResponse(BaseModel):
    app_id: str
    client_id: str
    access_token: str
    scopes: List[str]
    knowledge_bases: List[KnowledgeBaseItem]

    class Config:
        from_attributes = True


class AppUpdateRequest(BaseModel):
    app_name: Optional[str] = None
    domain: Optional[str] = None
    default_chat_prompt: Optional[str] = None
    chat_callback: Optional[str] = None
    upload_callback: Optional[str] = None
    callback_token: Optional[str] = None

    @field_validator("chat_callback", "upload_callback")
    @classmethod
    def validate_https_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("https://"):
            raise ValueError("Callback URLs must use HTTPS")
        return v


class AppUpdateResponse(BaseModel):
    app_id: str
    app_name: str
    domain: str
    default_chat_prompt: Optional[str] = None
    chat_callback: str
    upload_callback: str
    callback_token: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class AppMeResponse(BaseModel):
    app_id: str
    app_name: str
    domain: str
    default_chat_prompt: Optional[str]
    chat_callback_url: str
    upload_callback_url: str
    scopes: List[str]
    status: AppStatus
    knowledge_bases: List[KnowledgeBaseItem]

    class Config:
        from_attributes = True


class AppRotateRequest(BaseModel):
    rotate_access_token: bool = False
    rotate_callback_token: bool = False
    new_callback_token: Optional[str] = None


class AppRotateResponse(BaseModel):
    app_id: str
    access_token: Optional[str] = None
    callback_token: Optional[str] = None
    message: str

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    error: str
    message: str


class DocumentUploadItem(BaseModel):
    id: int
    file_name: str
    status: str
    knowledge_base_id: int
    content_type: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
