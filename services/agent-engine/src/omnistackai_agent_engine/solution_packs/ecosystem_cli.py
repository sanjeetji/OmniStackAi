"""Command-line interface for Solution Pack Ecosystem Pack operations (R-444).

Supports:
- synthesize: Synthesize a multi-surface ecosystem pack from a Solution Pack
- verify: Verify integrity and Application IR validity of an ecosystem package file
- inspect: Pretty-print ecosystem package metadata and surfaces
- build: Materialize all surfaces of an ecosystem package as separate Git repos
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
    sys.stderr.write(f"Unknown subcommand: {args.subcommand}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
