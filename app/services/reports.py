from collections import defaultdict
from datetime import date as Date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.expense import Expense
from app.models.partner import Partner
from app.models.payment_schedule import PaymentSchedule
from app.models.product import Product
from app.models.production_item import ProductionItem
from app.models.production_report import ProductionReport
from app.models.raw_material_receipt import RawMaterialReceipt
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.utils import D, today as _today


def month_range(today: Date | None = None) -> tuple[Date, Date]:
    today = today or _today()
    return today.replace(day=1), today


def _daterange(a: Date, b: Date):
    for n in range((b - a).days + 1):
        yield a + timedelta(days=n)


def summary(db: Session, date_from: Date, date_to: Date) -> dict:
    today = _today()

    production_total = D(db.scalar(
        select(func.coalesce(func.sum(ProductionItem.quantity), 0))
        .join(ProductionReport, ProductionReport.id == ProductionItem.production_id)
        .where(ProductionReport.date.between(date_from, date_to))
    ))
    sales_total, sales_count = db.execute(
        select(func.coalesce(func.sum(Sale.total_amount), 0), func.count(Sale.id))
        .where(Sale.date.between(date_from, date_to))
    ).one()
    expenses_total = D(db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.date.between(date_from, date_to))
    ))
    purchases_total = D(db.scalar(
        select(func.coalesce(func.sum(RawMaterialReceipt.quantity * RawMaterialReceipt.unit_price), 0))
        .where(RawMaterialReceipt.date.between(date_from, date_to))
    ))

    # Qarzdorlik - butun vaqt bo'yicha (davrga bog'liq emas)
    unpaid = PaymentSchedule.amount - PaymentSchedule.paid_amount
    receivable = D(db.scalar(select(func.coalesce(func.sum(unpaid), 0)).where(PaymentSchedule.paid.is_(False))))
    overdue = D(db.scalar(
        select(func.coalesce(func.sum(unpaid), 0))
        .where(PaymentSchedule.paid.is_(False), PaymentSchedule.due_date < today)
    ))

    # Kunlik qatorlar
    prod_by_day = defaultdict(Decimal)
    for d, q in db.execute(
        select(ProductionReport.date, func.sum(ProductionItem.quantity))
        .join(ProductionItem, ProductionItem.production_id == ProductionReport.id)
        .where(ProductionReport.date.between(date_from, date_to)).group_by(ProductionReport.date)
    ):
        prod_by_day[d] = D(q)
    sales_by_day = defaultdict(Decimal)
    for d, q in db.execute(
        select(Sale.date, func.sum(Sale.total_amount)).where(Sale.date.between(date_from, date_to)).group_by(Sale.date)
    ):
        sales_by_day[d] = D(q)
    exp_by_day = defaultdict(Decimal)
    for d, q in db.execute(
        select(Expense.date, func.sum(Expense.amount)).where(Expense.date.between(date_from, date_to)).group_by(Expense.date)
    ):
        exp_by_day[d] = D(q)

    daily = [
        {
            "date": d.isoformat(),
            "production": float(prod_by_day[d]),
            "sales": float(sales_by_day[d]),
            "expenses": float(exp_by_day[d]),
        }
        for d in _daterange(date_from, date_to)
    ]

    top_products = [
        {"product_id": pid, "name": name, "unit": unit, "quantity": float(q), "revenue": float(r)}
        for pid, name, unit, q, r in db.execute(
            select(Product.id, Product.name, Product.unit, func.sum(SaleItem.quantity), func.sum(SaleItem.total_price))
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.date.between(date_from, date_to))
            .group_by(Product.id, Product.name, Product.unit)
            .order_by(func.sum(SaleItem.total_price).desc())
            .limit(5)
        )
    ]

    by_partner = defaultdict(lambda: {"production": 0.0, "revenue": 0.0})
    names = {p.id: p.name for p in db.scalars(select(Partner))}
    for pid, q in db.execute(
        select(ProductionItem.partner_id, func.sum(ProductionItem.quantity))
        .join(ProductionReport, ProductionReport.id == ProductionItem.production_id)
        .where(ProductionReport.date.between(date_from, date_to)).group_by(ProductionItem.partner_id)
    ):
        by_partner[pid]["production"] = float(q)
    for pid, r in db.execute(
        select(SaleItem.partner_id, func.sum(SaleItem.total_price))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Sale.date.between(date_from, date_to)).group_by(SaleItem.partner_id)
    ):
        by_partner[pid]["revenue"] = float(r)

    expense_by_category = [
        {"category": c, "amount": float(a)}
        for c, a in db.execute(
            select(Expense.category, func.sum(Expense.amount))
            .where(Expense.date.between(date_from, date_to))
            .group_by(Expense.category).order_by(func.sum(Expense.amount).desc())
        )
    ]

    sales_total = D(sales_total)
    return {
        "date_from": date_from, "date_to": date_to,
        "production_total": float(production_total),
        "sales_total": float(sales_total),
        "sales_count": sales_count,
        "expenses_total": float(expenses_total),
        "purchases_total": float(purchases_total),
        "net_result": float(sales_total - expenses_total - purchases_total),
        "receivable_total": float(receivable),
        "overdue_total": float(overdue),
        "daily": daily,
        "top_products": top_products,
        "by_partner": [{"partner_id": k, "partner_name": names.get(k, "?"), **v} for k, v in by_partner.items()],
        "expense_by_category": expense_by_category,
    }


def debts(db: Session) -> list[dict]:
    """Mijozlar kesimida umumiy qarz, muddati o'tgan summa va eng yaqin to'lov sanasi."""
    today = _today()
    rows = db.execute(
        select(Customer.id, Customer.name, Customer.phone, Sale.id, PaymentSchedule)
        .join(Sale, Sale.customer_id == Customer.id)
        .join(PaymentSchedule, PaymentSchedule.sale_id == Sale.id)
        .where(PaymentSchedule.paid.is_(False))
        .order_by(PaymentSchedule.due_date)
    ).all()

    result: dict[int, dict] = {}
    for cid, cname, phone, sale_id, sched in rows:
        c = result.setdefault(cid, {
            "customer_id": cid, "customer_name": cname, "phone": phone,
            "debt": 0.0, "overdue": 0.0, "next_due_date": None, "sale_ids": set(),
        })
        remaining = float(D(sched.amount) - D(sched.paid_amount))
        c["debt"] += remaining
        c["sale_ids"].add(sale_id)
        if sched.due_date < today:
            c["overdue"] += remaining
        if c["next_due_date"] is None or sched.due_date < c["next_due_date"]:
            c["next_due_date"] = sched.due_date

    out = []
    for c in result.values():
        c["sale_ids"] = sorted(c["sale_ids"])
        out.append(c)
    return sorted(out, key=lambda x: (-x["overdue"], -x["debt"]))
