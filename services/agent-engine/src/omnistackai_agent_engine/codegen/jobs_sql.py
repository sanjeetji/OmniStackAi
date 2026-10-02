"""R-568: the scheduler's SQL, worked out once and run unchanged by every backend.

A schedule compiles to one statement that touches at most `BATCH` rows: the rows are picked by the
schedule's conditions and locked with SKIP LOCKED, so a request editing a row is never blocked
behind the sweep. A backend runs the statement again while it fills a batch, up to `MAX_BATCHES`;
whatever is left is the next run's.

The scheduler's own statements (enqueue what is due, claim a run, record how it went) are here too,
so Python, Go and Node agree on them to the character. `%s` / `$1` placeholders differ by driver,
so the statements that take values are written with `$n` (in order) and converted for Python.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..application_ir import ApplicationIR
from ..application_ir.jobs import Schedule, describe, jobs_of, seconds
from ..application_ir.workflow import workflows_of
from .schema_sql import sql_identifier, table_name

BATCH = 500
MAX_BATCHES = 20
MAX_ATTEMPTS = 5

JOBS_SCHEMA = """\
-- R-568: background jobs. A schedule's next run is a row; every run is a row (retried, then dead).
CREATE TABLE IF NOT EXISTS "scheduler_schedule" (
    "name"          VARCHAR PRIMARY KEY,
    "every_seconds" INTEGER NOT NULL CHECK ("every_seconds" >= 60),
    "paused"        BOOLEAN NOT NULL DEFAULT FALSE,
    "next_run_at"   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "last_run_at"   TIMESTAMPTZ,
    "last_status"   VARCHAR,
    "last_affected" INTEGER,
    "last_error"    TEXT
);
CREATE TABLE IF NOT EXISTS "scheduler_run" (
    "id"           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "schedule"     VARCHAR NOT NULL,
    "trigger"      VARCHAR NOT NULL DEFAULT 'schedule' CHECK ("trigger" IN ('schedule', 'manual', 'retry')),
    "status"       VARCHAR NOT NULL DEFAULT 'queued' CHECK ("status" IN ('queued', 'running', 'done', 'failed', 'dead')),
    "attempts"     INTEGER NOT NULL DEFAULT 0,
    "max_attempts" INTEGER NOT NULL DEFAULT 5,
    "run_at"       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "locked_until" TIMESTAMPTZ,
    "affected"     INTEGER,
    "error"        TEXT,
    "created_at"   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "finished_at"  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "ix_scheduler_run_due" ON "scheduler_run" ("run_at") WHERE "status" IN ('queued', 'failed', 'running');
CREATE INDEX IF NOT EXISTS "ix_scheduler_run_recent" ON "scheduler_run" ("created_at" DESC);
-- PC-117: a schedule at a time of day (minutes after local midnight), on a weekday (0 = Monday), in a zone.
ALTER TABLE "scheduler_schedule" ADD COLUMN IF NOT EXISTS "at_minutes" INTEGER;
ALTER TABLE "scheduler_schedule" ADD COLUMN IF NOT EXISTS "on_day" INTEGER;
ALTER TABLE "scheduler_schedule" ADD COLUMN IF NOT EXISTS "timezone" VARCHAR NOT NULL DEFAULT 'UTC';
-- The next local time at "at_minutes" (on "on_day") after now, as an instant. Postgres does the zone
-- arithmetic, daylight saving included, so every backend agrees.
CREATE OR REPLACE FUNCTION "scheduler_next_at"("at_minutes" integer, "on_day" integer, "every_seconds" integer, "zone" varchar)
RETURNS timestamptz AS $$
DECLARE
    "local_now" timestamp := NOW() AT TIME ZONE "zone";
    "step" interval := make_interval(secs => GREATEST("every_seconds", 86400));
    "candidate" timestamp;
BEGIN
    IF "on_day" IS NULL THEN
        "candidate" := date_trunc('day', "local_now") + make_interval(mins => "at_minutes");
    ELSE
        "candidate" := date_trunc('week', "local_now") + make_interval(days => "on_day", mins => "at_minutes");
    END IF;
    WHILE "candidate" <= "local_now" LOOP
        "candidate" := "candidate" + "step";
    END LOOP;
    RETURN "candidate" AT TIME ZONE "zone";
END
$$ LANGUAGE plpgsql STABLE;"""

#: Make every schedule that is due into a queued run, moving its next run on. Row locks on the
#: schedule make this safe with several replicas: each due schedule is enqueued once.
ENQUEUE_DUE = (
    'WITH due AS (UPDATE "scheduler_schedule" SET "next_run_at" = CASE WHEN "at_minutes" IS NULL '
    'THEN NOW() + make_interval(secs => "every_seconds") '
    'ELSE "scheduler_next_at"("at_minutes", "on_day", "every_seconds", "timezone") END '
    'WHERE "next_run_at" <= NOW() AND NOT "paused" RETURNING "name") '
    'INSERT INTO "scheduler_run" ("schedule") SELECT "name" FROM due'
)

#: Take one run that is due (or whose worker died holding it). SKIP LOCKED: replicas never share one.
CLAIM = (
    'UPDATE "scheduler_run" SET "status" = \'running\', "attempts" = "attempts" + 1, '
    '"locked_until" = NOW() + interval \'5 minutes\' '
    'WHERE "id" = (SELECT "id" FROM "scheduler_run" '
    'WHERE ("status" IN (\'queued\', \'failed\') AND "run_at" <= NOW()) '
    'OR ("status" = \'running\' AND "locked_until" < NOW()) '
    'ORDER BY "run_at" LIMIT 1 FOR UPDATE SKIP LOCKED) '
    'RETURNING "id", "schedule"'
)

#: A run asked for by an admin: queued now, claimed at once by the same request.
MANUAL = ('INSERT INTO "scheduler_run" ("schedule", "trigger", "status", "attempts", "locked_until") '
          'VALUES ($1, \'manual\', \'running\', 1, NOW() + interval \'5 minutes\') RETURNING "id", "schedule"')

DONE = ('UPDATE "scheduler_run" SET "status" = \'done\', "affected" = $1, "error" = NULL, '
        '"finished_at" = NOW(), "locked_until" = NULL WHERE "id" = $2')

#: A failed run waits 20s, 40s, 80s, ... before its next attempt; after the last it is dead.
FAILED = ('UPDATE "scheduler_run" SET "status" = CASE WHEN "attempts" >= "max_attempts" THEN \'dead\' ELSE \'failed\' END, '
          '"error" = $1, "finished_at" = NOW(), "locked_until" = NULL, '
          '"run_at" = NOW() + make_interval(secs => 10 * power(2, "attempts")) WHERE "id" = $2 RETURNING "status"')

RECORD = ('UPDATE "scheduler_schedule" SET "last_run_at" = NOW(), "last_status" = $1, "last_affected" = $2, '
          '"last_error" = $3 WHERE "name" = $4')

#: Done runs are kept two weeks; failed and dead ones until someone looks at them.
PRUNE = 'DELETE FROM "scheduler_run" WHERE "status" = \'done\' AND "finished_at" < NOW() - interval \'14 days\''

SCHEDULES = ('SELECT "name", "every_seconds", "paused", "next_run_at", "last_run_at", "last_status", '
             '"last_affected", "last_error" FROM "scheduler_schedule" ORDER BY "name"')

RUN_COLUMNS = ('"id", "schedule", "trigger", "status", "attempts", "max_attempts", "run_at", "affected", '
               '"error", "created_at", "finished_at"')

RUNS = f'SELECT {RUN_COLUMNS} FROM "scheduler_run" ORDER BY "created_at" DESC LIMIT 200'
RUNS_WITH_STATUS = f'SELECT {RUN_COLUMNS} FROM "scheduler_run" WHERE "status" = $1 ORDER BY "created_at" DESC LIMIT 200'
RUN = f'SELECT {RUN_COLUMNS} FROM "scheduler_run" WHERE "id" = $1'

#: An admin's retry of a failed or dead run: a fresh set of attempts, due now.
RETRY = ('UPDATE "scheduler_run" SET "status" = \'queued\', "trigger" = \'retry\', "attempts" = 0, "run_at" = NOW(), '
         '"error" = NULL, "finished_at" = NULL WHERE "id" = $1 AND "status" IN (\'failed\', \'dead\') '
         f'RETURNING {RUN_COLUMNS}')

PAUSE = 'UPDATE "scheduler_schedule" SET "paused" = $1 WHERE "name" = $2 RETURNING "name"'


#: Every statement above numbers its placeholders in the order they appear, so the same arguments
#: work for `$n` (Go, Node) and positional `%s` (Python). DONE, FAILED, RECORD and PAUSE put the row's
#: key last for that reason.
def python_placeholders(sql: str) -> str:
    """`$1` -> `%s` for psycopg; refuses a statement whose placeholders are out of order."""
    numbers = [int(n) for n in re.findall(r"\$(\d+)", sql)]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError(f"placeholders out of order: {sql[:60]}")
    return re.sub(r"\$\d+", "%s", sql)


def _literal(value) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


@dataclass(frozen=True, slots=True)
class CompiledSchedule:
    """A schedule, ready for a backend: its statement and its sentence."""

    name: str
    entity: str
    every_seconds: int
    action: str
    sql: str
    description: str
    at_minutes: int | None = None
    on_day: int | None = None


def compile_schedule(ir: ApplicationIR, schedule: Schedule, timezone: str = "UTC") -> CompiledSchedule:
    table = sql_identifier(table_name(schedule.entity))
    workflow = next((w for w in workflows_of(ir) if w.entity == schedule.entity), None)
    conditions: list[str] = []
    for column, values in schedule.where:
        if len(values) == 1:
            conditions.append(f"{sql_identifier(column)} = {_literal(values[0])}")
        else:
            conditions.append(f"{sql_identifier(column)} IN ({', '.join(_literal(v) for v in values)})")
    sets: list[str] = []
    if schedule.transition is not None:
        assert workflow is not None
        transition = next(t for t in workflow.transitions if t.name == schedule.transition)
        state = sql_identifier(workflow.field)
        # Only rows the workflow lets this transition leave - and not those already there.
        if transition.sources:
            conditions.append(f"{state} IN ({', '.join(_literal(s) for s in transition.sources)})")
        else:
            conditions.append(f"{state} IS DISTINCT FROM {_literal(transition.to)}")
        sets.append(f"{state} = {_literal(transition.to)}")
    for column, value in schedule.set:
        # Rows that already hold the value are left alone, so a run's count is what it changed.
        conditions.append(f"{sql_identifier(column)} IS DISTINCT FROM {_literal(value)}")
        sets.append(f"{sql_identifier(column)} = {_literal(value)}")
    if schedule.older_than is not None:
        column, age = schedule.older_than
        age_seconds = seconds(age)
        cutoff = "NOW()" if age_seconds == 0 else f"NOW() - make_interval(secs => {age_seconds})"
        conditions.append(f"{sql_identifier(column)} < {cutoff}")
    if schedule.due_within is not None:
        column, age = schedule.due_within
        conditions.append(f"{sql_identifier(column)} BETWEEN NOW() AND NOW() + make_interval(secs => {seconds(age)})")
    if schedule.notify is not None:  # PC-053: a reminder
        from .notifications_sql import reminder_sql

        return CompiledSchedule(
            name=schedule.name, entity=schedule.entity, every_seconds=schedule.every_seconds, action="notify",
            sql=reminder_sql(ir, schedule, conditions, BATCH), description=describe(schedule, workflow, timezone),
            at_minutes=schedule.at_minutes, on_day=schedule.on_day,
        )
    picked = (f'SELECT "id" FROM {table} WHERE {" AND ".join(conditions)} '
              f'ORDER BY "id" LIMIT {BATCH} FOR UPDATE SKIP LOCKED')
    if schedule.delete:
        sql = f'DELETE FROM {table} WHERE "id" IN ({picked})'
    else:
        sql = f'UPDATE {table} SET {", ".join(sets)}, "updated_at" = NOW() WHERE "id" IN ({picked})'
    return CompiledSchedule(
        name=schedule.name,
        entity=schedule.entity,
        every_seconds=schedule.every_seconds,
        action=schedule.action,
        sql=sql,
        description=describe(schedule, workflow, timezone),
        at_minutes=schedule.at_minutes,
        on_day=schedule.on_day,
    )


def compiled_schedules(ir: ApplicationIR) -> tuple[CompiledSchedule, ...]:
    jobs = jobs_of(ir)
    return tuple(compile_schedule(ir, s, jobs.timezone) for s in jobs.schedules) if jobs else ()


def sync_statements(ir: ApplicationIR) -> tuple[str, ...]:
    """Make the table of schedules match the app's: add new ones (due at once), keep each one's
    next run when it already exists, drop the ones the app no longer has."""
    compiled = compiled_schedules(ir)
    jobs = jobs_of(ir)
    zone = _literal(jobs.timezone if jobs else "UTC")

    def upsert(c: CompiledSchedule) -> str:
        at = "NULL" if c.at_minutes is None else str(c.at_minutes)
        on = "NULL" if c.on_day is None else str(c.on_day)
        # PC-117: a schedule at a time of day first runs at that time, not at start-up.
        first = "NOW()" if c.at_minutes is None else f'"scheduler_next_at"({at}, {on}, {c.every_seconds}, {zone})'
        return (
            'INSERT INTO "scheduler_schedule" ("name", "every_seconds", "at_minutes", "on_day", "timezone", "next_run_at") '
            f"VALUES ({_literal(c.name)}, {c.every_seconds}, {at}, {on}, {zone}, {first}) "
            'ON CONFLICT ("name") DO UPDATE SET "every_seconds" = EXCLUDED."every_seconds", '
            '"at_minutes" = EXCLUDED."at_minutes", "on_day" = EXCLUDED."on_day", "timezone" = EXCLUDED."timezone", '
            # A schedule whose time changed is due at its new time; one that did not keeps its next run.
            '"next_run_at" = CASE WHEN "scheduler_schedule"."at_minutes" IS DISTINCT FROM EXCLUDED."at_minutes" '
            'OR "scheduler_schedule"."on_day" IS DISTINCT FROM EXCLUDED."on_day" '
            'OR "scheduler_schedule"."timezone" IS DISTINCT FROM EXCLUDED."timezone" '
            'THEN EXCLUDED."next_run_at" ELSE "scheduler_schedule"."next_run_at" END'
        )

    upserts = tuple(upsert(c) for c in compiled)
    names = ", ".join(_literal(c.name) for c in compiled)
    return (*upserts, f'DELETE FROM "scheduler_schedule" WHERE "name" NOT IN ({names})')
