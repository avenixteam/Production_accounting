from datetime import date, timedelta

from test_flow import mk, setup_master


def test_sales_status_filter_applies_before_limit(client):
    partner, rm, product, machine, customer = setup_master(client)
    mk(client, "/inventory/receipts", {"partner_id": partner["id"], "raw_material_id": rm["id"], "quantity": 100})
    items = [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 100}]
    mk(client, "/production", {"machine_id": machine["id"], "items": items})

    def item(q):
        return [{"product_id": product["id"], "partner_id": partner["id"], "quantity": q, "unit_price": 1000}]

    past, future = date.today() - timedelta(days=5), date.today() + timedelta(days=20)
    cash = mk(client, "/sales", {"customer_id": customer["id"], "payment_type": "cash", "items": item(10)})
    overdue = mk(client, "/sales", {"customer_id": customer["id"], "payment_type": "installment", "items": item(10),
                                    "installments": [{"due_date": past.isoformat(), "amount": 10000}]})
    unpaid = mk(client, "/sales", {"customer_id": customer["id"], "payment_type": "installment", "items": item(10),
                                   "installments": [{"due_date": future.isoformat(), "amount": 10000}]})
    partial = mk(client, "/sales", {"customer_id": customer["id"], "payment_type": "installment", "items": item(10),
                                    "installments": [{"due_date": future.isoformat(), "amount": 10000}]})
    client.post(f"/sales/{partial['id']}/payments", json={"amount": 4000})

    def ids(status, **kw):
        r = client.get("/sales", params={"status": status, **kw})
        assert r.status_code == 200, r.text
        return {s["id"] for s in r.json()}

    assert ids("paid") == {cash["id"]}
    assert ids("overdue") == {overdue["id"]}
    assert ids("unpaid") == {unpaid["id"]}
    assert ids("partial") == {partial["id"]}
    # limit=1: filtr limitdan OLDIN ishlaydi (eng eski 'overdue' ham topiladi)
    assert ids("overdue", limit=1) == {overdue["id"]}
