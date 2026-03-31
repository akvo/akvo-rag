from datetime import datetime, timedelta
from pathlib import Path
import secrets
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken


# FastMail configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USER,
    MAIL_PASSWORD=settings.SMTP_PASS,
    MAIL_FROM=settings.SMTP_USER,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_FROM_NAME=settings.PROJECT_NAME,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=settings.SMTP_USE_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / 'templates' / 'email'
)

fm = FastMail(conf)


class EmailService:
    @staticmethod
    def _get_template_env():
        """Get Jinja2 template environment"""
        template_path = Path(__file__).parent.parent / 'templates' / 'email'
        template_path.mkdir(parents=True, exist_ok=True)
        return Environment(loader=FileSystemLoader(str(template_path)))

    @staticmethod
    async def send_password_reset_email(
        email: str,
        reset_token: str,
        user_name: str
    ) -> bool:
        """Send password reset email"""
        try:
            # Determine protocol based on domain
            protocol = "https" if settings.WEBDOMAIN != "127.0.0.1.nip.io" else "http"
            reset_url = f"{protocol}://{settings.WEBDOMAIN}/reset-password?token={reset_token}"

            env = EmailService._get_template_env()
            template = env.get_template('reset_password.html')

            html_content = template.render(
                webdomain=f"{protocol}://{settings.WEBDOMAIN}",
                logo=f"{protocol}://{settings.WEBDOMAIN}/logo.png",
                site_name=settings.PROJECT_NAME,
                button_url=reset_url,
                button_text="Reset Password",
                subject="Reset Password",
                user_name=user_name,
                body="""You recently requested a password reset.
                Please disregard this email if it wasn't you and make sure
                you can still login to your account.
                If it was you, please click the following button to
                reset your password."""
            )

            message = MessageSchema(
                subject=f"{settings.PROJECT_NAME} - Reset Password",
                recipients=[email],
                body=html_content,
                subtype="html"
            )

            await fm.send_message(message)
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False

    @staticmethod
    def generate_reset_token(db: Session, user: User) -> str:
        """Generate a new password reset token"""
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )

        # Create token record
        reset_token = PasswordResetToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at
        )

        db.add(reset_token)
        db.commit()

        return token

    @staticmethod
    def verify_reset_token(db: Session, token: str):
        """Verify reset token and return user if valid"""
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token
        ).first()

        if not reset_token:
            return None

        # Check if token is expired
        if reset_token.expires_at < datetime.utcnow():
            return None

        # Check if token was already used
        if reset_token.used_at is not None:
            return None

        return reset_token.user

    @staticmethod
    def mark_token_as_used(db: Session, token: str) -> bool:
        """Mark token as used"""
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token
        ).first()

        if reset_token:
            reset_token.used_at = datetime.utcnow()
            db.commit()
            return True
        return False
