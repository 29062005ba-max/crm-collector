"""SaaS features: tasks, notifications, activity logs, payment schedules, kanban status

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== Add columns to debtors ====================
    op.add_column('debtors', sa.Column('kanban_status', sa.String(30), server_default='new'))
    op.add_column('debtors', sa.Column('assigned_manager_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_debtor_manager', 'debtors', 'users', ['assigned_manager_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_debtors_kanban_status', 'debtors', ['kanban_status'])
    op.create_index('ix_debtors_assigned_manager', 'debtors', ['assigned_manager_id'])

    # ==================== Tasks ====================
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', sa.String(30), nullable=False, server_default='followup'),  # followup, call, visit, document, other
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),    # open, in_progress, done, cancelled
        sa.Column('priority', sa.String(20), nullable=False, server_default='normal'), # low, normal, high, urgent
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('debtor_id', sa.Integer(), nullable=True),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['debtor_id'], ['debtors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_tasks_assignee', 'tasks', ['assignee_id'])
    op.create_index('ix_tasks_debtor', 'tasks', ['debtor_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])
    op.create_index('ix_tasks_due_date', 'tasks', ['due_date'])

    # ==================== Notifications ====================
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),  # promise_overdue, schedule_overdue, task_assigned, etc
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('link', sa.String(255), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('related_debtor_id', sa.Integer(), nullable=True),
        sa.Column('related_task_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_debtor_id'], ['debtors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_task_id'], ['tasks.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_notifications_user_unread', 'notifications', ['user_id', 'is_read'])
    op.create_index('ix_notifications_created', 'notifications', ['created_at'])

    # ==================== Activity Logs ====================
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),  # created, updated, deleted, status_changed, etc
        sa.Column('entity_type', sa.String(30), nullable=False),  # debtor, contract, payment, promise, task
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),  # {"field": ["old", "new"]}
        sa.Column('debtor_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['debtor_id'], ['debtors.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_activity_actor', 'activity_logs', ['actor_id'])
    op.create_index('ix_activity_debtor', 'activity_logs', ['debtor_id'])
    op.create_index('ix_activity_entity', 'activity_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_activity_created', 'activity_logs', ['created_at'])

    # ==================== Payment Schedules ====================
    op.create_table(
        'payment_schedules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('contract_id', sa.Integer(), nullable=False),
        sa.Column('total_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('down_payment', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('months', sa.Integer(), nullable=False),
        sa.Column('monthly_payment', sa.Numeric(18, 2), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),  # active, completed, broken, cancelled
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_schedules_contract', 'payment_schedules', ['contract_id'])
    op.create_index('ix_schedules_status', 'payment_schedules', ['status'])

    # ==================== Schedule Payments ====================
    op.create_table(
        'schedule_payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('schedule_id', sa.Integer(), nullable=False),
        sa.Column('payment_number', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('paid_amount', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, paid, partial, overdue
        sa.Column('paid_at', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['schedule_id'], ['payment_schedules.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_sched_pay_schedule', 'schedule_payments', ['schedule_id'])
    op.create_index('ix_sched_pay_due', 'schedule_payments', ['due_date'])
    op.create_index('ix_sched_pay_status', 'schedule_payments', ['status'])


def downgrade():
    op.drop_table('schedule_payments')
    op.drop_table('payment_schedules')
    op.drop_table('activity_logs')
    op.drop_table('notifications')
    op.drop_table('tasks')
    op.drop_constraint('fk_debtor_manager', 'debtors', type_='foreignkey')
    op.drop_index('ix_debtors_kanban_status', 'debtors')
    op.drop_index('ix_debtors_assigned_manager', 'debtors')
    op.drop_column('debtors', 'assigned_manager_id')
    op.drop_column('debtors', 'kanban_status')
