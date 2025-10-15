from typing import Optional, List
import secrets
from sqlalchemy.orm import Session

from app.models.app import App, AppStatus
from app.schemas.app import AppRegisterRequest

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
        knowledge_base_ids: Optional[List[int]] = None,
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

        app = App(
            app_id=app_id,
            client_id=client_id,
            app_name=register_data.app_name,
            domain=register_data.domain,
            default_chat_prompt=register_data.default_chat_prompt,
            chat_callback_url=register_data.chat_callback,
            upload_callback_url=register_data.upload_callback,
            access_token=access_token,
            callback_token=register_data.callback_token,
            scopes=scopes,
            status=AppStatus.active,
            knowledge_base_ids=knowledge_base_ids,
        )

        db.add(app)
        db.commit()
        db.refresh(app)

        return app, access_token

    @staticmethod
    def get_app_by_access_token(db: Session, access_token: str) -> Optional[App]:
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
    def rotate_callback_token(db: Session, app: App, new_callback_token: str) -> None:
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
