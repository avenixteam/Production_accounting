from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.finished_product_movement import FinishedProductMovement
from app.models.machine import Machine
from app.models.partner import Partner
from app.models.product import Product
from app.models.production_item import ProductionItem
from app.models.production_report import ProductionReport
from app.models.raw_material_movement import RawMaterialMovement
from app.utils import D, bad_request, q3


def _get_active(db: Session, model, pk: int, label: str):
    obj = db.get(model, pk)
    if not obj:
        raise HTTPException(404, f"{label} topilmadi (id={pk})")
    if hasattr(obj, "active") and not obj.active:
        raise bad_request(f"{label} faol emas: {getattr(obj, 'name', pk)}")
    return obj


def serialize(report: ProductionReport) -> dict:
    return {
        "id": report.id,
        "date": report.date,
        "machine_id": report.machine_id,
        "machine_name": report.machine.name if report.machine else None,
        "note": report.note,
        "created_at": report.created_at,
        "total_quantity": float(sum(D(i.quantity) for i in report.items)),
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name,
                "unit": i.product.unit,
                "partner_id": i.partner_id,
                "partner_name": i.partner.name,
                "quantity": float(i.quantity),
            }
            for i in report.items
        ],
    }


def eager_options():
    return (
        selectinload(ProductionReport.machine),
        selectinload(ProductionReport.items).selectinload(ProductionItem.product),
        selectinload(ProductionReport.items).selectinload(ProductionItem.partner),
    )


def create_production(db: Session, data) -> ProductionReport:
    """Kunlik ishlab chiqarish hisoboti: qaysi stanokda, nima, kimning nomiga, qancha."""
    _get_active(db, Machine, data.machine_id, "Stanok")
    for it in data.items:
        _get_active(db, Product, it.product_id, "Mahsulot")
        _get_active(db, Partner, it.partner_id, "Hamkor")

    report = ProductionReport(date=data.date, machine_id=data.machine_id, note=data.note)
    db.add(report)
    db.flush()
    for it in data.items:
        db.add(ProductionItem(
            production_id=report.id, product_id=it.product_id,
            partner_id=it.partner_id, quantity=q3(it.quantity),
        ))
    db.commit()
    return get_production(db, report.id)


def get_production(db: Session, report_id: int) -> ProductionReport:
    report = db.scalar(
        select(ProductionReport).options(*eager_options()).where(ProductionReport.id == report_id)
    )
    if not report:
        raise HTTPException(404, "Ishlab chiqarish hisoboti topilmadi")
    return report


def delete_production(db: Session, report_id: int) -> None:
    report = get_production(db, report_id)
    # Eski ombor yozuvlari (agar bo'lsa) hisobotga bog'langan - avval ular o'chiriladi
    db.execute(delete(RawMaterialMovement).where(RawMaterialMovement.production_id == report_id))
    db.execute(delete(FinishedProductMovement).where(FinishedProductMovement.production_id == report_id))
    db.delete(report)  # mahsulotlar (va eski sarf yozuvlari) cascade orqali o'chadi
    db.commit()
