from datetime import date as Date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.production_report import ProductionReport
from app.schemas.production import ProductionCreate
from app.services import production as svc

router = APIRouter(prefix="/production", tags=["Production"])


@router.get("")
def list_reports(
    date_from: Date | None = None, date_to: Date | None = None,
    machine_id: int | None = None, limit: int = 200,
    db: Session = Depends(get_db),
):
    stmt = select(ProductionReport).options(*svc.eager_options())
    if date_from:
        stmt = stmt.where(ProductionReport.date >= date_from)
    if date_to:
        stmt = stmt.where(ProductionReport.date <= date_to)
    if machine_id:
        stmt = stmt.where(ProductionReport.machine_id == machine_id)
    stmt = stmt.order_by(ProductionReport.date.desc(), ProductionReport.id.desc()).limit(min(limit, 1000))
    return [svc.serialize(r) for r in db.scalars(stmt).all()]


@router.post("", status_code=201)
def create_report(payload: ProductionCreate, db: Session = Depends(get_db)):
    return svc.serialize(svc.create_production(db, payload))


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    return svc.serialize(svc.get_production(db, report_id))


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    svc.delete_production(db, report_id)
    return {"message": "Ishlab chiqarish hisoboti bekor qilindi"}
