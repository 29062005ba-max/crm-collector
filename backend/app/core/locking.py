"""Concurrency-safe utilities: SELECT FOR UPDATE, optimistic locking"""
from typing import Type, TypeVar, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import Base

T = TypeVar("T", bound=Base)


async def get_for_update(
    db: AsyncSession,
    model: Type[T],
    id: int,
    skip_locked: bool = False,
) -> Optional[T]:
    """
    SELECT ... FOR UPDATE — блокировка строки до конца транзакции.
    Используется в финансовых операциях для предотвращения race conditions.

    skip_locked=True — пропустить заблокированные строки (для batch processing).
    """
    q = select(model).where(model.id == id).with_for_update(skip_locked=skip_locked)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def increment_version(obj) -> None:
    """Optimistic locking: увеличить version. ORM сам проверит при commit."""
    if hasattr(obj, "version"):
        obj.version = (obj.version or 0) + 1
