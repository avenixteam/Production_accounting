from collections import defaultdict
from datetime import date as Date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.expense import Expense
from app.models.partner import Partner
from app.models.product import Product
from app.models.production_item import ProductionItem
from app.models.production_report import ProductionReport
from app.models.raw_material_receipt import RawMaterialReceipt
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_payment import SalePayment
from app.utils import D, today as _today

ZERO = Decimal("0")


def month_range(today: Date | None = None) -> tuple[Date, Date]:
    today = today or _today()
    return today.replace(day=1), today


def _daterange(a: Date, b: Date):
    for n in range((b - a).days + 1):
        yield a + timedelta(days=n)


def _months(a: Date, b: Date) -> list[str]:
    """a dan b gacha bo'lgan oylar: ['2026-01', '2026-02', ...]"""
    out, y, m = [], a.year, a.month
    while (y, m) <= (b.year, b.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _sum_by_day(db: Session, value, date_col, date_from: Date, date_to: Date) -> dict:
    """{sana: yig'indi} - kunlar kesimida."""
    result: dict = defaultdict(Decimal)
    for d, v in db.execute(
        select(date_col, func.sum(value)).where(date_col.between(date_from, date_to)).group_by(date_col)
    ):
        result[d] = D(v)
    return result


def debts(db: Session) -> list[dict]:
    """Qarzi bor mijozlar: har birining umumiy qarzi va qaysi sotuvlardan ekani."""
    paid = (
        select(SalePayment.sale_id.label("sale_id"), func.sum(SalePayment.amount).label("paid"))
        .group_by(SalePayment.sale_id)
        .subquery()
    )
    paid_col = func.coalesce(paid.c.paid, 0)
    rows = db.execute(
        select(Customer.id, Customer.name, Customer.phone, Sale.id, Sale.date, Sale.total_amount, paid_col)
        .join(Sale, Sale.customer_id == Customer.id)
        .outerjoin(paid, paid.c.sale_id == Sale.id)
        .where(Sale.total_amount - paid_col > 0)
        .order_by(Sale.date, Sale.id)
    ).all()

    result: dict[int, dict] = {}
    for cid, cname, phone, sale_id, sale_date, total, paid_amount in rows:
        debt = D(total) - D(paid_amount)
        c = result.setdefault(cid, {
            "customer_id": cid, "customer_name": cname, "phone": phone,
            "debt": ZERO, "oldest_date": sale_date, "sales": [],
        })
        c["debt"] += debt
        c["sales"].append({
            "id": sale_id, "date": sale_date,
            "total": float(total), "paid": float(paid_amount), "debt": float(debt),
        })

    out = []
    for c in result.values():
        c["debt"] = float(c["debt"])
        out.append(c)
    return sorted(out, key=lambda x: -x["debt"])


def summary(db: Session, date_from: Date, date_to: Date) -> dict:
    production_total = D(db.scalar(
        select(func.coalesce(func.sum(ProductionItem.quantity), 0))
        .join(ProductionReport, ProductionReport.id == ProductionItem.production_id)
        .where(ProductionReport.date.between(date_from, date_to))
    ))
    sales_total, sales_count = db.execute(
        select(func.coalesce(func.sum(Sale.total_amount), 0), func.count(Sale.id))
        .where(Sale.date.between(date_from, date_to))
    ).one()
    payments_total = D(db.scalar(
        select(func.coalesce(func.sum(SalePayment.amount), 0)).where(SalePayment.date.between(date_from, date_to))
    ))
    expenses_total = D(db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.date.between(date_from, date_to))
    ))
    purchases_total = D(db.scalar(
        select(func.coalesce(func.sum(RawMaterialReceipt.quantity * RawMaterialReceipt.unit_price), 0))
        .where(RawMaterialReceipt.date.between(date_from, date_to))
    ))

    # Qarzdorlik - butun vaqt bo'yicha (davrga bog'liq emas)
    debtors = debts(db)
    receivable = sum((D(c["debt"]) for c in debtors), ZERO)

    prod_by_day: dict = defaultdict(Decimal)
    for d, q in db.execute(
        select(ProductionReport.date, func.sum(ProductionItem.quantity))
        .join(ProductionItem, ProductionItem.production_id == ProductionReport.id)
        .where(ProductionReport.date.between(date_from, date_to)).group_by(ProductionReport.date)
    ):
        prod_by_day[d] = D(q)
    sales_by_day = _sum_by_day(db, Sale.total_amount, Sale.date, date_from, date_to)
    pay_by_day = _sum_by_day(db, SalePayment.amount, SalePayment.date, date_from, date_to)
    exp_by_day = _sum_by_day(db, Expense.amount, Expense.date, date_from, date_to)
    buy_by_day = _sum_by_day(
        db, RawMaterialReceipt.quantity * RawMaterialReceipt.unit_price, RawMaterialReceipt.date, date_from, date_to
    )

    daily = [
        {
            "date": d.isoformat(),
            "production": float(prod_by_day[d]),
            "sales": float(sales_by_day[d]),
            "payments": float(pay_by_day[d]),
            "expenses": float(exp_by_day[d]),
        }
        for d in _daterange(date_from, date_to)
    ]

    monthly = {m: {"month": m, "production": ZERO, "sales": ZERO, "payments": ZERO,
                   "expenses": ZERO, "purchases": ZERO} for m in _months(date_from, date_to)}
    for series, key in ((prod_by_day, "production"), (sales_by_day, "sales"), (pay_by_day, "payments"),
                        (exp_by_day, "expenses"), (buy_by_day, "purchases")):
        for d, v in series.items():
            monthly[d.strftime("%Y-%m")][key] += v
    monthly_rows = [
        {**{k: (float(v) if k != "month" else v) for k, v in row.items()},
         "net": float(row["sales"] - row["expenses"] - row["purchases"])}
        for row in monthly.values()
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

    names = {p.id: p.name for p in db.scalars(select(Partner))}
    by_partner = [
        {"partner_id": pid, "partner_name": names.get(pid, "?"), "production": float(q)}
        for pid, q in db.execute(
            select(ProductionItem.partner_id, func.sum(ProductionItem.quantity))
            .join(ProductionReport, ProductionReport.id == ProductionItem.production_id)
            .where(ProductionReport.date.between(date_from, date_to)).group_by(ProductionItem.partner_id)
        )
    ]

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
        "payments_total": float(payments_total),
        "expenses_total": float(expenses_total),
        "purchases_total": float(purchases_total),
        "net_result": float(sales_total - expenses_total - purchases_total),
        "receivable_total": float(receivable),
        "debtors_count": len(debtors),
        "daily": daily,
        "monthly": monthly_rows,
        "top_products": top_products,
        "by_partner": by_partner,
        "expense_by_category": expense_by_category,
    }
