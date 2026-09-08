import logging
from typing import Any, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel
import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    PreviewRequest,
)
from app.services.document_upload_service import process_and_enqueue_upload
from app.services.minio_service import MinIOService, get_minio_service
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_redis_client():
    """Dependency provider for async Redis client."""
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


class TestRetrievalRequest(BaseModel):
    query: str
    kb_id: int
    top_k: int


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
    """Retrieve knowledge bases from KB MCP Server."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.list_kbs()
    items = (
        result
        if isinstance(result, list)
        else (
            result.get("knowledge_bases", result.get("data", []))
            if isinstance(result, dict)
            else []
        )
    )
    formatted = []
    for item in items:
        if isinstance(item, dict):
            item_copy = dict(item)
            item_copy["is_superuser"] = current_user.is_superuser
            formatted.append(item_copy)
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
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get knowledge base by ID."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.get_kb(kb_id=kb_id)
    result["is_superuser"] = True
    return result


@router.post("", response_model=dict)
async def create_knowledge_base(
    *,
    db: Session = Depends(get_db),
    kb_in: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Create new knowledge base."""
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
    """Update knowledge base."""
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
    """Delete knowledge base and all associated resources."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.delete_kb(kb_id=kb_id)
    return result


# Batch upload documents
@router.post(
    "/{kb_id}/documents/upload",
    status_code=status.HTTP_202_ACCEPTED,
    description="Upload documents to MinIO S3 and enqueue ingestion tasks",
)
async def upload_kb_documents(
    kb_id: int,
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    minio_service: MinIOService = Depends(get_minio_service),
    redis_client=Depends(get_redis_client),
):
    """
    Upload documents to MinIO S3 and enqueue background ingestion tasks
    to Redis.
    """
    upload_files: List[UploadFile] = []
    single_mode = False
    if file:
        upload_files.append(file)
        single_mode = True
    elif files:
        upload_files.extend(files)

    if not upload_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload",
        )

    return await process_and_enqueue_upload(
        kb_id=kb_id,
        files=upload_files,
        minio_service=minio_service,
        redis_client=redis_client,
        single_mode=single_mode,
    )


@router.post("/{kb_id}/documents/preview")
async def preview_kb_documents(
    kb_id: int,
    preview_request: PreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview multiple documents' chunks."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.preview_documents(
        kb_id=kb_id, preview_request=preview_request.model_dump()
    )
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
    """Get status of multiple processing tasks."""
    task_id_list = [id.strip() for id in task_ids.split(",") if id.strip()]
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
    current_user: User = Depends(get_current_user),
) -> Any:
    """Get document details by ID."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.get_document(
        kb_id=kb_id, doc_id=doc_id
    )
    return result


@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(
    *,
    db: Session = Depends(get_db),
    kb_id: int,
    doc_id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Delete a document by ID."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.delete_document(
        kb_id=kb_id, doc_id=doc_id
    )
    return result


@router.post("/{kb_id}/documents/process")
async def process_kb_documents(
    kb_id: int,
    upload_results: List[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process multiple documents asynchronously."""
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
    """Clean up expired temporary files."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.cleanup_temp_files()
    return result


@router.post("/test-retrieval")
async def test_retrieval(
    request: TestRetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Test retrieval quality for a given query against a knowledge base."""
    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.test_retrieval(
        kb_id=request.kb_id,
        query=request.query,
        top_k=request.top_k,
    )
    return result
