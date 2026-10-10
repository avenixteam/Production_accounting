"""Jadvallarni yaratadi va mavjud bazaga yangi ustunlarni xavfsiz qo'shadi (idempotent).

Ishga tushirish:  python init_db.py
"""
from sqlalchemy import inspect, text

import app.models  # noqa: F401
from app.database import Base, engine
from app.legacy_migration import HAS_LEGACY_SALES, LEGACY_SALES_STEPS, SEED_EXPENSE_CATEGORIES

# (jadval, ustun, SQL turi) - eski bazada yo'q bo'lishi mumkin bo'lgan ustunlar
NEW_COLUMNS = [
    ("raw_material_movements", "receipt_id", "INTEGER REFERENCES raw_material_receipts(id)"),
    ("finished_product_movements", "sale_id", "INTEGER REFERENCES sales(id)"),
    ("raw_material_receipts", "unit_price", "NUMERIC(14, 2)"),
    ("products", "price", "NUMERIC(14, 2) NOT NULL DEFAULT 0"),
]


def main():
    Base.metadata.create_all(bind=engine)

    # create_all mavjud jadvallarga indeks qo'shmaydi - shuning uchun alohida (idempotent)
    created = 0
    for table in Base.metadata.sorted_tables:
        have = {i["name"] for i in inspect(engine).get_indexes(table.name)}
        for idx in table.indexes:
            if idx.name not in have:
                idx.create(bind=engine, checkfirst=True)
                created += 1
    if created:
        print(f"+ {created} ta indeks yaratildi")

    insp = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in NEW_COLUMNS:
            existing = {c["name"] for c in insp.get_columns(table)}
            if column not in existing:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))
                print(f"+ {table}.{column} qo'shildi")

    with engine.begin() as conn:
        # Ombor olib tashlangach sotuvda hamkor tanlash shart emas (faqat PostgreSQL)
        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE sale_items ALTER COLUMN partner_id DROP NOT NULL"))

        # Eski sotuvlar: naqd/karta/muddatli -> to'liq/qisman/nasiya (to'lovlar saqlanadi)
        if conn.execute(text(HAS_LEGACY_SALES)).scalar():
            for step in LEGACY_SALES_STEPS:
                conn.execute(text(step))
            print("+ eski sotuvlar yangi to'lov tizimiga o'tkazildi")

        # Mavjud xarajatlardagi nomlar -> kategoriyalar ro'yxati
        res = conn.execute(text(SEED_EXPENSE_CATEGORIES))
        if res.rowcount:
            print(f"+ {res.rowcount} ta xarajat kategoriyasi qo'shildi")
    print("Barcha jadvallar tayyor!")


if __name__ == "__main__":
    main()
