"""Demo ma'lumotlar bilan bazani to'ldiradi (faqat sinov uchun).

Ishga tushirish:  python seed.py
Talab: pip install -r requirements-dev.txt
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def post(url, body):
    r = c.post(url, json=body)
    if r.status_code >= 300:
        raise SystemExit(f"{url}: {r.status_code} {r.text}")
    return r.json()


def run():
    if c.get("/partners").json():
        print("Baza bo'sh emas - seed o'tkazib yuborildi.")
        return
    today = date.today()
    a = post("/partners", {"name": "Hamkor Alfa", "phone": "+998901112233"})
    b = post("/partners", {"name": "Hamkor Beta"})
    pe = post("/raw-materials", {"brand": "PE-100", "name": "Polietilen granula", "unit": "kg"})
    pp = post("/raw-materials", {"brand": "PP-H350", "name": "Polipropilen", "unit": "kg"})
    bag = post("/products", {"name": "Polietilen paket", "code": "PKT-01", "unit": "dona", "price": 1200})
    film = post("/products", {"name": "Streych plyonka", "code": "PLY-01", "unit": "kg", "price": 18000})
    c.put(f"/products/{bag['id']}/recipe", json={"items": [{"raw_material_id": pe["id"], "quantity": 0.04}]})
    c.put(f"/products/{film['id']}/recipe", json={"items": [{"raw_material_id": pe["id"], "quantity": 0.85}, {"raw_material_id": pp["id"], "quantity": 0.15}]})
    m1 = post("/machines", {"name": "Ekstruder-1"})
    m2 = post("/machines", {"name": "Ekstruder-2"})
    k1 = post("/customers", {"name": "Baraka Savdo MChJ", "phone": "+998933334455", "address": "Toshkent"})
    k2 = post("/customers", {"name": "Orzu Market"})

    for p in (a, b):
        post("/inventory/receipts", {"partner_id": p["id"], "raw_material_id": pe["id"], "quantity": 5000, "unit_price": 11500, "supplier_name": "Uzkimyo", "date": (today - timedelta(days=12)).isoformat()})
        post("/inventory/receipts", {"partner_id": p["id"], "raw_material_id": pp["id"], "quantity": 1500, "unit_price": 12800, "date": (today - timedelta(days=12)).isoformat()})

    for i in range(8, 0, -1):
        d = (today - timedelta(days=i)).isoformat()
        post("/production", {"date": d, "machine_id": m1["id"] if i % 2 else m2["id"], "items": [
            {"product_id": bag["id"], "partner_id": a["id"], "quantity": 4000 + i * 150},
            {"product_id": film["id"], "partner_id": b["id"], "quantity": 120 + i * 10}]})

    post("/sales", {"customer_id": k1["id"], "date": (today - timedelta(days=5)).isoformat(), "payment_type": "cash",
                    "items": [{"product_id": bag["id"], "partner_id": a["id"], "quantity": 10000, "unit_price": 1200}]})
    post("/sales", {"customer_id": k2["id"], "date": (today - timedelta(days=3)).isoformat(), "payment_type": "installment",
                    "items": [{"product_id": film["id"], "partner_id": b["id"], "quantity": 500, "unit_price": 18000}],
                    "installments": [
                        {"due_date": (today - timedelta(days=1)).isoformat(), "amount": 3000000},
                        {"due_date": (today + timedelta(days=29)).isoformat(), "amount": 3000000},
                        {"due_date": (today + timedelta(days=59)).isoformat(), "amount": 3000000}]})
    for cat, amt in (("Elektr energiyasi", 4200000), ("Ish haqi", 12000000), ("Ijara", 3500000)):
        post("/expenses", {"category": cat, "amount": amt, "date": (today - timedelta(days=2)).isoformat()})
    print("Demo ma'lumotlar qo'shildi.")


if __name__ == "__main__":
    run()
