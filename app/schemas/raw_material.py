from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class RawMaterialCreate(BaseModel):
    brand: str = Field(min_length=1, max_length=100)
    name: str | None = Field(default=None, max_length=150)
    unit: str = Field(default="kg", min_length=1, max_length=20)


class RawMaterialUpdate(BaseModel):
    brand: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, max_length=150)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    active: bool | None = None


class RawMaterialOut(ORMModel):
    id: int
    brand: str
    name: str | None
    unit: str
    active: bool
    created_at: datetime
