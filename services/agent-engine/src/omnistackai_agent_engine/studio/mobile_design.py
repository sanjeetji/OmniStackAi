"""PC-129: the phone app's screens designed by the model, like the web pages (PC-098).

The web and admin pages have been model-designed after every build; the React Native app kept its
templates. Here each phone screen - the home screen and every list - is redesigned by the model from
its working template, so the model starts from code that already calls the right data hooks,
navigates to the right screens and exports the right component, and only has to make it beautiful:

* **grounded** - the template, the app's design-system components and its brand tokens are in the
  request; the screen must keep its export name and may import only React, React Native, React
  Navigation, safe-area, the icon set, and the relative modules the template already uses;
* **checked** - every redesigned screen is type-checked with the app's own TypeScript (the shared
  mobile cache, as the build does); a screen that fails gets one repair from the compiler's errors;
* **never broken** - a screen that still fails, or could not be checked at all, goes back to its
  template, and the report says why.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Callable

logger = logging.getLogger(__name__)

MARKER = "// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI (phone)"
_ALLOWED_PACKAGES = ("react", "react-native", "@react-navigation/native", "@react-navigation/native-stack",
                     "react-native-safe-area-context", "lucide-react-native")
_IMPORT = re.compile(r"""(?:^|\n)\s*import\s+(?:type\s+)?(?:[^'";]+?\s+from\s+)?['"]([^'"]+)['"]""")
_TSC_LINE = re.compile(r"^(?P<path>[^\r\n(]+?)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<message>.*)$")


@dataclass(frozen=True)
class PhoneScreen:
    app: str  # "apps/mobile"
    path: str  # app-relative, e.g. "src/app/screens/OverviewScreen.tsx"
    export: str  # the component name the navigator imports

    @property
    def full(self) -> str:
        return f"{self.app}/{self.path}"


def is_model_written(path: Path) -> bool:
    try:
        return path.read_text(encoding="utf-8", errors="replace").startswith(MARKER)
    except OSError:
        return False


def expo_apps(root: Path) -> list[str]:
    apps = []
    for app in sorted((root / "apps").glob("*")):
        try:
            deps = json.loads((app / "package.json").read_text())["dependencies"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if "expo" in deps:
            apps.append(f"apps/{app.name}")
    return apps


def plan_screens(root: Path, only: list[str] | None = None) -> list[PhoneScreen]:
    """Every phone app's home screen, then its lists - what a person sees first. Already designed: skipped."""
    screens = []
    for app in expo_apps(root):
        base = root / app
        candidates = [base / "src/app/screens/OverviewScreen.tsx", *sorted(base.glob("src/features/*/ui/*ListScreen.tsx"))]
        for file in candidates:
            if not file.is_file():
                continue
            match = re.search(r"export\s+(?:const|function)\s+(\w+)", file.read_text(encoding="utf-8", errors="replace"))
            if not match:
                continue
            screen = PhoneScreen(app, str(file.relative_to(base)), match.group(1))
            if only is not None:
                if screen.full in only:
                    screens.append(screen)
            elif not is_model_written(file):
                screens.append(screen)
    return screens


def _relative_imports(text: str) -> set[str]:
    return {m for m in _IMPORT.findall(text) if m.startswith(".")}


def kit_imports(app_dir: Path, screen_path: str) -> set[str]:
    """The design system's modules (components, tokens) as this screen would import them."""
    here = (app_dir / screen_path).parent
    found = set()
    for file in [*(app_dir / "src/design-system/components").glob("*.tsx"), app_dir / "src/design-system/tokens.ts"]:
        if file.exists():
            found.add(os.path.relpath(file.with_suffix(""), here).replace(os.sep, "/"))
    return {f if f.startswith(".") else "./" + f for f in found}


def validate(content: str, template: str, export: str, kit: set[str] = frozenset()) -> tuple[bool, str]:
    """Whether a redesigned screen keeps the contract its template has (it may also use the design-system kit)."""
    if not re.search(rf"export\s+(?:const|function)\s+{re.escape(export)}\b", content):
        return False, f"the screen must still export {export}"
    if re.search(r"\brequire\s*\(|\bimport\s*\(", content):
        return False, "dynamic import() and require() are not allowed"
    allowed_relative = _relative_imports(template) | set(kit)
    for module in _IMPORT.findall(content):
        if module.startswith("."):
            if module not in allowed_relative:
                return False, f"it imports {module!r}, which the screen did not use; only these: {sorted(allowed_relative)}"
        elif not any(module == p or module.startswith(p + "/") for p in _ALLOWED_PACKAGES):
            return False, f"it imports {module!r}; only {', '.join(_ALLOWED_PACKAGES)} and the screen's own modules"
    if content.count("{") != content.count("}"):
        return False, "the file is truncated (unbalanced braces)"
    return True, ""


def _clean(raw: str) -> str:
    text = (raw or "").strip()
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    if blocks:
        text = max(blocks, key=len)
    return text.strip() + "\n"


def _request_text(screen: PhoneScreen, template: str, components: dict[str, str], tokens: str, prompt: str,
                  brand: dict[str, Any]) -> str:
    kit = "\n\n".join(f"// {name}\n{source[:1500]}" for name, source in components.items())
    return (
        f"Redesign this React Native (Expo SDK 57, React 19) screen of the phone app for: {prompt[:600]}\n\n"
        f"Brand: {json.dumps({k: brand.get(k) for k in ('name', 'primaryColor', 'accentColor', 'style') if brand.get(k)})}\n\n"
        "Make it look like a polished, modern consumer app: a clear header area, generous spacing, rounded cards "
        "with subtle shadows, readable type hierarchy, icons from lucide-react-native, friendly empty and loading "
        "states, and the brand colour for emphasis. Use the design-system tokens for colours, spacing and radius.\n\n"
        "Hard rules - the screen must keep working:\n"
        f"- keep `export const {screen.export}` (same name, same props) and every data hook, call and "
        "navigation.navigate(...) route the template uses; do not invent data, fields or routes;\n"
        f"- import only from: {', '.join(_ALLOWED_PACKAGES)}, the relative modules the template already imports, "
        "and the design-system components and tokens listed below (same relative style as the template);\n"
        "- no require(), no dynamic import, no web-only APIs (no div, no CSS, no window);\n"
        "- StyleSheet.create for styles; TypeScript that type-checks under strict mode.\n\n"
        f"Design tokens (src/design-system/tokens.ts):\n{tokens[:2500]}\n\n"
        f"Design-system components you may use (their source, shortened):\n{kit[:6000]}\n\n"
        f"The working template (src path {screen.path}):\n```tsx\n{template}\n```\n\n"
        "Return only the complete new file in one ```tsx block."
    )


async def _ask(provider: Any, model_id: str | None, text: str, timeout: float) -> str:
    from ..codegen.llm_ui import _resolve_target
    from ..model_gateway.contracts import ChatRole, GenerateRequest, Message

    target, max_output = _resolve_target(provider, model_id)
    request = GenerateRequest(
        request_id=f"phone-ui-{uuid.uuid4().hex[:12]}", model=target,
        messages=(Message(ChatRole.SYSTEM, "You are an expert React Native UI designer. Respond only with code."),
                  Message(ChatRole.USER, text)),
        max_output_tokens=max(1024, max_output), timeout_seconds=timeout)
    response = await provider.generate(request)
    return getattr(response, "text", "") or ""


def typecheck(app_dir: Path, runner: Callable[[list[str], Path], tuple[int, str]] | None = None) -> dict[str, list[str]] | None:
    """tsc errors per app-relative file; None when the app cannot be checked here."""
    from ..intake.build_verify import MOBILE_NODE_MODULES_ENV

    source = os.environ.get(MOBILE_NODE_MODULES_ENV) or str(Path.home() / ".omnistackai" / "mobile-typecheck" / "node_modules")
    link = app_dir / "node_modules"
    linked = False
    if runner is None:
        if not link.exists():
            if not (Path(source) / ".bin" / "tsc").exists():
                return None
            link.symlink_to(Path(source).resolve(), target_is_directory=True)
            linked = True

        def runner(argv: list[str], cwd: Path) -> tuple[int, str]:
            done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=600, check=False)
            return done.returncode, done.stdout + done.stderr
    try:
        code, output = runner([str(app_dir / "node_modules" / ".bin" / "tsc"), "--noEmit", "--pretty", "false"], app_dir)
    finally:
        if linked:
            link.unlink(missing_ok=True)
    errors: dict[str, list[str]] = {}
    for line in output.splitlines():
        match = _TSC_LINE.match(line.strip())
        if match:
            errors.setdefault(match["path"].strip(), []).append(f"L{match['line']} {match['code']}: {match['message']}")
    if code != 0 and not errors:
        return {"*": [output[-300:]]}
    return errors


async def design_phone_screens(
    repo_dir: str | os.PathLike[str], prompt: str, provider: Any, *, model_id: str | None = None,
    only: list[str] | None = None, timeout_seconds: float = 240.0, cancelled: Callable[[], bool] = lambda: False,
    runner: Any = None,
) -> AsyncIterator[dict]:
    """Design the phone app's screens; events: ``page`` (designed or kept_template, with a reason)."""
    root = Path(repo_dir)
    try:
        brand = json.loads((root / "brand.json").read_text())
    except (OSError, ValueError):
        brand = {}
    by_app: dict[str, list[PhoneScreen]] = {}
    for screen in plan_screens(root, only):
        by_app.setdefault(screen.app, []).append(screen)
    for app, screens in by_app.items():
        base = root / app
        tokens = (base / "src/design-system/tokens.ts").read_text(errors="replace") if (base / "src/design-system/tokens.ts").exists() else ""
        components = {p.name: p.read_text(errors="replace") for p in sorted((base / "src/design-system/components").glob("*.tsx"))}
        templates: dict[str, str] = {}
        written: list[PhoneScreen] = []
        for screen in screens:
            if cancelled():
                break
            template = (base / screen.path).read_text(encoding="utf-8")
            try:
                content = _clean(await _ask(provider, model_id, _request_text(screen, template, components, tokens, prompt, brand),
                                            timeout_seconds))
            except Exception as error:  # noqa: BLE001 - a refused or failed call keeps the template
                yield {"phase": "page", "path": screen.full, "status": "kept_template",
                       "reason": f"the model could not answer ({type(error).__name__})"}
                continue
            kit = kit_imports(base, screen.path)
            ok, why = validate(content, template, screen.export, kit)
            if not ok:
                yield {"phase": "page", "path": screen.full, "status": "kept_template", "reason": why}
                continue
            templates[screen.path] = template
            (base / screen.path).write_text(f"{MARKER} ({model_id or 'model'})\n{content}", encoding="utf-8")
            written.append(screen)
        if not written:
            continue
        errors = typecheck(base, runner)
        if errors is None:
            for screen in written:
                (base / screen.path).write_text(templates[screen.path], encoding="utf-8")
                yield {"phase": "page", "path": screen.full, "status": "kept_template",
                       "reason": "it could not be type-checked here (no phone type-check cache)"}
            continue
        failing = [s for s in written if errors.get(s.path) or "*" in errors]
        for screen in failing:  # one repair, from the compiler's own words
            current = (base / screen.path).read_text(encoding="utf-8").split("\n", 1)[1]
            try:
                fixed = _clean(await _ask(provider, model_id, (
                    f"This React Native screen does not type-check. Fix only these errors and return the whole file "
                    f"in one ```tsx block, keeping the same rules (imports, export {screen.export}):\n"
                    + "\n".join(errors.get(screen.path) or errors.get("*") or []) + f"\n\n```tsx\n{current}\n```"), timeout_seconds))
                ok, _why = validate(fixed, templates[screen.path], screen.export, kit_imports(base, screen.path))
                if ok:
                    (base / screen.path).write_text(f"{MARKER} ({model_id or 'model'}; repaired)\n{fixed}", encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
        errors = typecheck(base, runner) if failing else errors
        for screen in written:
            if errors is None or errors.get(screen.path) or "*" in (errors or {}):
                (base / screen.path).write_text(templates[screen.path], encoding="utf-8")
                yield {"phase": "page", "path": screen.full, "status": "kept_template",
                       "reason": "the model's screen did not type-check and could not be repaired"}
            else:
                yield {"phase": "page", "path": screen.full, "status": "designed"}
