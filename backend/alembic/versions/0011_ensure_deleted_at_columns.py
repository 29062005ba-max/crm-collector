"""Hotfix v3.2: ensure deleted_at columns exist in call_logs and assignments

Этот скрипт использует PostgreSQL ADD COLUMN IF NOT EXISTS — гарантированно
работает даже если миграция 0010 (hotfix v3.1) уже применилась но не создала
колонки. Без conditional Python-чеков, которые могли упасть на async контексте.

Revision ID: 0011
Revises: 0010
"""
from alembic import op


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    # ============ call_logs.deleted_at ============
    op.execute("""
        ALTER TABLE call_logs
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_call_logs_deleted
        ON call_logs(deleted_at)
    """)

    # ============ assignments.deleted_at ============
    op.execute("""
        ALTER TABLE assignments
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_assignments_deleted
        ON assignments(deleted_at)
    """)


def downgrade():
    # downgrade удаляет только индексы; колонки оставляем чтоб не потерять данные
    op.execute("DROP INDEX IF EXISTS ix_assignments_deleted")
    op.execute("DROP INDEX IF EXISTS ix_call_logs_deleted")
