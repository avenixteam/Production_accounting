"""Kunlik hisobotni Excel (.xlsx) faylga aylantiradi.

Bu modul ma'lumotlar bazasiga BOG'LIQ EMAS: `daily_report.collect()` tayyorlagan oddiy
lug'atlarni oladi va .xlsx baytlarini qaytaradi (shu sababli uni alohida sinash oson).
Yig'indilar FORMULA bilan yoziladi; hisoblangan qiymat ham saqlanadi (telefon ko'rinishi uchun).

Kutiladigan `data`: date, generated_at, production, receipts, sales, payments, expenses.
"""
from __future__ import annotations

import io
from decimal import ROUND_HALF_UP, Decimal

import xlsxwriter
from xlsxwriter.utility import xl_range, xl_range_abs, xl_rowcol_to_cell

FONT = "Arial"
NAVY = "#1E3A5F"
GRID = "#C9CFD8"
SOFT = "#F3F5F9"
MUTED = "#6B7280"

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

STATUS_LABELS = {
    "paid": "To'langan",
    "partial": "Qisman",
    "unpaid": "Nasiya",
}

ZERO = Decimal("0")


# ---------------------------------------------------------------- yordamchilar
def _d(value) -> Decimal:
    """Son -> Decimal (float xatoliklarisiz). None -> 0."""
    if value is None or value == "":
        return ZERO
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round2(value) -> Decimal:
    return _d(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _f(value) -> float:
    """Excelga yoziladigan son (3 xonagacha yaxlitlanadi - bazadagi aniqlik shunday)."""
    return float(_d(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def _is_whole(value) -> bool:
    v = float(value)
    return abs(v - round(v)) < 1e-9


class _Styles:
    """Excel kataklari uchun uslublar (bir xil uslub bir marta yaratiladi)."""

    def __init__(self, wb):
        self.wb = wb
        self._cache: dict = {}

    def fmt(self, **props):
        key = tuple(sorted(props.items()))
        f = self._cache.get(key)
        if f is None:
            f = self.wb.add_format({"font_name": FONT, "font_size": 10, "valign": "vcenter", **props})
            self._cache[key] = f
        return f

    def title(self):
        return self.fmt(bold=True, font_size=14, font_color=NAVY)

    def section(self):
        return self.fmt(bold=True, font_size=11, font_color=NAVY)

    def meta(self, **kw):
        return self.fmt(font_color=MUTED, **kw)

    def head(self):
        return self.fmt(bold=True, font_color="#FFFFFF", bg_color=NAVY, border=1,
                        border_color=NAVY, text_wrap=True, align="center")

    def cell(self, **kw):
        return self.fmt(border=1, border_color=GRID, **kw)

    def text(self, **kw):
        return self.cell(text_wrap=True, indent=1, **kw)

    def empty_note(self):
        return self.cell(italic=True, font_color=MUTED, align="center")

    def number(self, value, money=False, decimals=None, **kw):
        """Miqdor: butun bo'lsa '1,250', kasr bo'lsa '1,250.5'.
        Pul: `decimals` berilsa butun jadval bir xil ('.00' bor yoki yo'q) bo'ladi."""
        if money:
            frac = (not _is_whole(value)) if decimals is None else decimals
            nf = "#,##0.00" if frac else "#,##0"
        else:
            nf = "#,##0" if _is_whole(value) else "#,##0.0##"
        return self.cell(num_format=nf, align="right", **kw)

    def total_label(self):
        return self.cell(bold=True, bg_color=SOFT, align="right")

    def total_blank(self):
        return self.cell(bg_color=SOFT)

    def total_number(self, value, money=False, decimals=None):
        return self.number(value, money=money, decimals=decimals, bold=True, bg_color=SOFT)


def _prepare(ws, widths, landscape=True):
    for col, w in enumerate(widths):
        ws.set_column(col, col, w)
    ws.hide_gridlines(2)
    if landscape:
        ws.set_landscape()
    ws.set_paper(9)  # A4
    ws.fit_to_pages(1, 0)
    ws.set_margins(left=0.4, right=0.4, top=0.5, bottom=0.6)
    ws.set_footer("&L&8Zavod hisobi&R&8&P / &N")


def _title_block(ws, st, title: str, data: dict, last_col: int) -> None:
    """1-2 qatorlar: sarlavha, sana va tuzilgan vaqt."""
    ws.merge_range(0, 0, 0, last_col, title, st.title())
    ws.set_row(0, 24)
    ws.merge_range(1, 0, 1, 2, f"Sana: {data['date'].strftime('%d.%m.%Y')}", st.fmt(bold=True, align="left"))
    stamp = f"Tuzilgan: {data['generated_at'].strftime('%d.%m.%Y %H:%M')}"
    ws.merge_range(1, max(last_col - 2, 2), 1, last_col, stamp, st.meta(align="right"))


def _write_headers(ws, st, row: int, headers: list[str], height: int = 30) -> None:
    for col, text in enumerate(headers):
        ws.write_string(row, col, text, st.head())
    ws.set_row(row, height)


def _cell_ref(row: int, col: int, absolute: bool = False) -> str:
    return xl_rowcol_to_cell(row, col, row_abs=absolute, col_abs=absolute)


# ---------------------------------------------------------------- 1-varaq: ishlab chiqarish
def _production_sheet(wb, st: _Styles, data: dict) -> None:
    ws = wb.add_worksheet("Ishlab chiqarish")
    _prepare(ws, [5, 18, 20, 30, 13, 9, 11, 36])
    _title_block(ws, st, "Kunlik ishlab chiqarish hisoboti", data, last_col=7)

    head_row = 3
    _write_headers(ws, st, head_row, ["№", "Stanok", "Hamkor", "Mahsulot", "Miqdor", "Birlik", "Hisobot №", "Izoh"], 22)
    ws.freeze_panes(head_row + 1, 0)

    lines = []
    for rep in data["production"]:
        for it in rep["items"]:
            lines.append({
                "machine": rep.get("machine_name") or "", "partner": it["partner_name"],
                "product": it["product_name"], "qty": _d(it["quantity"]), "unit": it["unit"],
                "report_id": rep["id"], "note": rep.get("note") or "",
            })

    row = head_row + 1
    if not lines:
        ws.merge_range(row, 0, row, 7, "Bu kunda ishlab chiqarish hisoboti kiritilmagan", st.empty_note())
        return

    first = row
    for n, ln in enumerate(lines, start=1):
        ws.write_number(row, 0, n, st.cell(align="center"))
        ws.write_string(row, 1, ln["machine"], st.text())
        ws.write_string(row, 2, ln["partner"], st.text())
        ws.write_string(row, 3, ln["product"], st.text())
        ws.write_number(row, 4, _f(ln["qty"]), st.number(ln["qty"]))
        ws.write_string(row, 5, ln["unit"], st.cell(align="center"))
        ws.write_number(row, 6, ln["report_id"], st.cell(align="center"))
        ws.write_string(row, 7, ln["note"], st.text())
        row += 1
    last = row - 1

    # Jami (formula)
    total = sum((ln["qty"] for ln in lines), ZERO)
    units = {ln["unit"] for ln in lines}
    ws.merge_range(row, 0, row, 3, "Jami", st.total_label())
    qty_range = xl_range(first, 4, last, 4)
    ws.write_formula(row, 4, f"=SUM({qty_range})", st.total_number(total), _f(total))
    ws.write_string(row, 5, units.pop() if len(units) == 1 else "", st.cell(bg_color=SOFT, align="center", bold=True))
    ws.write_blank(row, 6, None, st.total_blank())
    ws.write_blank(row, 7, None, st.total_blank())
    row += 2

    # Mahsulotlar bo'yicha jami. SUMPRODUCT - nomdagi '*' yoki '?' belgilari xato moslashmasligi uchun.
    prod_rng = xl_range_abs(first, 3, last, 3)
    mach_rng = xl_range_abs(first, 1, last, 1)
    qty_rng = xl_range_abs(first, 4, last, 4)

    ws.write_string(row, 3, "Mahsulot bo'yicha jami", st.head())
    ws.write_string(row, 4, "Miqdor", st.head())
    ws.write_string(row, 5, "Birlik", st.head())
    row += 1
    seen: dict[str, dict] = {}
    for ln in lines:
        s = seen.setdefault(ln["product"], {"unit": ln["unit"], "qty": ZERO})
        s["qty"] += ln["qty"]
    for name, s in seen.items():
        ws.write_string(row, 3, name, st.text())
        ws.write_formula(
            row, 4, f"=SUMPRODUCT(--({prod_rng}={_cell_ref(row, 3)}),{qty_rng})",
            st.number(s["qty"]), _f(s["qty"]),
        )
        ws.write_string(row, 5, s["unit"], st.cell(align="center"))
        row += 1
    row += 1

    ws.write_string(row, 3, "Stanok bo'yicha jami", st.head())
    ws.write_string(row, 4, "Miqdor", st.head())
    ws.write_blank(row, 5, None, st.head())
    row += 1
    by_machine: dict[str, Decimal] = {}
    for ln in lines:
        by_machine[ln["machine"]] = by_machine.get(ln["machine"], ZERO) + ln["qty"]
    for name, qty in by_machine.items():
        ws.write_string(row, 3, name, st.text())
        ws.write_formula(
            row, 4, f"=SUMPRODUCT(--({mach_rng}={_cell_ref(row, 3)}),{qty_rng})",
            st.number(qty), _f(qty),
        )
        ws.write_blank(row, 5, None, st.cell())
        row += 1


# ---------------------------------------------------------------- 2-varaq: moliya
def _section(ws, st, row: int, text: str) -> int:
    ws.merge_range(row, 0, row, 7, text, st.section())
    ws.set_row(row, 20)
    return row + 1


def _finance_sheet(wb, st: _Styles, data: dict) -> None:
    ws = wb.add_worksheet("Moliya")
    _prepare(ws, [10, 24, 22, 30, 12, 15, 17, 34])
    _title_block(ws, st, "Kunlik moliya: xomashyo kirimi, sotuv, to'lovlar va xarajatlar", data, last_col=7)

    # Pul summalarida tiyin bor-yo'qligi: butun varaq uchun bir xil format
    priced = [r for r in data["receipts"] if r.get("unit_price") is not None]
    frac = any(not _is_whole(r["unit_price"]) or not _is_whole(_d(r["quantity"]) * _d(r["unit_price"]))
               for r in priced)
    frac = frac or any(not _is_whole(it["unit_price"]) or not _is_whole(it["total_price"])
                       for s in data["sales"] for it in s["items"])
    frac = frac or any(not _is_whole(p["amount"]) for p in data["payments"])
    frac = frac or any(not _is_whole(s["debt"]) for s in data["sales"])
    frac = frac or any(not _is_whole(e["amount"]) for e in data["expenses"])

    def money(value, **kw):
        return st.number(value, money=True, decimals=frac, **kw)

    def money_total(value):
        return st.total_number(value, money=True, decimals=frac)

    def total_row(row, label, first, count, total):
        """Jami qatori: SUM formulasi (ma'lumot bo'lmasa 0)."""
        ws.merge_range(row, 0, row, 5, label, st.total_label())
        if count:
            ws.write_formula(row, 6, f"=SUM({xl_range(first, 6, first + count - 1, 6)})",
                             money_total(total), float(total))
        else:
            ws.write_number(row, 6, 0, money_total(0))
        ws.write_blank(row, 7, None, st.total_blank())

    row = 3

    # --- Xomashyo kirimi
    row = _section(ws, st, row, "Xomashyo kirimi (xarid)")
    _write_headers(ws, st, row, ["№", "Hamkor", "Xomashyo", "Yetkazib beruvchi", "Miqdor",
                                 "Narxi (so'm)", "Summa (so'm)", "To'lov turi / izoh"], 22)
    row += 1
    rec_first, rec_total = row, ZERO
    if not data["receipts"]:
        ws.merge_range(row, 0, row, 7, "Bu kunda xomashyo kirimi yo'q", st.empty_note())
        row += 1
    for n, r in enumerate(data["receipts"], start=1):
        ws.write_number(row, 0, n, st.cell(align="center"))
        ws.write_string(row, 1, r["partner_name"], st.text())
        ws.write_string(row, 2, f"{r['brand']} ({r['unit']})", st.text())
        ws.write_string(row, 3, r.get("supplier_name") or "", st.text())
        ws.write_number(row, 4, _f(r["quantity"]), st.number(r["quantity"]))
        if r.get("unit_price") is not None:
            amount = _round2(_d(r["quantity"]) * _d(r["unit_price"]))
            rec_total += amount
            ws.write_number(row, 5, float(_round2(r["unit_price"])), money(r["unit_price"]))
            ws.write_formula(row, 6, f"=ROUND({_cell_ref(row, 4)}*{_cell_ref(row, 5)},2)",
                             money(amount), float(amount))
        else:
            ws.write_blank(row, 5, None, st.cell())
            ws.write_blank(row, 6, None, st.cell())
        extra = " / ".join(x for x in (r.get("payment_type"), r.get("note")) if x)
        ws.write_string(row, 7, extra, st.text())
        row += 1
    rec_total_row = row
    total_row(row, "Jami xomashyo xaridi", rec_first, len(data["receipts"]), rec_total)
    row += 2

    # --- Sotuvlar
    row = _section(ws, st, row, "Sotuvlar")
    _write_headers(ws, st, row, ["Sotuv №", "Mijoz", "To'lov holati", "Mahsulot", "Miqdor",
                                 "Narxi (so'm)", "Summa (so'm)", "Hamkor / izoh"], 22)
    row += 1
    sale_first, sale_total, sale_lines = row, ZERO, 0
    if not data["sales"]:
        ws.merge_range(row, 0, row, 7, "Bu kunda sotuv yo'q", st.empty_note())
        row += 1
    for s in data["sales"]:
        for it in s["items"]:
            amount = _d(it["total_price"])
            sale_total += amount
            sale_lines += 1
            ws.write_number(row, 0, s["id"], st.cell(align="center"))
            ws.write_string(row, 1, s.get("customer_name") or "", st.text())
            ws.write_string(row, 2, STATUS_LABELS.get(s.get("status"), s.get("status") or ""), st.text())
            ws.write_string(row, 3, f"{it['product_name']} ({it['unit']})", st.text())
            ws.write_number(row, 4, _f(it["quantity"]), st.number(it["quantity"]))
            ws.write_number(row, 5, float(_round2(it["unit_price"])), money(it["unit_price"]))
            ws.write_formula(row, 6, f"=ROUND({_cell_ref(row, 4)}*{_cell_ref(row, 5)},2)",
                             money(amount), float(amount))
            tail = "; ".join(x for x in (it.get("partner_name"), s.get("note")) if x)
            ws.write_string(row, 7, tail, st.text())
            row += 1
    sale_total_row = row
    total_row(row, "Jami sotuv", sale_first, sale_lines, sale_total)
    row += 2

    # --- Shu kuni qabul qilingan to'lovlar (eski qarz bo'yicha ham)
    row = _section(ws, st, row, "Shu kuni qabul qilingan to'lovlar")
    ws.write_string(row, 0, "Sotuv №", st.head())
    ws.write_string(row, 1, "Mijoz", st.head())
    ws.merge_range(row, 2, row, 5, "Izoh", st.head())
    ws.write_string(row, 6, "Summa (so'm)", st.head())
    ws.write_blank(row, 7, None, st.head())
    ws.set_row(row, 22)
    row += 1
    pay_first, pay_total = row, ZERO
    if not data["payments"]:
        ws.merge_range(row, 0, row, 7, "Bu kunda to'lov qabul qilinmagan", st.empty_note())
        row += 1
    for p in data["payments"]:
        amount = _d(p["amount"])
        pay_total += amount
        ws.write_number(row, 0, p["sale_id"], st.cell(align="center"))
        ws.write_string(row, 1, p.get("customer_name") or "", st.text())
        ws.merge_range(row, 2, row, 5, p.get("note") or "", st.text())
        ws.write_number(row, 6, float(_round2(amount)), money(amount))
        ws.write_blank(row, 7, None, st.cell())
        row += 1
    pay_total_row = row
    total_row(row, "Jami qabul qilingan to'lov", pay_first, len(data["payments"]), pay_total)
    row += 2

    # --- Xarajatlar (kategoriya bo'yicha tartiblangan)
    row = _section(ws, st, row, "Xarajatlar")
    ws.write_string(row, 0, "№", st.head())
    ws.write_string(row, 1, "Kategoriya", st.head())
    ws.merge_range(row, 2, row, 5, "Nima uchun", st.head())
    ws.write_string(row, 6, "Summa (so'm)", st.head())
    ws.write_blank(row, 7, None, st.head())
    ws.set_row(row, 22)
    row += 1
    expenses = sorted(data["expenses"], key=lambda e: (e["category"].lower(), e.get("id", 0)))
    exp_first, exp_total = row, ZERO
    if not expenses:
        ws.merge_range(row, 0, row, 7, "Bu kunda xarajat yo'q", st.empty_note())
        row += 1
    for n, e in enumerate(expenses, start=1):
        amount = _d(e["amount"])
        exp_total += amount
        ws.write_number(row, 0, n, st.cell(align="center"))
        ws.write_string(row, 1, e["category"], st.text())
        ws.merge_range(row, 2, row, 5, e.get("description") or "", st.text())
        ws.write_number(row, 6, float(_round2(amount)), money(amount))
        ws.write_blank(row, 7, None, st.cell())
        row += 1
    exp_total_row = row
    total_row(row, "Jami xarajat", exp_first, len(expenses), exp_total)
    row += 1

    if expenses:  # kategoriya bo'yicha jami (SUMPRODUCT: nomdagi '*' kabi belgilar xato moslashmasligi uchun)
        row += 1
        cat_rng = xl_range_abs(exp_first, 1, exp_first + len(expenses) - 1, 1)
        amt_rng = xl_range_abs(exp_first, 6, exp_first + len(expenses) - 1, 6)
        ws.write_string(row, 1, "Kategoriya bo'yicha jami", st.head())
        ws.merge_range(row, 2, row, 5, "", st.head())
        ws.write_string(row, 6, "Summa (so'm)", st.head())
        row += 1
        by_cat: dict[str, Decimal] = {}
        for e in expenses:
            by_cat[e["category"]] = by_cat.get(e["category"], ZERO) + _d(e["amount"])
        for name, value in by_cat.items():
            ws.write_string(row, 1, name, st.text())
            ws.merge_range(row, 2, row, 5, "", st.cell())
            ws.write_formula(
                row, 6, f"=SUMPRODUCT(--({cat_rng}={_cell_ref(row, 1)}),{amt_rng})",
                money(value), float(_round2(value)),
            )
            row += 1
    row += 1

    # --- Kun xulosasi (sof natija: sotuv − xarajat − xomashyo xaridi)
    row = _section(ws, st, row, "Kun xulosasi")
    net = sale_total - exp_total - rec_total
    for label, ref, value in (
        ("Sotuv jami", sale_total_row, sale_total),
        ("Xarajatlar jami", exp_total_row, exp_total),
        ("Xomashyo xaridi jami", rec_total_row, rec_total),
    ):
        ws.merge_range(row, 0, row, 5, label, st.cell())
        ws.write_formula(row, 6, f"={_cell_ref(ref, 6)}", money(value), float(_round2(value)))
        row += 1
    s_ref, e_ref, r_ref = (_cell_ref(sale_total_row, 6), _cell_ref(exp_total_row, 6), _cell_ref(rec_total_row, 6))
    ws.merge_range(row, 0, row, 5, "Sof natija (sotuv − xarajat − xomashyo xaridi)", st.total_label())
    ws.write_formula(row, 6, f"={s_ref}-{e_ref}-{r_ref}", money_total(net), float(_round2(net)))
    row += 2

    day_debt = sum((_d(s["debt"]) for s in data["sales"]), ZERO)
    ws.merge_range(row, 0, row, 5, "Shu kuni qabul qilingan to'lovlar (jami)", st.cell())
    ws.write_formula(row, 6, f"={_cell_ref(pay_total_row, 6)}", money(pay_total), float(_round2(pay_total)))
    row += 1
    ws.merge_range(row, 0, row, 5, "Shu kungi sotuvlardan hozirgi qarz", st.cell())
    ws.write_number(row, 6, float(_round2(day_debt)), money(day_debt))
    row += 1
    ws.merge_range(
        row, 0, row, 7,
        "Sof natija sotuv summasi bo'yicha hisoblanadi (nasiyaga berilgani ham kiradi). "
        "Narxi kiritilmagan kirimlar xarid summasiga kirmaydi.",
        st.meta(text_wrap=True),
    )
    ws.set_row(row, 28)


# ---------------------------------------------------------------- asosiy funksiya
def build_workbook(data: dict) -> bytes:
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {
        "in_memory": True,
        # Izoh/nom '=' yoki 'http' bilan boshlansa ham oddiy matn bo'lib qolsin
        "strings_to_formulas": False,
        "strings_to_urls": False,
        "strings_to_numbers": False,
    })
    wb.formats[0].set_font_name(FONT)  # bo'sh kataklar uchun ham bir xil shrift
    wb.formats[0].set_font_size(10)
    wb.set_properties({
        "title": f"Kunlik hisobot {data['date'].strftime('%d.%m.%Y')}",
        "subject": "Zavod kunlik hisoboti",
        "author": "Zavod hisobi",
    })
    st = _Styles(wb)

    _production_sheet(wb, st, data)
    _finance_sheet(wb, st, data)

    wb.close()
    return buf.getvalue()
