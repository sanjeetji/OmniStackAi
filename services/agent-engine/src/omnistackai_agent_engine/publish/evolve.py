"""PC-049: bring a published app's database up to date with its project, without losing anything.

PC-008 applied `0001_init.sql` once; a changed plan (a new field, a new entity, notifications) never
reached the live database. Publishing now notices that the schema changed since it was applied and:

1. applies the new schema to a scratch schema (`_omnistack_shadow`) in the same database;
2. compares its columns with the live tables' - this module, pure and testable;
3. adds each missing column to the live table (with its type, default and foreign key; NOT NULL only
   when it has a default, since existing rows would have no value);
4. re-applies the schema, whose every statement is safe to run again (R-502 / PC-049), so new
   tables, indexes, a lifecycle's new states, functions and triggers arrive;
5. reports what it would not do: a column or table the plan no longer has is kept, a changed type
   is left as it is. A publish never drops data.

Steps 3 and 4 run in one transaction: if anything fails, the live database is as it was.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SHADOW = "_omnistack_shadow"

#: Columns of every ordinary table in a schema: table, column, type, default, not null, foreign key.
COLUMNS_SQL = (
    "SELECT t.relname, a.attname, format_type(a.atttypid, a.atttypmod), "
    "COALESCE(pg_get_expr(d.adbin, d.adrelid), ''), a.attnotnull, "
    "COALESCE((SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c WHERE c.conrelid = t.oid AND c.contype = 'f' "
    "AND c.conkey = ARRAY[a.attnum] LIMIT 1), '') "
    "FROM pg_attribute a JOIN pg_class t ON t.oid = a.attrelid JOIN pg_namespace n ON n.oid = t.relnamespace "
    "LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum "
    "WHERE n.nspname = '{schema}' AND t.relkind = 'r' AND a.attnum > 0 AND NOT a.attisdropped "
    "AND t.relname NOT LIKE '\\_omnistack%' ORDER BY t.relname, a.attnum"
)


@dataclass(frozen=True, slots=True)
class Column:
    table: str
    name: str
    type: str
    default: str
    not_null: bool
    foreign_key: str  # "FOREIGN KEY (x) REFERENCES schema.t(id) ..." or ""


def parse_columns(output: str) -> list[Column]:
    """psql -tA -F '\\t' output of COLUMNS_SQL."""
    out = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 6:
            continue
        table, name, type_, default, not_null, fk = parts
        out.append(Column(table, name, type_, default, not_null == "t", fk))
    return out


def _ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@dataclass
class Evolution:
    """What publishing will do to the live database, and what it reports and leaves alone."""

    statements: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = []
        if self.added:
            parts.append("added " + ", ".join(self.added))
        parts += self.notes
        return "; ".join(parts) or "no column changes"


def plan_evolution(live: list[Column], wanted: list[Column], shadow: str = SHADOW) -> Evolution:
    """Compare the live tables with the new schema's; the statements that add what is missing."""
    plan = Evolution()
    live_by_table: dict[str, dict[str, Column]] = {}
    for column in live:
        live_by_table.setdefault(column.table, {})[column.name] = column
    wanted_by_table: dict[str, dict[str, Column]] = {}
    for column in wanted:
        wanted_by_table.setdefault(column.table, {})[column.name] = column
    for table, columns in wanted_by_table.items():
        existing = live_by_table.get(table)
        if existing is None:
            continue  # a new table: re-applying the schema creates it whole
        for name, column in columns.items():
            have = existing.get(name)
            if have is not None:
                if have.type != column.type:
                    plan.notes.append(f"{table}.{name} is {have.type} live and {column.type} in the plan; left as it is")
                continue
            definition = f"{_ident(name)} {column.type}"
            if column.default:
                definition += f" DEFAULT {column.default.replace(f'{shadow}.', '')}"
                if column.not_null:
                    definition += " NOT NULL"
            elif column.not_null:
                plan.notes.append(f"{table}.{name} added without NOT NULL (existing rows have no value)")
            plan.statements.append(f"ALTER TABLE {_ident(table)} ADD COLUMN IF NOT EXISTS {definition};")
            if column.foreign_key:
                constraint = _ident(f"fk_{table}_{name}"[:63])
                reference = column.foreign_key.replace(f"{shadow}.", "")
                plan.statements.append(f"ALTER TABLE {_ident(table)} DROP CONSTRAINT IF EXISTS {constraint};")
                plan.statements.append(f"ALTER TABLE {_ident(table)} ADD CONSTRAINT {constraint} {reference} NOT VALID;")
            plan.added.append(f"{table}.{name}")
        for name in existing:
            if name not in columns:
                plan.notes.append(f"{table}.{name} is no longer in the plan; kept with its data")
    for table in live_by_table:
        if table not in wanted_by_table:
            plan.notes.append(f"table {table} is no longer in the plan; kept with its data")
    return plan


def shadow_sql(schema_sql: str, shadow: str = SHADOW) -> str:
    """The new schema, applied to a fresh scratch schema."""
    return (f"DROP SCHEMA IF EXISTS {shadow} CASCADE;\nCREATE SCHEMA {shadow};\n"
            f"SET search_path TO {shadow}, pg_catalog;\n" + schema_sql)


def evolve_sql(plan: Evolution, schema_sql: str) -> str:
    """Add the missing columns, then re-apply the schema - one transaction (psql -1)."""
    return "SET search_path TO public;\n" + "\n".join(plan.statements) + "\n" + schema_sql


def drop_shadow_sql(shadow: str = SHADOW) -> str:
    return f"DROP SCHEMA IF EXISTS {shadow} CASCADE;"
