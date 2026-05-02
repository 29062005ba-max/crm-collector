"""Manager KPI snapshots + performance indexes for my-day

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    # ============ manager_kpi_snapshots ============
    op.create_table(
        "manager_kpi_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("manager_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period", sa.String(10), nullable=False, index=True),  # day / week / month
        sa.Column("snapshot_date", sa.Date(), nullable=False, index=True),
        # Collection metrics
        sa.Column("collection_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("payments_count", sa.Integer(), nullable=False, server_default="0"),
        # PTP (Promise to Pay) metrics
        sa.Column("promises_given", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("promises_kept", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("promises_broken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ptp_conversion_pct", sa.Numeric(5, 2), nullable=False, server_default="0"),
        # Activity metrics
        sa.Column("calls_made", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calls_reached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queue_items_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_completed", sa.Integer(), nullable=False, server_default="0"),
        # Meta
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_kpi_snapshots_unique",
        "manager_kpi_snapshots",
        ["company_id", "manager_id", "period", "snapshot_date"],
        unique=True,
    )
    op.create_index(
        "ix_kpi_snapshots_period_date",
        "manager_kpi_snapshots",
        ["company_id", "period", "snapshot_date"],
    )

    # ============ Promise auto-fulfilled fields (Module 3) ============
    op.add_column("promises", sa.Column("auto_fulfilled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("promises", sa.Column("fulfilled_by_payment_id", sa.Integer(),
                                          sa.ForeignKey("payments.id", ondelete="SET NULL"), nullable=True))
    op.add_column("promises", sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_promises_auto_fulfilled", "promises", ["auto_fulfilled"])

    # ============ Performance indexes for my-day query ============
    # tasks: lookup by assignee + due_date + status (for «План на день»)
    op.create_index(
        "ix_tasks_assignee_due_status",
        "tasks",
        ["assignee_id", "due_date", "status"],
    )
    # promises: by status + date (for «обещания на сегодня» / «просроченные»)
    op.create_index(
        "ix_promises_status_date",
        "promises",
        ["status", "promise_date"],
    )
    # promises: by created_by + status (для KPI менеджера)
    op.create_index(
        "ix_promises_creator_status",
        "promises",
        ["created_by_id", "status"],
    )
    # payments: by registered_by + date (для KPI sum)
    op.create_index(
        "ix_payments_registrar_date",
        "payments",
        ["registered_by_id", "payment_date"],
    )


def downgrade():
    op.drop_index("ix_payments_registrar_date", table_name="payments")
    op.drop_index("ix_promises_creator_status", table_name="promises")
    op.drop_index("ix_promises_status_date", table_name="promises")
    op.drop_index("ix_tasks_assignee_due_status", table_name="tasks")
    op.drop_index("ix_promises_auto_fulfilled", table_name="promises")
    op.drop_column("promises", "fulfilled_at")
    op.drop_column("promises", "fulfilled_by_payment_id")
    op.drop_column("promises", "auto_fulfilled")
    op.drop_index("ix_kpi_snapshots_period_date", table_name="manager_kpi_snapshots")
    op.drop_index("ix_kpi_snapshots_unique", table_name="manager_kpi_snapshots")
    op.drop_table("manager_kpi_snapshots")
