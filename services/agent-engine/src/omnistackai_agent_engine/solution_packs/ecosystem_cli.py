"""Command-line interface for Solution Pack Ecosystem Pack operations (R-444).

Supports:
- synthesize: Synthesize a multi-surface ecosystem pack from a Solution Pack
- verify: Verify integrity and Application IR validity of an ecosystem package file
- inspect: Pretty-print ecosystem package metadata and surfaces
- build: Materialize all surfaces of an ecosystem package as separate Git repos
- verify-suite: Inspect or dry-run simulate the full ecosystem verification suite
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from omnistackai_agent_engine.intake.build_app import build_app_from_ir
from omnistackai_agent_engine.verify import verify_plans_for_ir
from .ecosystem_pack import (
    EcosystemPackPackage,
    parse_ecosystem_pack_package,
    synthesize_ecosystem_pack,
)
from .registry import DEFAULT_SOLUTION_PACK_REGISTRY, SolutionPackError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omnistackai-agent-engine solution-pack-ecosystem",
        description="Synthesize, verify, inspect, and build Solution Pack multi-surface ecosystem packages.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # Subcommand: synthesize
    synthesize_parser = subparsers.add_parser("synthesize", help="Synthesize an ecosystem pack from a Solution Pack.")
    synthesize_parser.add_argument(
        "--pack",
        required=True,
        help="Pack identifier in the registry (e.g. 'minimal-blog', 'rideshare-favourites').",
    )
    synthesize_parser.add_argument(
        "--prompt",
        default=None,
        help="Optional prompt to drive surface scoping.",
    )
    synthesize_parser.add_argument(
        "--option",
        default="complete",
        help="Build-scope option ('complete', 'customer', etc.). Defaults to 'complete'.",
    )
    synthesize_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path for the .ecosystem.pack.json artifact. If omitted, writes to stdout.",
    )

    # Subcommand: verify
    verify_parser = subparsers.add_parser("verify", help="Verify the integrity and schema of an ecosystem pack file.")
    verify_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file to verify.")

    # Subcommand: inspect
    inspect_parser = subparsers.add_parser("inspect", help="Pretty-print ecosystem package details.")
    inspect_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file to inspect.")

    # Subcommand: build
    build_parser = subparsers.add_parser("build", help="Materialize all surfaces into separate Git repositories.")
    build_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file.")
    build_parser.add_argument("--out-dir", required=True, help="Root output directory where repositories will be created.")
    build_parser.add_argument("--author-name", default=os.environ.get("GIT_AUTHOR_NAME", "sanjeetji"), help="Git author name.")
    build_parser.add_argument("--author-email", default=os.environ.get("GIT_AUTHOR_EMAIL", "sk698166@gmail.com"), help="Git author email.")
    build_parser.add_argument("--overwrite", action="store_true", help="Overwrite target directories if they exist.")

    # Subcommand: catalog
    catalog_parser = subparsers.add_parser("catalog", help="List registered ecosystem packs in the default registry.")
    catalog_parser.add_argument("--domain", default=None, help="Optional domain filter.")
    catalog_parser.add_argument("--json", action="store_true", help="Output catalog as canonical JSON.")

    # Subcommand: auth
    auth_parser = subparsers.add_parser("auth", help="Inspect cross-app auth contract and role matrix for an ecosystem pack.")
    auth_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file to inspect.")
    auth_parser.add_argument("--json", action="store_true", help="Output auth contract as canonical JSON.")

    # Subcommand: state
    state_parser = subparsers.add_parser("state", help="Inspect unified state binding and lifecycle flows for an ecosystem pack.")
    state_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file to inspect.")
    state_parser.add_argument("--json", action="store_true", help="Output state binding as canonical JSON.")

    # Subcommand: events
    events_parser = subparsers.add_parser("events", help="Inspect cross-surface event bridge contracts, webhook subscriptions, and delivery policies.")
    events_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.")
    events_parser.add_argument("--json", action="store_true", help="Output event bridge contract as canonical JSON.")

    # Subcommand: telemetry
    telemetry_parser = subparsers.add_parser("telemetry", help="Inspect cross-surface telemetry contract, traced surfaces, and audit actions for an ecosystem pack.")
    telemetry_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.")
    telemetry_parser.add_argument("--json", action="store_true", help="Output telemetry contract as canonical JSON.")

    # Subcommand: deploy
    deploy_parser = subparsers.add_parser("deploy", help="Inspect multi-surface deployment manifest, gateway routes, or generate Docker Compose YAML.")
    deploy_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.")
    deploy_parser.add_argument("--json", action="store_true", help="Output deployment manifest as canonical JSON.")
    deploy_parser.add_argument("--compose", action="store_true", help="Output deployment manifest as Docker Compose YAML.")

    # Subcommand: sync
    sync_parser = subparsers.add_parser("sync", help="Inspect cross-surface data sync contracts, sync entities, and conflict resolution rules.")
    sync_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.")
    sync_parser.add_argument("--json", action="store_true", help="Output sync contract as canonical JSON.")

    # Subcommand: cicd
    cicd_parser = subparsers.add_parser("cicd", help="Inspect multi-surface CI/CD workflow contracts, generate GitHub Actions YAML, or simulate pipeline.")
    cicd_parser.add_argument("package_file", help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.")
    cicd_parser.add_argument("--json", action="store_true", help="Output CI/CD contract as canonical JSON.")
    cicd_parser.add_argument("--yaml", action="store_true", help="Output GitHub Actions workflow YAML.")
    cicd_parser.add_argument("--simulate", action="store_true", help="Run in-process dry-run simulation of the CI/CD DAG.")

    # Subcommand: verify-suite
    verify_suite_parser = subparsers.add_parser(
        "verify-suite",
        help="Inspect or dry-run simulate the health check, smoke test, and canary verification suite for an ecosystem pack.",
    )
    verify_suite_parser.add_argument(
        "package_file",
        help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.",
    )
    verify_suite_parser.add_argument("--json", action="store_true", help="Output verification contract as canonical JSON.")
    verify_suite_parser.add_argument("--simulate", action="store_true", help="Run in-process dry-run simulation of all probes, smoke tests, and canary rules.")

    # Subcommand: recovery
    recovery_parser = subparsers.add_parser(
        "recovery",
        help="Inspect or dry-run simulate the disaster recovery, snapshot backup, and rollback contract for an ecosystem pack.",
    )
    recovery_parser.add_argument(
        "package_file",
        help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.",
    )
    recovery_parser.add_argument("--json", action="store_true", help="Output disaster recovery contract as canonical JSON.")
    recovery_parser.add_argument("--simulate", action="store_true", help="Run in-process dry-run simulation of snapshots, recovery steps, and rollback triggers.")

    # Subcommand: capacity
    capacity_parser = subparsers.add_parser(
        "capacity",
        help="Inspect or dry-run simulate capacity planning, resource quotas, and unit economics for an ecosystem pack.",
    )
    capacity_parser.add_argument(
        "package_file",
        help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.",
    )
    capacity_parser.add_argument("--json", action="store_true", help="Output capacity planning contract as canonical JSON.")
    capacity_parser.add_argument("--simulate", action="store_true", help="Run in-process dry-run simulation of workload scaling tiers.")
    capacity_parser.add_argument(
        "--tier",
        choices=["base", "peak", "stress"],
        default="base",
        help="Workload tier for simulation (base, peak, or stress; default: base).",
    )

    # Subcommand: alerting
    alerting_parser = subparsers.add_parser(
        "alerting",
        help="Inspect or dry-run simulate alert rules, incident runbooks, and escalation policies for an ecosystem pack.",
    )
    alerting_parser.add_argument(
        "package_file",
        help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.",
    )
    alerting_parser.add_argument("--json", action="store_true", help="Output alerting contract as canonical JSON.")
    alerting_parser.add_argument("--simulate", action="store_true", help="Run in-process dry-run simulation of incident scenario.")
    alerting_parser.add_argument(
        "--scenario",
        default="api_error_spike",
        help="Incident scenario for simulation (api_error_spike, latency_spike, db_connection_exhaustion, budget_overrun; default: api_error_spike).",
    )

    # Subcommand: sla
    sla_parser = subparsers.add_parser(
        "sla",
        help="Inspect or dry-run simulate SLIs, SLOs, error budgets, and SLAs for an ecosystem pack.",
    )
    sla_parser.add_argument(
        "package_file",
        help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.",
    )
    sla_parser.add_argument("--json", action="store_true", help="Output SLA contract as canonical JSON.")
    sla_parser.add_argument("--simulate", action="store_true", help="Run in-process dry-run simulation of SLA compliance and burn rates.")
    sla_parser.add_argument(
        "--scenario",
        default="normal_operations",
        help="SLA simulation scenario (normal_operations, minor_degradation, severe_outage, budget_exhaustion; default: normal_operations).",
    )

    # Subcommand: governance
    governance_parser = subparsers.add_parser(
        "governance",
        help="Inspect or dry-run simulate compliance policies, data classifications, and audit evidence for an ecosystem pack.",
    )
    governance_parser.add_argument(
        "package_file",
        help="Path to the .ecosystem.pack.json file or registered ecosystem ID to inspect.",
    )
    governance_parser.add_argument("--json", action="store_true", help="Output governance contract as canonical JSON.")
    governance_parser.add_argument("--simulate", action="store_true", help="Run in-process dry-run simulation of compliance audit.")
    governance_parser.add_argument(
        "--scenario",
        default="standard_audit",
        help="Audit simulation scenario (standard_audit, gdpr_dsar_request, data_breach_investigation, soc2_certification, high_risk_violations; default: standard_audit).",
    )

    return parser


def run_synthesize(args: argparse.Namespace) -> int:
    registry = DEFAULT_SOLUTION_PACK_REGISTRY
    pack = registry.get(args.pack)
    if pack is None:
        sys.stderr.write(f"Error: Unknown solution pack '{args.pack}'\n")
        return 1

    try:
        from omnistackai_agent_engine.intake.scope_compiler import propose_ecosystem
        proposal = propose_ecosystem(args.prompt) if args.prompt else None
        eco_pkg = synthesize_ecosystem_pack(pack, proposal=proposal, option_id=args.option, registry=registry)
    except SolutionPackError as exc:
        sys.stderr.write(f"Error synthesizing ecosystem pack: {exc}\n")
        return 1

    canonical_json = eco_pkg.to_json()

    if args.output:
        out_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(canonical_json)
            f.write("\n")
        sys.stdout.write(f"Synthesized ecosystem pack '{eco_pkg.ecosystem_id}' (version {eco_pkg.version}) to {out_path}\n")
    else:
        sys.stdout.write(canonical_json)
        sys.stdout.write("\n")
    return 0


def run_verify(args: argparse.Namespace) -> int:
    path = os.path.abspath(args.package_file)
    if not os.path.isfile(path):
        sys.stderr.write(f"Error: File not found: {path}\n")
        return 1

    try:
        with open(path, "rb") as f:
            content = f.read()
        parse_ecosystem_pack_package(content)
        sys.stdout.write(f"Package {path} is valid (verified).\n")
        return 0
    except SolutionPackError as exc:
        sys.stderr.write(f"Package verification FAILED for {path}: {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"Unexpected error verifying {path}: {exc}\n")
        return 1


def _load_package(target: str) -> tuple[EcosystemPackPackage | None, str]:
    if os.path.isfile(target):
        try:
            with open(target, "rb") as f:
                content = f.read()
            return parse_ecosystem_pack_package(content), ""
        except Exception as exc:
            return None, f"Error reading ecosystem package file: {exc}"
    try:
        from .ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
        eco = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get(target)
        if eco is not None and eco.package is not None:
            return eco.package, ""
    except Exception:
        pass
    return None, f"File not found: {target}"


def run_inspect(args: argparse.Namespace) -> int:
    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    sys.stdout.write(f"Ecosystem Pack: {pkg.ecosystem_id} (version {pkg.version})\n")
    sys.stdout.write(f"Display Name: {pkg.display_name}\n")
    sys.stdout.write(f"Description: {pkg.description}\n")
    sys.stdout.write(f"Domain: {pkg.domain}\n")
    sys.stdout.write(f"Base Pack: {pkg.base_pack_id}\n")
    sys.stdout.write(f"Schema Version: {pkg.schema_version}\n")
    sys.stdout.write(f"Surfaces: {len(pkg.surfaces)}\n")
    for s in pkg.surfaces:
        ir = s.to_application_ir()
        entities_str = ", ".join(e.name for e in ir.entities)
        targets_str = ", ".join(s.verify_targets) or "none"
        sys.stdout.write(f"  - [{s.surface_kind}] {s.app_name} (slug: {s.slug})\n")
        sys.stdout.write(f"    Entities: {entities_str}\n")
        sys.stdout.write(f"    APIs: {len(ir.apis)}, Screens: {len(ir.screens)}\n")
        sys.stdout.write(f"    Targets: {targets_str}\n")
        sys.stdout.write(f"    IR SHA-256: {s.ir_sha256}\n")
    sys.stdout.write(f"Package Checksum: {pkg.package_sha256}\n")
    sys.stdout.write("Integrity: VERIFIED\n")
    return 0


def run_build(args: argparse.Namespace) -> int:
    path = os.path.abspath(args.package_file)
    if not os.path.isfile(path):
        sys.stderr.write(f"Error: File not found: {path}\n")
        return 1

    try:
        with open(path, "rb") as f:
            content = f.read()
        pkg = parse_ecosystem_pack_package(content)
    except SolutionPackError as exc:
        sys.stderr.write(f"Error loading package {path}: {exc}\n")
        return 1

    root_out = os.path.abspath(args.out_dir)
    os.makedirs(root_out, exist_ok=True)

    sys.stdout.write(f"Building ecosystem pack '{pkg.ecosystem_id}' ({len(pkg.surfaces)} surfaces) into {root_out}...\n")
    build_results = []
    used_slugs: dict[str, int] = {}

    for s in pkg.surfaces:
        ir = s.to_application_ir()
        base_slug = s.slug
        count = used_slugs.get(base_slug, 0)
        used_slugs[base_slug] = count + 1
        unique_slug = base_slug if count == 0 else f"{base_slug}-{count + 1}"
        target_dir = os.path.join(root_out, unique_slug)

        build_res = build_app_from_ir(
            ir,
            target_dir,
            author_name=args.author_name,
            author_email=args.author_email,
            prompt=pkg.description,
            overwrite=args.overwrite,
        )
        build_results.append((s, build_res))
        sys.stdout.write(f"  [OK] {s.surface_kind}: {s.app_name} -> {target_dir} (commit: {build_res.commit_sha[:8]}, {build_res.file_count} files)\n")

    sys.stdout.write(f"Materialized {len(build_results)} ecosystem applications under {root_out}\n")
    return 0


def run_catalog(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY

    packs = DEFAULT_ECOSYSTEM_PACK_REGISTRY.list_packs()
    if args.domain:
        packs = tuple(p for p in packs if p.domain == args.domain)

    if args.json:
        payload = {"ecosystems": [p.to_dict() for p in packs]}
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    sys.stdout.write(f"Registered Ecosystem Packs ({len(packs)}):\n\n")
    for p in packs:
        sys.stdout.write(f"• {p.display_name} ({p.ecosystem_id}@{p.version})\n")
        sys.stdout.write(f"  Domain:    {p.domain}\n")
        sys.stdout.write(f"  Base Pack: {p.base_pack_id}\n")
        sys.stdout.write(f"  Surfaces ({p.surface_count}):\n")
        for s in p.surfaces:
            targets_str = ", ".join(s.verify_targets) or "none"
            sys.stdout.write(f"    - [{s.surface_kind}] {s.app_name} (slug: {s.slug}, targets: {targets_str})\n")
        sys.stdout.write(f"  Checksum:  {p.package_sha256[:16]}...\n\n")
    return 0


def run_auth(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_auth import CrossAppAuthMatrix, synthesize_ecosystem_auth

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    auth = pkg.auth_contract
    if auth is None:
        auth = synthesize_ecosystem_auth(pkg.ecosystem_id, pkg.surfaces)

    matrix = CrossAppAuthMatrix.from_contract(auth)

    if args.json:
        payload = {
            "auth_contract": auth.to_dict(),
            "matrix": matrix.to_dict(),
        }
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    sys.stdout.write(f"Ecosystem Cross-App Auth: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Algorithm: {auth.jwt_algorithm}\n")
    sys.stdout.write(f"  Issuer:    {auth.issuer}\n")
    sys.stdout.write(f"  Audience:  {auth.audience}\n")
    sys.stdout.write(f"  TTL:       {auth.token_ttl_seconds}s\n")
    sys.stdout.write(f"  Roles ({len(auth.roles)}):\n")
    for r in auth.roles:
        sys.stdout.write(f"    - Role: {r.role_id} (surface: {r.surface_slug})\n")
        sys.stdout.write(f"      Allowed surfaces: {', '.join(r.allowed_surfaces)}\n")
        sys.stdout.write(f"      Actions:          {', '.join(r.authorized_actions)}\n")
        sys.stdout.write(f"      Permissions:      {', '.join(r.scope_permissions)}\n")
    return 0


def run_state(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_state import synthesize_ecosystem_state

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    state = pkg.state_binding
    if state is None:
        state = synthesize_ecosystem_state(pkg.ecosystem_id, pkg.surfaces)

    if args.json:
        sys.stdout.write(json.dumps(state.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    sys.stdout.write(f"Ecosystem Unified State: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Database: {state.database_strategy}\n")
    sys.stdout.write(f"  Shared Entities ({len(state.shared_entities)}):\n")
    for e in state.shared_entities:
        sys.stdout.write(f"    - {e.entity_name} (author: {e.authoritative_surface})\n")
        sys.stdout.write(f"      Readers: {', '.join(e.reading_surfaces)}\n")
        sys.stdout.write(f"      Writers: {', '.join(e.writing_surfaces)}\n")
    sys.stdout.write(f"  State Flows ({len(state.state_flows)}):\n")
    for f in state.state_flows:
        sys.stdout.write(f"    - {f.entity_name}.{f.state_field} (initial: {f.initial_state}, terminal: {', '.join(f.terminal_states)})\n")
        for t in f.transitions:
            sys.stdout.write(f"      [{t.from_state} -> {t.to_state}] by {', '.join(t.authorized_roles)} (action: {t.action_name})\n")
    sys.stdout.write(f"  Endpoints ({len(state.cross_app_endpoints)}):\n")
    for ep in state.cross_app_endpoints:
        sys.stdout.write(f"    - {ep.http_method} {ep.endpoint_path} -> consumers: {', '.join(ep.consuming_surfaces)}\n")
    return 0


def run_events(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_events import synthesize_ecosystem_events

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    events = pkg.event_bridge
    if events is None:
        events = synthesize_ecosystem_events(pkg.ecosystem_id, pkg.surfaces)

    if args.json:
        sys.stdout.write(json.dumps(events.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    sys.stdout.write(f"Ecosystem Event Bridge: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Signature Algorithm: {events.signature_algorithm} (header: {events.signature_header})\n")
    sys.stdout.write(f"  Idempotency Header:  {events.idempotency_header}\n")
    sys.stdout.write(f"  Secret Reference:    {events.secret_ref}\n")
    sys.stdout.write(f"  Supported Events ({len(events.supported_events)}):\n")
    for ev in events.supported_events:
        sys.stdout.write(f"    - {ev}\n")
    sys.stdout.write(f"  Webhook Subscriptions ({len(events.subscriptions)}):\n")
    for sub in events.subscriptions:
        active_str = "active" if sub.is_active else "disabled"
        retry = f"retries={sub.retry_policy.max_retries}, backoff={sub.retry_policy.backoff_seconds}s"
        sys.stdout.write(
            f"    - [{active_str}] {sub.source_surface} -> {sub.target_surface} ({sub.event_type}) "
            f"at {sub.webhook_path} ({retry})\n"
        )
    return 0


def run_telemetry(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_telemetry import synthesize_ecosystem_telemetry

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    telemetry = pkg.telemetry_contract
    if telemetry is None:
        telemetry = synthesize_ecosystem_telemetry(pkg.ecosystem_id, pkg.surfaces)

    if args.json:
        sys.stdout.write(json.dumps(telemetry.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    sys.stdout.write(f"Ecosystem Telemetry: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Trace ID Algorithm: {telemetry.trace_id_algorithm}\n")
    sys.stdout.write(f"  Span ID Algorithm:  {telemetry.span_id_algorithm}\n")
    sys.stdout.write(f"  Default Sampling Rate: {telemetry.default_sampling_policy.sampling_rate}\n")
    sys.stdout.write(f"  Export Format:      {telemetry.default_sampling_policy.export_format}\n")
    sys.stdout.write(f"  Propagation Header: {telemetry.default_sampling_policy.propagation_header}\n")
    sys.stdout.write(f"  Traced Surfaces ({len(telemetry.traced_surfaces)}):\n")
    for ts in telemetry.traced_surfaces:
        audit_str = "emits audit" if ts.emits_audit_events else "no audit"
        sys.stdout.write(f"    - [{ts.surface_slug}] {ts.display_name} ({audit_str})\n")
        sys.stdout.write(f"      Operations: {', '.join(ts.instrumented_operations[:5])}{', ...' if len(ts.instrumented_operations) > 5 else ''}\n")
    sys.stdout.write(f"  Cross-Surface Operations ({len(telemetry.cross_surface_operations)}):\n")
    for op in telemetry.cross_surface_operations:
        sys.stdout.write(f"    - {op}\n")
    sys.stdout.write(f"  Audit Actions ({len(telemetry.audit_actions)}):\n")
    for action in telemetry.audit_actions:
        sys.stdout.write(f"    - {action}\n")
    return 0


def run_deploy(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_deployment import synthesize_ecosystem_deployment

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    deployment = pkg.deployment_manifest
    if deployment is None:
        deployment = synthesize_ecosystem_deployment(
            pkg.ecosystem_id,
            pkg.surfaces,
            auth_contract=pkg.auth_contract,
            state_binding=pkg.state_binding,
        )

    if args.compose:
        sys.stdout.write(deployment.to_compose_yaml())
        sys.stdout.write("\n")
        return 0

    if args.json:
        sys.stdout.write(json.dumps(deployment.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    sys.stdout.write(f"Ecosystem Deployment: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Schema Version:     {deployment.schema_version}\n")
    sys.stdout.write(f"  Gateway Port:       {deployment.gateway_port}\n")
    sys.stdout.write(f"  Database Engine:    {deployment.database_spec.get('engine')} ({deployment.database_spec.get('database_name')})\n")
    sys.stdout.write(f"  Surfaces ({len(deployment.surfaces)}):\n")
    for s in deployment.surfaces:
        deps = f"deps: {', '.join(s.depends_on)}" if s.depends_on else "no deps"
        sys.stdout.write(f"    - [{s.surface_slug}] {s.app_name} ({s.runtime_target}) -> host:{s.host_port} container:{s.container_port} ({deps})\n")
    sys.stdout.write(f"  Gateway Routes ({len(deployment.gateway_routes)}):\n")
    for r in deployment.gateway_routes:
        sys.stdout.write(f"    - {r.path_prefix} -> {r.target_surface} (port {r.target_port})\n")
    return 0


def run_sync(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_sync import synthesize_ecosystem_sync

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    sync = pkg.sync_contract
    if sync is None:
        sync = synthesize_ecosystem_sync(
            pkg.ecosystem_id,
            pkg.surfaces,
            version=pkg.version,
        )

    if args.json:
        sys.stdout.write(json.dumps(sync.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    sys.stdout.write(f"Ecosystem Data Sync: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:          {sync.version}\n")
    sys.stdout.write(f"  Default Strategy: {sync.default_strategy}\n")
    sys.stdout.write(f"  Offline Queue:    {sync.offline_queue_max_size} mutations\n")
    sys.stdout.write(f"  Surface Policies ({len(sync.surface_policies)}):\n")
    for surf, policy in sorted(sync.surface_policies.items()):
        sys.stdout.write(f"    - {surf}: {policy}\n")
    sys.stdout.write(f"  Sync Entities ({len(sync.sync_entities)}):\n")
    for e in sync.sync_entities:
        auth = f" [SoT: {e.source_of_truth_surface}]" if e.source_of_truth_surface else ""
        sys.stdout.write(f"    - {e.entity_name} ({e.sync_mode}, {e.conflict_strategy}){auth}\n")
    return 0


def run_cicd(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_cicd import synthesize_ecosystem_cicd

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    cicd = pkg.cicd_contract
    if cicd is None:
        cicd = synthesize_ecosystem_cicd(
            pkg.ecosystem_id,
            pkg.surfaces,
        )

    if args.json:
        sys.stdout.write(json.dumps(cicd.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    if args.yaml:
        from .ecosystem_cicd import to_workflow_yaml
        yaml_text = to_workflow_yaml(cicd)
        sys.stdout.write(yaml_text)
        if not yaml_text.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    if args.simulate:
        from .ecosystem_cicd import EcosystemCICDEngine
        engine = EcosystemCICDEngine(cicd)
        res = engine.simulate_pipeline_run()
        sys.stdout.write(f"CI/CD Simulation: {res['status'].upper()}\n")
        sys.stdout.write(f"  Total Duration: {res['total_duration_ms'] / 1000.0:.2f}s\n")
        sys.stdout.write(f"  Executed Jobs ({len(res['jobs'])}):\n")
        for j in res["jobs"]:
            sys.stdout.write(f"    - {j['job_id']} ({j['runs_on']}): {j['status']} ({len(j['steps'])} steps)\n")
        return 0

    sys.stdout.write(f"Ecosystem CI/CD: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:   {cicd.version}\n")
    sys.stdout.write(f"  Workflows: {len(cicd.workflows)}\n")
    for wf in cicd.workflows:
        sys.stdout.write(f"  Workflow '{wf.workflow_id}' ({wf.name}):\n")
        sys.stdout.write(f"    Triggers: {', '.join(wf.triggers)}\n")
        sys.stdout.write(f"    Jobs ({len(wf.jobs)}):\n")
        for j in wf.jobs:
            needs_str = f" [needs: {', '.join(j.needs)}]" if j.needs else ""
            sys.stdout.write(f"      - {j.job_id} ({j.name}, runner: {j.runs_on}){needs_str}\n")
            for st in j.steps:
                action = st.uses or st.run or "step"
                sys.stdout.write(f"          * {st.name} ({action})\n")
    return 0


def run_verify_suite(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_verification import EcosystemVerificationEngine, synthesize_ecosystem_verification

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    vc = pkg.verification_contract
    if vc is None:
        vc = synthesize_ecosystem_verification(
            pkg.ecosystem_id,
            pkg.surfaces,
            version=pkg.version,
        )

    if args.json:
        sys.stdout.write(json.dumps(vc.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    if args.simulate:
        engine = EcosystemVerificationEngine(vc)
        res = engine.simulate_full_verification()
        summary = res["summary"]
        status = res["status"].upper()
        sys.stdout.write(f"Verification Simulation: {status}\n")
        sys.stdout.write(f"  Probes:      {summary['probe_pass']} pass / {summary['probe_fail']} fail (total {summary['total_probes']})\n")
        sys.stdout.write(f"  Smoke Tests: {summary['smoke_pass']} pass / {summary['smoke_fail']} fail (total {summary['total_smoke_tests']})\n")
        sys.stdout.write(f"  Canary Rules:{summary['canary_pass']} pass / {summary['canary_fail']} fail (total {summary['total_canary_rules']})\n")
        if summary["probe_fail"] + summary["smoke_fail"] + summary["canary_fail"] == 0:
            sys.stdout.write("  All checks PASSED (dry-run)\n")
        else:
            sys.stdout.write("  Some checks FAILED\n")
        return 0

    sys.stdout.write(f"Ecosystem Verification Suite: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:      {vc.version}\n")
    sys.stdout.write(f"  Digest:       {vc.digest()[:16]}...\n")
    sys.stdout.write(f"  Probes ({len(vc.probes)}):\n")
    for p in vc.probes:
        tags_str = ", ".join(p.tags) or "none"
        sys.stdout.write(f"    - [{p.surface_slug}] {p.method} {p.endpoint} -> {p.expected_status} (timeout: {p.timeout_seconds}s, tags: {tags_str})\n")
    sys.stdout.write(f"  Smoke Tests ({len(vc.smoke_tests)}):\n")
    for t in vc.smoke_tests:
        sys.stdout.write(f"    - [{t.surface_slug}] {t.name} ({t.category}, {len(t.steps)} steps, expected: {t.expected_outcome})\n")
    sys.stdout.write(f"  Canary Rules ({len(vc.canary_rules)}):\n")
    for r in vc.canary_rules:
        surfaces_str = ", ".join(r.surfaces_covered)
        sys.stdout.write(f"    - [{r.severity.upper()}] {r.rule_id}\n")
        sys.stdout.write(f"      Trigger:   {r.trigger}\n")
        sys.stdout.write(f"      Assertion: {r.assertion}\n")
        sys.stdout.write(f"      Surfaces:  {surfaces_str}\n")
    return 0


def run_recovery(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_recovery import EcosystemRecoveryEngine, synthesize_ecosystem_recovery

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    rc = pkg.recovery_contract
    if rc is None:
        rc = synthesize_ecosystem_recovery(
            pkg.ecosystem_id,
            pkg.surfaces,
            version=pkg.version,
        )

    if args.json:
        sys.stdout.write(json.dumps(rc.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    if args.simulate:
        engine = EcosystemRecoveryEngine(rc)
        res = engine.simulate_full_dr_exercise()
        summary = res["summary"]
        status = res["status"].upper()
        sys.stdout.write(f"Disaster Recovery Simulation: {status}\n")
        sys.stdout.write(f"OVERALL STATUS: {status}\n")
        sys.stdout.write(f"  Snapshots: {summary['snapshots_pass']} pass / {summary['snapshots_fail']} fail (total {summary['total_backup_targets']})\n")
        sys.stdout.write(f"  Recovery:  {summary['steps_pass']} pass / {summary['steps_fail']} fail (total {summary['total_recovery_steps']})\n")
        sys.stdout.write(f"  Rollback:  {summary['triggers_pass']} pass / {summary['triggers_fail']} fail (total {summary['total_rollback_triggers']})\n")
        if summary["snapshots_fail"] + summary["steps_fail"] + summary["triggers_fail"] == 0:
            sys.stdout.write("  All disaster recovery checks PASSED (dry-run)\n")
        else:
            sys.stdout.write("  Some disaster recovery checks FAILED\n")
        return 0

    sys.stdout.write(f"Disaster Recovery Contract: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:          {rc.version}\n")
    sys.stdout.write(f"  Digest:           {rc.digest()[:16]}...\n")
    sys.stdout.write(f"  Backup Targets: ({len(rc.backup_targets)}):\n")
    for t in rc.backup_targets:
        enc = "encrypted" if t.encryption_required else "unencrypted"
        sys.stdout.write(f"    - [{t.surface_slug}] {t.target_id} ({t.target_kind}, {t.frequency}, retention: {t.retention_days}d, {enc})\n")
        sys.stdout.write(f"      URI: {t.storage_uri}\n")
    sys.stdout.write(f"  Recovery Steps: ({len(rc.recovery_steps)}):\n")
    for s in rc.recovery_steps:
        crit = "CRITICAL" if s.critical else "OPTIONAL"
        sys.stdout.write(f"    {s.sequence_order}. [{s.surface_slug}] {s.action} (target: {s.target or 'none'}, timeout: {s.timeout_seconds}s, {crit})\n")
        if s.description:
            sys.stdout.write(f"       {s.description}\n")
    sys.stdout.write(f"  Rollback Triggers: ({len(rc.rollback_triggers)}):\n")
    for r in rc.rollback_triggers:
        sys.stdout.write(f"    - [{r.severity.upper()}] {r.trigger_id}: if {r.condition} ({r.threshold}) -> {r.action}\n")
    return 0


def run_capacity(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_capacity import EcosystemCapacityEngine, synthesize_ecosystem_capacity

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    cap = pkg.capacity_contract
    if cap is None:
        cap = synthesize_ecosystem_capacity(
            pkg.ecosystem_id,
            pkg.surfaces,
            version=pkg.version,
        )

    if args.json:
        sys.stdout.write(json.dumps(cap.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    if args.simulate:
        engine = EcosystemCapacityEngine(cap)
        tier = getattr(args, "tier", "base") or "base"
        rep = engine.simulate_workload_tier(tier=tier)
        status = rep.status.upper()
        sys.stdout.write(f"Capacity Planning Simulation ({tier}): {status}\n")
        sys.stdout.write(f"OVERALL STATUS: {status}\n")
        sys.stdout.write(f"  Monthly Requests: {rep.total_monthly_requests:,}\n")
        sys.stdout.write(f"  Monthly Cost:     ${rep.total_monthly_cost_usd:.2f} (Budget: ${rep.monthly_budget_limit_usd:.2f})\n")
        sys.stdout.write(f"  Within Budget:    {'YES' if rep.within_budget else 'NO'}\n")
        sys.stdout.write(f"  Surfaces:         {len(rep.surface_projections)}\n")
        for p in rep.surface_projections:
            sys.stdout.write(f"    - [{p.surface_slug}] replicas: {p.required_replicas}, CPU: {p.estimated_cpu_cores:.1f}, Mem: {p.estimated_memory_mb}MB, Est: ${p.estimated_monthly_cost_usd:.2f}/mo\n")
            for v in p.quota_violations:
                sys.stdout.write(f"      * VIOLATION: {v}\n")
        sys.stdout.write(f"  Summary:          {rep.summary}\n")
        return 0

    sys.stdout.write(f"Capacity Contract: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:          {cap.version}\n")
    sys.stdout.write(f"  Digest:           {cap.digest()[:16]}...\n")
    sys.stdout.write(f"  Monthly Budget:   ${cap.monthly_budget_limit_usd:.2f}\n")
    sys.stdout.write(f"  Surface Capacities ({len(cap.surface_capacities)}):\n")
    for s in cap.surface_capacities:
        sys.stdout.write(f"    - [{s.surface_slug}] {s.surface_kind} (replicas: {s.min_replicas}-{s.max_replicas}, CPU target: {s.target_cpu_utilization_pct}%, Mem target: {s.target_memory_utilization_pct}%)\n")
    sys.stdout.write(f"  Resource Quotas ({len(cap.resource_quotas)}):\n")
    for q in cap.resource_quotas:
        sys.stdout.write(f"    - [{q.surface_slug}] {q.resource_kind}: limit {q.limit_value} {q.unit} (burst: {q.burst_limit_value} {q.unit}, action: {q.enforcement_action})\n")
    sys.stdout.write(f"  Cost Models ({len(cap.cost_models)}):\n")
    for m in cap.cost_models:
        sys.stdout.write(f"    - [{m.surface_slug}] base: ${m.base_monthly_cost_usd:.2f}/mo, marginal/1k: ${m.marginal_cost_per_1k_requests_usd:.4f} ({m.cost_tier})\n")
    return 0


def run_alerting(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_alerting import EcosystemAlertingEngine, synthesize_ecosystem_alerting

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    alerting = pkg.alerting_contract
    if alerting is None:
        alerting = synthesize_ecosystem_alerting(
            pkg.ecosystem_id,
            pkg.surfaces,
            version=pkg.version,
        )

    if args.json:
        sys.stdout.write(json.dumps(alerting.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    if args.simulate:
        engine = EcosystemAlertingEngine(alerting)
        scenario = getattr(args, "scenario", "api_error_spike") or "api_error_spike"
        rep = engine.simulate_incident(scenario=scenario)
        status = rep.status.upper()
        sys.stdout.write(f"Incident Simulation ({scenario}): {status}\n")
        sys.stdout.write(f"OVERALL STATUS: {status}\n")
        sys.stdout.write(f"  Trigger:          {rep.alert_trigger.rule_id} ({rep.alert_trigger.severity})\n")
        sys.stdout.write(f"  Metric:           {rep.alert_trigger.metric_name} = {rep.alert_trigger.metric_value} ({rep.alert_trigger.condition} {rep.alert_trigger.threshold})\n")
        if rep.runbook_report:
            sys.stdout.write(f"  Runbook:          {rep.runbook_report.title} ({rep.runbook_report.status})\n")
            sys.stdout.write(f"    - Steps:        {rep.runbook_report.total_steps} ({rep.runbook_report.automated_steps} auto, {rep.runbook_report.manual_steps} manual)\n")
            for step in rep.runbook_report.step_executions:
                sys.stdout.write(f"      * [{step.order}] {step.action} -> {step.status} ({step.output})\n")
        sys.stdout.write(f"  Escalation:       Tier {rep.escalation_tier_reached} ({', '.join(rep.active_responder_channels)})\n")
        sys.stdout.write(f"  Summary:          {rep.summary}\n")
        return 0

    sys.stdout.write(f"Alerting Contract: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:          {alerting.version}\n")
    sys.stdout.write(f"  Digest:           {alerting.digest()[:16]}...\n")
    sys.stdout.write(f"  Alert Rules ({len(alerting.alert_rules)}):\n")
    for r in alerting.alert_rules:
        sys.stdout.write(f"    - [{r.surface_slug}] {r.rule_id} ({r.severity}): {r.metric_name} {r.condition} {r.threshold} -> runbook: {r.runbook_id}\n")
    sys.stdout.write(f"  Incident Runbooks ({len(alerting.runbooks)}):\n")
    for rb in alerting.runbooks:
        sys.stdout.write(f"    - [{rb.runbook_id}] {rb.title} ({len(rb.steps)} steps, policy: {rb.escalation_policy_id})\n")
    sys.stdout.write(f"  Escalation Policies ({len(alerting.escalation_policies)}):\n")
    for ep in alerting.escalation_policies:
        sys.stdout.write(f"    - [{ep.policy_id}] {ep.name} ({len(ep.tiers)} tiers)\n")
    return 0


def run_sla(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_sla import EcosystemSLAEngine, synthesize_ecosystem_sla

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    sla_contract = pkg.sla_contract
    if sla_contract is None:
        sla_contract = synthesize_ecosystem_sla(
            pkg.ecosystem_id,
            pkg.surfaces,
            version=pkg.version,
        )

    if args.json:
        sys.stdout.write(json.dumps(sla_contract.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    if args.simulate:
        engine = EcosystemSLAEngine(sla_contract)
        scenario = getattr(args, "scenario", "normal_operations") or "normal_operations"
        rep = engine.simulate_sla_compliance(scenario=scenario)
        status = rep.status.upper()
        sys.stdout.write(f"SLA Compliance Simulation ({scenario}): {status}\n")
        sys.stdout.write(f"OVERALL STATUS: {status}\n")
        sys.stdout.write(f"  SLIs Evaluated:   {len(rep.sli_evaluations)}\n")
        for sli in rep.sli_evaluations:
            pass_str = "PASS" if sli.is_good else "FAIL"
            sys.stdout.write(f"    - [{sli.surface_slug}] {sli.sli_id}: {sli.observed_value:.2f}{sli.unit} (threshold: {sli.threshold}{sli.unit}) -> {pass_str}\n")
        sys.stdout.write(f"  Burn Reports:     {len(rep.burn_reports)}\n")
        for br in rep.burn_reports:
            sys.stdout.write(f"    - [{br.slo_id}]: remaining={br.remaining_pct:.4f}% burn_rate_1h={br.burn_rate_1h:.1f}x status={br.status}\n")
        sys.stdout.write(f"  Financial Credits: {rep.total_financial_credit_pct:.1f}%\n")
        sys.stdout.write(f"  Breached SLOs ({len(rep.breached_slos)}): {', '.join(rep.breached_slos) or 'None'}\n")
        sys.stdout.write(f"  Breached SLAs ({len(rep.breached_slas)}): {', '.join(rep.breached_slas) or 'None'}\n")
        sys.stdout.write(f"  Summary:          {rep.summary}\n")
        return 0

    sys.stdout.write(f"SLA Contract: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:          {sla_contract.version}\n")
    sys.stdout.write(f"  Digest:           {sla_contract.digest()[:16]}...\n")
    sys.stdout.write(f"  SLIs ({len(sla_contract.slis)}):\n")
    for sli in sla_contract.slis:
        sys.stdout.write(f"    - [{sli.surface_slug}] {sli.sli_id} ({sli.kind}): {sli.metric_name} threshold {sli.threshold}{sli.unit}\n")
    sys.stdout.write(f"  SLOs ({len(sla_contract.slos)}):\n")
    for slo in sla_contract.slos:
        sys.stdout.write(f"    - [{slo.surface_slug}] {slo.slo_id} ({slo.tier}): {slo.target_percentage}% over {slo.rolling_window_days}d\n")
    sys.stdout.write(f"  Error Budgets ({len(sla_contract.error_budgets)}):\n")
    for eb in sla_contract.error_budgets:
        sys.stdout.write(f"    - [{eb.slo_id}]: total={eb.total_budget_percentage}% remaining={eb.remaining_budget_percentage}%\n")
    sys.stdout.write(f"  SLAs ({len(sla_contract.slas)}):\n")
    for sla in sla_contract.slas:
        sys.stdout.write(f"    - [{sla.sla_id}] {sla.customer_tier} ({sla.surface_slug}): {sla.availability_target_pct}% uptime, {sla.financial_credit_pct}% credit\n")
    return 0


def run_governance(args: argparse.Namespace) -> int:
    import json
    from .ecosystem_governance import EcosystemGovernanceEngine, synthesize_ecosystem_governance

    pkg, err = _load_package(args.package_file)
    if pkg is None:
        sys.stderr.write(f"Error: {err}\n")
        return 1

    gov_contract = pkg.governance_contract
    if gov_contract is None:
        gov_contract = synthesize_ecosystem_governance(
            pkg.ecosystem_id,
            pkg.surfaces,
            version=pkg.version,
        )

    if args.json:
        sys.stdout.write(json.dumps(gov_contract.to_dict(), indent=2, sort_keys=True))
        sys.stdout.write("\n")
        return 0

    if args.simulate:
        engine = EcosystemGovernanceEngine(gov_contract)
        scenario = getattr(args, "scenario", "standard_audit") or "standard_audit"
        rep = engine.simulate_compliance_audit(scenario=scenario)
        status = rep.audit_status.upper()
        sys.stdout.write(f"Governance Audit Simulation ({scenario}): {status}\n")
        sys.stdout.write(f"OVERALL STATUS: {status}\n")
        sys.stdout.write(f"  Standards Tested: {', '.join(rep.standards_evaluated)}\n")
        sys.stdout.write(f"  Controls Tested:  {rep.total_controls_tested} (Passed: {rep.passed_controls}, Failed: {rep.failed_controls})\n")
        sys.stdout.write(f"  Risk Score:       {rep.risk_score:.2f}\n")
        sys.stdout.write(f"  Findings ({len(rep.findings)}):\n")
        for f in rep.findings:
            sys.stdout.write(f"    - [{f.get('severity', 'info').upper()}] {f.get('finding_id')}: {f.get('title')} - {f.get('description')}\n")
        sys.stdout.write(f"  Recommended Actions ({len(rep.recommended_actions)}):\n")
        for act in rep.recommended_actions:
            sys.stdout.write(f"    - {act}\n")
        return 0

    sys.stdout.write(f"Governance Contract: {pkg.display_name} ({pkg.ecosystem_id})\n")
    sys.stdout.write(f"  Version:          {gov_contract.version}\n")
    sys.stdout.write(f"  Digest:           {gov_contract.digest()[:16]}...\n")
    sys.stdout.write(f"  Standards ({len(gov_contract.standards)}):\n")
    for std in gov_contract.standards:
        sys.stdout.write(f"    - {std.name} ({std.standard_id} v{std.version}): {len(std.mandatory_controls)} mandatory controls\n")
    sys.stdout.write(f"  Policies ({len(gov_contract.policies)}):\n")
    for pol in gov_contract.policies:
        sys.stdout.write(f"    - [{pol.surface_slug}] {pol.policy_id} ({pol.severity}/{pol.enforcement_mode}): {pol.control_id} - {pol.description}\n")
    sys.stdout.write(f"  Data Classifications ({len(gov_contract.classifications)}):\n")
    for cls in gov_contract.classifications:
        sys.stdout.write(f"    - [{cls.surface_slug}] {cls.entity_name}.{cls.field_name}: {cls.classification_level} (encryption: {cls.encryption_required})\n")
    sys.stdout.write(f"  Audit Evidence Items ({len(gov_contract.evidence_items)}):\n")
    for ev in gov_contract.evidence_items:
        sys.stdout.write(f"    - [{ev.surface_slug}] {ev.evidence_id}: {ev.control_id} ({ev.collector_kind}) -> {ev.status}\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "synthesize":
        return run_synthesize(args)
    if args.subcommand == "verify":
        return run_verify(args)
    if args.subcommand == "inspect":
        return run_inspect(args)
    if args.subcommand == "build":
        return run_build(args)
    if args.subcommand == "catalog":
        return run_catalog(args)
    if args.subcommand == "auth":
        return run_auth(args)
    if args.subcommand == "state":
        return run_state(args)
    if args.subcommand == "events":
        return run_events(args)
    if args.subcommand == "telemetry":
        return run_telemetry(args)
    if args.subcommand == "deploy":
        return run_deploy(args)
    if args.subcommand == "sync":
        return run_sync(args)
    if args.subcommand == "cicd":
        return run_cicd(args)
    if args.subcommand == "verify-suite":
        return run_verify_suite(args)
    if args.subcommand == "recovery":
        return run_recovery(args)
    if args.subcommand == "capacity":
        return run_capacity(args)
    if args.subcommand == "alerting":
        return run_alerting(args)
    if args.subcommand == "sla":
        return run_sla(args)
    if args.subcommand == "governance":
        return run_governance(args)
    sys.stderr.write(f"Unknown subcommand: {args.subcommand}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

