"""initial vkb schema

Revision ID: 001_initial_vkb_schema
Revises:
Create Date: 2026-09-02 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_vkb_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create vkb_knowledge_bases table
    op.create_table(
        "vkb_knowledge_bases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "embedding_model",
            sa.String(length=100),
            server_default="text-embedding-3-small",
            nullable=False,
        ),
        sa.Column(
            "embedding_dim",
            sa.Integer(),
            server_default="1536",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vkb_knowledge_bases_id"),
        "vkb_knowledge_bases",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vkb_knowledge_bases_name"),
        "vkb_knowledge_bases",
        ["name"],
        unique=False,
    )

    # 2. Create vkb_documents table
    op.create_table(
        "vkb_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("doc_version", sa.String(length=50), nullable=True),
        sa.Column("issuing_authority", sa.String(length=255), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("doc_type", sa.String(length=100), nullable=True),
        sa.Column("jurisdiction", sa.String(length=100), nullable=True),
        sa.Column(
            "metadata_",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["vkb_knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "knowledge_base_id", "file_name", name="uq_vkb_doc_kb_file_name"
        ),
    )
    op.create_index(
        op.f("ix_vkb_documents_id"), "vkb_documents", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_vkb_documents_knowledge_base_id"),
        "vkb_documents",
        ["knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vkb_documents_file_hash"),
        "vkb_documents",
        ["file_hash"],
        unique=False,
    )
    op.create_index(
        "idx_vkb_doc_kb_status",
        "vkb_documents",
        ["knowledge_base_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_vkb_doc_authority",
        "vkb_documents",
        ["issuing_authority"],
        unique=False,
    )
    op.create_index(
        "idx_vkb_doc_type",
        "vkb_documents",
        ["knowledge_base_id", "doc_type"],
        unique=False,
    )
    op.create_index(
        "idx_vkb_doc_metadata_gin",
        "vkb_documents",
        ["metadata_"],
        unique=False,
        postgresql_using="gin",
    )

    # 3. Create vkb_document_chunks table
    op.create_table(
        "vkb_document_chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("kb_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column(
            "chunk_metadata",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["vkb_documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["kb_id"], ["vkb_knowledge_bases.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vkb_document_chunks_kb_id"),
        "vkb_document_chunks",
        ["kb_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vkb_document_chunks_document_id"),
        "vkb_document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vkb_document_chunks_content_hash"),
        "vkb_document_chunks",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        "idx_vkb_chunk_kb_file",
        "vkb_document_chunks",
        ["kb_id", "file_name"],
        unique=False,
    )
    op.create_index(
        "idx_vkb_chunk_doc_idx",
        "vkb_document_chunks",
        ["document_id", "chunk_index"],
        unique=False,
    )

    # 4. Create vkb_processing_tasks table
    op.create_table(
        "vkb_processing_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["vkb_documents.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["vkb_knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vkb_processing_tasks_id"),
        "vkb_processing_tasks",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vkb_processing_tasks_task_id"),
        "vkb_processing_tasks",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "idx_vkb_task_kb_status",
        "vkb_processing_tasks",
        ["knowledge_base_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("vkb_processing_tasks")
    op.drop_table("vkb_document_chunks")
    op.drop_table("vkb_documents")
    op.drop_table("vkb_knowledge_bases")
