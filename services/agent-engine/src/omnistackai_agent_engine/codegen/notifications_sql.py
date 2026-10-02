"""PC-053: notifications in the database, shared by every backend.

`notification_send` writes one notification for one person, leaving out the channels they muted, and
does nothing when nothing is left. A trigger per entity calls it for each rule that matches a change;
a reminder (a scheduled job's notify) calls it for each record that is due, once. The backends only
list notifications, mark them read, keep preferences and send the emails in the outbox.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application_ir import ApplicationIR
from ..application_ir.jobs import jobs_of
from ..application_ir.notifications import Message, has_notifications, notifications_of, placeholders
from ..application_ir.ownership import ownership_for_entity
from .schema_sql import sql_identifier, table_name

EMAIL_MAX_ATTEMPTS = 5

NOTIFICATIONS_SCHEMA = """\
-- PC-053: notifications. One row per person; in_app shows it behind the bell, email_status is the outbox.
CREATE TABLE IF NOT EXISTS "notification" (
    "id"             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "user_id"        UUID NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
    "rule"           VARCHAR NOT NULL,
    "entity"         VARCHAR NOT NULL,
    "record_id"      UUID,
    "title"          TEXT NOT NULL,
    "body"           TEXT NOT NULL DEFAULT '',
    "in_app"         BOOLEAN NOT NULL DEFAULT TRUE,
    "read_at"        TIMESTAMPTZ,
    "email_status"   VARCHAR CHECK ("email_status" IN ('pending', 'sending', 'sent', 'failed', 'skipped')),
    "email_attempts" INTEGER NOT NULL DEFAULT 0,
    "email_next_at"  TIMESTAMPTZ,
    "email_error"    TEXT,
    "created_at"     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS "ix_notification_inbox" ON "notification" ("user_id", "created_at" DESC) WHERE "in_app";
CREATE INDEX IF NOT EXISTS "ix_notification_outbox" ON "notification" ("email_next_at") WHERE "email_status" IN ('pending', 'sending');
-- A reminder reaches each person once per record.
CREATE UNIQUE INDEX IF NOT EXISTS "uq_notification_reminder" ON "notification" ("rule", "record_id", "user_id") WHERE "rule" LIKE 'reminder:%';
-- What each person turned off: a rule (or every rule, '*') on a channel.
CREATE TABLE IF NOT EXISTS "notification_mute" (
    "user_id" UUID NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
    "rule"    VARCHAR NOT NULL,
    "channel" VARCHAR NOT NULL CHECK ("channel" IN ('in_app', 'email')),
    PRIMARY KEY ("user_id", "rule", "channel")
);
-- One notification for one person, without the channels they muted. Returns 1 when one was written.
CREATE OR REPLACE FUNCTION "notification_send"("recipient" uuid, "rule_name" varchar, "entity_name" varchar,
                                               "record" uuid, "title_text" text, "body_text" text,
                                               "want_in_app" boolean, "want_email" boolean)
RETURNS integer AS $$
DECLARE
    "v_in_app" boolean;
    "v_email" boolean;
    "v_written" integer;
BEGIN
    IF "recipient" IS NULL THEN
        RETURN 0;
    END IF;
    "v_in_app" := "want_in_app" AND NOT EXISTS (SELECT 1 FROM "notification_mute" "m"
        WHERE "m"."user_id" = "recipient" AND "m"."channel" = 'in_app' AND "m"."rule" IN ('*', "rule_name"));
    "v_email" := "want_email" AND NOT EXISTS (SELECT 1 FROM "notification_mute" "m"
        WHERE "m"."user_id" = "recipient" AND "m"."channel" = 'email' AND "m"."rule" IN ('*', "rule_name"));
    IF NOT ("v_in_app" OR "v_email") THEN
        RETURN 0;
    END IF;
    INSERT INTO "notification" ("user_id", "rule", "entity", "record_id", "title", "body", "in_app", "email_status", "email_next_at")
    VALUES ("recipient", "rule_name", "entity_name", "record", COALESCE("title_text", ''), COALESCE("body_text", ''), "v_in_app",
            CASE WHEN "v_email" THEN 'pending' END, CASE WHEN "v_email" THEN NOW() END)
    ON CONFLICT DO NOTHING;
    GET DIAGNOSTICS "v_written" = ROW_COUNT;
    RETURN "v_written";
END
$$ LANGUAGE plpgsql;"""

# --- the outbox (run by each backend's sender) ------------------------------------------------------

#: Take up to 20 emails that are due (or whose sender died while sending), with their addresses.
CLAIM_EMAILS = (
    'UPDATE "notification" "n" SET "email_status" = \'sending\', "email_attempts" = "n"."email_attempts" + 1, '
    '"email_next_at" = NOW() + interval \'5 minutes\' FROM "users" "u" '
    'WHERE "n"."id" IN (SELECT "id" FROM "notification" WHERE "email_status" IN (\'pending\', \'sending\') '
    'AND "email_next_at" <= NOW() ORDER BY "email_next_at" LIMIT 20 FOR UPDATE SKIP LOCKED) AND "u"."id" = "n"."user_id" '
    'RETURNING "n"."id", "n"."title", "n"."body", "n"."email_attempts", "u"."email"'
)
EMAIL_SENT = 'UPDATE "notification" SET "email_status" = \'sent\', "email_error" = NULL, "email_next_at" = NULL WHERE "id" = $1'
EMAIL_SKIPPED = ('UPDATE "notification" SET "email_status" = \'skipped\', "email_error" = $1, "email_next_at" = NULL '
                 'WHERE "id" = $2')
#: A failed email is tried again after 1, 2, 4, 8 minutes; after the fifth attempt it has failed.
EMAIL_FAILED = (
    'UPDATE "notification" SET "email_status" = CASE WHEN "email_attempts" >= ' + str(EMAIL_MAX_ATTEMPTS)
    + ' THEN \'failed\' ELSE \'pending\' END, "email_error" = $1, '
    '"email_next_at" = NOW() + make_interval(secs => 30 * power(2, "email_attempts")) WHERE "id" = $2'
)

# --- the inbox (the API) ----------------------------------------------------------------------------

INBOX_COLUMNS = '"id", "rule", "entity", "record_id", "title", "body", "read_at", "created_at"'
INBOX = f'SELECT {INBOX_COLUMNS} FROM "notification" WHERE "user_id" = $1 AND "in_app" ORDER BY "created_at" DESC LIMIT 100'
INBOX_UNREAD = (f'SELECT {INBOX_COLUMNS} FROM "notification" WHERE "user_id" = $1 AND "in_app" AND "read_at" IS NULL '
                'ORDER BY "created_at" DESC LIMIT 100')
UNREAD_COUNT = 'SELECT count(*) AS "count" FROM "notification" WHERE "user_id" = $1 AND "in_app" AND "read_at" IS NULL'
MARK_READ = ('UPDATE "notification" SET "read_at" = COALESCE("read_at", NOW()) WHERE "id" = $1 AND "user_id" = $2 '
             'RETURNING "id"')
MARK_ALL_READ = 'UPDATE "notification" SET "read_at" = NOW() WHERE "user_id" = $1 AND "in_app" AND "read_at" IS NULL'
MUTES = 'SELECT "rule", "channel" FROM "notification_mute" WHERE "user_id" = $1'
MUTE = 'INSERT INTO "notification_mute" ("user_id", "rule", "channel") VALUES ($1, $2, $3) ON CONFLICT DO NOTHING'
UNMUTE = 'DELETE FROM "notification_mute" WHERE "user_id" = $1 AND "rule" = $2 AND "channel" = $3'


# --- rules, compiled --------------------------------------------------------------------------------

def _literal(value) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


def text_expression(template: str, row: str) -> str:
    """'Order {status} for {total}' -> 'Order ' || COALESCE(NEW."status"::text, '') || ' for ' || ..."""
    parts: list[str] = []
    rest = template
    for name in placeholders(template):
        before, _, rest = rest.partition("{" + name + "}")
        if before:
            parts.append(_literal(before))
        parts.append(f"COALESCE({row}.{sql_identifier(name)}::text, '')")
    if rest:
        parts.append(_literal(rest))
    return " || ".join(parts) if parts else "''"


def recipients(ir: ApplicationIR, entity: str, message: Message, row: str) -> str:
    """The people a message is for, as `SELECT "uid"` over the record `row`."""
    rule = ownership_for_entity(ir, entity)
    selects: list[str] = []
    for who in message.to:
        if who == "creator":
            selects.append(f'SELECT {row}."created_by" AS "uid"')
        elif who == "assignee":
            assert rule is not None and rule.assignee
            selects.append(f"SELECT {row}.{sql_identifier(rule.assignee)} AS \"uid\"")
        elif who.startswith("role:"):
            selects.append(f'SELECT "id" AS "uid" FROM "users" WHERE "role" = {_literal(who[5:])}')
        else:
            selects.append(f"SELECT {row}.{sql_identifier(who)} AS \"uid\"")
    return f'SELECT DISTINCT "uid" FROM ({" UNION ".join(selects)}) "w" WHERE "uid" IS NOT NULL'


def _send(ir: ApplicationIR, entity: str, rule_name: str, message: Message, row: str, uid: str) -> str:
    return (f'"notification_send"({uid}, {_literal(rule_name)}, {_literal(entity)}, {row}."id", '
            f"{text_expression(message.title, row)}, {text_expression(message.body, row)}, "
            f"{_literal('in_app' in message.channels)}, {_literal('email' in message.channels)})")


@dataclass(frozen=True, slots=True)
class RuleInfo:
    """What a person sees on their preferences page."""

    rule: str
    label: str
    channels: tuple[str, ...]
    #: Who can receive it at all, when it is only for roles ("role:staff"); () means anyone.
    only_roles: tuple[str, ...] = ()


def _label(title: str) -> str:
    """'Order {status} is assigned to you' -> 'Order … is assigned to you'."""
    import re

    return re.sub(r"\{[a-z][a-z0-9_]*\}", "…", title)


def _only_roles(message: Message) -> tuple[str, ...]:
    if message.to and all(who.startswith("role:") for who in message.to):
        return tuple(who[5:] for who in message.to)
    return ()


def rule_catalogue(ir: ApplicationIR) -> tuple[RuleInfo, ...]:
    out: list[RuleInfo] = []
    rules = notifications_of(ir)
    for rule in rules.rules if rules else ():
        out.append(RuleInfo(rule.name, _label(rule.message.title), rule.message.channels, _only_roles(rule.message)))
    jobs = jobs_of(ir)
    for schedule in jobs.schedules if jobs else ():
        if schedule.notify is not None:
            out.append(RuleInfo(f"reminder:{schedule.name}", _label(schedule.notify.title), schedule.notify.channels,
                                _only_roles(schedule.notify)))
    return tuple(out)


def notification_triggers(ir: ApplicationIR) -> str:
    rules = notifications_of(ir)
    if not rules or not rules.rules:
        return ""
    by_entity: dict[str, list] = {}
    for rule in rules.rules:
        by_entity.setdefault(rule.entity, []).append(rule)
    blocks: list[str] = []
    for entity, entity_rules in by_entity.items():
        table = table_name(entity)
        function = sql_identifier(f"notify_{table}")
        branches: list[str] = []
        for rule in entity_rules:
            row = "OLD" if rule.when == "deleted" else "NEW"
            if rule.when == "created":
                condition = "TG_OP = 'INSERT'"
            elif rule.when == "deleted":
                condition = "TG_OP = 'DELETE'"
            elif rule.when == "changed":
                condition = "TG_OP = 'UPDATE' AND NEW IS DISTINCT FROM OLD"
            elif rule.when == "assigned":
                owner = ownership_for_entity(ir, entity)
                column = sql_identifier(owner.assignee)
                condition = (f"NEW.{column} IS NOT NULL AND (TG_OP = 'INSERT' OR "
                             f"(TG_OP = 'UPDATE' AND NEW.{column} IS DISTINCT FROM OLD.{column}))")
            else:
                column, value = sql_identifier(rule.field), _literal(rule.becomes)
                condition = (f"((TG_OP = 'INSERT' AND NEW.{column} = {value}) OR "
                             f"(TG_OP = 'UPDATE' AND NEW.{column} = {value} AND OLD.{column} IS DISTINCT FROM {value}))")
            branches.append(
                f"    IF {condition} THEN\n"
                f'        PERFORM {_send(ir, entity, rule.name, rule.message, row, chr(34) + "who" + chr(34) + "." + chr(34) + "uid" + chr(34))}\n'
                f'        FROM ({recipients(ir, entity, rule.message, row)}) "who";\n'
                "    END IF;"
            )
        blocks.append(
            f"CREATE OR REPLACE FUNCTION {function}() RETURNS trigger AS $$\nBEGIN\n"
            + "\n".join(branches)
            + "\n    RETURN NULL;\nEND\n$$ LANGUAGE plpgsql;\n"
            f"DROP TRIGGER IF EXISTS {function} ON {sql_identifier(table)};\n"
            f"CREATE TRIGGER {function} AFTER INSERT OR UPDATE OR DELETE ON {sql_identifier(table)} "
            f"FOR EACH ROW EXECUTE FUNCTION {function}();"
        )
    return "\n".join(blocks)


def notifications_schema(ir: ApplicationIR) -> str:
    if not has_notifications(ir):
        return ""
    triggers = notification_triggers(ir)
    return NOTIFICATIONS_SCHEMA + ("\n" + triggers if triggers else "")


def reminder_sql(ir: ApplicationIR, schedule, conditions: list[str], batch: int) -> str:
    """A reminder's statement: one row back per notification written, each record reminded once."""
    table = sql_identifier(table_name(schedule.entity))
    rule = f"reminder:{schedule.name}"
    message = schedule.notify
    # The schedule's conditions name the entity's own columns; the recipients' only column is "uid".
    where = " AND ".join([*conditions,
                          f'NOT EXISTS (SELECT 1 FROM "notification" "n" WHERE "n"."rule" = {_literal(rule)} AND "n"."record_id" = "t"."id")'])
    picked = (f'SELECT "t".*, "who"."uid" AS "notify_uid" FROM {table} "t" '
              f'CROSS JOIN LATERAL ({recipients(ir, schedule.entity, message, chr(34) + "t" + chr(34))}) "who" '
              f'WHERE {where} ORDER BY "t"."id" LIMIT {batch}')
    return f'SELECT 1 FROM ({picked}) "c" WHERE {_send(ir, schedule.entity, rule, message, chr(34) + "c" + chr(34), chr(34) + "c" + chr(34) + "." + chr(34) + "notify_uid" + chr(34))} > 0'
