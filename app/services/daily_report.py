"""Kunlik hisobot uchun ma'lumot yig'ish (ma'lumotlar bazasidan).

Excel faylning o'zi `daily_excel.build_workbook()` da yaratiladi.
O'tgan sana bilan kiritilgan yozuv ham o'z kunining hisobotida ko'rinadi:
hamma narsa yozuvning SANASI bo'yicha tanlanadi (kiritilgan vaqti bo'yicha emas).
"""
from datetime import date as Date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.expense import Expense
from app.models.partner import Partner
from app.models.production_report import ProductionReport
from app.models.raw_material import RawMaterial
from app.models.raw_material_receipt import RawMaterialReceipt as Receipt
from app.models.sale import Sale
from app.models.sale_payment import SalePayment
from app.services import production as production_svc
from app.services import sales as sales_svc
from app.services.daily_excel import build_workbook
from app.utils import TZ


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

    # Shu kuni qabul qilingan barcha to'lovlar (eski sotuvlar bo'yicha qarz to'lovlari ham)
    payments = [
        {"id": p.id, "sale_id": p.sale_id, "customer_name": customer, "amount": p.amount, "note": p.note}
        for p, customer in db.execute(
            select(SalePayment, Customer.name)
            .join(Sale, Sale.id == SalePayment.sale_id)
            .join(Customer, Customer.id == Sale.customer_id)
            .where(SalePayment.date == d)
            .order_by(SalePayment.id)
        )
    ]

    return {
        "date": d,
        "generated_at": datetime.now(TZ),
        "production": [production_svc.serialize(r) for r in reports],
        "receipts": receipts,
        "sales": [sales_svc.serialize(s) for s in sales],
        "payments": payments,
        "expenses": [
            {"id": e.id, "category": e.category, "description": e.description, "amount": e.amount}
            for e in expenses
        ],
    }


def build_excel(db: Session, d: Date) -> bytes:
    return build_workbook(collect(db, d))
