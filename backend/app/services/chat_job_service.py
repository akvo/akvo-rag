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
    db: Session,
    job_id: str,
    data: dict,
    callback_url: str,
    knowledge_base_ids: List[int] = []
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
        callback_url = data.get("callback_url") or callback_url
        callback_params = data.get("callback_params", {})
        trace_id = data.get("trace_id")

        chat_history = []
        for msg in chats:
            role = msg["role"]
            if role in ["farmer", "extension_officer"]:
                role = "user"
            chat_history.append({
                "role": role,
                "content": msg["content"]
            })

        query = chat_history[-1].get("content") if chat_history else ""
        chat_history = (
            chat_history[0:len(chat_history)-1] if chat_history else [])

        # Build initial graph state
        contextualize_prompt = prompt_service.get_full_contextualize_prompt()
        qa_prompt = prompt_service.get_full_qa_strict_prompt()

        state = {
            "query": query,
            "chat_history": chat_history,
            "contextualize_prompt_str": contextualize_prompt,
            "qa_prompt_str": prompt or qa_prompt,
            "scope": {
                "knowledge_base_ids": knowledge_base_ids,
                "top_k": top_k,
            },
        }
        logger.info(f"State: {state}")

        result_state = await query_answering_workflow.ainvoke(state)
        logger.info(f"Chat job {job_id} completed.")

        answer = result_state.get("answer", "")
        error = result_state.get("error")

        citations = []
        for context in result_state.get("context", []):
            doc_metadata = context.metadata or {}
            doc_content = context.page_content
            doc_context = {
                "document": doc_metadata.get("source") or doc_metadata.get("title"),
                "chunk": doc_content,
                "page": doc_metadata.get("page_label") or doc_metadata.get("page"),
            }
            citations.append(doc_context)

        output = {"answer": answer, "citations": citations}
        logger.info(f"Chat job {job_id} output: {output}")

        if error:
            JobService.update_status_to_failed(db, job_id, output=str(error))
        else:
            JobService.update_status_to_completed(db, job_id, output=output)

        # Trigger callback
        if callback_url:
            payload = {
                "job_id": job_id,
                "status": "failed" if error else "completed",
                "output": output,
                "error": error,
                "callback_params": callback_params,
            }
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(callback_url, json=payload)
                logger.info(f"Callback sent to {callback_url}")
            except Exception as cb_err:
                logger.warning(f"Callback failed: {cb_err}")
        return output

    except Exception as e:
        logger.exception(f"Chat job execution failed: {e}")
        JobService.update_status_to_failed(db, job_id, output=str(e))
        return str(e)
