from datetime import date as Date

from pydantic import BaseModel, Field
from app.utils import today


class ProductionItemIn(BaseModel):
    product_id: int
    partner_id: int
    quantity: float = Field(gt=0)


class ProductionCreate(BaseModel):
    date: Date = Field(default_factory=today)
    machine_id: int
    note: str | None = Field(default=None, max_length=500)
    items: list[ProductionItemIn] = Field(min_length=1)
    allow_negative: bool = Field(
        default=False,
        description="True bo'lsa xomashyo yetarli bo'lmasa ham qoldiq minusga tushishiga ruxsat",
    )


class ProductionPreviewIn(BaseModel):
    items: list[ProductionItemIn] = Field(min_length=1)
