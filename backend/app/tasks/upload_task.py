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
            logger.warning(f"[Upload job] Job {job_id} not found")
            return

        # 🚀 Update to running
        JobService.update_status_to_running(db=db, job_id=job_id)

        # 🔍 Validate files before processing
        logger.info(
            f"[Upload job {job_id}] Validating {len(file_paths)} files"
        )
        for path in file_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")

            file_size = os.path.getsize(path)
            if file_size == 0:
                raise ValueError(f"File is empty: {path}")

            # Check file extension
            _, ext = os.path.splitext(path)
            supported = {".pdf", ".docx", ".md", ".txt"}
            if ext.lower() not in supported:
                raise ValueError(
                    f"Unsupported file type: {ext}. " f"Supported: {supported}"
                )

            logger.info(
                f"[Upload job {job_id}] Validated: {os.path.basename(path)} "
                f"({file_size} bytes, {ext})"
            )

        try:
            kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()

            # 🧠 Run async upload+process in MCP
            logger.info(
                f"[Upload job {job_id}] Starting upload and process "
                f"for KB {knowledge_base_id}"
            )

            result = asyncio.run(
                kb_mcp_endpoint_service.upload_and_process_documents(
                    kb_id=knowledge_base_id,
                    files=file_paths,  # use local paths
                )
            )

            logger.info(
                f"[Upload job {job_id}] Processing completed: {result}"
            )

        except Exception as e:
            logger.error(
                f"[Upload job {job_id}] Error processing upload: {e}",
                exc_info=True,
            )
            FileStorageService.mark_failed(file_paths)
            raise  # Re-raise so Celery marks it as failed

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
            logger.info(f"[Upload job {job_id}] Cleaned up: {file_paths}")
        except Exception as clean_err:
            logger.warning(
                f"[Upload job {job_id}] Cleanup failed: {clean_err}"
            )

        # 🔔 Callback if URL provided
        if callback_url:
            send_callback(callback_url, job, output=output)

        return result

    except Exception as e:
        # ❌ Failure: mark job failed
        error_msg = str(e)
        logger.exception(
            f"[Upload job {job_id}] Upload job failed: {error_msg}"
        )

        JobService.update_status_to_failed(
            db=db, job_id=job_id, output=error_msg
        )

        # ⚠️ Keep files for inspection/debugging
        failed_dir = "/mnt/uploads/failed"
        os.makedirs(failed_dir, exist_ok=True)

        for path in file_paths:
            if os.path.exists(path):
                new_path = os.path.join(failed_dir, os.path.basename(path))
                try:
                    os.rename(path, new_path)
                    logger.warning(
                        f"[Upload job {job_id} FAIL] Moved {path} → {new_path}"
                    )
                except Exception as move_err:
                    logger.error(
                        f"[Upload job {job_id}] Failed to move: {move_err}"
                    )

        return error_msg

    finally:
        db.close()
