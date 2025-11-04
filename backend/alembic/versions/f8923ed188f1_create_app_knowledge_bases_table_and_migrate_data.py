"""create app_knowledge_bases table and migrate data

Revision ID: f8923ed188f1
Revises: 9c130e8c6c92
Create Date: 2025-11-03 19:19:44.709923
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "f8923ed188f1"
down_revision: Union[str, None] = "9c130e8c6c92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1️⃣ Create new table
    op.create_table(
        "app_knowledge_bases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "app_id",
            sa.Integer(),
            sa.ForeignKey("apps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.UniqueConstraint("app_id", "knowledge_base_id", name="uq_app_kb"),
    )

    # 2️⃣ Add a generated virtual column to enforce only one default KB per app
    op.execute(
        text(
            """
            ALTER TABLE app_knowledge_bases
            ADD COLUMN unique_default_app_id INT
            GENERATED ALWAYS AS (
                CASE WHEN is_default = 1 THEN app_id ELSE NULL END
            ) VIRTUAL,
            ADD UNIQUE INDEX uq_app_default_kb_per_app (unique_default_app_id);
            """
        )
    )

    # 3️⃣ Migrate existing data from apps.knowledge_base_id
    conn = op.get_bind()
    conn.execute(
        text(
            """
            INSERT INTO app_knowledge_bases (
                app_id, knowledge_base_id, is_default,
                created_at, updated_at
            )
            SELECT id, knowledge_base_id, TRUE, NOW(), NOW()
            FROM apps
            WHERE knowledge_base_id IS NOT NULL;
            """
        )
    )

    # 4️⃣ Drop old column from apps
    op.drop_column("apps", "knowledge_base_id")


def downgrade():
    # 1️⃣ Re-add the old column
    op.add_column(
        "apps", sa.Column("knowledge_base_id", sa.Integer(), nullable=True)
    )

    # 2️⃣ Restore default KB relationships from app_knowledge_bases
    conn = op.get_bind()
    conn.execute(
        text(
            """
            UPDATE apps
            JOIN (
                SELECT akb.app_id,
                    COALESCE(
                        MAX(CASE WHEN akb.is_default = TRUE THEN akb.knowledge_base_id END),
                        MAX(akb.knowledge_base_id)
                    ) AS knowledge_base_id
                FROM app_knowledge_bases akb
                GROUP BY akb.app_id
            ) AS sub ON apps.id = sub.app_id
            SET apps.knowledge_base_id = sub.knowledge_base_id;
            """
        )
    )

    # 3️⃣ Drop unique index and virtual column
    op.execute(
        text(
            """
            ALTER TABLE app_knowledge_bases
            DROP INDEX uq_app_default_kb_per_app,
            DROP COLUMN unique_default_app_id;
            """
        )
    )

    # 4️⃣ Drop table
    op.drop_table("app_knowledge_bases")
