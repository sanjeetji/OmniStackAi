"""Generate a per-entity data-access layer for the backends (reads/writes the R-238 tables).

Both renderers are pure and deterministic — they return (path, content) pairs; nothing connects to or
queries a database. Every query VALUE is parameterized (psycopg ``%s`` / pgx ``$N``); the table and
column identifiers are fixed strings derived from the IR (validated entity/field names), so no value is
ever string-interpolated into SQL.
"""

from __future__ import annotations

import re

from ..application_ir import ApplicationIR, Entity, FieldType, RelationKind
from .field_validation import filter_fields
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


def _searchable_fields(entity: Entity) -> list[str]:
    return [field.name for field in entity.fields if field.type in (FieldType.STRING, FieldType.TEXT)]


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
    cols = [field.name for field in entity.fields]
    searchable = _searchable_fields(entity)
    filters = filter_fields(entity)
    filter_names = [f.name for f, _ in filters]
    filter_kwargs = "".join(f", {name}=None" for name in filter_names)
    filter_call = "".join(f", {name}={name}" for name in filter_names)

    if filters:
        # R-282: dynamic WHERE builder folding in q (search) + optional per-field equality filters.
        helper = [
            f"def _list_filters(q=None{filter_kwargs}):",
            "    conditions: list[str] = []",
            "    params: list[Any] = []",
        ]
        if searchable:
            search_or = " OR ".join(f"{f} ILIKE %s" for f in searchable)
            helper += [
                "    if q:",
                f'        conditions.append("({search_or})")',
                f'        params.extend([f"%{{q}}%"] * {len(searchable)})',
            ]
        for name in filter_names:
            helper += [
                f"    if {name} is not None:",
                f'        conditions.append("{name} = %s")',
                f"        params.append({name})",
            ]
        helper += [
            '    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""',
            "    return where, params",
        ]
        filters_helper = "\n".join(helper) + "\n\n\n"
        list_body = (
            f"        where, params = _list_filters(q{filter_call})\n"
            '        sql = f"SELECT * FROM {TABLE}{where} ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s"\n'
            "        await cur.execute(sql, (*params, limit, offset))\n"
        )
        count_body = (
            f"        where, params = _list_filters(q{filter_call})\n"
            '        await cur.execute(f"SELECT COUNT(*) AS count FROM {TABLE}{where}", tuple(params))\n'
        )
    elif searchable:
        filters_helper = ""
        search_or = " OR ".join(f"{f} ILIKE %s" for f in searchable)
        list_body = (
            '        if q:\n'
            '            pattern = f"%{q}%"\n'
            f'            sql = f"SELECT * FROM {{TABLE}} WHERE ({search_or}) ORDER BY {{sort_col}} {{sort_dir}} LIMIT %s OFFSET %s"\n'
            f'            await cur.execute(sql, (*([pattern] * {len(searchable)}), limit, offset))\n'
            '        else:\n'
            '            await cur.execute(f"SELECT * FROM {TABLE} ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s", (limit, offset))\n'
        )
        count_body = (
            '        if q:\n'
            '            pattern = f"%{q}%"\n'
            f'            sql = f"SELECT COUNT(*) AS count FROM {{TABLE}} WHERE ({search_or})"\n'
            f'            await cur.execute(sql, tuple([pattern] * {len(searchable)}))\n'
            '        else:\n'
            '            await cur.execute(f"SELECT COUNT(*) AS count FROM {TABLE}")\n'
        )
    else:
        filters_helper = ""
        list_body = (
            '        await cur.execute(f"SELECT * FROM {TABLE} ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s", (limit, offset))\n'
        )
        count_body = (
            '        await cur.execute(f"SELECT COUNT(*) AS count FROM {TABLE}")\n'
        )

    return (
        f'"""Data access for {entity.name} (table "{table}"). '
        'Values are parameterized; identifiers are fixed."""\n'
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        "from app.db import connect\n\n"
        f'TABLE = "{table}"\n'
        f"ALLOWED_SORT_FIELDS = {cols!r}\n\n\n"
        f"{filters_helper}"
        f'async def list_{table}(limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None{filter_kwargs}) -> list[dict[str, Any]]:\n'
        '    sort_col = sort if sort in ALLOWED_SORT_FIELDS else "id"\n'
        '    sort_dir = "DESC" if order.lower() == "desc" else "ASC"\n'
        "    async with await connect() as conn, conn.cursor() as cur:\n"
        f"{list_body}"
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
        "        return cur.rowcount > 0\n\n\n"
        f"async def count_{table}(q: str | None = None{filter_kwargs}) -> int:\n"
        "    async with await connect() as conn, conn.cursor() as cur:\n"
        f"{count_body}"
        "        row = await cur.fetchone()\n"
        "        return int(row[\"count\"]) if row else 0\n"
        + _python_update(entity, table)
        + _python_filtered_lists(entity, table, cols)
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


def _python_filtered_lists(entity: Entity, table: str, cols: list[str] | None = None) -> str:
    searchable = _searchable_fields(entity)
    parts = []
    for relation in _fk_relation_names(entity):
        if searchable:
            search_or = " OR ".join(f"{f} ILIKE %s" for f in searchable)
            list_exec = (
                '        if q:\n'
                '            pattern = f"%{q}%"\n'
                f'            sql = f"SELECT * FROM {{TABLE}} WHERE {relation}_id = %s AND ({search_or}) ORDER BY {{sort_col}} {{sort_dir}} LIMIT %s OFFSET %s"\n'
                f'            await cur.execute(sql, ({relation}_id, *([pattern] * {len(searchable)}), limit, offset))\n'
                '        else:\n'
                f'            await cur.execute(f"SELECT * FROM {{TABLE}} WHERE {relation}_id = %s ORDER BY {{sort_col}} {{sort_dir}} LIMIT %s OFFSET %s", ({relation}_id, limit, offset))\n'
            )
            count_exec = (
                '        if q:\n'
                '            pattern = f"%{q}%"\n'
                f'            sql = f"SELECT COUNT(*) AS count FROM {{TABLE}} WHERE {relation}_id = %s AND ({search_or})"\n'
                f'            await cur.execute(sql, ({relation}_id, *([pattern] * {len(searchable)})))\n'
                '        else:\n'
                f'            await cur.execute(f"SELECT COUNT(*) AS count FROM {{TABLE}} WHERE {relation}_id = %s", ({relation}_id,))\n'
            )
        else:
            list_exec = (
                f'        await cur.execute(f"SELECT * FROM {{TABLE}} WHERE {relation}_id = %s ORDER BY {{sort_col}} {{sort_dir}} LIMIT %s OFFSET %s", ({relation}_id, limit, offset))\n'
            )
            count_exec = (
                f'        await cur.execute(f"SELECT COUNT(*) AS count FROM {{TABLE}} WHERE {relation}_id = %s", ({relation}_id,))\n'
            )
        parts.append(
            "\n\n"
            f'async def list_{table}_by_{relation}({relation}_id: str, limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc", q: str | None = None) -> list[dict[str, Any]]:\n'
            '    sort_col = sort if sort in ALLOWED_SORT_FIELDS else "id"\n'
            '    sort_dir = "DESC" if order.lower() == "desc" else "ASC"\n'
            "    async with await connect() as conn, conn.cursor() as cur:\n"
            f"{list_exec}"
            "        return await cur.fetchall()\n\n\n"
            f"async def count_{table}_by_{relation}({relation}_id: str, q: str | None = None) -> int:\n"
            "    async with await connect() as conn, conn.cursor() as cur:\n"
            f"{count_exec}"
            "        row = await cur.fetchone()\n"
            '        return int(row["count"]) if row else 0\n'
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


def _go_sort_whitelist_block(cols: list[str]) -> str:
    cases = "".join(f'\tcase "{c}":\n\t\tcol = "{c}"\n' for c in cols)
    return (
        '\tcol := "id"\n'
        "\tswitch sort {\n"
        f"{cases}"
        "\t}\n"
        '\tdir := "ASC"\n'
        '\tif strings.ToLower(order) == "desc" {\n'
        '\t\tdir = "DESC"\n'
        "\t}\n"
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

    sort_block = _go_sort_whitelist_block(cols)
    searchable = _searchable_fields(entity)
    filters = filter_fields(entity)
    go_filters_helper = ""
    filters_param = ""

    if filters:
        # R-282: a per-store <table>Filters helper builds the WHERE (q search + per-field equality)
        # with correct $N numbering; only the whitelisted field keys ever become column identifiers.
        filter_var = f"{table}Filters"
        helper_lines = [
            f"func {filter_var}(q string, filters map[string]string) (string, []any) {{",
            "\tconds := []string{}",
            "\targs := []any{}",
        ]
        if searchable:
            search_or = " OR ".join(f"{f} ILIKE $1" for f in searchable)
            helper_lines += [
                '\tif q != "" {',
                f'\t\tconds = append(conds, "({search_or})")',
                '\t\targs = append(args, "%"+q+"%")',
                "\t}",
            ]
        for field, kind in filters:
            coerce = 'v == "true"' if kind == "bool" else "v"
            helper_lines += [
                f'\tif v, ok := filters["{field.name}"]; ok && v != "" {{',
                f'\t\tconds = append(conds, fmt.Sprintf("{field.name} = $%d", len(args)+1))',
                f"\t\targs = append(args, {coerce})",
                "\t}",
            ]
        helper_lines += [
            "\tif len(conds) == 0 {",
            '\t\treturn "", args',
            "\t}",
            '\treturn " WHERE " + strings.Join(conds, " AND "), args',
            "}",
            "",
            "",
        ]
        go_filters_helper = "\n".join(helper_lines) + "\n"
        filters_param = ", filters map[string]string"
        go_list_query = (
            f"\twhere, args := {filter_var}(q, filters)\n"
            f'\tquery := fmt.Sprintf("SELECT {col_list} FROM {table}%s ORDER BY %s %s LIMIT $%d OFFSET $%d", where, col, dir, len(args)+1, len(args)+2)\n'
            f"\targs = append(args, limit, offset)\n"
            f"\trows, err := db.QueryContext(ctx, query, args...)\n"
        )
        go_count_query = (
            f"\twhere, args := {filter_var}(q, filters)\n"
            f"\tvar count int\n"
            f'\terr := db.QueryRowContext(ctx, fmt.Sprintf("SELECT COUNT(*) FROM {table}%s", where), args...).Scan(&count)\n'
        )
    elif searchable:
        search_or = " OR ".join(f"{f} ILIKE $1" for f in searchable)
        go_list_query = (
            f'\tvar rows *sql.Rows\n'
            f'\tvar err error\n'
            f'\tif q != "" {{\n'
            f'\t\tquery := fmt.Sprintf("SELECT {col_list} FROM {table} WHERE ({search_or}) ORDER BY %s %s LIMIT $2 OFFSET $3", col, dir)\n'
            f'\t\trows, err = db.QueryContext(ctx, query, "%"+q+"%", limit, offset)\n'
            f'\t}} else {{\n'
            f'\t\tquery := fmt.Sprintf("SELECT {col_list} FROM {table} ORDER BY %s %s LIMIT $1 OFFSET $2", col, dir)\n'
            f'\t\trows, err = db.QueryContext(ctx, query, limit, offset)\n'
            f'\t}}\n'
        )
        go_count_query = (
            f'\tvar count int\n'
            f'\tvar err error\n'
            f'\tif q != "" {{\n'
            f'\t\tquery := `SELECT COUNT(*) FROM {table} WHERE ({search_or})`\n'
            f'\t\terr = db.QueryRowContext(ctx, query, "%"+q+"%").Scan(&count)\n'
            f'\t}} else {{\n'
            f'\t\terr = db.QueryRowContext(ctx, `SELECT COUNT(*) FROM {table}`).Scan(&count)\n'
            f'\t}}\n'
        )
    else:
        go_list_query = (
            f'\tquery := fmt.Sprintf("SELECT {col_list} FROM {table} ORDER BY %s %s LIMIT $1 OFFSET $2", col, dir)\n'
            f'\trows, err := db.QueryContext(ctx, query, limit, offset)\n'
        )
        go_count_query = (
            f'\tvar count int\n'
            f'\terr := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM {table}`).Scan(&count)\n'
        )

    return (
        "package store\n\n"
        "import (\n"
        '\t"context"\n'
        '\t"database/sql"\n'
        '\t"fmt"\n'
        '\t"strings"\n\n'
        f'\t"{slug}/internal/models"\n'
        ")\n\n"
        f"{go_filters_helper}"
        f"func List{pascal}(ctx context.Context, db *sql.DB, limit, offset int, sort, order, q string{filters_param}) ([]models.{pascal}, error) {{\n"
        f"{sort_block}"
        f"{go_list_query}"
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
        "}\n\n"
        f"func Count{pascal}(ctx context.Context, db *sql.DB, q string{filters_param}) (int, error) {{\n"
        f"{go_count_query}"
        "\treturn count, err\n"
        "}\n\n"
        + _go_filtered_lists(entity, table, col_list, scan_targets, cols)
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


def _go_filtered_lists(entity: Entity, table: str, col_list: str, scan_targets: str, cols: list[str] | None = None) -> str:
    pascal = entity.name
    if cols is None:
        cols = [field.name for field in entity.fields]
    sort_block = _go_sort_whitelist_block(cols)
    searchable = _searchable_fields(entity)
    parts = []
    for relation in _fk_relation_names(entity):
        rel_pascal = _pascal(relation)
        if searchable:
            search_or = " OR ".join(f"{f} ILIKE $2" for f in searchable)
            sub_list_query = (
                f'\tvar rows *sql.Rows\n'
                f'\tvar err error\n'
                f'\tif q != "" {{\n'
                f'\t\tquery := fmt.Sprintf("SELECT {col_list} FROM {table} WHERE {relation}_id = $1 AND ({search_or}) ORDER BY %s %s LIMIT $3 OFFSET $4", col, dir)\n'
                f'\t\trows, err = db.QueryContext(ctx, query, {relation}ID, "%"+q+"%", limit, offset)\n'
                f'\t}} else {{\n'
                f'\t\tquery := fmt.Sprintf("SELECT {col_list} FROM {table} WHERE {relation}_id = $1 ORDER BY %s %s LIMIT $2 OFFSET $3", col, dir)\n'
                f'\t\trows, err = db.QueryContext(ctx, query, {relation}ID, limit, offset)\n'
                f'\t}}\n'
            )
            sub_count_query = (
                f'\tvar count int\n'
                f'\tvar err error\n'
                f'\tif q != "" {{\n'
                f'\t\tquery := `SELECT COUNT(*) FROM {table} WHERE {relation}_id = $1 AND ({search_or})`\n'
                f'\t\terr = db.QueryRowContext(ctx, query, {relation}ID, "%"+q+"%").Scan(&count)\n'
                f'\t}} else {{\n'
                f'\t\terr = db.QueryRowContext(ctx, `SELECT COUNT(*) FROM {table} WHERE {relation}_id = $1`, {relation}ID).Scan(&count)\n'
                f'\t}}\n'
            )
        else:
            sub_list_query = (
                f'\tquery := fmt.Sprintf("SELECT {col_list} FROM {table} WHERE {relation}_id = $1 ORDER BY %s %s LIMIT $2 OFFSET $3", col, dir)\n'
                f'\trows, err := db.QueryContext(ctx, query, {relation}ID, limit, offset)\n'
            )
            sub_count_query = (
                f'\tvar count int\n'
                f'\terr := db.QueryRowContext(ctx, `SELECT COUNT(*) FROM {table} WHERE {relation}_id = $1`, {relation}ID).Scan(&count)\n'
            )

        parts.append(
            "\n"
            f"func List{pascal}By{rel_pascal}(ctx context.Context, db *sql.DB, {relation}ID string, limit, offset int, sort, order, q string) ([]models.{pascal}, error) {{\n"
            f"{sort_block}"
            f"{sub_list_query}"
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
            f"func Count{pascal}By{rel_pascal}(ctx context.Context, db *sql.DB, {relation}ID string, q string) (int, error) {{\n"
            f"{sub_count_query}"
            "\treturn count, err\n"
            "}\n"
        )
    return "".join(parts)


def go_data_access_files(ir: ApplicationIR, slug: str) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = [("internal/store/store.go", _go_store(slug))]
    for entity in ir.entities:
        files.append((f"internal/store/{table_name(entity.name)}.go", _go_entity_store(entity, slug)))
    return files
