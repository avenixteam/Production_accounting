"""Parol hash (scrypt, standart kutubxona) va JWT token (PyJWT)."""
import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt

TOKEN_HOURS = int(os.getenv("TOKEN_HOURS", "12"))
_ALGO = "HS256"
_N, _R, _P = 2**14, 8, 1


def auth_disabled() -> bool:
    """Faqat lokal ishlab chiqish/testlar uchun: AUTH_DISABLED=1."""
    return os.getenv("AUTH_DISABLED", "0") == "1"


def _secret() -> str:
    key = os.getenv("SECRET_KEY", "")
    if len(key) < 16:
        raise RuntimeError(
            "SECRET_KEY o'rnatilmagan yoki juda qisqa. .env ga kamida 32 belgili tasodifiy qiymat yozing: "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    return key


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(
        _N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(dk).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id), "username": username, "role": role,
        "iat": int(now.timestamp()), "exp": int((now + timedelta(hours=TOKEN_HOURS)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def decode_token(token: str) -> dict:
    """Noto'g'ri yoki muddati o'tgan token bo'lsa jwt.PyJWTError ko'taradi."""
    return jwt.decode(token, _secret(), algorithms=[_ALGO])


# ---- login urinishlarini cheklash (xotirada, brute-force'dan himoya) ----
_FAILS: dict[str, list[float]] = {}
MAX_FAILS, WINDOW = 8, 300  # 5 daqiqada 8 ta xato urinish


def is_locked(key: str) -> bool:
    now = time.time()
    _FAILS[key] = [t for t in _FAILS.get(key, []) if now - t < WINDOW]
    return len(_FAILS[key]) >= MAX_FAILS


def register_fail(key: str) -> None:
    _FAILS.setdefault(key, []).append(time.time())


def clear_fails(key: str) -> None:
    _FAILS.pop(key, None)
