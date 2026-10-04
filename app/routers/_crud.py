"""Oddiy ma'lumotnomalar (hamkor, xomashyo, stanok, mijoz, mahsulot) uchun umumiy CRUD."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils import commit_or_409


def make_crud_router(*, prefix, tag, model, create_schema, update_schema, out_schema,
                     search_fields=(), order_by=None, label="Yozuv"):
    router = APIRouter(prefix=prefix, tags=[tag])

    def _get_or_404(db: Session, item_id: int):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, f"{label} topilmadi")
        return obj

    @router.get("", response_model=list[out_schema])
    def list_items(
        include_inactive: bool = False, q: str | None = None,
        limit: int = Query(2000, ge=1, le=5000), offset: int = Query(0, ge=0),
        db: Session = Depends(get_db),
    ):
        stmt = select(model)
        if not include_inactive:
            stmt = stmt.where(model.active.is_(True))
        if q and search_fields:
            like = f"%{q}%"
            stmt = stmt.where(or_(*[getattr(model, f).ilike(like) for f in search_fields]))
        stmt = stmt.order_by(order_by if order_by is not None else model.id.desc())
        return db.scalars(stmt.limit(limit).offset(offset)).all()

    @router.get("/{item_id}", response_model=out_schema)
    def get_item(item_id: int, db: Session = Depends(get_db)):
        return _get_or_404(db, item_id)

    @router.post("", response_model=out_schema, status_code=201)
    def create_item(payload: create_schema, db: Session = Depends(get_db)):
        obj = model(**payload.model_dump())
        db.add(obj)
        commit_or_409(db)
        db.refresh(obj)
        return obj

    @router.put("/{item_id}", response_model=out_schema)
    def update_item(item_id: int, payload: update_schema, db: Session = Depends(get_db)):
        obj = _get_or_404(db, item_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(obj, key, value)
        commit_or_409(db)
        db.refresh(obj)
        return obj

    @router.delete("/{item_id}")
    def deactivate_item(item_id: int, db: Session = Depends(get_db)):
        """Soft delete: tarixiy hujjatlar buzilmasligi uchun yozuv faolsizlantiriladi."""
        obj = _get_or_404(db, item_id)
        obj.active = False
        db.commit()
        return {"message": f"{label} faolsizlantirildi"}

    return router
