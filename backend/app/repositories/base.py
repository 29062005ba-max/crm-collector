from typing import TypeVar, Generic, Type, Optional, Sequence
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    def _apply_company_filter(self, query, company_id: int | None):
        """Apply tenant isolation if model has company_id"""
        if company_id is not None and hasattr(self.model, "company_id"):
            query = query.where(self.model.company_id == company_id)
        return query

    def _apply_soft_delete_filter(self, query, include_deleted: bool = False):
        """Filter out soft-deleted records"""
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))
        return query

    async def get(self, id: int, company_id: int | None = None) -> Optional[ModelType]:
        q = select(self.model).where(self.model.id == id)
        q = self._apply_company_filter(q, company_id)
        q = self._apply_soft_delete_filter(q)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100, company_id: int | None = None) -> Sequence[ModelType]:
        q = select(self.model)
        q = self._apply_company_filter(q, company_id)
        q = self._apply_soft_delete_filter(q)
        q = q.offset(skip).limit(limit)
        result = await self.db.execute(q)
        return result.scalars().all()

    async def count(self, company_id: int | None = None) -> int:
        q = select(func.count()).select_from(self.model)
        q = self._apply_company_filter(q, company_id)
        q = self._apply_soft_delete_filter(q)
        result = await self.db.execute(q)
        return result.scalar_one()

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType) -> ModelType:
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """Hard delete. For audit-sensitive data use soft_delete()"""
        await self.db.delete(obj)
        await self.db.flush()

    async def soft_delete(self, obj: ModelType) -> ModelType:
        """Mark as deleted without removing from DB"""
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(obj)
        else:
            raise ValueError(f"{self.model.__name__} doesn't support soft delete")
        return obj
