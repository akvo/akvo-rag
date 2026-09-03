from __future__ import annotations

from typing import Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .knowledge_base import KnowledgeBase
    from .document import Document


class DocumentChunk(Base):
    __tablename__ = "vkb_document_chunks"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True
    )  # SHA-256 deterministic chunk ID
    kb_id: Mapped[int] = mapped_column(
        ForeignKey("vkb_knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int] = mapped_column(
        ForeignKey("vkb_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    knowledge_base: Mapped[KnowledgeBase] = relationship(
        "KnowledgeBase", back_populates="chunks"
    )
    document: Mapped[Document] = relationship(
        "Document", back_populates="chunks"
    )

    __table_args__ = (
        Index("idx_vkb_chunk_kb_file", "kb_id", "file_name"),
        Index("idx_vkb_chunk_doc_idx", "document_id", "chunk_index"),
    )
