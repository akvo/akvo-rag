from sqlalchemy import Column, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.dialects.mysql import JSON
import enum

from app.models.base import Base, TimestampMixin


class AppStatus(str, enum.Enum):
    active = "active"
    revoked = "revoked"
    suspended = "suspended"


class App(Base, TimestampMixin):
    __tablename__ = "apps"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(64), unique=True, index=True, nullable=False)
    client_id = Column(String(64), unique=True, index=True, nullable=False)
    app_name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False)
    default_chat_prompt = Column(Text, nullable=True)
    chat_callback_url = Column(String(512), nullable=False)
    upload_callback_url = Column(String(512), nullable=False)

    # Token management
    access_token = Column(String(128), unique=True, index=True, nullable=False)
    callback_token = Column(String(255), nullable=True)

    # Authorization
    scopes = Column(JSON, nullable=False)  # Store as JSON array
    status = Column(SQLEnum(AppStatus), default=AppStatus.active, nullable=False)

    # list of KB IDs
    knowledge_base_id = Column(Integer, nullable=True)