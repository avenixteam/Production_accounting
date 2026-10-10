from datetime import date as Date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.customer import Customer
from app.models.finished_product_movement import FinishedProductMovement
from app.models.partner import Partner
from app.models.product import Product
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.utils import D, bad_request, fmt, q2, q3

ZERO = Decimal("0")


def eager_options():
    return (
        selectinload(Sale.customer),
        selectinload(Sale.items).selectinload(SaleItem.product),
        selectinload(Sale.items).selectinload(SaleItem.partner),
        selectinload(Sale.payments),
    )


def paid_and_debt(sale: Sale) -> tuple[Decimal, Decimal]:
    total = D(sale.total_amount)
    paid = sum((D(p.amount) for p in sale.payments), ZERO)
    return paid, max(total - paid, ZERO)


def sale_status(sale: Sale) -> str:
    """paid - to'liq to'langan, partial - qisman, unpaid - nasiya (hali to'lanmagan)."""
    paid, debt = paid_and_debt(sale)
    if debt <= 0:
        return "paid"
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
                "partner_name": i.partner.name if i.partner else None,
                "quantity": float(i.quantity),
                "unit_price": float(i.unit_price),
                "total_price": float(i.total_price),
            }
            for i in sale.items
        ],
        "payments": [
            {"id": p.id, "date": p.date, "amount": float(p.amount), "note": p.note}
            for p in sale.payments
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
    partner_ids = {i.partner_id for i in data.items if i.partner_id}
    partners = {p.id: p for p in db.scalars(select(Partner).where(Partner.id.in_(partner_ids)))} if partner_ids else {}

    total = ZERO
    rows = []
    for it in data.items:
        if it.product_id not in products:
            raise HTTPException(404, f"Mahsulot topilmadi (id={it.product_id})")
        if it.partner_id and it.partner_id not in partners:
            raise HTTPException(404, f"Hamkor topilmadi (id={it.partner_id})")
        qty = q3(it.quantity)
        line_total = q2(qty * D(it.unit_price))
        total += line_total
        rows.append((it, qty, line_total))

    if data.payment_type == "full":
        paid_now = total
    elif data.payment_type == "credit":
        if data.paid_amount:
            raise bad_request("Nasiyada to'lov summasi kiritilmaydi. Qisman to'lov bo'lsa 'Qisman' ni tanlang")
        paid_now = ZERO
    else:  # partial
        paid_now = q2(data.paid_amount or 0)
        if paid_now <= 0:
            raise bad_request("Qisman to'lov uchun hozir to'langan summani kiriting")
        if paid_now >= total:
            raise bad_request(
                f"Qisman to'lov jami summadan ({fmt(total)}) kam bo'lishi kerak. To'liq to'langan bo'lsa 'To'liq' ni tanlang"
            )

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
    if paid_now > 0:
        db.add(SalePayment(sale_id=sale.id, amount=paid_now, date=data.date, note="Sotuv vaqtida"))

    db.commit()
    return get_sale(db, sale.id)


def delete_sale(db: Session, sale_id: int) -> None:
    """Sotuvni (to'lovlari bilan) o'chiradi."""
    sale = get_sale(db, sale_id)
    # Eski ombor yozuvlari (agar bo'lsa) sotuvga bog'langan - avval ular o'chiriladi
    db.execute(delete(FinishedProductMovement).where(FinishedProductMovement.sale_id == sale_id))
    db.delete(sale)  # mahsulotlar, to'lovlar cascade orqali o'chadi
    db.commit()


def add_payment(db: Session, sale_id: int, amount, pay_date: Date, note: str | None = None) -> Sale:
    """Qarz bo'yicha yangi to'lov qabul qiladi (qarzdan ayriladi)."""
    # Parallel ikki to'lov qarzdan oshib ketmasligi uchun sotuv qatorini bloklaymiz
    db.execute(select(Sale.id).where(Sale.id == sale_id).with_for_update())
    sale = get_sale(db, sale_id)
    _, debt = paid_and_debt(sale)
    amt = q2(amount)
    if debt <= 0:
        raise bad_request("Bu sotuv bo'yicha qarz yo'q")
    if amt > debt:
        raise bad_request(f"To'lov summasi qarzdan ({fmt(debt)}) oshib ketdi")
    db.add(SalePayment(sale_id=sale_id, amount=amt, date=pay_date, note=note))
    db.commit()
    return get_sale(db, sale_id)


def status_filter(status: str):
    """sale_status() mantig'ining SQL varianti (filtr limitdan OLDIN qo'llanishi uchun)."""
    paid_sum = (
        select(func.coalesce(func.sum(SalePayment.amount), 0))
        .where(SalePayment.sale_id == Sale.id)
        .scalar_subquery()
    )
    has_debt = Sale.total_amount - paid_sum > 0
    if status == "paid":
        return Sale.total_amount - paid_sum <= 0
    if status == "partial":
        return and_(has_debt, paid_sum > 0)
    if status == "unpaid":
        return and_(has_debt, paid_sum == 0)
    return None
