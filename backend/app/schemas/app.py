from typing import List, Optional, Generic, TypeVar
from urllib.parse import urlparse
from pydantic import BaseModel, field_validator, Field
from datetime import datetime

from app.models.app import AppStatus

# Hosts allowed over HTTP when ALLOW_HTTP_CALLBACKS=True
_LOCAL_DEV_HOSTS = {
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
    "0.0.0.0",
}


def _is_callback_url_allowed(url: str) -> bool:
    """Return True if the URL is acceptable as a callback."""
    if url.startswith("https://"):
        return True
    # Allow HTTP only for local dev hosts when explicitly enabled
    from app.core.config import settings

    if settings.ALLOW_HTTP_CALLBACKS and url.startswith("http://"):
        host = urlparse(url).hostname or ""
        if host in _LOCAL_DEV_HOSTS:
            return True
    return False


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    data: List[T]


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
        if not _is_callback_url_allowed(v):
            raise ValueError(
                "Callback URLs must use HTTPS "
                "(HTTP allowed only for local dev hosts "
                "when ALLOW_HTTP_CALLBACKS=True)"
            )
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
        if v is not None and not _is_callback_url_allowed(v):
            raise ValueError(
                "Callback URLs must use HTTPS "
                "(HTTP allowed only for local dev hosts "
                "when ALLOW_HTTP_CALLBACKS=True)"
            )
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


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the knowledge base")
    description: Optional[str] = Field(
        None, description="Description of the KB"
    )
    is_default: bool = Field(
        False, description="Whether this KB is the default for the app"
    )


class KnowledgeBaseUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Name of the knowledge base")
    description: Optional[str] = Field(
        None, description="Description of the KB"
    )
    is_default: Optional[bool] = Field(
        None, description="Whether this KB is the default for the app"
    )


class KnowledgeBaseResponse(BaseModel):
    id: int
    knowledge_base_id: int
    name: str
    description: Optional[str]
    is_default: bool

    class Config:
        from_attributes = True


class KnowledgeBaseListItem(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    documents: List[dict] = []  # or create a DocumentResponse model

    class Config:
        from_attributes = True


class PaginatedKnowledgeBaseResponse(PaginatedResponse[KnowledgeBaseListItem]):
    pass


class KnowledgeBaseDetailResponse(BaseModel):
    name: str
    description: Optional[str]
    id: int
    created_at: datetime
    updated_at: datetime
    is_default: bool
    documents: List[dict] = []


class ProcessingTaskItem(BaseModel):
    id: int
    document_id: int
    knowledge_base_id: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentItem(BaseModel):
    id: int
    knowledge_base_id: int

    file_name: str
    file_path: str
    file_hash: str
    file_size: int
    content_type: Optional[str]

    created_at: datetime
    updated_at: datetime

    processing_tasks: List[ProcessingTaskItem] = []

    class Config:
        from_attributes = True


class PaginatedDocumentResponse(PaginatedResponse[DocumentItem]):
    pass
