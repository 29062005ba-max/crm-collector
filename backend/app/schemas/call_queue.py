"""Pydantic schemas for call queue module"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


# ============ Queue ============
class CallQueueCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    filter_overdue_min_days: Optional[int] = None
    filter_overdue_max_days: Optional[int] = None
    filter_debt_min: Optional[Decimal] = None
    filter_debt_max: Optional[Decimal] = None
    filter_contract_status: Optional[str] = None
    auto_assign_strategy: Literal["round_robin", "manual", "by_debt_size"] = "round_robin"
    max_attempts: int = Field(3, ge=1, le=10)
    retry_after_hours: int = Field(2, ge=1, le=72)


class CallQueueUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    max_attempts: Optional[int] = None
    retry_after_hours: Optional[int] = None
    auto_assign_strategy: Optional[str] = None


class CallQueueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    is_active: bool
    auto_assign_strategy: str
    max_attempts: int
    retry_after_hours: int
    created_at: datetime
    updated_at: datetime
    # вычисляемые
    total_items: Optional[int] = None
    pending_items: Optional[int] = None
    completed_items: Optional[int] = None


# ============ Queue items ============
class CallQueuePopulate(BaseModel):
    """Параметры наполнения очереди должниками"""
    manager_ids: Optional[list[int]] = None  # если задано — раскидать только между ними
    limit: int = Field(500, ge=1, le=10000)
    priority: int = 0


class CallQueueItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    queue_id: int
    debtor_id: int
    contract_id: Optional[int]
    assigned_manager_id: Optional[int]
    status: str
    priority: int
    attempt_count: int
    last_attempt_at: Optional[datetime]
    next_attempt_at: Optional[datetime]
    last_call_outcome: Optional[str]
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    # join-данные
    debtor_full_name: Optional[str] = None
    debtor_iin: Optional[str] = None
    debtor_phone_primary: Optional[str] = None
    debtor_phone_secondary: Optional[str] = None
    contract_number: Optional[str] = None
    total_debt: Optional[Decimal] = None
    manager_name: Optional[str] = None


# ============ Take next / submit result ============
class TakeNextRequest(BaseModel):
    queue_id: Optional[int] = None  # если None — берём из любой активной очереди


class CallResultSubmit(BaseModel):
    item_id: int
    outcome: Literal["reached", "not_reached", "promise", "callback", "refused", "wrong_number"]
    duration_seconds: Optional[int] = None
    phone_number: Optional[str] = None
    notes: Optional[str] = None
    # Для promise:
    promise_amount: Optional[Decimal] = None
    promise_date: Optional[date] = None
    # Для callback:
    callback_at: Optional[datetime] = None


class CallResultResponse(BaseModel):
    item_id: int
    new_status: str
    next_attempt_at: Optional[datetime] = None
    promise_id: Optional[int] = None
    task_id: Optional[int] = None
    message: str


# ============ Manager progress ============
class ManagerCallProgress(BaseModel):
    manager_id: int
    manager_name: str
    total_assigned: int
    completed_today: int
    reached_today: int
    not_reached_today: int
    promises_today: int
    pending: int
