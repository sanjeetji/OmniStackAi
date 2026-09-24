"""Code-edit agent: change a project's real source files by chat (Phase T, T-4 / R-525).

Template projects are hand-built code with no Application IR, so the IR delta engine cannot edit
them (and it can only ever add). This agent works on the files themselves:

1. **select**: the model reads the request, ``omnistack.json`` and a file index, and names the files
   it needs (JSON ``{"plan", "files"}``);
2. **edit**: given those files, it answers in a line-delimited block format (not JSON: code inside
   JSON strings is where models fail) with WRITE / REPLACE / DELETE operations;
3. **validate + apply**: every operation is checked (paths, sizes, exact single matches) and computed
   in memory before anything is written;
4. **verify**: the touched apps are type-checked or syntax-checked where the toolchain exists; one
   repair round gets the errors; if checks still fail every touched file is restored;
5. **commit**: only the touched paths are staged (``git add -A -- <paths>``), never the whole tree,
   because a preview leaves untracked ``node_modules`` behind.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from ..model_gateway import ChatRole, GenerateRequest, Message, ModelProvider, ModelRef

MAX_SELECTED_FILES = 12
MAX_OPERATIONS = 25
MAX_FILE_BYTES = 200_000
MAX_FILE_CHARS_SHOWN = 40_000
MAX_TOTAL_CHARS_SHOWN = 90_000
MAX_INDEX_ENTRIES = 1_500
MAX_ERROR_LINES = 30
_REQUEST_PREFIX = "r525-code-edit"

_SKIP_DIRS = frozenset({".git", "node_modules", ".next", ".turbo", "dist", "build", ".venv", "__pycache__", "coverage"})
_BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".woff", ".woff2", ".ttf", ".otf",
    ".pdf", ".zip", ".gz", ".mp4", ".mp3", ".wasm", ".lockb",
})
_LOCKFILES = frozenset({"pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lockb"})
_DIRECTIVE = re.compile(r"^@@@ (SUMMARY|WRITE|REPLACE|FIND|WITH|DELETE|END)\b ?(.*)$")

# A raw anchor to a root-relative path (href="/x") escapes a UI app's base path; next/link adds it.
_RAW_ROOT_ANCHOR = re.compile(r"""<a\b[^>]*\bhref\s*=\s*\{?\s*["'`]/(?!/)""")
_UI_KINDS = frozenset({"web", "admin", "pwa"})
_UI_SOURCE_SUFFIXES = frozenset({".jsx", ".tsx", ".js", ".ts", ".mdx"})

_SOURCE_SUFFIXES = frozenset({".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"})
_TOP_LEVEL_DECL = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s*\*?\s*|(?:const|let|var|class)\s+)([A-Za-z_$][\w$]*)"
)

_AUTHOR_NAME = "OmniStackAI"
_AUTHOR_EMAIL = "agent@omnistackai.internal"


class CodeEditError(Exception):
    """The edit could not be produced, applied or verified. Nothing was committed."""


@dataclass(frozen=True)
class EditOp:
    kind: str  # "write" | "replace" | "delete"
    path: str
    content: str | None = None  # write
    find: str | None = None  # replace
    replacement: str | None = None  # replace


@dataclass(frozen=True)
class EditReply:
    summary: str
    ops: tuple[EditOp, ...]


@dataclass
class Verification:
    errors: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"passed": not self.errors, "checked": self.checked, "not_checked": self.skipped, "errors": self.errors}


# --- reply parsing ---------------------------------------------------------------------------------


def parse_edit_reply(text: str) -> EditReply:
    """Parse the line-delimited edit format. Raises CodeEditError with a reason the model can act on."""

    if not isinstance(text, str) or not text.strip():
        raise CodeEditError("the reply was empty")
    lines = text.replace("\r\n", "\n").split("\n")
    # Tolerate a surrounding markdown fence.
    while lines and lines[0].strip().startswith("```"):
        lines.pop(0)
    summary_lines: list[str] = []
    ops: list[EditOp] = []
    ended = False
    mode: str | None = None
    buffer: list[str] = []
    current: dict[str, Any] = {}

    def flush() -> None:
        nonlocal buffer, mode, current
        body = "\n".join(buffer)
        if mode == "SUMMARY":
            summary_lines.append(body.strip())
        elif mode == "WRITE":
            content = body if body.endswith("\n") or not body else body + "\n"
            ops.append(EditOp("write", current["path"], content=content))
        elif mode == "FIND":
            current["find"] = body
        elif mode == "WITH":
            if "find" not in current:
                raise CodeEditError(f"REPLACE {current.get('path')}: WITH without FIND")
            ops.append(EditOp("replace", current["path"], find=current["find"], replacement=body))
        elif mode == "REPLACE" and body.strip():
            raise CodeEditError(f"REPLACE {current.get('path')}: expected @@@ FIND before any text")
        buffer = []

    for line in lines:
        match = _DIRECTIVE.match(line)
        if not match:
            if ended:
                if line.strip() and not line.strip().startswith("```"):
                    raise CodeEditError("text after @@@ END")
                continue
            if mode is None:
                # Small local models almost always open with a sentence ("Sure, here is the
                # change:") before the first directive. Skip anything before it rather than
                # refusing the whole reply (R-530).
                continue
            buffer.append(line)
            continue
        directive, arg = match.group(1), match.group(2).strip()
        flush()
        if directive == "END":
            ended = True
            mode = None
            continue
        if directive in ("WRITE", "REPLACE", "DELETE") and not arg:
            raise CodeEditError(f"@@@ {directive} needs a file path")
        if directive == "DELETE":
            ops.append(EditOp("delete", arg))
            mode = None
            current = {}
        elif directive in ("WRITE", "REPLACE"):
            current = {"path": arg}
            mode = directive
        elif directive == "FIND":
            if mode not in ("REPLACE",):
                raise CodeEditError("@@@ FIND must follow @@@ REPLACE <path>")
            mode = "FIND"
        elif directive == "WITH":
            if mode != "FIND":
                raise CodeEditError("@@@ WITH must follow @@@ FIND")
            mode = "WITH"
        else:  # SUMMARY
            mode = "SUMMARY"
    if not ended:
        raise CodeEditError("the reply was cut off before @@@ END; make a smaller change or use REPLACE instead of WRITE")
    if not ops:
        raise CodeEditError("the reply contains no WRITE, REPLACE or DELETE operations")
    summary = " ".join(part for part in summary_lines if part).strip()
    if not summary:
        # A missing summary is cosmetic when the operations themselves parsed; describe them
        # rather than throwing the work away.
        summary = "Changed " + ", ".join(dict.fromkeys(op.path for op in ops))
    if len(ops) > MAX_OPERATIONS:
        raise CodeEditError(f"too many operations ({len(ops)}); at most {MAX_OPERATIONS}")
    return EditReply(summary=summary[:600], ops=tuple(ops))


# --- repository helpers ----------------------------------------------------------------------------


def _safe_path(repo: Path, raw: str) -> tuple[str, Path]:
    cleaned = raw.strip()
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    rel = PurePosixPath(cleaned)
    if not cleaned or rel.is_absolute() or ".." in rel.parts or "\\" in raw:
        raise CodeEditError(f"{raw!r} is not a relative path inside the project")
    if any(part in _SKIP_DIRS for part in rel.parts):
        raise CodeEditError(f"{rel} is inside a generated or tool directory and cannot be edited")
    name = rel.name
    if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
        raise CodeEditError(f"{rel}: real .env files are never edited; use .env.example")
    if name in _LOCKFILES:
        raise CodeEditError(f"{rel}: lockfiles are regenerated by the package manager, not edited")
    target = (repo / rel).resolve()
    if repo.resolve() not in target.parents:
        raise CodeEditError(f"{rel} is outside the project")
    return rel.as_posix(), target


def project_file_index(repo_dir: str | os.PathLike[str]) -> list[tuple[str, int]]:
    """(path, bytes) for the project's editable text files, sorted, bounded."""

    root = Path(repo_dir)
    entries: list[tuple[str, int]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".git"))
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix.lower() in _BINARY_SUFFIXES or name in _LOCKFILES or path.is_symlink():
                continue
            if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
                continue
            entries.append((path.relative_to(root).as_posix(), path.stat().st_size))
            if len(entries) >= MAX_INDEX_ENTRIES:
                return entries
    return entries


def compute_changes(
    repo_dir: str | os.PathLike[str], ops: tuple[EditOp, ...], *, truncated: frozenset[str] = frozenset()
) -> dict[str, str | None]:
    """Validate operations and return the new content of every touched path (None = delete).

    Operations apply in order, so a REPLACE can follow a WRITE of the same file. Nothing is written.
    """

    repo = Path(repo_dir)
    state: dict[str, str | None] = {}
    for op in ops:
        rel, target = _safe_path(repo, op.path)

        def current() -> str | None:
            if rel in state:
                return state[rel]
            if target.is_file():
                try:
                    return target.read_text(encoding="utf-8")
                except UnicodeDecodeError as error:
                    raise CodeEditError(f"{rel} is not a text file") from error
            return None

        if op.kind == "write":
            if rel in truncated:
                raise CodeEditError(f"{rel} was only shown in part; change it with REPLACE, not WRITE")
            if len((op.content or "").encode("utf-8")) > MAX_FILE_BYTES:
                raise CodeEditError(f"{rel} would exceed {MAX_FILE_BYTES} bytes")
            state[rel] = op.content or ""
        elif op.kind == "replace":
            text = current()
            if text is None:
                raise CodeEditError(f"REPLACE {rel}: the file does not exist (use WRITE to create it)")
            find = op.find or ""
            if not find.strip():
                raise CodeEditError(f"REPLACE {rel}: FIND is empty")
            count = text.count(find)
            if count != 1:
                raise CodeEditError(
                    f"REPLACE {rel}: FIND text occurs {count} times; it must be copied exactly from the file and occur once"
                )
            updated = text.replace(find, op.replacement or "", 1)
            if len(updated.encode("utf-8")) > MAX_FILE_BYTES:
                raise CodeEditError(f"{rel} would exceed {MAX_FILE_BYTES} bytes")
            state[rel] = updated
        elif op.kind == "delete":
            if current() is None:
                raise CodeEditError(f"DELETE {rel}: the file does not exist")
            state[rel] = None
        else:  # pragma: no cover - parser only produces the three kinds
            raise CodeEditError(f"unknown operation {op.kind!r}")
    return state


def _read_original(repo: Path, paths: list[str]) -> dict[str, bytes | None]:
    original: dict[str, bytes | None] = {}
    for rel in paths:
        target = repo / rel
        original[rel] = target.read_bytes() if target.is_file() else None
    return original


def _write_changes(repo: Path, changes: dict[str, str | None]) -> None:
    for rel, content in changes.items():
        target = repo / rel
        if content is None:
            if target.is_file():
                target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def restore(repo_dir: str | os.PathLike[str], original: dict[str, bytes | None]) -> None:
    """Put every touched path back exactly as it was (removing files the edit created)."""

    repo = Path(repo_dir)
    for rel, content in original.items():
        target = repo / rel
        if content is None:
            if target.is_file():
                target.unlink()
            parent = target.parent
            while parent != repo and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def _git(repo: Path, *args: str) -> str:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    # Git 2.5x starts a detached `gc --auto` after a commit, which keeps writing inside .git
    # while the platform may be copying or removing that project. These repositories are small
    # and the platform owns their lifecycle, so never let git maintain them in the background.
    env["GIT_CONFIG_COUNT"] = "2"
    env["GIT_CONFIG_KEY_0"] = "gc.auto"
    env["GIT_CONFIG_VALUE_0"] = "0"
    env["GIT_CONFIG_KEY_1"] = "maintenance.auto"
    env["GIT_CONFIG_VALUE_1"] = "false"
    env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = _AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = _AUTHOR_EMAIL
    process = subprocess.run(["git", *args], cwd=str(repo), env=env, capture_output=True, text=True, check=False)
    if process.returncode != 0:
        raise CodeEditError(f"git {args[0]} failed: {process.stderr.strip()[:200]}")
    return process.stdout.strip()


def commit_paths(repo_dir: str | os.PathLike[str], paths: list[str], message: str) -> str:
    """Stage exactly ``paths`` (additions, changes and deletions) and commit. Returns the new HEAD."""

    repo = Path(repo_dir)
    _git(repo, "add", "-A", "--", *paths)
    staged = _git(repo, "diff", "--cached", "--name-only")
    if not staged:
        return _git(repo, "rev-parse", "HEAD")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


# --- verification ----------------------------------------------------------------------------------


Runner = Callable[..., subprocess.CompletedProcess]


def _owning_app(rel: str, apps: list[dict]) -> dict | None:
    best = None
    for app in apps:
        prefix = str(app.get("path", "")).strip("/")
        if prefix and (rel == prefix or rel.startswith(prefix + "/")):
            if best is None or len(prefix) > len(str(best.get("path", ""))):
                best = app
    return best


def _tsc_binary(repo: Path, app_dir: Path) -> Path | None:
    for base in (app_dir, repo):
        candidate = base / "node_modules" / ".bin" / "tsc"
        if candidate.exists():
            return candidate
    return None


def structure_errors(rel: str, content: str) -> list[str]:
    """Top-level duplicates that no valid module has: a repeated import line, a second default export,
    or a name declared twice. They are what a whole file pasted into a REPLACE produces (R-525)."""

    errors: list[str] = []
    imports: set[str] = set()
    names: set[str] = set()
    defaults = 0
    for number, line in enumerate(content.splitlines(), start=1):
        if not line or line[0].isspace():
            continue  # only column-0 (top-level) statements
        stripped = line.strip()
        if stripped.startswith("import ") and " from " in stripped:
            key = " ".join(stripped.rstrip(";").split())
            if key in imports:
                errors.append(f"{rel}:{number}: `{key[:80]}` is imported twice (was a whole file pasted into a REPLACE?)")
            imports.add(key)
        if stripped.startswith("export default"):
            defaults += 1
            if defaults == 2:
                errors.append(f"{rel}:{number}: the file has more than one default export (was a whole file pasted into a REPLACE?)")
        match = _TOP_LEVEL_DECL.match(stripped)
        if match:
            name = match.group(1)
            if name in names:
                errors.append(f"{rel}:{number}: `{name}` is declared twice at the top level")
            names.add(name)
    return errors


def verify_changes(
    repo_dir: str | os.PathLike[str],
    manifest: dict | None,
    changes: dict[str, str | None],
    *,
    runner: Runner = subprocess.run,
) -> Verification:
    """Check what the edit touched with the tools that exist. Never claims an unchecked file passed."""

    repo = Path(repo_dir)
    result = Verification()
    apps = list((manifest or {}).get("apps") or [])
    touched_apps: dict[str, dict] = {}
    for rel, content in changes.items():
        if content is None:
            app = _owning_app(rel, apps)
            if app is not None:
                touched_apps[app["id"]] = app
            continue
        suffix = PurePosixPath(rel).suffix.lower()
        if rel == "omnistack.json":
            from ..localrun.multiapp import ProjectManifestError, load_project_manifest

            try:
                load_project_manifest(repo)
                result.checked.append(rel)
            except ProjectManifestError as error:
                result.errors.append(f"omnistack.json: {error}")
            continue
        if suffix == ".json":
            try:
                json.loads(content)
                result.checked.append(rel)
            except json.JSONDecodeError as error:
                result.errors.append(f"{rel}: invalid JSON ({error})")
        if suffix in _SOURCE_SUFFIXES:
            result.errors.extend(structure_errors(rel, content))
        app = _owning_app(rel, apps)
        if app is not None:
            touched_apps[app["id"]] = app
            # UI apps run under a base path in the preview and wherever they are hosted.
            if app.get("kind") in _UI_KINDS and suffix in _UI_SOURCE_SUFFIXES:
                for number, line in enumerate(content.splitlines(), start=1):
                    if _RAW_ROOT_ANCHOR.search(line):
                        result.errors.append(
                            f"{rel}:{number}: internal link uses <a href=\"/...\">, which ignores the app's base "
                            "path; use Link from next/link (or a relative href)"
                        )

    node = shutil.which("node")
    for app in touched_apps.values():
        app_dir = repo / str(app["path"])
        tsc = _tsc_binary(repo, app_dir) if (app_dir / "tsconfig.json").is_file() else None
        if tsc is not None:
            proc = runner(
                [str(tsc), "--noEmit", "-p", str(app_dir)],
                cwd=str(app_dir), capture_output=True, text=True, timeout=240, check=False,
            )
            if proc.returncode == 0:
                result.checked.append(f"{app['id']} (tsc)")
            else:
                lines = [line for line in (proc.stdout + proc.stderr).splitlines() if "error" in line.lower()]
                result.errors.extend(f"{app['id']}: {line.strip()}" for line in lines[:MAX_ERROR_LINES] or ["tsc failed"])
            continue
        js_files = [
            rel for rel, content in changes.items()
            if content is not None
            and _owning_app(rel, apps) is app
            and PurePosixPath(rel).suffix.lower() in (".js", ".mjs", ".cjs")
        ]
        if js_files and node:
            for rel in js_files:
                proc = runner([node, "--check", str(repo / rel)], capture_output=True, text=True, timeout=60, check=False)
                if proc.returncode == 0:
                    result.checked.append(rel)
                else:
                    detail = (proc.stderr or proc.stdout).strip().splitlines()
                    result.errors.append(f"{rel}: {' '.join(detail[-3:])[:300]}")
        others = [
            rel for rel, content in changes.items()
            if content is not None and _owning_app(rel, apps) is app and rel not in js_files
            and PurePosixPath(rel).suffix.lower() not in (".json",)
        ]
        if others:
            reason = "install dependencies (run the preview) to type-check" if (app_dir / "tsconfig.json").is_file() else "no checker for this file type"
            result.skipped.extend(f"{rel} ({reason})" for rel in others)
    return result


# --- prompts -------------------------------------------------------------------------------------

_SELECT_SYSTEM = (
    "You are a senior engineer about to change an existing multi-app project (one repository with "
    "web, admin, mobile PWA and API apps). Decide which EXISTING files you must read to make the "
    "requested change: the files you will modify plus closely related ones (the page, its layout, the "
    "API route it calls, the latest migration, seed files, navigation). New files do not need to be "
    "listed. Reply with ONLY a JSON object: {\"plan\": \"3-6 short steps\", \"files\": [\"path\", ...]} "
    f"with at most {MAX_SELECTED_FILES} paths copied exactly from the index."
)

_EDIT_SYSTEM = """You change an existing multi-app project by editing its files. Reply ONLY in this format:

@@@ SUMMARY
One to three sentences for the project owner describing what changed.
@@@ WRITE path/to/file
(the complete file content: use for NEW files, or to fully rewrite a small file you were shown in full)
@@@ REPLACE path/to/file
@@@ FIND
(text copied EXACTLY from the current file, a few lines, occurring exactly once)
@@@ WITH
(the new text)
@@@ DELETE path/to/file
@@@ END

Rules:
- Prefer REPLACE for changes to existing files; use several REPLACE blocks for several spots.
  WITH replaces only the FIND text. Never paste a whole file into WITH: to rewrite a file, use WRITE.
- Internal links in web/admin/PWA apps use Link from next/link, never <a href="/...">.
- Paths are relative to the repository root. Never touch node_modules, lockfiles or real .env files.
- Web, admin and PWA apps are Next.js App Router apps served under a base path: use next/link and
  relative links, never hard-code /preview/... URLs. Browser code calls the API at
  process.env.NEXT_PUBLIC_API_URL; server components call process.env.API_URL.
- The API app reads PORT and DATABASE_URL and must keep GET /health answering 200.
- Database changes: add a NEW migration file in the API app's migrations/ folder with the next number
  (never edit an existing migration), and update seed/ files so demo data stays valid.
- When asked to remove a feature, remove it completely: its pages, links, API routes and UI.
- Keep the project's existing style, naming and components. Do not add npm dependencies unless the
  change is impossible without them (then add them to that app's package.json).
- Finish with @@@ END. Keep the change focused so the reply is not cut off."""


def _msg(role: ChatRole, text: str) -> Message:
    """Messages must be non-empty with no surrounding whitespace (a gateway contract)."""

    return Message(role, text.strip() or "(empty)")


def _index_text(index: list[tuple[str, int]]) -> str:
    return "\n".join(f"{path} ({size} bytes)" for path, size in index)


def _files_text(repo: Path, paths: list[str]) -> tuple[str, frozenset[str]]:
    parts: list[str] = []
    truncated: set[str] = set()
    total = 0
    for rel in paths:
        target = repo / rel
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        shown = text
        if len(text) > MAX_FILE_CHARS_SHOWN or total + len(text) > MAX_TOTAL_CHARS_SHOWN:
            room = max(0, min(MAX_FILE_CHARS_SHOWN, MAX_TOTAL_CHARS_SHOWN - total))
            if room < 2_000:
                parts.append(f"=== FILE {rel} (not shown: context budget used up) ===")
                truncated.add(rel)
                continue
            shown = text[:room]
            truncated.add(rel)
        total += len(shown)
        note = " (TRUNCATED: only the beginning is shown; use REPLACE)" if rel in truncated else ""
        parts.append(f"=== FILE {rel} ({text.count(chr(10)) + 1} lines){note} ===\n{shown}\n=== END FILE ===")
    return "\n\n".join(parts), frozenset(truncated)


# Words that say nothing about which file to open.
_STOPWORDS = frozenset(
    "a an and are add adds added also app apps as at be but by can change changes changed create "
    "do does for from get give has have how in into is it its make makes making new not of on only "
    "or page pages please remove removes removed screen set should show shows so that the their "
    "then there this to toggle update updates use used user users want when where which with "
    "without work works".split()
)


#: R-550: a request that is really about branding. Every one of these is now answered by editing
#: brand.json, which the apps derive from, rather than by hunting through stylesheets.
_BRANDING_WORDS = {
    "brand", "branding", "colour", "color", "colours", "colors", "theme", "palette",
    "logo", "icon", "icons", "splash", "font", "fonts", "typeface", "typography",
    "rename", "renamed", "rebrand", "appearance", "corners", "rounded", "radius",
    "red", "green", "blue", "purple", "orange", "yellow", "teal", "pink", "black", "white",
}


def published_identity_violation(repo_dir: str | os.PathLike[str], changes: dict) -> str | None:
    """The one edit that must be refused rather than repaired (R-550).

    Apple ties the bundle identifier to the App Store Connect record, and Google Play uses it as
    the listing's primary key and never lets anyone reuse one. Changing it after publication does
    not update the app — it makes a different one, with no reviews, no ratings and no update path
    for anyone who already installed the original. That is not a mistake a repair round should get
    to fix; it is a change that should not happen.

    Everything else about a published app — icon, colours, font, display name — is legal, and is
    deliberately not blocked here.
    """
    content = changes.get("brand.json")
    if content is None:  # untouched, or deleted (which the path rules already reject)
        return None
    previous_path = Path(repo_dir) / "brand.json"
    if not previous_path.is_file():
        return None
    try:
        previous = json.loads(previous_path.read_text(encoding="utf-8")).get("identity") or {}
        proposed = json.loads(content).get("identity") or {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None  # malformed JSON is the verifier's business, not this guard's

    published_as = previous.get("publishedBundleId")
    if not previous.get("published") or not published_as:
        return None
    if proposed.get("bundleId") == published_as:
        return None
    return (
        f"this app was published as {published_as}, and a store bundle identifier cannot be "
        f"changed afterwards — Apple ties it to the App Store Connect record and Google Play "
        f"never lets one be reused, so building under {proposed.get('bundleId')!r} would create a "
        f"separate app with no reviews, no ratings and no update path for your existing users. "
        f"Its icon, colours, font and display name can all still be changed; only the identifier "
        f"cannot."
    )


def pick_files_by_name(prompt: str, index_paths: list[str], limit: int = MAX_SELECTED_FILES) -> list[str]:
    """Rank real repository paths against the words in the request.

    A small local model often answers the selection step with paths that do not exist, which used
    to leave the edit step with no file contents at all — so it invented both paths and text, and
    every edit was rejected. This deterministic fallback keeps the editor looking at real code
    (R-530).
    """

    words = {w for w in re.split(r"[^a-z0-9]+", prompt.lower()) if len(w) > 2 and w not in _STOPWORDS}
    if not words:
        return []
    # R-550: "make it green" names no file, and ranking by word overlap would never find the one
    # place a colour is now defined. Branding lives in brand.json; say so rather than hoping.
    ranked: list[str] = []
    if words & _BRANDING_WORDS and "brand.json" in index_paths:
        ranked.append("brand.json")
    scored: list[tuple[int, int, str]] = []
    for path in index_paths:
        lowered = path.lower()
        segments = re.split(r"[^a-z0-9]+", lowered)
        score = 0
        for word in words:
            if word in segments:
                score += 3                      # a path segment is exactly the word
            elif word in lowered:
                score += 1                      # the word appears somewhere in the path
            if word.rstrip("s") != word and word.rstrip("s") in segments:
                score += 2                      # "rides" matching a "ride" segment
        if score:
            scored.append((-score, len(path), path))
    scored.sort()
    ranked += [path for _, _, path in scored if path not in ranked]
    return ranked[:limit]


def _extract_json(text: str) -> dict:
    stripped = (text or "").strip()
    first, last = stripped.find("{"), stripped.rfind("}")
    if first == -1 or last < first:
        raise CodeEditError("the file selection was not a JSON object")
    try:
        data = json.loads(stripped[first : last + 1])
    except json.JSONDecodeError as error:
        raise CodeEditError(f"the file selection was not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise CodeEditError("the file selection was not a JSON object")
    return data


# --- the agent -----------------------------------------------------------------------------------


async def run_code_edit(
    repo_dir: str | os.PathLike[str],
    prompt: str,
    provider: ModelProvider,
    *,
    model_id: str | None = None,
    max_output_tokens: int = 8_192,
    timeout_seconds: float = 300.0,
    context_text: str = "",
    verifier: Callable[..., Verification] = verify_changes,
) -> dict:
    """Plan, edit, verify (one repair round) and commit a change. Raises CodeEditError on failure,
    leaving every file exactly as it was."""

    repo = Path(repo_dir)
    if not (repo / ".git").exists():
        raise CodeEditError("the project has no git history")
    manifest_path = repo / "omnistack.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
    manifest_text = manifest_path.read_text(encoding="utf-8") if manifest_path.is_file() else "(none)"
    index = project_file_index(repo)
    index_paths = {path for path, _ in index}

    ref = provider.model_ref() if hasattr(provider, "model_ref") else None
    target = ModelRef(
        getattr(provider, "provider_id", None) or (ref.provider_id if ref else "provider"),
        model_id or (ref.model_id if ref else "model"),
    )

    async def ask(messages: list[Message]) -> str:
        request = GenerateRequest(
            request_id=f"{_REQUEST_PREFIX}-{uuid.uuid4().hex[:12]}",
            model=target,
            messages=tuple(messages),
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
        )
        return (await provider.generate(request)).text

    context_block = f"\n\nProject knowledge and skills:\n{context_text}" if context_text.strip() else ""

    # 1. select files
    plan = ""
    files: list[str] = []
    try:
        selection = _extract_json(await ask([
            _msg(ChatRole.SYSTEM, _SELECT_SYSTEM),
            _msg(ChatRole.USER, f"Request: {prompt}{context_block}\n\nomnistack.json:\n{manifest_text}\n\nFile index:\n{_index_text(index)}"),
        ]))
        plan = str(selection.get("plan", "")).strip()[:2_000]
        wanted = [p for p in selection.get("files", []) if isinstance(p, str)]
        cleaned = [p.strip()[2:] if p.strip().startswith("./") else p.strip() for p in wanted]
        files = [p for p in dict.fromkeys(cleaned) if p in index_paths][:MAX_SELECTED_FILES]
    except CodeEditError:
        files = []  # the fallback below keeps the edit grounded in real files
    if not files:
        files = pick_files_by_name(prompt, index_paths)

    # 2. edit (one retry when the reply is rejected)
    files_text, truncated = _files_text(repo, files)
    messages = [
        _msg(ChatRole.SYSTEM, _EDIT_SYSTEM),
        Message(
            ChatRole.USER,
            f"Request: {prompt}{context_block}\n\nYour plan:\n{plan or '(none)'}\n\nomnistack.json:\n{manifest_text}\n\n"
            f"All files (paths only):\n{chr(10).join(sorted(index_paths))}\n\nFiles you asked to read:\n{files_text or '(none)'}",
        ),
    ]
    reply, changes = await _edit_round(ask, messages, repo, truncated)

    original = _read_original(repo, list(changes))
    _write_changes(repo, changes)
    repaired = False
    try:
        verification = verifier(repo, manifest, changes)
        if verification.errors:
            # 3. one repair round against the files as they are now
            current_text, current_truncated = _files_text(repo, [p for p, c in changes.items() if c is not None])
            messages += [
                _msg(ChatRole.ASSISTANT, reply[:20_000]),
                Message(
                    ChatRole.USER,
                    "Your change was applied, but these checks failed:\n"
                    + "\n".join(verification.errors[:MAX_ERROR_LINES])
                    + f"\n\nCurrent versions of the files you changed:\n{current_text}\n\n"
                    "Reply in the same format with edits that fix these errors, relative to the CURRENT files.",
                ),
            ]
            _, fix = await _edit_round(ask, messages, repo, current_truncated)
            for rel in fix:
                if rel not in original:
                    original.update(_read_original(repo, [rel]))
            _write_changes(repo, fix)
            changes = {**changes, **fix}
            repaired = True
            verification = verifier(repo, manifest, changes)
            if verification.errors:
                raise CodeEditError(
                    "the change did not pass its checks, so nothing was saved: " + "; ".join(verification.errors[:5])
                )
        # R-550: the one edit that is refused rather than repaired. Checked inside the try, so the
        # handler below restores every file — outside it, a violation would raise with the change
        # still written to disk, which is the opposite of what "nothing was saved" promises.
        violation = published_identity_violation(repo, changes)
        if violation is not None:
            raise CodeEditError(f"nothing was saved: {violation}")
    except BaseException:
        restore(repo, original)
        raise

    added = sorted(p for p, c in changes.items() if c is not None and original.get(p) is None)
    deleted = sorted(p for p, c in changes.items() if c is None and original.get(p) is not None)
    modified = sorted(
        p for p, c in changes.items()
        if c is not None and original.get(p) is not None and original[p] != c.encode("utf-8")
    )
    summary = parse_edit_reply(reply).summary
    commit_sha = commit_paths(repo, sorted(changes), f"edit: {prompt.strip()[:72]}")
    return {
        "summary": summary,
        "plan": plan,
        "added": added,
        "modified": modified,
        "deleted": deleted,
        "commit_sha": commit_sha,
        "repaired": repaired,
        "verification": verification.to_dict(),
    }


async def _edit_round(
    ask: Callable[[list[Message]], Any],
    messages: list[Message],
    repo: Path,
    truncated: frozenset[str],
) -> tuple[str, dict[str, str | None]]:
    last_error = ""
    for attempt in (1, 2):
        reply = await ask(messages)
        try:
            parsed = parse_edit_reply(reply)
            return reply, compute_changes(repo, parsed.ops, truncated=truncated)
        except CodeEditError as error:
            last_error = str(error)
            if attempt == 2:
                break
            messages.append(_msg(ChatRole.ASSISTANT, reply[:20_000]))
            messages.append(Message(
                ChatRole.USER,
                f"That reply was rejected: {last_error}\n"
                "Reply again with nothing but the format below, ending with @@@ END. Use real file "
                "paths from the files shown above, never the placeholders:\n"
                "@@@ SUMMARY\n<what you changed, in one line>\n"
                "@@@ REPLACE <a path shown above>\n@@@ FIND\n<exact text copied from that file>\n"
                "@@@ WITH\n<the replacement text>\n"
                "@@@ END\n"
                "Prefer REPLACE over WRITE: WRITE needs the complete file and may not fit.",
            ))
    raise CodeEditError(f"the model's edit could not be applied: {last_error}")
