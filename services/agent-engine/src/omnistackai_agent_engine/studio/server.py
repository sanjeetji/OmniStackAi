"""A dependency-free (stdlib ``http.server``) web server for the OmniStackAI Studio.

Serves the chat-to-create page at ``GET /`` and handles ``POST /api/build``. The build
function is INJECTED (``build_fn(prompt) -> dict``) so the HTTP layer is fully testable
offline against an in-memory stub; the live local-Ollama wiring lives in ``live_serve``.
No web framework, no external dependencies.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from ..intake.ecosystem import propose_ecosystem
from ..solution_packs import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    EcosystemPackRegistry,
    SolutionPackRegistry,
)
from .page import STUDIO_HTML

BuildFn = Callable[..., dict]
ControlFn = Callable[..., dict]
PreviewBuildFn = Callable[..., dict]

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
            elif self.path == "/api/history":
                if history_fn is None:
                    self._send_json(404, {"error": "preview controls are not enabled"})
                else:
                    self._send_json(200, history_fn())
            elif self.path == "/api/solution-packs":
                self._send_json(200, {"packs": [p.to_dict() for p in pack_registry.packs]})
            elif self.path == "/api/ecosystem-packs":
                self._send_json(200, {"ecosystems": [e.to_dict() for e in eco_registry.list_packs()]})
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
            else:
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
            if self.path != "/api/build":
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
            ):
                if key in data and data[key] is not None and str(data[key]).strip():
                    options[key] = str(data[key]).strip()
            if "configuration_changes" in data and isinstance(data["configuration_changes"], list):
                options["configuration_changes"] = data["configuration_changes"]
            if "ai_delta_prompt" in data and data["ai_delta_prompt"] is not None and str(data["ai_delta_prompt"]).strip():
                options["ai_delta_prompt"] = str(data["ai_delta_prompt"]).strip()
            if "ai_features" in data and isinstance(data["ai_features"], list):
                options["ai_features"] = [str(f).strip() for f in data["ai_features"] if str(f).strip()]

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
) -> ThreadingHTTPServer:
    """Create (but do not start) a studio server bound to ``host``/``port``.

    Pass ``port=0`` for an ephemeral port (used by tests). Call ``serve_forever()`` to run.
    The preview control and history handlers are optional; when unset, ``GET /api/preview``,
    ``POST /api/preview/stop|restart``, ``POST /api/preview/switch``, ``GET /api/history``,
    ``POST /api/history/preview``, ``POST /api/history/open``, and ``POST /api/history/delete``
    return 404 (build-only mode).
    ``history_fn`` and ``delete_build_fn`` may be wired in build-only mode (list/remove recorded
    builds); ``preview_build_fn`` (re-preview) and ``open_dir_fn`` (open the recorded repo folder)
    are wired only in trusted-local preview mode.
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
        ),
    )

