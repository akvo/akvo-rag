from typing import List, Optional
from pydantic import BaseModel, HttpUrl, field_validator
from datetime import datetime

from app.models.app import AppStatus


class AppRegisterRequest(BaseModel):
    app_name: str
    domain: str
    default_chat_prompt: Optional[str] = ""
    chat_callback: str
    upload_callback: str
    callback_token: str

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
    knowledge_base_id: Optional[int] = None

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
    knowledge_base_id: Optional[int] = None

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
