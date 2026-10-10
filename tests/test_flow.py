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
    return partner, rm, product, machine, customer


def sale_body(customer, product, qty=10, price=1000, payment_type="full", **extra):
    return {"customer_id": customer["id"], "payment_type": payment_type,
            "items": [{"product_id": product["id"], "quantity": qty, "unit_price": price}], **extra}


def test_receipt_and_production(client):
    partner, rm, product, machine, _ = setup_master(client)

    rc = mk(client, "/receipts", {"partner_id": partner["id"], "raw_material_id": rm["id"],
                                  "quantity": 100, "unit_price": 12000})
    assert rc["total"] == 1200000
    assert len(client.get("/receipts").json()) == 1

    # ishlab chiqarish: retsept ham, xomashyo qoldig'i ham talab qilinmaydi
    items = [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 100}]
    rep = mk(client, "/production", {"machine_id": machine["id"], "items": items})
    assert rep["total_quantity"] == 100 and rep["items"][0]["product_name"] == "Paket"
    assert len(client.get("/production").json()) == 1

    assert client.delete(f"/production/{rep['id']}").status_code == 200
    assert client.get("/production").json() == []
    assert client.delete(f"/receipts/{rc['id']}").status_code == 200
    assert client.get("/receipts").json() == []


def test_sale_full_partial_credit_and_payments(client):
    _, _, product, _, customer = setup_master(client)

    full = mk(client, "/sales", sale_body(customer, product, 40, 1500))
    assert full["total_amount"] == 60000 and full["status"] == "paid"
    assert full["paid_amount"] == 60000 and full["debt"] == 0 and len(full["payments"]) == 1

    credit = mk(client, "/sales", sale_body(customer, product, 50, 1000, "credit"))
    assert credit["status"] == "unpaid" and credit["debt"] == 50000 and credit["payments"] == []

    part = mk(client, "/sales", sale_body(customer, product, 50, 1000, "partial", paid_amount=20000))
    assert part["status"] == "partial" and part["paid_amount"] == 20000 and part["debt"] == 30000

    def code(body):
        return client.post("/sales", json=body).status_code

    assert code(sale_body(customer, product, 10, 1000, "partial")) == 400
    assert code(sale_body(customer, product, 10, 1000, "partial", paid_amount=10000)) == 400
    assert code(sale_body(customer, product, 10, 1000, "partial", paid_amount=99999)) == 400
    assert code(sale_body(customer, product, 10, 1000, "credit", paid_amount=500)) == 400
    assert code(sale_body(customer, product, 10, 1000, "installment")) == 422

    # qarz to'lash: qo'shilib, qarzdan ayriladi
    r = client.post(f"/sales/{part['id']}/payments", json={"amount": 10000})
    assert r.status_code == 200
    p = r.json()
    assert p["paid_amount"] == 30000 and p["debt"] == 20000 and p["status"] == "partial"
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    p = client.post(f"/sales/{part['id']}/payments", json={"amount": 20000, "date": yesterday}).json()
    assert p["debt"] == 0 and p["status"] == "paid"
    assert any(x["date"] == yesterday for x in p["payments"])
    assert client.post(f"/sales/{part['id']}/payments", json={"amount": 1}).status_code == 400
    assert client.post(f"/sales/{credit['id']}/payments", json={"amount": 999999}).status_code == 400

    debts = client.get("/sales/debts").json()
    assert len(debts) == 1 and debts[0]["debt"] == 50000
    assert [s["id"] for s in debts[0]["sales"]] == [credit["id"]]

    assert client.delete(f"/sales/{credit['id']}").status_code == 200
    assert client.get("/sales/debts").json() == []


def test_debts_grouped_by_customer(client):
    _, _, product, _, c1 = setup_master(client)
    c2 = mk(client, "/customers", {"name": "Mijoz 2"})
    mk(client, "/sales", sale_body(c1, product, 10, 1000, "credit"))
    mk(client, "/sales", sale_body(c1, product, 10, 1000, "partial", paid_amount=4000))
    mk(client, "/sales", sale_body(c2, product, 5, 1000, "credit"))
    debts = {d["customer_name"]: d for d in client.get("/sales/debts").json()}
    assert debts["Mijoz 1"]["debt"] == 16000 and len(debts["Mijoz 1"]["sales"]) == 2
    assert debts["Mijoz 2"]["debt"] == 5000


def test_summary_and_periods(client):
    partner, rm, product, machine, customer = setup_master(client)
    mk(client, "/receipts", {"partner_id": partner["id"], "raw_material_id": rm["id"],
                             "quantity": 100, "unit_price": 12000})
    mk(client, "/production", {"machine_id": machine["id"],
                               "items": [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 100}]})
    mk(client, "/sales", sale_body(customer, product, 40, 1500))
    mk(client, "/sales", sale_body(customer, product, 50, 1000, "partial", paid_amount=20000))
    mk(client, "/expenses/categories", {"name": "Elektr"})
    mk(client, "/expenses", {"category": "Elektr", "amount": 10000})

    s = client.get("/reports/summary").json()
    assert s["production_total"] == 100 and s["sales_total"] == 110000
    assert s["payments_total"] == 80000 and s["receivable_total"] == 30000 and s["debtors_count"] == 1
    assert s["expenses_total"] == 10000 and s["purchases_total"] == 1200000
    assert len(s["monthly"]) == 1 and s["monthly"][0]["sales"] == 110000
    assert s["expense_by_category"] == [{"category": "Elektr", "amount": 10000}]

    start = (date.today().replace(day=1) - timedelta(days=330)).isoformat()
    y = client.get("/reports/summary", params={"date_from": start}).json()
    assert len(y["monthly"]) >= 11 and y["sales_total"] == 110000


def test_expense_categories(client):
    assert client.post("/expenses", json={"category": "Oshxona", "amount": 30000}).status_code == 400

    cat = mk(client, "/expenses/categories", {"name": "Oshxona"})
    assert client.post("/expenses/categories", json={"name": "oshxona"}).status_code == 409

    mk(client, "/expenses", {"category": "Oshxona", "amount": 30000, "description": "kartoshka"})
    mk(client, "/expenses", {"category": "oshxona", "amount": 5000, "description": "piyoz"})
    cats = client.get("/expenses/categories").json()
    assert cats[0]["name"] == "Oshxona" and cats[0]["count"] == 2 and cats[0]["total"] == 35000

    assert client.delete(f"/expenses/categories/{cat['id']}").status_code == 400

    assert client.put(f"/expenses/categories/{cat['id']}", json={"name": "Ovqat"}).status_code == 200
    assert {e["category"] for e in client.get("/expenses").json()} == {"Ovqat"}

    empty = mk(client, "/expenses/categories", {"name": "Bo'sh"})
    assert client.delete(f"/expenses/categories/{empty['id']}").status_code == 200


def test_duplicates_and_soft_delete(client):
    partner, *_ = setup_master(client)
    assert client.post("/raw-materials", json={"brand": "PE-100"}).status_code == 409
    assert client.delete(f"/partners/{partner['id']}").status_code == 200
    assert client.get("/partners").json() == []
