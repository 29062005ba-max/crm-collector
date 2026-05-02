"""
Scoring Service — рейтинг должников по вероятности оплаты.

Алгоритм (баллы 0-100):
  Базовый балл = 50

  ПЛЮС:
  + до 20 за наличие телефонов (2 номера = +20, 1 = +10)
  + до 15 за активные обещания (active promise сегодня/в будущем)
  + до 15 за недавние reached звонки (за 30 дней)
  + до 10 за платежи за последние 90 дней
  + 5 за работодателя (есть employer)

  МИНУС:
  - до 20 за сорванные обещания (broken/overdue)
  - до 15 за failed call_queue items (не дозвонились 3 раза)
  - до 10 за слишком большой долг (>500 000)
  - до 10 за большую просрочку (>180 дней)

Tier:
  >= 70 → hot
  40-69 → medium
  < 40  → low
"""
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.debtor import Debtor
from app.models.contract import Contract
from app.models.operations import Promise, Payment, CallLog
from app.models.call_queue import CallQueueItem, QUEUE_ITEM_STATUS_FAILED


def tier_for(score: int) -> str:
    if score >= 70:
        return "hot"
    if score >= 40:
        return "medium"
    return "low"


class ScoringService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    async def calculate(self, debtor_id: int) -> dict:
        debtor = await self.db.get(Debtor, debtor_id)
        if not debtor:
            return {"score": 0, "tier": "low"}

        score = 50

        # Phones
        phones = sum(1 for p in [debtor.phone_primary, debtor.phone_secondary] if p)
        score += phones * 10  # max +20

        # Employer
        if debtor.employer:
            score += 5

        # Contracts — total debt
        cq = select(func.sum(Contract.total_debt)).where(Contract.debtor_id == debtor_id)
        if self.company_id is not None:
            cq = cq.where(Contract.company_id == self.company_id)
        total_debt = (await self.db.execute(cq)).scalar() or 0
        if float(total_debt) > 500_000:
            score -= 10
        elif float(total_debt) > 200_000:
            score -= 5

        # Overdue depth
        oq = select(func.min(Contract.overdue_date)).where(Contract.debtor_id == debtor_id)
        if self.company_id is not None:
            oq = oq.where(Contract.company_id == self.company_id)
        oldest_overdue = (await self.db.execute(oq)).scalar()
        if oldest_overdue:
            days_overdue = (date.today() - oldest_overdue).days
            if days_overdue > 180:
                score -= 10
            elif days_overdue > 90:
                score -= 5

        # Active promises
        contract_ids_q = select(Contract.id).where(Contract.debtor_id == debtor_id)
        if self.company_id is not None:
            contract_ids_q = contract_ids_q.where(Contract.company_id == self.company_id)
        contract_ids = list((await self.db.execute(contract_ids_q)).scalars().all())

        if contract_ids:
            active_promises = (await self.db.execute(
                select(func.count(Promise.id)).where(
                    Promise.contract_id.in_(contract_ids),
                    Promise.status == "active",
                    Promise.promise_date >= date.today(),
                )
            )).scalar() or 0
            score += min(active_promises * 8, 15)

            # Broken promises
            broken_promises = (await self.db.execute(
                select(func.count(Promise.id)).where(
                    Promise.contract_id.in_(contract_ids),
                    Promise.status.in_(["overdue", "broken"]),
                )
            )).scalar() or 0
            score -= min(broken_promises * 7, 20)

            # Recent reached calls
            since = datetime.utcnow() - timedelta(days=30)
            reached = (await self.db.execute(
                select(func.count(CallLog.id)).where(
                    CallLog.contract_id.in_(contract_ids),
                    CallLog.outcome.in_(["reached", "promise"]),
                    CallLog.called_at >= since,
                )
            )).scalar() or 0
            score += min(reached * 5, 15)

            # Recent payments
            pay_since = date.today() - timedelta(days=90)
            recent_pays = (await self.db.execute(
                select(func.count(Payment.id)).where(
                    Payment.contract_id.in_(contract_ids),
                    Payment.payment_date >= pay_since,
                )
            )).scalar() or 0
            score += min(recent_pays * 3, 10)

        # Failed call queue items
        fq = select(func.count(CallQueueItem.id)).where(
            CallQueueItem.debtor_id == debtor_id,
            CallQueueItem.status == QUEUE_ITEM_STATUS_FAILED,
        )
        if self.company_id is not None:
            fq = fq.where(CallQueueItem.company_id == self.company_id)
        failed = (await self.db.execute(fq)).scalar() or 0
        score -= min(failed * 8, 15)

        score = max(0, min(100, score))
        tier = tier_for(score)

        debtor.score = score
        debtor.score_tier = tier
        debtor.score_calculated_at = datetime.utcnow()
        await self.db.commit()

        return {"debtor_id": debtor_id, "score": score, "tier": tier}

    async def recalculate_all(self) -> dict:
        """Пересчёт скоринга для всех должников компании. Вызывается из Celery."""
        q = select(Debtor.id).where(Debtor.deleted_at.is_(None))
        if self.company_id is not None:
            q = q.where(Debtor.company_id == self.company_id)
        ids = list((await self.db.execute(q)).scalars().all())
        for did in ids:
            await self.calculate(did)
        return {"updated": len(ids)}

    async def list_priority(self, tier: str | None = None, limit: int = 200, manager_id: int | None = None) -> list[dict]:
        """Список должников отсортированных по score desc."""
        from app.models.user import User
        q = (
            select(
                Debtor,
                func.coalesce(func.sum(Contract.total_debt), 0).label("total_debt"),
                User.full_name.label("manager_name"),
            )
            .outerjoin(Contract, and_(Contract.debtor_id == Debtor.id))
            .outerjoin(User, User.id == Debtor.assigned_manager_id)
            .where(Debtor.deleted_at.is_(None))
        )
        if self.company_id is not None:
            q = q.where(Debtor.company_id == self.company_id)
        if tier:
            q = q.where(Debtor.score_tier == tier)
        if manager_id:
            q = q.where(Debtor.assigned_manager_id == manager_id)
        q = q.group_by(Debtor.id, User.full_name).order_by(Debtor.score.desc().nullslast()).limit(limit)
        rows = (await self.db.execute(q)).all()

        out = []
        for debtor, total_debt, manager_name in rows:
            out.append({
                "id": debtor.id,
                "iin": debtor.iin,
                "full_name": debtor.full_name,
                "phone_primary": debtor.phone_primary,
                "score": debtor.score,
                "score_tier": debtor.score_tier,
                "score_calculated_at": debtor.score_calculated_at,
                "kanban_status": debtor.kanban_status,
                "total_debt": float(total_debt) if total_debt else 0,
                "manager_name": manager_name,
                "manager_id": debtor.assigned_manager_id,
            })
        return out

    async def tier_summary(self) -> dict:
        q = select(Debtor.score_tier, func.count()).where(Debtor.deleted_at.is_(None))
        if self.company_id is not None:
            q = q.where(Debtor.company_id == self.company_id)
        q = q.group_by(Debtor.score_tier)
        rows = (await self.db.execute(q)).all()
        by = {r[0]: r[1] for r in rows}
        return {
            "hot": by.get("hot", 0),
            "medium": by.get("medium", 0),
            "low": by.get("low", 0),
            "unscored": by.get(None, 0),
        }
