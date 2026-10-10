from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    payment_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False
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

    customer = relationship("Customer")
    items = relationship(
        "SaleItem",
        cascade="all, delete-orphan",
        order_by="SaleItem.id"
    )
    payments = relationship(
        "SalePayment",
        cascade="all, delete-orphan",
        order_by="SalePayment.date, SalePayment.id"
    )
    # Eski muddatli to'lov jadvali: endi ishlatilmaydi, faqat eski yozuvlar sotuv bilan birga o'chishi uchun
    schedule = relationship(
        "PaymentSchedule",
        cascade="all, delete-orphan",
        order_by="PaymentSchedule.due_date"
    )
