from datetime import date as Date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.utils import today


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    date: Date = Field(default_factory=today)
    description: str | None = Field(default=None, max_length=500)


class ExpenseUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0)
    date: Date | None = None
    description: str | None = Field(default=None, max_length=500)


class ExpenseOut(ORMModel):
    id: int
    category: str
    amount: float
    date: Date
    description: str | None
    created_at: datetime
