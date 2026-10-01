#!/usr/bin/env sh
# Restore a backup INTO THE LIVE DATABASES (stop web traffic first; see docs/runbooks/backup-restore.md).
# Usage: infra/backup/restore.sh backups/pg-XXXX.dump backups/mongo-XXXX.archive.gz
set -eu
PG="$1"; MONGO="$2"
docker compose stop core-api workers beat ingest-ml realtime demo-simulator
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$PG"
docker compose exec -T mongo mongorestore --quiet --drop --archive --gzip < "$MONGO"
docker compose start core-api workers beat ingest-ml realtime demo-simulator
echo "restore ok"
