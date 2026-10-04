# Production Accounting — ishlab chiqarish zavodi hisob tizimi

FastAPI + PostgreSQL (backend) va React + Vite (frontend).

## Tizim qanday ishlaydi

```
Xomashyo kirimi ──► Ombor (xomashyo, hamkor kesimida)
                        │  retsept bo'yicha avtomatik yechiladi
Ishlab chiqarish ───────┤
(stanok, kun, mahsulot) └──► Ombor (tayyor mahsulot, hamkor kesimida)
                                   │
Sotuv (naqd / karta / o'tkazma / muddatli) ◄┘
   └─ muddatli bo'lsa ──► To'lov jadvali ──► Qarzdorlik
Xarajatlar ─────────────────────────────────► Boshqaruv paneli (sof natija)
```

Asosiy qoidalar:

- **Qoldiq hech qachon alohida saqlanmaydi** — u har doim harakatlar jurnali (`*_movements`) yig'indisidan hisoblanadi, shuning uchun jurnalga zid kelmaydi.
- **Retsept** — 1 birlik mahsulotga qancha xomashyo ketishi. Ishlab chiqarish hisobotida xomashyo shu bo'yicha avtomatik hisoblanadi.
- Xomashyo yetmasa ishlab chiqarish saqlanmaydi (ixtiyoriy ravishda "minusga ruxsat" belgilanishi mumkin).
- Ombordagidan ko'p mahsulot sotib bo'lmaydi.
- Hujjatlarni bekor qilish (ishlab chiqarish, sotuv, kirim) ombor qoldig'ini avtomatik qaytaradi; agar bekor qilish qoldiqni minusga tushirsa — taqiqlanadi.
- Ma'lumotnomalar (hamkor, mahsulot va h.k.) o'chirilmaydi, **faolsizlantiriladi** — tarixiy hujjatlar buzilmasligi uchun.
- Muddatli to'lov qabul qilinganda summa eng eski muddatdan boshlab (FIFO) taqsimlanadi.

## Lokal ishga tushirish (kompyuteringizda)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # SECRET_KEY ni to'ldiring (pastda)
docker compose up -d          # lokal PostgreSQL (127.0.0.1:5432)
python init_db.py             # jadvallar + yangi ustunlar + indekslar
python create_user.py admin --role admin     # birinchi admin (parol so'raydi)
python seed.py                # (ixtiyoriy) demo ma'lumot; requirements-dev.txt kerak
uvicorn app.main:app --reload --port 8001

cd frontend && npm install && npm run dev      # http://localhost:5173  (/api -> 8001 proxy)
```

`SECRET_KEY` yaratish: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

Testlar (SQLite'da, asosiy bazaga tegmaydi): `pip install -r requirements-dev.txt && pytest`

## Production: serverga joylashtirish (Docker)

```
Internet -> Caddy (80/443, HTTPS) -> /     statik frontend
                                  -> /api  gunicorn + FastAPI -> PostgreSQL (faqat ichki tarmoq)
```

```bash
cp .env.example .env     # SECRET_KEY, POSTGRES_PASSWORD, SITE_ADDRESS ni to'ldiring
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend python create_user.py admin --role admin
```

Sayt: `http://SERVER_IP` (yoki SITE_ADDRESS dagi domen, HTTPS bilan). Jadvallar va indekslar backend ishga tushganda avtomatik yaratiladi.

**Neon'dan ko'chirish:**
```bash
docker compose -f docker-compose.prod.yml up -d db
NEON_URL="postgresql://USER:PASS@HOST/DB?sslmode=require" ./scripts/migrate_from_neon.sh
docker compose -f docker-compose.prod.yml up -d
```

**Zaxira nusxa:** `./scripts/backup.sh` (cron: `0 2 * * * /yo/l/Production_accounting/scripts/backup.sh`), tiklash: `./scripts/restore.sh backups/FAYL.dump`.
Nusxalarni ALBATTA serverdan tashqariga ham ko'chiring (`rclone`), va tiklashni bir marta sinab ko'ring.

**Yangilash:** `git pull` (yoki yangi fayllarni yuklab) -> `docker compose -f docker-compose.prod.yml up -d --build`.
**Loglar:** `docker compose -f docker-compose.prod.yml logs -f backend`.

Batafsil bepul 24/7 joylashtirish qo'llanmasi: [DEPLOY_FREE.md](DEPLOY_FREE.md).

## Xavfsizlik

- Barcha endpointlar login talab qiladi (JWT, 12 soat). `/health` ochiq (monitoring uchun).
- Rollar: **admin** (hammasi + foydalanuvchilar boshqaruvi), **staff** (kiritish/ko'rish, lekin hujjatni bekor qila/o'chira olmaydi).
- Login'ga 5 daqiqada 8 ta xato urinishdan keyin vaqtincha cheklov qo'yiladi.
- Parollar scrypt bilan hash qilinadi. Token brauzerda localStorage'da saqlanadi.
- `AUTH_DISABLED=1` faqat lokal sinov uchun. Production'da qo'ymang.

## Tezlik uchun nimalar qilingan

- Indekslar (`app/models/indexes.py`): ombor qoldig'i va sana filtrlari tez ishlaydi. `init_db.py` ularni mavjud bazaga ham qo'shadi.
- Xomashyo/mahsulot qoldig'i bitta so'rovda hisoblanadi (oldin har qator uchun alohida edi).
- Sotuvlar `status` filtri SQL darajasida (oldin `limit` dan keyin filtrlanib, eski yozuvlar yo'qolardi).
- Parallel ishlashda qoldiq minusga tushmasligi uchun hamkor qatorlari bloklanadi (`SELECT ... FOR UPDATE`).
- Frontend: sahifalar bo'lib yuklanadi, javoblar keshlanadi, qidiruvga 300 ms debounce, Caddy siqish (gzip/zstd) va uzoq kesh.
- Baza backend bilan bir serverda: har so'rov ~1 ms (bulut bazada ~100-200 ms edi).

## Loyiha tuzilmasi

```
app/
  models/      SQLAlchemy modellari (jadvallar)
  schemas/     Pydantic: kiruvchi ma'lumotlar validatsiyasi
  services/    Biznes mantiq: stock, production, sales, reports
  routers/     HTTP endpointlar (_crud.py - ma'lumotnomalar uchun umumiy CRUD)
frontend/src/
  pages/       Sahifalar (Dashboard, Production, Sales, Inventory, ...)
  components/  Umumiy UI: Modal, Table, MasterPage, Toast, Layout
tests/         pytest: ishlab chiqarish → sotuv → to'lov oqimi
```

## Asosiy endpointlar

| Bo'lim | Endpoint |
|---|---|
| Ma'lumotnomalar | `/partners`, `/raw-materials`, `/products`, `/machines`, `/customers` (GET/POST/PUT/DELETE) |
| Retsept | `GET/PUT /products/{id}/recipe` |
| Xomashyo kirimi | `/inventory/receipts` |
| Ishlab chiqarish | `/production`, `POST /production/preview` (kerakli xomashyoni oldindan hisoblash) |
| Ombor | `/inventory/raw-materials`, `/inventory/finished-products`, `.../movements`, `.../adjust` |
| Sotuv | `/sales`, `POST /sales/{id}/payments`, `GET /sales/debts` |
| Xarajatlar | `/expenses`, `/expenses/summary`, `/expenses/categories` |
| Hisobot | `GET /reports/summary?date_from=&date_to=` |

## Eslatma: eski bazadan yangilash

Modellarga to'rtta yangi ustun qo'shildi (`products.price`, `raw_material_receipts.unit_price`,
`raw_material_movements.receipt_id`, `finished_product_movements.sale_id`).
`python init_db.py` ularni mavjud bazaga avtomatik qo'shadi (ma'lumotlar saqlanadi). Docker'da bu har ishga tushishda o'zi bajariladi.
