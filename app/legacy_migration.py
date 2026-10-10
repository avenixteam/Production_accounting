"""Eski bazani yangi tizimga o'tkazish (SQL). `init_db.py` ishlatadi; qayta ishga tushirilsa ham zarar qilmaydi.

1) Sotuv to'lovlari: eski turlar (naqd/karta/o'tkazma/muddatli) -> to'liq / qisman / nasiya.
   Eski to'lov jadvalidagi to'langan summalar `sale_payments` ga ko'chiriladi.
2) Xarajat kategoriyalari: mavjud xarajatlardagi nomlar kategoriyalar ro'yxatiga qo'shiladi.
"""

# Eski turdagi sotuv bormi?
HAS_LEGACY_SALES = (
    "SELECT COUNT(*) FROM sales WHERE payment_type IN ('cash', 'card', 'transfer', 'installment')"
)

# Tartib muhim: avval to'lovlar ko'chiriladi, keyin turlar yangilanadi
LEGACY_SALES_STEPS = [
    """INSERT INTO sale_payments (sale_id, amount, date, note, created_at)
       SELECT id, total_amount, date, 'Eski tizimdan: to''liq to''lov', created_at
       FROM sales WHERE payment_type IN ('cash', 'card', 'transfer')""",
    """INSERT INTO sale_payments (sale_id, amount, date, note, created_at)
       SELECT s.id, SUM(ps.paid_amount), s.date, 'Eski tizimdan: to''langan qismi', s.created_at
       FROM sales s JOIN payment_schedule ps ON ps.sale_id = s.id
       WHERE s.payment_type = 'installment'
       GROUP BY s.id, s.date, s.created_at
       HAVING SUM(ps.paid_amount) > 0""",
    "UPDATE sales SET payment_type = 'full' WHERE payment_type IN ('cash', 'card', 'transfer')",
    """UPDATE sales SET payment_type = CASE
         WHEN COALESCE((SELECT SUM(p.amount) FROM sale_payments p WHERE p.sale_id = sales.id), 0) >= total_amount
           THEN 'full'
         WHEN COALESCE((SELECT SUM(p.amount) FROM sale_payments p WHERE p.sale_id = sales.id), 0) > 0
           THEN 'partial'
         ELSE 'credit' END
       WHERE payment_type = 'installment'""",
]

SEED_EXPENSE_CATEGORIES = """INSERT INTO expense_categories (name, created_at)
   SELECT DISTINCT category, CURRENT_TIMESTAMP FROM expenses
   WHERE category NOT IN (SELECT name FROM expense_categories)"""
