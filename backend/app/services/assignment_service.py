"""
Автораспределение договоров по менеджерам.

Логика:
- Берём всех активных менеджеров
- Считаем текущую нагрузку каждого (кол-во активных договоров)
- Новые договора распределяем равномерно (round-robin по нагрузке)
- Судебные (litigation) — отдельная очередь если есть специализация
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.models.user import User, UserRole
from app.models.operations import Assignment
from app.models.contract import Contract


class AssignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_assign_all(self) -> dict:
        """Распределить все договора без менеджера."""
        managers = await self._get_active_managers()
        if not managers:
            return {"assigned": 0, "error": "Нет активных менеджеров"}

        # Договора без активного назначения
        assigned_contract_ids_q = (
            select(Assignment.contract_id)
            .where(Assignment.is_active == True)
        )
        unassigned = await self.db.execute(
            select(Contract).where(
                and_(
                    Contract.status.in_(["active", "litigation"]),
                    ~Contract.id.in_(assigned_contract_ids_q),
                )
            )
        )
        contracts = list(unassigned.scalars().all())

        if not contracts:
            return {"assigned": 0, "message": "Все договора уже распределены"}

        # Текущая нагрузка менеджеров
        loads = await self._get_manager_loads(managers)

        count = 0
        for contract in contracts:
            # Выбираем менеджера с минимальной нагрузкой
            manager = min(managers, key=lambda m: loads.get(m.id, 0))
            assignment = Assignment(
                contract_id=contract.id,
                manager_id=manager.id,
                is_active=True,
            )
            self.db.add(assignment)
            loads[manager.id] = loads.get(manager.id, 0) + 1
            count += 1

        await self.db.commit()
        return {"assigned": count, "managers": len(managers)}

    async def reassign_manager(self, from_manager_id: int, to_manager_id: int) -> dict:
        """Переназначить все договора от одного менеджера другому."""
        result = await self.db.execute(
            select(Assignment).where(
                and_(Assignment.manager_id == from_manager_id, Assignment.is_active == True)
            )
        )
        assignments = list(result.scalars().all())
        for a in assignments:
            a.manager_id = to_manager_id
        await self.db.flush()
        return {"reassigned": len(assignments)}

    async def get_manager_loads(self) -> list[dict]:
        """Нагрузка по каждому менеджеру."""
        managers = await self._get_active_managers()
        loads = await self._get_manager_loads(managers)
        return [
            {
                "manager_id": m.id,
                "manager_name": m.full_name,
                "contracts_count": loads.get(m.id, 0),
            }
            for m in managers
        ]

    async def _get_active_managers(self) -> list[User]:
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.is_active == True,
                    User.role.in_(["MANAGER", "HEAD", "manager", "head"]),
                )
            )
        )
        return list(result.scalars().all())

    async def _get_manager_loads(self, managers: list[User]) -> dict:
        if not managers:
            return {}
        manager_ids = [m.id for m in managers]
        result = await self.db.execute(
            select(Assignment.manager_id, func.count(Assignment.id).label("cnt"))
            .where(
                and_(
                    Assignment.manager_id.in_(manager_ids),
                    Assignment.is_active == True,
                )
            )
            .group_by(Assignment.manager_id)
        )
        return {row.manager_id: row.cnt for row in result.all()}
