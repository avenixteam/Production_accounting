from datetime import date as Date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.finished_product_movement import FinishedProductMovement as FPM
from app.models.partner import Partner
from app.models.product import Product
from app.models.raw_material import RawMaterial
from app.models.raw_material_movement import RawMaterialMovement as RMM
from app.models.raw_material_receipt import RawMaterialReceipt as Receipt
from app.schemas.inventory import ProductAdjustmentCreate, RawAdjustmentCreate, ReceiptCreate
from app.services.stock import FP_SIGNED, RAW_SIGNED, lock_partners, product_balance, raw_balance
from app.utils import D, bad_request, fmt, q2, q3

router = APIRouter(prefix="/inventory", tags=["Inventory"])


def _require(db: Session, model, pk, label):
    obj = db.get(model, pk)
    if not obj:
        raise HTTPException(404, f"{label} topilmadi")
    if not obj.active:
        raise bad_request(f"{label} faol emas")
    return obj


# ---------------- Qoldiqlar ----------------
@router.get("/raw-materials")
def raw_material_balances(partner_id: int | None = None, include_zero: bool = False, db: Session = Depends(get_db)):
    bal = func.coalesce(func.sum(RAW_SIGNED), 0)
    stmt = (
        select(RMM.partner_id, Partner.name, RMM.raw_material_id, RawMaterial.brand, RawMaterial.name, RawMaterial.unit, bal)
        .join(Partner, Partner.id == RMM.partner_id)
        .join(RawMaterial, RawMaterial.id == RMM.raw_material_id)
        .group_by(RMM.partner_id, Partner.name, RMM.raw_material_id, RawMaterial.brand, RawMaterial.name, RawMaterial.unit)
        .order_by(Partner.name, RawMaterial.brand)
    )
    if partner_id:
        stmt = stmt.where(RMM.partner_id == partner_id)
    rows = [
        {"partner_id": pid, "partner_name": pn, "raw_material_id": rid, "brand": brand,
         "name": name, "unit": unit, "balance": float(b)}
        for pid, pn, rid, brand, name, unit, b in db.execute(stmt)
    ]
    return rows if include_zero else [r for r in rows if r["balance"] != 0]


@router.get("/finished-products")
def finished_product_balances(partner_id: int | None = None, include_zero: bool = False, db: Session = Depends(get_db)):
    bal = func.coalesce(func.sum(FP_SIGNED), 0)
    stmt = (
        select(FPM.partner_id, Partner.name, FPM.product_id, Product.name, Product.code, Product.unit, Product.price, bal)
        .join(Partner, Partner.id == FPM.partner_id)
        .join(Product, Product.id == FPM.product_id)
        .group_by(FPM.partner_id, Partner.name, FPM.product_id, Product.name, Product.code, Product.unit, Product.price)
        .order_by(Partner.name, Product.name)
    )
    if partner_id:
        stmt = stmt.where(FPM.partner_id == partner_id)
    rows = [
        {"partner_id": pid, "partner_name": pn, "product_id": prid, "product_name": name,
         "code": code, "unit": unit, "price": float(price), "balance": float(b)}
        for pid, pn, prid, name, code, unit, price, b in db.execute(stmt)
    ]
    return rows if include_zero else [r for r in rows if r["balance"] != 0]


# ---------------- Harakatlar jurnali ----------------
@router.get("/raw-materials/movements")
def raw_material_movements(
    partner_id: int | None = None, raw_material_id: int | None = None,
    date_from: Date | None = None, date_to: Date | None = None, limit: int = 200,
    db: Session = Depends(get_db),
):
    stmt = (
        select(RMM, Partner.name, RawMaterial.brand, RawMaterial.unit)
        .join(Partner, Partner.id == RMM.partner_id)
        .join(RawMaterial, RawMaterial.id == RMM.raw_material_id)
    )
    if partner_id:
        stmt = stmt.where(RMM.partner_id == partner_id)
    if raw_material_id:
        stmt = stmt.where(RMM.raw_material_id == raw_material_id)
    if date_from:
        stmt = stmt.where(RMM.date >= date_from)
    if date_to:
        stmt = stmt.where(RMM.date <= date_to)
    stmt = stmt.order_by(RMM.date.desc(), RMM.id.desc()).limit(min(limit, 1000))
    return [
        {"id": m.id, "date": m.date, "partner_id": m.partner_id, "partner_name": pn,
         "raw_material_id": m.raw_material_id, "brand": brand, "unit": unit,
         "movement_type": m.movement_type, "quantity": float(m.quantity),
         "production_id": m.production_id, "receipt_id": m.receipt_id, "note": m.note}
        for m, pn, brand, unit in db.execute(stmt)
    ]


@router.get("/finished-products/movements")
def finished_product_movements(
    partner_id: int | None = None, product_id: int | None = None,
    date_from: Date | None = None, date_to: Date | None = None, limit: int = 200,
    db: Session = Depends(get_db),
):
    stmt = (
        select(FPM, Partner.name, Product.name, Product.unit)
        .join(Partner, Partner.id == FPM.partner_id)
        .join(Product, Product.id == FPM.product_id)
    )
    if partner_id:
        stmt = stmt.where(FPM.partner_id == partner_id)
    if product_id:
        stmt = stmt.where(FPM.product_id == product_id)
    if date_from:
        stmt = stmt.where(FPM.date >= date_from)
    if date_to:
        stmt = stmt.where(FPM.date <= date_to)
    stmt = stmt.order_by(FPM.date.desc(), FPM.id.desc()).limit(min(limit, 1000))
    return [
        {"id": m.id, "date": m.date, "partner_id": m.partner_id, "partner_name": pn,
         "product_id": m.product_id, "product_name": prod, "unit": unit,
         "movement_type": m.movement_type, "quantity": float(m.quantity),
         "production_id": m.production_id, "sale_id": m.sale_id, "note": m.note}
        for m, pn, prod, unit in db.execute(stmt)
    ]


# ---------------- Xomashyo kirimi ----------------
def _receipt_out(r: Receipt, partner: str, brand: str, unit: str) -> dict:
    price = float(r.unit_price) if r.unit_price is not None else None
    return {
        "id": r.id, "date": r.date, "partner_id": r.partner_id, "partner_name": partner,
        "raw_material_id": r.raw_material_id, "brand": brand, "unit": unit,
        "quantity": float(r.quantity), "unit_price": price,
        "total": round(float(r.quantity) * price, 2) if price is not None else None,
        "supplier_name": r.supplier_name, "payment_type": r.payment_type, "note": r.note,
    }


@router.get("/receipts")
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


@router.post("/receipts", status_code=201)
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
    db.flush()
    db.add(RMM(
        partner_id=payload.partner_id, raw_material_id=payload.raw_material_id,
        movement_type="receipt", quantity=q3(payload.quantity), date=payload.date,
        receipt_id=receipt.id, note=payload.note or f"Kirim #{receipt.id}",
    ))
    db.commit()
    db.refresh(receipt)
    return _receipt_out(receipt, partner.name, rm.brand, rm.unit)


@router.delete("/receipts/{receipt_id}")
def delete_receipt(receipt_id: int, db: Session = Depends(get_db)):
    r = db.get(Receipt, receipt_id)
    if not r:
        raise HTTPException(404, "Kirim topilmadi")
    lock_partners(db, [r.partner_id])
    if raw_balance(db, r.partner_id, r.raw_material_id) < D(r.quantity):
        raise bad_request("Kirimni o'chirib bo'lmaydi: bu xomashyo allaqachon ishlatilgan (qoldiq minusga tushadi)")
    for m in db.scalars(select(RMM).where(RMM.receipt_id == receipt_id)):
        db.delete(m)
    db.delete(r)
    db.commit()
    return {"message": "Kirim o'chirildi"}


# ---------------- Qo'lda tuzatish ----------------
@router.post("/raw-materials/adjust", status_code=201)
def adjust_raw(payload: RawAdjustmentCreate, db: Session = Depends(get_db)):
    _require(db, Partner, payload.partner_id, "Hamkor")
    _require(db, RawMaterial, payload.raw_material_id, "Xomashyo")
    qty = q3(payload.quantity)
    lock_partners(db, [payload.partner_id])
    if raw_balance(db, payload.partner_id, payload.raw_material_id) + qty < 0:
        raise bad_request("Tuzatishdan keyin qoldiq manfiy bo'lib qoladi")
    db.add(RMM(partner_id=payload.partner_id, raw_material_id=payload.raw_material_id,
               movement_type="adjustment", quantity=qty, date=payload.date,
               note=payload.note or "Qo'lda tuzatish"))
    db.commit()
    return {"message": "Qoldiq tuzatildi"}


@router.post("/finished-products/adjust", status_code=201)
def adjust_product(payload: ProductAdjustmentCreate, db: Session = Depends(get_db)):
    _require(db, Partner, payload.partner_id, "Hamkor")
    _require(db, Product, payload.product_id, "Mahsulot")
    qty = q3(payload.quantity)
    lock_partners(db, [payload.partner_id])
    if product_balance(db, payload.partner_id, payload.product_id) + qty < 0:
        raise bad_request("Tuzatishdan keyin qoldiq manfiy bo'lib qoladi")
    db.add(FPM(partner_id=payload.partner_id, product_id=payload.product_id,
               movement_type="adjustment", quantity=qty, date=payload.date,
               note=payload.note or "Qo'lda tuzatish"))
    db.commit()
    return {"message": "Qoldiq tuzatildi"}
