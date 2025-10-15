from typing import Any, List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Response,
    UploadFile
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.app import App
from app.core.security import get_current_app
from app.services.app_service import AppService
from app.schemas.app import (
    AppRegisterRequest,
    AppRegisterResponse,
    AppMeResponse,
    AppRotateRequest,
    AppRotateResponse,
    ErrorResponse,
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
        kb_result = await KnowledgeBaseMCPEndpointService.create_kb(
            data={
                "name": register_data.app_name,
                "description": f"Knowledge base for {register_data.app_name}"
            }
        )
        knowledge_base_id = kb_result.get('id', None)

        # create app
        app, access_token = AppService.create_app(
            db=db,
            register_data=register_data,
            knowledge_base_id=knowledge_base_id
        )

        return AppRegisterResponse(
            app_id=app.app_id,
            client_id=app.client_id,
            access_token=access_token,
            scopes=app.scopes,
            knowledge_base_id=app.knowledge_base_id,
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
        403: {"model": ErrorResponse, "description": "Forbidden - Inactive app"},
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
    return AppMeResponse(
        app_id=current_app.app_id,
        app_name=current_app.app_name,
        domain=current_app.domain,
        default_chat_prompt=current_app.default_chat_prompt,
        chat_callback_url=current_app.chat_callback_url,
        upload_callback_url=current_app.upload_callback_url,
        scopes=current_app.scopes,
        status=current_app.status,
        knowledge_base_id=current_app.knowledge_base_id,
    )


@router.post(
    "/rotate",
    response_model=AppRotateResponse,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized - Invalid or missing token",
        },
        403: {"model": ErrorResponse, "description": "Forbidden - Inactive app"},
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
        new_access_token = AppService.rotate_access_token(db=db, app=current_app)

    if rotate_request.rotate_callback_token:
        if not rotate_request.new_callback_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="new_callback_token is required when rotate_callback_token is true",
            )
        AppService.rotate_callback_token(db=db, app=current_app, new_callback_token=rotate_request.new_callback_token)

    if not rotate_request.rotate_access_token and not rotate_request.rotate_callback_token:
        message = "No tokens were rotated"
    elif rotate_request.rotate_access_token and rotate_request.rotate_callback_token:
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
        403: {"model": ErrorResponse, "description": "Forbidden - Inactive app"},
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
    *,
    files: List[UploadFile],
    current_app: App = Depends(get_current_app)
) -> Any:
    """
    Upload and process documents for the app in one go
    Send multiple files in a single request.
    """
    await KnowledgeBaseMCPEndpointService.upload_and_process_documents(
        kb_id=current_app.knowledge_base_id,
        files=files
    )
    return {
        "message": "Document received and is being processed.",
        "file_count": len(files),
    }
