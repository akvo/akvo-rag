from typing import List, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=List[dict],
    description="List of all available knowledge bases from the MCP Server",
)
async def get_knowledge_bases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve knowledge bases from KB MCP Server

    Returns a list of knowledge base objects containing:
    - name: The name of the knowledge base
    - description: A description of what the knowledge base contains
    - id: Unique identifier
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    - documents: Array of associated documents (empty by default)
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.list_kbs()
    formatted = []
    for res in result:
        res["is_superuser"] = True
        formatted.append(res)
    return formatted


@router.get(
    "/{kb_id}",
    response_model=dict,
    description="Get knowledge base detail by kb id from MCP Server",
)
async def get_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get knowledge base by ID.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.get_kb(kb_id=kb_id)
    result["is_superuser"] = True
    return result


@router.get("/{kb_id}/documents/tasks")
async def get_processing_tasks(
    kb_id: int,
    task_ids: str = Query(
        ..., description="Comma-separated list of task IDs to check status for"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of multiple processing tasks.
    """
    task_id_list = [int(id.strip()) for id in task_ids.split(",")]
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.get_processing_tasks(
        kb_id=kb_id, task_ids=task_id_list
    )
    return result


@router.get("/{kb_id}/documents/{doc_id}")
async def get_document(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get document details by ID.
    - include knowledge base created by super user
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.get_document(
        kb_id=kb_id, doc_id=doc_id
    )
    return result
