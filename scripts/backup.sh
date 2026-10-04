#!/usr/bin/env bash
# Kunlik zaxira: ./scripts/backup.sh   (cron: 0 2 * * * /home/ubuntu/Production_accounting/scripts/backup.sh)
# 14 kunlik nusxa saqlanadi. Tashqi joyga (rclone) nusxalash uchun oxirgi qatorni yoqing.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
FILE="backups/factory_$(date +%Y%m%d_%H%M%S).dump"
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U factory -d factory_db -Fc > "$FILE"
[ -s "$FILE" ] || { echo "Backup bo'sh chiqdi!"; rm -f "$FILE"; exit 1; }
find backups -name 'factory_*.dump' -mtime +14 -delete
echo "OK: $FILE ($(du -h "$FILE" | cut -f1))"
# rclone copy "$FILE" remote:factory-backups/    # <- Google Drive / boshqa bulutga (rclone config kerak)
