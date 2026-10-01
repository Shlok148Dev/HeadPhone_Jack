# Backup and restore (JNG-13-03)

| What | How | Kept |
| --- | --- | --- |
| PostgreSQL (all business data) | `pg_dump -Fc` | 14 days |
| MongoDB `jingle` (listens) | `mongodump --archive --gzip` | 14 days |
| Redis | not backed up: caches and short-lived state only | — |
| Qdrant | not backed up: vectors are rebuilt by the nightly suggestions job | — |

## Daily backup

```bash
infra/backup/backup.sh /var/backups/jingle
```

## Weekly tested restore (automated)

```bash
infra/backup/restore-test.sh /var/backups/jingle
```

The test loads the newest backup into scratch databases (`jingle_restore_test`), compares key counts with live, then drops the scratch copies. It never touches live data. The result of the last run on the development stack (2026-10-01):

```
postgres users,friendships,circles live=341,188,8 restored=341,188,8
mongo listens live=4799 restored=4799
restore test ok
```

## Real restore (data loss)

1. Announce downtime. The script stops the app services itself.
2. Run:

```bash
infra/backup/restore.sh /var/backups/jingle/pg-<stamp>.dump /var/backups/jingle/mongo-<stamp>.archive.gz
```

3. Check: sign in, open Home, `/staff` → Audit log.
4. Account deletions requested after the backup was taken must be applied again. Keep the purge list from the audit log, then run:

```bash
docker compose exec core-api python manage.py shell -c "from accounts.tasks import purge_due_users; purge_due_users()"
```

## Data export (JNG-13-04)

Settings → Account → **Download my data** returns one JSON file. It covers:

- profile, privacy and consents;
- connections and Companion tokens;
- listens (most recent 10,000);
- friends, requests sent, blocks and reports filed;
- taste picks;
- circles, sends and received songs, Blends, sessions and queue adds;
- battle nominations and votes, recaps;
- notification settings and notifications;
- moderation actions.

`tests/accounts/test_data_rights_s11.py` keeps this list honest.
