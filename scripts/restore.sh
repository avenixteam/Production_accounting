#!/usr/bin/env bash
# Tiklash: ./scripts/restore.sh backups/factory_YYYYMMDD_HHMMSS.dump
# DIQQAT: bazadagi hozirgi ma'lumotlar o'chirilib, nusxadagisi bilan almashtiriladi.
set -euo pipefail
cd "$(dirname "$0")/.."
FILE="${1:?Fayl yoli kerak}"
read -r -p "Hozirgi baza o'chiriladi va '$FILE' dan tiklanadi. Davom etasizmi? (ha/yoq) " a
[ "$a" = "ha" ] || exit 1
docker compose -f docker-compose.prod.yml stop backend
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U factory -d factory_db --clean --if-exists --no-owner < "$FILE"
docker compose -f docker-compose.prod.yml start backend
echo "Tiklandi."
