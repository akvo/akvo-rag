from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
import logging

from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_user

from sqlalchemy import or_

from app.api.api_v1.extended.util.util_user import get_super_user_ids
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService

router = APIRouter()

logger = logging.getLogger(__name__)


# TODO :: DELETE BELOW
# class ExtendKnowledgeBaseResponse(KnowledgeBaseResponse):
#     is_superuser: Optional[bool] = False
# EOL DELETE


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
    # TODO :: DELETE prev code
    # super_user_ids = get_super_user_ids(db=db)
    # knowledge_bases = (
    #     db.query(KnowledgeBase, User.is_superuser)
    #     .join(User, KnowledgeBase.user_id == User.id, isouter=True)
    #     .filter(
    #         or_(
    #             KnowledgeBase.user_id == current_user.id,
    #             KnowledgeBase.user_id.in_(super_user_ids),
    #         )
    #     )
    #     .offset(skip)
    #     .limit(limit)
    #     .all()
    # )

    # results = []
    # for kb, is_superuser in knowledge_bases:
    #     kb_data = ExtendKnowledgeBaseResponse(
    #         id=kb.id,
    #         user_id=kb.user_id,
    #         name=kb.name,
    #         description=kb.description,
    #         created_at=kb.created_at,
    #         updated_at=kb.updated_at,
    #         documents=kb.documents or [],
    #         is_superuser=is_superuser,
    #     )
    #     results.append(kb_data)

    # return results
    # EOL TODO

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
    # TODO :: DELETE BELOW
    # from sqlalchemy.orm import joinedload

    # super_user_ids = get_super_user_ids(db=db)
    # kb_data = (
    #     db.query(KnowledgeBase, User.is_superuser)
    #     .join(User, KnowledgeBase.user_id == User.id, isouter=True)
    #     .options(
    #         joinedload(KnowledgeBase.documents).joinedload(
    #             Document.processing_tasks
    #         )
    #     )
    #     .filter(KnowledgeBase.id == kb_id)
    #     .filter(
    #         or_(
    #             KnowledgeBase.user_id == current_user.id,
    #             KnowledgeBase.user_id.in_(super_user_ids),
    #         )
    #     )
    #     .first()
    # )

    # kb, is_superuser = kb_data
    # if not kb:
    #     raise HTTPException(
    #         status_code=404,
    #         detail="Knowledge base not found"
    #     )

    # result = ExtendKnowledgeBaseResponse(
    #     id=kb.id,
    #     user_id=kb.user_id,
    #     name=kb.name,
    #     description=kb.description,
    #     created_at=kb.created_at,
    #     updated_at=kb.updated_at,
    #     documents=kb.documents or [],
    #     is_superuser=is_superuser,
    # )

    # return result
    # EOL DELETE

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
    # TODO :: DELETE BELOW
    # task_id_list = [int(id.strip()) for id in task_ids.split(",")]

    # kb = (
    #     db.query(KnowledgeBase)
    #     .filter(
    #         KnowledgeBase.id == kb_id, KnowledgeBase.user_id == current_user.id
    #     )
    #     .first()
    # )

    # if not kb:
    #     raise HTTPException(status_code=404, detail="Knowledge base not found")

    # tasks = (
    #     db.query(ProcessingTask)
    #     .options(selectinload(ProcessingTask.document_upload))
    #     .filter(
    #         ProcessingTask.id.in_(task_id_list),
    #         ProcessingTask.knowledge_base_id == kb_id,
    #     )
    #     .all()
    # )

    # return {
    #     task.id: {
    #         "document_id": task.document_id,
    #         "status": task.status,
    #         "error_message": task.error_message,
    #         "upload_id": task.document_upload_id,
    #         "file_name": (
    #             task.document_upload.file_name
    #             if task.document_upload
    #             else None
    #         ),
    #     }
    #     for task in tasks
    # }
    # EOL DELETE

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
    # TODO :: DELETE BELOW
    # super_user_ids = get_super_user_ids(db=db)
    # document = (
    #     db.query(Document)
    #     .join(KnowledgeBase)
    #     .filter(
    #         Document.id == doc_id,
    #         Document.knowledge_base_id == kb_id,
    #     )
    #     .filter(
    #         or_(
    #             KnowledgeBase.user_id == current_user.id,
    #             KnowledgeBase.user_id.in_(super_user_ids),
    #         )
    #     )
    #     .first()
    # )

    # if not document:
    #     raise HTTPException(status_code=404, detail="Document not found")

    # return document
    # EOL DELETE

    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    result = await kb_mcp_endpoint_service.get_document(
        kb_id=kb_id, doc_id=doc_id
    )
    return result
