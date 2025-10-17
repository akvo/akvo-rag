import asyncio

from typing import List
from app.celery_app import celery_app
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService

@celery_app.task(name="tasks.upload_full_process_task")
def upload_full_process_task(files: List[dict], knowledge_base_id: int):
    """
    Celery task that runs the upload and process documents for the app in one go
    Send multiple files in a single request.
    """
    try:
        kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
        result = asyncio.run(
            kb_mcp_endpoint_service.upload_and_process_documents(
                kb_id=knowledge_base_id,
                files=files
            )
        )
        return result
    except Exception as e:
        return str(e)

