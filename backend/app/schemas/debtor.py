from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DebtorBase(BaseModel):
    iin: str
    full_name: str
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class DebtorCreate(DebtorBase):
    pass


class DebtorUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class DebtorFilter(BaseModel):
    search: Optional[str] = None
    is_active: Optional[bool] = None
    contract_status: Optional[str] = None
    manager_id: Optional[int] = None
    debt_min: Optional[float] = None
    debt_max: Optional[float] = None
    page: int = 1
    page_size: int = 20


class DebtorResponse(DebtorBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
