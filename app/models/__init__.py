"""Barcha modellarni import qilish - Base.metadata to'liq bo'lishi uchun."""
from app.models.partner import Partner  # noqa: F401
from app.models.raw_material import RawMaterial  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.machine import Machine  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.raw_material_receipt import RawMaterialReceipt  # noqa: F401
from app.models.production_report import ProductionReport  # noqa: F401
from app.models.raw_material_movement import RawMaterialMovement  # noqa: F401
from app.models.production_item import ProductionItem  # noqa: F401
from app.models.material_usage import MaterialUsage  # noqa: F401
from app.models.product_recipe import ProductRecipe  # noqa: F401
from app.models.sale import Sale  # noqa: F401
from app.models.sale_item import SaleItem  # noqa: F401
from app.models.finished_product_movement import FinishedProductMovement  # noqa: F401
from app.models.payment_schedule import PaymentSchedule  # noqa: F401
from app.models.expense import Expense  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models import indexes  # noqa: F401,E402  (indekslar Base.metadata ga qo'shiladi)
