import json
import httpx
import asyncio

from typing import List
from app.db.session import SessionLocal
from app.celery_app import celery_app
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService
from app.services.job_service import JobService
from app.models.job import Job

@celery_app.task(name="tasks.upload_full_process_task")
def upload_full_process_task(
    job_id: str,
    files: List[dict],
    callback_url: str,
    knowledge_base_id: int
):
    """
    Celery task that runs the upload and process documents for the app in one go
    Send multiple files in a single request.
    """
    db = SessionLocal()
    try:
        # current job
        job = JobService.get_job(db=db, job_id=job_id)
        if not job:
            return

        # running
        JobService.update_status_to_running(db=db, job_id=job_id)
        kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
        result = asyncio.run(
            kb_mcp_endpoint_service.upload_and_process_documents(
                kb_id=knowledge_base_id,
                files=files
            )
        )

        output = json.dumps(result)
        # completed
        JobService.update_status_to_completed(
            db=db, job_id=job_id, output=output
        )

        # Trigger callback
        if callback_url:
            async def callback(job: Job, output: str):
                payload = {
                    "job_id": job.id,
                    "status": "completed",
                    "output": output,
                    "error": None,
                    "callback_params": job.callback_params,
                }
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        await client.post(callback_url, json=payload)
                    logger.info(f"Callback sent to {callback_url}")
                except Exception as cb_err:
                    logger.warning(f"Callback failed: {cb_err}")
            asyncio.run(callback(job=job, output=output))
        return result

    except Exception as e:
        JobService.update_status_to_failed(
            db=db, job_id=job_id, output=str(e)
        )
        return str(e)

    finally:
        db.close()
