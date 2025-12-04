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
    app_default_prompt: str,
    knowledge_base_ids: List[int] = [],
):
    """Background job executor for [chat job]s (non-streaming)."""
    job = JobService.get_job(db, job_id)
    if not job:
        return

    try:
        JobService.update_status_to_running(db, job_id)

        # prompt from app logic
        app_default_prompt = app_default_prompt or None
        job_payload_prompt = data.get("prompt") or None
        app_final_prompt = (
            job_payload_prompt if job_payload_prompt else app_default_prompt
        ) or None
        app_final_prompt = (
            "**IMPORTANT: Follow these additional rules strictly:**\n\n"
            + app_final_prompt
            if app_final_prompt
            else ""
        )
        # eol prompt from app logic

        prompt_service = PromptService(db=db)
        settings_service = SystemSettingsService(db=db)
        top_k = settings_service.get_top_k()

        chats = data.get("chats", [])
        callback_url = data.get("callback_url") or callback_url

        chat_history = []
        for msg in chats:
            role = msg["role"]
            if role in ["farmer", "extension_officer"]:
                role = "user"
            chat_history.append({"role": role, "content": msg["content"]})

        query = chat_history[-1].get("content") if chat_history else ""
        chat_history = chat_history[:-1] if chat_history else []

        # default rag prompt
        contextualize_prompt = prompt_service.get_full_contextualize_prompt()
        qa_prompt = prompt_service.get_full_qa_strict_prompt()

        # combined prompt
        final_prompt = qa_prompt + "\n\n" + app_final_prompt

        if (
            "context" not in final_prompt.lower()
            or "{context}" not in final_prompt.lower()
        ):
            final_prompt += "\n### Provided Context:\n{context}"

        logger.info("[Chat job] BEGIN final prompt: ==============")
        logger.info(f"[Chat job] final prompt: {final_prompt}")
        logger.info("[Chat job] EOL final prompt: ==============")

        state = {
            "query": query,
            "chat_history": chat_history,
            "contextualize_prompt_str": contextualize_prompt,
            "qa_prompt_str": final_prompt,
            "scope": {
                "knowledge_base_ids": knowledge_base_ids,
                "top_k": top_k,
            },
        }
        logger.info(f"[Chat job] {job_id} starting with state: {state}")

        result_state = await query_answering_workflow.ainvoke(state)
        logger.info(f"[Chat job] {job_id} completed workflow")

        answer = result_state.get("answer", "")
        error = result_state.get("error")

        citations = []
        for context in result_state.get("context", []):
            doc_metadata = context.metadata or {}
            citations.append(
                {
                    "document": doc_metadata.get("source")
                    or doc_metadata.get("title"),
                    "chunk": context.page_content,
                    "page": doc_metadata.get("page_label")
                    or doc_metadata.get("page"),
                }
            )

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
        logger.exception(f"[Chat job] execution failed: {e}")
        JobService.update_status_to_failed(db, job_id, output=str(e))
        await send_callback_async(callback_url, job, error=str(e))
        return str(e)
