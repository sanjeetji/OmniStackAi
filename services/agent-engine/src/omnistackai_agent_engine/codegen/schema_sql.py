"""Render a PostgreSQL schema from the Application IR — the generated backend's persistence layer.

`render_postgres_schema(ir)` is pure and deterministic: one CREATE TABLE per entity, columns typed from
`FieldType`, `NOT NULL` for required fields, a UUID primary key (the entity's own ``id`` field if it
declares one, else a surrogate), foreign-key columns for many_to_one/one_to_one relations, and a join
table per many_to_many relation. Nothing connects to or runs a database; this only emits SQL text that
a later migration file carries.
"""

from __future__ import annotations

import re

from ..application_ir import ApplicationIR, Entity, FieldType, RelationKind
from .auth_guard import needs_auth
from .field_validation import parse_field_rules

# ---------------------------------------------------------------------------
# R-461: users table — emitted before application entity tables when auth is on
# ---------------------------------------------------------------------------

_USERS_TABLE_DDL = """\
CREATE TABLE IF NOT EXISTS "users" (
    "id"            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "email"         VARCHAR UNIQUE NOT NULL,
    "password_hash" VARCHAR NOT NULL,
    "full_name"     VARCHAR,
    "role"          VARCHAR NOT NULL DEFAULT 'user',
    "created_at"    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);"""

# A deterministic dev-access seed row so developers can log in immediately.
# The password hash encodes: salt=0000...00 (32 zero bytes) / plain='changeme'.
# Production deployments should rotate this credential immediately.
import hashlib as _hashlib
_ADMIN_SEED_HASH = (
    '0' * 64 + ':' +
    _hashlib.pbkdf2_hmac(
        'sha256', b'changeme', bytes(32), 100_000
    ).hex()
)
del _hashlib

_ADMIN_SEED_ROW = (
    '-- Development admin seed (email: admin@example.local / password: changeme)\n'
    '-- IMPORTANT: rotate this credential before any production deployment.\n'
    f"INSERT INTO \"users\" (email, password_hash, full_name, role) VALUES "
    f"('admin@example.local', '{_ADMIN_SEED_HASH}', 'Admin User', 'admin') "
    f"ON CONFLICT (email) DO NOTHING;"
)

_PG_TYPE: dict[FieldType, str] = {
    FieldType.STRING: "TEXT",
    FieldType.TEXT: "TEXT",
    FieldType.INT: "BIGINT",
    FieldType.FLOAT: "DOUBLE PRECISION",
    FieldType.BOOL: "BOOLEAN",
    FieldType.DATETIME: "TIMESTAMPTZ",
    FieldType.UUID: "UUID",
    FieldType.JSON: "JSONB",
    FieldType.ATTACHMENT: "TEXT",
}

_FK_KINDS = frozenset({RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE})

# R-502: trigger function emitted once per migration file to keep updated_at current.
_SET_UPDATED_AT_FUNCTION = """\
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;"""

# Columns automatically appended to every entity table (unless already declared by the IR).
_AUDIT_COLUMNS: tuple[str, str] = ("created_at", "updated_at")


def _snake(name: str) -> str:
    """PascalCase/camelCase -> snake_case (entity names are [A-Za-z][A-Za-z0-9]*)."""

    stepped = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    stepped = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stepped)
    return stepped.lower()


def _table(entity_name: str) -> str:
    return _snake(entity_name)


def table_name(entity_name: str) -> str:
    """Public: the PostgreSQL table name for an entity (snake_case). Shared with the data-access layer."""

    return _snake(entity_name)


def sql_identifier(name: str) -> str:
    """Return one PostgreSQL identifier with defensive standard double quoting."""

    if not isinstance(name, str) or not name:
        raise ValueError("SQL identifier must be a non-empty string")
    return '"' + name.replace('"', '""') + '"'


def ordered_entities(ir: ApplicationIR) -> tuple[Entity, ...]:
    """Stable FK-dependency order for entity creation and fixture insertion.

    PostgreSQL accepts a self-reference in the table currently being created, but an inline foreign
    key to another table requires that target table to exist already. A non-self cycle cannot satisfy
    that contract with inline constraints, so fail honestly instead of emitting a broken migration.
    """

    remaining = list(ir.entities)
    emitted: set[str] = set()
    ordered: list[Entity] = []
    while remaining:
        ready_index: int | None = None
        for index, entity in enumerate(remaining):
            dependencies = {
                relation.target_entity
                for relation in entity.relations
                if relation.kind in _FK_KINDS and relation.target_entity != entity.name
            }
            if dependencies <= emitted:
                ready_index = index
                break
        if ready_index is None:
            names = ", ".join(entity.name for entity in remaining)
            raise ValueError(f"cyclic foreign-key dependencies: {names}")
        entity = remaining.pop(ready_index)
        ordered.append(entity)
        emitted.add(entity.name)
    return tuple(ordered)


def _column_lines(entity: Entity, has_auth: bool = False) -> list[str]:
    lines: list[str] = []
    has_id = any(field.name == "id" for field in entity.fields)
    if not has_id:
        lines.append(f"    {sql_identifier('id')} UUID PRIMARY KEY DEFAULT gen_random_uuid()")

    fk_map: dict[str, Relation] = {}
    for relation in entity.relations:
        if relation.kind in _FK_KINDS:
            fk_map[f"{relation.name}_id"] = relation
            if relation.name.endswith("_id"):
                fk_map[relation.name] = relation

    emitted_field_names: set[str] = set()

    for field in entity.fields:
        column = sql_identifier(field.name)
        emitted_field_names.add(field.name)
        if field.name == "id":
            default = " DEFAULT gen_random_uuid()" if field.type is FieldType.UUID else ""
            lines.append(f"    {column} {sql_identifier('id') and _PG_TYPE[field.type]} PRIMARY KEY{default}")
        elif field.name in fk_map:
            relation = fk_map[field.name]
            target = sql_identifier(_table(relation.target_entity))
            null = " NOT NULL" if field.required else ""
            unique = " UNIQUE" if field.unique else ""
            lines.append(f"    {column} UUID{null}{unique} REFERENCES {target}({sql_identifier('id')})")
        else:
            pg = _PG_TYPE[field.type]
            rules = parse_field_rules(field)
            if field.type is FieldType.STRING and rules.max_length is not None:
                pg = f"VARCHAR({rules.max_length})"
            null = " NOT NULL" if field.required else ""
            unique = " UNIQUE" if field.unique else ""
            checks: list[str] = []
            if rules.enum:
                allowed = ", ".join("'" + value.replace("'", "''") + "'" for value in rules.enum)
                checks.append(f"{column} IN ({allowed})")
            if field.type in (FieldType.INT, FieldType.FLOAT):
                if rules.minimum is not None:
                    checks.append(f"{column} >= {rules.minimum}")
                if rules.maximum is not None:
                    checks.append(f"{column} <= {rules.maximum}")
            check = "".join(f" CHECK ({clause})" for clause in checks)
            lines.append(f"    {column} {pg}{null}{unique}{check}")

    for relation in entity.relations:
        if relation.kind in _FK_KINDS:
            target = sql_identifier(_table(relation.target_entity))
            relation_column_name = f"{relation.name}_id"
            if relation_column_name not in emitted_field_names and relation.name not in emitted_field_names:
                relation_column = sql_identifier(relation_column_name)
                lines.append(f"    {relation_column} UUID REFERENCES {target}({sql_identifier('id')})")
                emitted_field_names.add(relation_column_name)

    # Phase 3: Row ownership column (created_by) when auth is enabled.
    if has_auth and "created_by" not in emitted_field_names:
        lines.append(f'    {sql_identifier("created_by")} UUID REFERENCES {sql_identifier("users")}({sql_identifier("id")}) ON DELETE SET NULL')

    # R-502: audit timestamp columns — skipped if the IR already declares them.
    if "created_at" not in emitted_field_names:
        lines.append(f'    {sql_identifier("created_at")} TIMESTAMPTZ NOT NULL DEFAULT NOW()')
    if "updated_at" not in emitted_field_names:
        lines.append(f'    {sql_identifier("updated_at")} TIMESTAMPTZ NOT NULL DEFAULT NOW()')

    return lines


def _join_tables(ir: ApplicationIR) -> list[str]:
    """One deterministic join table per unique many_to_many relation pair."""

    seen: dict[tuple[str, str], str] = {}
    for entity in ir.entities:
        left = _table(entity.name)
        for relation in entity.relations:
            if relation.kind is RelationKind.MANY_TO_MANY:
                right = _table(relation.target_entity)
                key = tuple(sorted((left, right)))
                if key in seen:
                    continue
                a, b = key
                join = f"{a}_{b}"
                seen[key] = (
                    f"CREATE TABLE {sql_identifier(join)} (\n"
                    f"    {sql_identifier(f'{a}_id')} UUID NOT NULL REFERENCES {sql_identifier(a)}({sql_identifier('id')}),\n"
                    f"    {sql_identifier(f'{b}_id')} UUID NOT NULL REFERENCES {sql_identifier(b)}({sql_identifier('id')}),\n"
                    f"    PRIMARY KEY ({sql_identifier(f'{a}_id')}, {sql_identifier(f'{b}_id')})\n"
                    f");"
                )
    return [seen[key] for key in sorted(seen)]


def _index_statements(ir: ApplicationIR) -> list[str]:
    """One CREATE [UNIQUE] INDEX per entity index; deterministic default name when unnamed."""

    statements: list[str] = []
    for entity in ir.entities:
        table = _table(entity.name)
        for index in entity.indexes:
            columns = ", ".join(sql_identifier(field) for field in index.fields)
            default_name = f"{table}_{'_'.join(index.fields)}_{'key' if index.unique else 'idx'}"
            name = index.name or default_name
            unique = "UNIQUE " if index.unique else ""
            statements.append(
                f"CREATE {unique}INDEX {sql_identifier(name)} ON {sql_identifier(table)} ({columns});"
            )
    return statements


def render_postgres_schema(ir: ApplicationIR) -> str:
    """Deterministic PostgreSQL DDL for the IR's entities and relations.

    When `needs_auth(ir)` is True, a `users` table is prepended before any
    application entity tables, and a dev-mode admin seed INSERT is appended
    (empty only when there are no entities AND auth is not required).
    """

    if not isinstance(ir, ApplicationIR):
        raise TypeError("render_postgres_schema expects an ApplicationIR")

    auth = needs_auth(ir)

    if not ir.entities and not auth:
        return ""

    blocks: list[str] = [
        f"-- PostgreSQL schema for {ir.name}",
        "-- Generated by OmniStackAI from the Application IR. Review before applying.",
        "",
    ]

    # R-461: users table precedes all application entity tables.
    if auth:
        blocks.append(_USERS_TABLE_DDL)
        blocks.append("")

    # R-502: emit the trigger function once before the entity tables.
    if ir.entities:
        blocks.append(_SET_UPDATED_AT_FUNCTION)
        blocks.append("")

    # R-566: a lifecycle belongs in the database, not only in the application. A workflow's states
    # become a CHECK constraint and a default, so a row cannot hold a state nobody declared — not
    # even through a hand-written UPDATE. A lifecycle enforced only in application code lasts
    # exactly as long as every writer remembers it.
    from ..application_ir.workflow import workflows_of

    workflows_by_entity = {w.entity: w for w in workflows_of(ir)}

    for entity in ordered_entities(ir):
        table = _table(entity.name)
        columns = ",\n".join(_column_lines(entity, has_auth=auth))
        workflow = workflows_by_entity.get(entity.name)
        if workflow is not None:
            allowed = ", ".join(f"'{state}'" for state in workflow.states)
            columns += (
                f",\n  CONSTRAINT {sql_identifier(f'chk_{table}_{workflow.field}')}"
                f" CHECK ({sql_identifier(workflow.field)} IN ({allowed}))"
            )
        blocks.append(f"CREATE TABLE {sql_identifier(table)} (\n{columns}\n);")
        if workflow is not None:
            blocks.append(
                f"ALTER TABLE {sql_identifier(table)} ALTER COLUMN {sql_identifier(workflow.field)}"
                f" SET DEFAULT '{workflow.initial}';"
            )
        # R-502: BEFORE UPDATE trigger keeps updated_at current.
        blocks.append(
            f"CREATE TRIGGER {sql_identifier(f'trg_{table}_updated_at')}\n"
            f"  BEFORE UPDATE ON {sql_identifier(table)}\n"
            f"  FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
        )
        blocks.append("")

    join_tables = _join_tables(ir)
    if join_tables:
        blocks.append("-- Association tables (many-to-many)")
        for table in join_tables:
            blocks.append(table)
            blocks.append("")

    index_statements = _index_statements(ir)
    if index_statements:
        blocks.append("-- Indexes")
        blocks.extend(index_statements)
        blocks.append("")

    # R-461: dev admin seed row.
    if auth:
        blocks.append(_ADMIN_SEED_ROW)
        blocks.append("")

    return "\n".join(blocks).rstrip("\n") + "\n"
