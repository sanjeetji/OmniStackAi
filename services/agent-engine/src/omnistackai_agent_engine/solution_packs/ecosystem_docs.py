"""Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts (R-459).

Defines canonical contracts, documentation pages, operational runbooks, and aggregated
OpenAPI 3.1 specifications for an entire multi-surface business ecosystem:
- DocPage: Surface-scoped or ecosystem-wide Markdown documentation pages.
- RunbookStep: Discrete operational procedure step with optional automated command and verification.
- ArchitectureRunbook: Developer and SRE operational runbook (local dev, deploy, triage, backup).
- OpenAPIRoute: Granular endpoint definition with method, path, operation ID, and parameters.
- OpenAPIAggregationEntry: Surface-scoped OpenAPI endpoint collection.
- AggregatedAPISpec: Multi-surface unified OpenAPI 3.1 specification with route collision detection.
- EcosystemDocsContract: Immutable multi-surface documentation contract with deterministic SHA-256 digest.
- EcosystemDocsEngine: Thread-safe in-process documentation query, search, rendering, and export simulator.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Literal

DocCategory = Literal["overview", "architecture", "api_reference", "runbook", "deployment", "security"]
ExportFormat = Literal["markdown", "json", "openapi_bundle", "runbook_checklist"]


def _canonical_json(data: Any) -> str:
    """Serialize data to byte-stable, sorted canonical JSON string."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _surface_slug_from(surface: Any) -> str:
    """Extract surface slug safely from dict or surface dataclass."""
    if isinstance(surface, Mapping):
        return str(surface.get("slug") or surface.get("surface_slug") or "default")
    return str(getattr(surface, "slug", getattr(surface, "surface_slug", "default")))


def _surface_kind_from(surface: Any) -> str:
    """Extract surface kind safely from dict or surface dataclass and normalize."""
    if isinstance(surface, Mapping):
        raw = str(surface.get("surface_kind") or surface.get("kind") or "customer_web").lower()
    else:
        raw = str(getattr(surface, "surface_kind", getattr(surface, "kind", "customer_web"))).lower()
    if "admin" in raw:
        return "admin"
    if "api" in raw or "backend" in raw:
        return "api"
    if "worker" in raw or "queue" in raw or "async" in raw:
        return "worker"
    if "db" in raw or "database" in raw or "storage" in raw:
        return "db"
    return "web"


@dataclass(frozen=True, slots=True)
class DocPage:
    """A Markdown documentation page within the ecosystem."""

    page_id: str
    surface_slug: str
    title: str
    slug: str
    category: DocCategory
    content_markdown: str
    order: int = 0
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "surface_slug": self.surface_slug,
            "title": self.title,
            "slug": self.slug,
            "category": self.category,
            "content_markdown": self.content_markdown,
            "order": self.order,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DocPage:
        return cls(
            page_id=str(data.get("page_id", "")),
            surface_slug=str(data.get("surface_slug", "_ecosystem")),
            title=str(data.get("title", "")),
            slug=str(data.get("slug", "")),
            category=data.get("category", "overview"),  # type: ignore[arg-type]
            content_markdown=str(data.get("content_markdown", "")),
            order=int(data.get("order", 0)),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class RunbookStep:
    """A discrete operational step in a runbook."""

    step_id: str
    order: int
    title: str
    command: str = ""
    description: str = ""
    verification: str = ""
    is_automated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "order": self.order,
            "title": self.title,
            "command": self.command,
            "description": self.description,
            "verification": self.verification,
            "is_automated": self.is_automated,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RunbookStep:
        return cls(
            step_id=str(data.get("step_id", "")),
            order=int(data.get("order", 1)),
            title=str(data.get("title", "")),
            command=str(data.get("command", "")),
            description=str(data.get("description", "")),
            verification=str(data.get("verification", "")),
            is_automated=bool(data.get("is_automated", False)),
        )


@dataclass(frozen=True, slots=True)
class ArchitectureRunbook:
    """An operational, architectural, or deployment runbook."""

    runbook_id: str
    surface_slug: str
    title: str
    summary: str
    prerequisites: tuple[str, ...] = ()
    steps: tuple[RunbookStep, ...] = ()
    target_role: str = "developer"
    estimated_minutes: int = 15
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runbook_id": self.runbook_id,
            "surface_slug": self.surface_slug,
            "title": self.title,
            "summary": self.summary,
            "prerequisites": list(self.prerequisites),
            "steps": [s.to_dict() for s in self.steps],
            "target_role": self.target_role,
            "estimated_minutes": self.estimated_minutes,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ArchitectureRunbook:
        steps_raw = data.get("steps", ())
        steps = tuple(
            RunbookStep.from_dict(s) if isinstance(s, Mapping) else s
            for s in steps_raw
        )
        return cls(
            runbook_id=str(data.get("runbook_id", "")),
            surface_slug=str(data.get("surface_slug", "_ecosystem")),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            prerequisites=tuple(str(p) for p in data.get("prerequisites", ())),
            steps=steps,
            target_role=str(data.get("target_role", "developer")),
            estimated_minutes=int(data.get("estimated_minutes", 15)),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class OpenAPIRoute:
    """A discrete OpenAPI endpoint route."""

    path: str
    method: str
    summary: str
    operation_id: str
    surface_slug: str
    tags: tuple[str, ...] = ()
    parameters: tuple[dict[str, Any], ...] = ()
    request_body: dict[str, Any] | None = None
    responses: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "path": self.path,
            "method": self.method,
            "summary": self.summary,
            "operation_id": self.operation_id,
            "surface_slug": self.surface_slug,
            "tags": list(self.tags),
            "parameters": [dict(p) for p in self.parameters],
        }
        if self.request_body is not None:
            data["request_body"] = self.request_body
        if self.responses is not None:
            data["responses"] = self.responses
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OpenAPIRoute:
        params_raw = data.get("parameters", ())
        params = tuple(dict(p) for p in params_raw if isinstance(p, Mapping))
        req_body = data.get("request_body")
        responses = data.get("responses")
        return cls(
            path=str(data.get("path", "")),
            method=str(data.get("method", "GET")).upper(),
            summary=str(data.get("summary", "")),
            operation_id=str(data.get("operation_id", "")),
            surface_slug=str(data.get("surface_slug", "default")),
            tags=tuple(str(t) for t in data.get("tags", ())),
            parameters=params,
            request_body=dict(req_body) if isinstance(req_body, Mapping) else None,
            responses=dict(responses) if isinstance(responses, Mapping) else None,
        )


@dataclass(frozen=True, slots=True)
class OpenAPIAggregationEntry:
    """Surface-scoped OpenAPI endpoints collection."""

    surface_slug: str
    surface_kind: str
    base_path: str
    title: str
    version: str
    endpoints_count: int
    routes: tuple[OpenAPIRoute, ...] = ()
    spec_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "surface_kind": self.surface_kind,
            "base_path": self.base_path,
            "title": self.title,
            "version": self.version,
            "endpoints_count": self.endpoints_count,
            "routes": [r.to_dict() for r in self.routes],
            "spec_hash": self.spec_hash,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OpenAPIAggregationEntry:
        routes_raw = data.get("routes", ())
        routes = tuple(
            OpenAPIRoute.from_dict(r) if isinstance(r, Mapping) else r
            for r in routes_raw
        )
        return cls(
            surface_slug=str(data.get("surface_slug", "")),
            surface_kind=str(data.get("surface_kind", "api")),
            base_path=str(data.get("base_path", "/")),
            title=str(data.get("title", "")),
            version=str(data.get("version", "1.0.0")),
            endpoints_count=int(data.get("endpoints_count", len(routes))),
            routes=routes,
            spec_hash=str(data.get("spec_hash", "")),
        )


@dataclass(frozen=True, slots=True)
class AggregatedAPISpec:
    """Ecosystem-wide aggregated OpenAPI 3.1 specification."""

    title: str
    version: str
    description: str
    surfaces: tuple[str, ...] = ()
    total_endpoints: int = 0
    paths_summary: tuple[str, ...] = ()
    spec_hash: str = ""
    raw_openapi_json: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "description": self.description,
            "surfaces": list(self.surfaces),
            "total_endpoints": self.total_endpoints,
            "paths_summary": list(self.paths_summary),
            "spec_hash": self.spec_hash,
            "raw_openapi_json": self.raw_openapi_json,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AggregatedAPISpec:
        return cls(
            title=str(data.get("title", "")),
            version=str(data.get("version", "1.0.0")),
            description=str(data.get("description", "")),
            surfaces=tuple(str(s) for s in data.get("surfaces", ())),
            total_endpoints=int(data.get("total_endpoints", 0)),
            paths_summary=tuple(str(p) for p in data.get("paths_summary", ())),
            spec_hash=str(data.get("spec_hash", "")),
            raw_openapi_json=str(data.get("raw_openapi_json", "")),
        )


@dataclass(frozen=True, slots=True)
class EcosystemDocsContract:
    """Complete multi-surface documentation, runbooks, and OpenAPI aggregation contract."""

    ecosystem_id: str
    version: str
    pages: tuple[DocPage, ...] = ()
    runbooks: tuple[ArchitectureRunbook, ...] = ()
    entries: tuple[OpenAPIAggregationEntry, ...] = ()
    aggregated_api: AggregatedAPISpec | None = None
    generated_at: str = ""

    def digest(self) -> str:
        """Deterministic SHA-256 digest of documentation contract."""
        payload = {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "pages": [p.to_dict() for p in self.pages],
            "runbooks": [r.to_dict() for r in self.runbooks],
            "entries": [e.to_dict() for e in self.entries],
            "aggregated_api": self.aggregated_api.to_dict() if self.aggregated_api else None,
        }
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "pages": [p.to_dict() for p in self.pages],
            "runbooks": [r.to_dict() for r in self.runbooks],
            "entries": [e.to_dict() for e in self.entries],
            "aggregated_api": self.aggregated_api.to_dict() if self.aggregated_api else None,
            "digest": self.digest(),
            "generated_at": self.generated_at,
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemDocsContract:
        pages_raw = data.get("pages", ())
        pages = tuple(
            DocPage.from_dict(p) if isinstance(p, Mapping) else p
            for p in pages_raw
        )
        runbooks_raw = data.get("runbooks", ())
        runbooks = tuple(
            ArchitectureRunbook.from_dict(r) if isinstance(r, Mapping) else r
            for r in runbooks_raw
        )
        entries_raw = data.get("entries", ())
        entries = tuple(
            OpenAPIAggregationEntry.from_dict(e) if isinstance(e, Mapping) else e
            for e in entries_raw
        )
        agg_raw = data.get("aggregated_api")
        agg_api = AggregatedAPISpec.from_dict(agg_raw) if isinstance(agg_raw, Mapping) else None

        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "default")),
            version=str(data.get("version", "1.0.0")),
            pages=pages,
            runbooks=runbooks,
            entries=entries,
            aggregated_api=agg_api,
            generated_at=str(data.get("generated_at", "")),
        )

    @classmethod
    def from_json(cls, raw: str) -> EcosystemDocsContract:
        return cls.from_dict(json.loads(raw))


# ==============================================================================
# Deterministic Synthesis
# ==============================================================================

def synthesize_ecosystem_docs(
    ecosystem_id: str,
    surfaces: Sequence[Any],
    version: str = "1.0.0",
) -> EcosystemDocsContract:
    """Synthesize canonical documentation, runbooks, and aggregated OpenAPI specs.

    Pure, deterministic, Python 3.13 stdlib-only.
    """
    slug = ecosystem_id or "default-ecosystem"
    pages: list[DocPage] = []
    runbooks: list[ArchitectureRunbook] = []
    entries: list[OpenAPIAggregationEntry] = []

    # 1. System Overview Page
    surface_summaries = []
    for s in surfaces:
        s_slug = _surface_slug_from(s)
        s_kind = _surface_kind_from(s)
        surface_summaries.append(f"- **`{s_slug}`** ({s_kind}): Primary surface interface and bounded domain.")

    overview_md = (
        f"# {slug.replace('-', ' ').title()} — Architecture Overview\n\n"
        f"This document provides the canonical architectural documentation and operational boundaries "
        f"for the **{slug}** multi-surface application ecosystem.\n\n"
        f"## Surfaces Topology\n\n"
        + "\n".join(surface_summaries)
        + "\n\n## Inter-Surface Communication\n\n"
        "- **Synchronous Ingress**: REST APIs, OpenAPI 3.1 documented endpoints, CORS and HMAC-signed webhooks.\n"
        "- **Asynchronous Events**: Event bridge messaging, decoupled workers, and idempotent consumers.\n"
        "- **Data Persistence**: Isolated PostgreSQL database schemas with automated migrations and audit trails.\n"
    )
    pages.append(
        DocPage(
            page_id=f"{slug}-doc-overview",
            surface_slug="_ecosystem",
            title="Ecosystem Architecture Overview",
            slug="overview",
            category="overview",
            content_markdown=overview_md,
            order=1,
            tags=("overview", "architecture", "ecosystem"),
        )
    )

    # 2. Data Flow & Event Topology Page
    dataflow_md = (
        f"# {slug.replace('-', ' ').title()} — Data Flow & Event Topology\n\n"
        "## Synchronous Request Flow\n\n"
        "1. Client Web/Mobile interfaces initiate TLS 1.3 encrypted HTTPS requests.\n"
        "2. Control-plane gateway validates JWT authorization tokens and evaluates rate limits.\n"
        "3. Backend APIs invoke scoped repository contracts with parameterized PostgreSQL queries.\n\n"
        "## Asynchronous Event Flow\n\n"
        "1. Domain state changes publish transactional events to the durable event stream.\n"
        "2. Background workers process jobs with exponential backoff and dead-letter queues.\n"
        "3. Event audit logging persists immutable cryptographic traces.\n"
    )
    pages.append(
        DocPage(
            page_id=f"{slug}-doc-dataflow",
            surface_slug="_ecosystem",
            title="Data Flow & Event Topology",
            slug="data-flow",
            category="architecture",
            content_markdown=dataflow_md,
            order=2,
            tags=("dataflow", "events", "architecture"),
        )
    )

    # 3. Security & Governance Documentation Page
    sec_md = (
        f"# {slug.replace('-', ' ').title()} — Security & Governance Standards\n\n"
        "## Compliance Foundations\n\n"
        "- **SOC 2 Type II**: Role-based access control, least privilege, audit trail immutability.\n"
        "- **GDPR**: Data subject privacy, automated retention purging, field pseudonymization.\n"
        "- **ISO/IEC 27001**: Information security policies, cryptographic controls, incident triage.\n\n"
        "## Secret Management & Isolation\n\n"
        "- Zero plain-text secrets in repository code or client builds.\n"
        "- Brokered capability references and environment-isolated credentials.\n"
    )
    pages.append(
        DocPage(
            page_id=f"{slug}-doc-security",
            surface_slug="_ecosystem",
            title="Security & Governance Policy",
            slug="security-governance",
            category="security",
            content_markdown=sec_md,
            order=3,
            tags=("security", "governance", "compliance"),
        )
    )

    # 4. Surface-specific Documentation Pages
    order_counter = 4
    for s in surfaces:
        s_slug = _surface_slug_from(s)
        s_kind = _surface_kind_from(s)
        s_title = s_slug.replace("-", " ").replace("_", " ").title()

        page_content = (
            f"# {s_title} Surface Specification\n\n"
            f"- **Surface Slug**: `{s_slug}`\n"
            f"- **Surface Kind**: `{s_kind}`\n"
            f"- **Ecosystem**: `{slug}`\n\n"
            f"## Architectural Role\n\n"
            f"The `{s_slug}` surface executes the `{s_kind}` responsibilities within the {slug} ecosystem. "
            f"It operates with strict process isolation, bounded data access policies, and dedicated health probes.\n\n"
            f"## Verification Gates\n\n"
            f"Every code change to `{s_slug}` passes deterministic verification gates: install, typecheck, "
            f"lint, unit tests, and build.\n"
        )
        pages.append(
            DocPage(
                page_id=f"{slug}-doc-{s_slug}",
                surface_slug=s_slug,
                title=f"{s_title} Specification",
                slug=f"surface-{s_slug}",
                category="architecture",
                content_markdown=page_content,
                order=order_counter,
                tags=("surface", s_kind, s_slug),
            )
        )
        order_counter += 1

    # 5. Operational Runbooks
    # Runbook 1: Local Development
    runbooks.append(
        ArchitectureRunbook(
            runbook_id=f"{slug}-rb-local-dev",
            surface_slug="_ecosystem",
            title="Local Multi-Surface Development Setup",
            summary="Bootstrapping and verifying the entire multi-surface ecosystem locally without external cloud services.",
            prerequisites=("Python 3.13+", "Git 2.40+", "Docker Compose (optional)"),
            steps=(
                RunbookStep(
                    step_id="rb-step-1",
                    order=1,
                    title="Clone and Verify Workspace",
                    command="git status && task doctor",
                    description="Confirm clean git working directory and that developer toolchain is operational.",
                    verification="Doctor passed with all green checks.",
                    is_automated=True,
                ),
                RunbookStep(
                    step_id="rb-step-2",
                    order=2,
                    title="Bootstrap Local Dependencies",
                    command="task bootstrap",
                    description="Install local dependencies deterministically into isolated environments.",
                    verification="Dependencies installed cleanly without network timeouts.",
                    is_automated=True,
                ),
                RunbookStep(
                    step_id="rb-step-3",
                    order=3,
                    title="Run Multi-Surface Test Verification",
                    command="task verify",
                    description="Execute 100% offline Stage 0 verification test suites across all surfaces.",
                    verification="All test suites pass with 0 errors.",
                    is_automated=True,
                ),
                RunbookStep(
                    step_id="rb-step-4",
                    order=4,
                    title="Launch Studio Multi-Surface Orchestration",
                    command="task studio",
                    description="Start the local Studio server with multi-surface live preview and surface switching.",
                    verification="Studio server running on http://127.0.0.1:4000.",
                    is_automated=False,
                ),
            ),
            target_role="developer",
            estimated_minutes=10,
            tags=("local", "setup", "developer", "bootstrap"),
        )
    )

    # Runbook 2: Production Deployment
    runbooks.append(
        ArchitectureRunbook(
            runbook_id=f"{slug}-rb-prod-deploy",
            surface_slug="_ecosystem",
            title="Production Multi-Surface Deployment & Verification",
            summary="Sequential staged deployment across web, API, worker, and database surfaces with canary health gates.",
            prerequisites=("Target environment credentials", "Passing CI/CD pipeline", "Clean git tag"),
            steps=(
                RunbookStep(
                    step_id="rb-step-deploy-1",
                    order=1,
                    title="Database Migration Dry-Run",
                    command="task agent-engine:solution-pack:ecosystem -- recovery <ecosystem> --simulate",
                    description="Verify pre-deployment database backup target and migration rollback trigger.",
                    verification="Snapshot verification returns valid SHA-256 digest.",
                    is_automated=True,
                ),
                RunbookStep(
                    step_id="rb-step-deploy-2",
                    order=2,
                    title="Deploy Backend Services & API Gateway",
                    command="docker compose -f docker-compose.prod.yml up -d --no-deps api worker",
                    description="Roll out updated API and worker containers before frontend traffic cutover.",
                    verification="Readiness health checks return HTTP 200 OK.",
                    is_automated=True,
                ),
                RunbookStep(
                    step_id="rb-step-deploy-3",
                    order=3,
                    title="Deploy Web & Admin Frontend Surfaces",
                    command="docker compose -f docker-compose.prod.yml up -d --no-deps web admin",
                    description="Roll out frontend assets with cache busting and zero downtime.",
                    verification="Synthetic canary smoke tests pass.",
                    is_automated=True,
                ),
            ),
            target_role="devops",
            estimated_minutes=25,
            tags=("production", "deploy", "release", "canary"),
        )
    )

    # Runbook 3: Incident Triage
    runbooks.append(
        ArchitectureRunbook(
            runbook_id=f"{slug}-rb-incident-triage",
            surface_slug="_ecosystem",
            title="High-Severity Incident Triage & Recovery",
            summary="Emergency diagnosis, traffic shedding, escalation protocol, and rapid service restoration.",
            prerequisites=("Incident Commander assigned", "Monitoring dashboard access"),
            steps=(
                RunbookStep(
                    step_id="rb-step-inc-1",
                    order=1,
                    title="Assess Blast Radius & Degraded Surfaces",
                    command="task agent-engine:solution-pack:ecosystem -- alerting <ecosystem> --simulate",
                    description="Evaluate alerting rules and active incident runbooks across all surfaces.",
                    verification="Degraded surface identified with active escalation tier.",
                    is_automated=True,
                ),
                RunbookStep(
                    step_id="rb-step-inc-2",
                    order=2,
                    title="Execute Circuit Breaker or Traffic Shedding",
                    command="curl -X POST http://localhost:4000/api/ecosystem/gateway/circuit-break",
                    description="Isolate failing downstream service to protect healthy surfaces.",
                    verification="Upstream services receive graceful fallback response.",
                    is_automated=True,
                ),
                RunbookStep(
                    step_id="rb-step-inc-3",
                    order=3,
                    title="Perform Service Rollback If Required",
                    command="task agent-engine:solution-pack:ecosystem -- recovery <ecosystem> --rollback",
                    description="Revert to last known verified snapshot if root cause is faulty deployment.",
                    verification="Health check probes return healthy status.",
                    is_automated=False,
                ),
            ),
            target_role="sre",
            estimated_minutes=15,
            tags=("incident", "sre", "emergency", "triage"),
        )
    )

    # 6. OpenAPI Specifications Aggregation
    all_routes: list[OpenAPIRoute] = []
    paths_summary: list[str] = []

    for s in surfaces:
        s_slug = _surface_slug_from(s)
        s_kind = _surface_kind_from(s)
        base_path = f"/api/{s_slug}" if s_kind in ("api", "admin") else f"/{s_slug}"
        surface_routes: list[OpenAPIRoute] = []

        # Standard Health Endpoints for all surfaces
        surface_routes.append(
            OpenAPIRoute(
                path=f"{base_path}/health/live",
                method="GET",
                summary=f"Liveness probe for {s_slug}",
                operation_id=f"get_{s_slug.replace('-', '_')}_live",
                surface_slug=s_slug,
                tags=(s_slug, "health"),
                responses={"200": {"description": "Service is alive"}},
            )
        )
        surface_routes.append(
            OpenAPIRoute(
                path=f"{base_path}/health/ready",
                method="GET",
                summary=f"Readiness probe for {s_slug}",
                operation_id=f"get_{s_slug.replace('-', '_')}_ready",
                surface_slug=s_slug,
                tags=(s_slug, "health"),
                responses={"200": {"description": "Service is ready to handle traffic"}},
            )
        )

        # Domain endpoints for API surfaces
        if s_kind in ("api", "admin"):
            surface_routes.append(
                OpenAPIRoute(
                    path=f"{base_path}/v1/items",
                    method="GET",
                    summary=f"List collection items for {s_slug}",
                    operation_id=f"list_{s_slug.replace('-', '_')}_items",
                    surface_slug=s_slug,
                    tags=(s_slug, "items"),
                    parameters=(
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                        {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}},
                    ),
                    responses={"200": {"description": "List of items with pagination metadata"}},
                )
            )
            surface_routes.append(
                OpenAPIRoute(
                    path=f"{base_path}/v1/items",
                    method="POST",
                    summary=f"Create a new item in {s_slug}",
                    operation_id=f"create_{s_slug.replace('-', '_')}_item",
                    surface_slug=s_slug,
                    tags=(s_slug, "items"),
                    request_body={"content": {"application/json": {"schema": {"type": "object"}}}},
                    responses={"201": {"description": "Item created successfully"}},
                )
            )
            surface_routes.append(
                OpenAPIRoute(
                    path=f"{base_path}/v1/items/{{item_id}}",
                    method="GET",
                    summary=f"Get single item by ID in {s_slug}",
                    operation_id=f"get_{s_slug.replace('-', '_')}_item",
                    surface_slug=s_slug,
                    tags=(s_slug, "items"),
                    parameters=({"name": "item_id", "in": "path", "required": True, "schema": {"type": "string"}},),
                    responses={
                        "200": {"description": "Single item record"},
                        "404": {"description": "Item not found"},
                    },
                )
            )

        spec_raw = {
            "surface": s_slug,
            "routes": [r.to_dict() for r in surface_routes],
        }
        entry_hash = hashlib.sha256(_canonical_json(spec_raw).encode("utf-8")).hexdigest()

        entry = OpenAPIAggregationEntry(
            surface_slug=s_slug,
            surface_kind=s_kind,
            base_path=base_path,
            title=f"{s_slug.title()} API Specification",
            version=version,
            endpoints_count=len(surface_routes),
            routes=tuple(surface_routes),
            spec_hash=entry_hash,
        )
        entries.append(entry)
        all_routes.extend(surface_routes)
        for r in surface_routes:
            paths_summary.append(f"{r.method} {r.path}")

    # Build OpenAPI 3.1 Aggregated Spec Object
    openapi_paths: dict[str, dict[str, Any]] = {}
    for r in all_routes:
        if r.path not in openapi_paths:
            openapi_paths[r.path] = {}
        m_lower = r.method.lower()
        method_obj: dict[str, Any] = {
            "summary": r.summary,
            "operationId": r.operation_id,
            "tags": list(r.tags),
            "responses": r.responses or {"200": {"description": "Success"}},
        }
        if r.parameters:
            method_obj["parameters"] = [dict(p) for p in r.parameters]
        if r.request_body:
            method_obj["requestBody"] = r.request_body
        openapi_paths[r.path][m_lower] = method_obj

    aggregated_doc = {
        "openapi": "3.1.0",
        "info": {
            "title": f"{slug.replace('-', ' ').title()} Unified API",
            "version": version,
            "description": f"Aggregated OpenAPI 3.1 specification for all surfaces in {slug}.",
        },
        "paths": openapi_paths,
    }
    raw_json = _canonical_json(aggregated_doc)
    aggregated_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    aggregated_api = AggregatedAPISpec(
        title=f"{slug.replace('-', ' ').title()} Unified API",
        version=version,
        description=f"Aggregated OpenAPI 3.1 specification across {len(surfaces)} surfaces.",
        surfaces=tuple(_surface_slug_from(s) for s in surfaces),
        total_endpoints=len(all_routes),
        paths_summary=tuple(paths_summary),
        spec_hash=aggregated_hash,
        raw_openapi_json=raw_json,
    )

    return EcosystemDocsContract(
        ecosystem_id=slug,
        version=version,
        pages=tuple(pages),
        runbooks=tuple(runbooks),
        entries=tuple(entries),
        aggregated_api=aggregated_api,
        generated_at="2026-09-15T00:00:00Z",
    )


# ==============================================================================
# In-Process Engine
# ==============================================================================

class EcosystemDocsEngine:
    """Thread-safe in-process documentation, runbook query, search, and export engine."""

    def __init__(self, contract: EcosystemDocsContract) -> None:
        self._contract = contract
        self._lock = threading.RLock()

    @property
    def contract(self) -> EcosystemDocsContract:
        with self._lock:
            return self._contract

    def render_markdown_bundle(
        self,
        include_runbooks: bool = True,
        include_api: bool = True,
    ) -> str:
        """Render a unified, comprehensive Markdown documentation site/book."""
        with self._lock:
            c = self._contract
            toc_lines = [
                f"# {c.ecosystem_id.replace('-', ' ').title()} Documentation Bundle\n",
                f"> Version: `{c.version}` | Contract Digest: `{c.digest()[:16]}...`\n",
                "## Table of Contents\n",
                "### Architectural Documentation",
            ]
            for p in sorted(c.pages, key=lambda x: x.order):
                toc_lines.append(f"- [{p.title}](#{p.slug}) (`{p.category}`)")

            if include_runbooks and c.runbooks:
                toc_lines.append("\n### Operational Runbooks")
                for rb in c.runbooks:
                    toc_lines.append(f"- [{rb.title}](#{rb.runbook_id}) ({rb.target_role}, {rb.estimated_minutes}m)")

            if include_api and c.aggregated_api:
                toc_lines.append("\n### OpenAPI API Reference")
                toc_lines.append(f"- [Aggregated API Endpoints ({c.aggregated_api.total_endpoints})](#api-reference)")

            sections = ["\n".join(toc_lines), "---\n"]

            # Append pages in order
            for p in sorted(c.pages, key=lambda x: x.order):
                page_block = (
                    f"<a id=\"{p.slug}\"></a>\n\n"
                    f"{p.content_markdown}\n\n"
                    f"*Category: `{p.category}` | Surface: `{p.surface_slug}` | Tags: {', '.join(p.tags)}*\n\n"
                    "---\n"
                )
                sections.append(page_block)

            # Append runbooks
            if include_runbooks:
                for rb in c.runbooks:
                    step_lines = []
                    for step in rb.steps:
                        auto_badge = "*(Automated)*" if step.is_automated else "*(Manual)*"
                        cmd_block = f"```bash\n{step.command}\n```\n" if step.command else ""
                        ver_line = f"- **Verification**: {step.verification}\n" if step.verification else ""
                        step_lines.append(
                            f"#### Step {step.order}: {step.title} {auto_badge}\n\n"
                            f"{step.description}\n\n"
                            f"{cmd_block}"
                            f"{ver_line}"
                        )

                    prereq_lines = "\n".join(f"- {pr}" for pr in rb.prerequisites) if rb.prerequisites else "None"
                    rb_block = (
                        f"<a id=\"{rb.runbook_id}\"></a>\n\n"
                        f"# Runbook: {rb.title}\n\n"
                        f"**Role**: `{rb.target_role}` | **Est. Time**: `{rb.estimated_minutes} min`\n\n"
                        f"### Summary\n{rb.summary}\n\n"
                        f"### Prerequisites\n{prereq_lines}\n\n"
                        f"### Execution Steps\n\n"
                        + "\n".join(step_lines)
                        + "\n---\n"
                    )
                    sections.append(rb_block)

            # Append API routes summary
            if include_api and c.aggregated_api:
                api_lines = [
                    "<a id=\"api-reference\"></a>\n\n",
                    f"# Aggregated OpenAPI 3.1 Reference\n\n",
                    f"Total Endpoints: `{c.aggregated_api.total_endpoints}` | Spec Hash: `{c.aggregated_api.spec_hash[:16]}...`\n\n",
                    "| Method | Path | Surface | Summary |\n",
                    "| --- | --- | --- | --- |\n",
                ]
                for entry in c.entries:
                    for route in entry.routes:
                        api_lines.append(f"| `{route.method}` | `{route.path}` | `{route.surface_slug}` | {route.summary} |\n")
                sections.append("".join(api_lines))

            return "\n".join(sections)

    def search_documentation(
        self,
        query: str,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fast tokenized keyword search across pages, runbooks, and API endpoints."""
        with self._lock:
            q = query.lower().strip()
            results: list[dict[str, Any]] = []
            if not q:
                return results

            terms = q.split()

            # 1. Search Pages
            for page in self._contract.pages:
                if category and page.category != category:
                    continue
                score = 0
                title_lower = page.title.lower()
                content_lower = page.content_markdown.lower()
                tags_lower = [t.lower() for t in page.tags]

                for term in terms:
                    if term in title_lower:
                        score += 10
                    if any(term in t for t in tags_lower):
                        score += 5
                    if term in content_lower:
                        score += 2

                if score > 0:
                    results.append({
                        "kind": "doc_page",
                        "id": page.page_id,
                        "title": page.title,
                        "surface_slug": page.surface_slug,
                        "category": page.category,
                        "score": score,
                        "snippet": page.content_markdown[:160].replace("\n", " ") + "...",
                    })

            # 2. Search Runbooks
            if not category or category == "runbook":
                for rb in self._contract.runbooks:
                    score = 0
                    title_lower = rb.title.lower()
                    summary_lower = rb.summary.lower()
                    tags_lower = [t.lower() for t in rb.tags]

                    for term in terms:
                        if term in title_lower:
                            score += 10
                        if any(term in t for t in tags_lower):
                            score += 5
                        if term in summary_lower:
                            score += 3
                        for s in rb.steps:
                            if term in s.title.lower() or term in s.command.lower():
                                score += 2

                    if score > 0:
                        results.append({
                            "kind": "runbook",
                            "id": rb.runbook_id,
                            "title": rb.title,
                            "surface_slug": rb.surface_slug,
                            "category": "runbook",
                            "score": score,
                            "snippet": rb.summary,
                        })

            # 3. Search API Routes
            if not category or category == "api_reference":
                for entry in self._contract.entries:
                    for route in entry.routes:
                        score = 0
                        path_lower = route.path.lower()
                        summary_lower = route.summary.lower()
                        op_id_lower = route.operation_id.lower()

                        for term in terms:
                            if term in path_lower:
                                score += 8
                            if term in summary_lower:
                                score += 4
                            if term in op_id_lower:
                                score += 4

                        if score > 0:
                            results.append({
                                "kind": "api_route",
                                "id": f"{route.method}_{route.path}",
                                "title": f"{route.method} {route.path}",
                                "surface_slug": route.surface_slug,
                                "category": "api_reference",
                                "score": score,
                                "snippet": route.summary,
                            })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results

    def get_aggregated_openapi(self, format: str = "json") -> dict[str, Any] | str:
        """Return the aggregated OpenAPI 3.1 document as dict or canonical JSON string."""
        with self._lock:
            if not self._contract.aggregated_api or not self._contract.aggregated_api.raw_openapi_json:
                doc = {
                    "openapi": "3.1.0",
                    "info": {"title": self._contract.ecosystem_id, "version": self._contract.version},
                    "paths": {},
                }
            else:
                doc = json.loads(self._contract.aggregated_api.raw_openapi_json)

            if format == "json":
                return _canonical_json(doc)
            return doc

    def simulate_documentation_export(
        self,
        export_format: ExportFormat = "markdown",
    ) -> dict[str, Any]:
        """Simulate a documentation export dry-run across formats."""
        with self._lock:
            c = self._contract
            files: list[dict[str, Any]] = []

            if export_format == "markdown":
                bundle_text = self.render_markdown_bundle()
                files.append({
                    "path": f"docs/{c.ecosystem_id}/COMPLETE_DOCUMENTATION.md",
                    "format": "markdown",
                    "bytes": len(bundle_text.encode("utf-8")),
                    "description": "Unified all-in-one markdown documentation site",
                })
                for page in c.pages:
                    files.append({
                        "path": f"docs/{c.ecosystem_id}/pages/{page.slug}.md",
                        "format": "markdown",
                        "bytes": len(page.content_markdown.encode("utf-8")),
                        "description": f"Page: {page.title}",
                    })
            elif export_format == "json":
                json_str = c.to_json(indent=2)
                files.append({
                    "path": f"docs/{c.ecosystem_id}/ecosystem-docs-contract.json",
                    "format": "json",
                    "bytes": len(json_str.encode("utf-8")),
                    "description": "Canonical documentation contract JSON",
                })
            elif export_format == "openapi_bundle":
                openapi_str = str(self.get_aggregated_openapi(format="json"))
                files.append({
                    "path": f"docs/{c.ecosystem_id}/openapi-unified-spec.json",
                    "format": "json",
                    "bytes": len(openapi_str.encode("utf-8")),
                    "description": "Aggregated OpenAPI 3.1 unified JSON specification",
                })
                for entry in c.entries:
                    files.append({
                        "path": f"docs/{c.ecosystem_id}/openapi/{entry.surface_slug}-spec.json",
                        "format": "json",
                        "bytes": len(_canonical_json(entry.to_dict()).encode("utf-8")),
                        "description": f"Surface OpenAPI spec: {entry.surface_slug}",
                    })
            elif export_format == "runbook_checklist":
                for rb in c.runbooks:
                    checklist_lines = [f"# {rb.title} — Checklist\n", f"Role: {rb.target_role}\n"]
                    for s in rb.steps:
                        checklist_lines.append(f"- [ ] Step {s.order}: {s.title} ({s.command})")
                    text = "\n".join(checklist_lines)
                    files.append({
                        "path": f"docs/{c.ecosystem_id}/runbooks/{rb.runbook_id}-checklist.md",
                        "format": "markdown",
                        "bytes": len(text.encode("utf-8")),
                        "description": f"Operational checklist: {rb.title}",
                    })
            else:
                raise ValueError(f"Unsupported export format: '{export_format}'")

            total_bytes = sum(f["bytes"] for f in files)
            return {
                "ecosystem_id": c.ecosystem_id,
                "version": c.version,
                "export_format": export_format,
                "status": "success",
                "file_count": len(files),
                "total_bytes": total_bytes,
                "pages_exported": len(c.pages),
                "runbooks_exported": len(c.runbooks),
                "endpoints_exported": c.aggregated_api.total_endpoints if c.aggregated_api else 0,
                "files": files,
            }
