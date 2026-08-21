#!/usr/bin/env bash
# PostgreSQL 备份脚本：使用 pg_dump 导出 GEAP 数据库。
set -euo pipefail

DB_USER="${POSTGRES_USER:-geap}"
DB_NAME="${POSTGRES_DB:-geap}"
DB_HOST="${POSTGRES_HOST:-db}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT="$BACKUP_DIR/geap_${TIMESTAMP}.sql"

echo "[backup] 备份 $DB_NAME 到 $OUTPUT ..."
pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -Fc -f "$OUTPUT"

echo "[backup] 完成：$OUTPUT"
