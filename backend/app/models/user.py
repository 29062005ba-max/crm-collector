from sqlalchemy import String, Boolean, Index, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.mixins import TimestampMixin
import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    HEAD = "HEAD"
    MANAGER = "MANAGER"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="MANAGER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True, default=1)

    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="manager")
    call_logs: Mapped[list["CallLog"]] = relationship("CallLog", back_populates="manager")
