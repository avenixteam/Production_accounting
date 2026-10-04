"""Machine va Customer schemalari."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MachineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class MachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None


class MachineOut(ORMModel):
    id: int
    name: str
    active: bool
    created_at: datetime


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=300)
    active: bool | None = None


class CustomerOut(ORMModel):
    id: int
    name: str
    phone: str | None
    address: str | None
    active: bool
    created_at: datetime
