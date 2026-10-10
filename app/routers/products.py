from app.models.product import Product
from app.routers._crud import make_crud_router
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate

router = make_crud_router(
    prefix="/products", tag="Products", model=Product,
    create_schema=ProductCreate, update_schema=ProductUpdate, out_schema=ProductOut,
    search_fields=("name", "code"), order_by=Product.name, label="Mahsulot",
)
