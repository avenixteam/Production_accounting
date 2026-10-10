from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field

from app.utils import today

# To'liq - to'langan; qisman - bir qismi to'langan, qolgani qarz; nasiya - hali hech narsa to'lanmagan
PaymentType = Literal["full", "partial", "credit"]


class SaleItemIn(BaseModel):
    product_id: int
    partner_id: int | None = None
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class SaleCreate(BaseModel):
    customer_id: int
    date: Date = Field(default_factory=today)
    payment_type: PaymentType = "full"
    paid_amount: float | None = Field(
        default=None, ge=0,
        description="Faqat 'qisman' uchun: hozir to'langan summa (0 dan katta, jami summadan kichik)",
    )
    note: str | None = Field(default=None, max_length=500)
    items: list[SaleItemIn] = Field(min_length=1)


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)
    date: Date = Field(default_factory=today)
    note: str | None = Field(default=None, max_length=500)
