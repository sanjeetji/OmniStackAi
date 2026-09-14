"""CLI to build a Solution Pack project into an owned Git repository (R-440).

Deterministic disk work (no model/network).
Usage:
    python3 -m omnistackai_agent_engine.solution_packs.build_cli [pack-id-or-manifest-path] [out-dir]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Sequence, TextIO

from .builder import build_solution_pack_project
from .manifest import parse_solution_pack_manifest
from .registry import DEFAULT_SOLUTION_PACK_REGISTRY

_DEFAULT_AUTHOR_NAME = "sanjeetji"
_DEFAULT_AUTHOR_EMAIL = "sk698166@gmail.com"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a Solution Pack project into an owned Git repository"
    )
    parser.add_argument(
        "source",
        nargs="?",
        default="minimal-blog",
        help="Registered pack ID (e.g. minimal-blog) or path to a SolutionPackManifest JSON file",
    )
    parser.add_argument(
        "out_dir",
        nargs="?",
        default="",
        help="Target output directory for the Git repository (default: temp dir)",
    )
    parser.add_argument(
        "--author-name",
        default=_DEFAULT_AUTHOR_NAME,
        help=f"Git commit author name (default: {_DEFAULT_AUTHOR_NAME})",
    )
    parser.add_argument(
        "--author-email",
        default=_DEFAULT_AUTHOR_EMAIL,
        help=f"Git commit author email (default: {_DEFAULT_AUTHOR_EMAIL})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite target directory if it already exists",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = _parser().parse_args(argv)
    output = stdout or sys.stdout

    source_arg = args.source.strip()
    out_dir = (
        args.out_dir.strip()
        or os.environ.get("OMNISTACKAI_APP_OUT_DIR", "").strip()
        or tempfile.mkdtemp(prefix="omnistackai-pack-")
    )

    source_path = Path(source_arg)
    if source_path.is_file():
        manifest = parse_solution_pack_manifest(source_path.read_text(encoding="utf-8"))
        result = build_solution_pack_project(
            manifest,
            out_dir,
            author_name=args.author_name,
            author_email=args.author_email,
            overwrite=args.overwrite or True,
        )
    else:
        pack = DEFAULT_SOLUTION_PACK_REGISTRY.get(source_arg)
        if pack is None:
            print(f"Error: Unknown solution pack or file '{source_arg}'", file=sys.stderr)
            return 2
        # Build base pack by creating a minimal manifest without changes
        from .manifest import create_solution_pack_manifest
        rec = DEFAULT_SOLUTION_PACK_REGISTRY.recommend(
            pack.domains[0],
            required_targets=pack.targets,
        )
        manifest = create_solution_pack_manifest(rec, changes=())
        result = build_solution_pack_project(
            manifest,
            out_dir,
            author_name=args.author_name,
            author_email=args.author_email,
            overwrite=args.overwrite or True,
        )

    print(f"\n=== OmniStackAI Solution Pack Project Builder ===", file=output)
    print(f"Pack:         {result.pack_id} v{result.pack_version}", file=output)
    print(f"App Name:     {result.app_name}", file=output)
    print(f"Target Dir:   {result.target_dir}", file=output)
    print(f"File Count:   {result.file_count}", file=output)
    print(f"Commit SHA:   {result.commit_sha[:12]} (author: {args.author_name})", file=output)
    print(f"Verify Targets: {', '.join(result.verify_targets)}", file=output)
    print("\n--- SolutionPackBuildResult (JSON) ---", file=output)
    print(result.to_json(), file=output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
