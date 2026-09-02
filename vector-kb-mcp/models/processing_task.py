from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .knowledge_base import KnowledgeBase
    from .document import Document


class ProcessingTask(Base, TimestampMixin):
    __tablename__ = "vkb_processing_tasks"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("vkb_knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vkb_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # UUID correlation ID
    job_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "INGEST_DOCUMENT", "DELETE_KB"
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", server_default="PENDING", nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    knowledge_base: Mapped[KnowledgeBase] = relationship(
        "KnowledgeBase", back_populates="processing_tasks"
    )
    document: Mapped[Optional[Document]] = relationship(
        "Document", back_populates="processing_tasks"
    )

    __table_args__ = (
        Index("idx_vkb_task_kb_status", "knowledge_base_id", "status"),
    )
