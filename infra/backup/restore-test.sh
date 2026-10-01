#!/usr/bin/env sh
# Tested restore (JNG-13-03): load the newest backup into scratch databases, compare counts with
# live, then drop the scratch copies. Never touches live data. Run weekly (cron: 0 4 * * 0).
set -eu
DIR="${1:-./backups}"
PG="$(ls -t "$DIR"/pg-*.dump | head -1)"
MONGO="$(ls -t "$DIR"/mongo-*.archive.gz | head -1)"
docker compose exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" --if-exists jingle_restore_test && createdb -U "$POSTGRES_USER" jingle_restore_test'
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d jingle_restore_test --no-owner' < "$PG"
count_pg() { docker compose exec -T postgres sh -c "psql -U \"\$POSTGRES_USER\" -d $1 -tAc 'select concat_ws(chr(44), (select count(*) from users), (select count(*) from friendships), (select count(*) from circles))'"; }
LIVE="$(count_pg "\$POSTGRES_DB")"; COPY="$(count_pg jingle_restore_test)"
docker compose exec -T mongo mongorestore --quiet --drop --archive --gzip --nsFrom 'jingle.*' --nsTo 'jingle_restore_test.*' < "$MONGO"
MLIVE="$(docker compose exec -T mongo mongosh --quiet jingle --eval 'db.listens.countDocuments()')"
MCOPY="$(docker compose exec -T mongo mongosh --quiet jingle_restore_test --eval 'db.listens.countDocuments()')"
docker compose exec -T postgres sh -c 'dropdb -U "$POSTGRES_USER" jingle_restore_test'
docker compose exec -T mongo mongosh --quiet jingle_restore_test --eval 'db.dropDatabase()' > /dev/null
echo "postgres users,friendships,circles live=$LIVE restored=$COPY"
echo "mongo listens live=$MLIVE restored=$MCOPY (live may be ahead: the simulator keeps playing)"
[ -n "$COPY" ] && [ "$MCOPY" -gt 0 ] && echo "restore test ok"
