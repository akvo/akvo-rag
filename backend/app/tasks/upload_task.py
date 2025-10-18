import os
import json
import asyncio
import logging
from typing import List

from app.db.session import SessionLocal
from app.celery_app import celery_app
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService
from app.services.job_service import JobService
from app.services.file_storage_service import FileStorageService
from app.models.job import Job
from app.utils import send_callback

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.upload_full_process_task")
def upload_full_process_task(
    job_id: str,
    file_paths: List[str],
    callback_url: str,
    knowledge_base_id: int,
):
    """
    Celery task that uploads and processes documents via the MCP service.
    - file_paths: list of local file paths (already saved by FastAPI).
    """
    db = SessionLocal()
    try:
        # 🔍 Get job record
        job = JobService.get_job(db=db, job_id=job_id)
        if not job:
            logger.warning(f"Job {job_id} not found")
            return

        # 🚀 Update to running
        JobService.update_status_to_running(db=db, job_id=job_id)

        kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()

        # 🧠 Run async upload+process in MCP
        result = asyncio.run(
            kb_mcp_endpoint_service.upload_and_process_documents(
                kb_id=knowledge_base_id,
                file_paths=file_paths,  # ✅ use local paths now
            )
        )

        output = json.dumps(result)

        # ✅ Mark completed
        JobService.update_status_to_completed(
            db=db,
            job_id=job_id,
            output=output,
        )

        # 🧹 Cleanup only if all succeeded
        try:
            FileStorageService.cleanup_files(file_paths)
            logger.info(f"Cleaned up uploaded files: {file_paths}")
        except Exception as clean_err:
            logger.warning(f"Cleanup failed: {clean_err}")

        # 🔔 Callback if URL provided
        send_callback(callback_url, job, output=output)

        return result

    except Exception as e:
        # ❌ Failure: mark job failed
        JobService.update_status_to_failed(
            db=db, job_id=job_id, output=str(e)
        )

        logger.exception(f"Upload job {job_id} failed: {e}")

        # ⚠️ Keep files for inspection/debugging
        failed_dir = "/mnt/uploads/failed"
        os.makedirs(failed_dir, exist_ok=True)
        for path in file_paths:
            if os.path.exists(path):
                new_path = os.path.join(failed_dir, os.path.basename(path))
                os.rename(path, new_path)
                logger.warning(f"Moved failed file {path} → {new_path}")

        return str(e)

    finally:
        db.close()
