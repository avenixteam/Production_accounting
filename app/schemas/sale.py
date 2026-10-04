from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field
from app.utils import today

PaymentType = Literal["cash", "card", "transfer", "installment"]


class SaleItemIn(BaseModel):
    product_id: int
    partner_id: int
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class InstallmentIn(BaseModel):
    due_date: Date
    amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class SaleCreate(BaseModel):
    customer_id: int
    date: Date = Field(default_factory=today)
    payment_type: PaymentType = "cash"
    note: str | None = Field(default=None, max_length=500)
    items: list[SaleItemIn] = Field(min_length=1)
    installments: list[InstallmentIn] = Field(default_factory=list)


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)
