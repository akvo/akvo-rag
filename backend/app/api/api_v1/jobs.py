from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import JobCreate, JobResponse
from app.services.job_service import JobService
from app.models.app import App
from app.core.security import get_current_app
from app.tasks.chat_task import execute_chat_job_task

router = APIRouter()


# only accessed by apps
@router.post("/jobs", response_model=JobResponse)
async def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
):
    """Create a job and run it in background."""
    job = JobService.create_job(
        db=db, job_type="chat", data=data.dict(), app_id=current_app.app_id
    )

    knowledge_base_ids = (
        [current_app.knowledge_base_id]
        if current_app.knowledge_base_id
        else []
    )
    if data.job == "chat":
        # Launch chat workflow
        celery_task = execute_chat_job_task.delay(
            job.id, data.dict(), knowledge_base_ids
        )
        JobService.update_celery_task_id(db, job.id, celery_task.id)
    else:
        # In the future: other job types (summarize, embed, etc.)
        pass

    return JobResponse(
        job_id=job.id,
        status=job.status,
        trace_id=job.trace_id
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
):
    """
    Retrieve a job status (only chat jobs visible, not upload jobs).
    """
    job = JobService.get_job(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=job.id,
        status=job.status,
        trace_id=job.trace_id,
    )
