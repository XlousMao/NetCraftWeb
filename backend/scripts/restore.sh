#!/usr/bin/env bash
# PostgreSQL 恢复脚本：从 pg_dump 备份恢复 GEAP 数据库。
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "用法: $0 <备份文件>"
  exit 1
fi

DB_USER="${POSTGRES_USER:-geap}"
DB_NAME="${POSTGRES_DB:-geap}"
DB_HOST="${POSTGRES_HOST:-db}"

echo "[restore] 从 $1 恢复 $DB_NAME ..."
pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists "$1"

echo "[restore] 完成"
