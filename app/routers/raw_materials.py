from app.models.raw_material import RawMaterial
from app.routers._crud import make_crud_router
from app.schemas.raw_material import RawMaterialCreate, RawMaterialOut, RawMaterialUpdate

router = make_crud_router(
    prefix="/raw-materials", tag="Raw Materials", model=RawMaterial,
    create_schema=RawMaterialCreate, update_schema=RawMaterialUpdate, out_schema=RawMaterialOut,
    search_fields=("brand", "name"), order_by=RawMaterial.brand, label="Xomashyo",
)
