"""Birinchi admin (yoki istalgan foydalanuvchi) yaratish / parolini tiklash.

    python create_user.py                      # so'raydi
    python create_user.py admin --role admin   # parolni so'raydi
Foydalanuvchi mavjud bo'lsa, parol yangilanadi.
"""
import argparse
import getpass

from sqlalchemy import select

import app.models  # noqa: F401
from app.database import Base, SessionLocal, engine
from app.models.user import User
from app.security import hash_password


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("username", nargs="?")
    ap.add_argument("--role", choices=["admin", "staff"], default="admin")
    ap.add_argument("--full-name", default=None)
    ap.add_argument("--password", default=None, help="berilmasa, yashirin so'raladi")
    a = ap.parse_args()

    username = a.username or input("Login: ").strip()
    password = a.password or getpass.getpass("Parol (kamida 8 belgi): ")
    if len(password) < 8:
        raise SystemExit("Parol kamida 8 belgi bo'lishi kerak")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.username == username))
        if u:
            u.password_hash = hash_password(password)
            u.active = True
            print(f"'{username}' paroli yangilandi")
        else:
            db.add(User(username=username, full_name=a.full_name, role=a.role, password_hash=hash_password(password)))
            print(f"'{username}' ({a.role}) yaratildi")
        db.commit()


if __name__ == "__main__":
    main()
