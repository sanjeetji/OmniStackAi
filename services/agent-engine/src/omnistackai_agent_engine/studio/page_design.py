"""Model-designed pages, after the build (PC-098).

PC-084 switched model-written pages off on the console's build path: they cost ~80 s of a 165 s
build and the admin page did not compile, so every console build shipped template pages only (one
model-written page across 33 projects on 2026-09-27). This brings them back without either cost:

* **The build does not wait.** The build and its template preview are exactly as fast as before;
  pages are designed afterwards, as their own step, while the preview is already running.
* **A broken page never stays.** Each app's new pages are type-checked and repaired from the
  compiler's errors, or put back to that app's own template (PC-097). A page that cannot be checked
  at all is put back too, rather than left unverified.
* **It is honest.** Every page is reported as designed or kept as the template, with the reason.
* **It is bounded and billed.** At most ``OMNISTACKAI_PAGE_DESIGN_MAX_PAGES`` pages per run (home
  pages first); the caller's usage ledger carries the task budget, so a spent budget stops page
  writing and the rest keep their templates.

Pages already designed are skipped unless named in ``only`` (an edit that changed what a designed
page shows asks for it by name). No model call is made without a provider, so ``task verify``
exercises all of this with stubs.
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Callable

logger = logging.getLogger(__name__)

DESIGN_ENV = "OMNISTACKAI_PAGE_DESIGN"
MAX_PAGES_ENV = "OMNISTACKAI_PAGE_DESIGN_MAX_PAGES"
#: PC-129: every page by default (home pages first); the time budget still bounds a run, and an
#: operator can lower it. It was 8, so most of a larger product kept its templates.
DEFAULT_MAX_PAGES = 40
#: Compile passes after the first: every one but the last asks the model to fix the errors.
DESIGN_REPAIR_ROUNDS = 3
TIME_BUDGET_ENV = "OMNISTACKAI_PAGE_DESIGN_BUDGET_SECONDS"
#: Found live: a slow model took over 30 minutes for 8 pages and the run outlived the control
#: plane's bound, so its end - and its bill - never arrived. No page starts after this many seconds;
#: the control plane's own bound (OMNISTACKAI_PAGE_DESIGN_TIMEOUT, 60 min) leaves room to finish.
DEFAULT_TIME_BUDGET = 40 * 60.0


def design_enabled() -> bool:
    """Page design runs unless the operator turns it off."""
    return (os.environ.get(DESIGN_ENV) or "on").strip().lower() not in {"off", "0", "false", "no"}


def time_budget() -> float:
    try:
        return max(0.0, float(os.environ.get(TIME_BUDGET_ENV, str(DEFAULT_TIME_BUDGET))))
    except ValueError:
        return DEFAULT_TIME_BUDGET


def max_pages() -> int:
    try:
        return max(0, int(os.environ.get(MAX_PAGES_ENV, str(DEFAULT_MAX_PAGES))))
    except ValueError:
        return DEFAULT_MAX_PAGES


RATE_LIMIT_WAITS_ENV = "OMNISTACKAI_PAGE_RATE_LIMIT_WAITS"
#: Seconds to wait after each successive rate-limit refusal before asking again. Measured live
#: (PC-098): Gemini's free tier limits requests per minute, and the provider's own ~30 s of
#: backoff gave up on 7 of 8 pages; waiting out the minute lets them through.
DEFAULT_RATE_LIMIT_WAITS = (20.0, 40.0, 60.0)


def _rate_limit_waits() -> tuple[float, ...]:
    raw = os.environ.get(RATE_LIMIT_WAITS_ENV)
    if not raw:
        return DEFAULT_RATE_LIMIT_WAITS
    try:
        return tuple(max(0.0, float(part)) for part in raw.split(",") if part.strip())
    except ValueError:
        return DEFAULT_RATE_LIMIT_WAITS


class PatientProvider:
    """Waits out a provider's per-minute limit instead of giving a page up (PC-098).

    Page design runs after the build, while the preview is already up, so a minute's wait costs the
    person nothing - unlike a build, where the provider's own short backoff is right. Wraps the
    billing provider, so refused calls are recorded as failures and never billed.
    """

    def __init__(self, inner: Any, waits: tuple[float, ...] | None = None, sleep: Callable | None = None) -> None:
        import asyncio

        self._inner = inner
        self._waits = _rate_limit_waits() if waits is None else waits
        self._sleep = sleep or asyncio.sleep

    @property
    def provider_id(self) -> str:
        return self._inner.provider_id

    async def generate(self, request: Any) -> Any:
        from ..model_gateway.errors import ProviderRateLimitedError, ProviderUnavailableError

        from ..model_gateway import health

        for wait in (*self._waits, None):
            # PC-126: no waiting out a limit that lasts longer than this page's waits (a spent daily
            # quota): the chain's next provider answers now.
            back = health.out_until(self.provider_id)
            if back and back - time.time() > sum(self._waits):
                raise ProviderRateLimitedError(f"{self.provider_id} is out until its limit resets", status_code=429)
            try:
                return await self._inner.generate(request)
            except ProviderUnavailableError:
                # Found live: NVIDIA's endpoint answered "unavailable" mid-run and a page that was
                # one fix from compiling was put back. A passing outage is waited out like a limit.
                if wait is None:
                    raise
                logger.info("page design: %s is unavailable; waiting %.0fs", self.provider_id, wait)
                await self._sleep(wait)
                continue
            except ProviderRateLimitedError as error:
                # A daily quota does not reset in a minute: say so at once rather than waiting.
                # Measured (PC-098): Gemini 3 Flash's free tier allows 20 requests a day.
                if wait is None or re.search(r"PerDay|per day|daily", str(error), re.I):
                    raise
                hinted = getattr(error, "retry_after_seconds", None) or 0.0
                logger.info("page design: %s is rate-limiting; waiting %.0fs", self.provider_id, max(wait, hinted))
                await self._sleep(max(wait, min(float(hinted), 120.0)))
        raise AssertionError("unreachable")


class ChainProvider:
    """Several page-writing providers, each patient, tried in order when one's limit is spent.

    Each request is re-addressed to the model of the provider that serves it; the billing wrapper
    on each records what it served, so the user pays for the answers used, whoever gave them.
    """

    def __init__(self, entries: list[tuple], waits: tuple[float, ...] | None = None,
                 sleep: Callable | None = None) -> None:
        if not entries:
            raise ValueError("a chain needs at least one provider")
        # (provider, model) or (provider, model, timeout seconds): a local model may need far
        # longer for one page than a cloud one, so each keeps its own bound.
        self._entries = [
            (PatientProvider(e[0], waits, sleep), e[1], e[2] if len(e) > 2 else None, e[3] if len(e) > 3 else None)
            for e in entries
        ]
        self._inner = entries[0][0]  # limits (answer budget) are read from the first
        self._waits = tuple(w for patient, _m, _t, _o in self._entries for w in patient._waits)
        self.served_by: list[str] = []
        # A provider whose limit ran out stays out for the rest of the run: otherwise every page
        # would wait its limit out again before reaching the next provider.
        self._spent: set[int] = set()

    @property
    def provider_id(self) -> str:
        return self._entries[0][0].provider_id

    async def generate(self, request: Any) -> Any:
        from dataclasses import replace as _replace

        from ..model_gateway.contracts import ModelRef
        from ..model_gateway.errors import BudgetExceededError, ModelProviderError

        from ..model_gateway import health

        last: Exception | None = None
        # PC-126: a provider another job found out (a spent quota, a limit) is tried last, not first;
        # and a limit is waited out only on the last provider left - while another can answer, it does.
        candidates = [i for i in health.order([p.provider_id for p, _m, _t, _o in self._entries]) if i not in self._spent]
        for position, index in enumerate(candidates):
            patient, model, timeout, max_out = self._entries[index]
            final = position == len(candidates) - 1
            addressed = _replace(request, model=ModelRef(patient.provider_id, model))
            if timeout:
                addressed = _replace(addressed, timeout_seconds=float(timeout))
            if max_out and addressed.max_output_tokens > max_out:
                addressed = _replace(addressed, max_output_tokens=int(max_out))  # each model's own limit
            try:
                answer = await (patient.generate(addressed) if final else patient._inner.generate(addressed))
            except BudgetExceededError:
                raise  # the task's credit budget is spent: no provider may continue
            except (ModelProviderError, TimeoutError) as error:
                # Spent, down, too slow, or a model no longer offered: the next provider may serve.
                logger.info("page design: %s failed (%s); trying the next provider", patient.provider_id,
                            type(error).__name__)
                health.note_failure(patient.provider_id, error)
                self._spent.add(index)
                last = error
                continue
            health.note_success(patient.provider_id)
            if patient.provider_id not in self.served_by:
                self.served_by.append(patient.provider_id)
            return answer
        if last is None:
            from ..model_gateway.errors import ProviderRateLimitedError as _Limited

            raise _Limited("every page-writing provider is spent or unavailable", status_code=429)
        raise last


@dataclass(frozen=True, slots=True)
class PageTarget:
    """One page to design: its app (monorepo-relative), the page inside it, and what it shows."""

    app: str
    flavour: str  # "web" | "admin"
    page: str  # app-relative, e.g. "app/page.tsx"
    screen_id: str | None  # None for the home page
    ir: Any = None  # the app's own plan (an ecosystem's apps each have one)

    @property
    def path(self) -> str:
        return f"{self.app}/{self.page}"


def plan_pages(
    repo_dir: str | os.PathLike[str],
    ir: Any,
    *,
    only: list[str] | None = None,
    limit: int | None = None,
    apps: list[tuple[str, Any, str]] | None = None,
) -> list[PageTarget]:
    """The pages to design, most visible first: every app's home page, then the screens.

    ``only`` restricts to those monorepo paths (and designs them even if already designed).
    ``apps`` (directory, its IR, flavour) names the apps; by default the single-project layout.
    Found live (PC-099): an ecosystem (web, provider and admin apps) had no page designed at all,
    because only the single-project layout was known here.
    """
    from ..codegen.hybrid_repair import is_model_written
    from ..intake.build_verify import next_apps_for

    root = Path(repo_dir)
    layout = apps if apps is not None else next_apps_for(ir)
    present = [(rel, app_ir, flavour) for rel, app_ir, flavour in layout if (root / rel).is_dir()]
    homes = [PageTarget(rel, flavour, "app/page.tsx", None, app_ir) for rel, app_ir, flavour in present]
    auth_routes = {"login", "register", "forgot-password", "reset-password"}  # the app's own sign-in pages
    screens = [
        PageTarget(rel, flavour, f"app/{screen.id}/page.tsx", screen.id, app_ir)
        for rel, app_ir, flavour in present
        for screen in getattr(app_ir, "screens", ())
        if screen.id not in auth_routes
    ]
    wanted = set(only or ())
    ordered: list[PageTarget] = []
    for target in homes + screens:
        page_file = root / target.path
        if not page_file.is_file():
            continue
        if wanted:
            if target.path in wanted:
                ordered.append(target)
        elif not is_model_written(page_file):
            ordered.append(target)
    cap = max_pages() if limit is None else limit
    return ordered[:cap] if not wanted else ordered


async def _write_page(target: PageTarget, ir: Any, prompt: str, provider: Any, model_id: str | None,
                      timeout_seconds: float, grounding: dict, compact: dict) -> tuple[str | None, str]:
    """Ask the model for one page. Returns (content, "") when it wrote one, (None, reason) otherwise."""
    from ..codegen.archetype import Archetype, detect_archetype
    from ..codegen.llm_ui import synthesize_overview_page, synthesize_screen_page

    outcomes: list = []
    if target.screen_id is None:
        archetype = (Archetype.ADMIN_PANEL if target.flavour == "admin" else detect_archetype(ir, prompt)).value
        content = await synthesize_overview_page(
            ir, prompt, provider=provider, model_id=model_id, timeout_seconds=timeout_seconds,
            outcomes=outcomes, compact_grounding=compact, archetype=archetype, flavour=target.flavour,
            **grounding,
        )
    else:
        screen = next((s for s in ir.screens if s.id == target.screen_id), None)
        if screen is None:
            return None, "the screen is no longer in the plan"
        content = await synthesize_screen_page(
            screen, ir, prompt, provider=provider, model_id=model_id, timeout_seconds=timeout_seconds,
            outcomes=outcomes, compact_grounding=compact, **grounding,
        )
    last = outcomes[-1] if outcomes else None
    if last is not None and last.mode == "llm":
        return content, ""
    return None, _plain_reason(last.last_reason if last is not None else "")


def _plain_reason(reason: str) -> str:
    """The reason a page kept its template, in words a person can act on."""
    if not reason:
        return "the model did not return a usable page"
    if "413" in reason:
        return "the page request was too large for this model"
    if "BudgetExceeded" in reason:
        return "this task's credit budget was used up"
    if "429" in reason:
        return "the model provider is rate-limiting requests; try again shortly"
    if "Timeout" in reason:
        return "the model did not answer in time"
    return f"the model's page did not pass checks ({reason[:120]})"


async def design_pages(
    repo_dir: str | os.PathLike[str],
    ir: Any,
    prompt: str,
    provider: Any,
    *,
    model_id: str | None = None,
    only: list[str] | None = None,
    limit: int | None = None,
    timeout_seconds: float = 120.0,
    cancelled: Callable[[], bool] = lambda: False,
    author_name: str = "OmniStackAI",
    author_email: str = "agent@omnistack.ai",
    runner: Any = None,
    apps: list[tuple[str, Any, str]] | None = None,
    critiques: dict[str, str] | None = None,
) -> AsyncIterator[dict]:
    """Design pages one app at a time, streaming what happens to each.

    Events: ``planned`` (the pages), ``page`` (one page written by the model or kept as its
    template), ``checked`` (an app's compile result), and a final ``summary``.
    """
    from ..codegen.hybrid_repair import compile_and_repair, is_model_written, llm_file_specs
    from ..codegen.nextjs import compact_grounding, summarize_components, summarize_data_layer, summarize_design_tokens
    from ..git_service import commit_all
    from ..intake.build_verify import NODE_MODULES_ENV, next_apps_for
    from ..verify import VerifyError, ensure_web_dependencies

    root = Path(repo_dir)
    targets = plan_pages(root, ir, only=only, limit=limit, apps=apps)
    from .mobile_design import plan_screens

    phones = plan_screens(root, [p for p in (only or []) if "/src/" in p] if only else None) if limit != 0 else []
    yield {"phase": "planned", "pages": [t.path for t in targets] + [s.full for s in phones]}
    results: dict[str, dict] = {}
    if not targets and not phones:
        yield {"phase": "summary", "designed": 0, "kept_template": 0, "pages": results}
        return

    layout = apps if apps is not None else next_apps_for(ir)
    flavours = {rel: flavour for rel, _i, flavour in layout}
    app_irs = {rel: app_ir for rel, app_ir, _f in layout}
    groundings: dict[str, tuple[dict, dict]] = {}

    def grounding_for(app: str) -> tuple[dict, dict]:
        if app not in groundings:
            app_ir = app_irs[app]
            groundings[app] = ({
                "data_layer": summarize_data_layer(app_ir),
                "components": summarize_components(app_ir),
                "design_tokens": summarize_design_tokens(),
            }, compact_grounding(app_ir))
        return groundings[app]
    source = os.environ.get(NODE_MODULES_ENV) or None
    changed = False
    limit_reached = ""
    deadline = time.monotonic() + time_budget()

    provider = provider if isinstance(provider, ChainProvider) else PatientProvider(provider)
    # Found live: each model call is bounded by `timeout_seconds`, and the patient waits happen
    # inside that bound - so waiting out a rate limit itself timed out. The bound covers them.
    timeout_seconds = timeout_seconds + sum(provider._waits)
    # Every app's home page first (what a person sees first), then the screens. Each wave checks
    # each app once, so a page is never left unchecked while the next wave runs.
    waves = [[t for t in targets if t.screen_id is None], [t for t in targets if t.screen_id is not None]]
    for app, wave in [(rel, w) for w in waves for rel in flavours if any(t.app == rel for t in w)]:
        written: list[PageTarget] = []
        for target in (t for t in wave if t.app == app):
            if cancelled():
                break
            if not limit_reached and time.monotonic() > deadline:
                limit_reached = "page design used its time for this run; ask for the pages to be designed again"
            if limit_reached:
                # One page already waited out the limit and failed: every next page would too.
                results[target.path] = {"status": "kept_template", "reason": limit_reached}
                yield {"phase": "page", "path": target.path, **results[target.path]}
                continue
            grounding, compact = grounding_for(app)
            # PC-130: a page the design review sent back is written with its review as the brief.
            page_prompt = prompt + ("\n\n" + critiques[target.path] if critiques and target.path in critiques else "")
            content, reason = await _write_page(target, app_irs[app], page_prompt, provider, model_id, timeout_seconds,
                                                grounding, compact)
            if content is None and "rate-limiting" in reason:
                limit_reached = "the model's request limit is used up for now; try designing again later"
                reason = limit_reached
            if content is None:
                results[target.path] = {"status": "kept_template", "reason": reason}
                yield {"phase": "page", "path": target.path, "status": "kept_template", "reason": reason}
                continue
            (root / target.path).write_text(content, encoding="utf-8")
            written.append(target)
            changed = True
            yield {"phase": "page", "path": target.path, "status": "written"}
        if not written:
            continue

        app_dir = root / app
        specs = llm_file_specs(app_irs[app], prompt, synthesize_screens=True, flavour=flavours[app])
        repair_outcomes: list = []
        try:
            if runner is None:
                if source is None and not (app_dir / "node_modules").exists():
                    raise VerifyError("dependencies are not installed")
                ensure_web_dependencies(app_dir, node_modules_source=source)
            report = await compile_and_repair(
                repo_dir=str(root), ir=app_irs[app], user_prompt=prompt, provider=provider, model_id=model_id,
                synthesize_screens=True, web_prefix=f"{app}/", flavour=flavours[app], runner=runner,
                timeout_seconds=timeout_seconds, outcomes=repair_outcomes,
                # Measured live: one repair round took a page from 6 errors to 1; the default gave
                # it no second round. Page design runs in the background, so it can afford two.
                max_rounds=DESIGN_REPAIR_ROUNDS,
            )
            reverted, ok = set(report.reverted), report.final_ok
            reason_unchecked = ""
        except VerifyError as error:
            # Never leave a page nobody could type-check: put every new page back.
            for target in written:
                (root / target.path).write_text(specs[target.page].fallback, encoding="utf-8")
            reverted, ok = {t.page for t in written}, True
            reason_unchecked = f"it could not be type-checked here ({error})"
        # Why a repair gave up, per page (the model's own failure, when there was one).
        repair_reasons: dict[str, str] = {}
        for outcome in repair_outcomes:
            if outcome.mode == "deterministic" and outcome.last_reason and not outcome.last_reason.startswith("tsc:"):
                repair_reasons[outcome.path] = outcome.last_reason
        for target in written:
            if target.page in reverted:
                why = reason_unchecked or "the model's page did not compile and could not be repaired"
                if not reason_unchecked and target.page in repair_reasons:
                    why += f": {_plain_reason(repair_reasons[target.page])}"
                results[target.path] = {"status": "kept_template", "reason": why}
            else:
                results[target.path] = {"status": "designed"}
            yield {"phase": "page", "path": target.path, **results[target.path]}
        # Found live: a later check of the same app can put back a page an earlier one kept, and
        # its "designed" was never corrected. What is on disk decides.
        for path, result in list(results.items()):
            if (path.startswith(f"{app}/") and result["status"] == "designed"
                    and not is_model_written(root / path)):
                results[path] = {"status": "kept_template",
                                 "reason": "it stopped compiling when the app's other pages were checked"}
                yield {"phase": "page", "path": path, **results[path]}
        yield {"phase": "checked", "app": app, "compiles": ok}

    # PC-129: then the phone app's screens, with the same promise - checked, or put back.
    if not limit_reached and time.monotonic() <= deadline and not cancelled():
        from .mobile_design import design_phone_screens

        phone_only = [p for p in (only or []) if "/src/" in p] if only else None
        if phones:
            async for event in design_phone_screens(root, prompt, provider, model_id=model_id, only=phone_only,
                                                    timeout_seconds=timeout_seconds, cancelled=cancelled):
                if event.get("phase") == "page":
                    results[event["path"]] = {k: v for k, v in event.items() if k in ("status", "reason")}
                    if event.get("status") == "designed":
                        changed = True
                yield event

    designed = sum(1 for r in results.values() if r["status"] == "designed")
    # PC-014, found live: every page was put back, yet the dependency install's lockfile was
    # committed as "model-designed pages". Only a designed page is worth that commit.
    if changed and designed:
        from ..git_service import RepositoryError

        try:
            commit_all(str(root), author_name=author_name, author_email=author_email,
                       message=f"feat(ui): model-designed pages ({designed})")
        except RepositoryError:
            pass
    yield {"phase": "summary", "designed": designed, "kept_template": len(results) - designed, "pages": results}
