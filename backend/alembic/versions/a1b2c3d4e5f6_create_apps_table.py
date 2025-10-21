"""create apps table

Revision ID: a1b2c3d4e5f6
Revises: 4fa99fd9129b
Create Date: 2025-10-09 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "4fa99fd9129b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create apps table
    op.create_table(
        "apps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("app_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.Column("app_name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("default_chat_prompt", sa.Text(), nullable=True),
        sa.Column("chat_callback_url", sa.String(length=512), nullable=False),
        sa.Column("upload_callback_url", sa.String(length=512), nullable=False),
        sa.Column("access_token", sa.String(length=128), nullable=False),
        sa.Column("callback_token", sa.String(length=255), nullable=True),
        sa.Column("scopes", mysql.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "revoked", "suspended", name="appstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_apps_id"), "apps", ["id"], unique=False)
    op.create_index(op.f("ix_apps_app_id"), "apps", ["app_id"], unique=True)
    op.create_index(op.f("ix_apps_client_id"), "apps", ["client_id"], unique=True)
    op.create_index(
        op.f("ix_apps_access_token"), "apps", ["access_token"], unique=True
    )


def downgrade() -> None:
    # Drop apps table
    op.drop_index(op.f("ix_apps_access_token"), table_name="apps")
    op.drop_index(op.f("ix_apps_client_id"), table_name="apps")
    op.drop_index(op.f("ix_apps_app_id"), table_name="apps")
    op.drop_index(op.f("ix_apps_id"), table_name="apps")
    op.drop_table("apps")
