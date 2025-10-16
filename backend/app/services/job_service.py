import json

from typing import Optional
from sqlalchemy.orm import Session
from app.models.job import Job


class JobService:
    @staticmethod
    def create_job(
        db: Session, job_type: str, data: dict, app_id: Optional[str] = None
    ) -> Job:
        job = Job(
            job_type=job_type,
            app_id=app_id,
            status="pending",
            input_data=json.dumps(data),
            callback_url=data.get("callback_url"),
            callback_params=json.dumps(data.get("callback_params", {})),
            trace_id=data.get("trace_id"),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def get_job(db: Session, job_id: str):
        return db.query(Job).filter(Job.id == job_id).first()

    # helper to update job status
    def _update_job_status(
        db: Session, job_id: str, status: str, output: str = None
    ):
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = status
            if output is not None:
                job.output = (
                    json.dumps(output) if isinstance(output, dict) else output
                )
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def update_status_to_running(db: Session, job_id: str):
        # use upodate_job_status to avoid code duplication
        return JobService._update_job_status(db, job_id, "running")

    @staticmethod
    def update_status_to_completed(
        db: Session, job_id: str, output: str = None
    ):
        return JobService._update_job_status(db, job_id, "completed", output)

    @staticmethod
    def update_status_to_failed(
        db: Session, job_id: str, output: str = None
    ):
        return JobService._update_job_status(db, job_id, "failed", output)
