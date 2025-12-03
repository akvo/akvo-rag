"""Add approval columns in users table

Revision ID: de57ec74e817
Revises: f8923ed188f1
Create Date: 2025-11-17 09:34:03.358613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de57ec74e817'
down_revision: Union[str, None] = 'f8923ed188f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('approved_by', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'users', 'users', ['approved_by'], ['id'])


def downgrade() -> None:
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.drop_column('users', 'approved_at')
    op.drop_column('users', 'approved_by')
