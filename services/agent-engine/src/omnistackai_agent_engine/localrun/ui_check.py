"""PC-106: the UI check runs by itself once a preview is ready.

PC-101 built `scripts/ui-check.mjs` (every page at phone and desktop width: overflow, console
errors, failed requests, broken images, contrast) and ran it by hand. Now the runner starts it in
the background after a preview's pages are warmed, on the apps' own ports (their API calls routed
straight to the API), and keeps the result beside the project's logs:

    <workspace>/logs/ui-check/status.json    running | passed | failed | skipped, counts, first problems
    <workspace>/logs/ui-check/report.md      every page, with screenshots in shots/

It asks no model anything. It needs Node, Chrome and `playwright-core`, which is never a dependency
of the platform or of a generated app: `scripts/omnistack.sh` installs it once into
~/.omnistackai/ui-check (as it does the type-check caches) when Chrome is present. Without them the
check is skipped and the status says why. OMNISTACKAI_UI_CHECK=0 turns it off.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from .plan import RunPlan

_REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT = _REPO_ROOT / "scripts" / "ui-check.mjs"
_CHROME = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)
_TIMEOUT_SECONDS = 15 * 60
_FIRST_PROBLEMS = 5


def playwright_dir() -> Path:
    return Path(os.environ.get("OMNISTACKAI_UI_CHECK_PLAYWRIGHT") or Path.home() / ".omnistackai" / "ui-check")


def unavailable_reason() -> str:
    """Why the check cannot run here, or "" when it can."""
    if os.environ.get("OMNISTACKAI_UI_CHECK") == "0":
        return "turned off (OMNISTACKAI_UI_CHECK=0)"
    if shutil.which("node") is None:
        return "Node is not installed"
    if not SCRIPT.is_file():
        return "scripts/ui-check.mjs is missing"
    if not (playwright_dir() / "node_modules" / "playwright-core").is_dir():
        return "playwright-core is not installed (scripts/omnistack.sh up installs it when Chrome is present)"
    if not any(Path(path).exists() for path in _CHROME):
        return "no Chrome or Chromium found"
    return ""


def report_dir(repo_dir: str) -> Path | None:
    """Where a workspace keeps its check: beside its logs. None outside a workspace (CLI runs)."""
    logs = Path(repo_dir).parent / "logs"
    return logs / "ui-check" if logs.is_dir() else None


def _write_status(folder: Path, status: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / "status.json.tmp"
    tmp.write_text(json.dumps(status, indent=2), encoding="utf-8")
    tmp.replace(folder / "status.json")


def check_arguments(plan: RunPlan, out: Path) -> list[str]:
    """The command line for one preview: every web app under its base path, the API routed."""
    base = plan.public_base.rstrip("/")
    surfaces = plan.web_surfaces or (("web", plan.web_url), ("admin", plan.admin_url))
    args = ["node", str(SCRIPT), "--playwright", str(playwright_dir()), "--out", str(out)]
    for app_id, url in surfaces:
        if url:
            args += ["--app", f"{app_id}={url.rstrip('/')}{base}/{app_id}"]
    if plan.backend_kind != "none" and plan.api_url:
        args += ["--route-api", f"{base}/api={plan.api_url.rstrip('/')}"]
    return args


def summarize(report: dict) -> dict:
    results = report.get("results") or []
    failing = [r for r in results if r.get("problems")]
    return {
        "status": "failed" if failing else "passed",
        "page_views": len(results),
        "pages": len({(r.get("app"), r.get("route")) for r in results}),
        "failing": len(failing),
        "transient": sum(1 for r in results if r.get("notes")),
        "problems": [
            {"app": r.get("app"), "route": r.get("route"), "device": r.get("device"), "problem": r["problems"][0][:300]}
            for r in failing[:_FIRST_PROBLEMS]
        ],
    }


def run_ui_check(plan: RunPlan, *, after: threading.Thread | None = None) -> threading.Thread | None:
    """Start the check in the background for a preview (multi-app, under the console's base path)."""
    if not (plan.multi_app and plan.public_base):
        return None
    folder = report_dir(plan.repo_dir)
    if folder is None:
        return None
    reason = unavailable_reason()
    if reason:
        _write_status(folder, {"status": "skipped", "reason": reason, "finished_at": time.time()})
        return None

    def _run() -> None:
        if after is not None:
            after.join(timeout=_TIMEOUT_SECONDS)  # let every page compile first
        started = time.time()
        _write_status(folder, {"status": "running", "started_at": started})
        try:
            done = subprocess.run(check_arguments(plan, folder), capture_output=True, text=True,
                                  timeout=_TIMEOUT_SECONDS, check=False)
            report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            _write_status(folder, {"status": "error", "reason": f"{type(error).__name__}: {error}"[:300],
                                   "started_at": started, "finished_at": time.time()})
            return
        summary = summarize(report)
        if done.returncode not in (0, 1):
            summary = {"status": "error", "reason": (done.stderr or done.stdout)[-300:]}
        _write_status(folder, {**summary, "started_at": started, "finished_at": time.time()})

    thread = threading.Thread(target=_run, name="ui-check", daemon=True)
    thread.start()
    return thread


def read_status(repo_dir: str, since: float) -> dict | None:
    """The check of this preview run (a status older than ``since`` belongs to an earlier one)."""
    folder = report_dir(repo_dir)
    if folder is None:
        return None
    try:
        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    stamp = status.get("started_at") or status.get("finished_at") or 0
    return status if stamp >= since else None
