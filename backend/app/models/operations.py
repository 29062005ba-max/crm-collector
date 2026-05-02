from sqlalchemy import String, Date, DateTime, Numeric, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func
from app.db.session import Base
from app.models.mixins import TimestampMixin
from decimal import Decimal
import datetime
import enum


class CallResult(str, enum.Enum):
    REACHED = "reached"
    NOT_REACHED = "not_reached"
    BUSY = "busy"
    WRONG_NUMBER = "wrong_number"
    REFUSED = "refused"


class PromiseStatus(str, enum.Enum):
    ACTIVE = "active"
    DONE = "done"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentSource(str, enum.Enum):
    BANK = "bank"
    CASH = "cash"
    CARD = "card"
    COURT = "court"


class CsiStatus(str, enum.Enum):
    PENDING = "pending"
    FILED = "filed"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(default=None, index=True)

    contract: Mapped["Contract"] = relationship("Contract", back_populates="assignments")
    manager: Mapped["User"] = relationship("User", back_populates="assignments")


class CallLog(Base, TimestampMixin):
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    called_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50))
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(default=None, index=True)

    # Call queue integration (миграция 0007)
    outcome: Mapped[str | None] = mapped_column(String(30), index=True)
    queue_item_id: Mapped[int | None] = mapped_column(ForeignKey("call_queue_items.id", ondelete="SET NULL"))
    next_callback_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    contract: Mapped["Contract"] = relationship("Contract", back_populates="call_logs")
    manager: Mapped["User"] = relationship("User", back_populates="call_logs")


class Promise(Base, TimestampMixin):
    __tablename__ = "promises"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    promise_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Soft delete (миграция 0004 добавила колонку в БД, в модели НЕ было — fix v3.2)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), default=None, index=True)

    # === Auto-fulfilled tracking (Module 3, migration 0009) ===
    # True если обещание было закрыто системой автоматически при поступлении платежа
    auto_fulfilled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    # Идентификатор платежа который закрыл обещание (используется для idempotency)
    fulfilled_by_payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    fulfilled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    contract: Mapped["Contract"] = relationship("Contract", back_populates="promises")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    payment_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="bank")
    reference: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    receipt_path: Mapped[str | None] = mapped_column(String(500))
    registered_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Soft delete (миграция 0004 добавила колонку в БД, в модели НЕ было — fix v3.2)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), default=None, index=True)

    contract: Mapped["Contract"] = relationship("Contract", back_populates="payments")


class CsiCase(Base, TimestampMixin):
    __tablename__ = "csi_cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    debtor_id: Mapped[int] = mapped_column(ForeignKey("debtors.id"), nullable=False, index=True)
    case_number: Mapped[str | None] = mapped_column(String(100))
    filed_date: Mapped[datetime.date | None] = mapped_column(Date)
    court_name: Mapped[str | None] = mapped_column(String(500))
    bailiff_name: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    amount_claimed: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    debtor: Mapped["Debtor"] = relationship("Debtor", back_populates="csi_cases")


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="processing")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    old_status: Mapped[str | None] = mapped_column(String(100))
    new_status: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    comment: Mapped[str | None] = mapped_column(Text)

    contract: Mapped["Contract"] = relationship("Contract", back_populates="status_history")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    old_values: Mapped[dict | None] = mapped_column(JSON)
    new_values: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
