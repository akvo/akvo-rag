from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin
from enum import Enum


# This Enum remains the single source of truth for prompt names
class PromptNameEnum(
    str, Enum
):  # Inherit from str for direct use as string values
    contextualize_q_system_prompt = "contextualize_q_system_prompt"
    qa_flexible_prompt = "qa_flexible_prompt"
    qa_strict_prompt = "qa_strict_prompt"


class PromptDefinition(Base, TimestampMixin):
    """
    Defines the logical prompt types (e.g., "qa_flexible_prompt").
    This table stores the fixed, unique names of your prompts.
    """

    __tablename__ = "prompt_definitions"

    id = Column(Integer, primary_key=True, index=True)
    # The 'name' here will store the string value from PromptNameEnum
    # It must be unique as it defines the distinct prompt categories
    name = Column(String(255), unique=True, index=True, nullable=False)

    versions = relationship(
        "PromptVersion",
        back_populates="definition",
        order_by="PromptVersion.version_number.desc()",
        lazy="selectin",
        cascade="all, delete-orphan",
    )  # Eager load versions, delete orphans


class PromptVersion(Base, TimestampMixin):
    """
    Stores the content of each version of a prompt, linked to its definition.
    Manages which version is currently active.
    """

    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_definition_id = Column(
        Integer,
        ForeignKey("prompt_definitions.id"),
        nullable=False,
        index=True,
    )
    content = Column(LONGTEXT, nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, default=False, nullable=False)
    activated_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    activation_reason = Column(String(512), nullable=True)

    # Relationships
    definition = relationship("PromptDefinition", back_populates="versions")
    activated_by_user = relationship("User")
