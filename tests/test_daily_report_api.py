"""Kunlik Excel hisobot endpointi (butun tizim orqali). Eslatma: `pytest` bilan ishga tushiring."""
import io
from datetime import date, timedelta

from openpyxl import load_workbook



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


def _find(ws, text):
    for row in ws.iter_rows():
        for c in row:
            if c.value == text:
                return c.row
    raise AssertionError(f"'{text}' topilmadi")


def _get(client, d):
    r = client.get("/reports/daily/excel", params={"date": d.isoformat()})
    assert r.status_code == 200, r.text
    assert "spreadsheetml" in r.headers["content-type"]
    assert f"kunlik_hisobot_{d.isoformat()}.xlsx" in r.headers["content-disposition"]
    return load_workbook(io.BytesIO(r.content), data_only=True)


def test_backdated_entries_land_in_their_own_day(client):
    partner, rm, product, machine, customer = setup_master(client)
    yesterday = date.today() - timedelta(days=1)

    # kecha unutilgan yozuvlar bugun, kechagi sana bilan kiritiladi
    mk(client, "/inventory/receipts", {"partner_id": partner["id"], "raw_material_id": rm["id"],
                                       "quantity": 100, "unit_price": 1000, "date": yesterday.isoformat()})
    mk(client, "/production", {"date": yesterday.isoformat(), "machine_id": machine["id"],
                               "items": [{"product_id": product["id"], "partner_id": partner["id"], "quantity": 80}]})
    mk(client, "/sales", {"customer_id": customer["id"], "date": yesterday.isoformat(), "payment_type": "cash",
                          "items": [{"product_id": product["id"], "partner_id": partner["id"],
                                     "quantity": 30, "unit_price": 2000}]})
    mk(client, "/expenses", {"category": "Elektr", "amount": 5000, "date": yesterday.isoformat()})

    wb = _get(client, yesterday)
    ws = wb["Ishlab chiqarish"]
    assert ws.cell(_find(ws, "Jami"), 5).value == 80
    raw = wb["Xomashyo"]
    r = _find(raw, "PE-100 — Polietilen")
    # boshida 0, kirim 100, sarf 80 * 0.5 = 40 -> oxirida 60
    assert [raw.cell(r, c).value for c in (4, 5, 6, 8)] == [0, 100, 40, 60]
    fp = wb["Tayyor mahsulot"]
    r = _find(fp, "Paket")
    assert [fp.cell(r, c).value for c in (4, 5, 6, 8)] == [0, 80, 30, 50]
    fin = wb["Moliya"]
    assert fin.cell(_find(fin, "Jami sotuv"), 7).value == 60000
    assert fin.cell(_find(fin, "Jami xarajat"), 7).value == 5000
    assert fin.cell(_find(fin, "Jami xomashyo xaridi"), 7).value == 100000

    # bugungi hisobot: yozuvlar yo'q, lekin kecha qolgan qoldiq "kun boshiga" bo'lib ko'rinadi
    today_wb = _get(client, date.today())
    assert "kiritilmagan" in today_wb["Ishlab chiqarish"]["A5"].value
    raw = today_wb["Xomashyo"]
    r = _find(raw, "PE-100 — Polietilen")
    assert [raw.cell(r, c).value for c in (4, 5, 6, 8)] == [60, 0, 0, 60]


def test_default_date_is_today_and_empty_day_works(client):
    r = client.get("/reports/daily/excel")
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Ishlab chiqarish", "Xomashyo", "Tayyor mahsulot", "Moliya"]


def test_invalid_date_rejected(client):
    assert client.get("/reports/daily/excel", params={"date": "kecha"}).status_code == 422
