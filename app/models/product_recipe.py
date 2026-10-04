from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProductRecipe(Base):
    __tablename__ = "product_recipes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    raw_material_id: Mapped[int] = mapped_column(
        ForeignKey("raw_materials.id"),
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 6),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )