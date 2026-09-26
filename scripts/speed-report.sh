#!/usr/bin/env bash
# PC-084: how fast builds really are, from the timings every build records.
#
#   scripts/speed-report.sh            # all workspaces under ~/.omnistackai/workspaces
#   OMNISTACKAI_WORKSPACES=/path scripts/speed-report.sh
#
# Reads each workspace's state.json (written by the Studio after every build) and prints the median
# and 90th percentile per stage, and how many builds met the targets: prompt -> running app under
# 90 s (the Vibe promise). Offline; reads files only.
set -euo pipefail
root="${OMNISTACKAI_WORKSPACES:-$HOME/.omnistackai/workspaces}"
python3 - "$root" <<'PY'
import json, pathlib, statistics, sys

root = pathlib.Path(sys.argv[1])
rows = []
for state in sorted(root.glob("*/state.json")):
    try:
        timings = json.loads(state.read_text()).get("timings") or {}
    except (OSError, ValueError):
        continue
    if timings.get("total"):
        rows.append(timings)
if not rows:
    print(f"No timed builds under {root} yet (timings are recorded from PC-084 on).")
    raise SystemExit(0)

def pct(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(q * (len(values) - 1))))]

print(f"{len(rows)} timed builds in {root}\n")
print(f"{'stage':<12}{'median s':>10}{'p90 s':>10}")
for stage in ("plan", "assemble", "repository", "verify", "preview", "total"):
    values = [r[stage] for r in rows if stage in r]
    if values:
        print(f"{stage:<12}{statistics.median(values):>10.1f}{pct(values, 0.9):>10.1f}")
met = sum(1 for r in rows if r["total"] < 90)
print(f"\nprompt -> running app under 90 s: {met}/{len(rows)} builds")
PY
