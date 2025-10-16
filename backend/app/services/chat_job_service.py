import httpx
import logging

from typing import List
from sqlalchemy.orm import Session
from app.services.query_answering_workflow import query_answering_workflow
from app.services.job_service import JobService
from app.services.prompt_service import PromptService
from app.services.system_settings_service import SystemSettingsService

logger = logging.getLogger(__name__)


async def execute_chat_job(
    db: Session, job_id: str, data: dict, knowledge_base_ids: List[int] = []
):
    """Background job executor for chat jobs (non-streaming)."""
    job = JobService.get_job(db, job_id)
    if not job:
        return

    try:
        JobService.update_status_to_running(db, job_id)

        prompt_service = PromptService(db=db)
        settings_service = SystemSettingsService(db=db)
        top_k = settings_service.get_top_k()

        chats = data.get("chats", [])
        prompt = data.get("prompt") or None # will replace qa prompt if provided
        callback_url = data.get("callback_url")
        callback_params = data.get("callback_params", {})
        trace_id = data.get("trace_id")

        chat_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in chats
        ]

        # Build initial graph state
        contextualize_prompt = prompt_service.get_full_contextualize_prompt()
        qa_prompt = prompt_service.get_full_qa_strict_prompt()

        state = {
            "query": prompt, # where is the query?
            "chat_history": chat_history,
            "contextualize_prompt_str": contextualize_prompt,
            "qa_prompt_str": prompt or qa_prompt,
            "scope": {
                "knowledge_base_ids": knowledge_base_ids,
                "top_k": top_k,
            },
        }

        result_state = await query_answering_workflow.ainvoke(state)

        answer = result_state.get("answer", "")
        error = result_state.get("error")

        if error:
            JobService.update_status_to_failed(db, job_id, output=str(error))
        else:
            JobService.update_status_to_completed(db, job_id, output=answer)

        # Trigger callback
        if callback_url:
            payload = {
                "job_id": job_id,
                "trace_id": trace_id,
                "status": "failed" if error else "completed",
                "output": answer,
                "error": error,
                "callback_params": callback_params,
            }
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(callback_url, json=payload)
                logger.info(f"Callback sent to {callback_url}")
            except Exception as cb_err:
                logger.warning(f"Callback failed: {cb_err}")

    except Exception as e:
        logger.exception(f"Chat job execution failed: {e}")
        JobService.update_status_to_failed(db, job_id, output=str(e))
