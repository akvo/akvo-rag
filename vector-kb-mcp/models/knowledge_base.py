from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .document import Document
    from .document_chunk import DocumentChunk
    from .processing_task import ProcessingTask


class KnowledgeBase(Base, TimestampMixin):
    __tablename__ = "vkb_knowledge_bases"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    # Embedding model configuration & dimension guard
    embedding_model: Mapped[str] = mapped_column(
        String(100),
        default="text-embedding-3-small",
        server_default="text-embedding-3-small",
        nullable=False,
    )
    embedding_dim: Mapped[int] = mapped_column(
        Integer,
        default=1536,
        server_default="1536",
        nullable=False,
    )

    # Relationships with strict cascade deletion
    documents: Mapped[List[Document]] = relationship(
        "Document",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[List[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    processing_tasks: Mapped[List[ProcessingTask]] = relationship(
        "ProcessingTask",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
