from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import date
from sqlalchemy import (
    String,
    BigInteger,
    ForeignKey,
    UniqueConstraint,
    Index,
    Date,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
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

    # --- Public-Sector Governance & Citation Metadata ---
    doc_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    issuing_authority: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    doc_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    jurisdiction: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
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
        Index("idx_vkb_doc_authority", "issuing_authority"),
        Index("idx_vkb_doc_type", "knowledge_base_id", "doc_type"),
        Index("idx_vkb_doc_metadata_gin", "metadata_", postgresql_using="gin"),
    )
