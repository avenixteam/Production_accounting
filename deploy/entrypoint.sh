#!/bin/sh
set -e
# Jadvallar, yangi ustunlar va indekslarni (idempotent) tayyorlaydi
python init_db.py
# Orqada ishlovchi worker'lar soni: 2 CPU uchun 2-3 yetarli
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w "${WEB_CONCURRENCY:-2}" \
  -b 0.0.0.0:8000 \
  --timeout 60 --graceful-timeout 30 --keep-alive 5 \
  --access-logfile - --forwarded-allow-ips="*"
