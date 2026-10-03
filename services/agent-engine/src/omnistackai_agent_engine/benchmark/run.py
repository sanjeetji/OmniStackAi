"""PC-122: build every benchmark prompt the way the console does, then measure what came out.

For each case, in its own folder (``<out>/<run>/<case>/repo`` and ``logs``):

1. **build** - ``build_app_from_prompt`` with the configured generation provider (free tiers and
   local Ollama by default), exactly the console's build;
2. **design** (``--design``) - the model designs the pages afterwards, as the console's design step
   does (PC-098), with the same provider chain;
3. **preview** - the project runs against a real database; every list endpoint is called; the UI
   check (PC-106) opens every page at phone and desktop width and keeps a screenshot of each;
4. **score** - see ``score.py``.

Then ``report.json`` and ``report.md`` for the run, compared with the previous run in the same folder
(or ``--baseline``). It calls real models, so it is opt-in and never part of ``task verify``.
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import score
from .cases import Case

AUTHOR = ("OmniStackAI Benchmark", "benchmark@omnistack.ai")
UI_CHECK_WAIT_SECONDS = 20 * 60


@dataclass
class CaseResult:
    id: str
    prompt: str
    tags: tuple[str, ...]
    score: float = 0.0
    parts: dict[str, float | None] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    verification: dict = field(default_factory=dict)
    endpoints: dict[str, int] = field(default_factory=dict)
    ui: dict = field(default_factory=dict)
    design: dict = field(default_factory=dict)
    review: dict = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    repo: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in self.__dict__.items()}


def _error(stage: str, error: BaseException) -> str:
    return f"{stage}: {type(error).__name__}: {str(error)[:300]}"


async def build_case(case: Case, folder: Path, *, design: bool, log: Callable[[str], None]) -> tuple[CaseResult, Any]:
    from ..intake.build_app import build_app_from_prompt
    from ..intake.provider_resolution import resolve_generation_provider_from_env

    result = CaseResult(case.id, case.prompt, case.tags)
    repo = folder / "repo"
    (folder / "logs").mkdir(parents=True, exist_ok=True)  # the UI check writes beside a project's logs
    result.repo = str(repo)
    started = time.perf_counter()
    try:
        provider, model_id, max_output, timeout = resolve_generation_provider_from_env()
        built = await build_app_from_prompt(
            case.prompt, provider, repo, model_id=model_id, author_name=AUTHOR[0], author_email=AUTHOR[1],
            max_output_tokens=max_output, timeout_seconds=timeout, overwrite=True,
        )
    except Exception as error:  # noqa: BLE001 - a failed build is a result, not a crash of the run
        result.errors.append(_error("build", error))
        result.timings["build"] = round(time.perf_counter() - started, 1)
        log(f"   build failed: {result.errors[-1]}")
        return result, None
    result.timings.update({k: float(v) for k, v in built.timings.items()})
    result.timings["build"] = round(time.perf_counter() - started, 1)
    result.verification = dict(built.verification)
    result.apps = list(built.ecosystem_apps) or [built.ir.name]
    result.entities = [e.name for e in built.ir.entities]
    result.capabilities = sorted({c.kind for c in built.ir.capabilities})
    result.design = {"model": model_id, "provider": getattr(provider, "provider_id", "")}
    if design:
        started = time.perf_counter()
        try:
            result.design.update(await _design(case, repo, built))
        except Exception as error:  # noqa: BLE001
            result.errors.append(_error("design", error))
        result.timings["design"] = round(time.perf_counter() - started, 1)
    return result, built


async def _design(case: Case, repo: Path, built: Any) -> dict:
    from ..intake.provider_resolution import resolve_page_providers_from_env
    from ..studio.page_design import ChainProvider, design_enabled, design_pages

    if not design_enabled():
        return {"skipped": "page design is turned off (OMNISTACKAI_PAGE_DESIGN)"}
    chain = resolve_page_providers_from_env()
    provider = ChainProvider([(entry[0], entry[1], entry[3], entry[2]) for entry in chain])
    apps = None
    if built.ecosystem_apps:
        from ..intake.build_app import ecosystem_next_apps
        from ..intake.ecosystem import plan_ecosystem_from_prompt

        apps = ecosystem_next_apps(plan_ecosystem_from_prompt(case.prompt, entities=built.ir.entities), brand=built.ir.brand)
    summary: dict = {}
    async for event in design_pages(repo, built.ir, case.prompt, provider, model_id=chain[0][1],
                                    timeout_seconds=max(e[3] for e in chain), apps=apps,
                                    author_name=AUTHOR[0], author_email=AUTHOR[1]):
        if event.get("phase") == "summary":
            summary = event
    kept = {path: page.get("reason", "") for path, page in (summary.get("pages") or {}).items()
            if isinstance(page, dict) and page.get("status") == "kept_template"}
    return {"designed": int(summary.get("designed", 0)), "kept_template": int(summary.get("kept_template", 0)),
            "served_by": list(getattr(provider, "served_by", [])), "kept_because": kept}


def preview_case(result: CaseResult, built: Any, *, log: Callable[[str], None],
                 start: Callable[..., Any] | None = None, fetch: Callable[[str], int] | None = None,
                 review: bool = False) -> None:
    """Run the project, call every list endpoint, and wait for the UI check of every page."""
    from ..localrun import start_preview_app
    from ..localrun.ui_check import read_status

    started_at = time.time()
    begun = time.perf_counter()
    app_log = Path(result.repo).parent / "logs" / "app.log"
    app_log.parent.mkdir(parents=True, exist_ok=True)
    sink = app_log.open("a", encoding="utf-8")
    try:
        session = (start or start_preview_app)(result.repo, public_base=f"/preview/bench-{result.id}", log=lambda m: None,
                                               log_callback=lambda line: (sink.write(line), sink.flush()))
    except Exception as error:  # noqa: BLE001
        sink.close()
        result.errors.append(_error("preview", error) + f" (its output: {app_log})")
        result.parts["runs"] = 0.0
        result.timings["preview"] = round(time.perf_counter() - begun, 1)
        return
    try:
        result.timings["preview"] = round(time.perf_counter() - begun, 1)
        plan = session.plan
        result.parts["runs"] = score.runs_part(
            bool(getattr(session, "api_ready", True)) if plan.backend_kind != "none" else None,
            {"web": bool(getattr(session, "web_ready", True))} | ({"admin": bool(session.admin_ready)} if plan.has_admin else {}),
        )
        if plan.backend_kind != "none":
            result.endpoints = call_list_endpoints(plan.api_url, built.ir, fetch=fetch)
        status = None
        deadline = time.monotonic() + UI_CHECK_WAIT_SECONDS
        while time.monotonic() < deadline:
            status = read_status(result.repo, started_at)
            if status and status.get("status") not in (None, "running"):
                break
            time.sleep(5)
        result.ui = dict(status or {"status": "timeout"})
        log(f"   ui check: {result.ui.get('status')} ({result.ui.get('failing', '?')}/{result.ui.get('page_views', '?')} page views with problems)")
        if review and result.ui.get("status") in ("passed", "failed"):
            result.review = _review(result, log)
    finally:
        session.stop()
        sink.close()


def _review(result: CaseResult, log: Callable[[str], None]) -> dict:
    """PC-130: every page's look, scored from its screenshots by a model that can see."""
    import asyncio

    from ..studio.design_review import PASS_SCORE, review_pages

    async def go() -> list:
        return [r async for r in review_pages(Path(result.repo).parent / "logs" / "ui-check", result.prompt)]

    try:
        reviews = asyncio.run(go())
    except Exception as error:  # noqa: BLE001
        return {"error": f"{type(error).__name__}: {error}"[:200]}
    scored = [r for r in reviews if not r.error]
    mean = round(sum(r.score for r in scored) / len(scored), 1) if scored else None
    log(f"   design review: {mean}/10 over {len(scored)} pages" if scored else "   design review: no model that can see answered")
    return {"mean": mean, "pages": len(reviews), "scored": len(scored),
            "below_bar": [f"{r.app}{r.route} {r.score:g}" for r in scored if r.score < PASS_SCORE],
            "worst": sorted(([r.score, f"{r.app}{r.route}", r.summary] for r in scored))[:3]}


def call_list_endpoints(api_url: str, ir: Any, *, fetch: Callable[[str], int] | None = None) -> dict[str, int]:
    """Every GET without a path parameter, called once; the HTTP status of each (0: no answer)."""

    def _default(url: str) -> int:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - the local preview
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
        except Exception:  # noqa: BLE001
            return 0

    get = fetch or _default
    paths = sorted({a.path for a in ir.apis if a.method.value == "GET" and "{" not in a.path})
    return {path: get(api_url.rstrip("/") + path) for path in paths}


def finish(case: Case, result: CaseResult) -> CaseResult:
    built = bool(result.apps) and not any(e.startswith(("build:", "run:")) for e in result.errors)
    result.parts["build"] = score.build_part(built, result.verification)
    if built:
        result.parts["complete"], result.missing = score.complete_part(
            case, result.entities, result.capabilities, len(result.apps))
    else:
        result.parts["complete"] = 0.0
    if result.endpoints:
        result.parts["api"] = score.ratio(sum(1 for s in result.endpoints.values() if 200 <= s < 300), len(result.endpoints))
    if result.ui.get("status") in ("passed", "failed"):
        views = int(result.ui.get("page_views") or 0)
        result.parts["pages"] = score.ratio(views - int(result.ui.get("failing") or 0), views)
    if result.review.get("mean") is not None:
        result.parts["looks"] = result.review["mean"] / 10
    if "designed" in result.design:
        result.parts["designed"] = score.ratio(result.design["designed"], result.design["designed"] + result.design["kept_template"])
    result.score = score.total(result.parts)
    return result


async def run_benchmark(cases: tuple[Case, ...], out: Path, *, design: bool = False, preview: bool = True,
                        baseline: Path | None = None, log: Callable[[str], None] = print, review: bool = False) -> dict:
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = out / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    previous = _previous_report(out, run_id) if baseline is None else json.loads(baseline.read_text())
    results: list[CaseResult] = []
    for index, case in enumerate(cases, 1):
        log(f"[{index}/{len(cases)}] {case.id}: {case.prompt[:80]}")
        try:
            result, built = await build_case(case, run_dir / case.id, design=design, log=log)
            if built is not None and preview:
                await asyncio.to_thread(preview_case, result, built, log=log, review=review)
        except Exception as error:  # noqa: BLE001 - one case never ends the run
            result = CaseResult(case.id, case.prompt, case.tags)
            result.errors.append(_error("run", error) + " | " + traceback.format_exc(limit=2)[-300:])
        results.append(finish(case, result))
        log(f"   score {results[-1].score} {json.dumps({k: (round(v, 2) if v is not None else None) for k, v in results[-1].parts.items()})}")
        _write(run_dir, run_id, results, previous, design, preview)  # partial results survive an interrupted run
    return _write(run_dir, run_id, results, previous, design, preview)


def _previous_report(out: Path, run_id: str) -> dict | None:
    for folder in sorted((p for p in out.iterdir() if p.is_dir() and p.name < run_id), reverse=True):
        report = folder / "report.json"
        if report.is_file():
            try:
                return json.loads(report.read_text())
            except ValueError:
                continue
    return None


def _write(run_dir: Path, run_id: str, results: list[CaseResult], previous: dict | None, design: bool, preview: bool) -> dict:
    from .report import markdown

    cases = [r.to_dict() for r in results]
    report = {
        "run": run_id,
        "design": design,
        "preview": preview,
        "mean": round(sum(c["score"] for c in cases) / len(cases), 1) if cases else 0.0,
        "cases": cases,
        "comparison": score.compare(cases, (previous or {}).get("cases")),
        "baseline_run": (previous or {}).get("run"),
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text(markdown(report, run_dir), encoding="utf-8")
    return report


def rescore(run_dir: Path) -> dict:
    """Score a saved run again with the current rules, so a change to the scoring keeps runs comparable."""
    from .cases import CASES

    report = json.loads((run_dir / "report.json").read_text())
    by_id = {c.id: c for c in CASES}
    results = []
    for saved in report["cases"]:
        result = CaseResult(saved["id"], saved["prompt"], tuple(saved.get("tags") or ()))
        for key, value in saved.items():
            if key in result.__dict__ and key not in ("score", "parts", "missing"):
                setattr(result, key, value)
        result.parts = {k: v for k, v in (saved.get("parts") or {}).items() if k == "runs"}
        results.append(finish(by_id[saved["id"]], result) if saved["id"] in by_id else result)
    previous = _previous_report(run_dir.parent, run_dir.name)
    return _write(run_dir, report["run"], results, previous, report.get("design", False), report.get("preview", True))


def main_async(cases: tuple[Case, ...], out: Path, **kwargs) -> dict:
    return asyncio.run(run_benchmark(cases, out, **kwargs))
