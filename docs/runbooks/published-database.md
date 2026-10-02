# A published app's database

Every published app has its own PostgreSQL database, created by PC-008. This page covers how it
keeps up with the project (PC-049), and how to restore a backup.

## Publishing again after the plan changed

You add a field, an entity, notifications or a lifecycle state, then publish again. The publisher
notices that the generated schema (`services/api/migrations/0001_init.sql`) changed since the live
database got it, and brings the database up to date:

1. **Backup first.** It saves the live database to
   `~/.omnistackai/published/<app>/backups/release-NNNN-<time>.sql.gz` and keeps the last five.
2. **Compare.** It applies the new schema to a scratch schema (`_omnistack_shadow`) in the same
   database and compares the columns.
3. **Add.** It adds each missing column to the live table, with its type, default and foreign key.
   A required field gets `NOT NULL` only if it has a default, because existing rows have no value
   for it.
4. **Re-apply.** It re-applies the schema. Every generated statement is safe to run twice, so new
   tables, indexes, functions, triggers and a lifecycle's new states all arrive.
5. **Report, never drop.** A field or entity the plan no longer has is **kept with its data**, and
   a changed type is left as it is. The publish log says which.

Steps 3 and 4 run in one transaction. If anything fails, the database stays as it was, the publish
stops at "migrate", and the release that was live stays live.

## Restoring a backup

On the machine that runs the app (`<project>` is the app's compose project, `omni-<id>`):

```bash
gunzip -c ~/.omnistackai/published/<app>/backups/release-0003-<time>.sql.gz > restore.sql
docker compose -p <project> exec -T db psql -U app -d postgres -c "DROP DATABASE app WITH (FORCE)"
docker compose -p <project> exec -T db psql -U app -d postgres -c "CREATE DATABASE app OWNER app"
docker compose -p <project> exec -T db psql -U app -d app < restore.sql
```

Then roll back to the matching release from the Studio, or publish again.

## Disk

Unpublishing an app removes its images. They are rebuilt on the next publish. Older releases beyond
the last few are pruned, the companion service's images included. Before this, unpublished apps'
images filled Colima's Docker disk and stopped the platform's own database.

## Not yet

- Hosted databases (Neon, Supabase) need an account: PC-123, at the credentials step.
- Backups are taken only before a schema change. Scheduled backups are part of PC-123.
