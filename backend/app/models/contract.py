from sqlalchemy import String, Date, Numeric, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.mixins import TimestampMixin
from decimal import Decimal
import datetime
import enum


class ContractStatus(str, enum.Enum):
    ACTIVE = "active"           # Досудебный
    LITIGATION = "litigation"   # Судебный (ИсполНад)
    CLOSED = "closed"           # Закрыт
    WRITTEN_OFF = "written_off" # Списан


STATUS_LABELS = {
    "active": "Досудебный",
    "litigation": "Судебный",
    "closed": "Закрыт",
    "written_off": "Списан",
}


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    debtor_id: Mapped[int] = mapped_column(ForeignKey("debtors.id"), nullable=False, index=True)
    contract_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    original_creditor: Mapped[str] = mapped_column(String(500), nullable=False)
    product_type: Mapped[str | None] = mapped_column(String(100))
    principal_debt: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    interest_debt: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    penalty_debt: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))
    total_debt: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="KZT")
    issue_date: Mapped[datetime.date | None] = mapped_column(Date)
    overdue_date: Mapped[datetime.date | None] = mapped_column(Date)
    purchase_date: Mapped[datetime.date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(default=None, index=True)

    debtor: Mapped["Debtor"] = relationship("Debtor", back_populates="contracts")
    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="contract")
    call_logs: Mapped[list["CallLog"]] = relationship("CallLog", back_populates="contract")
    promises: Mapped[list["Promise"]] = relationship("Promise", back_populates="contract")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="contract")
    status_history: Mapped[list["StatusHistory"]] = relationship("StatusHistory", back_populates="contract")
