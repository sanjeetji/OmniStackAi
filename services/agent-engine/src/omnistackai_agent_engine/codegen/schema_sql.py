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
from .field_validation import parse_field_rules

_PG_TYPE: dict[FieldType, str] = {
    FieldType.STRING: "TEXT",
    FieldType.TEXT: "TEXT",
    FieldType.INT: "BIGINT",
    FieldType.FLOAT: "DOUBLE PRECISION",
    FieldType.BOOL: "BOOLEAN",
    FieldType.DATETIME: "TIMESTAMPTZ",
    FieldType.UUID: "UUID",
    FieldType.JSON: "JSONB",
}

_FK_KINDS = frozenset({RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE})


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


def _column_lines(entity: Entity) -> list[str]:
    lines: list[str] = []
    has_id = any(field.name == "id" for field in entity.fields)
    if not has_id:
        lines.append(f"    {sql_identifier('id')} UUID PRIMARY KEY DEFAULT gen_random_uuid()")

    for field in entity.fields:
        pg = _PG_TYPE[field.type]
        column = sql_identifier(field.name)
        if field.name == "id":
            default = " DEFAULT gen_random_uuid()" if field.type is FieldType.UUID else ""
            lines.append(f"    {column} {pg} PRIMARY KEY{default}")
        else:
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
            relation_column = sql_identifier(f"{relation.name}_id")
            lines.append(f"    {relation_column} UUID REFERENCES {target}({sql_identifier('id')})")
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
    """Deterministic PostgreSQL DDL for the IR's entities and relations (empty if no entities)."""

    if not isinstance(ir, ApplicationIR):
        raise TypeError("render_postgres_schema expects an ApplicationIR")
    if not ir.entities:
        return ""

    blocks: list[str] = [
        f"-- PostgreSQL schema for {ir.name}",
        "-- Generated by OmniStackAI from the Application IR. Review before applying.",
        "",
    ]
    for entity in ordered_entities(ir):
        columns = ",\n".join(_column_lines(entity))
        blocks.append(f"CREATE TABLE {sql_identifier(_table(entity.name))} (\n{columns}\n);")
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

    return "\n".join(blocks).rstrip("\n") + "\n"
