from __future__ import annotations

from typing import List, TYPE_CHECKING
from sqlalchemy import String, BigInteger, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .knowledge_base import KnowledgeBase
    from .document_chunk import DocumentChunk
    from .processing_task import ProcessingTask


class Document(Base, TimestampMixin):
    __tablename__ = "vkb_documents"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, index=True
    )
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("vkb_knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # S3/MinIO key
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", server_default="PENDING", nullable=False
    )

    # Relationships
    knowledge_base: Mapped[KnowledgeBase] = relationship(
        "KnowledgeBase", back_populates="documents"
    )
    chunks: Mapped[List[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    processing_tasks: Mapped[List[ProcessingTask]] = relationship(
        "ProcessingTask",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "knowledge_base_id", "file_name", name="uq_vkb_doc_kb_file_name"
        ),
        Index("idx_vkb_doc_kb_status", "knowledge_base_id", "status"),
    )
