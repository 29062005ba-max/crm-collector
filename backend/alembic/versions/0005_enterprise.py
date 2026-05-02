"""Enterprise: idempotency keys, optimistic locking, observability fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    # ============== Idempotency Keys ==============
    # Защита от дублей: каждое критическое действие имеет уникальный ключ
    op.create_table(
        'idempotency_keys',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('key', sa.String(128), unique=True, nullable=False, index=True),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('request_hash', sa.String(64), nullable=False),  # SHA256 от тела запроса
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),  # обычно +24h
    )
    op.create_index('ix_idempotency_company', 'idempotency_keys', ['company_id'])
    op.create_index('ix_idempotency_expires', 'idempotency_keys', ['expires_at'])

    # ============== Event Log ==============
    # История всех событий системы (event sourcing lite)
    op.create_table(
        'event_log',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('event_type', sa.String(64), nullable=False, index=True),
        sa.Column('aggregate_type', sa.String(32), nullable=False),  # debtor, payment, promise...
        sa.Column('aggregate_id', sa.Integer(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True, index=True),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('handler_results', postgresql.JSONB, nullable=True),
        sa.Column('correlation_id', sa.String(64), nullable=True),  # связь между событиями одной операции
        sa.Column('idempotency_key', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_event_unprocessed', 'event_log', ['processed', 'created_at'])
    op.create_index('ix_event_correlation', 'event_log', ['correlation_id'])

    # ============== Background Job Tracker ==============
    # Tracking Celery tasks для observability
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('task_id', sa.String(64), unique=True, nullable=False, index=True),  # Celery task UUID
        sa.Column('task_name', sa.String(128), nullable=False),
        sa.Column('queue', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),  # pending, running, success, failed, retry
        sa.Column('args', postgresql.JSONB, nullable=True),
        sa.Column('result', postgresql.JSONB, nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('company_id', sa.Integer(), nullable=True, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_jobs_status', 'background_jobs', ['status'])
    op.create_index('ix_jobs_queue', 'background_jobs', ['queue'])

    # ============== Optimistic Locking ==============
    # Добавим version столбец в финансовые таблицы
    for table in ['debtors', 'contracts', 'promises', 'payments', 'payment_schedules']:
        op.add_column(table, sa.Column('version', sa.Integer(), nullable=False, server_default='1'))

    # ============== Audit Log v3 - дополнительные поля наблюдаемости ==============
    op.add_column('activity_logs', sa.Column('correlation_id', sa.String(64), nullable=True))
    op.add_column('activity_logs', sa.Column('request_id', sa.String(64), nullable=True))
    op.create_index('ix_activity_correlation', 'activity_logs', ['correlation_id'])


def downgrade():
    op.drop_index('ix_activity_correlation', table_name='activity_logs')
    op.drop_column('activity_logs', 'request_id')
    op.drop_column('activity_logs', 'correlation_id')
    for table in ['debtors', 'contracts', 'promises', 'payments', 'payment_schedules']:
        op.drop_column(table, 'version')
    op.drop_table('background_jobs')
    op.drop_table('event_log')
    op.drop_table('idempotency_keys')
