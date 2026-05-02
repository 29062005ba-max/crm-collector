from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


def _norm_email(v: str) -> str:
    return v.lower().strip()

def _norm_role(v: str) -> str:
    return v.upper() if v else v


class UserBase(BaseModel):
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str = "MANAGER"


class UserCreate(UserBase):
    password: str

    @field_validator('role')
    @classmethod
    def normalize_role(cls, v: str) -> str:
        return _norm_role(v)


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator('role')
    @classmethod
    def normalize_role(cls, v: Optional[str]) -> Optional[str]:
        return _norm_role(v) if v else v


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserShort(BaseModel):
    id: int
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True
