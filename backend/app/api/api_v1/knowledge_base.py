from typing import List, Any
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    BackgroundTasks,
)
from sqlalchemy.orm import Session
import logging
from pydantic import BaseModel

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user

from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    PreviewRequest,
)
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService

router = APIRouter()

logger = logging.getLogger(__name__)


class TestRetrievalRequest(BaseModel):
    query: str
    kb_id: int
    top_k: int


@router.post("", response_model=dict)
async def create_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_in: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create new knowledge base.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.create_kb(data=kb_in.model_dump())
    return result


@router.put("/{kb_id}")
async def update_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    kb_in: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update knowledge base.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.update_kb(
        kb_id=kb_id, data=kb_in.model_dump()
    )
    return result


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete knowledge base and all associated resources.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.delete_kb(kb_id=kb_id)
    return result


# Batch upload documents
@router.post("/{kb_id}/documents/upload")
async def upload_kb_documents(
    kb_id: int,
    files: List[UploadFile],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload multiple documents to MCP.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.upload_documents(
        kb_id=kb_id, files=files
    )
    return result


@router.post("/{kb_id}/documents/preview")
async def preview_kb_documents(
    kb_id: int,
    preview_request: PreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview multiple documents' chunks.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.preview_documents(
        kb_id=kb_id, preview_request=preview_request.model_dump()
    )
    return result


@router.post("/{kb_id}/documents/process")
async def process_kb_documents(
    kb_id: int,
    upload_results: List[dict],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process multiple documents asynchronously.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.process_documents(
        kb_id=kb_id, upload_results=upload_results
    )
    return result


@router.post("/cleanup")
async def cleanup_temp_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Clean up expired temporary files.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.cleanup_temp_files()
    return result


@router.post("/test-retrieval")
async def test_retrieval(
    request: TestRetrievalRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Test retrieval quality for a given query against a knowledge base.
    """
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.test_retrieval(
        kb_id=request.kb_id,
        query=request.query,
        top_k=request.top_k,
    )
    return result
