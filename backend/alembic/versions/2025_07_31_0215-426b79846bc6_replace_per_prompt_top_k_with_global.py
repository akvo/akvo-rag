"""Add global top_k system setting

Revision ID: 426b79846bc6
Revises: 3b1d563d14f2
Create Date: 2025-07-31 02:15:00.082853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '426b79846bc6'
down_revision: Union[str, None] = '3b1d563d14f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add global system_settings table with default top_k setting.
    """
    system_settings_table = op.create_table('system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_id'), 'system_settings', ['id'], unique=False)
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    op.bulk_insert(system_settings_table,
        [
            {'key': 'top_k', 'value': '4'}
        ]
    )


def downgrade() -> None:
    """
    Remove the system_settings table.
    """
    op.drop_index(op.f('ix_system_settings_key'), table_name='system_settings')
    op.drop_index(op.f('ix_system_settings_id'), table_name='system_settings')
    op.drop_table('system_settings')
