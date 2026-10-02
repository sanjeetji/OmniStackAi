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
#: The same idea for the Expo apps (founder, 2026-09-26: "what about the app side?"). Mobile apps
#: used to be checked only when someone had installed their dependencies, which in the build path
#: meant never. The cache's own package.json sits beside it so a mismatch is detected, not guessed.
MOBILE_NODE_MODULES_ENV = "OMNISTACKAI_MOBILE_NODE_MODULES"

#: "auto" verifies when dependencies are already there or can be linked; "install" also allows a
#: `pnpm install`, which is slow enough to be a choice; "off" disables it.
MODE_ENV = "OMNISTACKAI_BUILD_VERIFY"

_MAX_REASON_CHARS = 300



#: PC-125: what a web app's "clean" means.
CHECKS = ("types: every file type-checks with the app's own TypeScript",
          "links: every link and navigation goes to a page of this app",
          "text colours: no text is set in a background colour")

def _mode() -> str:
    value = (os.environ.get(MODE_ENV) or "auto").strip().lower()
    return value if value in {"auto", "install", "off"} else "auto"


def skipped(reason: str) -> dict[str, Any]:
    """A build that was not type-checked, and the reason a person can act on."""
    return {"status": "skipped", "reason": reason[:_MAX_REASON_CHARS]}


def next_apps_for(ir: Any) -> list[tuple[str, Any, str]]:
    """Every Next.js app a single-project build lays out: (directory, its IR, "web" | "admin").

    PC-097: taken from the assembler's own layout decision, so the apps repaired are exactly the
    apps generated - including an admin-only project whose console lives in apps/web.
    """
    from ..codegen.assembler import assembled_targets
    from ..codegen.adapter import GenerationTarget

    flavours = {GenerationTarget.NEXTJS_WEB.value: "web", GenerationTarget.NEXTJS_ADMIN.value: "admin"}
    try:
        apps = assembled_targets(ir)
    except (TypeError, ValueError):
        return []
    return [(app.directory, ir, flavours[app.target]) for app in apps if app.target in flavours]


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
    next_apps: list[tuple[str, Any, str]] | None = None,
) -> dict[str, Any]:
    """Type-check every generated Next.js app, repair what the model wrote, and report what happened.

    PC-097: the repair loop used to cover apps/web only; a model-written page in the admin console
    or an ecosystem role app was type-checked at most, never repaired or reverted, so it could ship
    broken. Now every Next.js app goes through the same loop with its own IR and its own template
    fallbacks. ``next_apps`` lists them (directory, IR, "web" | "admin"); by default they are the
    apps the assembler lays out for ``ir``. The main app's result is the top-level record, the
    others are reported per surface, as before.

    Returns a JSON-safe record; never raises for an ordinary failure to verify, because a build that
    produced a repository is a successful build whether or not we could compile it.
    """
    mode = _mode()
    if mode == "off":
        return skipped(f"type-checking is turned off ({MODE_ENV}=off)")

    root = Path(target_dir)
    apps = next_apps if next_apps is not None else next_apps_for(ir)
    apps = [app for app in apps if (root / app[0]).is_dir()]
    repairable = {relative for relative, _ir, _flavour in apps} if provider is not None else set()

    # R-561: the other surfaces are checked whatever happens to the web app. The Next.js apps the
    # repair loop takes are left to it, so nothing is compiled twice.
    surfaces = verify_other_surfaces(target_dir, skip=repairable)

    if provider is None:
        # Without a model there is nobody to repair a broken file, and compiling only to report
        # errors the user cannot act on inside the product is not worth a minute of their build.
        return _with_surfaces(skipped("this build ran without a model provider, so the web app was not type-checked"), surfaces)

    if not apps:
        return _with_surfaces(skipped("this project has no web app to type-check"), surfaces)

    from ..verify import VerifyError, ensure_web_dependencies

    source = os.environ.get(NODE_MODULES_ENV) or None
    if source is not None and Path(source).name != "node_modules":
        # TypeScript resolves through the symlink's real path, and nested lookups only recognise a
        # directory literally named `node_modules`. Pointed at anything else, `next`'s own types
        # become unresolvable and tsc reports implicit-any errors in code that is perfectly correct.
        # Reporting invented errors is worse than reporting none, so this refuses instead.
        return _with_surfaces(skipped(
            f"{NODE_MODULES_ENV} must point at a directory named 'node_modules' (got "
            f"'{Path(source).name}'); type resolution silently breaks otherwise, so nothing was checked"
        ), surfaces)

    from ..codegen import compile_and_repair_sync

    primary = "apps/web" if any(relative == "apps/web" for relative, _i, _f in apps) else apps[0][0]
    web_deps = _dependency_set(root / primary / "package.json")
    records: dict[str, dict[str, Any]] = {}
    for relative, app_ir, flavour in apps:
        app_dir = root / relative
        if mode == "auto" and source is None and not (app_dir / "node_modules").exists():
            records[relative] = skipped(
                "dependencies are not installed, so the web app was not type-checked. Set "
                f"{NODE_MODULES_ENV} to a warm node_modules, or {MODE_ENV}=install to install them"
            )
            continue
        if (source is not None and relative != primary and not (app_dir / "node_modules").exists()
                and _dependency_set(app_dir / "package.json") != web_deps):
            # The one warm cache is only correct for an app with exactly the same dependencies;
            # linking it anyway is how correct code gets reported as broken.
            records[relative] = skipped("this app's dependencies differ from the shared cache, so it was not type-checked")
            continue
        try:
            how = ensure_web_dependencies(app_dir, node_modules_source=source)
            report = compile_and_repair_sync(
                repo_dir=str(target_dir),
                ir=app_ir,
                user_prompt=prompt,
                provider=provider,
                model_id=model_id,
                # Every page the model wrote is repairable, whichever flags produced it: a page is
                # taken as model-written by its marker, never by a flag.
                synthesize_screens=True,
                outcomes=outcomes,
                timeout_seconds=timeout_seconds,
                web_prefix=f"{relative}/",
                flavour=flavour,
            )
        except VerifyError as error:
            records[relative] = skipped(f"the type-checker could not run: {error}")
            continue
        records[relative] = {
            "status": "clean" if report.final_ok else "failing",
            # PC-125: what "clean" covers - the build report says what was verified, not just a verdict.
            "checks": list(CHECKS),
            "dependencies": how,
            "repaired": list(report.repaired),
            "reverted": list(report.reverted),
            # Deterministic files the repair loop reports but will never rewrite — it only touches
            # what a model wrote. This is precisely where R-549's defect lived, so it is carried out
            # to the user rather than left in a report nobody reads: a template bug affects every
            # project generated until someone fixes the generator.
            "generator_failures": list(report.untouched_failures),
        }

    changed = [rec for rec in records.values() if rec.get("repaired") or rec.get("reverted")]
    commit_sha = None
    if changed:
        from ..git_service import commit_all

        commit_sha = commit_all(
            str(target_dir),
            author_name=author_name,
            author_email=author_email,
            message="fix(ui): compile-level repair of model-written pages",
        ).commit_sha
    for rec in records.values():
        if rec.get("status") == "skipped":
            continue
        if rec.get("repaired") or rec.get("reverted"):
            rec["repair_commit"] = commit_sha
            if rec["status"] == "clean":
                rec["status"] = "repaired"
        rec["summary"] = _summary(rec)

    record = records.pop(primary)
    for relative, rec in records.items():
        surfaces[relative] = rec
    return _with_surfaces(record, surfaces)


def _with_surfaces(record: dict[str, Any], surfaces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Attach the other surfaces, and let a failure in one of them set the overall verdict.

    Reported per surface rather than as one verdict: "your project does not compile" is not
    something a person can act on, and it hides which of four things is broken.
    """
    if not surfaces:
        return record
    record["surfaces"] = surfaces
    broken = sorted(name for name, result in surfaces.items() if result.get("status") == "failing")
    if broken:
        record["status"] = "failing"
        record["failing_surfaces"] = broken
        record["summary"] = (
            f"{', '.join(broken)} did not compile. Every file in "
            f"{'these' if len(broken) > 1 else 'it'} is generated by OmniStackAI, so this is a "
            "fault in the generator rather than in your project — please report it."
        )
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
        return "The generated code was type-checked and compiled cleanly, and every link goes to a page that exists."
    parts = []
    if repaired:
        parts.append(f"{repaired} page{'s' if repaired != 1 else ''} repaired (compiler errors, links to pages "
                     "that do not exist, or text in a background colour)")
    if reverted:
        parts.append(
            f"{reverted} page{'s' if reverted != 1 else ''} replaced with the built-in template after repairs failed"
        )
    detail = " and ".join(parts) if parts else "no changes were needed"
    if record["status"] == "failing":
        return f"The generated code still does not compile after {detail}."
    return f"The generated code was type-checked: {detail}."


# --- Every other surface (R-561) -------------------------------------------------------------
#
# R-560 compiled `apps/web` and nothing else, so the admin console, the React Native app and the
# backend were never built by anyone. That is how a generated Go backend came to ship unable to
# start at all: it has `go.mod` and no `go.sum`, and its own README told the user to run `go run .`,
# which fails on every dependency.
#
# None of these surfaces has a model-written file — the model only writes web pages — so nothing
# here is ever repaired. A failure in a file we generate ourselves is our bug in every project built
# from that template, and is reported as one.

import json
import shutil
import subprocess

#: Surfaces whose dependency set is generated identically to the web app's, so the one warm
#: node_modules is correct for them. Checked rather than assumed: linking a cache built from a
#: different dependency set is how a correct file gets reported as broken.
_SHARES_WEB_DEPENDENCIES = ("apps/admin",)


def _next_surfaces(root: Path) -> list[str]:
    """Every Next.js app besides the main web app (which the repair loop checks itself)."""
    found = list(_SHARES_WEB_DEPENDENCIES) if (root / "apps" / "admin").is_dir() else []
    apps_root = root / "apps"
    for app_dir in sorted(apps_root.iterdir()) if apps_root.is_dir() else ():
        relative = f"apps/{app_dir.name}"
        deps = _dependency_set(app_dir / "package.json") or {}
        if app_dir.name != "web" and relative not in found and "next" in deps and "expo" not in deps:
            found.append(relative)
    return found


def _dependency_set(package_json: Path) -> dict | None:
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {**data.get("dependencies", {}), **data.get("devDependencies", {})}


def _run(argv: list[str], cwd: Path, timeout: float = 300.0) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        return 1, str(error)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


def _typecheck(app_dir: Path) -> dict[str, Any]:
    tsc = app_dir / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        return skipped("dependencies are not installed for this app, so it was not type-checked")
    code, output = _run([str(tsc), "--noEmit", "--pretty", "false"], app_dir)
    if code == 0:
        return {"status": "clean"}
    lines = [line.strip() for line in output.splitlines() if "error" in line.lower()][:5]
    return {"status": "failing", "errors": lines}


def verify_other_surfaces(
    target_dir: str | os.PathLike[str], *, skip: set[str] | frozenset[str] = frozenset()
) -> dict[str, dict[str, Any]]:
    """Compile the admin console, the mobile app and the backend, each reporting for itself.

    One combined verdict would hide which surface is broken, and "your project does not compile" is
    not something a person can act on.
    """
    root = Path(target_dir)
    surfaces: dict[str, dict[str, Any]] = {}
    web_deps = _dependency_set(root / WEB_PREFIX / "package.json")
    source = os.environ.get(NODE_MODULES_ENV) or None
    shared_ok = source is not None and Path(source).name == "node_modules"

    # PC-008, found live: only apps/admin was checked, so a role surface an ecosystem plan produced
    # (a clinic's `provider` app) shipped a page importing a component that does not exist, and
    # the first anyone heard of it was a failed production build. Every Next app is checked now.
    for relative in _next_surfaces(root):
        app_dir = root / relative
        if not app_dir.is_dir() or relative in skip:
            continue
        if shared_ok and not (app_dir / "node_modules").exists():
            # Only when the dependency sets match exactly. They are generated from one template
            # today, but checking costs nothing and a divergence would otherwise surface as
            # invented type errors in correct code.
            if web_deps is not None and _dependency_set(app_dir / "package.json") == web_deps:
                try:
                    (app_dir / "node_modules").symlink_to(Path(source).resolve(), target_is_directory=True)
                except OSError:
                    pass
        surfaces[relative] = _typecheck(app_dir)

    # Every Expo app, not only `apps/mobile`: an ecosystem can hold a courier app and a customer
    # app (R-562). Their dependencies are Expo and React Native, nothing like the web app's, so they
    # get their own cache — linked only when the dependency set matches it exactly.
    mobile_source = os.environ.get(MOBILE_NODE_MODULES_ENV) or None
    mobile_ok = mobile_source is not None and Path(mobile_source).name == "node_modules"
    mobile_deps = _dependency_set(Path(mobile_source).parent / "package.json") if mobile_ok else None
    apps_root = root / "apps"
    for app_dir in sorted(apps_root.iterdir()) if apps_root.is_dir() else ():
        deps = _dependency_set(app_dir / "package.json")
        if not deps or "expo" not in deps:
            continue
        link = app_dir / "node_modules"
        linked = False
        if mobile_ok and mobile_deps == deps and not link.exists():
            try:
                link.symlink_to(Path(mobile_source).resolve(), target_is_directory=True)
                linked = True
            except OSError:
                pass
        try:
            surfaces[f"apps/{app_dir.name}"] = _typecheck(app_dir)
        finally:
            # The shared cache must never be written by a project's own install (Expo's preview
            # installs in place), so the link lives only as long as the check.
            if linked:
                link.unlink(missing_ok=True)

    api = root / "services" / "api"
    if api.is_dir():
        surfaces["services/api"] = _verify_backend(api)
    return surfaces


def _verify_backend(api: Path) -> dict[str, Any]:
    """Whatever can be checked without a network or an install, plus a full build when allowed."""
    if (api / "go.mod").is_file():
        if shutil.which("go") is None:
            return skipped("Go is not installed, so the backend was not compiled")
        # Syntax first: gofmt parses every file and needs no modules, so it works with no network.
        code, output = _run(["gofmt", "-l", "."], api)
        unformatted = [line for line in output.splitlines() if line.strip()]
        if code != 0:
            return {"status": "failing", "errors": [line.strip() for line in output.splitlines()[:5]]}
        if _mode() != "install":
            # A real build needs `go mod tidy` first, which downloads modules. That is a decision,
            # not something to do quietly inside someone's build.
            return {
                "status": "parsed",
                "reason": f"Go sources parse; set {MODE_ENV}=install to resolve modules and compile",
                "unformatted": unformatted,
            }
        tidy_code, tidy_out = _run(["go", "mod", "tidy"], api, timeout=600.0)
        if tidy_code != 0:
            return skipped(f"go mod tidy failed, so the backend was not compiled: {tidy_out[-200:]}")
        build_code, build_out = _run(["go", "build", "./..."], api, timeout=600.0)
        if build_code == 0:
            return {"status": "clean"}
        return {"status": "failing", "errors": [line.strip() for line in build_out.splitlines()[:5]]}

    if (api / "requirements.txt").is_file():
        # compileall parses every module without installing anything, so it always runs.
        code, output = _run([os.sys.executable, "-m", "compileall", "-q", str(api)], api)
        if code == 0:
            return {"status": "parsed", "reason": "every Python module parses; imports need an install to check"}
        return {"status": "failing", "errors": [line.strip() for line in output.splitlines()[:5]]}

    if (api / "tsconfig.json").is_file():
        return _typecheck(api)
    return skipped("this backend has no checker yet")
