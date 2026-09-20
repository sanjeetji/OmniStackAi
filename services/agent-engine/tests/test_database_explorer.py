"""Tests for the Database Explorer & SQL Editor (studio/database.py, F-09 / R-507).

Deterministic and offline: all subprocess calls (docker exec psql) are patched with
``unittest.mock.patch``; the HTTP routes are tested against a real ephemeral localhost
server with a stub workspace store, following the same pattern as test_studio_server.py.

Test groups
-----------
1. Unit: slug derivation, schema SQL discovery, CSV parsing helpers.
2. Unit: execute_query  — read-only wraps in BEGIN/ROLLBACK, write passes through.
3. Unit: get_table_rows — verifies COUNT + SELECT composition, honours limit/offset/order.
4. Integration (HTTP): GET /api/workspaces/{id}/db/tables  — 404 on bad ws, 409 if DB absent.
5. Integration (HTTP): GET /api/workspaces/{id}/db/tables/{table}
6. Integration (HTTP): POST /api/workspaces/{id}/db/query
7. Integration (HTTP): GET /api/workspaces/{id}/db/schema
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# ---- module under test ----
import omnistackai_agent_engine.studio.database as db_mod
from omnistackai_agent_engine.studio.database import (
    DatabaseNotFoundError,
    QueryExecutionError,
    QueryTooLargeError,
    check_database_exists,
    execute_query,
    get_database_name,
    get_schema_sql,
    get_table_rows,
    get_table_schema,
    list_tables,
)
from omnistackai_agent_engine.studio import create_studio_server
from omnistackai_agent_engine.studio.workspace import StudioWorkspaceStore


# ---------------------------------------------------------------------------
# Helpers for integration tests
# ---------------------------------------------------------------------------

def _stub_build(prompt: str) -> dict:
    return {"prompt": prompt, "name": "stub", "file_count": 0}


@contextmanager
def _running_server(**kwargs):
    server = create_studio_server(_stub_build, host="127.0.0.1", port=0, **kwargs)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        port = server.server_address[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        t.join(timeout=5)


def _get(url: str):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def _post(url: str, body: dict):
    raw = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=raw, method="POST",
        headers={"Content-Type": "application/json", "Content-Length": str(len(raw))},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


# Mock subprocess.CompletedProcess helper
def _ok_proc(stdout: str = "", returncode: int = 0):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout.encode("utf-8")
    m.stderr = b""
    return m


# ---------------------------------------------------------------------------
# 1. Unit — slug and schema SQL
# ---------------------------------------------------------------------------

class TestGetDatabaseName(unittest.TestCase):
    def test_normal_name(self) -> None:
        self.assertEqual(get_database_name("/home/user/my-cool-app"), "my_cool_app")

    def test_uppercase_and_spaces(self) -> None:
        self.assertEqual(get_database_name("/workspaces/Fleet Manager Pro"), "fleet_manager_pro")

    def test_empty_fallback(self) -> None:
        self.assertEqual(get_database_name("/"), "app")

    def test_trailing_separators(self) -> None:
        # pathlib.Path.name strips trailing slashes
        self.assertEqual(get_database_name("/repos/todo-list"), "todo_list")


class TestGetSchemaSql(unittest.TestCase):
    def test_returns_none_when_no_migrations_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = get_schema_sql(tmp)
            self.assertIsNone(result)

    def test_returns_init_sql_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mig = Path(tmp) / "services" / "api" / "migrations"
            mig.mkdir(parents=True)
            (mig / "0001_init.sql").write_text("CREATE TABLE foo (id SERIAL);")
            result = get_schema_sql(tmp)
            self.assertIn("CREATE TABLE foo", result)

    def test_falls_back_to_first_sql_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mig = Path(tmp) / "services" / "api" / "migrations"
            mig.mkdir(parents=True)
            (mig / "0002_add_bar.sql").write_text("ALTER TABLE foo ADD COLUMN bar TEXT;")
            result = get_schema_sql(tmp)
            self.assertIn("ALTER TABLE", result)

    def test_returns_none_when_no_sql_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mig = Path(tmp) / "services" / "api" / "migrations"
            mig.mkdir(parents=True)
            self.assertIsNone(get_schema_sql(tmp))


# ---------------------------------------------------------------------------
# 2. Unit — execute_query
# ---------------------------------------------------------------------------

class TestExecuteQuery(unittest.TestCase):
    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_read_only_wraps_in_begin_rollback(self, mock_run) -> None:
        mock_run.return_value = _ok_proc("column\n1\n")
        execute_query("mydb", "SELECT 1")
        called_input = mock_run.call_args.kwargs["input"]
        sql_text = called_input.decode("utf-8")
        self.assertIn("BEGIN", sql_text)
        self.assertIn("ROLLBACK", sql_text)
        self.assertIn("SELECT 1", sql_text)

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_write_mode_no_wrapping(self, mock_run) -> None:
        mock_run.return_value = _ok_proc("column\n1\n")
        execute_query("mydb", "INSERT INTO t VALUES (1)", write=True)
        called_input = mock_run.call_args.kwargs["input"]
        sql_text = called_input.decode("utf-8")
        self.assertNotIn("BEGIN", sql_text)
        self.assertNotIn("ROLLBACK", sql_text)
        self.assertIn("INSERT INTO t", sql_text)

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_result_structure(self, mock_run) -> None:
        mock_run.return_value = _ok_proc("id,name\n1,Alice\n2,Bob\n")
        result = execute_query("mydb", "SELECT id, name FROM users")
        self.assertEqual(result["columns"], ["id", "name"])
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["rows"][0]["name"], "Alice")
        self.assertEqual(result["rowcount"], 2)
        self.assertIn("duration_ms", result)
        self.assertFalse(result["write_mode"])

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_psql_error_raises_query_execution_error(self, mock_run) -> None:
        m = MagicMock()
        m.returncode = 1
        m.stdout = b""
        m.stderr = b"ERROR:  relation \"missing\" does not exist"
        mock_run.return_value = m
        with self.assertRaises(QueryExecutionError):
            execute_query("mydb", "SELECT * FROM missing")

    def test_empty_sql_returns_empty(self) -> None:
        result = execute_query("mydb", "   ")
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["rowcount"], 0)

    def test_oversized_sql_raises(self) -> None:
        big_sql = "SELECT 1; " * 5000  # > 32 KB
        with self.assertRaises(QueryTooLargeError):
            execute_query("mydb", big_sql)


# ---------------------------------------------------------------------------
# 3. Unit — get_table_rows
# ---------------------------------------------------------------------------

class TestGetTableRows(unittest.TestCase):
    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_two_psql_calls_made(self, mock_run) -> None:
        # First call = COUNT, second = SELECT
        mock_run.side_effect = [
            _ok_proc("count\n42\n"),
            _ok_proc("id,name\n1,Alice\n"),
        ]
        result = get_table_rows("mydb", "users")
        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(result["total"], 42)
        self.assertEqual(result["rows"][0]["name"], "Alice")

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_limit_clamped_to_500(self, mock_run) -> None:
        mock_run.side_effect = [_ok_proc("count\n5\n"), _ok_proc("id\n1\n")]
        result = get_table_rows("mydb", "t", limit=9999)
        # The SELECT sql should contain LIMIT 500
        select_sql = mock_run.call_args_list[1].kwargs["input"].decode()
        self.assertIn("LIMIT 500", select_sql)
        self.assertEqual(result["limit"], 500)

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_order_by_injected(self, mock_run) -> None:
        mock_run.side_effect = [_ok_proc("count\n1\n"), _ok_proc("id\n1\n")]
        get_table_rows("mydb", "t", order_by="created_at", direction="DESC")
        select_sql = mock_run.call_args_list[1].kwargs["input"].decode()
        self.assertIn("ORDER BY", select_sql)
        self.assertIn("created_at", select_sql)
        self.assertIn("DESC", select_sql)

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_special_chars_stripped_from_table_name(self, mock_run) -> None:
        # The sanitiser strips non-word chars so "users; DROP TABLE users;--"
        # becomes the identifier "usersDROPTABLEusers" — a single token, not a
        # SQL injection.  The security property is that no statement boundary
        # (semicolon) or comment marker (--) survives.
        mock_run.side_effect = [_ok_proc("count\n0\n"), _ok_proc("")]
        get_table_rows("mydb", "users; DROP TABLE users;--")
        select_sql = mock_run.call_args_list[1].kwargs["input"].decode()
        # Semicolons and comment markers must not appear in the composed SQL
        self.assertNotIn(";", select_sql.split("SELECT", 1)[-1].split("FROM", 1)[0])
        self.assertNotIn("--", select_sql)


# ---------------------------------------------------------------------------
# 4–7. Integration — HTTP routes via real ephemeral server
# ---------------------------------------------------------------------------

def _make_workspace_store_with_repo(tmp_dir: str) -> tuple[StudioWorkspaceStore, str]:
    """Create a workspace store with one workspace that has a minimal repo."""
    store = StudioWorkspaceStore(root_dir=tmp_dir)
    ws_id = "test-ws-1"
    store.ensure_workspace(ws_id)
    # Create migrations dir so schema endpoint works
    mig = store.repo_path(ws_id) / "services" / "api" / "migrations"
    mig.mkdir(parents=True, exist_ok=True)
    (mig / "0001_init.sql").write_text("CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT);")
    return store, ws_id


class TestDbTablesRoute(unittest.TestCase):
    """GET /api/workspaces/{id}/db/tables"""

    def test_returns_404_for_unknown_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StudioWorkspaceStore(root_dir=tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _get(f"{base}/api/workspaces/no-such-ws/db/tables")
                self.assertEqual(code, 404)

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_returns_409_when_db_absent(self, mock_run) -> None:
        # check_database_exists → empty result → no DB
        mock_run.return_value = _ok_proc("")
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _get(f"{base}/api/workspaces/{ws_id}/db/tables")
                self.assertEqual(code, 409)
                self.assertIn("database does not exist", body["error"])

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_returns_table_list(self, mock_run) -> None:
        # First call: check_database_exists → "1" (DB present)
        # Second call: list_tables → CSV rows
        mock_run.side_effect = [
            _ok_proc("1\n"),
            _ok_proc(
                "schema,name,row_count,column_count\n"
                "public,users,5,3\n"
                "public,posts,12,4\n"
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _get(f"{base}/api/workspaces/{ws_id}/db/tables")
                self.assertEqual(code, 200)
                self.assertIn("tables", body)
                names = [t["name"] for t in body["tables"]]
                self.assertIn("users", names)
                self.assertIn("posts", names)


class TestDbTableRowsRoute(unittest.TestCase):
    """GET /api/workspaces/{id}/db/tables/{table}"""

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_returns_rows_and_column_meta(self, mock_run) -> None:
        mock_run.side_effect = [
            _ok_proc("1\n"),           # check_database_exists
            _ok_proc("count\n3\n"),    # COUNT query
            _ok_proc("id,name\n1,Alice\n2,Bob\n3,Carol\n"),  # SELECT
            _ok_proc(                  # column schema
                "column_name,data_type,is_nullable,column_default\n"
                "id,integer,NO,\n"
                "name,text,YES,\n"
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _get(f"{base}/api/workspaces/{ws_id}/db/tables/users")
                self.assertEqual(code, 200)
                self.assertEqual(body["table"], "users")
                self.assertEqual(body["total"], 3)
                self.assertEqual(len(body["rows"]), 3)
                col_names = [c["column"] for c in body["columns_meta"]]
                self.assertIn("id", col_names)

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_pagination_params_forwarded(self, mock_run) -> None:
        mock_run.side_effect = [
            _ok_proc("1\n"),
            _ok_proc("count\n100\n"),
            _ok_proc("id\n11\n"),
            _ok_proc("column_name,data_type,is_nullable,column_default\nid,integer,NO,\n"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _get(
                    f"{base}/api/workspaces/{ws_id}/db/tables/orders"
                    "?limit=10&offset=10&order_by=created_at&direction=DESC"
                )
                self.assertEqual(code, 200)
                # SELECT sql should reflect the params
                select_call = mock_run.call_args_list[2]
                sql = select_call.kwargs["input"].decode()
                self.assertIn("LIMIT 10", sql)
                self.assertIn("OFFSET 10", sql)
                self.assertIn("DESC", sql)


class TestDbQueryRoute(unittest.TestCase):
    """POST /api/workspaces/{id}/db/query"""

    def test_returns_400_without_sql(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                # Patch check_database_exists so it passes
                with patch("omnistackai_agent_engine.studio.database.subprocess.run",
                           return_value=_ok_proc("1\n")):
                    code, body = _post(
                        f"{base}/api/workspaces/{ws_id}/db/query", {"sql": ""}
                    )
                    self.assertEqual(code, 400)

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_read_only_default(self, mock_run) -> None:
        mock_run.side_effect = [
            _ok_proc("1\n"),        # check_database_exists
            _ok_proc("id\n1\n"),    # execute_query
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _post(
                    f"{base}/api/workspaces/{ws_id}/db/query",
                    {"sql": "SELECT 1 AS id"},
                )
                self.assertEqual(code, 200)
                self.assertFalse(body["write_mode"])
                self.assertIn("rolled back", body["notice"])

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_write_mode_flag(self, mock_run) -> None:
        mock_run.side_effect = [
            _ok_proc("1\n"),
            _ok_proc(""),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _post(
                    f"{base}/api/workspaces/{ws_id}/db/query",
                    {"sql": "INSERT INTO users(name) VALUES ('x')", "write": True},
                )
                self.assertEqual(code, 200)
                self.assertTrue(body["write_mode"])

    @patch("omnistackai_agent_engine.studio.database.subprocess.run")
    def test_psql_error_returns_422(self, mock_run) -> None:
        bad = MagicMock()
        bad.returncode = 1
        bad.stdout = b""
        bad.stderr = b"ERROR:  syntax error at or near \"SELEC\""
        mock_run.side_effect = [_ok_proc("1\n"), bad]
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _post(
                    f"{base}/api/workspaces/{ws_id}/db/query",
                    {"sql": "SELEC * FROM users"},
                )
                self.assertEqual(code, 422)
                self.assertIn("syntax error", body["error"])


class TestDbSchemaRoute(unittest.TestCase):
    """GET /api/workspaces/{id}/db/schema"""

    def test_returns_schema_sql(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, ws_id = _make_workspace_store_with_repo(tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _get(f"{base}/api/workspaces/{ws_id}/db/schema")
                self.assertEqual(code, 200)
                self.assertIn("schema_sql", body)
                self.assertIn("CREATE TABLE users", body["schema_sql"])

    def test_returns_404_when_no_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StudioWorkspaceStore(root_dir=tmp)
            ws_id = "empty-ws"
            store.ensure_workspace(ws_id)
            # No migrations dir at all
            with _running_server(workspace_store=store) as base:
                code, body = _get(f"{base}/api/workspaces/{ws_id}/db/schema")
                self.assertEqual(code, 404)
                self.assertIn("migration SQL", body["error"])

    def test_returns_404_for_unknown_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StudioWorkspaceStore(root_dir=tmp)
            with _running_server(workspace_store=store) as base:
                code, body = _get(f"{base}/api/workspaces/ghost/db/schema")
                self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main()
