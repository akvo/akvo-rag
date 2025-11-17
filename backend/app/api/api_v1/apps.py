from typing import Any, List, Optional, Union
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Response,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.app import App
from app.core.security import get_current_app
from app.services.app_service import AppService
from app.services.file_storage_service import FileStorageService
from app.schemas.app import (
    AppRegisterRequest,
    AppRegisterResponse,
    AppMeResponse,
    AppRotateRequest,
    AppRotateResponse,
    ErrorResponse,
    DocumentUploadItem,
    AppUpdateRequest,
    AppUpdateResponse,
    KnowledgeBaseItem,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdateRequest,
    PaginatedKnowledgeBaseResponse,
    PaginatedDocumentResponse,
    KnowledgeBaseDetailResponse,
)
from mcp_clients.kb_mcp_endpoint_service import KnowledgeBaseMCPEndpointService

router = APIRouter()


@router.post(
    "/register",
    response_model=AppRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "Conflict"},
    },
)
async def register_app(
    *,
    db: Session = Depends(get_db),
    register_data: AppRegisterRequest,
) -> Any:
    """
    Register a new app and issue credentials.

    - **app_name**: Name of the application
    - **domain**: Domain of the application
    - **default_chat_prompt**: Optional default chat prompt
    - **chat_callback**: HTTPS callback URL for chat operations
    - **upload_callback**: HTTPS callback URL for upload operations

    Returns app credentials including access_token and callback_token.
    """
    try:
        # register KB for the app
        kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
        kb_result = await kb_mcp_endpoint_service.create_kb(
            data={
                "name": register_data.app_name,
                "description": f"Knowledge base for {register_data.app_name}",
            }
        )
        knowledge_base_id = kb_result.get("id", None)

        # create app
        app, access_token = AppService.create_app(
            db=db,
            register_data=register_data,
            knowledge_base_id=knowledge_base_id,
        )

        knowledge_bases = [
            KnowledgeBaseItem(
                knowledge_base_id=kb.knowledge_base_id,
                is_default=kb.is_default,
            )
            for kb in app.knowledge_bases
        ]

        return AppRegisterResponse(
            app_id=app.app_id,
            client_id=app.client_id,
            access_token=access_token,
            scopes=app.scopes,
            knowledge_bases=knowledge_bases,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register app: {str(e)}",
        )


@router.get(
    "/me",
    response_model=AppMeResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Invalid or missing token",
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Inactive app",
        },
    },
)
def get_app_info(
    *,
    current_app: App = Depends(get_current_app),
) -> Any:
    """
    Validate token and return app metadata and scopes.

    Requires Bearer token authentication via Authorization header.
    Returns app information if token is valid and app is active.
    """
    knowledge_bases = [
        KnowledgeBaseItem(
            knowledge_base_id=kb.knowledge_base_id,
            is_default=kb.is_default,
        )
        for kb in current_app.knowledge_bases
    ]

    return AppMeResponse(
        app_id=current_app.app_id,
        app_name=current_app.app_name,
        domain=current_app.domain,
        default_chat_prompt=current_app.default_chat_prompt,
        chat_callback_url=current_app.chat_callback_url,
        upload_callback_url=current_app.upload_callback_url,
        scopes=current_app.scopes,
        status=current_app.status,
        knowledge_bases=knowledge_bases,
    )


@router.post(
    "/rotate",
    response_model=AppRotateResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Invalid or missing token",
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Inactive app",
        },
    },
)
def rotate_tokens(
    *,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
    rotate_request: AppRotateRequest,
) -> Any:
    """
    Rotate access token and/or callback token.

    - **rotate_access_token**: If true, rotate the access token
    - **rotate_callback_token**: If true, rotate the callback token
    - **new_callback_token**: Required if rotate_callback_token is true

    Old tokens remain valid until app is revoked or deactivated.
    """
    new_access_token = None

    if rotate_request.rotate_access_token:
        new_access_token = AppService.rotate_access_token(
            db=db, app=current_app
        )

    if rotate_request.rotate_callback_token:
        if not rotate_request.new_callback_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "new_callback_token is required when rotate_callback_token is true"  # noqa
                ),
            )
        AppService.rotate_callback_token(
            db=db,
            app=current_app,
            new_callback_token=rotate_request.new_callback_token,
        )

    if (
        not rotate_request.rotate_access_token
        and not rotate_request.rotate_callback_token
    ):
        message = "No tokens were rotated"
    elif (
        rotate_request.rotate_access_token
        and rotate_request.rotate_callback_token
    ):
        message = "Both tokens rotated successfully"
    elif rotate_request.rotate_access_token:
        message = "Access token rotated successfully"
    else:
        message = "Callback token rotated successfully"

    return AppRotateResponse(
        app_id=current_app.app_id,
        access_token=new_access_token,
        callback_token=None,
        message=message,
    )


@router.post(
    "/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Invalid or missing token",
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Inactive app",
        },
    },
)
def revoke_app(
    *,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
) -> Response:
    """
    Revoke the app immediately (idempotent).

    Sets app status to 'revoked'. After revocation, all endpoints
    requiring authentication will return 401.
    """
    AppService.revoke_app(db=db, app=current_app)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/upload")
async def upload_and_process_documents(
    *, files: List[UploadFile], current_app: App = Depends(get_current_app)
) -> Any:
    """
    Upload and process documents for the app in one go
    Send multiple files in a single request.
    """
    default_kb = next(
        (kb for kb in current_app.knowledge_bases if kb.is_default), None
    )
    if not default_kb:
        raise HTTPException(
            status_code=404, detail="Default KB not found for app"
        )

    # ✅ Save uploaded files locally before sending to Celery
    saved_file_paths = []
    if files:
        saved_file_paths = await FileStorageService.save_files(files)

    kb_mcp_endpoint_service = KnowledgeBaseMCPEndpointService()
    await kb_mcp_endpoint_service.upload_and_process_documents(
        kb_id=default_kb.knowledge_base_id, files=saved_file_paths
    )
    return {
        "message": "Document received and is being processed.",
        "file_count": len(files),
    }


@router.get(
    "/documents",
    response_model=Union[PaginatedDocumentResponse, List[DocumentUploadItem]],
)
async def get_documents(
    *,
    current_app: App = Depends(get_current_app),
    kb_id: Optional[int] = None,
    skip: Optional[int] = 0,
    limit: Optional[int] = 100,
    include_total: Optional[bool] = True,
    search: Optional[str] = None,
):
    """
    If kb_id is provided, proxy to MCP /documents list endpoint.
    If kb_id is NOT provided, return upload statuses for the default KB.
    """

    kb_mcp_service = KnowledgeBaseMCPEndpointService()

    # --- CASE 1: kb_id Explicitly Provided → List documents ---
    if kb_id is not None:
        return await kb_mcp_service.list_documents_by_kb_id(
            kb_id=kb_id,
            skip=skip,
            limit=limit,
            include_total=include_total,
            search=search,
        )

    # --- CASE 2: No kb_id → Use Default KB Upload Status ---
    default_kb = next(
        (kb for kb in current_app.knowledge_bases if kb.is_default),
        None,
    )

    if not default_kb:
        raise HTTPException(
            status_code=404,
            detail="Default KB not found for app",
        )

    return await kb_mcp_service.get_documents_upload(
        kb_id=default_kb.knowledge_base_id,
    )


@router.patch(
    "",
    response_model=AppUpdateResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Invalid or missing token",
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Inactive app",
        },
        404: {"model": ErrorResponse, "description": "App not found"},
    },
)
def update_app(
    *,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
    update_data: AppUpdateRequest,
) -> Any:
    """
    Partially update app metadata.

    Only provided fields will be updated. Access token and client_id
    will remain unchanged.

    Requires Bearer token authentication.
    """
    try:
        updated_app = AppService.update_app(
            db=db,
            app=current_app,
            update_data=update_data,
        )

        return AppUpdateResponse(
            app_id=updated_app.app_id,
            app_name=updated_app.app_name,
            domain=updated_app.domain,
            default_chat_prompt=updated_app.default_chat_prompt,
            chat_callback=updated_app.chat_callback_url,
            upload_callback=updated_app.upload_callback_url,
            callback_token=updated_app.callback_token,
            updated_at=updated_app.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update app: {str(e)}",
        )


@router.get(
    "/knowledge-bases",
    response_model=PaginatedKnowledgeBaseResponse,
)
async def list_knowledge_bases(
    *,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_app: App = Depends(get_current_app),
) -> Any:
    """
    Proxies KB listing request to MCP Knowledge Base service:
    GET /api/v1/knowledge-base?skip=&limit=&with_documents=&include_total=
    """
    try:
        kb_mcp = KnowledgeBaseMCPEndpointService()
        result = await kb_mcp.list_kbs(
            skip=skip,
            limit=limit,
            with_documents=False,
            include_total=True,
            search=search,
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch KB list: {str(e)}",
        )


@router.get(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBaseDetailResponse,
)
async def get_knowledge_base_details(
    kb_id: int,
    current_app: App = Depends(get_current_app),
):
    """
    Fetch a single Knowledge Base.
    Optionally include full document list from MCP.
    """

    # Ensure KB belongs to the current app
    kb_link = next(
        (
            kb
            for kb in current_app.knowledge_bases
            if kb.knowledge_base_id == kb_id
        ),
        None,
    )
    if not kb_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge Base not found for this app.",
        )

    mcp = KnowledgeBaseMCPEndpointService()

    try:
        kb_details = await mcp.get_kb(kb_id, with_documents=False)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch KB details: {e}",
        )

    # Merge local/link info (id, is_default) with MCP details
    merged = {
        "id": kb_id,
        "name": kb_details.get("name"),
        "description": kb_details.get("description"),
        "is_default": kb_link.is_default,
        "created_at": kb_details.get("created_at"),
        "updated_at": kb_details.get("updated_at"),
        "documents": [],
    }

    return merged


@router.post(
    "/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Inactive app",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_knowledge_base(
    *,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
    request_data: KnowledgeBaseCreateRequest,
) -> Any:
    """
    Create a new Knowledge Base for the current authenticated app.
    - If `is_default=True`,
        it will automatically unset the existing default KB.
    """
    try:
        app_kb = await AppService.create_knowledge_base(
            db=db,
            app=current_app,
            name=request_data.name,
            description=request_data.description,
            is_default=request_data.is_default,
        )

        return KnowledgeBaseResponse(
            id=app_kb.id,
            knowledge_base_id=app_kb.knowledge_base_id,
            name=request_data.name,
            description=request_data.description,
            is_default=app_kb.is_default,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create KB: {str(e)}",
        )


@router.patch(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_200_OK,
    responses={
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Inactive app",
        },
        404: {
            "model": ErrorResponse,
            "description": "Knowledge base not found",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_knowledge_base(
    *,
    kb_id: int,
    db: Session = Depends(get_db),
    request_data: KnowledgeBaseUpdateRequest,
    current_app: App = Depends(get_current_app),
) -> Any:
    """
    Set a specific KB as the default for the authenticated app.
    - Automatically unsets the previous default KB.
    - Returns the updated KB record.
    """
    try:
        update_result = await AppService.update_knowledge_base(
            db=db,
            app=current_app,
            kb_id=kb_id,
            name=request_data.name,
            description=request_data.description,
            is_default=request_data.is_default,
        )
        return update_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update KB: {str(e)}",
        )


@router.delete(
    "/knowledge-bases/{kb_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Inactive app or cannot delete KB",
        },
        404: {
            "model": ErrorResponse,
            "description": "Knowledge base not found",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_knowledge_base(
    *,
    kb_id: int,
    db: Session = Depends(get_db),
    current_app: App = Depends(get_current_app),
) -> Response:
    """
    Delete a knowledge base for the authenticated app.
    - Prevents deletion if:
        - It's the last remaining KB, OR
        - It's the default KB (unless another default exists)
    """
    # Find the KB under this app
    app_kb = next(
        (
            kb
            for kb in current_app.knowledge_bases
            if kb.knowledge_base_id == kb_id
        ),
        None,
    )
    if not app_kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found for this app.",
        )

    # Prevent deleting last KB
    if len(current_app.knowledge_bases) <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete the last knowledge base for this app.",
        )

    # Prevent deleting the default KB
    if app_kb.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete the default knowledge base. Set another KB as default first.",  # noqa
        )

    try:
        # Delete from MCP service
        kb_mcp_service = KnowledgeBaseMCPEndpointService()
        await kb_mcp_service.delete_kb(kb_id=kb_id)

        # Delete link from app_knowledge_bases
        AppService.delete_knowledge_base(db=db, app=current_app, kb_id=kb_id)

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete KB: {str(e)}",
        )
