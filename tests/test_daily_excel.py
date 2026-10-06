"""Kunlik Excel hisobot generatori (ma'lumotlar bazasiz, faqat tayyor lug'atlar bilan)."""
import io
from datetime import date, datetime

from openpyxl import load_workbook

from app.services.daily_excel import build_workbook


def _sample() -> dict:
    return {
        "date": date(2026, 10, 3),
        "generated_at": datetime(2026, 10, 4, 18, 42),
        "production": [
            {"id": 11, "machine_name": "Stanok-1", "note": None, "items": [
                {"product_name": "Paket", "unit": "dona", "partner_name": "Hamkor A", "quantity": 1000},
                {"product_name": "Plyonka", "unit": "kg", "partner_name": "Hamkor B", "quantity": 250.5},
            ]},
            {"id": 12, "machine_name": "Stanok-2", "note": "=1+1", "items": [
                {"product_name": "Paket", "unit": "dona", "partner_name": "Hamkor A", "quantity": 500},
            ]},
        ],
        "raw_rows": [
            {"partner_name": "Hamkor A", "label": "PE-100 — Polietilen", "unit": "kg",
             "opening": 100, "incoming": 50, "outgoing": 30.25, "adjustment": -2},
            {"partner_name": "Hamkor B", "label": "PP-7", "unit": "kg",
             "opening": 5, "incoming": 0, "outgoing": 10, "adjustment": 0},
        ],
        "fp_rows": [
            {"partner_name": "Hamkor A", "label": "Paket", "unit": "dona",
             "opening": 200, "incoming": 1500, "outgoing": 300, "adjustment": 0},
        ],
        "receipts": [
            {"partner_name": "Hamkor A", "brand": "PE-100", "unit": "kg", "quantity": 50, "unit_price": 12000.5,
             "supplier_name": "Ta'minotchi", "payment_type": "naqd", "note": "birinchi partiya"},
            {"partner_name": "Hamkor B", "brand": "PP-7", "unit": "kg", "quantity": 20, "unit_price": None,
             "supplier_name": None, "payment_type": None, "note": None},
        ],
        "sales": [
            {"id": 7, "customer_name": "Mijoz 1", "payment_type": "cash", "note": None, "items": [
                {"product_name": "Paket", "unit": "dona", "partner_name": "Hamkor A",
                 "quantity": 300, "unit_price": 1500, "total_price": 450000},
            ]},
            {"id": 8, "customer_name": "Mijoz 2", "payment_type": "installment", "note": "2 oyga", "items": [
                {"product_name": "Plyonka", "unit": "kg", "partner_name": "Hamkor B",
                 "quantity": 10.5, "unit_price": 3333.33, "total_price": 34999.97},
            ]},
        ],
        "expenses": [
            {"category": "Elektr", "description": "Sentabr", "amount": 100000},
            {"category": "Ijara", "description": None, "amount": 250000.5},
        ],
    }


def _empty() -> dict:
    d = _sample()
    d.update(production=[], raw_rows=[], fp_rows=[], receipts=[], sales=[], expenses=[])
    return d


def _load(data, values=True):
    return load_workbook(io.BytesIO(build_workbook(data)), data_only=values)


def _find(ws, text):
    """Matn yozilgan birinchi katakni topadi -> (qator, ustun)."""
    for row in ws.iter_rows():
        for c in row:
            if c.value == text:
                return c.row, c.column
    raise AssertionError(f"'{text}' topilmadi")


def test_sheet_names_and_valid_xlsx():
    wb = _load(_sample())
    assert wb.sheetnames == ["Ishlab chiqarish", "Xomashyo", "Tayyor mahsulot", "Moliya"]


def test_production_rows_and_totals():
    ws = _load(_sample())["Ishlab chiqarish"]
    r, _ = _find(ws, "Jami")
    assert ws.cell(r, 5).value == 1750.5  # 1000 + 250.5 + 500

    # mahsulot bo'yicha: Paket = 1500, Plyonka = 250.5
    rp, _ = _find(ws, "Mahsulot bo'yicha jami")
    got = {ws.cell(rp + i, 4).value: ws.cell(rp + i, 5).value for i in (1, 2)}
    assert got == {"Paket": 1500, "Plyonka": 250.5}

    # stanok bo'yicha: Stanok-1 = 1250.5, Stanok-2 = 500
    rm, _ = _find(ws, "Stanok bo'yicha jami")
    got = {ws.cell(rm + i, 4).value: ws.cell(rm + i, 5).value for i in (1, 2)}
    assert got == {"Stanok-1": 1250.5, "Stanok-2": 500}


def test_totals_are_formulas_with_cached_values():
    formulas = _load(_sample(), values=False)["Ishlab chiqarish"]
    r, _ = _find(formulas, "Jami")
    assert str(formulas.cell(r, 5).value).startswith("=SUM(")
    # hisoblangan qiymat ham saqlangan (telefon/preview uchun)
    assert _load(_sample())["Ishlab chiqarish"].cell(r, 5).value == 1750.5


def test_text_starting_with_equals_is_not_a_formula():
    ws = _load(_sample(), values=False)["Ishlab chiqarish"]
    cell = next(c for row in ws.iter_rows() for c in row if c.value == "=1+1")
    assert cell.data_type == "s"


def test_stock_closing_balance():
    ws = _load(_sample())["Xomashyo"]
    r, _ = _find(ws, "PE-100 — Polietilen")
    assert ws.cell(r, 8).value == 117.75  # 100 + 50 - 30.25 - 2
    r2, _ = _find(ws, "PP-7")
    assert ws.cell(r2, 8).value == -5  # manfiy qoldiq ham ko'rsatiladi

    fp = _load(_sample())["Tayyor mahsulot"]
    r3, _ = _find(fp, "Paket")
    assert fp.cell(r3, 8).value == 1400  # 200 + 1500 - 300


def test_finance_totals_and_net():
    ws = _load(_sample())["Moliya"]
    purchases, _ = _find(ws, "Jami xomashyo xaridi")
    assert ws.cell(purchases, 7).value == 600025.0  # 50 * 12000.50
    sales, _ = _find(ws, "Jami sotuv")
    assert ws.cell(sales, 7).value == 484999.97  # 450000 + 34999.97
    expenses, _ = _find(ws, "Jami xarajat")
    assert ws.cell(expenses, 7).value == 350000.5
    net, _ = _find(ws, "Sof natija (sotuv − xarajat − xomashyo xaridi)")
    assert ws.cell(net, 7).value == -465025.53  # 484999.97 - 350000.5 - 600025


def test_empty_day_still_builds():
    wb = _load(_empty())
    assert wb.sheetnames == ["Ishlab chiqarish", "Xomashyo", "Tayyor mahsulot", "Moliya"]
    _find(wb["Ishlab chiqarish"], "Bu kunda ishlab chiqarish hisoboti kiritilmagan")
    _find(wb["Moliya"], "Bu kunda sotuv yo'q")
    # xulosa nolga teng
    net, _ = _find(wb["Moliya"], "Sof natija (sotuv − xarajat − xomashyo xaridi)")
    assert wb["Moliya"].cell(net, 7).value == 0
