"""Scoring fields for debtors

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("debtors", sa.Column("score", sa.Integer(), nullable=True))
    op.add_column("debtors", sa.Column("score_tier", sa.String(10), nullable=True))
    op.add_column("debtors", sa.Column("score_calculated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_debtors_score_tier", "debtors", ["score_tier"])
    op.create_index("ix_debtors_score_desc", "debtors", ["score"])


def downgrade():
    op.drop_index("ix_debtors_score_desc", table_name="debtors")
    op.drop_index("ix_debtors_score_tier", table_name="debtors")
    op.drop_column("debtors", "score_calculated_at")
    op.drop_column("debtors", "score_tier")
    op.drop_column("debtors", "score")
