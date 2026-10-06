from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentSchedule(Base):
    __tablename__ = "payment_schedule"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id"),
        nullable=False
    )

    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    paid_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
        nullable=False
    )

    paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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