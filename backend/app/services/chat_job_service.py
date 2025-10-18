import logging

from typing import List
from sqlalchemy.orm import Session
from app.services.query_answering_workflow import query_answering_workflow
from app.services.job_service import JobService
from app.services.prompt_service import PromptService
from app.services.system_settings_service import SystemSettingsService
from app.utils import send_callback_async

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
        prompt = data.get("prompt") or None
        callback_url = data.get("callback_url") or callback_url

        chat_history = []
        for msg in chats:
            role = msg["role"]
            if role in ["farmer", "extension_officer"]:
                role = "user"
            chat_history.append({"role": role, "content": msg["content"]})

        query = chat_history[-1].get("content") if chat_history else ""
        chat_history = chat_history[:-1] if chat_history else []

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
        logger.info(f"Chat job {job_id} starting with state: {state}")

        result_state = await query_answering_workflow.ainvoke(state)
        logger.info(f"Chat job {job_id} completed workflow")

        answer = result_state.get("answer", "")
        error = result_state.get("error")

        citations = []
        for context in result_state.get("context", []):
            doc_metadata = context.metadata or {}
            citations.append({
                "document": doc_metadata.get("source") or doc_metadata.get("title"),
                "chunk": context.page_content,
                "page": doc_metadata.get("page_label") or doc_metadata.get("page"),
            })

        output = {"answer": answer, "citations": citations}

        if error:
            JobService.update_status_to_failed(db, job_id, output=str(error))
        else:
            JobService.update_status_to_completed(db, job_id, output=output)

        await send_callback_async(
            callback_url=callback_url,
            job=job,
            output=output if not error else None,
            error=str(error) if error else None,
        )

        return output

    except Exception as e:
        logger.exception(f"Chat job execution failed: {e}")
        JobService.update_status_to_failed(db, job_id, output=str(e))
        await send_callback_async(callback_url, job, error=str(e))
        return str(e)
