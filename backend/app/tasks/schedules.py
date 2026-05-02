"""Schedule-related background tasks"""
import asyncio
import logging
from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.tasks._async_helper import track_job

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.schedules.recalculate_schedule_status",
    queue="schedule_queue",
    autoretry_for=(Exception,),
    max_retries=3,
)
@track_job(task_name="recalculate_schedule_status", queue="schedule_queue")
def recalculate_schedule_status(self, schedule_id: int):
    """Пересчитать статус графика после получения платежа.
    Если все платежи paid → status='completed'.
    Если есть просроченные → могут быть triggered другие действия."""
    return asyncio.run(_recalc(schedule_id))


async def _recalc(schedule_id: int) -> dict:
    from sqlalchemy import select
    from app.models import PaymentSchedule, SchedulePayment

    async with AsyncSessionLocal() as db:
        try:
            schedule = await db.get(PaymentSchedule, schedule_id)
            if not schedule:
                return {"error": "schedule not found"}

            payments = (await db.execute(
                select(SchedulePayment).where(SchedulePayment.schedule_id == schedule_id)
            )).scalars().all()

            paid = sum(1 for p in payments if p.status == "paid")
            total = len(payments)

            new_status = schedule.status
            if paid == total and total > 0:
                new_status = "completed"

            if new_status != schedule.status:
                schedule.status = new_status
                await db.commit()
                logger.info(f"Schedule {schedule_id}: status → {new_status}")

            return {"schedule_id": schedule_id, "status": new_status, "paid": paid, "total": total}
        except Exception:
            await db.rollback()
            raise
