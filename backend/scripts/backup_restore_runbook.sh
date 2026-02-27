#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL backup/restore verification helper.
#
# Required env vars:
#   SOURCE_DATABASE_URL          e.g. postgresql://user:pass@host:5432/genxsop
#   RESTORE_DATABASE_URL         e.g. postgresql://user:pass@host:5432/genxsop_restore_check
#
# Optional:
#   BACKUP_DIR (default: ./backups)

if [[ -z "${SOURCE_DATABASE_URL:-}" || -z "${RESTORE_DATABASE_URL:-}" ]]; then
  echo "SOURCE_DATABASE_URL and RESTORE_DATABASE_URL are required"
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "${BACKUP_DIR}"

ts="$(date +%Y%m%d_%H%M%S)"
dump_file="${BACKUP_DIR}/genxsop_${ts}.dump"

echo "[1/4] Creating logical backup: ${dump_file}"
pg_dump --format=custom --file "${dump_file}" "${SOURCE_DATABASE_URL}"

echo "[2/4] Recreating restore target database"
dropdb --if-exists "${RESTORE_DATABASE_URL}" || true
createdb "${RESTORE_DATABASE_URL}"

echo "[3/4] Restoring backup into target"
pg_restore --no-owner --no-privileges --clean --if-exists --dbname "${RESTORE_DATABASE_URL}" "${dump_file}"

echo "[4/4] Running post-restore smoke query"
psql "${RESTORE_DATABASE_URL}" -c "SELECT NOW() AS restore_checked_at;"

echo "Backup + restore verification completed successfully"
echo "Backup artifact: ${dump_file}"
