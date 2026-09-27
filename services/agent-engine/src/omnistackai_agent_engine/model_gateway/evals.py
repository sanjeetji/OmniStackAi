"""PC-085: every provider is scored on the platform's own jobs, and each job goes to the best one.

Choosing a model by reputation failed twice: NVIDIA's flagship was 7-10x slower than Gemini on the
real intake step, and three of four Groq models could not produce a valid plan at all. So the
platform measures, on the two jobs a build gives a model:

* ``plan`` — a prompt becomes an app plan through the real intake (parse, repair, validate). Scored
  on whether the plan is valid, how much of the app it describes, and how fast it came back.
* ``code`` — a TypeScript file the compiler rejected is repaired. Scored by the TypeScript compiler
  itself, against the same dependencies generated web apps use.

``python -m omnistackai_agent_engine.model_gateway.evals`` (or ``scripts/model-eval.sh``) runs every
configured provider, prints a table and writes the scorecard. It calls real models, so it is opt-in
and never part of ``task verify``. Routing (`rank_chain`) reads the scorecard: each job's fallback
chain is ordered best first; a provider with no score keeps its configured place after the scored
ones that passed, and one that failed every run goes last. A project that pinned a model is never
re-routed. Scores are keyed by provider *and* model, so changing a model makes its old score moot.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import statistics
import subprocess
import tempfile
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCORECARD_ENV = "OMNISTACKAI_MODEL_SCORECARD"
ROUTING_ENV = "OMNISTACKAI_MODEL_ROUTING"
TASKS = ("plan", "code")

PLAN_CASES = (
    "A habit tracker where people add habits, group them in categories and check in every day",
    "A clinic booking app: patients book appointments with doctors, staff confirm or cancel them",
    "An online store for handmade candles with products, a cart, orders and order tracking",
)

# Each case: a file the compiler rejects, and what the compiler said. The fix must keep the export.
CODE_CASES = (
    (
        "habit-card.tsx",
        '''type Habit = { id: string; title: string; streak: number };

export default function HabitCard({ habit }: { habit: Habit }) {
  const label: number = habit.title;
  return (
    <div>
      <h3>{label}</h3>
      <p>{habit.streek} day streak</p>
    </div>
  );
}
''',
        "habit-card.tsx(4,9): error TS2322: Type 'string' is not assignable to type 'number'.\n"
        "habit-card.tsx(8,16): error TS2551: Property 'streek' does not exist on type 'Habit'. "
        "Did you mean 'streak'?",
    ),
    (
        "order-list.tsx",
        '''"use client";
import { useState } from "react";

type Order = { id: string; total: number; status: "open" | "shipped" };

export default function OrderList({ orders }: { orders: Order[] }) {
  const [filter, setFilter] = useState<Order["status"]>("open");
  const shown = orders.filter((o) => o.status === filter);
  return (
    <section>
      <button onClick={() => setFilter("delivered")}>Delivered</button>
      <ul>{shown.map((o) => <li key={o.id}>{o.total.toFixed(2)}</li>)}</ul>
      <p>{shown.length.toUpperCase()}</p>
    </section>
  );
}
''',
        "order-list.tsx(11,40): error TS2345: Argument of type '\"delivered\"' is not assignable to "
        "parameter of type 'SetStateAction<\"open\" | \"shipped\">'.\n"
        "order-list.tsx(13,27): error TS2339: Property 'toUpperCase' does not exist on type 'number'.",
    ),
)

_CODE_SYSTEM = (
    "You fix TypeScript React files that the compiler rejected. Keep the component's purpose, its "
    "props and its default export. Change only what the errors require. Reply with the complete "
    "corrected file and nothing else — no explanation, no Markdown fences."
)
_TSCONFIG = {
    "compilerOptions": {
        "strict": True, "noEmit": True, "jsx": "react-jsx", "target": "ES2020",
        "module": "ESNext", "moduleResolution": "bundler", "skipLibCheck": True,
        "lib": ["dom", "ES2020"], "types": ["react"],
    }
}


@dataclass(frozen=True)
class Candidate:
    """One provider and model to score, as the build chain would call it."""

    provider: Any
    model_id: str
    max_output_tokens: int
    timeout_seconds: float = 120.0

    @property
    def key(self) -> str:
        return f"{self.provider.provider_id}:{self.model_id}"


@dataclass(frozen=True)
class Run:
    ok: bool
    seconds: float
    richness: float = 0.0
    error: str = ""
    #: Rate-limited, keyless or unreachable: says nothing about quality, so it is not scored.
    unavailable: bool = False


def _failed(error: Exception, started: float) -> Run:
    from .errors import MissingCredentialError, ProviderHTTPError, ProviderRateLimitedError, ProviderUnavailableError

    status = getattr(error, "status_code", None)
    unavailable = isinstance(error, (ProviderRateLimitedError, MissingCredentialError, ProviderUnavailableError)) or (
        isinstance(error, ProviderHTTPError) and status in (401, 402, 403, 429)
    )
    return Run(False, time.perf_counter() - started, error=type(error).__name__, unavailable=unavailable)


# ── scorecard ─────────────────────────────────────────────────────────────────────────────────────


def scorecard_path() -> Path:
    configured = os.environ.get(SCORECARD_ENV, "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".omnistackai" / "model-evals" / "scorecard.json"


def load_scorecard(path: Path | None = None) -> dict[str, Any]:
    """The last scorecard, or an empty one. A damaged file routes nothing rather than failing a build."""
    try:
        card = json.loads((path or scorecard_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return card if isinstance(card, dict) and isinstance(card.get("tasks"), dict) else {}


def save_scorecard(card: dict[str, Any], path: Path | None = None) -> Path:
    target = path or scorecard_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(card, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target


def summarize(runs: Sequence[Run]) -> dict[str, Any]:
    """Quality first: a valid answer is worth far more than a fast or a rich one.

    score = 0.75 x share of valid runs + 0.15 x richness + 0.10 x speed, where speed is 1 at 10 s or
    faster and falls off beyond (20 s -> 0.5). Richness and speed count only valid runs. Runs the
    provider could not take at all (quota, key, outage) are left out: they are not a quality signal.
    """
    skipped = sum(1 for r in runs if r.unavailable)
    errors = sorted({r.error for r in runs if r.error})[:3]
    runs = [r for r in runs if not r.unavailable]
    good = [r for r in runs if r.ok]
    valid_rate = len(good) / len(runs) if runs else 0.0
    median = statistics.median(r.seconds for r in good) if good else None
    richness = sum(r.richness for r in good) / len(good) if good else 0.0
    speed = min(1.0, 10.0 / median) if median else 0.0
    return {
        "runs": len(runs),
        "valid": len(good),
        "valid_rate": round(valid_rate, 3),
        "median_seconds": round(median, 2) if median is not None else None,
        "richness": round(richness, 3),
        "score": round(0.75 * valid_rate + 0.15 * richness + 0.10 * speed, 3),
        "unavailable": skipped,
        "errors": errors,
    }


def rank_chain(keys: Sequence[str], task: str, card: dict[str, Any] | None = None) -> list[int]:
    """Indices of ``keys`` (``provider:model``) in the order the job should try them.

    Scored providers that produced valid work come first, best score first; then providers with no
    score, in their configured order; then providers that failed every scored run. Ties keep the
    configured order, so with no scorecard (or routing set to ``fixed``) nothing moves.
    """
    if os.environ.get(ROUTING_ENV, "scored").strip().lower() == "fixed":
        return list(range(len(keys)))
    scores = ((card if card is not None else load_scorecard()).get("tasks") or {}).get(task) or {}

    def bucket(index: int) -> tuple[int, float, int]:
        entry = scores.get(keys[index])
        if not isinstance(entry, dict) or not entry.get("runs"):
            return (1, 0.0, index)
        if not entry.get("valid"):
            return (2, 0.0, index)
        return (0, -float(entry.get("score", 0.0)), index)

    return sorted(range(len(keys)), key=bucket)


# ── the two jobs ──────────────────────────────────────────────────────────────────────────────────


async def eval_plan(candidate: Candidate, prompt: str) -> Run:
    from ..intake.nl_to_ir import generate_ir

    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            generate_ir(prompt, candidate.provider, model_id=candidate.model_id,
                        max_output_tokens=candidate.max_output_tokens,
                        timeout_seconds=candidate.timeout_seconds),
            timeout=candidate.timeout_seconds + 10,
        )
    except Exception as error:  # noqa: BLE001 - any failure is a failed run, with its kind recorded
        return _failed(error, started)
    ir = result.ir
    size = len(ir.entities) + len(ir.screens) + len(ir.apis) + 3 * len(getattr(ir, "capabilities", ()) or ())
    return Run(True, time.perf_counter() - started, richness=min(1.0, size / 30.0))


def _web_node_modules() -> Path | None:
    configured = os.environ.get("OMNISTACKAI_WEB_NODE_MODULES", "").strip()
    cache = Path(configured).expanduser() if configured else Path.home() / ".omnistackai" / "web-typecheck" / "node_modules"
    return cache if (cache / ".bin" / "tsc").exists() and (cache / "@types" / "react").is_dir() else None


def extract_code(text: str) -> str:
    """The file from a reply, with or without the fences the prompt asked it to leave out."""
    fenced = re.search(r"```(?:tsx|typescript|ts|jsx)?\s*\n(.*?)```", text, re.S)
    return (fenced.group(1) if fenced else text).strip() + "\n"


def typechecks(name: str, source: str, node_modules: Path) -> bool:
    with tempfile.TemporaryDirectory(prefix="omni-eval-") as tmp:
        root = Path(tmp)
        (root / name).write_text(source, encoding="utf-8")
        (root / "tsconfig.json").write_text(json.dumps({**_TSCONFIG, "files": [name]}), encoding="utf-8")
        (root / "node_modules").symlink_to(node_modules, target_is_directory=True)
        done = subprocess.run([str(node_modules / ".bin" / "tsc"), "-p", "."], cwd=root,
                              capture_output=True, text=True, timeout=120, check=False)
        return done.returncode == 0


async def eval_code(candidate: Candidate, case: tuple[str, str, str], node_modules: Path) -> Run:
    from .contracts import ChatRole, GenerateRequest, Message, ModelRef

    name, broken, errors = case
    request = GenerateRequest(
        f"eval-code-{name}", ModelRef(candidate.provider.provider_id, candidate.model_id),
        (Message(ChatRole.SYSTEM, _CODE_SYSTEM),
         Message(ChatRole.USER, f"File {name}:\n\n{broken}\nThe compiler said:\n{errors}")),
        min(candidate.max_output_tokens, 4096), candidate.timeout_seconds,
    )
    started = time.perf_counter()
    try:
        response = await asyncio.wait_for(candidate.provider.generate(request), timeout=candidate.timeout_seconds + 10)
    except Exception as error:  # noqa: BLE001
        return _failed(error, started)
    seconds = time.perf_counter() - started
    fixed = extract_code(response.text or "")
    if "export default" not in fixed:
        return Run(False, seconds, error="dropped the default export")
    ok = await asyncio.to_thread(typechecks, name, fixed, node_modules)
    return Run(ok, seconds, richness=1.0 if ok else 0.0, error="" if ok else "still does not compile")


async def evaluate(candidates: Sequence[Candidate], tasks: Sequence[str] = TASKS, runs: int = 1,
                   log=print, pause_seconds: float = 0.0) -> dict[str, Any]:
    """Score every candidate on every task. Providers run side by side; each one's cases in turn.

    ``pause_seconds`` spaces one provider's cases out, untimed. Free tiers limit tokens per minute,
    and back-to-back cases otherwise measure the provider's rate-limit waits, not its speed.
    """
    node_modules = _web_node_modules() if "code" in tasks else None
    if "code" in tasks and node_modules is None:
        log("code: skipped - the shared web type-check cache is not installed (run scripts/omnistack.sh up)")

    async def one(candidate: Candidate) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for task in tasks:
            if task == "code" and node_modules is None:
                continue
            collected: list[Run] = []
            for _ in range(max(1, runs)):
                cases = PLAN_CASES if task == "plan" else CODE_CASES
                for case in cases:
                    if collected and pause_seconds:
                        await asyncio.sleep(pause_seconds)
                    collected.append(await (eval_plan(candidate, case) if task == "plan"
                                            else eval_code(candidate, case, node_modules)))
            summary = summarize(collected)
            if not summary["runs"]:
                log(f"{task:<5} {candidate.key:<55} not available ({', '.join(summary['errors'])}); not scored")
                continue
            results[task] = summary
            log(f"{task:<5} {candidate.key:<55} {results[task]['valid']}/{results[task]['runs']} valid, "
                f"score {results[task]['score']}")
        return results

    per_candidate = await asyncio.gather(*(one(c) for c in candidates))
    card: dict[str, Any] = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "tasks": {}}
    for candidate, results in zip(candidates, per_candidate):
        for task, summary in results.items():
            card["tasks"].setdefault(task, {})[candidate.key] = summary
    return card


def configured_candidates() -> list[Candidate]:
    """Every provider the build chain would use, as configured in the environment."""
    from ..intake.provider_resolution import resolve_generation_provider_from_env
    from .fallback import FallbackChainProvider

    previous = os.environ.get(ROUTING_ENV)
    os.environ[ROUTING_ENV] = "fixed"  # evaluate the configured chain, not the last ranking
    try:
        provider, model_id, max_output, timeout = resolve_generation_provider_from_env()
    finally:
        if previous is None:
            os.environ.pop(ROUTING_ENV, None)
        else:
            os.environ[ROUTING_ENV] = previous
    if isinstance(provider, FallbackChainProvider):
        return [Candidate(e.provider, e.model_id, e.max_output_tokens, max(timeout, e.timeout_seconds or 0))
                for e in provider.entries]
    return [Candidate(provider, model_id, max_output, timeout)]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score every configured model provider on the platform's jobs.")
    parser.add_argument("--tasks", default=",".join(TASKS), help="comma-separated: plan,code")
    parser.add_argument("--runs", type=int, default=1, help="repeat each case this many times")
    parser.add_argument("--pause", type=float, default=20.0,
                        help="untimed seconds between one provider's cases, for free-tier rate limits")
    parser.add_argument("--only", default="", help="comma-separated provider ids to score (default: all)")
    args = parser.parse_args(argv)

    tasks = [t for t in (s.strip() for s in args.tasks.split(",")) if t in TASKS]
    candidates = configured_candidates()
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        candidates = [c for c in candidates if c.provider.provider_id in wanted or c.key in wanted]
    print(f"Scoring {len(candidates)} provider(s) on {', '.join(tasks)}: " + ", ".join(c.key for c in candidates))
    card = asyncio.run(evaluate(candidates, tasks, args.runs, pause_seconds=args.pause))
    # Keep scores for providers not re-run this time, so one provider can be re-scored alone.
    previous = load_scorecard()
    for task, entries in (previous.get("tasks") or {}).items():
        for key, summary in entries.items():
            card["tasks"].setdefault(task, {}).setdefault(key, summary)
    path = save_scorecard(card)
    for task in tasks:
        keys = list((card["tasks"].get(task) or {}).keys())
        order = [keys[i] for i in rank_chain(keys, task, card)]
        print(f"\n{task}: route order -> " + " -> ".join(order))
        for key in order:
            s = card["tasks"][task][key]
            print(f"  {key:<55} score {s['score']:<6} valid {s['valid']}/{s['runs']:<3} "
                  f"median {s['median_seconds']} s  {'; '.join(s['errors'])}")
    print(f"\nScorecard: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
