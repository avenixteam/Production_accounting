"""Kunlik hisobot uchun ma'lumot yig'ish (ma'lumotlar bazasidan).

Excel faylning o'zi `daily_excel.build_workbook()` da yaratiladi.

Ombor qoldig'i butun tarixdan harakatlar (movements) yig'indisi sifatida hisoblanadi:
  kun boshiga qoldiq  = sanadan OLDINGI harakatlar yig'indisi
  kun oxiriga qoldiq  = kun boshiga + shu kungi kirim − chiqim ± tuzatish
Shuning uchun o'tgan sana bilan (masalan, kecha) kiritilgan yozuv ham o'z kunining hisobotida to'g'ri ko'rinadi.
"""
from collections import defaultdict
from datetime import date as Date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.expense import Expense
from app.models.finished_product_movement import FinishedProductMovement as FPM
from app.models.partner import Partner
from app.models.product import Product
from app.models.production_report import ProductionReport
from app.models.raw_material import RawMaterial
from app.models.raw_material_movement import RawMaterialMovement as RMM
from app.models.raw_material_receipt import RawMaterialReceipt as Receipt
from app.models.sale import Sale
from app.services import production as production_svc
from app.services import sales as sales_svc
from app.services.daily_excel import build_workbook
from app.services.stock import FP_SIGNED, RAW_SIGNED
from app.utils import TZ, D

ZERO = Decimal("0")


def _stock_numbers(db: Session, d: Date, model, item_col, signed, in_type: str, out_type: str) -> list[tuple]:
    """(hamkor, element) kesimida: kun boshiga qoldiq, kirim, chiqim, tuzatish.

    Qaytaradi: [(partner_id, item_id, opening, incoming, outgoing, adjustment), ...]
    Hech qanday qoldig'i ham, shu kuni harakati ham bo'lmagan juftliklar tashlab yuboriladi.
    """
    partner_col = model.partner_id

    opening = {
        (p, i): D(v)
        for p, i, v in db.execute(
            select(partner_col, item_col, func.coalesce(func.sum(signed), 0))
            .where(model.date < d)
            .group_by(partner_col, item_col)
        )
    }

    day = defaultdict(lambda: defaultdict(Decimal))  # (hamkor, element) -> harakat turi -> miqdor
    for p, i, kind, qty in db.execute(
        select(partner_col, item_col, model.movement_type, func.coalesce(func.sum(model.quantity), 0))
        .where(model.date == d)
        .group_by(partner_col, item_col, model.movement_type)
    ):
        day[(p, i)][kind] += D(qty)

    rows = []
    for key in sorted(set(opening) | set(day)):
        moves = day.get(key, {})
        start = opening.get(key, ZERO)
        incoming = moves.get(in_type, ZERO)
        outgoing = moves.get(out_type, ZERO)
        adjustment = moves.get("adjustment", ZERO)
        if start == 0 and incoming == 0 and outgoing == 0 and adjustment == 0:
            continue
        rows.append((key[0], key[1], start, incoming, outgoing, adjustment))
    return rows


def _partner_names(db: Session, ids: set[int]) -> dict[int, str]:
    return {pid: name for pid, name in db.execute(select(Partner.id, Partner.name).where(Partner.id.in_(ids)))}


def _raw_rows(db: Session, d: Date) -> list[dict]:
    nums = _stock_numbers(db, d, RMM, RMM.raw_material_id, RAW_SIGNED, "receipt", "usage")
    if not nums:
        return []
    partners = _partner_names(db, {n[0] for n in nums})
    materials = {
        m.id: m for m in db.scalars(select(RawMaterial).where(RawMaterial.id.in_({n[1] for n in nums})))
    }
    rows = []
    for pid, rid, start, incoming, outgoing, adjustment in nums:
        m = materials[rid]
        rows.append({
            "partner_name": partners[pid],
            "label": f"{m.brand} — {m.name}" if m.name else m.brand,
            "unit": m.unit,
            "opening": start, "incoming": incoming, "outgoing": outgoing, "adjustment": adjustment,
        })
    return sorted(rows, key=lambda r: (r["partner_name"], r["label"]))


def _fp_rows(db: Session, d: Date) -> list[dict]:
    nums = _stock_numbers(db, d, FPM, FPM.product_id, FP_SIGNED, "production", "sale")
    if not nums:
        return []
    partners = _partner_names(db, {n[0] for n in nums})
    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_({n[1] for n in nums})))}
    rows = []
    for pid, prod_id, start, incoming, outgoing, adjustment in nums:
        p = products[prod_id]
        rows.append({
            "partner_name": partners[pid],
            "label": p.name,
            "unit": p.unit,
            "opening": start, "incoming": incoming, "outgoing": outgoing, "adjustment": adjustment,
        })
    return sorted(rows, key=lambda r: (r["partner_name"], r["label"]))


def collect(db: Session, d: Date) -> dict:
    """Bir kunlik hisobot uchun barcha ma'lumotni yig'adi."""
    reports = db.scalars(
        select(ProductionReport)
        .options(*production_svc.eager_options())
        .where(ProductionReport.date == d)
        .order_by(ProductionReport.id)
    ).all()

    sales = db.scalars(
        select(Sale).options(*sales_svc.eager_options()).where(Sale.date == d).order_by(Sale.id)
    ).all()

    expenses = db.scalars(select(Expense).where(Expense.date == d).order_by(Expense.id)).all()

    receipts = [
        {
            "id": r.id, "partner_name": partner, "brand": brand, "unit": unit,
            "quantity": r.quantity, "unit_price": r.unit_price,
            "supplier_name": r.supplier_name, "payment_type": r.payment_type, "note": r.note,
        }
        for r, partner, brand, unit in db.execute(
            select(Receipt, Partner.name, RawMaterial.brand, RawMaterial.unit)
            .join(Partner, Partner.id == Receipt.partner_id)
            .join(RawMaterial, RawMaterial.id == Receipt.raw_material_id)
            .where(Receipt.date == d)
            .order_by(Receipt.id)
        )
    ]

    return {
        "date": d,
        "generated_at": datetime.now(TZ),
        "production": [production_svc.serialize(r) for r in reports],
        "raw_rows": _raw_rows(db, d),
        "fp_rows": _fp_rows(db, d),
        "receipts": receipts,
        "sales": [sales_svc.serialize(s) for s in sales],
        "expenses": [
            {"id": e.id, "category": e.category, "description": e.description, "amount": e.amount}
            for e in expenses
        ],
    }


def build_excel(db: Session, d: Date) -> bytes:
    return build_workbook(collect(db, d))
