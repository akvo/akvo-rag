from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
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
    status = Column(
        SQLEnum(AppStatus), default=AppStatus.active, nullable=False
    )

    # Relationships
    knowledge_bases = relationship(
        "AppKnowledgeBase",
        back_populates="app",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AppKnowledgeBase(Base, TimestampMixin):
    __tablename__ = "app_knowledge_bases"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(
        Integer, ForeignKey("apps.id", ondelete="CASCADE"), nullable=False
    )
    knowledge_base_id = Column(Integer, nullable=False)  # External MCP KB ID
    is_default = Column(Boolean, default=False, nullable=False)

    # Relationship back to App
    app = relationship("App", back_populates="knowledge_bases")
