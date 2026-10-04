from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, require_admin
from app.models.user import User
from app.security import (
    clear_fails, create_token, hash_password, is_locked, register_fail, verify_password,
)
from app.utils import commit_or_409

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=200)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=200)
    full_name: str | None = Field(default=None, max_length=150)
    role: str = Field(default="staff", pattern="^(admin|staff)$")


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|staff)$")
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)


def _out(u) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role, "active": u.active}


def _client_key(request: Request, username: str) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")
    return f"{ip}|{username.lower()}"


@router.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    key = _client_key(request, payload.username)
    if is_locked(key):
        raise HTTPException(429, "Juda ko'p xato urinish. 5 daqiqadan keyin qayta urinib ko'ring")
    user = db.scalar(select(User).where(User.username == payload.username))
    # foydalanuvchi bo'lmasa ham hash hisoblanadi (vaqt orqali foydalanuvchi nomini aniqlab bo'lmasin)
    stored = user.password_hash if user else "scrypt$16384$8$1$AAAAAAAAAAAAAAAAAAAAAA==$" + "A" * 43 + "="
    ok = verify_password(payload.password, stored)
    if not user or not ok or not user.active:
        register_fail(key)
        raise HTTPException(401, "Login yoki parol noto'g'ri")
    clear_fails(key)
    return {"access_token": create_token(user.id, user.username, user.role), "token_type": "bearer", "user": _out(user)}


@router.get("/me")
def me(user=Depends(current_user)):
    return _out(user)


@router.post("/change-password")
def change_password(payload: PasswordChange, user=Depends(current_user), db: Session = Depends(get_db)):
    obj = db.get(User, user.id)
    if not obj or not verify_password(payload.old_password, obj.password_hash):
        raise HTTPException(400, "Eski parol noto'g'ri")
    obj.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Parol o'zgartirildi"}


# ---- faqat admin ----
@router.get("/users")
def list_users(_=Depends(require_admin), db: Session = Depends(get_db)):
    return [_out(u) for u in db.scalars(select(User).order_by(User.id))]


@router.post("/users", status_code=201)
def create_user(payload: UserCreate, _=Depends(require_admin), db: Session = Depends(get_db)):
    u = User(username=payload.username, full_name=payload.full_name, role=payload.role,
             password_hash=hash_password(payload.password))
    db.add(u)
    commit_or_409(db)
    db.refresh(u)
    return _out(u)


@router.put("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    data = payload.model_dump(exclude_unset=True)
    if u.id == admin.id and (data.get("active") is False or data.get("role") == "staff"):
        raise HTTPException(400, "O'zingizni bloklash yoki admin huquqini olib tashlash mumkin emas")
    if "password" in data:
        pw = data.pop("password")
        if pw:
            u.password_hash = hash_password(pw)
    for k, v in data.items():
        setattr(u, k, v)
    db.commit()
    db.refresh(u)
    return _out(u)
