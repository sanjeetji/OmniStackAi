"""Database Explorer & SQL Editor service for OmniStackAI Studio (F-09 / R-507).

Provides safe, read-only by default database access for workspace projects via the
local Postgres container (``omnistackai-local-postgres-1``).

Key contracts:
- Read-only queries are wrapped in ``BEGIN; ...; ROLLBACK;`` – the transaction is
  **always** rolled back so writes are impossible in read-only mode.
- Write mode must be explicitly requested (``write=True``).  When granted, statements
  run in autocommit mode inside psql so each statement commits independently.
- The database URL is **never** exposed to callers or logs.
- A 409 Conflict is signalled via ``DatabaseNotFoundError`` when the workspace database
  does not exist yet (preview has not been run).
- Query execution timeout defaults to 10 s and is enforced via the subprocess timeout.
- The Postgres container name is read from ``OMNISTACKAI_POSTGRES_CONTAINER`` (default
  ``omnistackai-local-postgres-1``).
- The Postgres user is read from ``OMNISTACKAI_POSTGRES_USER`` (default ``omnistackai``).
"""

from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import time
from pathlib import Path

_SLUG_RE = re.compile(r"[^a-z0-9]+")

_DEFAULT_CONTAINER = "omnistackai-local-postgres-1"
_DEFAULT_USER = "omnistackai"
_DEFAULT_MAINTENANCE_DB = "omnistackai"
_QUERY_TIMEOUT_SECONDS = 10
# Hard limit: reject suspiciously large bodies before hitting psql
_MAX_SQL_BYTES = 32 * 1024


class DatabaseNotFoundError(Exception):
    """Raised (→ 409 Conflict) when the workspace database does not exist yet."""


class QueryTooLargeError(Exception):
    """Raised when the SQL body exceeds the allowed size."""


class QueryExecutionError(Exception):
    """Raised when psql returns a non-zero exit code."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    slug = _SLUG_RE.sub("_", text.lower()).strip("_")
    return slug or "app"


def _container() -> str:
    return os.environ.get("OMNISTACKAI_POSTGRES_CONTAINER", _DEFAULT_CONTAINER)


def _db_user() -> str:
    return os.environ.get("OMNISTACKAI_POSTGRES_USER", _DEFAULT_USER)


def _maintenance_db() -> str:
    return os.environ.get("OMNISTACKAI_POSTGRES_MAINTENANCE_DB", _DEFAULT_MAINTENANCE_DB)


def _run_psql(
    db_name: str,
    sql: str,
    *,
    csv_output: bool = False,
    timeout: int = _QUERY_TIMEOUT_SECONDS,
) -> str:
    """Execute *sql* against *db_name* inside the local Postgres container.

    Returns the combined stdout as a string.
    Raises ``QueryExecutionError`` on psql exit-code != 0.
    """
    cmd = [
        "docker", "exec", "-i", _container(),
        "psql", "-U", _db_user(), "-d", db_name,
        "--no-psqlrc",
        "-v", "ON_ERROR_STOP=1",
    ]
    if csv_output:
        cmd += ["--csv", "--tuples-only"]

    try:
        result = subprocess.run(
            cmd,
            input=sql.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise QueryExecutionError(f"query timed out after {timeout}s")

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise QueryExecutionError(stderr or f"psql exited with code {result.returncode}")

    return result.stdout.decode("utf-8", errors="replace")


def _parse_csv(raw: str) -> list[dict]:
    """Parse psql --csv output into a list of row dicts (column→value)."""
    reader = csv.DictReader(io.StringIO(raw))
    return [dict(row) for row in reader]


def _parse_csv_with_header(raw: str) -> tuple[list[str], list[dict]]:
    """Return (columns, rows) from psql --csv output."""
    reader = csv.reader(io.StringIO(raw))
    rows_raw = list(reader)
    if not rows_raw:
        return [], []
    columns = rows_raw[0]
    rows = [dict(zip(columns, r)) for r in rows_raw[1:]]
    return columns, rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_database_name(repo_dir: str) -> str:
    """Return the Postgres database name for the workspace repo at *repo_dir*.

    The name is the same slug computed by ``localrun/plan.py``: slug of the
    directory *basename* of the repo.
    """
    return _slug(Path(repo_dir).name)


def check_database_exists(db_name: str) -> bool:
    """Return True when *db_name* exists in the local Postgres container."""
    sql = f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';\n"
    try:
        out = _run_psql(_maintenance_db(), sql, csv_output=True, timeout=5)
        return "1" in out
    except QueryExecutionError:
        return False


def list_tables(repo_dir: str, db_name: str) -> list[dict]:
    """Return a list of table descriptors for the workspace database.

    Each dict contains:
      - ``name`` (str): table name
      - ``schema`` (str): schema name (usually ``public``)
      - ``row_count`` (int): approximate live tuple count from ``pg_stat_user_tables``
      - ``column_count`` (int): number of columns
    """
    sql = (
        "SELECT "
        "  t.table_schema AS schema,"
        "  t.table_name AS name,"
        "  COALESCE(s.n_live_tup, 0)::text AS row_count,"
        "  (SELECT COUNT(*) FROM information_schema.columns c "
        "   WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name)::text AS column_count "
        "FROM information_schema.tables t "
        "LEFT JOIN pg_stat_user_tables s "
        "  ON s.schemaname = t.table_schema AND s.relname = t.table_name "
        "WHERE t.table_schema NOT IN ('pg_catalog','information_schema') "
        "  AND t.table_type = 'BASE TABLE' "
        "ORDER BY t.table_schema, t.table_name;\n"
    )
    out = _run_psql(db_name, sql, csv_output=True)
    rows = _parse_csv(out)
    return [
        {
            "schema": r.get("schema", "public"),
            "name": r.get("name", ""),
            "row_count": int(r.get("row_count", 0) or 0),
            "column_count": int(r.get("column_count", 0) or 0),
        }
        for r in rows
    ]


def get_table_schema(db_name: str, table: str, schema: str = "public") -> list[dict]:
    """Return column definitions for *table* in *schema*.

    Each dict contains:
      - ``column`` (str)
      - ``type`` (str)
      - ``nullable`` (bool)
      - ``default`` (str|None)
    """
    # Sanitise table and schema: only allow identifier characters
    safe_table = re.sub(r"[^a-zA-Z0-9_]", "", table)
    safe_schema = re.sub(r"[^a-zA-Z0-9_]", "", schema)
    sql = (
        "SELECT column_name, data_type, is_nullable, column_default "
        "FROM information_schema.columns "
        f"WHERE table_schema = '{safe_schema}' AND table_name = '{safe_table}' "
        "ORDER BY ordinal_position;\n"
    )
    out = _run_psql(db_name, sql, csv_output=True)
    rows = _parse_csv(out)
    return [
        {
            "column": r.get("column_name", ""),
            "type": r.get("data_type", ""),
            "nullable": (r.get("is_nullable", "YES") == "YES"),
            "default": r.get("column_default") or None,
        }
        for r in rows
    ]


def get_table_rows(
    db_name: str,
    table: str,
    *,
    schema: str = "public",
    limit: int = 100,
    offset: int = 0,
    order_by: str | None = None,
    direction: str = "ASC",
) -> dict:
    """Return paginated rows from *table*.

    Returns a dict:
      - ``columns`` (list[str])
      - ``rows`` (list[dict])
      - ``total`` (int): approximate row count
      - ``limit`` (int)
      - ``offset`` (int)
    """
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    safe_table = re.sub(r"[^a-zA-Z0-9_]", "", table)
    safe_schema = re.sub(r"[^a-zA-Z0-9_]", "", schema)
    safe_dir = "DESC" if direction.upper() == "DESC" else "ASC"

    order_clause = ""
    if order_by:
        safe_col = re.sub(r"[^a-zA-Z0-9_]", "", order_by)
        if safe_col:
            order_clause = f' ORDER BY "{safe_col}" {safe_dir}'

    count_sql = (
        f'SELECT COUNT(*)::text FROM "{safe_schema}"."{safe_table}";\n'
    )
    data_sql = (
        f'SELECT * FROM "{safe_schema}"."{safe_table}"{order_clause} '
        f"LIMIT {limit} OFFSET {offset};\n"
    )

    count_out = _run_psql(db_name, count_sql, csv_output=True)
    total = 0
    try:
        total = int(count_out.strip().splitlines()[-1].strip())
    except (ValueError, IndexError):
        pass

    data_out = _run_psql(db_name, data_sql, csv_output=True)
    columns, rows = _parse_csv_with_header(data_out)

    return {
        "columns": columns,
        "rows": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def execute_query(
    db_name: str,
    sql: str,
    *,
    write: bool = False,
    log_manager=None,
    workspace_id: str | None = None,
) -> dict:
    """Execute *sql* against *db_name*.

    Read-only mode (default, ``write=False``):
      - Wraps the statement(s) in ``BEGIN; ... ROLLBACK;``
      - Guarantees no mutations survive.

    Write mode (``write=True``):
      - Executes statements directly (autocommit in psql).
      - **Must only be enabled by an explicit user toggle.**

    Returns a dict:
      - ``rows`` (list[dict]): result rows (empty for non-SELECT)
      - ``columns`` (list[str])
      - ``rowcount`` (int): number of rows returned
      - ``duration_ms`` (float): wall-clock execution time
      - ``write_mode`` (bool)
      - ``notice`` (str): human-readable mode notice
    """
    if len(sql.encode("utf-8")) > _MAX_SQL_BYTES:
        raise QueryTooLargeError(f"SQL body exceeds {_MAX_SQL_BYTES} bytes")

    sql_stripped = sql.strip()
    if not sql_stripped:
        return {
            "rows": [], "columns": [], "rowcount": 0,
            "duration_ms": 0.0, "write_mode": write,
            "notice": "empty query",
        }

    if write:
        effective_sql = sql_stripped
        notice = "write mode: changes committed"
    else:
        effective_sql = f"BEGIN;\n{sql_stripped};\nROLLBACK;\n"
        notice = "read-only mode: transaction rolled back"

    t0 = time.monotonic()
    out = _run_psql(db_name, effective_sql, csv_output=True)
    duration_ms = (time.monotonic() - t0) * 1000

    columns, rows = _parse_csv_with_header(out)

    # Audit log
    if log_manager is not None and workspace_id:
        try:
            log_manager.append_build_log(
                workspace_id,
                level="info",
                phase="db_query",
                message=f"[DB] write={write} rows={len(rows)} duration={duration_ms:.1f}ms",
            )
        except Exception:
            pass

    return {
        "rows": rows,
        "columns": columns,
        "rowcount": len(rows),
        "duration_ms": round(duration_ms, 2),
        "write_mode": write,
        "notice": notice,
    }


def get_schema_sql(repo_dir: str) -> str | None:
    """Return the contents of ``services/api/migrations/0001_init.sql``, if it exists.

    This is the canonical generated schema file created during the build phase.
    Returns None when no migrations exist yet.
    """
    migrations_dir = Path(repo_dir) / "services" / "api" / "migrations"
    if not migrations_dir.is_dir():
        return None
    init_sql = migrations_dir / "0001_init.sql"
    if not init_sql.is_file():
        # Fall back to the first alphabetically sorted .sql file
        sql_files = sorted(migrations_dir.glob("*.sql"))
        if not sql_files:
            return None
        init_sql = sql_files[0]
    try:
        return init_sql.read_text(encoding="utf-8")
    except OSError:
        return None
