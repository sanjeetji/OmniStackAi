"""R-569: the database side of live updates, shared by every backend.

A trigger on each live table publishes `{"t": table, "op": insert|update|delete, "id", "o": the row's
creator, "a": its assignee}` on the `app_changes` channel. The creator and assignee are there so a
backend can tell, without a query, who may hear of the change (R-570 / PC-111 ownership).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..application_ir import ApplicationIR
from ..application_ir.ownership import ownership_for_entity
from ..application_ir.realtime import realtime_of
from .schema_sql import sql_identifier, table_name

CHANNEL = "app_changes"
#: How long a stream ticket lives: long enough to open the stream, too short to be worth stealing.
TICKET_SECONDS = 60
PING_SECONDS = 20

_FUNCTION = f"""\
-- R-569: live updates. Each change to a live table is published for the API to stream.
CREATE OR REPLACE FUNCTION "realtime_notify"() RETURNS trigger AS $$
DECLARE
    "changed" jsonb;
BEGIN
    IF TG_OP = 'DELETE' THEN
        "changed" := to_jsonb(OLD);
    ELSE
        "changed" := to_jsonb(NEW);
    END IF;
    PERFORM pg_notify('{CHANNEL}', json_build_object(
        't', TG_TABLE_NAME, 'op', lower(TG_OP), 'id', "changed"->>'id',
        'o', "changed"->>'created_by',
        'a', CASE WHEN TG_NARGS > 0 THEN "changed"->>TG_ARGV[0] END)::text);
    RETURN NULL;
END
$$ LANGUAGE plpgsql;"""


@dataclass(frozen=True, slots=True)
class LiveTable:
    """A live entity as a backend needs it: who may hear of a change to one of its rows."""

    entity: str
    table: str
    owned: bool  # read 'own': only the creator (or assignee, or see_all roles) hears of it
    see_all: tuple[str, ...]
    assignee: str | None


def live_tables(ir: ApplicationIR) -> tuple[LiveTable, ...]:
    live = realtime_of(ir)
    if live is None:
        return ()
    out = []
    for name in live.entities:
        rule = ownership_for_entity(ir, name)
        out.append(LiveTable(
            entity=name,
            table=table_name(name),
            owned=rule is not None and rule.reads_own,
            see_all=tuple(rule.bypass_roles) if rule else (),
            assignee=rule.assignee if rule else None,
        ))
    return tuple(out)


def realtime_schema(ir: ApplicationIR) -> str:
    tables = live_tables(ir)
    if not tables:
        return ""
    blocks = [_FUNCTION]
    for live in tables:
        table = sql_identifier(live.table)
        trigger = sql_identifier(f"realtime_{live.table}")
        argument = f"'{live.assignee}'" if live.assignee else ""
        blocks.append(f"DROP TRIGGER IF EXISTS {trigger} ON {table};")
        blocks.append(f"CREATE TRIGGER {trigger} AFTER INSERT OR UPDATE OR DELETE ON {table} "
                      f'FOR EACH ROW EXECUTE FUNCTION "realtime_notify"({argument});')
    return "\n".join(blocks)
