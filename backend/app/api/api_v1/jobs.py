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
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail=f"Invalid JSON for field: {value}")

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job: Annotated[str, Form(..., description="Job type (chat, upload, etc.)")],
    prompt: Annotated[Optional[str], Form(..., description="Used for chat job-type")] = None,
    chats: Annotated[Optional[str], Form(..., description="Used for chat job-type (JSON list)")] = None,
    metadata: Annotated[Optional[str], Form(..., description="Used for upload job-type (JSON)")] = None,
    callback_params: Annotated[Optional[str], Form(...)] = None,
    trace_id: Annotated[Optional[str], Form(...)] = None,
    files: Annotated[Optional[List[UploadFile]], Form(...)] = None,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
):
    """Create a job (chat or upload) and dispatch background task if needed."""
    job_type = job.strip()

    chats_data = safe_json_parse(chats)
    metadata_data = safe_json_parse(metadata)
    callback_data = safe_json_parse(callback_params)

    data = {
        "prompt": prompt,
        "chats": chats_data,
        "metadata": metadata_data,
        "callback_params": callback_data,
        "trace_id": trace_id,
        "files": [f.filename for f in files] if files else [],
    }

    # ✅ Create DB job entry
    job = JobService.create_job(
        db=db, job_type=job_type, data=data, app_id=current_app.app_id
    )

    knowledge_base_ids = (
        [current_app.knowledge_base_id] if current_app.knowledge_base_id else []
    )

    if job_type == "chat":
        logger.info("🚀 Dispatching chat job to Celery")
        celery_task = execute_chat_job_task.delay(
            job_id=job.id,
            data=data,
            callback_url=current_app.chat_callback_url,
            knowledge_base_ids=knowledge_base_ids,
        )
        JobService.update_celery_task_id(db, job.id, celery_task.id)
        logger.info(f"✅ Queued Celery task: {celery_task.id}")

    return JobResponse(
        job_id=job.id,
        status=job.status,
        trace_id=job.trace_id,
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
