"""Manager KPI snapshot — pre-aggregated metrics for control panel.
Recalculated by Celery Beat every hour.
"""
from datetime import datetime, date as date_type
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, Date, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class ManagerKpiSnapshot(Base):
    __tablename__ = "manager_kpi_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    manager_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # day/week/month
    snapshot_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    # Collection
    collection_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal(0), nullable=False)
    payments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # PTP
    promises_given: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    promises_kept: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    promises_broken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ptp_conversion_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal(0), nullable=False)

    # Activity
    calls_made: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calls_reached: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    queue_items_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_kpi_snapshots_unique",
            "company_id", "manager_id", "period", "snapshot_date",
            unique=True,
        ),
        Index("ix_kpi_snapshots_period_date", "company_id", "period", "snapshot_date"),
    )
