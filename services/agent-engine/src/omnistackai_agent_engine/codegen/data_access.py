"""Generate a per-entity data-access layer for the backends (reads/writes the R-238 tables).

Both renderers are pure and deterministic — they return (path, content) pairs; nothing connects to or
queries a database. Every query VALUE is parameterized (psycopg ``%s`` / pgx ``$N``); the table and
column identifiers are fixed strings derived from the IR (validated entity/field names), so no value is
ever string-interpolated into SQL.
"""

from __future__ import annotations

import re

from ..application_ir import ApplicationIR, Entity, RelationKind
from .schema_sql import table_name

# Generated-project dependency pins (only added when the data-access layer is emitted).
PSYCOPG_REQUIREMENT = "psycopg[binary]==3.2.3"
PGX_REQUIRE = "github.com/jackc/pgx/v5 v5.7.1"

_FK_KINDS = frozenset({RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE})


def _pascal(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _insert_columns(entity: Entity) -> list[str]:
    return [field.name for field in entity.fields if field.name != "id"]


def _fk_relation_names(entity: Entity) -> list[str]:
    return [relation.name for relation in entity.relations if relation.kind in _FK_KINDS]


# --------------------------------------------------------------------------- Python (FastAPI)

def _python_db(slug: str) -> str:
    return (
        "from __future__ import annotations\n\n"
        "import os\n\n"
        "import psycopg\n"
        "from psycopg.rows import dict_row\n\n"
        f'DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/{slug}")\n\n\n'
        "async def connect() -> psycopg.AsyncConnection:\n"
        '    """Open an autocommit async connection that returns dict rows. Use via ``async with``."""\n\n'
        "    return await psycopg.AsyncConnection.connect(\n"
        "        DATABASE_URL, row_factory=dict_row, autocommit=True\n"
        "    )\n"
    )


def _python_repository(entity: Entity) -> str:
    table = table_name(entity.name)
    insert_cols = _insert_columns(entity)
    if insert_cols:
        create_body = (
            f"    columns = [c for c in {insert_cols!r} if c in data]\n"
            "    if not columns:\n"
            '        sql = f"INSERT INTO {TABLE} DEFAULT VALUES RETURNING *"\n'
            "        values: list = []\n"
            "    else:\n"
            '        placeholders = ", ".join(["%s"] * len(columns))\n'
            '        sql = f"INSERT INTO {TABLE} ({\', \'.join(columns)}) VALUES ({placeholders}) RETURNING *"\n'
            "        values = [data[c] for c in columns]\n"
        )
    else:
        create_body = (
            '    sql = f"INSERT INTO {TABLE} DEFAULT VALUES RETURNING *"\n'
            "    values: list = []\n"
        )
    return (
        f'"""Data access for {entity.name} (table "{table}"). '
        'Values are parameterized; identifiers are fixed."""\n'
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        "from app.db import connect\n\n"
        f'TABLE = "{table}"\n\n\n'
        f"async def list_{table}(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:\n"
        "    async with await connect() as conn, conn.cursor() as cur:\n"
        '        await cur.execute(f"SELECT * FROM {TABLE} ORDER BY id LIMIT %s OFFSET %s", (limit, offset))\n'
        "        return await cur.fetchall()\n\n\n"
        f"async def get_{table}(id: str) -> dict[str, Any] | None:\n"
        "    async with await connect() as conn, conn.cursor() as cur:\n"
        '        await cur.execute(f"SELECT * FROM {TABLE} WHERE id = %s", (id,))\n'
        "        return await cur.fetchone()\n\n\n"
        f"async def create_{table}(data: dict[str, Any]) -> dict[str, Any]:\n"
        f"{create_body}"
        "    async with await connect() as conn, conn.cursor() as cur:\n"
        "        await cur.execute(sql, values)\n"
        "        return await cur.fetchone()\n\n\n"
        f"async def delete_{table}(id: str) -> bool:\n"
        "    async with await connect() as conn, conn.cursor() as cur:\n"
        '        await cur.execute(f"DELETE FROM {TABLE} WHERE id = %s", (id,))\n'
        "        return cur.rowcount > 0\n"
        + _python_update(entity, table)
        + _python_filtered_lists(entity, table)
    )


def _python_update(entity: Entity, table: str) -> str:
    """Emit update_<table>(id, data) — parameterized UPDATE RETURNING *."""
    update_cols = _insert_columns(entity)  # every column except id
    if update_cols:
        set_clause = ", ".join(f"{c} = %s" for c in update_cols)
        values_expr = ", ".join(f"data['{c}']" for c in update_cols)
        update_body = (
            f'        sql = f"UPDATE {{TABLE}} SET {set_clause} WHERE id = %s RETURNING *"\n'
            f"        await cur.execute(sql, ({values_expr}, id))\n"
        )
    else:
        # id-only entity — nothing to update; no-op returns the row if it exists
        update_body = (
            '        sql = f"SELECT * FROM {TABLE} WHERE id = %s"\n'
            "        await cur.execute(sql, (id,))\n"
        )
    return (
        "\n\n"
        f"async def update_{table}(id: str, data: dict) -> dict | None:\n"
        "    async with await connect() as conn, conn.cursor() as cur:\n"
        f"{update_body}"
        "        return await cur.fetchone()\n"
    )


def _python_filtered_lists(entity: Entity, table: str) -> str:
    parts = []
    for relation in _fk_relation_names(entity):
        parts.append(
            "\n\n"
            f"async def list_{table}_by_{relation}({relation}_id: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:\n"
            "    async with await connect() as conn, conn.cursor() as cur:\n"
            f'        await cur.execute(f"SELECT * FROM {{TABLE}} WHERE {relation}_id = %s ORDER BY id LIMIT %s OFFSET %s", ({relation}_id, limit, offset))\n'
            "        return await cur.fetchall()\n"
        )
    return "".join(parts)


def python_data_access_files(ir: ApplicationIR, slug: str) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = [
        ("app/db.py", _python_db(slug)),
        ("app/repositories/__init__.py", ""),
    ]
    for entity in ir.entities:
        files.append((f"app/repositories/{table_name(entity.name)}.py", _python_repository(entity)))
    return files


# --------------------------------------------------------------------------- Go (database/sql)

def _go_store(slug: str) -> str:
    return (
        "package store\n\n"
        "import (\n"
        '\t"database/sql"\n'
        '\t"os"\n\n'
        '\t_ "github.com/jackc/pgx/v5/stdlib"\n'
        ")\n\n"
        "// Open connects to PostgreSQL using DATABASE_URL via the pgx database/sql driver.\n"
        "func Open() (*sql.DB, error) {\n"
        '\tdsn := os.Getenv("DATABASE_URL")\n'
        "\tif dsn == \"\" {\n"
        f'\t\tdsn = "postgres://localhost:5432/{slug}"\n'
        "\t}\n"
        '\treturn sql.Open("pgx", dsn)\n'
        "}\n"
    )


def _go_entity_store(entity: Entity, slug: str) -> str:
    table = table_name(entity.name)
    pascal = entity.name
    cols = [field.name for field in entity.fields]
    col_list = ", ".join(cols)
    scan_targets = ", ".join(f"&m.{_pascal(c)}" for c in cols)
    insert_cols = _insert_columns(entity)

    if insert_cols:
        insert_col_list = ", ".join(insert_cols)
        placeholders = ", ".join(f"${i + 1}" for i in range(len(insert_cols)))
        insert_args = ", ".join(f"m.{_pascal(c)}" for c in insert_cols)
        create_sql = f"`INSERT INTO {table} ({insert_col_list}) VALUES ({placeholders}) RETURNING id`, {insert_args}"
    else:
        create_sql = f"`INSERT INTO {table} DEFAULT VALUES RETURNING id`"

    return (
        "package store\n\n"
        "import (\n"
        '\t"context"\n'
        '\t"database/sql"\n\n'
        f'\t"{slug}/internal/models"\n'
        ")\n\n"
        f"func List{pascal}(ctx context.Context, db *sql.DB, limit int) ([]models.{pascal}, error) {{\n"
        f"\trows, err := db.QueryContext(ctx, `SELECT {col_list} FROM {table} ORDER BY id LIMIT $1`, limit)\n"
        "\tif err != nil {\n\t\treturn nil, err\n\t}\n"
        "\tdefer rows.Close()\n"
        f"\tvar out []models.{pascal}\n"
        "\tfor rows.Next() {\n"
        f"\t\tvar m models.{pascal}\n"
        f"\t\tif err := rows.Scan({scan_targets}); err != nil {{\n\t\t\treturn nil, err\n\t\t}}\n"
        "\t\tout = append(out, m)\n"
        "\t}\n"
        "\treturn out, rows.Err()\n"
        "}\n\n"
        f"func Get{pascal}(ctx context.Context, db *sql.DB, id string) (*models.{pascal}, error) {{\n"
        f"\tvar m models.{pascal}\n"
        f"\terr := db.QueryRowContext(ctx, `SELECT {col_list} FROM {table} WHERE id = $1`, id).Scan({scan_targets})\n"
        "\tif err == sql.ErrNoRows {\n\t\treturn nil, nil\n\t}\n"
        "\tif err != nil {\n\t\treturn nil, err\n\t}\n"
        "\treturn &m, nil\n"
        "}\n\n"
        f"func Create{pascal}(ctx context.Context, db *sql.DB, m models.{pascal}) (string, error) {{\n"
        "\tvar id string\n"
        f"\terr := db.QueryRowContext(ctx, {create_sql}).Scan(&id)\n"
        "\treturn id, err\n"
        "}\n\n"
        + _go_update(entity, table, pascal, col_list, scan_targets)
        + f"func Delete{pascal}(ctx context.Context, db *sql.DB, id string) (bool, error) {{\n"
        f"\tres, err := db.ExecContext(ctx, `DELETE FROM {table} WHERE id = $1`, id)\n"
        "\tif err != nil {\n\t\treturn false, err\n\t}\n"
        "\tn, _ := res.RowsAffected()\n"
        "\treturn n > 0, nil\n"
        "}\n"
        + _go_filtered_lists(entity, table, col_list, scan_targets)
    )


def _go_update(entity: Entity, table: str, pascal: str, col_list: str, scan_targets: str) -> str:
    """Emit Update<Entity>(ctx, db, id, m) — parameterized UPDATE RETURNING full row."""
    update_cols = _insert_columns(entity)  # every column except id
    if update_cols:
        set_clause = ", ".join(f"{c} = ${i + 1}" for i, c in enumerate(update_cols))
        set_args = ", ".join(f"m.{_pascal(c)}" for c in update_cols)
        id_placeholder = f"${len(update_cols) + 1}"
        update_sql = f"`UPDATE {table} SET {set_clause} WHERE id = {id_placeholder} RETURNING {col_list}`"
        scan_call = f"db.QueryRowContext(ctx, {update_sql}, {set_args}, id).Scan({scan_targets})"
    else:
        # id-only entity — nothing to set; treat as a GET (returns the row or nil)
        scan_call = f"db.QueryRowContext(ctx, `SELECT {col_list} FROM {table} WHERE id = $1`, id).Scan({scan_targets})"
    return (
        f"func Update{pascal}(ctx context.Context, db *sql.DB, id string, m models.{pascal}) (*models.{pascal}, error) {{\n"
        f"\tvar out models.{pascal}\n"
        f"\terr := {scan_call}\n"
        "\tif err == sql.ErrNoRows {\n\t\treturn nil, nil\n\t}\n"
        "\tif err != nil {\n\t\treturn nil, err\n\t}\n"
        "\treturn &out, nil\n"
        "}\n\n"
    )


def _go_filtered_lists(entity: Entity, table: str, col_list: str, scan_targets: str) -> str:
    pascal = entity.name
    parts = []
    for relation in _fk_relation_names(entity):
        rel_pascal = _pascal(relation)
        parts.append(
            "\n"
            f"func List{pascal}By{rel_pascal}(ctx context.Context, db *sql.DB, {relation}ID string, limit int) ([]models.{pascal}, error) {{\n"
            f"\trows, err := db.QueryContext(ctx, `SELECT {col_list} FROM {table} WHERE {relation}_id = $1 ORDER BY id LIMIT $2`, {relation}ID, limit)\n"
            "\tif err != nil {\n\t\treturn nil, err\n\t}\n"
            "\tdefer rows.Close()\n"
            f"\tvar out []models.{pascal}\n"
            "\tfor rows.Next() {\n"
            f"\t\tvar m models.{pascal}\n"
            f"\t\tif err := rows.Scan({scan_targets}); err != nil {{\n\t\t\treturn nil, err\n\t\t}}\n"
            "\t\tout = append(out, m)\n"
            "\t}\n"
            "\treturn out, rows.Err()\n"
            "}\n"
        )
    return "".join(parts)


def go_data_access_files(ir: ApplicationIR, slug: str) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = [("internal/store/store.go", _go_store(slug))]
    for entity in ir.entities:
        files.append((f"internal/store/{table_name(entity.name)}.go", _go_entity_store(entity, slug)))
    return files
