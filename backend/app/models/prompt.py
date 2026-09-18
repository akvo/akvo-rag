from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# This Enum remains the single source of truth for prompt names
class PromptNameEnum(str, Enum):
    contextualize_q_system_prompt = "contextualize_q_system_prompt"
    qa_flexible_prompt = "qa_flexible_prompt"
    qa_strict_prompt = "qa_strict_prompt"


class PromptDefinition(Base, TimestampMixin):
    """
    Defines the logical prompt types (e.g., "qa_flexible_prompt").
    This table stores the fixed, unique names of your prompts.
    """

    __tablename__ = "prompt_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    versions: Mapped[List["PromptVersion"]] = relationship(
        "PromptVersion",
        back_populates="definition",
        order_by="PromptVersion.version_number.desc()",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PromptVersion(Base, TimestampMixin):
    """
    Stores the content of each version of a prompt, linked to its definition.
    Manages which version is currently active.
    """

    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prompt_definition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prompt_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version_number: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    activated_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    activation_reason: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )

    # Relationships
    definition: Mapped["PromptDefinition"] = relationship(
        "PromptDefinition", back_populates="versions"
    )
    activated_by_user = relationship("User")
