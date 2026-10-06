from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.finished_product_movement import FinishedProductMovement
from app.models.machine import Machine
from app.models.material_usage import MaterialUsage
from app.models.partner import Partner
from app.models.product import Product
from app.models.product_recipe import ProductRecipe
from app.models.production_item import ProductionItem
from app.models.production_report import ProductionReport
from app.models.raw_material import RawMaterial
from app.models.raw_material_movement import RawMaterialMovement
from app.services.stock import lock_partners, product_balance, raw_balances
from app.utils import D, bad_request, fmt, q3


# ---------- yordamchi ----------
def _get_active(db: Session, model, pk: int, label: str):
    obj = db.get(model, pk)
    if not obj:
        raise HTTPException(404, f"{label} topilmadi (id={pk})")
    if hasattr(obj, "active") and not obj.active:
        raise bad_request(f"{label} faol emas: {getattr(obj, 'name', pk)}")
    return obj


def _recipes(db: Session, product_ids: set[int]) -> dict[int, list[ProductRecipe]]:
    rows = db.scalars(
        select(ProductRecipe).where(ProductRecipe.product_id.in_(product_ids))
    ).all()
    result: dict[int, list[ProductRecipe]] = defaultdict(list)
    for r in rows:
        result[r.product_id].append(r)
    return result


def calculate_requirements(db: Session, items) -> dict:
    """Ishlab chiqarish uchun kerakli xomashyo, mavjud qoldiq va yetishmovchilikni hisoblaydi."""
    product_ids = {i.product_id for i in items}
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids)))}
    partners = {
        p.id: p for p in db.scalars(select(Partner).where(Partner.id.in_({i.partner_id for i in items})))
    }
    recipes = _recipes(db, product_ids)

    per_item = []  # [(item, product, [(rm_id, qty)])]
    need: dict[tuple[int, int], Decimal] = defaultdict(Decimal)

    for item in items:
        product = products.get(item.product_id)
        if not product:
            raise HTTPException(404, f"Mahsulot topilmadi (id={item.product_id})")
        if not product.active:
            raise bad_request(f"Mahsulot faol emas: {product.name}")
        if item.partner_id not in partners:
            raise HTTPException(404, f"Hamkor topilmadi (id={item.partner_id})")
        if not partners[item.partner_id].active:
            raise bad_request(f"Hamkor faol emas: {partners[item.partner_id].name}")
        recipe = recipes.get(product.id)
        if not recipe:
            raise bad_request(f"'{product.name}' uchun retsept kiritilmagan. Avval Mahsulotlar bo'limida retsept belgilang.")

        mats = []
        for line in recipe:
            qty = q3(D(line.quantity) * D(item.quantity))
            mats.append((line.raw_material_id, qty))
            need[(item.partner_id, line.raw_material_id)] += qty
        per_item.append((item, product, mats))

    rm_ids = {k[1] for k in need}
    raws = {r.id: r for r in db.scalars(select(RawMaterial).where(RawMaterial.id.in_(rm_ids)))}

    balances = raw_balances(db, need.keys())  # bitta so'rov (N+1 yo'q)
    lines = []
    for (partner_id, rm_id), required in sorted(need.items()):
        available = balances[(partner_id, rm_id)]
        rm = raws[rm_id]
        lines.append({
            "partner_id": partner_id,
            "partner_name": partners[partner_id].name,
            "raw_material_id": rm_id,
            "brand": rm.brand,
            "name": rm.name,
            "unit": rm.unit,
            "required": float(required),
            "available": float(available),
            "shortage": float(max(required - available, Decimal("0"))),
            "ok": available >= required,
        })
    return {"lines": lines, "ok": all(l["ok"] for l in lines), "_per_item": per_item}


# ---------- serializer ----------
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
                "materials": [
                    {
                        "raw_material_id": m.raw_material_id,
                        "brand": m.raw_material.brand,
                        "name": m.raw_material.name,
                        "unit": m.raw_material.unit,
                        "quantity": float(m.quantity),
                    }
                    for m in i.materials
                ],
            }
            for i in report.items
        ],
    }


def eager_options():
    return (
        selectinload(ProductionReport.machine),
        selectinload(ProductionReport.items).selectinload(ProductionItem.product),
        selectinload(ProductionReport.items).selectinload(ProductionItem.partner),
        selectinload(ProductionReport.items)
        .selectinload(ProductionItem.materials)
        .selectinload(MaterialUsage.raw_material),
    )


# ---------- amallar ----------
def create_production(db: Session, data) -> ProductionReport:
    _get_active(db, Machine, data.machine_id, "Stanok")
    lock_partners(db, {i.partner_id for i in data.items})  # parallel so'rovlardan himoya
    calc = calculate_requirements(db, data.items)

    if not calc["ok"] and not data.allow_negative:
        short = "; ".join(
            f"{l['partner_name']} — {l['brand']}: kerak {fmt(l['required'])}, mavjud {fmt(l['available'])} {l['unit']}"
            for l in calc["lines"] if not l["ok"]
        )
        raise bad_request(f"Xomashyo yetarli emas → {short}")

    report = ProductionReport(date=data.date, machine_id=data.machine_id, note=data.note)
    db.add(report)
    db.flush()

    for item, _product, mats in calc["_per_item"]:
        pi = ProductionItem(
            production_id=report.id,
            product_id=item.product_id,
            partner_id=item.partner_id,
            quantity=q3(item.quantity),
        )
        db.add(pi)
        db.flush()

        for rm_id, qty in mats:
            db.add(MaterialUsage(
                production_id=report.id, production_item_id=pi.id,
                raw_material_id=rm_id, partner_id=item.partner_id, quantity=qty,
            ))
            db.add(RawMaterialMovement(
                partner_id=item.partner_id, raw_material_id=rm_id,
                movement_type="usage", quantity=qty, date=data.date,
                production_id=report.id, note=f"Ishlab chiqarish #{report.id}",
            ))

        db.add(FinishedProductMovement(
            product_id=item.product_id, partner_id=item.partner_id,
            movement_type="production", quantity=q3(item.quantity), date=data.date,
            production_id=report.id, note=f"Ishlab chiqarish #{report.id}",
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
    """Hisobotni bekor qiladi: xomashyo qaytariladi, tayyor mahsulot ombordan olinadi.
    Agar ishlab chiqarilgan mahsulot allaqachon sotilgan bo'lsa - bekor qilib bo'lmaydi."""
    report = get_production(db, report_id)
    lock_partners(db, {i.partner_id for i in report.items})

    produced: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    for i in report.items:
        produced[(i.partner_id, i.product_id)] += D(i.quantity)

    for (partner_id, product_id), qty in produced.items():
        if product_balance(db, partner_id, product_id) < qty:
            p = db.get(Product, product_id)
            raise bad_request(
                f"Bekor qilib bo'lmaydi: '{p.name}' mahsuloti allaqachon sotilgan yoki ombordan chiqarilgan"
            )

    for m in db.scalars(select(RawMaterialMovement).where(RawMaterialMovement.production_id == report_id)):
        db.delete(m)
    for m in db.scalars(select(FinishedProductMovement).where(FinishedProductMovement.production_id == report_id)):
        db.delete(m)
    db.delete(report)  # items va material_usage cascade orqali o'chadi
    db.commit()
