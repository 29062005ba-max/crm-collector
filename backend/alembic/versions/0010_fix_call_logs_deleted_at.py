"""Hotfix: add missing deleted_at column to call_logs (legacy schema gap)

Историческая проблема: модель CallLog имеет поле deleted_at, но миграции 0001-0009
его не создали. До модулей v2/v3 это было незаметно — никто не делал тяжёлых
запросов к call_logs. После запуска call_queue_service / analytics / my_day
все запросы по call_logs падают с UndefinedColumnError.

Эта миграция:
1. Безопасно (IF NOT EXISTS) добавляет deleted_at + индекс в call_logs
2. Делает defensive-проверку для других таблиц где модель ожидает deleted_at
   (assignments — на всякий случай; debtors уже имеет; promises уже имеет)

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    """Проверка наличия колонки через information_schema (PostgreSQL)."""
    bind = op.get_bind()
    res = bind.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column}).first()
    return res is not None


def _index_exists(index: str) -> bool:
    bind = op.get_bind()
    res = bind.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname=:i"
    ), {"i": index}).first()
    return res is not None


def upgrade():
    # === call_logs.deleted_at — главный фикс ===
    if not _column_exists("call_logs", "deleted_at"):
        op.add_column(
            "call_logs",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
    if not _index_exists("ix_call_logs_deleted"):
        op.create_index("ix_call_logs_deleted", "call_logs", ["deleted_at"])

    # === assignments.deleted_at — defensive check ===
    # модель Assignment тоже имеет deleted_at, проверим на всякий случай
    if not _column_exists("assignments", "deleted_at"):
        op.add_column(
            "assignments",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
    if not _index_exists("ix_assignments_deleted"):
        op.create_index("ix_assignments_deleted", "assignments", ["deleted_at"])


def downgrade():
    # downgrade удаляет колонки (но это опасно — данные потеряются если уже
    # что-то soft-delete'нуто). Поэтому только удаляем индексы; колонки оставляем.
    if _index_exists("ix_assignments_deleted"):
        op.drop_index("ix_assignments_deleted", table_name="assignments")
    if _index_exists("ix_call_logs_deleted"):
        op.drop_index("ix_call_logs_deleted", table_name="call_logs")
