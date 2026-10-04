from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MaterialUsage(Base):
    __tablename__ = "material_usage"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    production_id: Mapped[int] = mapped_column(
        ForeignKey("production_reports.id"),
        nullable=False
    )

    production_item_id: Mapped[int] = mapped_column(
        ForeignKey("production_items.id"),
        nullable=False
    )

    raw_material_id: Mapped[int] = mapped_column(
        ForeignKey("raw_materials.id"),
        nullable=False
    )

    partner_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id"),
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    raw_material = relationship("RawMaterial")
