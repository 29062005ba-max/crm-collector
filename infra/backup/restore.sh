#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: restore.sh <backup_filename>"
    echo "Available backups:"
    ls -lh /backups/crm_backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="/backups/$1"
if [ ! -f "$BACKUP_FILE" ]; then
    BACKUP_FILE="$1"  # full path
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "ERROR: Backup file not found: $1"
        exit 1
    fi
fi

echo "[$(date)] Restoring from $BACKUP_FILE..."
echo "WARNING: This will DROP all current data!"

gunzip -c "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD:-crm}" psql \
    -h "${POSTGRES_HOST:-postgres}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-crm}" \
    -d "${POSTGRES_DB:-crm_db}"

echo "[$(date)] Restore complete!"
