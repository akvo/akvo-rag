import logging
from typing import Any, List, Optional
from sqlalchemy.orm import Session

from app.services.job_service import JobService
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService

logger = logging.getLogger(__name__)


async def execute_upload_job(
    db: Session,
    job_id: str,
    kb_id: int,
    files: List[Any],
    callback_url: Optional[str] = None,
):
    """Background job executor for document upload jobs."""
    try:
        JobService.update_status_to_running(db, job_id)
        kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
        upload_results = (
            await kb_mcp_endpoint_service.upload_and_process_documents(
                kb_id=kb_id,
                files=files or [],
            )
        )
        output = {
            "kb_id": kb_id,
            "documents": upload_results,
            "file_count": len(upload_results),
        }
        JobService.update_status_to_completed(db, job_id, output=output)
        if callback_url:
            from app.utils.callback_util import send_callback_async

            job_obj = JobService.get_job(db, job_id)
            if job_obj:
                await send_callback_async(
                    callback_url=callback_url,
                    job=job_obj,
                    output=output,
                )
    except Exception as exc:
        logger.exception("Upload job %s failed: %s", job_id, exc)
        JobService.update_status_to_failed(db, job_id, output=str(exc))
        if callback_url:
            from app.utils.callback_util import send_callback_async

            job_obj = JobService.get_job(db, job_id)
            if job_obj:
                await send_callback_async(
                    callback_url=callback_url,
                    job=job_obj,
                    error=str(exc),
                )
    finally:
        db.close()
