from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PartnerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)


class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    active: bool | None = None


class PartnerOut(ORMModel):
    id: int
    name: str
    phone: str | None
    active: bool
    created_at: datetime
