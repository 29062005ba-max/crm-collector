from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from app.models.contract import ContractStatus
from app.models.operations import (
    CallResult, PromiseStatus, PaymentSource, CsiStatus
)


# --- Contract ---
class ContractBase(BaseModel):
    contract_number: str
    original_creditor: str
    product_type: Optional[str] = None
    principal_debt: Decimal
    interest_debt: Decimal = Decimal("0")
    penalty_debt: Decimal = Decimal("0")
    total_debt: Decimal
    currency: str = "KZT"
    issue_date: Optional[date] = None
    overdue_date: Optional[date] = None
    purchase_date: Optional[date] = None
    status: ContractStatus = ContractStatus.ACTIVE
    notes: Optional[str] = None


class ContractCreate(ContractBase):
    debtor_id: int


class ContractUpdate(BaseModel):
    original_creditor: Optional[str] = None
    product_type: Optional[str] = None
    principal_debt: Optional[Decimal] = None
    interest_debt: Optional[Decimal] = None
    penalty_debt: Optional[Decimal] = None
    total_debt: Optional[Decimal] = None
    status: Optional[ContractStatus] = None
    notes: Optional[str] = None


class ContractResponse(ContractBase):
    id: int
    debtor_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Promise ---
class PromiseCreate(BaseModel):
    contract_id: int
    promise_date: date
    amount: Decimal
    notes: Optional[str] = None


class PromiseUpdate(BaseModel):
    promise_date: Optional[date] = None
    amount: Optional[Decimal] = None
    status: Optional[PromiseStatus] = None
    notes: Optional[str] = None


class PromiseResponse(BaseModel):
    id: int
    contract_id: int
    promise_date: date
    amount: Decimal
    status: PromiseStatus
    notes: Optional[str]
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Payment ---
class PaymentCreate(BaseModel):
    contract_id: int
    amount: Decimal
    payment_date: date
    source: PaymentSource = PaymentSource.BANK
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    contract_id: int
    amount: Decimal
    payment_date: date
    source: PaymentSource
    reference: Optional[str]
    notes: Optional[str]
    receipt_path: Optional[str] = None
    registered_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Call Log ---
class CallLogCreate(BaseModel):
    contract_id: int
    called_at: datetime
    phone_number: str
    result: CallResult
    duration_seconds: Optional[int] = None
    notes: Optional[str] = None


class CallLogResponse(BaseModel):
    id: int
    contract_id: int
    manager_id: int
    called_at: datetime
    phone_number: str
    result: CallResult
    duration_seconds: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# --- CsiCase ---
class CsiCaseCreate(BaseModel):
    debtor_id: int
    case_number: Optional[str] = None
    filed_date: Optional[date] = None
    court_name: Optional[str] = None
    bailiff_name: Optional[str] = None
    status: CsiStatus = CsiStatus.PENDING
    amount_claimed: Optional[Decimal] = None
    notes: Optional[str] = None


class CsiCaseUpdate(BaseModel):
    case_number: Optional[str] = None
    filed_date: Optional[date] = None
    court_name: Optional[str] = None
    bailiff_name: Optional[str] = None
    status: Optional[CsiStatus] = None
    amount_claimed: Optional[Decimal] = None
    notes: Optional[str] = None


class CsiCaseResponse(CsiCaseCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Pagination ---
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int
