from app.models.partner import Partner
from app.routers._crud import make_crud_router
from app.schemas.partner import PartnerCreate, PartnerOut, PartnerUpdate

router = make_crud_router(
    prefix="/partners", tag="Partners", model=Partner,
    create_schema=PartnerCreate, update_schema=PartnerUpdate, out_schema=PartnerOut,
    search_fields=("name", "phone"), order_by=Partner.name, label="Hamkor",
)
