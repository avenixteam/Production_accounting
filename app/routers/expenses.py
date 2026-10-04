from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.expense import Expense
from app.schemas.expense import ExpenseCreate, ExpenseOut, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    date_from: Date | None = None, date_to: Date | None = None,
    category: str | None = None, limit: int = 500, db: Session = Depends(get_db),
):
    stmt = select(Expense)
    if date_from:
        stmt = stmt.where(Expense.date >= date_from)
    if date_to:
        stmt = stmt.where(Expense.date <= date_to)
    if category:
        stmt = stmt.where(Expense.category == category)
    return db.scalars(stmt.order_by(Expense.date.desc(), Expense.id.desc()).limit(min(limit, 2000))).all()


@router.get("/categories", response_model=list[str])
def categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(Expense.category).distinct().order_by(Expense.category)))


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
    obj = Expense(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db)):
    obj = db.get(Expense, expense_id)
    if not obj:
        raise HTTPException(404, "Xarajat topilmadi")
    for k, v in payload.model_dump(exclude_unset=True).items():
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
