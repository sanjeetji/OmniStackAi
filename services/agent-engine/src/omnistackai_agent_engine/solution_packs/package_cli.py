"""CLI for Solution Pack packaging, export, verification, and inspection (R-443)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO

from .package import SolutionPackPackage, parse_solution_pack_package, verify_package
from .registry import DEFAULT_SOLUTION_PACK_REGISTRY, SolutionPackError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="solution-pack-package",
        description="Package, export, verify, and inspect OmniStackAI Solution Packs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export subcommand
    export_parser = subparsers.add_parser(
        "export",
        help="Export a registered Solution Pack to a standalone .pack.json bundle",
    )
    export_parser.add_argument(
        "--pack",
        required=True,
        help="Pack ID to export (e.g. minimal-blog, rideshare-favourites)",
    )
    export_parser.add_argument(
        "--version",
        default=None,
        help="Exact semantic version (defaults to newest stable registered version)",
    )
    export_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (defaults to stdout if omitted)",
    )
    export_parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation spaces (default: 2)",
    )

    # verify subcommand
    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify cryptographic checksum and semantic validity of a .pack.json bundle",
    )
    verify_parser.add_argument(
        "package_file",
        help="Path to the .pack.json file to verify",
    )

    # inspect subcommand
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect metadata and contents of a .pack.json bundle",
    )
    inspect_parser.add_argument(
        "package_file",
        help="Path to the .pack.json file to inspect",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = _parser()

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1

    try:
        if args.command == "export":
            pack = DEFAULT_SOLUTION_PACK_REGISTRY.get(args.pack, args.version)
            if pack is None:
                version_str = f"@{args.version}" if args.version else ""
                print(
                    f"Error: unknown Solution Pack '{args.pack}{version_str}'",
                    file=err,
                )
                return 1

            pkg = SolutionPackPackage.from_solution_pack(pack)
            json_blob = pkg.to_json(indent=args.indent)

            if args.output and args.output != "-":
                out_path = Path(args.output)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json_blob, encoding="utf-8")
                print(
                    f"Exported Solution Pack {pkg.pack_id}@{pkg.version} to {out_path}",
                    file=out,
                )
            else:
                print(json_blob, file=out)
            return 0

        elif args.command == "verify":
            pkg_path = Path(args.package_file)
            if not pkg_path.is_file():
                print(f"Error: package file '{pkg_path}' does not exist", file=err)
                return 1
            content = pkg_path.read_text(encoding="utf-8")
            valid, reason = verify_package(content)
            if valid:
                print(f"SUCCESS: {reason}", file=out)
                return 0
            else:
                print(f"INVALID: {reason}", file=err)
                return 1

        elif args.command == "inspect":
            pkg_path = Path(args.package_file)
            if not pkg_path.is_file():
                print(f"Error: package file '{pkg_path}' does not exist", file=err)
                return 1
            content = pkg_path.read_text(encoding="utf-8")
            pkg = parse_solution_pack_package(content, verify_integrity=True)
            ir = pkg.to_application_ir()

            print(f"=== OmniStackAI Solution Pack Package ===", file=out)
            print(f"Pack ID:       {pkg.pack_id}@{pkg.version}", file=out)
            print(f"Display Name:  {pkg.display_name}", file=out)
            print(f"Description:   {pkg.description}", file=out)
            print(f"Domains:       {', '.join(pkg.domains)}", file=out)
            print(f"Capabilities:  {', '.join(pkg.capabilities)}", file=out)
            print(f"Targets:       {', '.join(pkg.targets)}", file=out)
            print(f"Verify Target: {', '.join(pkg.verify_targets)}", file=out)
            print(f"IR SHA-256:    {pkg.ir_sha256}", file=out)
            print(f"Pkg SHA-256:   {pkg.package_sha256}", file=out)
            print(f"\n--- Application IR Summary ---", file=out)
            print(f"Entities ({len(ir.entities)}):  {', '.join(e.name for e in ir.entities)}", file=out)
            print(f"APIs ({len(ir.apis)}):          {len(ir.apis)} endpoints", file=out)
            print(f"Screens ({len(ir.screens)}):    {', '.join(s.id for s in ir.screens)}", file=out)
            print(f"Roles:          {', '.join(r.id for r in ir.roles)}", file=out)
            return 0

        else:
            parser.print_help(err)
            return 1

    except SolutionPackError as exc:
        print(f"SolutionPackError: {exc}", file=err)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=err)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
