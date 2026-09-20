"""A dependency-free (stdlib ``http.server``) web server for the OmniStackAI Studio.

Serves the chat-to-create page at ``GET /`` and handles ``POST /api/build``. The build
function is INJECTED (``build_fn(prompt) -> dict``) so the HTTP layer is fully testable
offline against an in-memory stub; the live local-Ollama wiring lives in ``live_serve``.
No web framework, no external dependencies.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
from collections.abc import AsyncIterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

from ..intake.ecosystem import propose_ecosystem
from ..solution_packs import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    EcosystemPackRegistry,
    SolutionPackRegistry,
)
from .database import (
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
from .files import BuildNotFoundError, FileNotFoundInBuildError, PathOutsideBuildError
from .page import STUDIO_HTML
from .problems import NoWebTargetError, ProblemsNotCheckedError, ToolchainNotInstalledError
from .session import EditNotSupportedError
from .workspace import StudioWorkspaceStore, WorkspaceLockedError, WorkspaceNotFoundError

BuildFn = Callable[..., dict]
ControlFn = Callable[..., dict]
PreviewBuildFn = Callable[..., dict]
FileTreeFn = Callable[[str], dict]
EditFn = Callable[[str, str], dict]
ReadFileFn = Callable[[str, str], dict]
ProblemsFn = Callable[[str], dict]
ProvidersFn = Callable[[], dict]
BuildStreamFn = Callable[[str], AsyncIterator[dict]]
WorkspaceBuildFn = Callable[..., dict]
WorkspaceBuildStreamFn = Callable[..., AsyncIterator[dict]]

_MAX_BODY_BYTES = 64 * 1024


def _make_handler(
    build_fn: BuildFn,
    status_fn: ControlFn | None,
    stop_fn: ControlFn | None,
    restart_fn: ControlFn | None,
    history_fn: ControlFn | None,
    preview_build_fn: PreviewBuildFn | None,
    open_dir_fn: PreviewBuildFn | None,
    delete_build_fn: PreviewBuildFn | None,
    file_tree_fn: FileTreeFn | None = None,
    read_file_fn: ReadFileFn | None = None,
    edit_fn: EditFn | None = None,
    turns_fn: FileTreeFn | None = None,
    problems_check_fn: ProblemsFn | None = None,
    problems_get_fn: ProblemsFn | None = None,
    providers_fn: ProvidersFn | None = None,
    build_stream_fn: BuildStreamFn | None = None,
    registry: SolutionPackRegistry | None = None,
    ecosystem_registry: EcosystemPackRegistry | None = None,
    switch_surface_fn: PreviewBuildFn | None = None,
    get_ecosystem_auth_fn: ControlFn | None = None,
    get_ecosystem_state_fn: ControlFn | None = None,
    get_ecosystem_events_fn: ControlFn | None = None,
    dispatch_ecosystem_event_fn: Callable[..., dict] | None = None,
    get_ecosystem_telemetry_fn: ControlFn | None = None,
    get_ecosystem_deployment_fn: ControlFn | None = None,
    to_compose_yaml_fn: Callable[[], str | None] | None = None,
    get_ecosystem_sync_fn: ControlFn | None = None,
    push_sync_mutations_fn: Callable[[str, list[dict]], dict] | None = None,
    pull_sync_changes_fn: Callable[[str, int], dict] | None = None,
    simulate_sync_conflict_fn: Callable[..., dict] | None = None,
    get_ecosystem_cicd_fn: ControlFn | None = None,
    to_workflow_yaml_fn: Callable[[], str | None] | None = None,
    simulate_cicd_run_fn: Callable[[str], dict] | None = None,
    get_ecosystem_verification_fn: ControlFn | None = None,
    simulate_ecosystem_verification_fn: ControlFn | None = None,
    get_ecosystem_recovery_fn: ControlFn | None = None,
    simulate_ecosystem_recovery_fn: ControlFn | None = None,
    get_ecosystem_capacity_fn: ControlFn | None = None,
    simulate_ecosystem_capacity_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_alerting_fn: ControlFn | None = None,
    simulate_ecosystem_alerting_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_sla_fn: ControlFn | None = None,
    simulate_ecosystem_sla_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_governance_fn: ControlFn | None = None,
    simulate_ecosystem_governance_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_docs_fn: ControlFn | None = None,
    export_ecosystem_docs_fn: Callable[..., dict] | ControlFn | None = None,
    workspace_store: StudioWorkspaceStore | None = None,
    workspace_build_fn: WorkspaceBuildFn | None = None,
    workspace_build_stream_fn: WorkspaceBuildStreamFn | None = None,
    workspace_edit_fn: EditFn | None = None,
    workspace_preview_fn: PreviewBuildFn | None = None,
    workspace_preview_status_fn: PreviewBuildFn | None = None,
    workspace_preview_stop_fn: PreviewBuildFn | None = None,
    workspace_problems_check_fn: ProblemsFn | None = None,
    workspace_problems_get_fn: ProblemsFn | None = None,
    workspace_cancel_fn: Callable[[str], dict] | None = None,
    workspace_logs_fn: Callable[..., dict] | None = None,
    workspace_logs_stream_fn: Callable[..., AsyncIterator[dict]] | None = None,
    workspace_logs_clear_fn: Callable[..., dict] | None = None,
) -> type[BaseHTTPRequestHandler]:
    pack_registry = registry or DEFAULT_SOLUTION_PACK_REGISTRY
    eco_registry = ecosystem_registry or DEFAULT_ECOSYSTEM_PACK_REGISTRY

    class StudioHandler(BaseHTTPRequestHandler):
        server_version = "OmniStackAIStudio/1.0"

        def log_message(self, *args) -> None:  # keep the console quiet
            return

        def _send(self, code: int, content_type: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _send_json(self, code: int, payload: dict) -> None:
            self._send(code, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

        def _drain_body(self) -> None:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length:
                self.rfile.read(min(length, _MAX_BODY_BYTES))

        def _run_control(self, fn: ControlFn | None) -> None:
            self._drain_body()
            if fn is None:
                self._send_json(404, {"error": "preview controls are not enabled"})
                return
            try:
                self._send_json(200, fn())
            except Exception as error:  # surface any control failure as a clean 502
                self._send_json(502, {"error": str(error)})

        def _read_json_body(self) -> dict | None:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length > _MAX_BODY_BYTES:
                self._send_json(413, {"error": "request body too large"})
                return None
            raw = self.rfile.read(length) if length else b""
            try:
                return json.loads(raw.decode("utf-8")) if raw else {}
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                self._send_json(400, {"error": "invalid JSON body"})
                return None

        def _run_id_control(self, fn: PreviewBuildFn | None) -> None:
            data = self._read_json_body()
            if data is None:
                return
            if fn is None:
                self._send_json(404, {"error": "preview controls are not enabled"})
                return
            build_id = str(data.get("id", "")).strip()
            if not build_id:
                self._send_json(400, {"error": "id is required"})
                return
            try:
                self._send_json(200, fn(build_id))
            except Exception as error:  # surface any control failure as a clean 502
                self._send_json(502, {"error": str(error)})

        @staticmethod
        def _build_id_for_suffix(path: str, suffix: str) -> str | None:
            """``/api/build/<id><suffix>`` -> ``<id>``, or None when the path doesn't match.

            The id itself must not contain ``/`` (recorded build ids never do); a path like
            ``/api/build/1/2/files`` is therefore not a match and falls through to the generic 404.
            """
            prefix = "/api/build/"
            if not (path.startswith(prefix) and path.endswith(suffix)):
                return None
            build_id = unquote(path[len(prefix) : -len(suffix)])
            return build_id if build_id and "/" not in build_id else None

        @staticmethod
        def _workspace_id_for_suffix(path: str, suffix: str) -> str | None:
            prefix = "/api/workspaces/"
            if not path.startswith(prefix):
                return None
            if suffix:
                if not path.endswith(suffix):
                    return None
                ws_id = unquote(path[len(prefix) : -len(suffix)])
            else:
                ws_id = unquote(path[len(prefix) :])
            return ws_id if ws_id and "/" not in ws_id else None

        def _handle_workspace_get_state(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            state = workspace_store.get_state(ws_id)
            if state is None:
                self._send_json(404, {"error": f"workspace {ws_id} not found"})
                return
            self._send_json(200, state)

        def _handle_workspace_file_tree(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            try:
                self._send_json(200, workspace_store.list_files(ws_id))
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_read_file(self, ws_id: str, query: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            rel_path = parse_qs(query).get("path", [""])[0]
            if not rel_path:
                self._send_json(400, {"error": "path is required"})
                return
            try:
                self._send_json(200, workspace_store.read_file(ws_id, rel_path))
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except PathOutsideBuildError as error:
                self._send_json(400, {"error": str(error)})
            except FileNotFoundInBuildError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_turns(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            self._send_json(200, {"turns": workspace_store.get_turns(ws_id)})

        def _handle_workspace_get_problems(self, ws_id: str) -> None:
            if workspace_problems_get_fn is None:
                self._send_json(404, {"error": "problems checking is not enabled"})
                return
            try:
                self._send_json(200, workspace_problems_get_fn(ws_id))
            except ProblemsNotCheckedError as error:
                self._send_json(404, {"error": str(error)})
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_problems_check(self, ws_id: str) -> None:
            if workspace_problems_check_fn is None:
                self._send_json(404, {"error": "problems checking is not enabled"})
                return
            try:
                res = workspace_problems_check_fn(ws_id)
                self._send_json(200, res)
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except NoWebTargetError as error:
                self._send_json(400, {"error": str(error)})
            except ToolchainNotInstalledError as error:
                self._send_json(409, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_preview(self, ws_id: str) -> None:
            if workspace_preview_fn is None:
                self._send_json(404, {"error": "preview is not enabled"})
                return

            body_data = self._read_json_body() if int(self.headers.get("Content-Length", 0) or 0) > 0 else {}
            extra_env = body_data.get("env") if isinstance(body_data, dict) and isinstance(body_data.get("env"), dict) else None

            accept_header = self.headers.get("Accept", "")
            if "text/event-stream" in accept_header:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()

                def _stream_cb(phase: str) -> None:
                    self._write_sse_event({"status": "starting", "phase": phase})

                try:
                    res = workspace_preview_fn(ws_id, on_phase=_stream_cb, env=extra_env)
                except TypeError:
                    try:
                        res = workspace_preview_fn(ws_id, on_phase=_stream_cb)
                    except TypeError:
                        res = workspace_preview_fn(ws_id)
                except Exception as error:
                    self._write_sse_event({"status": "error", "phase": "error", "error": str(error)})
                    return
                self._write_sse_event(res)
                return

            try:
                try:
                    res = workspace_preview_fn(ws_id, env=extra_env)
                except TypeError:
                    res = workspace_preview_fn(ws_id)
                self._send_json(200, res)
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_preview_status(self, ws_id: str) -> None:
            if workspace_preview_status_fn is None:
                self._send_json(404, {"error": "preview is not enabled"})
                return
            try:
                res = workspace_preview_status_fn(ws_id)
                self._send_json(200, res)
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_preview_stop(self, ws_id: str) -> None:
            if workspace_preview_stop_fn is None:
                self._send_json(404, {"error": "preview is not enabled"})
                return
            try:
                res = workspace_preview_stop_fn(ws_id)
                self._send_json(200, res)
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_export(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            buf = io.BytesIO()
            try:
                workspace_store.export_zip(ws_id, buf)
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
                return
            except Exception as error:
                self._send_json(502, {"error": str(error)})
                return

            data = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{ws_id}.zip"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _handle_workspace_git_status(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            try:
                res = workspace_store.git_status(ws_id)
                self._send_json(200, res)
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_git_push(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            data = self._read_json_body()
            if data is None:
                return
            remote_url = str(data.get("remote_url", "")).strip()
            branch = str(data.get("branch", "main")).strip() or "main"
            try:
                res = workspace_store.git_push(ws_id, remote_url, branch)
                self._send_json(200, res)
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_seo_audit(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            try:
                repo_dir = workspace_store.repo_path(ws_id)
                from ..seo import audit_project_seo
                res = audit_project_seo(repo_dir)
                self._send_json(200, res)
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_seo_page(self, ws_id: str) -> None:
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return
            data = self._read_json_body() or {}
            route = str(data.get("route", "/"))
            title = str(data.get("title", ""))
            description = str(data.get("description", ""))
            noindex = bool(data.get("noindex", False))
            try:
                res = workspace_store.update_page_seo(ws_id, route, title, description, noindex)
                self._send_json(200, res)
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_seo_suggest(self, ws_id: str) -> None:
            data = self._read_json_body() or {}
            route = str(data.get("route", "/"))
            page_name = str(data.get("page_name", "")).strip()
            if not page_name:
                page_name = route.strip("/").replace("-", " ").capitalize() or "Home"
            title_suggestion = f"{page_name} — Fast, Reliable & Secure"
            desc_suggestion = f"Discover and explore {page_name.lower()} with intuitive features, real-time updates, and seamless performance designed for modern teams."
            self._send_json(200, {
                "suggested_title": title_suggestion,
                "suggested_description": desc_suggestion,
            })

        def _handle_workspace_build(self, ws_id: str) -> None:
            data = self._read_json_body()
            if data is None:
                return
            if workspace_build_fn is None:
                self._send_json(404, {"error": "workspace build is not enabled"})
                return
            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                self._send_json(400, {"error": "prompt is required"})
                return
            options = {k: v for k, v in data.items() if k != "prompt"}
            try:
                res = workspace_build_fn(ws_id, prompt, **options)
            except WorkspaceLockedError as error:
                self._send_json(409, {"error": str(error)})
                return
            except Exception as error:
                self._send_json(502, {"error": str(error)})
                return
            self._send_json(200, res)

        def _handle_workspace_build_stream(self, ws_id: str) -> None:
            data = self._read_json_body()
            if data is None:
                return
            if workspace_build_stream_fn is None:
                self._send_json(404, {"error": "workspace build streaming is not enabled"})
                return
            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                self._send_json(400, {"error": "prompt is required"})
                return
            if data.get("pack_id") or data.get("ecosystem_id") or data.get("hybrid_ui"):
                self._send_json(
                    400,
                    {"error": "streaming is only supported for a plain-prompt, non-hybrid_ui build today"},
                )
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            options = {k: v for k, v in data.items() if k != "prompt"}

            async def _drain() -> None:
                async for event in workspace_build_stream_fn(ws_id, prompt, **options):
                    self._write_sse_event(event)

            try:
                asyncio.run(_drain())
            except Exception as error:
                self._write_sse_event({"phase": "error", "error": str(error)})

        def _handle_workspace_edit(self, ws_id: str) -> None:
            data = self._read_json_body()
            if data is None:
                return
            if workspace_edit_fn is None:
                self._send_json(404, {"error": "editing is not enabled"})
                return
            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                self._send_json(400, {"error": "prompt is required"})
                return
            options = {k: v for k, v in data.items() if k != "prompt"}
            try:
                try:
                    maybe_coro = workspace_edit_fn(ws_id, prompt, **options)
                except TypeError:
                    maybe_coro = workspace_edit_fn(ws_id, prompt)
                if asyncio.iscoroutine(maybe_coro):
                    res = asyncio.run(maybe_coro)
                else:
                    res = maybe_coro
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
                return
            except EditNotSupportedError as error:
                self._send_json(400, {"error": str(error)})
                return
            except WorkspaceLockedError as error:
                self._send_json(409, {"error": str(error)})
                return
            except Exception as error:
                self._send_json(502, {"error": str(error)})
                return
            self._send_json(200, res)

        def _handle_workspace_cancel(self, ws_id: str) -> None:
            self._drain_body()
            if workspace_cancel_fn is not None:
                try:
                    res = workspace_cancel_fn(ws_id)
                    self._send_json(200, res or {"status": "cancelling", "workspace_id": ws_id})
                    return
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                    return
            if workspace_store is not None:
                workspace_store.set_cancelled(ws_id)
                self._send_json(200, {"status": "cancelling", "workspace_id": ws_id})
                return
            self._send_json(404, {"error": "workspaces are not enabled"})

        def _handle_workspace_logs(self, ws_id: str, query: str) -> None:
            if workspace_logs_fn is None:
                from .logs import StudioLogManager
                log_mgr = StudioLogManager()
                logs_fn = log_mgr.read_logs
                logs_stream_fn = log_mgr.stream_logs
            else:
                logs_fn = workspace_logs_fn
                logs_stream_fn = workspace_logs_stream_fn

            params = parse_qs(query)
            source = params.get("source", ["build"])[0]
            since_str = params.get("since", [None])[0]
            since = int(since_str) if since_str and since_str.isdigit() else None
            follow = params.get("follow", ["0"])[0] in ("1", "true", "yes")
            limit_str = params.get("limit", ["500"])[0]
            limit = int(limit_str) if limit_str and limit_str.isdigit() else 500

            if follow and logs_stream_fn is not None:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()

                async def _drain() -> None:
                    async for event in logs_stream_fn(ws_id, source=source, since=since):
                        self._write_sse_event(event)

                try:
                    asyncio.run(_drain())
                except Exception as error:
                    self._write_sse_event({"error": str(error)})
                return

            try:
                res = logs_fn(ws_id, source=source, since=since, limit=limit)
                self._send_json(200, res)
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_logs_clear(self, ws_id: str, query: str) -> None:
            params = parse_qs(query)
            source = params.get("source", [None])[0]
            if workspace_logs_clear_fn is not None:
                try:
                    res = workspace_logs_clear_fn(ws_id, source=source)
                    self._send_json(200, res)
                    return
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                    return
            from .logs import StudioLogManager
            log_mgr = StudioLogManager()
            res = log_mgr.clear_logs(ws_id, source=source)
            self._send_json(200, res)

        # ------------------------------------------------------------------
        # Database Explorer handlers (F-09 / R-507)
        # ------------------------------------------------------------------

        def _db_require_workspace(self, ws_id: str) -> str | None:
            """Return repo_dir string or send a 404 and return None."""
            if workspace_store is None:
                self._send_json(404, {"error": "workspaces are not enabled"})
                return None
            try:
                repo_dir = str(workspace_store.repo_path(ws_id))
            except Exception:
                self._send_json(404, {"error": f"workspace {ws_id!r} not found"})
                return None
            if not workspace_store.exists(ws_id):
                self._send_json(404, {"error": f"workspace {ws_id!r} not found"})
                return None
            return repo_dir

        def _db_require_database(self, db_name: str) -> bool:
            """Return True if DB exists, else send 409 and return False."""
            if not check_database_exists(db_name):
                self._send_json(409, {
                    "error": "database does not exist yet — run preview first",
                    "db_name": db_name,
                })
                return False
            return True

        def _handle_workspace_db_tables(self, ws_id: str) -> None:
            """GET /api/workspaces/{id}/db/tables"""
            repo_dir = self._db_require_workspace(ws_id)
            if repo_dir is None:
                return
            db_name = get_database_name(repo_dir)
            if not self._db_require_database(db_name):
                return
            try:
                tables = list_tables(repo_dir, db_name)
                self._send_json(200, {"db_name": db_name, "tables": tables})
            except QueryExecutionError as error:
                self._send_json(502, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_db_table_rows(self, ws_id: str, table: str, query: str) -> None:
            """GET /api/workspaces/{id}/db/tables/{table}"""
            repo_dir = self._db_require_workspace(ws_id)
            if repo_dir is None:
                return
            db_name = get_database_name(repo_dir)
            if not self._db_require_database(db_name):
                return
            params = parse_qs(query)
            limit = int(params.get("limit", ["100"])[0] or 100)
            offset = int(params.get("offset", ["0"])[0] or 0)
            order_by = params.get("order_by", [None])[0]
            direction = params.get("direction", ["ASC"])[0].upper()
            schema = params.get("schema", ["public"])[0] or "public"
            try:
                rows_data = get_table_rows(
                    db_name,
                    table,
                    schema=schema,
                    limit=limit,
                    offset=offset,
                    order_by=order_by,
                    direction=direction,
                )
                columns_meta = get_table_schema(db_name, table, schema=schema)
                self._send_json(200, {
                    "db_name": db_name,
                    "table": table,
                    "schema": schema,
                    "columns_meta": columns_meta,
                    **rows_data,
                })
            except QueryExecutionError as error:
                self._send_json(502, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_db_query(self, ws_id: str) -> None:
            """POST /api/workspaces/{id}/db/query"""
            repo_dir = self._db_require_workspace(ws_id)
            if repo_dir is None:
                return
            db_name = get_database_name(repo_dir)
            if not self._db_require_database(db_name):
                return
            data = self._read_json_body()
            if data is None:
                return
            sql = str(data.get("sql", "")).strip()
            if not sql:
                self._send_json(400, {"error": "sql is required"})
                return
            write = bool(data.get("write", False))
            try:
                from .logs import StudioLogManager
                log_mgr = StudioLogManager()
                result = execute_query(
                    db_name,
                    sql,
                    write=write,
                    log_manager=log_mgr,
                    workspace_id=ws_id,
                )
                self._send_json(200, {"db_name": db_name, **result})
            except QueryTooLargeError as error:
                self._send_json(413, {"error": str(error)})
            except QueryExecutionError as error:
                self._send_json(422, {"error": str(error)})
            except Exception as error:
                self._send_json(502, {"error": str(error)})

        def _handle_workspace_db_schema(self, ws_id: str) -> None:
            """GET /api/workspaces/{id}/db/schema"""
            repo_dir = self._db_require_workspace(ws_id)
            if repo_dir is None:
                return
            db_name = get_database_name(repo_dir)
            sql = get_schema_sql(repo_dir)
            if sql is None:
                self._send_json(404, {
                    "error": "no migration SQL found — build the project first",
                    "db_name": db_name,
                })
                return
            self._send_json(200, {"db_name": db_name, "schema_sql": sql})

        def _handle_file_tree(self, build_id: str) -> None:
            if file_tree_fn is None:
                self._send_json(404, {"error": "file browsing is not enabled"})
                return
            try:
                self._send_json(200, file_tree_fn(build_id))
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:  # surface any other failure as a clean 502
                self._send_json(502, {"error": str(error)})

        def _handle_read_file(self, build_id: str, query: str) -> None:
            if read_file_fn is None:
                self._send_json(404, {"error": "file browsing is not enabled"})
                return
            rel_path = parse_qs(query).get("path", [""])[0]
            if not rel_path:
                self._send_json(400, {"error": "path is required"})
                return
            try:
                self._send_json(200, read_file_fn(build_id, rel_path))
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except PathOutsideBuildError as error:
                self._send_json(400, {"error": str(error)})
            except FileNotFoundInBuildError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:  # surface any other failure as a clean 502
                self._send_json(502, {"error": str(error)})

        def _handle_turns(self, build_id: str) -> None:
            if turns_fn is None:
                self._send_json(404, {"error": "editing is not enabled"})
                return
            try:
                self._send_json(200, turns_fn(build_id))
            except Exception as error:  # a session read never targets a specific build_id error today
                self._send_json(502, {"error": str(error)})

        def _handle_check_problems(self, build_id: str) -> None:
            if problems_check_fn is None:
                self._send_json(404, {"error": "problems checking is not enabled"})
                return
            try:
                self._send_json(200, problems_check_fn(build_id))
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except NoWebTargetError as error:
                self._send_json(400, {"error": str(error)})
            except ToolchainNotInstalledError as error:
                self._send_json(409, {"error": str(error)})
            except Exception as error:  # surface any other failure (a real tsc crash) as a clean 502
                self._send_json(502, {"error": str(error)})

        def _handle_get_problems(self, build_id: str) -> None:
            if problems_get_fn is None:
                self._send_json(404, {"error": "problems checking is not enabled"})
                return
            try:
                self._send_json(200, problems_get_fn(build_id))
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except ProblemsNotCheckedError as error:
                self._send_json(404, {"error": str(error)})
            except Exception as error:  # surface any other failure as a clean 502
                self._send_json(502, {"error": str(error)})

        def _write_sse_event(self, payload: dict) -> None:
            """Write one SSE `data:` frame and flush immediately (R-484) - a real, incremental
            frame the client sees as soon as it's written, not buffered until the connection
            closes. Tolerates the client having already disconnected (a real, ordinary occurrence
            for a long-lived stream) rather than raising into the handler thread."""
            try:
                self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

        def _handle_build_stream(self) -> None:
            data = self._read_json_body()
            if data is None:
                return
            if build_stream_fn is None:
                self._send_json(404, {"error": "build streaming is not enabled"})
                return
            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                self._send_json(400, {"error": "prompt is required"})
                return
            # Reject an unsupported build kind BEFORE any SSE framing begins (a plain JSON 400,
            # never a broken half-open stream) - server.py stays framework-agnostic and testable
            # with a plain stub by checking this itself, rather than importing live_serve.py's own
            # StreamingBuildNotSupportedError (which would invert this module's dependency
            # direction: live_serve.py imports from server.py today, never the reverse).
            if data.get("pack_id") or data.get("ecosystem_id") or data.get("hybrid_ui"):
                self._send_json(
                    400,
                    {"error": "streaming is only supported for a plain-prompt, non-hybrid_ui build today"},
                )
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            # No Content-Length/chunked framing (by design - see module docstring), so the client's
            # only way to detect the end of the SSE body is the connection closing. BaseHTTPRequestHandler
            # special-cases the literal value "keep-alive" in send_header to mean "don't close the
            # socket" (self.close_connection = False) - sending that here would tell the client to
            # expect more bytes forever, hanging every real client. "close" is the correct, honest value.
            self.send_header("Connection", "close")
            self.send_header("X-Accel-Buffering", "no")  # reverse proxies must not buffer this
            self.end_headers()

            async def _drain() -> None:
                async for event in build_stream_fn(prompt):
                    self._write_sse_event(event)

            try:
                asyncio.run(_drain())
            except Exception as error:  # a genuinely unexpected failure mid-stream - report it as
                self._write_sse_event({"phase": "error", "error": str(error)})  # one last real frame

        def _handle_edit(self, build_id: str) -> None:
            data = self._read_json_body()
            if data is None:
                return
            if edit_fn is None:
                self._send_json(404, {"error": "editing is not enabled"})
                return
            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                self._send_json(400, {"error": "prompt is required"})
                return
            try:
                self._send_json(200, edit_fn(build_id, prompt))
            except BuildNotFoundError as error:
                self._send_json(404, {"error": str(error)})
            except EditNotSupportedError as error:
                self._send_json(400, {"error": str(error)})
            except Exception as error:  # surface any other failure (model/git) as a clean 502
                self._send_json(502, {"error": str(error)})

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", STUDIO_HTML.encode("utf-8"))
            elif self.path == "/healthz":
                self._send_json(200, {"status": "ok"})
            elif self.path == "/api/preview":
                if status_fn is None:
                    self._send_json(404, {"error": "preview controls are not enabled"})
                else:
                    self._send_json(200, status_fn())
            elif self.path == "/api/providers":
                if providers_fn is None:
                    self._send_json(404, {"error": "provider status is not enabled"})
                    return
                try:
                    self._send_json(200, providers_fn())
                except Exception as error:  # surface any other failure as a clean 502
                    self._send_json(502, {"error": str(error)})
            elif self.path == "/api/history":
                if history_fn is None:
                    self._send_json(404, {"error": "preview controls are not enabled"})
                else:
                    self._send_json(200, history_fn())
            elif self.path == "/api/solution-packs":
                self._send_json(200, {"packs": [p.to_dict() for p in pack_registry.packs]})
            elif self.path == "/api/ecosystem-packs":
                self._send_json(200, {"ecosystems": [e.to_dict() for e in eco_registry.list_packs()]})
            elif self.path == "/api/config":
                workspace_dir = os.path.abspath("scratch/apps")
                personal_dir = os.path.expanduser("~/Documents/Projects/GeneratedApps")
                current_env = os.environ.get("OMNISTACKAI_APP_OUT_DIR", "")
                self._send_json(200, {
                    "workspace_apps_dir": workspace_dir,
                    "personal_apps_dir": personal_dir,
                    "current_out_dir": current_env or workspace_dir,
                })
            elif self.path == "/api/ecosystem/auth":
                if get_ecosystem_auth_fn is None:
                    self._send_json(404, {"error": "ecosystem auth controls are not enabled"})
                else:
                    self._send_json(200, get_ecosystem_auth_fn())
            elif self.path == "/api/ecosystem/state":
                if get_ecosystem_state_fn is None:
                    self._send_json(404, {"error": "ecosystem state inspection not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_state_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/events":
                if get_ecosystem_events_fn is None:
                    self._send_json(404, {"error": "ecosystem event inspection not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_events_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/telemetry":
                if get_ecosystem_telemetry_fn is None:
                    self._send_json(404, {"error": "ecosystem telemetry inspection not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_telemetry_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/deployment":
                if get_ecosystem_deployment_fn is None:
                    self._send_json(404, {"error": "ecosystem deployment inspection not enabled"})
                    return
                try:
                    dep = get_ecosystem_deployment_fn()
                    if dep is None:
                        self._send_json(404, {"error": "no deployment manifest available"})
                    else:
                        self._send_json(200, dep)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/deployment/compose":
                if to_compose_yaml_fn is None:
                    self._send_json(404, {"error": "ecosystem compose export not enabled"})
                    return
                try:
                    yaml_text = to_compose_yaml_fn()
                    if yaml_text is None:
                        self._send_json(404, {"error": "no deployment manifest available"})
                    else:
                        self._send(200, "text/yaml; charset=utf-8", yaml_text.encode("utf-8"))
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/sync":
                if get_ecosystem_sync_fn is None:
                    self._send_json(404, {"error": "ecosystem sync inspection not enabled"})
                    return
                try:
                    sync_data = get_ecosystem_sync_fn()
                    if sync_data is None:
                        self._send_json(404, {"error": "no sync contract available"})
                    else:
                        self._send_json(200, sync_data)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path.startswith("/api/ecosystem/sync/pull"):
                if pull_sync_changes_fn is None:
                    self._send_json(404, {"error": "ecosystem sync pull not enabled"})
                    return
                qs = parse_qs(urlparse(self.path).query)
                surface_slug = qs.get("surface_slug", [""])[0]
                since_version = int(qs.get("since_version", ["0"])[0] or 0)
                if not surface_slug:
                    self._send_json(400, {"error": "surface_slug is required"})
                    return
                try:
                    res = pull_sync_changes_fn(surface_slug, since_version)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/cicd":
                if get_ecosystem_cicd_fn is None:
                    self._send_json(404, {"error": "ecosystem cicd inspection not enabled"})
                    return
                try:
                    cicd_data = get_ecosystem_cicd_fn()
                    if cicd_data is None:
                        self._send_json(404, {"error": "no cicd contract available"})
                    else:
                        self._send_json(200, cicd_data)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/cicd/yaml":
                if to_workflow_yaml_fn is None:
                    self._send_json(404, {"error": "ecosystem cicd yaml export not enabled"})
                    return
                try:
                    yaml_text = to_workflow_yaml_fn()
                    if yaml_text is None:
                        self._send_json(404, {"error": "no cicd contract available"})
                    else:
                        self._send(200, "text/yaml; charset=utf-8", yaml_text.encode("utf-8"))
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/verification":
                if get_ecosystem_verification_fn is None:
                    self._send_json(404, {"error": "ecosystem verification not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_verification_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/recovery":
                if get_ecosystem_recovery_fn is None:
                    self._send_json(404, {"error": "ecosystem recovery not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_recovery_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/capacity":
                if get_ecosystem_capacity_fn is None:
                    self._send_json(404, {"error": "ecosystem capacity not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_capacity_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/alerting":
                if get_ecosystem_alerting_fn is None:
                    self._send_json(404, {"error": "ecosystem alerting not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_alerting_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/sla":
                if get_ecosystem_sla_fn is None:
                    self._send_json(404, {"error": "ecosystem sla not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_sla_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/governance":
                if get_ecosystem_governance_fn is None:
                    self._send_json(404, {"error": "ecosystem governance not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_governance_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            elif self.path == "/api/ecosystem/docs":
                if get_ecosystem_docs_fn is None:
                    self._send_json(404, {"error": "ecosystem docs not enabled"})
                    return
                try:
                    self._send_json(200, get_ecosystem_docs_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            else:
                path_only = urlparse(self.path).path
                # --- Database Explorer GET routes (F-09 / R-507) ---
                # /api/workspaces/{id}/db/tables/{table}
                _db_table_m = re.fullmatch(
                    r"/api/workspaces/([^/]+)/db/tables/([^/]+)", path_only
                )
                if _db_table_m:
                    self._handle_workspace_db_table_rows(
                        unquote(_db_table_m.group(1)),
                        unquote(_db_table_m.group(2)),
                        urlparse(self.path).query,
                    )
                    return
                # /api/workspaces/{id}/db/tables
                ws_db_tables_id = self._workspace_id_for_suffix(path_only, "/db/tables")
                if ws_db_tables_id is not None:
                    self._handle_workspace_db_tables(ws_db_tables_id)
                    return
                # /api/workspaces/{id}/db/schema
                ws_db_schema_id = self._workspace_id_for_suffix(path_only, "/db/schema")
                if ws_db_schema_id is not None:
                    self._handle_workspace_db_schema(ws_db_schema_id)
                    return
                # --- existing workspace GET routes ---
                ws_files_id = self._workspace_id_for_suffix(path_only, "/files")
                if ws_files_id is not None:
                    self._handle_workspace_file_tree(ws_files_id)
                    return
                ws_file_id = self._workspace_id_for_suffix(path_only, "/file")
                if ws_file_id is not None:
                    self._handle_workspace_read_file(ws_file_id, urlparse(self.path).query)
                    return
                ws_turns_id = self._workspace_id_for_suffix(path_only, "/turns")
                if ws_turns_id is not None:
                    self._handle_workspace_turns(ws_turns_id)
                    return
                ws_problems_id = self._workspace_id_for_suffix(path_only, "/problems")
                if ws_problems_id is not None:
                    self._handle_workspace_get_problems(ws_problems_id)
                    return
                ws_export_id = self._workspace_id_for_suffix(path_only, "/export")
                if ws_export_id is not None:
                    self._handle_workspace_export(ws_export_id)
                    return
                ws_git_status_id = self._workspace_id_for_suffix(path_only, "/git/status")
                if ws_git_status_id is not None:
                    self._handle_workspace_git_status(ws_git_status_id)
                    return
                ws_preview_id = self._workspace_id_for_suffix(path_only, "/preview")
                if ws_preview_id is not None:
                    self._handle_workspace_preview_status(ws_preview_id)
                    return
                ws_logs_id = self._workspace_id_for_suffix(path_only, "/logs")
                if ws_logs_id is not None:
                    self._handle_workspace_logs(ws_logs_id, urlparse(self.path).query)
                    return
                ws_seo_audit_id = self._workspace_id_for_suffix(path_only, "/seo/audit")
                if ws_seo_audit_id is not None:
                    self._handle_workspace_seo_audit(ws_seo_audit_id)
                    return
                ws_state_id = self._workspace_id_for_suffix(path_only, "")
                if ws_state_id is not None:
                    self._handle_workspace_get_state(ws_state_id)
                    return

                files_build_id = self._build_id_for_suffix(path_only, "/files")
                if files_build_id is not None:
                    self._handle_file_tree(files_build_id)
                    return
                file_build_id = self._build_id_for_suffix(path_only, "/file")
                if file_build_id is not None:
                    self._handle_read_file(file_build_id, urlparse(self.path).query)
                    return
                turns_build_id = self._build_id_for_suffix(path_only, "/turns")
                if turns_build_id is not None:
                    self._handle_turns(turns_build_id)
                    return
                problems_build_id = self._build_id_for_suffix(path_only, "/problems")
                if problems_build_id is not None:
                    self._handle_get_problems(problems_build_id)
                    return
                self._send(404, "text/plain; charset=utf-8", b"not found")

        def do_POST(self) -> None:  # noqa: N802 (http.server API)
            if self.path == "/api/preview/switch":
                data = self._read_json_body()
                if data is None:
                    return
                if switch_surface_fn is None:
                    self._send_json(404, {"error": "preview controls are not enabled"})
                    return
                surface_slug = str(data.get("surface_slug", "")).strip()
                if not surface_slug:
                    self._send_json(400, {"error": "surface_slug is required"})
                    return
                try:
                    self._send_json(200, switch_surface_fn(surface_slug))
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/preview/stop":
                data = self._read_json_body()
                slug = str(data.get("surface_slug", "")).strip() if (data and isinstance(data, dict)) else None
                if stop_fn is None:
                    self._send_json(404, {"error": "preview controls are not enabled"})
                    return
                try:
                    res = stop_fn(slug) if slug else stop_fn()
                    self._send_json(200, res)
                except TypeError:
                    self._send_json(200, stop_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/preview/restart":
                data = self._read_json_body()
                slug = str(data.get("surface_slug", "")).strip() if (data and isinstance(data, dict)) else None
                if restart_fn is None:
                    self._send_json(404, {"error": "preview controls are not enabled"})
                    return
                try:
                    res = restart_fn(slug) if slug else restart_fn()
                    self._send_json(200, res)
                except TypeError:
                    self._send_json(200, restart_fn())
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/history/preview":
                data = self._read_json_body()
                if data is None:
                    return
                if preview_build_fn is None:
                    self._send_json(404, {"error": "preview controls are not enabled"})
                    return
                build_id = str(data.get("id", "")).strip()
                if not build_id:
                    self._send_json(400, {"error": "id is required"})
                    return
                surface_slug = str(data.get("surface_slug", "")).strip() if data.get("surface_slug") else None
                try:
                    if surface_slug:
                        try:
                            res = preview_build_fn(build_id, surface_slug)
                        except TypeError:
                            res = preview_build_fn(build_id)
                    else:
                        res = preview_build_fn(build_id)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/history/open":
                self._run_id_control(open_dir_fn)
                return
            if self.path == "/api/history/delete":
                self._run_id_control(delete_build_fn)
                return
            if self.path == "/api/ecosystem/events/dispatch":
                if dispatch_ecosystem_event_fn is None:
                    self._send_json(404, {"error": "ecosystem event dispatch not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    return
                event_type = str(data.get("event_type", "")).strip()
                entity_name = str(data.get("entity_name", "")).strip()
                entity_id = str(data.get("entity_id", "")).strip()
                if not event_type or not entity_name or not entity_id:
                    self._send_json(400, {"error": "event_type, entity_name, and entity_id are required"})
                    return
                try:
                    res = dispatch_ecosystem_event_fn(
                        event_type=event_type,
                        entity_name=entity_name,
                        entity_id=entity_id,
                        action=str(data.get("action", "update")).strip(),
                        data=data.get("data"),
                        source_surface=data.get("source_surface"),
                    )
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/solution-packs/recommend":
                data = self._read_json_body()
                if data is None:
                    return
                prompt = str(data.get("prompt", "")).strip()
                domain = str(data.get("domain", "")).strip()
                if not prompt and not domain:
                    self._send_json(400, {"error": "prompt or domain is required"})
                    return
                if not domain:
                    try:
                        proposal = propose_ecosystem(prompt)
                        domain = proposal.domain
                    except Exception:
                        domain = "custom-application"
                try:
                    recommendation = pack_registry.recommend(domain)
                    self._send_json(
                        200,
                        {
                            "domain": domain,
                            "recommendation": recommendation.to_dict(),
                            "packs": [p.to_dict() for p in pack_registry.packs],
                        },
                    )
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem-packs/recommend":
                data = self._read_json_body()
                if data is None:
                    return
                prompt = str(data.get("prompt", "")).strip()
                domain = str(data.get("domain", "")).strip()
                if not prompt and not domain:
                    self._send_json(400, {"error": "prompt or domain is required"})
                    return
                if not domain:
                    try:
                        proposal = propose_ecosystem(prompt)
                        domain = proposal.domain
                    except Exception:
                        domain = "custom-application"
                try:
                    recommendation = eco_registry.recommend(domain, prompt)
                    self._send_json(
                        200,
                        {
                            "domain": domain,
                            "recommendation": recommendation.to_dict(),
                            "ecosystems": [e.to_dict() for e in eco_registry.list_packs()],
                        },
                    )
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/sync/push":
                if push_sync_mutations_fn is None:
                    self._send_json(404, {"error": "ecosystem sync push not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    return
                surface_slug = str(data.get("surface_slug", "")).strip()
                mutations = data.get("mutations", [])
                if not surface_slug or not isinstance(mutations, list):
                    self._send_json(400, {"error": "surface_slug and mutations list are required"})
                    return
                try:
                    res = push_sync_mutations_fn(surface_slug, mutations)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/sync/simulate":
                if simulate_sync_conflict_fn is None:
                    self._send_json(404, {"error": "ecosystem sync simulate not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    return
                entity_name = str(data.get("entity_name", "")).strip()
                record_id = str(data.get("record_id", "")).strip()
                local_surface = str(data.get("local_surface", "")).strip()
                remote_surface = str(data.get("remote_surface", "")).strip()
                local_updates = data.get("local_updates", {})
                remote_updates = data.get("remote_updates", {})
                strategy = str(data.get("strategy", "field_merge")).strip()
                if not entity_name or not record_id or not local_surface or not remote_surface:
                    self._send_json(400, {"error": "entity_name, record_id, local_surface, and remote_surface are required"})
                    return
                try:
                    res = simulate_sync_conflict_fn(
                        entity_name=entity_name,
                        record_id=record_id,
                        local_surface=local_surface,
                        remote_surface=remote_surface,
                        local_updates=local_updates,
                        remote_updates=remote_updates,
                        strategy=strategy,
                    )
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/cicd/simulate":
                if simulate_cicd_run_fn is None:
                    self._send_json(404, {"error": "ecosystem cicd simulate not enabled"})
                    return
                data = self._read_json_body()
                trigger = "push"
                if data and isinstance(data, dict):
                    trigger = str(data.get("trigger", "push")).strip() or "push"
                try:
                    res = simulate_cicd_run_fn(trigger)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/verification/simulate":
                if simulate_ecosystem_verification_fn is None:
                    self._send_json(404, {"error": "ecosystem verification simulate not enabled"})
                    return
                self._drain_body()
                try:
                    res = simulate_ecosystem_verification_fn()
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/recovery/simulate":
                if simulate_ecosystem_recovery_fn is None:
                    self._send_json(404, {"error": "ecosystem recovery simulate not enabled"})
                    return
                self._drain_body()
                try:
                    res = simulate_ecosystem_recovery_fn()
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/capacity/simulate":
                if simulate_ecosystem_capacity_fn is None:
                    self._send_json(404, {"error": "ecosystem capacity simulate not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    data = {}
                try:
                    res = simulate_ecosystem_capacity_fn(data)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/alerting/simulate":
                if simulate_ecosystem_alerting_fn is None:
                    self._send_json(404, {"error": "ecosystem alerting simulate not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    data = {}
                try:
                    res = simulate_ecosystem_alerting_fn(data)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/sla/simulate":
                if simulate_ecosystem_sla_fn is None:
                    self._send_json(404, {"error": "ecosystem sla simulate not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    data = {}
                try:
                    res = simulate_ecosystem_sla_fn(data)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/governance/simulate":
                if simulate_ecosystem_governance_fn is None:
                    self._send_json(404, {"error": "ecosystem governance simulate not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    data = {}
                try:
                    res = simulate_ecosystem_governance_fn(data)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            if self.path == "/api/ecosystem/docs/export":
                if export_ecosystem_docs_fn is None:
                    self._send_json(404, {"error": "ecosystem docs export not enabled"})
                    return
                data = self._read_json_body()
                if data is None:
                    data = {}
                try:
                    res = export_ecosystem_docs_fn(data)
                    self._send_json(200, res)
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            path_only = urlparse(self.path).path
            # --- Database Explorer POST routes (F-09 / R-507) ---
            ws_db_query_id = self._workspace_id_for_suffix(path_only, "/db/query")
            if ws_db_query_id is not None:
                self._handle_workspace_db_query(ws_db_query_id)
                return
            # --- existing workspace POST routes ---
            ws_cancel_id = self._workspace_id_for_suffix(path_only, "/cancel")
            if ws_cancel_id is not None:
                self._handle_workspace_cancel(ws_cancel_id)
                return
            ws_stream_id = self._workspace_id_for_suffix(path_only, "/build/stream")
            if ws_stream_id is not None:
                self._handle_workspace_build_stream(ws_stream_id)
                return
            ws_build_id = self._workspace_id_for_suffix(path_only, "/build")
            if ws_build_id is not None:
                self._handle_workspace_build(ws_build_id)
                return
            ws_edit_id = self._workspace_id_for_suffix(path_only, "/edit")
            if ws_edit_id is not None:
                self._handle_workspace_edit(ws_edit_id)
                return
            ws_preview_stop_id = self._workspace_id_for_suffix(path_only, "/preview/stop")
            if ws_preview_stop_id is not None:
                self._handle_workspace_preview_stop(ws_preview_stop_id)
                return
            ws_preview_id = self._workspace_id_for_suffix(path_only, "/preview")
            if ws_preview_id is not None:
                self._handle_workspace_preview(ws_preview_id)
                return
            ws_problems_id = self._workspace_id_for_suffix(path_only, "/problems")
            if ws_problems_id is not None:
                self._handle_workspace_problems_check(ws_problems_id)
                return
            ws_git_push_id = self._workspace_id_for_suffix(path_only, "/git/push")
            if ws_git_push_id is not None:
                self._handle_workspace_git_push(ws_git_push_id)
                return
            ws_seo_audit_id = self._workspace_id_for_suffix(path_only, "/seo/audit")
            if ws_seo_audit_id is not None:
                self._handle_workspace_seo_audit(ws_seo_audit_id)
                return
            ws_seo_suggest_id = self._workspace_id_for_suffix(path_only, "/seo/suggest")
            if ws_seo_suggest_id is not None:
                self._handle_workspace_seo_suggest(ws_seo_suggest_id)
                return
            ws_seo_page_id = self._workspace_id_for_suffix(path_only, "/seo/page")
            if ws_seo_page_id is not None:
                self._handle_workspace_seo_page(ws_seo_page_id)
                return

            if self.path == "/api/build/stream":
                self._handle_build_stream()
                return
            if self.path != "/api/build":
                edit_build_id = self._build_id_for_suffix(self.path, "/edit")
                if edit_build_id is not None:
                    self._handle_edit(edit_build_id)
                    return
                problems_build_id = self._build_id_for_suffix(self.path, "/problems")
                if problems_build_id is not None:
                    self._handle_check_problems(problems_build_id)
                    return
                self._send_json(404, {"error": "not found"})
                return
            data = self._read_json_body()
            if data is None:
                return
            prompt = str(data.get("prompt", "")).strip()
            if not prompt:
                self._send_json(400, {"error": "prompt is required"})
                return

            options: dict = {}
            for key in (
                "pack_id",
                "pack_version",
                "custom_name",
                "custom_description",
                "ecosystem_id",
                "ecosystem_version",
                "surface_slug",
                "output_dir",
                "folder_name",
                "target_dir",
            ):
                if key in data and data[key] is not None and str(data[key]).strip():
                    options[key] = str(data[key]).strip()
            if "configuration_changes" in data and isinstance(data["configuration_changes"], list):
                options["configuration_changes"] = data["configuration_changes"]
            if "ai_delta_prompt" in data and data["ai_delta_prompt"] is not None and str(data["ai_delta_prompt"]).strip():
                options["ai_delta_prompt"] = str(data["ai_delta_prompt"]).strip()
            if "ai_features" in data and isinstance(data["ai_features"], list):
                options["ai_features"] = [str(f).strip() for f in data["ai_features"] if str(f).strip()]
            if "hybrid_ui" in data:
                options["hybrid_ui"] = bool(data["hybrid_ui"])

            try:
                if options:
                    try:
                        result = build_fn(prompt, **options)
                    except TypeError:
                        result = build_fn(prompt)
                else:
                    result = build_fn(prompt)
            except Exception as error:  # surface any build failure as a clean 502
                self._send_json(502, {"error": str(error)})
                return
            self._send_json(200, result)

        def do_PUT(self) -> None:  # noqa: N802 (http.server API)
            path_only = urlparse(self.path).path
            ws_seo_page_id = self._workspace_id_for_suffix(path_only, "/seo/page")
            if ws_seo_page_id is not None:
                self._handle_workspace_seo_page(ws_seo_page_id)
                return
            self._send_json(404, {"error": "not found"})

        def do_DELETE(self) -> None:  # noqa: N802 (http.server API)
            path_only = urlparse(self.path).path
            ws_logs_id = self._workspace_id_for_suffix(path_only, "/logs")
            if ws_logs_id is not None:
                self._handle_workspace_logs_clear(ws_logs_id, urlparse(self.path).query)
                return
            ws_id = self._workspace_id_for_suffix(path_only, "")
            if ws_id is not None:
                if workspace_store is None:
                    self._send_json(404, {"error": "workspaces are not enabled"})
                    return
                try:
                    workspace_store.purge(ws_id)
                    self._send_json(200, {"status": "purged", "id": ws_id})
                except Exception as error:
                    self._send_json(502, {"error": str(error)})
                return
            self._send_json(404, {"error": "not found"})

    return StudioHandler


def create_studio_server(
    build_fn: BuildFn,
    *,
    host: str = "127.0.0.1",
    port: int = 4173,
    status_fn: ControlFn | None = None,
    stop_fn: ControlFn | None = None,
    restart_fn: ControlFn | None = None,
    history_fn: ControlFn | None = None,
    preview_build_fn: PreviewBuildFn | None = None,
    open_dir_fn: PreviewBuildFn | None = None,
    delete_build_fn: PreviewBuildFn | None = None,
    file_tree_fn: FileTreeFn | None = None,
    read_file_fn: ReadFileFn | None = None,
    edit_fn: EditFn | None = None,
    turns_fn: FileTreeFn | None = None,
    problems_check_fn: ProblemsFn | None = None,
    problems_get_fn: ProblemsFn | None = None,
    providers_fn: ProvidersFn | None = None,
    build_stream_fn: BuildStreamFn | None = None,
    solution_pack_registry: SolutionPackRegistry | None = None,
    ecosystem_pack_registry: EcosystemPackRegistry | None = None,
    switch_surface_fn: PreviewBuildFn | None = None,
    get_ecosystem_auth_fn: ControlFn | None = None,
    get_ecosystem_state_fn: ControlFn | None = None,
    get_ecosystem_events_fn: ControlFn | None = None,
    dispatch_ecosystem_event_fn: Callable[..., dict] | None = None,
    get_ecosystem_telemetry_fn: ControlFn | None = None,
    get_ecosystem_deployment_fn: ControlFn | None = None,
    to_compose_yaml_fn: Callable[[], str | None] | None = None,
    get_ecosystem_sync_fn: ControlFn | None = None,
    push_sync_mutations_fn: Callable[[str, list[dict]], dict] | None = None,
    pull_sync_changes_fn: Callable[[str, int], dict] | None = None,
    simulate_sync_conflict_fn: Callable[..., dict] | None = None,
    get_ecosystem_cicd_fn: ControlFn | None = None,
    to_workflow_yaml_fn: Callable[[], str | None] | None = None,
    simulate_cicd_run_fn: Callable[[str], dict] | None = None,
    get_ecosystem_verification_fn: ControlFn | None = None,
    simulate_ecosystem_verification_fn: ControlFn | None = None,
    get_ecosystem_recovery_fn: ControlFn | None = None,
    simulate_ecosystem_recovery_fn: ControlFn | None = None,
    get_ecosystem_capacity_fn: ControlFn | None = None,
    simulate_ecosystem_capacity_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_alerting_fn: ControlFn | None = None,
    simulate_ecosystem_alerting_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_sla_fn: ControlFn | None = None,
    simulate_ecosystem_sla_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_governance_fn: ControlFn | None = None,
    simulate_ecosystem_governance_fn: Callable[..., dict] | ControlFn | None = None,
    get_ecosystem_docs_fn: ControlFn | None = None,
    export_ecosystem_docs_fn: Callable[..., dict] | ControlFn | None = None,
    workspace_store: StudioWorkspaceStore | None = None,
    workspace_build_fn: WorkspaceBuildFn | None = None,
    workspace_build_stream_fn: WorkspaceBuildStreamFn | None = None,
    workspace_edit_fn: EditFn | None = None,
    workspace_preview_fn: PreviewBuildFn | None = None,
    workspace_preview_status_fn: PreviewBuildFn | None = None,
    workspace_preview_stop_fn: PreviewBuildFn | None = None,
    workspace_problems_check_fn: ProblemsFn | None = None,
    workspace_problems_get_fn: ProblemsFn | None = None,
    workspace_cancel_fn: Callable[[str], dict] | None = None,
    workspace_logs_fn: Callable[..., dict] | None = None,
    workspace_logs_stream_fn: Callable[..., AsyncIterator[dict]] | None = None,
    workspace_logs_clear_fn: Callable[..., dict] | None = None,
) -> ThreadingHTTPServer:
    """Create (but do not start) a studio server bound to ``host``/``port``.

    Pass ``port=0`` for an ephemeral port (used by tests). Call ``serve_forever()`` to run.
    The preview control and history handlers are optional; when unset, ``GET /api/preview``,
    ``POST /api/preview/stop|restart``, ``POST /api/preview/switch``, ``GET /api/history``,
    ``POST /api/history/preview``, ``POST /api/history/open``, and ``POST /api/history/delete``
    return 404 (build-only mode).
    ``history_fn`` and ``delete_build_fn`` may be wired in build-only mode (list/remove recorded
    builds); ``preview_build_fn`` (re-preview) and ``open_dir_fn`` (open the recorded repo folder)
    are wired only in trusted-local preview mode. ``file_tree_fn`` (``GET /api/build/{id}/files``),
    ``read_file_fn`` (``GET /api/build/{id}/file?path=...``, R-467), ``edit_fn``
    (``POST /api/build/{id}/edit``), and ``turns_fn`` (``GET /api/build/{id}/turns``, R-468) may also be
    wired in build-only mode -- inspecting a build's files or applying a follow-up edit needs no toolchain
    or running preview, only git and a model. ``problems_check_fn``
    (``POST /api/build/{id}/problems``, R-480, triggers a fresh `tsc` type-check) and
    ``problems_get_fn`` (``GET /api/build/{id}/problems``, the last stored report) may also be wired in
    build-only mode -- the check itself needs the build's own installed `node_modules`/`tsc` (from a prior
    live-preview install), but not a *currently running* preview. ``providers_fn``
    (``GET /api/providers``, R-482, a zero-arg status view of the model fabric plus which provider would
    actually run the next real call) may also be wired in build-only mode -- it needs only environment
    variables and one optional, lightweight local health ping, never a toolchain or running preview.
    ``build_stream_fn`` (``POST /api/build/stream``, R-484) streams real incremental build progress via
    Server-Sent Events for a plain-prompt, non-``hybrid_ui`` build -- other build kinds are rejected with
    a plain 400 before any SSE framing begins, proxied through unchanged by every layer above this one.
    """
    return ThreadingHTTPServer(
        (host, port),
        _make_handler(
            build_fn,
            status_fn,
            stop_fn,
            restart_fn,
            history_fn,
            preview_build_fn,
            open_dir_fn,
            delete_build_fn,
            file_tree_fn=file_tree_fn,
            read_file_fn=read_file_fn,
            edit_fn=edit_fn,
            turns_fn=turns_fn,
            problems_check_fn=problems_check_fn,
            problems_get_fn=problems_get_fn,
            providers_fn=providers_fn,
            build_stream_fn=build_stream_fn,
            registry=solution_pack_registry,
            ecosystem_registry=ecosystem_pack_registry,
            switch_surface_fn=switch_surface_fn,
            get_ecosystem_auth_fn=get_ecosystem_auth_fn,
            get_ecosystem_state_fn=get_ecosystem_state_fn,
            get_ecosystem_events_fn=get_ecosystem_events_fn,
            dispatch_ecosystem_event_fn=dispatch_ecosystem_event_fn,
            get_ecosystem_telemetry_fn=get_ecosystem_telemetry_fn,
            get_ecosystem_deployment_fn=get_ecosystem_deployment_fn,
            to_compose_yaml_fn=to_compose_yaml_fn,
            get_ecosystem_sync_fn=get_ecosystem_sync_fn,
            push_sync_mutations_fn=push_sync_mutations_fn,
            pull_sync_changes_fn=pull_sync_changes_fn,
            simulate_sync_conflict_fn=simulate_sync_conflict_fn,
            get_ecosystem_cicd_fn=get_ecosystem_cicd_fn,
            to_workflow_yaml_fn=to_workflow_yaml_fn,
            simulate_cicd_run_fn=simulate_cicd_run_fn,
            get_ecosystem_verification_fn=get_ecosystem_verification_fn,
            simulate_ecosystem_verification_fn=simulate_ecosystem_verification_fn,
            get_ecosystem_recovery_fn=get_ecosystem_recovery_fn,
            simulate_ecosystem_recovery_fn=simulate_ecosystem_recovery_fn,
            get_ecosystem_capacity_fn=get_ecosystem_capacity_fn,
            simulate_ecosystem_capacity_fn=simulate_ecosystem_capacity_fn,
            get_ecosystem_alerting_fn=get_ecosystem_alerting_fn,
            simulate_ecosystem_alerting_fn=simulate_ecosystem_alerting_fn,
            get_ecosystem_sla_fn=get_ecosystem_sla_fn,
            simulate_ecosystem_sla_fn=simulate_ecosystem_sla_fn,
            get_ecosystem_governance_fn=get_ecosystem_governance_fn,
            simulate_ecosystem_governance_fn=simulate_ecosystem_governance_fn,
            get_ecosystem_docs_fn=get_ecosystem_docs_fn,
            export_ecosystem_docs_fn=export_ecosystem_docs_fn,
            workspace_store=workspace_store,
            workspace_build_fn=workspace_build_fn,
            workspace_build_stream_fn=workspace_build_stream_fn,
            workspace_edit_fn=workspace_edit_fn,
            workspace_preview_fn=workspace_preview_fn,
            workspace_preview_status_fn=workspace_preview_status_fn,
            workspace_preview_stop_fn=workspace_preview_stop_fn,
            workspace_problems_check_fn=workspace_problems_check_fn,
            workspace_problems_get_fn=workspace_problems_get_fn,
            workspace_cancel_fn=workspace_cancel_fn,
            workspace_logs_fn=workspace_logs_fn,
            workspace_logs_stream_fn=workspace_logs_stream_fn,
            workspace_logs_clear_fn=workspace_logs_clear_fn,
        ),
    )

