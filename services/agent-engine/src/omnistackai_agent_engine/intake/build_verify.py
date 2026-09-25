"""Compile what we generated, before the user does (R-560).

The compile-verify-repair loop has existed since R-466 and works: `compile_and_repair` runs the real
`tsc`, feeds each model-written file's own diagnostics back to the model, recompiles, and reverts
anything still failing to its deterministic template. Its only caller was an opt-in CLI
(`task agent-engine:ui:synthesize`). A user building through the console reached none of it.

The cost of that gap is measurable: R-549 shipped `lib/brand.ts` with two unnecessary
`@ts-expect-error` directives, which are themselves a compile error, and `next build` failed on
**every generated web app for nine tasks**. Every test of that change read the generated source and
agreed it was correct. None of them compiled it.

This module puts the CLI's proven sequence on the path both build twins share, with three rules the
CLI did not need:

* **A build is never failed by verification.** If the toolchain is missing the project is still
  generated and committed. Refusing to hand over a repository because we could not type-check it
  would trade a real deliverable for a diagnostic.
* **Skipping is never silent.** Every outcome carries a reason in plain words, and it travels to the
  console the same way R-559's substitutions do. "We did not check this, and here is why" is a
  different message from saying nothing.
* **Installing dependencies is a decision, not a side effect.** `pnpm install` on every build would
  add minutes to a path a person is watching. Verification runs for free when `node_modules` is
  already present or can be linked from a warm one, and says so plainly when it cannot.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

#: Where the generated web app lives inside the monorepo.
WEB_PREFIX = "apps/web"

#: An existing `node_modules` to symlink instead of installing. Documented since R-466 and, until
#: this task, read by nothing outside the CLI.
NODE_MODULES_ENV = "OMNISTACKAI_WEB_NODE_MODULES"

#: "auto" verifies when dependencies are already there or can be linked; "install" also allows a
#: `pnpm install`, which is slow enough to be a choice; "off" disables it.
MODE_ENV = "OMNISTACKAI_BUILD_VERIFY"

_MAX_REASON_CHARS = 300


def _mode() -> str:
    value = (os.environ.get(MODE_ENV) or "auto").strip().lower()
    return value if value in {"auto", "install", "off"} else "auto"


def skipped(reason: str) -> dict[str, Any]:
    """A build that was not type-checked, and the reason a person can act on."""
    return {"status": "skipped", "reason": reason[:_MAX_REASON_CHARS]}


def verify_and_repair_build(
    *,
    target_dir: str | os.PathLike[str],
    ir: Any,
    prompt: str,
    provider: Any | None,
    model_id: str | None = None,
    synthesize_screens: bool = False,
    author_name: str,
    author_email: str,
    outcomes: list | None = None,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Type-check the generated web app, repair what the model wrote, and report what happened.

    Returns a JSON-safe record; never raises for an ordinary failure to verify, because a build that
    produced a repository is a successful build whether or not we could compile it.
    """
    mode = _mode()
    if mode == "off":
        return skipped(f"type-checking is turned off ({MODE_ENV}=off)")
    if provider is None:
        # Without a model there is nobody to repair a broken file, and compiling only to report
        # errors the user cannot act on inside the product is not worth a minute of their build.
        return skipped("this build ran without a model provider, so generated code was not type-checked")

    web_dir = Path(target_dir) / WEB_PREFIX
    if not web_dir.is_dir():
        return skipped("this project has no web app to type-check")

    from ..verify import VerifyError, ensure_web_dependencies

    source = os.environ.get(NODE_MODULES_ENV) or None
    if source is not None and Path(source).name != "node_modules":
        # TypeScript resolves through the symlink's real path, and nested lookups only recognise a
        # directory literally named `node_modules`. Pointed at anything else, `next`'s own types
        # become unresolvable and tsc reports implicit-any errors in code that is perfectly correct.
        # Reporting invented errors is worse than reporting none, so this refuses instead.
        return skipped(
            f"{NODE_MODULES_ENV} must point at a directory named 'node_modules' (got "
            f"'{Path(source).name}'); type resolution silently breaks otherwise, so nothing was checked"
        )
    if mode == "auto" and source is None and not (web_dir / "node_modules").exists():
        return skipped(
            "dependencies are not installed, so the generated code was not type-checked. Set "
            f"{NODE_MODULES_ENV} to a warm node_modules, or {MODE_ENV}=install to install them"
        )
    try:
        how = ensure_web_dependencies(web_dir, node_modules_source=source)
    except VerifyError as error:
        return skipped(f"dependencies could not be prepared, so nothing was type-checked: {error}")

    from ..codegen import compile_and_repair_sync

    try:
        report = compile_and_repair_sync(
            repo_dir=str(target_dir),
            ir=ir,
            user_prompt=prompt,
            provider=provider,
            model_id=model_id,
            synthesize_screens=synthesize_screens,
            outcomes=outcomes,
            timeout_seconds=timeout_seconds,
        )
    except VerifyError as error:
        return skipped(f"the type-checker could not run, so nothing was verified: {error}")

    record: dict[str, Any] = {
        "status": "clean" if report.final_ok else "failing",
        "dependencies": how,
        "repaired": list(report.repaired),
        "reverted": list(report.reverted),
        # Deterministic files the repair loop reports but will never rewrite — it only touches what
        # a model wrote. This is precisely where R-549's defect lived, so it is carried out to the
        # user rather than left in a report nobody reads: a template bug affects every project
        # generated until someone fixes the generator.
        "generator_failures": list(report.untouched_failures),
    }
    if report.repaired or report.reverted:
        from ..git_service import commit_all

        commit = commit_all(
            str(target_dir),
            author_name=author_name,
            author_email=author_email,
            message="fix(ui): compile-level repair of model-written pages",
        )
        record["repair_commit"] = commit.commit_sha
        record["status"] = "repaired" if report.final_ok else "failing"
    record["summary"] = _summary(record)
    return record


def _summary(record: dict[str, Any]) -> str:
    """One sentence for the console. Counts rather than paths: a user wants the shape, not a list."""
    repaired, reverted = len(record.get("repaired", ())), len(record.get("reverted", ()))
    generator = len(record.get("generator_failures", ()))
    if generator:
        # Said first and said plainly. A fault in a file we generate ourselves is our bug in every
        # project built from that template, not something this user did or can fix.
        return (
            f"{generator} file{'s' if generator != 1 else ''} that OmniStackAI generates itself did "
            "not compile. This is a fault in the generator, not in your project — please report it."
        )
    if record["status"] == "clean" and not repaired and not reverted:
        return "The generated code was type-checked and compiled cleanly."
    parts = []
    if repaired:
        parts.append(f"{repaired} page{'s' if repaired != 1 else ''} repaired from the compiler's errors")
    if reverted:
        parts.append(
            f"{reverted} page{'s' if reverted != 1 else ''} replaced with the built-in template after repairs failed"
        )
    detail = " and ".join(parts) if parts else "no changes were needed"
    if record["status"] == "failing":
        return f"The generated code still does not compile after {detail}."
    return f"The generated code was type-checked: {detail}."
