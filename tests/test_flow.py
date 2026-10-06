from datetime import date, timedelta


def mk(client, url, body):
    r = client.post(url, json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()


def setup_master(client):
    partner = mk(client, "/partners", {"name": "Hamkor A"})
    rm = mk(client, "/raw-materials", {"brand": "PE-100", "name": "Polietilen", "unit": "kg"})
    product = mk(client, "/products", {"name": "Paket", "code": "P-1", "unit": "dona", "price": 1000})
    machine = mk(client, "/machines", {"name": "Stanok-1"})
    customer = mk(client, "/customers", {"name": "Mijoz 1"})
    r = client.put(f"/products/{product['id']}/recipe", json={"items": [{"raw_material_id": rm["id"], "quantity": 0.5}]})
    assert r.status_code == 200, r.text
    return partner, rm, product, machine, customer


def test_full_flow(client):
    partner, rm, product, machine, customer = setup_master(client)

    # kirim
    mk(client, "/inventory/receipts", {"partner_id": partner["id"], "raw_material_id": rm["id"],
                                       "quantity": 100, "unit_price": 12000})
    bal = client.get("/inventory/raw-materials").json()
    assert bal[0]["balance"] == 100

    # preview
    items = [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 100}]
    pv = client.post("/production/preview", json={"items": items}).json()
    assert pv["ok"] and pv["lines"][0]["required"] == 50

    # ishlab chiqarish: 100 dona * 0.5 = 50 kg
    rep = mk(client, "/production", {"machine_id": machine["id"], "items": items})
    assert rep["items"][0]["materials"][0]["quantity"] == 50
    assert client.get("/inventory/raw-materials").json()[0]["balance"] == 50
    assert client.get("/inventory/finished-products").json()[0]["balance"] == 100

    # xomashyo yetmaydi: 300 dona -> 150 kg kerak, 50 bor
    r = client.post("/production", json={"machine_id": machine["id"], "items": [{**items[0], "quantity": 300}]})
    assert r.status_code == 400 and "yetarli emas" in r.json()["detail"]

    # naqd sotuv
    sale = mk(client, "/sales", {"customer_id": customer["id"], "payment_type": "cash",
                                 "items": [{"product_id": product["id"], "partner_id": partner["id"],
                                            "quantity": 40, "unit_price": 1500}]})
    assert sale["total_amount"] == 60000 and sale["status"] == "paid"
    assert client.get("/inventory/finished-products").json()[0]["balance"] == 60

    # ombordan ortiq sotib bo'lmaydi
    r = client.post("/sales", json={"customer_id": customer["id"], "payment_type": "cash",
                                    "items": [{"product_id": product["id"], "partner_id": partner["id"],
                                               "quantity": 999, "unit_price": 1}]})
    assert r.status_code == 400

    # muddatli sotuv: 50 * 1000 = 50000, 2 ta to'lov (biri muddati o'tgan)
    past, future = date.today() - timedelta(days=3), date.today() + timedelta(days=30)
    inst = mk(client, "/sales", {
        "customer_id": customer["id"], "payment_type": "installment",
        "items": [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 50, "unit_price": 1000}],
        "installments": [{"due_date": past.isoformat(), "amount": 20000},
                         {"due_date": future.isoformat(), "amount": 30000}],
    })
    assert inst["status"] == "overdue" and inst["debt"] == 50000

    # jadval yig'indisi mos kelmasa - xato
    r = client.post("/sales", json={
        "customer_id": customer["id"], "payment_type": "installment",
        "items": [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 1, "unit_price": 1000}],
        "installments": [{"due_date": future.isoformat(), "amount": 5}]})
    assert r.status_code == 400

    # qarzdorlik va to'lov (FIFO)
    debts = client.get("/sales/debts").json()
    assert debts[0]["debt"] == 50000 and debts[0]["overdue"] == 20000
    paid = client.post(f"/sales/{inst['id']}/payments", json={"amount": 25000}).json()
    assert paid["paid_amount"] == 25000 and paid["status"] == "partial"
    assert paid["schedule"][0]["paid"] is True and paid["schedule"][1]["paid_amount"] == 5000
    assert client.post(f"/sales/{inst['id']}/payments", json={"amount": 99999}).status_code == 400

    # xarajat va dashboard
    mk(client, "/expenses", {"category": "Elektr", "amount": 10000})
    s = client.get("/reports/summary").json()
    assert s["production_total"] == 100 and s["sales_total"] == 110000
    assert s["expenses_total"] == 10000 and s["purchases_total"] == 1200000
    assert s["receivable_total"] == 25000

    # ishlab chiqarish sotilgan mahsulot tufayli bekor qilinmaydi
    assert client.delete(f"/production/{rep['id']}").status_code == 400
    # sotuvni bekor qilish mahsulotni qaytaradi
    assert client.delete(f"/sales/{inst['id']}").status_code == 200
    # 100 ishlab chiqarildi - 40 naqd sotuv = 60 (muddatli sotuv bekor qilindi)
    assert client.get("/inventory/finished-products").json()[0]["balance"] == 60
    assert client.get("/sales/debts").json() == []


def test_cancel_production_restores_stock(client):
    partner, rm, product, machine, _ = setup_master(client)
    mk(client, "/inventory/receipts", {"partner_id": partner["id"], "raw_material_id": rm["id"], "quantity": 10})
    rep = mk(client, "/production", {"machine_id": machine["id"],
                                     "items": [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 10}]})
    assert client.delete(f"/production/{rep['id']}").status_code == 200
    assert client.get("/inventory/raw-materials").json()[0]["balance"] == 10
    assert client.get("/inventory/finished-products").json() == []


def test_product_without_recipe_and_duplicates(client):
    partner, rm, product, machine, _ = setup_master(client)
    p2 = mk(client, "/products", {"name": "Plyonka"})
    r = client.post("/production", json={"machine_id": machine["id"],
                                         "items": [{"product_id": p2["id"], "partner_id": partner["id"], "quantity": 1}]})
    assert r.status_code == 400 and "retsept" in r.json()["detail"]
    assert client.post("/raw-materials", json={"brand": "PE-100"}).status_code == 409
    assert client.delete(f"/partners/{partner['id']}").status_code == 200
    assert client.get("/partners").json() == []
