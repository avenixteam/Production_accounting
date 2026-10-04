from collections import defaultdict
from datetime import date as Date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.finished_product_movement import FinishedProductMovement
from app.models.partner import Partner
from app.models.payment_schedule import PaymentSchedule
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.services.stock import lock_partners, product_balances
from app.utils import D, bad_request, fmt, q2, q3, today as _today


def eager_options():
    return (
        selectinload(Sale.customer),
        selectinload(Sale.items).selectinload(SaleItem.product),
        selectinload(Sale.items).selectinload(SaleItem.partner),
        selectinload(Sale.schedule),
    )


def paid_and_debt(sale: Sale) -> tuple[Decimal, Decimal]:
    total = D(sale.total_amount)
    if sale.payment_type != "installment":
        return total, Decimal("0")
    paid = sum((D(s.paid_amount) for s in sale.schedule), Decimal("0"))
    return paid, max(total - paid, Decimal("0"))


def sale_status(sale: Sale, today: Date | None = None) -> str:
    today = today or _today()
    paid, debt = paid_and_debt(sale)
    if debt <= 0:
        return "paid"
    if any((not s.paid) and s.due_date < today for s in sale.schedule):
        return "overdue"
    return "partial" if paid > 0 else "unpaid"


def serialize(sale: Sale) -> dict:
    paid, debt = paid_and_debt(sale)
    return {
        "id": sale.id,
        "date": sale.date,
        "customer_id": sale.customer_id,
        "customer_name": sale.customer.name if sale.customer else None,
        "payment_type": sale.payment_type,
        "total_amount": float(sale.total_amount),
        "paid_amount": float(paid),
        "debt": float(debt),
        "status": sale_status(sale),
        "note": sale.note,
        "created_at": sale.created_at,
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name,
                "unit": i.product.unit,
                "partner_id": i.partner_id,
                "partner_name": i.partner.name,
                "quantity": float(i.quantity),
                "unit_price": float(i.unit_price),
                "total_price": float(i.total_price),
            }
            for i in sale.items
        ],
        "schedule": [
            {
                "id": s.id,
                "due_date": s.due_date,
                "amount": float(s.amount),
                "paid_amount": float(s.paid_amount),
                "paid": s.paid,
                "note": s.note,
                "overdue": (not s.paid) and s.due_date < _today(),
            }
            for s in sale.schedule
        ],
    }


def get_sale(db: Session, sale_id: int) -> Sale:
    sale = db.scalar(select(Sale).options(*eager_options()).where(Sale.id == sale_id))
    if not sale:
        raise HTTPException(404, "Sotuv topilmadi")
    return sale


def create_sale(db: Session, data) -> Sale:
    customer = db.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(404, "Mijoz topilmadi")
    if not customer.active:
        raise bad_request("Mijoz faol emas")

    products = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_({i.product_id for i in data.items})))}
    partners = {p.id: p for p in db.scalars(select(Partner).where(Partner.id.in_({i.partner_id for i in data.items})))}

    wanted: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
    total = Decimal("0")
    rows = []
    for it in data.items:
        if it.product_id not in products:
            raise HTTPException(404, f"Mahsulot topilmadi (id={it.product_id})")
        if it.partner_id not in partners:
            raise HTTPException(404, f"Hamkor topilmadi (id={it.partner_id})")
        qty = q3(it.quantity)
        line_total = q2(qty * D(it.unit_price))
        total += line_total
        wanted[(it.partner_id, it.product_id)] += qty
        rows.append((it, qty, line_total))

    # Tayyor mahsulot yetarlimi? (avval hamkorlarni bloklaymiz - parallel sotuvdan himoya)
    lock_partners(db, {pid for pid, _ in wanted})
    balances = product_balances(db, wanted.keys())
    for (partner_id, product_id), qty in wanted.items():
        bal = balances[(partner_id, product_id)]
        if bal < qty:
            raise bad_request(
                f"Omborda yetarli mahsulot yo'q → {products[product_id].name} ({partners[partner_id].name}): "
                f"kerak {fmt(qty)}, mavjud {fmt(bal)} {products[product_id].unit}"
            )

    # Muddatli to'lov jadvali
    schedule_rows = []
    if data.payment_type == "installment":
        if not data.installments:
            raise bad_request("Muddatli to'lov uchun kamida bitta to'lov muddati kiriting")
        s = sum((q2(x.amount) for x in data.installments), Decimal("0"))
        if s != total:
            raise bad_request(
                f"To'lov jadvali yig'indisi ({fmt(s)}) sotuv summasiga ({fmt(total)}) teng bo'lishi kerak"
            )
        schedule_rows = data.installments

    sale = Sale(
        customer_id=data.customer_id, date=data.date, payment_type=data.payment_type,
        total_amount=total, note=data.note,
    )
    db.add(sale)
    db.flush()

    for it, qty, line_total in rows:
        db.add(SaleItem(
            sale_id=sale.id, product_id=it.product_id, partner_id=it.partner_id,
            quantity=qty, unit_price=q2(it.unit_price), total_price=line_total,
        ))
        db.add(FinishedProductMovement(
            product_id=it.product_id, partner_id=it.partner_id, movement_type="sale",
            quantity=qty, date=data.date, sale_id=sale.id, note=f"Sotuv #{sale.id}",
        ))
    for inst in schedule_rows:
        db.add(PaymentSchedule(
            sale_id=sale.id, due_date=inst.due_date, amount=q2(inst.amount),
            paid_amount=0, paid=False, note=inst.note,
        ))

    db.commit()
    return get_sale(db, sale.id)


def delete_sale(db: Session, sale_id: int) -> None:
    """Sotuvni bekor qiladi, mahsulot omborga qaytariladi."""
    sale = get_sale(db, sale_id)
    for m in db.scalars(select(FinishedProductMovement).where(FinishedProductMovement.sale_id == sale_id)):
        db.delete(m)
    db.delete(sale)
    db.commit()


def pay(db: Session, sale_id: int, amount) -> Sale:
    """To'lovni eng eski muddatdan boshlab (FIFO) taqsimlaydi."""
    sale = get_sale(db, sale_id)
    if sale.payment_type != "installment":
        raise bad_request("Bu sotuv muddatli emas, to'lov to'liq qilingan")
    _, debt = paid_and_debt(sale)
    amt = q2(amount)
    if debt <= 0:
        raise bad_request("Bu sotuv bo'yicha qarz yo'q")
    if amt > debt:
        raise bad_request(f"To'lov summasi qarzdan ({fmt(debt)}) oshib ketdi")

    left = amt
    for s in sorted(sale.schedule, key=lambda x: x.due_date):
        if left <= 0:
            break
        remaining = D(s.amount) - D(s.paid_amount)
        if remaining <= 0:
            continue
        part = min(left, remaining)
        s.paid_amount = D(s.paid_amount) + part
        s.paid = D(s.paid_amount) >= D(s.amount)
        left -= part
    db.commit()
    return get_sale(db, sale_id)


def status_filter(status: str, today: Date | None = None):
    """sale_status() mantig'ining SQL varianti (filtr limitdan OLDIN qo'llanishi uchun)."""
    today = today or _today()
    paid_sum = (
        select(func.coalesce(func.sum(PaymentSchedule.paid_amount), 0))
        .where(PaymentSchedule.sale_id == Sale.id)
        .scalar_subquery()
    )
    has_overdue = (
        select(PaymentSchedule.id)
        .where(
            PaymentSchedule.sale_id == Sale.id,
            PaymentSchedule.paid.is_(False),
            PaymentSchedule.due_date < today,
        )
        .exists()
    )
    installment = Sale.payment_type == "installment"
    has_debt = and_(installment, Sale.total_amount - paid_sum > 0)
    if status == "paid":
        return or_(~installment, Sale.total_amount - paid_sum <= 0)
    if status == "overdue":
        return and_(has_debt, has_overdue)
    if status == "partial":
        return and_(has_debt, ~has_overdue, paid_sum > 0)
    if status == "unpaid":
        return and_(has_debt, ~has_overdue, paid_sum == 0)
    return None
