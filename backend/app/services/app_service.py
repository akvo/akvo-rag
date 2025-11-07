from typing import Optional, List
import secrets
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.app import App, AppStatus, AppKnowledgeBase
from app.schemas.app import (
    AppRegisterRequest,
    AppUpdateRequest,
    KnowledgeBaseResponse,
)
from mcp_clients.kb_mcp_endpoint_service import (
    KnowledgeBaseMCPEndpointService,
)

# Default scopes for new apps
DEFAULT_SCOPES = ["jobs.write", "kb.read", "kb.write", "apps.read"]


class AppService:
    @staticmethod
    def generate_app_id() -> str:
        """Generate a unique app ID with 'app_' prefix."""
        return f"app_{secrets.token_urlsafe(16)}"

    @staticmethod
    def generate_client_id() -> str:
        """Generate a unique client ID with 'ac_' prefix."""
        return f"ac_{secrets.token_urlsafe(16)}"

    @staticmethod
    def generate_access_token() -> str:
        """Generate an opaque access token."""
        return f"tok_{secrets.token_urlsafe(48)}"

    @staticmethod
    def create_app(
        db: Session,
        register_data: AppRegisterRequest,
        scopes: Optional[List[str]] = None,
        knowledge_base_id: Optional[int] = None,
    ) -> tuple[App, str]:
        """
        Create a new app registration.
        Returns: (App model, access_token)
        """
        app_id = AppService.generate_app_id()
        client_id = AppService.generate_client_id()
        access_token = AppService.generate_access_token()

        if scopes is None:
            scopes = DEFAULT_SCOPES

        # create app
        app = App(
            app_id=app_id,
            client_id=client_id,
            app_name=register_data.app_name,
            domain=register_data.domain,
            default_chat_prompt=register_data.default_chat_prompt,
            chat_callback_url=register_data.chat_callback,
            upload_callback_url=register_data.upload_callback,
            access_token=access_token,
            callback_token=register_data.callback_token or None,
            scopes=scopes,
            status=AppStatus.active,
        )

        # Set the default knowledge base
        if knowledge_base_id is not None:
            app_kb = AppKnowledgeBase(
                knowledge_base_id=knowledge_base_id,
                is_default=True,
            )
            app.knowledge_bases.append(app_kb)

        db.add(app)
        db.commit()
        db.refresh(app)

        return app, access_token

    @staticmethod
    def update_app(
        db: Session,
        app: App,
        update_data: AppUpdateRequest,
    ) -> App:
        """
        Partially update app fields without resetting identifiers or tokens."""
        updated = False
        data = update_data.dict(exclude_unset=True)

        for field, value in data.items():
            if value is not None:
                if field == "chat_callback":
                    app.chat_callback_url = value
                elif field == "upload_callback":
                    app.upload_callback_url = value
                elif hasattr(app, field):
                    setattr(app, field, value)
                updated = True

        if updated:
            db.add(app)
            db.commit()
            db.refresh(app)
        return app

    @staticmethod
    def get_app_by_access_token(
        db: Session, access_token: str
    ) -> Optional[App]:
        """Get app by access token."""
        return db.query(App).filter(App.access_token == access_token).first()

    @staticmethod
    def get_app_by_app_id(db: Session, app_id: str) -> Optional[App]:
        """Get app by app_id."""
        return db.query(App).filter(App.app_id == app_id).first()

    @staticmethod
    def rotate_access_token(db: Session, app: App) -> str:
        """Rotate the access token for an app."""
        new_access_token = AppService.generate_access_token()
        app.access_token = new_access_token
        db.add(app)
        db.commit()
        db.refresh(app)
        return new_access_token

    @staticmethod
    def rotate_callback_token(
        db: Session, app: App, new_callback_token: str
    ) -> None:
        """Rotate the callback token for an app."""
        app.callback_token = new_callback_token
        db.add(app)
        db.commit()
        db.refresh(app)

    @staticmethod
    def revoke_app(db: Session, app: App) -> None:
        """Revoke an app (idempotent)."""
        app.status = AppStatus.revoked
        db.add(app)
        db.commit()

    @staticmethod
    def is_app_active(app: App) -> bool:
        """Check if app status is active."""
        return app.status == AppStatus.active

    @staticmethod
    def _unset_existing_default(db: Session, app: App) -> None:
        """
        Helper: Unset the current default KB for the given app.
        This is a small helper to keep logic consistent across operations.
        """
        db.query(AppKnowledgeBase).filter(
            AppKnowledgeBase.app_id == app.id,
            AppKnowledgeBase.is_default == 1,
        ).update({"is_default": 0})
        db.flush()

    @staticmethod
    async def create_knowledge_base(
        db: Session,
        app: App,
        name: str,
        description: str | None = None,
        is_default: bool = False,
    ) -> AppKnowledgeBase:
        """
        Create a new KB for the given app and optionally set it as default.
        """
        # Create KB in MCP service
        kb_mcp_service = KnowledgeBaseMCPEndpointService()
        kb_result = await kb_mcp_service.create_kb(
            data={
                "name": name,
                "description": description or f"KB for {app.app_name}",
            }
        )

        knowledge_base_id = kb_result.get("id")
        if not knowledge_base_id:
            raise HTTPException(
                status_code=500, detail="Failed to create KB from MCP service"
            )

        # If new KB is default → unset existing default
        if is_default:
            AppService._unset_existing_default(db, app)

        # Create record
        app_kb = AppKnowledgeBase(
            app_id=app.id,
            knowledge_base_id=knowledge_base_id,
            is_default=is_default,
        )
        db.add(app_kb)
        db.commit()
        db.refresh(app_kb)
        return app_kb

    @staticmethod
    async def update_knowledge_base(
        db: Session,
        app: App,
        kb_id: int,
        name: str | None = None,
        description: str | None = None,
        is_default: bool | None = None,
    ) -> KnowledgeBaseResponse:
        """
        Update knowledge base detail
        """
        app_kb = (
            db.query(AppKnowledgeBase)
            .filter_by(knowledge_base_id=kb_id, app_id=app.id)
            .first()
        )
        if not app_kb:
            raise HTTPException(
                status_code=404, detail="Knowledge base not found for this app"
            )

        kb_mcp_service = KnowledgeBaseMCPEndpointService()

        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description

        kb_result = await kb_mcp_service.update_kb(
            kb_id=kb_id,
            data=data,
        )
        if not kb_result:
            raise HTTPException(
                status_code=500, detail="Failed to update KB from MCP service"
            )

        if is_default is not None:
            # Update  default
            app_kb.is_default = is_default

        db.commit()
        db.refresh(app_kb)
        return KnowledgeBaseResponse(
            id=app_kb.id,
            knowledge_base_id=app_kb.knowledge_base_id,
            name=kb_result.get("name"),
            description=kb_result.get("description"),
            is_default=app_kb.is_default,
        )

    @staticmethod
    def delete_knowledge_base(db: Session, app: App, kb_id: int):
        """
        Remove KB link for this app (not the MCP record itself).
        """
        app_kb = (
            db.query(AppKnowledgeBase)
            .filter(
                AppKnowledgeBase.app_id == app.id,
                AppKnowledgeBase.knowledge_base_id == kb_id,
            )
            .first()
        )
        if not app_kb:
            raise HTTPException(
                status_code=404,
                detail="Knowledge base not found for this app.",
            )

        db.delete(app_kb)
        db.commit()
