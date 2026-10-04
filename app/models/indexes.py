"""Tezlik uchun indekslar.

PostgreSQL foreign key ustunlariga avtomatik indeks qo'ymaydi. Ombor qoldig'i har safar
harakatlar jurnali yig'indisidan hisoblangani uchun (partner, mahsulot/xomashyo) bo'yicha
indeks eng muhim. `python init_db.py` bu indekslarni MAVJUD bazaga ham qo'shadi.
"""
from sqlalchemy import Index

from app.models.expense import Expense
from app.models.finished_product_movement import FinishedProductMovement as FPM
from app.models.material_usage import MaterialUsage
from app.models.payment_schedule import PaymentSchedule
from app.models.product_recipe import ProductRecipe
from app.models.production_item import ProductionItem
from app.models.production_report import ProductionReport
from app.models.raw_material_movement import RawMaterialMovement as RMM
from app.models.raw_material_receipt import RawMaterialReceipt
from app.models.sale import Sale
from app.models.sale_item import SaleItem

Index("ix_rmm_partner_material", RMM.partner_id, RMM.raw_material_id)
Index("ix_rmm_date", RMM.date)
Index("ix_rmm_production", RMM.production_id)
Index("ix_rmm_receipt", RMM.receipt_id)

Index("ix_fpm_partner_product", FPM.partner_id, FPM.product_id)
Index("ix_fpm_date", FPM.date)
Index("ix_fpm_production", FPM.production_id)
Index("ix_fpm_sale", FPM.sale_id)

Index("ix_sales_date", Sale.date)
Index("ix_sales_customer", Sale.customer_id)
Index("ix_sale_items_sale", SaleItem.sale_id)
Index("ix_sale_items_partner", SaleItem.partner_id)
Index("ix_sale_items_product", SaleItem.product_id)

Index("ix_schedule_sale", PaymentSchedule.sale_id)
Index("ix_schedule_open_due", PaymentSchedule.paid, PaymentSchedule.due_date)

Index("ix_expenses_date", Expense.date)
Index("ix_expenses_category", Expense.category)

Index("ix_production_date", ProductionReport.date)
Index("ix_production_items_report", ProductionItem.production_id)
Index("ix_production_items_partner", ProductionItem.partner_id)
Index("ix_material_usage_report", MaterialUsage.production_id)
Index("ix_material_usage_item", MaterialUsage.production_item_id)

Index("ix_receipts_date", RawMaterialReceipt.date)
Index("ix_receipts_partner_material", RawMaterialReceipt.partner_id, RawMaterialReceipt.raw_material_id)
Index("ix_recipes_product", ProductRecipe.product_id)
