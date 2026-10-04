"""Ombor qoldig'i hisob-kitobi.

Qoldiq alohida saqlanmaydi - har doim harakatlar (movements) yig'indisidan hisoblanadi.
Shu sababli qoldiq hech qachon harakatlar jurnaliga zid kelmaydi (single source of truth).
"""
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.finished_product_movement import FinishedProductMovement as FPM
from app.models.raw_material_movement import RawMaterialMovement as RMM
from app.utils import D

# Xomashyo: kirim (+), ishlatilgan (-), tuzatish (ishorali)
RAW_SIGNED = case(
    (RMM.movement_type.in_(["receipt", "adjustment"]), RMM.quantity),
    (RMM.movement_type == "usage", -RMM.quantity),
    else_=0,
)

# Tayyor mahsulot: ishlab chiqarildi (+), sotildi (-), tuzatish (ishorali)
FP_SIGNED = case(
    (FPM.movement_type.in_(["production", "adjustment"]), FPM.quantity),
    (FPM.movement_type == "sale", -FPM.quantity),
    else_=0,
)


def raw_balance(db: Session, partner_id: int, raw_material_id: int) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(RAW_SIGNED), 0)).where(
            RMM.partner_id == partner_id,
            RMM.raw_material_id == raw_material_id,
        )
    )
    return D(value)


def product_balance(db: Session, partner_id: int, product_id: int) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(FP_SIGNED), 0)).where(
            FPM.partner_id == partner_id,
            FPM.product_id == product_id,
        )
    )
    return D(value)


def raw_balances(db: Session, pairs) -> dict[tuple[int, int], Decimal]:
    """Bir nechta (partner_id, raw_material_id) uchun qoldiqni BITTA so'rovda hisoblaydi."""
    pairs = set(pairs)
    if not pairs:
        return {}
    rows = db.execute(
        select(RMM.partner_id, RMM.raw_material_id, func.coalesce(func.sum(RAW_SIGNED), 0))
        .where(
            RMM.partner_id.in_({p for p, _ in pairs}),
            RMM.raw_material_id.in_({r for _, r in pairs}),
        )
        .group_by(RMM.partner_id, RMM.raw_material_id)
    )
    found = {(p, r): D(v) for p, r, v in rows}
    return {k: found.get(k, Decimal("0")) for k in pairs}


def product_balances(db: Session, pairs) -> dict[tuple[int, int], Decimal]:
    """Bir nechta (partner_id, product_id) uchun tayyor mahsulot qoldig'i - bitta so'rovda."""
    pairs = set(pairs)
    if not pairs:
        return {}
    rows = db.execute(
        select(FPM.partner_id, FPM.product_id, func.coalesce(func.sum(FP_SIGNED), 0))
        .where(
            FPM.partner_id.in_({p for p, _ in pairs}),
            FPM.product_id.in_({r for _, r in pairs}),
        )
        .group_by(FPM.partner_id, FPM.product_id)
    )
    found = {(p, r): D(v) for p, r, v in rows}
    return {k: found.get(k, Decimal("0")) for k in pairs}


def lock_partners(db: Session, partner_ids) -> None:
    """Hamkor qatorlarini bloklaydi (SELECT ... FOR UPDATE), id tartibida - deadlock bo'lmasligi uchun.

    Bir vaqtda ikki kishi bir xil ombor qoldig'idan foydalanmoqchi bo'lsa, ikkinchisi
    birinchisi tugaguncha kutadi va yangilangan qoldiqni ko'radi (qoldiq minusga tushmaydi).
    Qulf tranzaksiya commit/rollback bo'lganda o'zi bo'shaydi. SQLite'da (testlar) hech narsa qilmaydi.
    """
    from app.models.partner import Partner

    ids = sorted({int(i) for i in partner_ids})
    if ids:
        db.execute(select(Partner.id).where(Partner.id.in_(ids)).order_by(Partner.id).with_for_update()).all()
