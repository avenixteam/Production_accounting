import os

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import models  # noqa: F401  (barcha modellar ro'yxatdan o'tadi)
from app.database import engine
from app.deps import current_user
from app.routers import (
    auth, customers, expenses, inventory, machines, partners, production,
    products, raw_materials, reports, sales,
)

app = FastAPI(
    title="Factory Production Accounting API",
    version="1.0.0",
    description="Ishlab chiqarish zavodi uchun hisob-kitob tizimi: xomashyo, ishlab chiqarish, ombor, sotuv, qarzdorlik, xarajatlar.",
    root_path=os.getenv("ROOT_PATH", ""),  # Caddy orqasida "/api"
)

origins = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)  # /auth/login ochiq, qolganlari ichida tekshiriladi

for r in (
    partners.router, raw_materials.router, products.router, machines.router,
    customers.router, inventory.router, production.router, sales.router,
    expenses.router, reports.router,
):
    app.include_router(r, dependencies=[Depends(current_user)])  # hammasi login talab qiladi


@app.get("/", tags=["System"])
def root():
    return {"message": "Factory System API ishlayapti!", "docs": "/docs"}


@app.get("/health", tags=["System"])
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:  # noqa: BLE001
        # 503: monitoring (UptimeRobot, docker healthcheck) muammoni sezishi uchun
        return JSONResponse({"status": "error", "database": "not connected"}, status_code=503)
