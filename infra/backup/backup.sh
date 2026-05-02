#!/bin/bash
set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="crm_backup_${TIMESTAMP}.sql.gz"
KEEP_DAYS=${BACKUP_KEEP_DAYS:-30}

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

PGPASSWORD="${POSTGRES_PASSWORD:-crm}" pg_dump \
    -h "${POSTGRES_HOST:-postgres}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-crm}" \
    -d "${POSTGRES_DB:-crm_db}" \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
    | gzip > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "[$(date)] Backup created: ${FILENAME} (${SIZE})"

# Cleanup old backups (keep last N days)
DELETED=$(find "$BACKUP_DIR" -name "crm_backup_*.sql.gz" -type f -mtime +${KEEP_DAYS} -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date)] Cleanup: deleted ${DELETED} old backups (older than ${KEEP_DAYS} days)"
fi

# List existing backups
TOTAL=$(find "$BACKUP_DIR" -name "crm_backup_*.sql.gz" -type f | wc -l)
echo "[$(date)] Total backups: ${TOTAL}"
