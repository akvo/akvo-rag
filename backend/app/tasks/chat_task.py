import asyncio

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.chat_job_service import execute_chat_job

@celery_app.task(name="tasks.execute_chat_job_task")
def execute_chat_job_task(
    job_id: str,
    data: dict,
    callback_url: str,
    knowledge_base_ids: list[int] = [],
):
    """
    Celery task that runs the async chat workflow in a separate process.
    """
    db = SessionLocal()
    try:
        result = asyncio.run(
            execute_chat_job(
                db=db,
                job_id=job_id,
                data=data,
                callback_url=callback_url,
                knowledge_base_ids=knowledge_base_ids
            )
        )
        return result
    except Exception as e:
        return str(e)
    finally:
        db.close()
