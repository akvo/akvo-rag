import hashlib
from typing import List, Any, Dict
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    BackgroundTasks,
    Query,
)
from sqlalchemy.orm import Session
from langchain_chroma import Chroma
from sqlalchemy import text
import logging
from datetime import datetime, timedelta
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
import time
import asyncio

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user

from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    PreviewRequest,
)
from app.core.config import settings
from app.core.minio import get_minio_client
from minio.error import MinioException
from app.services.vector_store import VectorStoreFactory
from app.services.embedding.embedding_factory import EmbeddingsFactory
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


# TODO :: REPLACE with route from extend_knowledge_base.py
# @router.get("", response_model=List[KnowledgeBaseResponse])
# def get_knowledge_bases(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
#     skip: int = 0,
#     limit: int = 100,
# ) -> Any:
#     """
#     Retrieve knowledge bases.
#     """
#     knowledge_bases = (
#         db.query(KnowledgeBase)
#         .filter(KnowledgeBase.user_id == current_user.id)
#         .offset(skip)
#         .limit(limit)
#         .all()
#     )
#     return knowledge_bases
# EOL TODO


# TODO :: REPLACE with route from extend_knowledge_base.py
# @router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
# def get_knowledge_base(
#     *,
#     db: Session = Depends(get_db),
#     kb_id: int,
#     current_user: User = Depends(get_current_user),
# ) -> Any:
#     """
#     Get knowledge base by ID.
#     """
#     from sqlalchemy.orm import joinedload

#     kb = (
#         db.query(KnowledgeBase)
#         .options(
#             joinedload(KnowledgeBase.documents).joinedload(
#                 Document.processing_tasks
#             )
#         )
#         .filter(
#             KnowledgeBase.id == kb_id, KnowledgeBase.user_id == current_user.id
#         )
#         .first()
#     )

#     if not kb:
#         raise HTTPException(status_code=404, detail="Knowledge base not found")

#     return kb
# EOL TODO


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
    Upload multiple documents to MinIO.
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


# TODO :: REPLACE with route from extend_knowledge_base.py
# @router.get("/{kb_id}/documents/tasks")
# async def get_processing_tasks(
#     kb_id: int,
#     task_ids: str = Query(
#         ..., description="Comma-separated list of task IDs to check status for"
#     ),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     Get status of multiple processing tasks.
#     """
#     task_id_list = [int(id.strip()) for id in task_ids.split(",")]

#     kb = (
#         db.query(KnowledgeBase)
#         .filter(
#             KnowledgeBase.id == kb_id, KnowledgeBase.user_id == current_user.id
#         )
#         .first()
#     )

#     if not kb:
#         raise HTTPException(status_code=404, detail="Knowledge base not found")

#     tasks = (
#         db.query(ProcessingTask)
#         .options(selectinload(ProcessingTask.document_upload))
#         .filter(
#             ProcessingTask.id.in_(task_id_list),
#             ProcessingTask.knowledge_base_id == kb_id,
#         )
#         .all()
#     )

#     return {
#         task.id: {
#             "document_id": task.document_id,
#             "status": task.status,
#             "error_message": task.error_message,
#             "upload_id": task.document_upload_id,
#             "file_name": (
#                 task.document_upload.file_name
#                 if task.document_upload
#                 else None
#             ),
#         }
#         for task in tasks
#     }
# EOL REPLACE


# TODO :: REPLACE with route from extend_knowledge_base.py
# @router.get("/{kb_id}/documents/{doc_id}", response_model=DocumentResponse)
# async def get_document(
#     *,
#     db: Session = Depends(get_db),
#     kb_id: int,
#     doc_id: int,
#     current_user: User = Depends(get_current_user),
# ) -> Any:
#     """
#     Get document details by ID.
#     """
#     document = (
#         db.query(Document)
#         .join(KnowledgeBase)
#         .filter(
#             Document.id == doc_id,
#             Document.knowledge_base_id == kb_id,
#             KnowledgeBase.user_id == current_user.id,
#         )
#         .first()
#     )

#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")

#     return document
# EOL REPLACE


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
