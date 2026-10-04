from app.models.customer import Customer
from app.routers._crud import make_crud_router
from app.schemas.master import CustomerCreate, CustomerOut, CustomerUpdate

router = make_crud_router(
    prefix="/customers", tag="Customers", model=Customer,
    create_schema=CustomerCreate, update_schema=CustomerUpdate, out_schema=CustomerOut,
    search_fields=("name", "phone"), order_by=Customer.name, label="Mijoz",
)
