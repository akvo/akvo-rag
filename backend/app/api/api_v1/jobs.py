import json
import logging

from typing import List, Optional, Annotated
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    Form,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import JobResponse
from app.services.job_service import JobService
from app.models.app import App
from app.core.security import get_current_app
from app.tasks.chat_task import execute_chat_job_task

router = APIRouter()
logger = logging.getLogger(__name__)


def safe_json_parse(value: Optional[str]):
    """Helper to safely parse JSON strings into Python objects."""
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")


@router.post("/jobs", response_model=JobResponse)
async def create_job(
    payload: Annotated[
        str,
        Form(
            ...,
            description=(
                "JSON string defining the job details.\n\n"
                "Example:\n"
                "{\n"
                '  "job": "chat",\n'
                '  "prompt": "Explain AI simply.",\n'
                '  "chats": [\n'
                '    {"role": "user", "content": "What is AI?"},\n'
                '    {"role": "assistant", "content": "AI means Artificial Intelligence."}\n'
                '  ],\n'
                '  "callback_params": {"reply_to": "wa:+1234"},\n'
                '  "trace_id": "trace_abc_123"\n'
                "}"
            ),
            example={
                "job": "chat",
                "prompt": "Explain AI simply.",
                "chats": [
                    {"role": "user", "content": "What is AI?"},
                    {"role": "assistant", "content": "AI means Artificial Intelligence."},
                ],
                "callback_params": {"reply_to": "wa:+1234"},
                "trace_id": "trace_abc_123",
            },
        ),
    ],
    files: Optional[List[UploadFile]] = None,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
):
    """Universal job creation endpoint (chat, upload, etc.)."""

    data = safe_json_parse(payload)
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Payload must be a JSON object")

    job_type = data.get("job")
    if not job_type:
        raise HTTPException(status_code=400, detail="Missing 'job' field in payload")

    # Attach uploaded file names (if any)
    if files:
        data["files"] = [f.filename for f in files]

    # Create DB job entry
    job_record = JobService.create_job(
        db=db, job_type=job_type, data=data, app_id=current_app.app_id
    )

    # Determine knowledge base IDs
    knowledge_base_ids = (
        [current_app.knowledge_base_id] if current_app.knowledge_base_id else []
    )

    # Dispatch Celery background job for chat
    if job_type == "chat":
        logger.info("🚀 Dispatching chat job to Celery")
        celery_task = execute_chat_job_task.delay(
            job_id=job_record.id,
            data=data,
            callback_url=current_app.chat_callback_url,
            knowledge_base_ids=knowledge_base_ids,
        )
        JobService.update_celery_task_id(db, job_record.id, celery_task.id)
        logger.info(f"✅ Queued Celery task: {celery_task.id}")

    # Dispatch Celery background job for upload
    elif job_type == "upload":
        logger.info("📦 Upload job received, queued for processing...")
        # You could add a Celery task for upload processing here later.

    return JobResponse(
        job_id=job_record.id,
        status=job_record.status,
        trace_id=job_record.trace_id,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
):
    """Retrieve job status."""
    job = JobService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=job.id,
        status=job.status,
        trace_id=job.trace_id,
    )
