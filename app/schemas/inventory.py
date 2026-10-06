from datetime import date as Date

from pydantic import BaseModel, Field, field_validator
from app.utils import today


class ReceiptCreate(BaseModel):
    partner_id: int
    raw_material_id: int
    quantity: float = Field(gt=0)
    date: Date = Field(default_factory=today)
    supplier_name: str | None = Field(default=None, max_length=150)
    payment_type: str | None = Field(default=None, max_length=30)
    unit_price: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)


class RawAdjustmentCreate(BaseModel):
    """Qoldiqni qo'lda to'g'rilash (inventarizatsiya, brak). Musbat - qo'shish, manfiy - ayirish."""
    partner_id: int
    raw_material_id: int
    quantity: float
    date: Date = Field(default_factory=today)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("quantity")
    @classmethod
    def non_zero(cls, v):
        if v == 0:
            raise ValueError("Miqdor 0 bo'lishi mumkin emas")
        return v


class ProductAdjustmentCreate(BaseModel):
    partner_id: int
    product_id: int
    quantity: float
    date: Date = Field(default_factory=today)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("quantity")
    @classmethod
    def non_zero(cls, v):
        if v == 0:
            raise ValueError("Miqdor 0 bo'lishi mumkin emas")
        return v
