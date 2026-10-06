from datetime import date as _Date, datetime as _DateTime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

TZ = ZoneInfo("Asia/Tashkent")

Q3 = Decimal("0.001")
Q2 = Decimal("0.01")


def D(value) -> Decimal:
    """Float/str/Decimal -> Decimal (float xatoliklarisiz)."""
    if value is None:
        return Decimal("0")
    return value if isinstance(value, Decimal) else Decimal(str(value))


def q3(value) -> Decimal:
    return D(value).quantize(Q3, rounding=ROUND_HALF_UP)


def q2(value) -> Decimal:
    return D(value).quantize(Q2, rounding=ROUND_HALF_UP)


def fmt(value) -> str:
    """Xabarlar uchun chiroyli son: 12.500 -> 12.5"""
    s = f"{D(value):.3f}".rstrip("0").rstrip(".")
    return s or "0"


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail=message)


def commit_or_409(db: Session) -> None:
    """commit; unikal cheklov buzilsa 409 qaytaradi."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Bunday qiymat allaqachon mavjud yoki bog'liq yozuvlar bor",
        ) from exc


def today() -> _Date:
    """Bugungi sana - server vaqt zonasidan qat'i nazar Toshkent vaqti bo'yicha."""
    return _DateTime.now(TZ).date()
