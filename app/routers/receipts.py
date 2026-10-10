from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.partner import Partner
from app.models.raw_material import RawMaterial
from app.models.raw_material_movement import RawMaterialMovement
from app.models.raw_material_receipt import RawMaterialReceipt as Receipt
from app.schemas.receipt import ReceiptCreate
from app.utils import bad_request, q2, q3

router = APIRouter(prefix="/receipts", tags=["Receipts"])


def _require(db: Session, model, pk, label):
    obj = db.get(model, pk)
    if not obj:
        raise HTTPException(404, f"{label} topilmadi")
    if not obj.active:
        raise bad_request(f"{label} faol emas")
    return obj


def _receipt_out(r: Receipt, partner: str, brand: str, unit: str) -> dict:
    price = float(r.unit_price) if r.unit_price is not None else None
    return {
        "id": r.id, "date": r.date, "partner_id": r.partner_id, "partner_name": partner,
        "raw_material_id": r.raw_material_id, "brand": brand, "unit": unit,
        "quantity": float(r.quantity), "unit_price": price,
        "total": round(float(r.quantity) * price, 2) if price is not None else None,
        "supplier_name": r.supplier_name, "payment_type": r.payment_type, "note": r.note,
    }


@router.get("")
def list_receipts(
    partner_id: int | None = None, raw_material_id: int | None = None,
    date_from: Date | None = None, date_to: Date | None = None, limit: int = 200,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Receipt, Partner.name, RawMaterial.brand, RawMaterial.unit)
        .join(Partner, Partner.id == Receipt.partner_id)
        .join(RawMaterial, RawMaterial.id == Receipt.raw_material_id)
    )
    if partner_id:
        stmt = stmt.where(Receipt.partner_id == partner_id)
    if raw_material_id:
        stmt = stmt.where(Receipt.raw_material_id == raw_material_id)
    if date_from:
        stmt = stmt.where(Receipt.date >= date_from)
    if date_to:
        stmt = stmt.where(Receipt.date <= date_to)
    stmt = stmt.order_by(Receipt.date.desc(), Receipt.id.desc()).limit(min(limit, 1000))
    return [_receipt_out(r, pn, b, u) for r, pn, b, u in db.execute(stmt)]


@router.post("", status_code=201)
def create_receipt(payload: ReceiptCreate, db: Session = Depends(get_db)):
    partner = _require(db, Partner, payload.partner_id, "Hamkor")
    rm = _require(db, RawMaterial, payload.raw_material_id, "Xomashyo")
    receipt = Receipt(
        partner_id=payload.partner_id, raw_material_id=payload.raw_material_id,
        quantity=q3(payload.quantity), date=payload.date,
        supplier_name=payload.supplier_name, payment_type=payload.payment_type,
        unit_price=q2(payload.unit_price) if payload.unit_price is not None else None,
        note=payload.note,
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return _receipt_out(receipt, partner.name, rm.brand, rm.unit)


@router.delete("/{receipt_id}")
def delete_receipt(receipt_id: int, db: Session = Depends(get_db)):
    r = db.get(Receipt, receipt_id)
    if not r:
        raise HTTPException(404, "Kirim topilmadi")
    # Eski ombor yozuvi (agar bo'lsa) kirimga bog'langan - avval u o'chiriladi
    db.execute(delete(RawMaterialMovement).where(RawMaterialMovement.receipt_id == receipt_id))
    db.delete(r)
    db.commit()
    return {"message": "Kirim o'chirildi"}
