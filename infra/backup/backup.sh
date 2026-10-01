#!/usr/bin/env sh
# Daily backup (JNG-13-03): PostgreSQL (all business data) + MongoDB (listens).
# Redis holds only caches and short-lived state; Qdrant vectors are rebuilt by the nightly job.
# Usage: infra/backup/backup.sh [backup-dir]   (cron: 30 2 * * *)
set -eu
DIR="${1:-./backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DIR"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$DIR/pg-$STAMP.dump"
docker compose exec -T mongo mongodump --quiet --db jingle --archive --gzip > "$DIR/mongo-$STAMP.archive.gz"
# Keep 14 days.
find "$DIR" -name 'pg-*.dump' -mtime +14 -delete 2>/dev/null || true
find "$DIR" -name 'mongo-*.archive.gz' -mtime +14 -delete 2>/dev/null || true
echo "backup ok: $DIR/pg-$STAMP.dump $DIR/mongo-$STAMP.archive.gz"
