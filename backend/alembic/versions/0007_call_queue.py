"""Call queue module: queues, items, extend call_logs

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    # ============ call_queues ============
    op.create_table(
        "call_queues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("filter_overdue_min_days", sa.Integer(), nullable=True),
        sa.Column("filter_overdue_max_days", sa.Integer(), nullable=True),
        sa.Column("filter_debt_min", sa.Numeric(18, 2), nullable=True),
        sa.Column("filter_debt_max", sa.Numeric(18, 2), nullable=True),
        sa.Column("filter_contract_status", sa.String(50), nullable=True),
        sa.Column("auto_assign_strategy", sa.String(20), nullable=False, server_default="round_robin"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("retry_after_hours", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_call_queues_company_active", "call_queues", ["company_id", "is_active"])

    # ============ call_queue_items ============
    op.create_table(
        "call_queue_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, server_default="1"),
        sa.Column("queue_id", sa.Integer(), sa.ForeignKey("call_queues.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("debtor_id", sa.Integer(), sa.ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("assigned_manager_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0", index=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("last_call_outcome", sa.String(30), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("locked_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # composite index для быстрого "взять следующего"
    op.create_index(
        "ix_cqi_queue_status_priority",
        "call_queue_items",
        ["queue_id", "status", "priority", "next_attempt_at"],
    )
    op.create_index(
        "ix_cqi_manager_status",
        "call_queue_items",
        ["assigned_manager_id", "status"],
    )

    # ============ extend call_logs ============
    op.add_column("call_logs", sa.Column("outcome", sa.String(30), nullable=True))
    op.add_column("call_logs", sa.Column("queue_item_id", sa.Integer(), sa.ForeignKey("call_queue_items.id", ondelete="SET NULL"), nullable=True))
    op.add_column("call_logs", sa.Column("next_callback_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_call_logs_outcome", "call_logs", ["outcome"])


def downgrade():
    op.drop_index("ix_call_logs_outcome", table_name="call_logs")
    op.drop_column("call_logs", "next_callback_at")
    op.drop_column("call_logs", "queue_item_id")
    op.drop_column("call_logs", "outcome")

    op.drop_index("ix_cqi_manager_status", table_name="call_queue_items")
    op.drop_index("ix_cqi_queue_status_priority", table_name="call_queue_items")
    op.drop_table("call_queue_items")

    op.drop_index("ix_call_queues_company_active", table_name="call_queues")
    op.drop_table("call_queues")
