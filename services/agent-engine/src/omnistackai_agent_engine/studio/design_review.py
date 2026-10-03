"""PC-130: the design review - every page looked at, scored, and improved until it passes.

A page that type-checks and has no broken links can still look poor: crowded, unbalanced, a badge
on top of a button, a hero with nothing in it. Only looking at it shows that. So, after the preview's
UI check has screenshotted every page at phone and desktop width (PC-106):

1. **look** - a model that can see is shown both screenshots of a page and scores it 1-10 against a
   fixed rubric (hierarchy, spacing and alignment, overlap and clipping, readability, consistency,
   empty and loading states, and whether it looks like a finished modern product), listing concrete
   problems, each with its fix;
2. **improve** - a page below the bar (7 by default) is designed again with its review as the brief;
   the new page goes through the same checks as every designed page (types, links, colours) or is
   put back;
3. **report** - every page's score and problems are kept beside the screenshots
   (``logs/design-review/review.json``), and the mean is the benchmark's "looks" score.

Only models that can see are asked (Anthropic, OpenAI, Gemini, or OpenRouter's free vision models,
with a key set); without one the review says so and changes nothing. No model call happens in ``task verify``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable

logger = logging.getLogger(__name__)

PASS_SCORE = float(os.environ.get("OMNISTACKAI_DESIGN_REVIEW_PASS", "7") or 7)
#: Providers whose models can see a screenshot, in order of preference, with the model to ask.
#: The free OpenRouter models (checked live, 2026-10-03) keep the review working once Gemini's free
#: daily quota is spent. OMNISTACKAI_VISION_CHAIN (provider:model, comma-separated) replaces the list.
VISION = (("anthropic", ""), ("openai", ""), ("google", "gemini-3.8-flash"),
          ("openrouter", "qwen/qwen3.8-27b:free"), ("openrouter", "google/gemma-4-31b-it:free"))


def _vision_spec() -> tuple[tuple[str, str], ...]:
    raw = (os.environ.get("OMNISTACKAI_VISION_CHAIN") or "").strip()
    if not raw:
        return VISION
    return tuple((part.split(":", 1)[0].strip().lower(), part.split(":", 1)[1].strip() if ":" in part else "")
                 for part in raw.split(",") if part.strip())
RUBRIC = """Score this page of a web application from 1 to 10 for visual and UX quality, as a senior product
designer would. You see it at desktop width and at phone width.

Judge: visual hierarchy (is the important thing obvious?), spacing and alignment, overlapping or
clipped elements, text readability and contrast, consistency with a modern design system, empty and
loading states that still look intentional, responsive layout on the phone, and overall: does it look
like a finished, modern product people would pay for (10), a decent template (5-6), or broken (1-3)?

Answer with JSON only:
{"score": <1-10>, "summary": "<one sentence>", "problems": [{"issue": "<what is wrong, where>", "fix": "<what to change>"}]}
List at most 6 problems, the most visible first. No problems for a 9 or 10."""


@dataclass
class PageReview:
    app: str
    route: str
    score: float
    summary: str = ""
    problems: list[dict[str, str]] = field(default_factory=list)
    shots: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def page_path(self) -> str:
        """The page file this route is served by (the Next app router)."""
        route = self.route.strip("/")
        return f"apps/{self.app}/app/{route + '/' if route else ''}page.tsx"

    def critique(self) -> str:
        lines = [f"A design review scored the current version of this page {self.score:g}/10: {self.summary}",
                 "Fix every point:"]
        lines += [f"- {p.get('issue', '')} -> {p.get('fix', '')}" for p in self.problems]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {"app": self.app, "route": self.route, "page": self.page_path, "score": self.score,
                "summary": self.summary, "problems": self.problems, "shots": self.shots, "error": self.error}


def vision_chain(usage_ledger: Any = None) -> list[tuple[Any, str, int, float]]:
    """The models that can see, whose keys are set; empty when there is none."""
    from ..intake.provider_resolution import resolve_generation_provider_from_env, resolve_provider_specs

    specs = resolve_provider_specs()
    chain = []
    for name, model in _vision_spec():
        spec = specs.get(name)
        if spec is None or not os.environ.get(spec.key_env, "").strip():
            continue
        try:
            chain.append(resolve_generation_provider_from_env(load_dotenv=False, provider_id=name, model_id=model or None,
                                                              max_output_tokens=2048, rate_limit_retries=0,
                                                              usage_ledger=usage_ledger))
        except Exception as error:  # noqa: BLE001 - one unusable provider must not stop the others
            logger.warning("design review: %s unavailable: %s", name, error)
    return chain


def pages_to_review(ui_check_dir: Path) -> list[tuple[str, str, list[Path]]]:
    """(app, route, [desktop shot, phone shot]) for every page the UI check screenshotted."""
    try:
        report = json.loads((ui_check_dir / "report.json").read_text())
    except (OSError, ValueError):
        return []
    pages: dict[tuple[str, str], list[Path]] = {}
    for result in report.get("results") or []:
        shot = ui_check_dir / str(result.get("shot") or "")
        if result.get("app") and result.get("route") and shot.is_file():
            pages.setdefault((result["app"], result["route"]), []).append(shot)
    skip = re.compile(r"^/(login|register|forgot-password|reset-password)$")
    return [(app, route, sorted(shots, key=lambda p: "phone" in p.name)) for (app, route), shots in pages.items()
            if not skip.match(route)]


def parse_review(text: str) -> tuple[float, str, list[dict[str, str]]]:
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        raise ValueError("the review was not JSON")
    data = json.loads(match.group(0))
    score = float(data.get("score"))
    if not 1 <= score <= 10:
        raise ValueError("the score is not 1-10")
    problems = [{"issue": str(p.get("issue", ""))[:300], "fix": str(p.get("fix", ""))[:300]}
                for p in (data.get("problems") or [])[:6] if isinstance(p, dict)]
    return score, str(data.get("summary", ""))[:300], problems


async def review_page(provider: Any, model_id: str, app: str, route: str, shots: list[Path], prompt: str,
                      timeout: float = 120.0) -> PageReview:
    from ..model_gateway.contracts import ChatRole, GenerateRequest, Message, ModelRef

    images = tuple(p.read_bytes() for p in shots[:2])
    text = f"The product: {prompt[:400]}\nThe page: {route} of the {app} app.\n\n{RUBRIC}"
    request = GenerateRequest(f"design-review-{uuid.uuid4().hex[:12]}", ModelRef(provider.provider_id, model_id),
                              (Message(ChatRole.USER, text, images),), 2048, timeout)
    response = await provider.generate(request)
    score, summary, problems = parse_review(getattr(response, "text", "") or "")
    return PageReview(app, route, score, summary, problems, [p.name for p in shots])


async def review_pages(ui_check_dir: Path, prompt: str, *, chain: list | None = None,
                       cancelled: Callable[[], bool] = lambda: False, only: set[str] | None = None,
                       sleep: Callable[[float], Any] | None = None) -> AsyncIterator[PageReview]:
    """Every screenshotted page (or only these page files), scored. A page whose review fails is reported
    with the reason, unscored. Found live: free vision tiers limit requests per minute, so a page every
    model refused for a limit is tried once more after a pause."""
    import asyncio

    chain = vision_chain() if chain is None else chain
    pause = sleep or asyncio.sleep
    for app, route, shots in pages_to_review(ui_check_dir):
        if cancelled():
            return
        review = PageReview(app, route, 0.0, shots=[p.name for p in shots], error="no model that can see is configured")
        if only is not None and review.page_path not in only:
            continue
        for attempt in range(2):
            limited = False
            for provider, model_id, _out, timeout in chain:
                try:
                    review = await review_page(provider, model_id, app, route, shots, prompt, timeout)
                    break
                except Exception as error:  # noqa: BLE001 - the next model may answer
                    limited = limited or "429" in str(error) or "RateLimit" in type(error).__name__
                    review.error = f"{getattr(provider, 'provider_id', '?')}: {type(error).__name__}: {str(error)[:120]}"
            if not review.error or not limited or attempt:
                break
            await pause(30.0)
        yield review


def save(review_dir: Path, reviews: list[PageReview], improved: dict[str, str] | None = None) -> dict[str, Any]:
    scored = [r for r in reviews if not r.error]
    summary = {
        "reviewed_at": time.time(),
        "page_count": len(reviews),
        "scored": len(scored),
        "mean": round(sum(r.score for r in scored) / len(scored), 1) if scored else None,
        "below_bar": [r.page_path for r in scored if r.score < PASS_SCORE],
        "pass_score": PASS_SCORE,
        "improved": improved or {},
        "reviews": [r.to_dict() for r in reviews],
    }
    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "review.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


async def review_and_improve(repo_dir: str | Path, ir: Any, prompt: str, page_provider: Any, *, page_model: str | None,
                             timeout_seconds: float = 240.0, chain: list | None = None, improve: bool = True,
                             apps: list | None = None, author_name: str = "OmniStackAI",
                             author_email: str = "agent@omnistack.ai", usage_ledger: Any = None,
                             rescreenshot: Callable[[], dict] | None = None,
                             sleep: Callable[[float], Any] | None = None) -> AsyncIterator[dict]:
    """Review every screenshotted page; design the ones below the bar again with their review.

    Found live: a redesign from a review did not always score higher. With ``rescreenshot`` (the
    preview's own check, run now), each redesigned page is screenshotted and scored again, and kept
    only if it scores higher - otherwise the version before it is restored. The review can only make
    the product look better.
    """
    from .page_design import design_pages

    root = Path(repo_dir)
    ui_check_dir = root.parent / "logs" / "ui-check"
    review_dir = root.parent / "logs" / "design-review"
    reviews: list[PageReview] = []
    chain = vision_chain(usage_ledger) if chain is None else chain
    async for review in review_pages(ui_check_dir, prompt, chain=chain, sleep=sleep):
        reviews.append(review)
        yield {"phase": "review", **review.to_dict()}
    if not reviews:
        yield {"phase": "summary", **save(review_dir, reviews), "note": "no screenshots yet: start the preview first"}
        return
    low = [r for r in reviews if not r.error and r.score < PASS_SCORE and (root / r.page_path).is_file()]
    improved: dict[str, Any] = {}
    if improve and low:
        critiques = {r.page_path: r.critique() for r in low}
        before = {path: (root / path).read_text(encoding="utf-8") for path in critiques}
        async for event in design_pages(root, ir, prompt, page_provider, model_id=page_model, only=list(critiques),
                                        timeout_seconds=timeout_seconds, critiques=critiques, apps=apps,
                                        author_name=author_name, author_email=author_email):
            if event.get("phase") == "page" and event.get("path") in critiques and event.get("status") in ("designed", "kept_template"):
                improved[event["path"]] = event["status"] if event["status"] == "designed" else f"kept: {event.get('reason', '')}"
            if event.get("phase") != "summary":
                yield event
        redesigned = {p for p, status in improved.items() if status == "designed"}
        if redesigned and rescreenshot is not None:
            import asyncio

            shots = await asyncio.to_thread(rescreenshot)
            old = {r.page_path: r.score for r in low}
            new = {}
            if shots.get("status") in ("passed", "failed"):
                async for review in review_pages(ui_check_dir, prompt, chain=chain, only=redesigned, sleep=sleep):
                    if not review.error:
                        new[review.page_path] = review.score
            restored = []
            for path in sorted(redesigned):
                after = new.get(path)
                if after is not None and after > old[path]:
                    improved[path] = {"before": old[path], "after": after, "kept": True}
                else:
                    (root / path).write_text(before[path], encoding="utf-8")
                    restored.append(path)
                    improved[path] = {"before": old[path], "after": after, "kept": False}
                yield {"phase": "rescored", "path": path, **improved[path]}
            if restored:
                from ..git_service import RepositoryError, commit_all

                try:
                    commit_all(str(root), author_name=author_name, author_email=author_email,
                               message=f"revert(ui): {len(restored)} redesign(s) that did not score higher")
                except RepositoryError:
                    pass
    yield {"phase": "summary", **save(review_dir, reviews, improved)}
