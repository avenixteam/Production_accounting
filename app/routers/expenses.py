from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.expense import Expense
from app.models.expense_category import ExpenseCategory
from app.schemas.expense import CategoryIn, ExpenseCreate, ExpenseOut, ExpenseUpdate
from app.utils import bad_request

router = APIRouter(prefix="/expenses", tags=["Expenses"])


# ---------------- Kategoriyalar ----------------
def _find_category(db: Session, name: str, exclude_id: int | None = None) -> ExpenseCategory | None:
    stmt = select(ExpenseCategory).where(func.lower(ExpenseCategory.name) == name.strip().lower())
    if exclude_id:
        stmt = stmt.where(ExpenseCategory.id != exclude_id)
    return db.scalar(stmt)


def _category_out(c: ExpenseCategory, count: int = 0, total: float = 0.0) -> dict:
    return {"id": c.id, "name": c.name, "count": count, "total": total}


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    stats = {
        name: (n, float(total))
        for name, n, total in db.execute(
            select(Expense.category, func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0))
            .group_by(Expense.category)
        )
    }
    cats = db.scalars(select(ExpenseCategory).order_by(ExpenseCategory.name)).all()
    return [_category_out(c, *stats.get(c.name, (0, 0.0))) for c in cats]


@router.post("/categories", status_code=201)
def create_category(payload: CategoryIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise bad_request("Kategoriya nomi bo'sh bo'lmasligi kerak")
    if _find_category(db, name):
        raise HTTPException(409, "Bunday kategoriya allaqachon bor")
    cat = ExpenseCategory(name=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return _category_out(cat)


@router.put("/categories/{category_id}")
def rename_category(category_id: int, payload: CategoryIn, db: Session = Depends(get_db)):
    cat = db.get(ExpenseCategory, category_id)
    if not cat:
        raise HTTPException(404, "Kategoriya topilmadi")
    name = payload.name.strip()
    if not name:
        raise bad_request("Kategoriya nomi bo'sh bo'lmasligi kerak")
    if _find_category(db, name, exclude_id=category_id):
        raise HTTPException(409, "Bunday kategoriya allaqachon bor")
    old = cat.name
    cat.name = name
    # Xarajatlarda kategoriya nomi saqlanadi - ularni ham yangilaymiz
    db.execute(update(Expense).where(Expense.category == old).values(category=name))
    db.commit()
    db.refresh(cat)
    return _category_out(cat)


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(ExpenseCategory, category_id)
    if not cat:
        raise HTTPException(404, "Kategoriya topilmadi")
    n = db.scalar(select(func.count(Expense.id)).where(Expense.category == cat.name))
    if n:
        raise bad_request(f"Bu kategoriyada {n} ta xarajat bor. Avval ularni o'chiring, so'ng kategoriyani o'chiring")
    db.delete(cat)
    db.commit()
    return {"message": "Kategoriya o'chirildi"}


def _existing_category_name(db: Session, name: str) -> str:
    cat = _find_category(db, name)
    if not cat:
        raise bad_request(f"'{name.strip()}' kategoriyasi topilmadi. Avval kategoriya yarating")
    return cat.name


# ---------------- Xarajatlar ----------------
@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    date_from: Date | None = None, date_to: Date | None = None,
    category: str | None = None, limit: int = 1000, db: Session = Depends(get_db),
):
    stmt = select(Expense)
    if date_from:
        stmt = stmt.where(Expense.date >= date_from)
    if date_to:
        stmt = stmt.where(Expense.date <= date_to)
    if category:
        stmt = stmt.where(Expense.category == category)
    return db.scalars(stmt.order_by(Expense.date.desc(), Expense.id.desc()).limit(min(limit, 5000))).all()


@router.get("/summary")
def summary(date_from: Date | None = None, date_to: Date | None = None, db: Session = Depends(get_db)):
    stmt = select(Expense.category, func.sum(Expense.amount), func.count(Expense.id)).group_by(Expense.category)
    if date_from:
        stmt = stmt.where(Expense.date >= date_from)
    if date_to:
        stmt = stmt.where(Expense.date <= date_to)
    rows = db.execute(stmt.order_by(func.sum(Expense.amount).desc())).all()
    return [{"category": c, "amount": float(a), "count": n} for c, a, n in rows]


@router.post("", response_model=ExpenseOut, status_code=201)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["category"] = _existing_category_name(db, payload.category)
    obj = Expense(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db)):
    obj = db.get(Expense, expense_id)
    if not obj:
        raise HTTPException(404, "Xarajat topilmadi")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("category") is not None:
        changes["category"] = _existing_category_name(db, changes["category"])
    for k, v in changes.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    obj = db.get(Expense, expense_id)
    if not obj:
        raise HTTPException(404, "Xarajat topilmadi")
    db.delete(obj)
    db.commit()
    return {"message": "Xarajat o'chirildi"}
