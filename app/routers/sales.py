from datetime import date as Date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sale import Sale
from app.schemas.sale import PaymentIn, SaleCreate
from app.services import reports
from app.services import sales as svc

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("")
def list_sales(
    date_from: Date | None = None, date_to: Date | None = None,
    customer_id: int | None = None, status: str | None = None, limit: int = 200, offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Sale).options(*svc.eager_options())
    if date_from:
        stmt = stmt.where(Sale.date >= date_from)
    if date_to:
        stmt = stmt.where(Sale.date <= date_to)
    if customer_id:
        stmt = stmt.where(Sale.customer_id == customer_id)
    if status:
        cond = svc.status_filter(status)
        if cond is not None:
            stmt = stmt.where(cond)
    stmt = stmt.order_by(Sale.date.desc(), Sale.id.desc()).limit(min(limit, 1000)).offset(max(offset, 0))
    return [svc.serialize(s) for s in db.scalars(stmt).all()]


@router.get("/debts")
def customer_debts(db: Session = Depends(get_db)):
    return reports.debts(db)


@router.post("", status_code=201)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db)):
    return svc.serialize(svc.create_sale(db, payload))


@router.get("/{sale_id}")
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    return svc.serialize(svc.get_sale(db, sale_id))


@router.post("/{sale_id}/payments")
def add_payment(sale_id: int, payload: PaymentIn, db: Session = Depends(get_db)):
    return svc.serialize(svc.add_payment(db, sale_id, payload.amount, payload.date, payload.note))


@router.delete("/{sale_id}")
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    svc.delete_sale(db, sale_id)
    return {"message": "Sotuv bekor qilindi"}
