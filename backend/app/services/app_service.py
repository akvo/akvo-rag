from typing import Optional, List
import secrets
import hmac
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.orm import Session

from app.models.app import App, AppStatus
from app.schemas.app import AppRegisterRequest

# Initialize Argon2 hasher
ph = PasswordHasher()

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
    def generate_callback_token() -> str:
        """Generate a callback token."""
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_callback_token(token: str) -> str:
        """Hash callback token using Argon2."""
        return ph.hash(token)

    @staticmethod
    def verify_callback_token(token: str, hashed: str) -> bool:
        """Verify callback token using constant-time comparison (via Argon2)."""
        try:
            ph.verify(hashed, token)
            return True
        except VerifyMismatchError:
            return False

    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Constant-time string comparison."""
        return hmac.compare_digest(a, b)

    @staticmethod
    def create_app(
        db: Session, register_data: AppRegisterRequest, scopes: Optional[List[str]] = None
    ) -> tuple[App, str, str]:
        """
        Create a new app registration.
        Returns: (App model, access_token, callback_token)
        """
        app_id = AppService.generate_app_id()
        client_id = AppService.generate_client_id()
        access_token = AppService.generate_access_token()
        callback_token = AppService.generate_callback_token()
        callback_token_hash = AppService.hash_callback_token(callback_token)

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
            callback_token_hash=callback_token_hash,
            scopes=scopes,
            status=AppStatus.active,
        )

        db.add(app)
        db.commit()
        db.refresh(app)

        return app, access_token, callback_token

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
    def rotate_callback_token(db: Session, app: App) -> str:
        """Rotate the callback token for an app."""
        new_callback_token = AppService.generate_callback_token()
        app.callback_token_hash = AppService.hash_callback_token(new_callback_token)
        db.add(app)
        db.commit()
        db.refresh(app)
        return new_callback_token

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
