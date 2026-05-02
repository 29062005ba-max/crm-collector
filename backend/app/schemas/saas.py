"""Pydantic schemas for SaaS features"""
from datetime import datetime, date
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ==================== Tasks ====================
class TaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    type: str = "followup"
    priority: str = "normal"
    due_date: datetime | None = None
    assignee_id: int | None = None
    debtor_id: int | None = None
    contract_id: int | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    assignee_id: int | None = None


class TaskResponse(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    created_by_id: int | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskWithDebtor(TaskResponse):
    debtor_name: str | None = None
    contract_number: str | None = None
    assignee_name: str | None = None


# ==================== Notifications ====================
class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    message: str | None
    link: str | None
    is_read: bool
    related_debtor_id: int | None
    related_task_id: int | None
    created_at: datetime


# ==================== Activity Logs ====================
class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int | None
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: int | None
    description: str | None
    changes: dict[str, Any] | None = None
    debtor_id: int | None
    created_at: datetime


# ==================== Payment Schedules ====================
class SchedulePaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    payment_number: int
    due_date: date
    amount: Decimal
    paid_amount: Decimal
    status: str
    paid_at: date | None


class PaymentScheduleCreate(BaseModel):
    contract_id: int
    total_amount: Decimal
    down_payment: Decimal = Decimal(0)
    months: int = Field(..., ge=1, le=60)
    monthly_payment: Decimal
    start_date: date
    notes: str | None = None


class PaymentScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int
    total_amount: Decimal
    down_payment: Decimal
    months: int
    monthly_payment: Decimal
    start_date: date
    status: str
    notes: str | None
    created_by_id: int | None
    created_at: datetime
    payments: list[SchedulePaymentResponse] = []


# ==================== Kanban / Assignment ====================
class AssignManagerRequest(BaseModel):
    manager_id: int | None  # None = unassign


class KanbanStatusUpdate(BaseModel):
    kanban_status: str


# ==================== Manager KPI ====================
class ManagerKPI(BaseModel):
    manager_id: int
    manager_name: str
    debtors_count: int
    active_promises: int
    overdue_promises: int
    promises_kept_count: int
    payments_this_month: Decimal
    payments_count: int
    active_schedules: int
    overdue_schedules: int
    completion_rate: float  # % выполненных обещаний


class DashboardKPI(BaseModel):
    total_debtors: int
    debtors_by_kanban: dict[str, int]
    promises_today: int
    promises_today_amount: Decimal
    promises_overdue: int
    active_schedules: int
    overdue_schedules: int
    payments_today: Decimal
    payments_this_week: Decimal
    payments_this_month: Decimal
    daily_collections: list[dict[str, Any]]  # last 30 days
