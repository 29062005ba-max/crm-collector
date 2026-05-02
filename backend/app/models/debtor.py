from sqlalchemy import String, Date, Text, Index, Numeric, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.mixins import TimestampMixin
from decimal import Decimal
import datetime


class Debtor(Base, TimestampMixin):
    __tablename__ = "debtors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    iin: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    birth_date: Mapped[datetime.date | None] = mapped_column(Date)
    phone_primary: Mapped[str | None] = mapped_column(String(50))
    phone_secondary: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    employer: Mapped[str | None] = mapped_column(String(500))
    employer_phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), default=None, index=True)
    kanban_status: Mapped[str] = mapped_column(String(30), default="new", server_default="new")
    assigned_manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True)

    # Scoring (миграция 0008)
    score: Mapped[int | None] = mapped_column(Integer, index=True)
    score_tier: Mapped[str | None] = mapped_column(String(10), index=True)  # hot / medium / low
    score_calculated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="debtor")
    csi_cases: Mapped[list["CsiCase"]] = relationship("CsiCase", back_populates="debtor")

    __table_args__ = (
        Index("ix_debtors_full_name", "full_name"),
        Index("ix_debtors_phone", "phone_primary"),
    )
