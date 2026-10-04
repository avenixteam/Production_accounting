from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RawMaterialReceipt(Base):
    __tablename__ = "raw_material_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id"),
        nullable=False
    )

    raw_material_id: Mapped[int] = mapped_column(
        ForeignKey("raw_materials.id"),
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )

    unit_price: Mapped[float | None] = mapped_column(
        Numeric(14, 2),
        nullable=True
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    supplier_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True
    )

    payment_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )