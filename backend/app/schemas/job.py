from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    trace_id: Optional[str]

    class Config:
        orm_mode = True


class JobStatus(BaseModel):
    job_id: str
    job: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None
