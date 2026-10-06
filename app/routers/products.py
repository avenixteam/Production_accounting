from fastapi import Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.models.product_recipe import ProductRecipe
from app.models.raw_material import RawMaterial
from app.routers._crud import make_crud_router
from app.schemas.product import (
    ProductCreate, ProductOut, ProductUpdate, RecipeLineOut, RecipeSetIn,
)
from app.utils import bad_request, commit_or_409

router = make_crud_router(
    prefix="/products", tag="Products", model=Product,
    create_schema=ProductCreate, update_schema=ProductUpdate, out_schema=ProductOut,
    search_fields=("name", "code"), order_by=Product.name, label="Mahsulot",
)


def _recipe_out(db: Session, product_id: int) -> list[dict]:
    rows = db.execute(
        select(ProductRecipe, RawMaterial)
        .join(RawMaterial, RawMaterial.id == ProductRecipe.raw_material_id)
        .where(ProductRecipe.product_id == product_id)
        .order_by(RawMaterial.brand)
    ).all()
    return [
        RecipeLineOut(
            raw_material_id=rm.id, brand=rm.brand, name=rm.name, unit=rm.unit, quantity=float(r.quantity)
        ).model_dump()
        for r, rm in rows
    ]


@router.get("/{product_id}/recipe", response_model=list[RecipeLineOut])
def get_recipe(product_id: int, db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(404, "Mahsulot topilmadi")
    return _recipe_out(db, product_id)


@router.put("/{product_id}/recipe", response_model=list[RecipeLineOut])
def set_recipe(product_id: int, payload: RecipeSetIn, db: Session = Depends(get_db)):
    """Retseptni to'liq almashtiradi: 1 birlik mahsulotga qancha xomashyo ketishi."""
    if not db.get(Product, product_id):
        raise HTTPException(404, "Mahsulot topilmadi")

    ids = [i.raw_material_id for i in payload.items]
    if len(ids) != len(set(ids)):
        raise bad_request("Bir xil xomashyo retseptda ikki marta kiritilgan")
    found = {r.id for r in db.scalars(select(RawMaterial).where(RawMaterial.id.in_(ids)))}
    missing = set(ids) - found
    if missing:
        raise HTTPException(404, f"Xomashyo topilmadi: {sorted(missing)}")

    db.execute(delete(ProductRecipe).where(ProductRecipe.product_id == product_id))
    for line in payload.items:
        db.add(ProductRecipe(
            product_id=product_id, raw_material_id=line.raw_material_id,
            quantity=round(line.quantity, 6),
        ))
    commit_or_409(db)
    return _recipe_out(db, product_id)
