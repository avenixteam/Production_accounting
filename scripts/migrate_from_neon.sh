#!/usr/bin/env bash
# Neon'dagi ma'lumotlarni yangi (serverdagi) bazaga ko'chirish.
#   NEON_URL="postgresql://USER:PASS@HOST/DB?sslmode=require" ./scripts/migrate_from_neon.sh
# Oldin: docker compose -f docker-compose.prod.yml up -d db
set -euo pipefail
cd "$(dirname "$0")/.."
: "${NEON_URL:?NEON_URL ozgaruvchisi kerak}"
docker run --rm postgres:16-alpine pg_dump "$NEON_URL" -Fc --no-owner > neon.dump
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U factory -d factory_db --no-owner --clean --if-exists < neon.dump
echo "Ko'chirildi. neon.dump faylini xavfsiz joyga saqlang yoki o'chiring."
