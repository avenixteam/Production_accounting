"""Autentifikatsiya bog'liqliklari."""
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.security import auth_disabled, decode_token

_bearer = HTTPBearer(auto_error=False)


class _Anon:
    id, username, role, active, full_name = 0, "dev", "admin", True, "Dev (auth o'chirilgan)"


def current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
):
    """Barcha himoyalangan endpointlar uchun. DELETE (hujjatni bekor qilish) faqat admin uchun."""
    if auth_disabled():
        return _Anon()
    if creds is None:
        raise HTTPException(401, "Tizimga kiring", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Sessiya muddati tugadi, qayta kiring") from None
    except jwt.PyJWTError:
        raise HTTPException(401, "Yaroqsiz token") from None

    user = db.get(User, int(payload["sub"]))
    if not user or not user.active:
        raise HTTPException(401, "Foydalanuvchi topilmadi yoki bloklangan")
    if request.method == "DELETE" and user.role != "admin":
        raise HTTPException(403, "Hujjatni bekor qilish/o'chirish faqat admin uchun")
    return user


def require_admin(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Bu amal faqat admin uchun")
    return user
