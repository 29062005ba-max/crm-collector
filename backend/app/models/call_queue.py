"""Call Queue models — auto-dial queue with manager distribution"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Integer, Text, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.mixins import TimestampMixin


# ===== Statuses =====
QUEUE_ITEM_STATUS_PENDING = "pending"        # ждёт обзвона
QUEUE_ITEM_STATUS_IN_PROGRESS = "in_progress"  # менеджер взял в работу (locked)
QUEUE_ITEM_STATUS_COMPLETED = "completed"    # дозвонился / отказ / неверный номер
QUEUE_ITEM_STATUS_SCHEDULED = "scheduled"    # повторный звонок запланирован
QUEUE_ITEM_STATUS_FAILED = "failed"          # исчерпаны попытки

# ===== Outcomes =====
CALL_OUTCOME_REACHED = "reached"
CALL_OUTCOME_NOT_REACHED = "not_reached"
CALL_OUTCOME_PROMISE = "promise"
CALL_OUTCOME_CALLBACK = "callback"
CALL_OUTCOME_REFUSED = "refused"
CALL_OUTCOME_WRONG_NUMBER = "wrong_number"


class CallQueue(Base, TimestampMixin):
    __tablename__ = "call_queues"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Фильтры для наполнения
    filter_overdue_min_days: Mapped[int | None] = mapped_column(Integer)
    filter_overdue_max_days: Mapped[int | None] = mapped_column(Integer)
    filter_debt_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    filter_debt_max: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    filter_contract_status: Mapped[str | None] = mapped_column(String(50))

    # Стратегия
    auto_assign_strategy: Mapped[str] = mapped_column(String(20), default="round_robin", nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_after_hours: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    items: Mapped[list["CallQueueItem"]] = relationship(
        "CallQueueItem", back_populates="queue", cascade="all, delete-orphan"
    )


class CallQueueItem(Base, TimestampMixin):
    __tablename__ = "call_queue_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1
    )
    queue_id: Mapped[int] = mapped_column(
        ForeignKey("call_queues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    debtor_id: Mapped[int] = mapped_column(
        ForeignKey("debtors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[int | None] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), index=True
    )
    assigned_manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    status: Mapped[str] = mapped_column(String(20), default=QUEUE_ITEM_STATUS_PENDING, nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)

    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_call_outcome: Mapped[str | None] = mapped_column(String(30))

    # Lock — менеджер «забронировал» на 5 минут пока разговаривает
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    locked_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    queue: Mapped["CallQueue"] = relationship("CallQueue", back_populates="items")
