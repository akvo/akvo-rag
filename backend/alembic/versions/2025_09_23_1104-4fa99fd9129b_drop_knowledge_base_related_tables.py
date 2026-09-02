"""drop knowledge base related tables

Revision ID: 4fa99fd9129b
Revises: f6f5943ad151
Create Date: 2025-09-23 11:04:22.646338

⚠️ WARNING: Destructive migration DATA LOSS

This migration will:
- TRUNCATE chat_knowledge_bases, messages, and chats (permanent data loss)
- DROP all knowledge base related tables (knowledge_bases, documents
    document_uploads, processing_tasks, document_chunks)

Downgrade will recreate the dropped tables, but chat/message data
cannot be restored after truncation.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "4fa99fd9129b"
down_revision: Union[str, None] = "f6f5943ad151"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Step 1: Delete and reset chat-related tables ---
    # Delete data while respecting FKs
    op.execute("DELETE FROM chat_knowledge_bases;")
    op.execute("DELETE FROM messages;")
    op.execute("DELETE FROM chats;")

    # Reset AUTO_INCREMENT counters
    op.execute("ALTER TABLE messages AUTO_INCREMENT = 1;")
    op.execute("ALTER TABLE chats AUTO_INCREMENT = 1;")

    # --- Step 2: Drop FKs and tables in dependency order ---

    # --- document_chunks ---
    op.drop_constraint(
        "document_chunks_ibfk_1", "document_chunks", type_="foreignkey"
    )
    op.drop_constraint(
        "document_chunks_ibfk_2", "document_chunks", type_="foreignkey"
    )
    op.drop_table("document_chunks")

    # --- processing_tasks ---
    op.drop_constraint(
        "processing_tasks_document_upload_id_fkey",
        "processing_tasks",
        type_="foreignkey",
    )
    op.drop_constraint(
        "processing_tasks_ibfk_1", "processing_tasks", type_="foreignkey"
    )
    op.drop_constraint(
        "processing_tasks_ibfk_2", "processing_tasks", type_="foreignkey"
    )
    op.drop_table("processing_tasks")

    # --- document_uploads ---
    op.drop_constraint(
        "document_uploads_ibfk_1", "document_uploads", type_="foreignkey"
    )
    op.drop_table("document_uploads")

    # --- documents ---
    op.drop_constraint("documents_ibfk_1", "documents", type_="foreignkey")
    op.drop_table("documents")

    # --- knowledge_bases ---
    op.drop_constraint(
        "knowledge_bases_ibfk_1", "knowledge_bases", type_="foreignkey"
    )
    op.drop_table("knowledge_bases")


def downgrade() -> None:
    # --- knowledge_bases ---
    op.create_table(
        "knowledge_bases",
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", mysql.LONGTEXT, nullable=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_knowledge_bases_id", "id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="knowledge_bases_ibfk_1"
        ),
    )

    # --- documents ---
    op.create_table(
        "documents",
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("file_path", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("knowledge_base_id", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_documents_id", "id"),
        sa.Index("ix_documents_file_hash", "file_hash"),
        sa.UniqueConstraint(
            "knowledge_base_id", "file_name", name="uq_kb_file_name"
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name="documents_ibfk_1",
        ),
    )

    # --- document_uploads ---
    op.create_table(
        "document_uploads",
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("knowledge_base_id", sa.Integer, nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("temp_path", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="pending"
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_document_uploads_id", "id"),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name="document_uploads_ibfk_1",
            ondelete="CASCADE",
        ),
    )

    # --- processing_tasks ---
    op.create_table(
        "processing_tasks",
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("knowledge_base_id", sa.Integer, nullable=True),
        sa.Column("document_id", sa.Integer, nullable=True),
        sa.Column(
            "status", sa.String(50), nullable=True, server_default="pending"
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.Column("document_upload_id", sa.Integer, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_processing_tasks_id", "id"),
        sa.Index("document_id", "document_id"),
        sa.Index("knowledge_base_id", "knowledge_base_id"),
        sa.Index(
            "processing_tasks_document_upload_id_fkey", "document_upload_id"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="processing_tasks_ibfk_1"
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            name="processing_tasks_ibfk_2",
        ),
        sa.ForeignKeyConstraint(
            ["document_upload_id"],
            ["document_uploads.id"],
            name="processing_tasks_document_upload_id_fkey",
        ),
    )

    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(64), primary_key=True, nullable=False),
        sa.Column("kb_id", sa.Integer, nullable=False),
        sa.Column("document_id", sa.Integer, nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("chunk_metadata", sa.JSON, nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_kb_file_name", "kb_id", "file_name"),
        sa.Index("ix_document_chunks_hash", "hash"),
        sa.Index("document_id", "document_id"),
        sa.ForeignKeyConstraint(
            ["kb_id"], ["knowledge_bases.id"], name="document_chunks_ibfk_1"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], name="document_chunks_ibfk_2"
        ),
    )

    # NOTE: chats/messages/chat_knowledge_bases remain empty after downgrade
