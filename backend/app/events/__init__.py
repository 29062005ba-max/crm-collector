"""Event-driven architecture: domain events + dispatcher"""
from app.events.bus import EventBus, event_bus
from app.events.types import (
    DomainEvent,
    DebtorCreated,
    PaymentCreated,
    PromiseCreated,
    PaymentMissed,
    ScheduleOverdue,
    TaskCreated,
    StatusChanged,
)

__all__ = [
    "EventBus", "event_bus",
    "DomainEvent",
    "DebtorCreated", "PaymentCreated", "PromiseCreated",
    "PaymentMissed", "ScheduleOverdue", "TaskCreated", "StatusChanged",
]
