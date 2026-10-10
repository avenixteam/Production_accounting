from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    partner_id: Mapped[int | None] = mapped_column(
        ForeignKey("partners.id"),
        nullable=True
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )

    unit_price: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    total_price: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    product = relationship("Product")
    partner = relationship("Partner")
