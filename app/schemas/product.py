from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    unit: str = Field(default="dona", min_length=1, max_length=20)
    price: float = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    price: float | None = Field(default=None, ge=0)
    active: bool | None = None


class ProductOut(ORMModel):
    id: int
    name: str
    code: str | None
    unit: str
    price: float
    active: bool
    created_at: datetime
