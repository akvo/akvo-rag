from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class JobCreate(BaseModel):
    """Universal job creation schema."""
    job: str
    prompt: Optional[str] = None
    chats: Optional[List[ChatMessage]] = None  # used for chat-type jobs
    callback_url: Optional[str] = None
    callback_params: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    trace_id: Optional[str]
    message: str


class JobStatus(BaseModel):
    job_id: str
    job: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
