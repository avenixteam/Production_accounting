from app.models.machine import Machine
from app.routers._crud import make_crud_router
from app.schemas.master import MachineCreate, MachineOut, MachineUpdate

router = make_crud_router(
    prefix="/machines", tag="Machines", model=Machine,
    create_schema=MachineCreate, update_schema=MachineUpdate, out_schema=MachineOut,
    search_fields=("name",), order_by=Machine.name, label="Stanok",
)
