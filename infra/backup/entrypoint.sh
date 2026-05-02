#!/bin/bash
set -e

echo "Backup service starting..."
echo "Schedule: daily at 03:00 (Asia/Almaty)"
echo "Keep last: ${BACKUP_KEEP_DAYS:-30} days"

# Run an initial backup on startup (after 60s wait for DB ready)
(sleep 60 && /usr/local/bin/backup.sh) &

# Start cron in foreground
crond -f -l 8
