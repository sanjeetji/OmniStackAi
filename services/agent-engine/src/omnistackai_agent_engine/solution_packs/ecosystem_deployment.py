"""Ecosystem Multi-Surface Export, Deployment Manifest, and Live Gateway Orchestration (R-450).

Provides canonical deployment manifests, docker-compose generation, and in-process
reverse-proxy live gateway orchestration for multi-surface business ecosystems
using Python 3.13 stdlib only (0 external dependencies, 100% offline).
"""

from __future__ import annotations

import http.server
import json
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


# ---------------------------------------------------------------------------
# Dataclasses — Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GatewayRoute:
    """A reverse-proxy routing rule mapping path prefixes to ecosystem surfaces."""

    route_id: str
    path_prefix: str
    target_surface: str
    target_port: int
    strip_prefix: bool = False
    auth_required: bool = False
    required_role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "path_prefix": self.path_prefix,
            "target_surface": self.target_surface,
            "target_port": self.target_port,
            "strip_prefix": self.strip_prefix,
            "auth_required": self.auth_required,
            "required_role": self.required_role,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GatewayRoute:
        return cls(
            route_id=str(data.get("route_id", "")),
            path_prefix=str(data.get("path_prefix", "/")),
            target_surface=str(data.get("target_surface", "")),
            target_port=int(data.get("target_port", 3000)),
            strip_prefix=bool(data.get("strip_prefix", False)),
            auth_required=bool(data.get("auth_required", False)),
            required_role=data.get("required_role"),
        )


def match_gateway_route(routes: Sequence[GatewayRoute], path: str) -> GatewayRoute | None:
    """Find the best-matching GatewayRoute for a request path using longest prefix match."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    best_match: GatewayRoute | None = None
    best_len = -1

    for r in routes:
        prefix = r.path_prefix
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"

        if prefix == "/" or prefix == "":
            if best_len < 1:
                best_match = r
                best_len = 1
        elif normalized_path == prefix or normalized_path.startswith(prefix if prefix.endswith("/") else f"{prefix}/"):
            if len(prefix) > best_len:
                best_match = r
                best_len = len(prefix)

    return best_match


@dataclass(frozen=True, slots=True)
class SurfaceDeploymentSpec:
    """Deployment configuration for a single surface in the ecosystem."""

    surface_slug: str
    surface_kind: str
    app_name: str
    runtime_target: str
    container_port: int
    host_port: int
    env_vars: dict[str, str] = field(default_factory=dict)
    health_path: str = "/api/health"
    depends_on: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "surface_kind": self.surface_kind,
            "app_name": self.app_name,
            "runtime_target": self.runtime_target,
            "container_port": self.container_port,
            "host_port": self.host_port,
            "env_vars": dict(self.env_vars),
            "health_path": self.health_path,
            "depends_on": list(self.depends_on),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SurfaceDeploymentSpec:
        return cls(
            surface_slug=str(data.get("surface_slug", "")),
            surface_kind=str(data.get("surface_kind", "")),
            app_name=str(data.get("app_name", "")),
            runtime_target=str(data.get("runtime_target", "nextjs-web")),
            container_port=int(data.get("container_port", 3000)),
            host_port=int(data.get("host_port", 3000)),
            env_vars=dict(data.get("env_vars", {})),
            health_path=str(data.get("health_path", "/api/health")),
            depends_on=tuple(str(x) for x in data.get("depends_on", ())),
        )


def generate_docker_compose(manifest: EcosystemDeploymentManifest) -> str:
    """Deterministically generate valid Docker Compose YAML for the ecosystem."""
    lines: list[str] = [
        f"name: {manifest.ecosystem_id}",
        "",
        "services:",
    ]

    # Database service (PostgreSQL with pgvector)
    db = manifest.database_spec
    db_name = db.get("database_name", "app_db")
    db_port = db.get("default_port", 5432)
    lines.extend([
        "  postgres:",
        "    image: postgres:16-alpine",
        "    restart: unless-stopped",
        "    environment:",
        f"      POSTGRES_DB: {db_name}",
        "      POSTGRES_USER: omnistackai",
        "      POSTGRES_PASSWORD: omnistackai_secret",
        "    ports:",
        f"      - \"{db_port}:5432\"",
        "    volumes:",
        f"      - {manifest.ecosystem_id}-db-data:/var/lib/postgresql/data",
        "    healthcheck:",
        "      test: [\"CMD-SHELL\", \"pg_isready -U omnistackai -d ${POSTGRES_DB:-" + db_name + "}\"]",
        "      interval: 5s",
        "      timeout: 5s",
        "      retries: 5",
        "    networks:",
        f"      - {manifest.ecosystem_id}-net",
        "",
    ])

    # Application surface services
    for s in manifest.surfaces:
        lines.append(f"  {s.surface_slug}:")
        if "nextjs" in s.runtime_target:
            lines.append("    image: node:20-alpine")
        elif "python" in s.runtime_target:
            lines.append("    image: python:3.13-slim")
        elif "go" in s.runtime_target:
            lines.append("    image: golang:1.24-alpine")
        else:
            lines.append("    image: alpine:latest")

        lines.append("    restart: unless-stopped")

        # Dependencies
        deps = list(s.depends_on)
        if "backend" in s.runtime_target and "postgres" not in deps:
            deps.append("postgres")
        if deps:
            lines.append("    depends_on:")
            for dep in deps:
                if dep == "postgres":
                    lines.append("      postgres:")
                    lines.append("        condition: service_healthy")
                else:
                    lines.append(f"      - {dep}")

        # Environment variables
        lines.append("    environment:")
        lines.append(f"      PORT: \"{s.container_port}\"")
        for k, v in sorted(s.env_vars.items()):
            if k != "PORT":
                lines.append(f"      {k}: \"{v}\"")

        # Ports
        lines.append("    ports:")
        lines.append(f"      - \"{s.host_port}:{s.container_port}\"")

        # Healthcheck
        lines.append("    healthcheck:")
        lines.append(f"      test: [\"CMD\", \"wget\", \"--quiet\", \"--spider\", \"http://127.0.0.1:{s.container_port}{s.health_path}\"]")
        lines.append("      interval: 10s")
        lines.append("      timeout: 5s")
        lines.append("      retries: 3")

        lines.append("    networks:")
        lines.append(f"      - {manifest.ecosystem_id}-net")
        lines.append("")

    # Networks and Volumes
    lines.extend([
        "networks:",
        f"  {manifest.ecosystem_id}-net:",
        "    driver: bridge",
        "",
        "volumes:",
        f"  {manifest.ecosystem_id}-db-data:",
        "",
    ])

    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class EcosystemDeploymentManifest:
    """Canonical multi-surface deployment topology and reverse-proxy routing manifest."""

    ecosystem_id: str
    version: str
    gateway_port: int
    surfaces: tuple[SurfaceDeploymentSpec, ...]
    gateway_routes: tuple[GatewayRoute, ...]
    schema_version: str = "1.0"
    database_spec: dict[str, Any] = field(
        default_factory=lambda: {
            "engine": "postgresql",
            "version": "16-alpine",
            "database_name": "app_db",
            "default_port": 5432,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "gateway_port": self.gateway_port,
            "surfaces": [s.to_dict() for s in self.surfaces],
            "gateway_routes": [r.to_dict() for r in self.gateway_routes],
            "database_spec": dict(self.database_spec),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_compose_yaml(self) -> str:
        return generate_docker_compose(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemDeploymentManifest:
        surfaces = tuple(
            SurfaceDeploymentSpec.from_dict(s)
            for s in data.get("surfaces", ())
        )
        routes = tuple(
            GatewayRoute.from_dict(r)
            for r in data.get("gateway_routes", ())
        )
        return cls(
            schema_version=str(data.get("schema_version", "1.0")),
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            gateway_port=int(data.get("gateway_port", 8080)),
            surfaces=surfaces,
            gateway_routes=routes,
            database_spec=dict(data.get("database_spec", {})),
        )


# ---------------------------------------------------------------------------
# Deterministic Synthesis
# ---------------------------------------------------------------------------


def synthesize_ecosystem_deployment(
    ecosystem_id: str,
    surfaces: Sequence[Any],
    auth_contract: Any = None,
    state_binding: Any = None,
    base_port: int = 3000,
) -> EcosystemDeploymentManifest:
    """Derive canonical deployment specs and gateway routing rules for an ecosystem."""
    db_name = f"{ecosystem_id.replace('-', '_')}_db"
    db_spec = {
        "engine": "postgresql",
        "version": "16-alpine",
        "database_name": db_name,
        "default_port": 5432,
        "connection_url": f"postgresql://omnistackai:omnistackai_secret@postgres:5432/{db_name}",
    }

    deployment_surfaces: list[SurfaceDeploymentSpec] = []
    routes: list[GatewayRoute] = []

    def _surface_val(s: Any, key: str, default: Any = "") -> Any:
        if isinstance(s, dict):
            return s.get(key, default)
        return getattr(s, key, default)

    # Map surface slugs to assigned host ports
    slug_to_port: dict[str, int] = {}
    for idx, s in enumerate(surfaces):
        s_slug = _surface_val(s, "slug", f"surface-{idx}")
        host_port = base_port + idx
        slug_to_port[s_slug] = host_port

    # Identify primary/public surface for root route
    root_surface_slug = _surface_val(surfaces[0], "slug", "") if surfaces else ""
    for s in surfaces:
        kind = _surface_val(s, "surface_kind", "")
        if kind in ("public_web", "customer_pwa", "customer_web"):
            root_surface_slug = _surface_val(s, "slug", "")
            break

    for idx, s in enumerate(surfaces):
        slug = _surface_val(s, "slug", f"surface-{idx}")
        host_port = slug_to_port[slug]
        kind = _surface_val(s, "surface_kind", "web")
        app_name = _surface_val(s, "app_name", slug)

        # Detect primary target
        targets = _surface_val(s, "targets", ()) or _surface_val(s, "verify_targets", ())
        runtime_target = "nextjs-web"
        container_port = 3000
        health_path = "/api/health"
        depends_on: list[str] = []

        if any("backend" in t for t in targets):
            if any("go" in t for t in targets):
                runtime_target = "backend-go"
                container_port = 8080
            else:
                runtime_target = "backend-python"
                container_port = 8000
            health_path = "/healthz"
            depends_on.append("postgres")

        # Environment variables
        env_vars: dict[str, str] = {
            "NODE_ENV": "production",
            "PORT": str(container_port),
            "ECOSYSTEM_ID": ecosystem_id,
            "SURFACE_SLUG": slug,
        }
        if depends_on:
            env_vars["DATABASE_URL"] = db_spec["connection_url"]

        # Incorporate state binding environment if provided
        if state_binding is not None and hasattr(state_binding, "surface_bindings"):
            for sb in state_binding.surface_bindings:
                if sb.surface_slug == slug:
                    env_vars.update(sb.env_vars)

        spec = SurfaceDeploymentSpec(
            surface_slug=slug,
            surface_kind=kind,
            app_name=app_name,
            runtime_target=runtime_target,
            container_port=container_port,
            host_port=host_port,
            env_vars=env_vars,
            health_path=health_path,
            depends_on=tuple(depends_on),
        )
        deployment_surfaces.append(spec)

        # Generate Gateway Routes
        if slug == root_surface_slug:
            routes.append(
                GatewayRoute(
                    route_id=f"route-{slug}-root",
                    path_prefix="/",
                    target_surface=slug,
                    target_port=host_port,
                    strip_prefix=False,
                )
            )
        else:
            path_prefix = f"/{slug}"
            routes.append(
                GatewayRoute(
                    route_id=f"route-{slug}",
                    path_prefix=path_prefix,
                    target_surface=slug,
                    target_port=host_port,
                    strip_prefix=False,
                )
            )

    return EcosystemDeploymentManifest(
        ecosystem_id=ecosystem_id,
        version="1.0.0",
        gateway_port=8080,
        surfaces=tuple(deployment_surfaces),
        gateway_routes=tuple(routes),
        database_spec=db_spec,
    )


# ---------------------------------------------------------------------------
# In-Process Live Gateway Orchestration (Loopback Reverse Proxy)
# ---------------------------------------------------------------------------


class _GatewayHandler(http.server.BaseHTTPRequestHandler):
    """Internal HTTP handler for EcosystemLiveGateway."""

    routes: tuple[GatewayRoute, ...] = ()
    timeout: float = 3.0

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard output in testing/preview
        pass

    def _proxy(self, method: str) -> None:
        route = match_gateway_route(self.routes, self.path)
        if route is None:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-OmniStack-Gateway", "1.0")
            self.end_headers()
            self.wfile.write(b'{"error": "No matching gateway route found for path"}\n')
            return

        # Build target URL
        forward_path = self.path
        if route.strip_prefix and route.path_prefix != "/":
            if forward_path.startswith(route.path_prefix):
                forward_path = forward_path[len(route.path_prefix):]
                if not forward_path.startswith("/"):
                    forward_path = f"/{forward_path}"

        target_url = f"http://127.0.0.1:{route.target_port}{forward_path}"

        # Read incoming body
        body: bytes | None = None
        content_length = self.headers.get("Content-Length")
        if content_length:
            try:
                body = self.rfile.read(int(content_length))
            except Exception:
                body = None

        # Prepare request headers
        req_headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}
        req_headers["X-OmniStack-Gateway"] = "1.0"
        req_headers["X-Forwarded-For"] = self.client_address[0]
        req_headers["X-Forwarded-Proto"] = "http"

        req = urllib.request.Request(
            url=target_url,
            data=body,
            headers=req_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "content-length"):
                        self.send_header(k, v)
                resp_body = resp.read()
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as exc:
            self.send_response(exc.code)
            for k, v in exc.headers.items():
                if k.lower() not in ("transfer-encoding", "content-length"):
                    self.send_header(k, v)
            resp_body = exc.read()
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-OmniStack-Gateway", "1.0")
            self.end_headers()
            payload = json.dumps({
                "error": f"Gateway target unavailable at port {route.target_port}",
                "detail": str(exc),
            }).encode("utf-8")
            self.wfile.write(payload)

    def do_GET(self) -> None:
        self._proxy("GET")

    def do_POST(self) -> None:
        self._proxy("POST")

    def do_PUT(self) -> None:
        self._proxy("PUT")

    def do_DELETE(self) -> None:
        self._proxy("DELETE")

    def do_PATCH(self) -> None:
        self._proxy("PATCH")


class EcosystemLiveGateway:
    """Thread-safe, lightweight loopback reverse proxy for multi-surface ecosystem preview."""

    def __init__(self, manifest: EcosystemDeploymentManifest) -> None:
        self._manifest = manifest
        self._server: http.server.HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._port: int = manifest.gateway_port
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._server is not None

    @property
    def port(self) -> int:
        with self._lock:
            return self._port

    @property
    def url(self) -> str:
        with self._lock:
            return f"http://127.0.0.1:{self._port}"

    def start(self) -> None:
        with self._lock:
            if self._server is not None:
                return

            class _BoundHandler(_GatewayHandler):
                routes = self._manifest.gateway_routes

            # Bind to loopback; port 0 allows kernel ephemeral port allocation for tests
            server = http.server.HTTPServer(("127.0.0.1", self._port), _BoundHandler)
            self._port = server.server_address[1]
            self._server = server

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._thread = thread

    def stop(self) -> None:
        with self._lock:
            if self._server is None:
                return
            server = self._server
            self._server = None
            self._thread = None
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
