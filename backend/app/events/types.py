"""Domain events - типы бизнес-событий"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class DomainEvent:
    """Базовый класс для всех domain events"""
    event_type: str = ""
    aggregate_type: str = ""
    aggregate_id: int | None = None
    company_id: int | None = None
    actor_id: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    idempotency_key: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp
        return d


# ==================== Debtor Events ====================
@dataclass
class DebtorCreated(DomainEvent):
    event_type: str = "debtor.created"
    aggregate_type: str = "debtor"


@dataclass
class StatusChanged(DomainEvent):
    event_type: str = "status.changed"
    # payload: {entity_type, entity_id, old_status, new_status}


# ==================== Payment Events ====================
@dataclass
class PaymentCreated(DomainEvent):
    event_type: str = "payment.created"
    aggregate_type: str = "payment"
    # payload: {amount, source, contract_id, debtor_id}


@dataclass
class PaymentMissed(DomainEvent):
    event_type: str = "payment.missed"
    aggregate_type: str = "payment_schedule"
    # payload: {schedule_payment_id, due_date, amount}


# ==================== Promise Events ====================
@dataclass
class PromiseCreated(DomainEvent):
    event_type: str = "promise.created"
    aggregate_type: str = "promise"


@dataclass
class PromiseOverdue(DomainEvent):
    event_type: str = "promise.overdue"
    aggregate_type: str = "promise"


# ==================== Schedule Events ====================
@dataclass
class ScheduleOverdue(DomainEvent):
    event_type: str = "schedule.overdue"
    aggregate_type: str = "payment_schedule"


# ==================== Task Events ====================
@dataclass
class TaskCreated(DomainEvent):
    event_type: str = "task.created"
    aggregate_type: str = "task"
