"""add is_admin to users

Revision ID: 0001_add_is_admin
Revises: 
Create Date: 2026-09-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_is_admin'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == 'sqlite':
        with op.batch_alter_table('users') as batch_op:
            batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    else:
        default = 'false' if dialect.startswith('postgres') else '0'
        op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text(default)))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == 'sqlite':
        with op.batch_alter_table('users') as batch_op:
            batch_op.drop_column('is_admin')
    else:
        op.drop_column('users', 'is_admin')
