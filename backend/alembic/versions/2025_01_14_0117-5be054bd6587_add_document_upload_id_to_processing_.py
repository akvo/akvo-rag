"""add_document_upload_id_to_processing_tasks

Revision ID: 5be054bd6587
Revises: fd73eebc87c1
Create Date: 2025-01-14 01:17:24.164593

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5be054bd6587"
down_revision: Union[str, None] = "fd73eebc87c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add document_upload_id column and foreign key constraint
    op.add_column(
        "processing_tasks",
        sa.Column("document_upload_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "processing_tasks_document_upload_id_fkey",
        "processing_tasks",
        "document_uploads",
        ["document_upload_id"],
        ["id"],
    )


def downgrade() -> None:
    # 1. Drop foreign key constraint and column
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE processing_tasks "
            "DROP CONSTRAINT IF EXISTS "
            "processing_tasks_document_upload_id_fkey;"
        )
    else:
        try:
            op.drop_constraint(
                "processing_tasks_document_upload_id_fkey",
                "processing_tasks",
                type_="foreignkey",
            )
        except Exception:
            pass
    op.drop_column("processing_tasks", "document_upload_id")
