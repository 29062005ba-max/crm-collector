"""Mixins for multi-tenancy and soft delete"""
from datetime import datetime
from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column


class TenantMixin:
    """Add company_id (tenant isolation) - usage: class Foo(Base, TenantMixin):"""
    @classmethod
    def __declare_first__(cls):
        pass

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


class SoftDeleteMixin:
    """Add deleted_at - records remain in DB but excluded from queries"""
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
