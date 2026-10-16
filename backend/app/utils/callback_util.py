import asyncio
import json
import logging
from typing import Any, Optional
import httpx

from app.models.job import Job

logger = logging.getLogger(__name__)


async def send_callback_async(
    callback_url: str,
    job: Job,
    output: Optional[Any] = None,
    error: Optional[str] = None,
):
    """
    Asynchronous callback sender.
    Posts job results (success/failure) to an external callback endpoint.
    """
    if not callback_url:
        logger.warning("⚠️ Callback URL not provided, skipping callback.")
        return

    # Parse callback_params if stored as a string in DB
    callback_params = job.callback_params
    if isinstance(callback_params, str):
        try:
            callback_params = json.loads(callback_params)
        except Exception:
            pass
    if not isinstance(callback_params, dict):
        callback_params = {}

    payload = {
        "job_id": job.id,
        "job": job.job_type or "chat",
        "status": "failed" if error else "completed",
        "output": output,
        "error": error,
        "callback_params": callback_params,
        "trace_id": job.trace_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(callback_url, json=payload)
            response.raise_for_status()
        logger.info(f"✅ Callback sent successfully to {callback_url}")
    except httpx.RequestError as e:
        logger.warning(f"❌ Callback request error for {callback_url}: {e}")
    except httpx.HTTPStatusError as e:
        logger.warning(
            f"❌ Callback failed [{e.response.status_code}] for "
            f"{callback_url}: {e.response.text}"
        )


def send_callback(
    callback_url: str,
    job: Job,
    output: Optional[Any] = None,
    error: Optional[str] = None,
):
    """
    Wrapper to safely run the async callback from sync Celery tasks.
    """
    try:
        asyncio.run(send_callback_async(callback_url, job, output, error))
    except RuntimeError:
        # If there's already an event loop (nested async tasks)
        loop = asyncio.get_event_loop()
        loop.create_task(send_callback_async(callback_url, job, output, error))
