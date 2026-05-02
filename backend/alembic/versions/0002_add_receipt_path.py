"""add receipt_path to payments

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('receipt_path', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('payments', 'receipt_path')
