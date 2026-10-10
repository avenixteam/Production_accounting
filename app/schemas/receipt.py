from datetime import date as Date

from pydantic import BaseModel, Field

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
