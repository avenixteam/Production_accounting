from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductionItem(Base):
    __tablename__ = "production_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    production_id: Mapped[int] = mapped_column(
        ForeignKey("production_reports.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
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

    product = relationship("Product")
    partner = relationship("Partner")
    materials = relationship(
        "MaterialUsage",
        cascade="all, delete-orphan",
        order_by="MaterialUsage.id"
    )
