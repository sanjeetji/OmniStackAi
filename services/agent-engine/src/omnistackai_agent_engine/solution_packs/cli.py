"""Deterministic Solution Pack registry inspection CLI (no build/model/live execution)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence, TextIO

from .registry import DEFAULT_SOLUTION_PACK_REGISTRY


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect registered OmniStackAI Solution Packs")
    parser.add_argument("--domain", help="Select one exact domain instead of listing all packs")
    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Required capability (repeatable; requires --domain)",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = _parser().parse_args(argv)
    output = stdout or sys.stdout
    if args.capability and not args.domain:
        _parser().error("--capability requires --domain")

    if args.domain:
        capabilities = tuple(sorted(args.capability))
        selected = DEFAULT_SOLUTION_PACK_REGISTRY.select(
            args.domain,
            required_capabilities=capabilities,
        )
        payload: dict[str, object] = {
            "query": {
                "domain": args.domain,
                "required_capabilities": list(capabilities),
            },
            "selection": None if selected is None else selected.to_dict(),
        }
    else:
        payload = DEFAULT_SOLUTION_PACK_REGISTRY.to_dict()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), file=output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
