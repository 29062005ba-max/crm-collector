"""Company model - tenant isolation (multi-tenancy)"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.mixins import TimestampMixin


class Company(Base, TimestampMixin):
    """Tenant - каждая компания изолирована"""
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    tariff: Mapped[str] = mapped_column(String(50), default="basic", nullable=False)  # basic, pro, enterprise
    max_users: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_debtors: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict | None] = mapped_column(JSONB)


# Tariff limits configuration
TARIFF_LIMITS = {
    "basic": {"max_users": 3, "max_debtors": 1000, "label": "Базовый"},
    "pro": {"max_users": 10, "max_debtors": 10000, "label": "Профессиональный"},
    "enterprise": {"max_users": 100, "max_debtors": 100000, "label": "Enterprise"},
}
