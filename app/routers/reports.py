from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import reports as svc

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary")
def summary(date_from: Date | None = None, date_to: Date | None = None, db: Session = Depends(get_db)):
    """Dashboard va hisobotlar uchun umumiy ko'rsatkichlar. Standart davr - joriy oy."""
    d_from, d_to = svc.month_range()
    d_from, d_to = date_from or d_from, date_to or d_to
    if d_from > d_to:
        raise HTTPException(400, "Boshlanish sanasi tugash sanasidan keyin bo'lishi mumkin emas")
    if (d_to - d_from).days > 366:
        raise HTTPException(400, "Davr 1 yildan oshmasligi kerak")
    return svc.summary(db, d_from, d_to)
