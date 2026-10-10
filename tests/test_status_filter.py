from test_flow import mk, sale_body, setup_master


def test_sales_status_filter_applies_before_limit(client):
    _, _, product, _, customer = setup_master(client)

    paid = mk(client, "/sales", sale_body(customer, product, 10, 1000, "full"))
    credit = mk(client, "/sales", sale_body(customer, product, 10, 1000, "credit"))
    partial = mk(client, "/sales", sale_body(customer, product, 10, 1000, "partial", paid_amount=4000))
    later = mk(client, "/sales", sale_body(customer, product, 10, 1000, "credit"))
    client.post(f"/sales/{later['id']}/payments", json={"amount": 10000})  # to'liq to'landi -> "paid"

    def ids(status, **kw):
        r = client.get("/sales", params={"status": status, **kw})
        assert r.status_code == 200, r.text
        return {s["id"] for s in r.json()}

    assert ids("paid") == {paid["id"], later["id"]}
    assert ids("unpaid") == {credit["id"]}
    assert ids("partial") == {partial["id"]}
    assert ids("unpaid", limit=1) == {credit["id"]}
