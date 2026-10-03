"""PC-122: scripts/benchmark.sh - build the benchmark prompts end to end and score them.

    scripts/benchmark.sh                         # the quick set (8 prompts), build + preview
    scripts/benchmark.sh --set full --design     # every prompt, pages designed by the model
    scripts/benchmark.sh --only clinic,blog      # chosen cases
    scripts/benchmark.sh --no-preview            # plans and code only (no database, no browser)

Results go to ~/.omnistackai/benchmark/<run>/ (report.md with screenshots, report.json), compared
with the previous run there. It calls real models: opt-in, never part of task verify.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .cases import SETS, select
from .run import main_async


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="benchmark", description=__doc__.split("\n\n")[0])
    parser.add_argument("--set", default="quick", choices=sorted(SETS))
    parser.add_argument("--only", default="", help="comma-separated case ids")
    parser.add_argument("--design", action="store_true", help="let the model design the pages, as the console does")
    parser.add_argument("--no-preview", action="store_true", help="skip running the projects")
    parser.add_argument("--review", action="store_true", help="score every page's look from its screenshots (PC-130)")
    parser.add_argument("--out", default=os.environ.get("OMNISTACKAI_BENCHMARK_DIR", str(Path.home() / ".omnistackai" / "benchmark")))
    parser.add_argument("--baseline", default="", help="a report.json to compare with (default: the previous run)")
    parser.add_argument("--list", action="store_true", help="print the cases and exit")
    parser.add_argument("--rescore", default="", help="score a saved run folder again with the current rules")
    args = parser.parse_args(argv)
    if args.rescore:
        from .run import rescore

        report = rescore(Path(args.rescore).expanduser())
        print(f"mean score {report['mean']} (rescored)")
        return 0
    cases = select(args.set, [c for c in args.only.split(",") if c] or None)
    if args.list:
        for case in cases:
            print(f"{case.id:22} {case.prompt}")
        return 0
    # Type-check the way the Studio does (scripts/omnistack.sh warms this cache): without it every
    # web app is reported as not type-checked, and a page using a component it never imported passes.
    cache = Path.home() / ".omnistackai" / "web-typecheck" / "node_modules"
    if not os.environ.get("OMNISTACKAI_WEB_NODE_MODULES") and (cache / ".bin" / "tsc").exists():
        os.environ["OMNISTACKAI_WEB_NODE_MODULES"] = str(cache)
    if not os.environ.get("OMNISTACKAI_WEB_NODE_MODULES"):
        print("note: no type-check cache - run ./scripts/omnistack.sh up once; web apps will count as not type-checked")
    # PC-126: remember which providers are out (a spent quota) across cases, as the Studio does.
    from ..model_gateway.health import DEFAULT_FILE, PATH_ENV

    os.environ.setdefault(PATH_ENV, str(DEFAULT_FILE))
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    report = main_async(cases, out, design=args.design, preview=not args.no_preview,
                        baseline=Path(args.baseline) if args.baseline else None, review=args.review)
    print(f"\nmean score {report['mean']} - {out / report['run'] / 'report.md'}")
    regressions = report["comparison"].get("regressions") or []
    for line in regressions:
        print(f"REGRESSION {line}")
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
