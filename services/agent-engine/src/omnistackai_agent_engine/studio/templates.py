"""Template catalogue for the OmniStackAI Studio (Phase T, T-1 / R-519).

A template is a hand-built, complete source repository plus a manifest:

    templates/catalog/<slug>/
      template.json   manifest (schema_version 1, see templates/catalog/README.md)
      repo/           the golden repository that "use template" copies
      media/          optional cover and screenshots referenced by the manifest

The original is read-only and identical for every user. ``instantiate_template`` copies it into
the user's own project workspace with a fresh git history and marks the workspace
``kind: "template"``, so later edits change only that user's copy. A template that fails
validation is never listed or instantiated.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from .workspace import StudioWorkspaceStore

SCHEMA_VERSION = 1
CATEGORIES = (
    "mobility",
    "commerce",
    "healthcare",
    "education",
    "real-estate",
    "services",
    "fintech",
    "content",
)
APP_KINDS = ("web", "admin", "pwa", "api")

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FORBIDDEN_DIRS = frozenset({".git", "node_modules", ".next", ".turbo", "__pycache__"})
_ALLOWED_ENV_FILES = frozenset({".env.example"})
# Desktop junk: never copied into a user's project and never part of the digest (R-530).
_JUNK_FILES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
_MAX_FILES = 5_000
_MAX_BYTES = 50 * 1024 * 1024
_MAX_TAGLINE = 140

PROJECT_MANIFEST = "omnistack.json"

_AUTHOR_NAME = "OmniStackAI"
_AUTHOR_EMAIL = "agent@omnistackai.internal"


class TemplateNotFoundError(Exception):
    """No valid template with that slug exists in the catalogue."""


class TemplateTargetNotEmptyError(Exception):
    """The workspace already has code; a template is only ever copied into a new project."""


class TemplateInstantiationError(Exception):
    """Copying or committing the template failed; the half-made workspace was removed."""


def default_catalog_root() -> Path:
    """``OMNISTACKAI_TEMPLATE_CATALOG`` if set, else the repository's ``templates/catalog``."""

    override = os.environ.get("OMNISTACKAI_TEMPLATE_CATALOG", "").strip()
    if override:
        return Path(os.path.expanduser(override)).resolve()
    # studio/ -> omnistackai_agent_engine/ -> src/ -> agent-engine/ -> services/ -> repo root
    return Path(__file__).resolve().parents[5] / "templates" / "catalog"


# --- repository walking and digest -------------------------------------------------------------


def _repo_files(repo_dir: Path) -> tuple[list[str], list[str]]:
    """Return (sorted posix paths of every file, problems found) for a template repo."""

    files: list[str] = []
    problems: list[str] = []
    total_bytes = 0
    for dirpath, dirnames, filenames in os.walk(repo_dir, followlinks=False):
        current = Path(dirpath)
        for name in sorted(dirnames):
            rel = (current / name).relative_to(repo_dir).as_posix()
            if (current / name).is_symlink():
                problems.append(f"repo/{rel}: symlinks are not allowed")
            elif name in _FORBIDDEN_DIRS:
                problems.append(f"repo/{rel}: {name} must not be shipped in a template")
        dirnames[:] = [
            d for d in dirnames if d not in _FORBIDDEN_DIRS and not (current / d).is_symlink()
        ]
        for name in filenames:
            path = current / name
            rel = path.relative_to(repo_dir).as_posix()
            if path.is_symlink():
                problems.append(f"repo/{rel}: symlinks are not allowed")
                continue
            if name in _JUNK_FILES:
                continue
            if (name == ".env" or name.startswith(".env.")) and name not in _ALLOWED_ENV_FILES:
                problems.append(f"repo/{rel}: real .env files are not allowed (ship .env.example)")
                continue
            total_bytes += path.stat().st_size
            files.append(rel)
    if len(files) > _MAX_FILES:
        problems.append(f"repo has {len(files)} files (limit {_MAX_FILES})")
    if total_bytes > _MAX_BYTES:
        problems.append(f"repo is {total_bytes} bytes (limit {_MAX_BYTES})")
    return sorted(files), problems


def template_digest(repo_dir: str | os.PathLike[str]) -> str:
    """A stable ``sha256:`` digest of a repo's file paths and contents (``.git`` etc. excluded)."""

    root = Path(repo_dir)
    files, _ = _repo_files(root)
    outer = hashlib.sha256()
    for rel in files:
        inner = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        outer.update(f"{rel}\0{inner}\n".encode("utf-8"))
    return f"sha256:{outer.hexdigest()}"


# --- manifest validation -----------------------------------------------------------------------


def _safe_relative(value: object) -> PurePosixPath | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = PurePosixPath(value.strip())
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        return None
    return path


def _text(manifest: dict, key: str, errors: list[str], *, limit: int | None = None) -> None:
    value = manifest.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key} is required and must be a non-empty string")
    elif limit is not None and len(value) > limit:
        errors.append(f"{key} must be at most {limit} characters")


def _string_list(manifest: dict, key: str, errors: list[str], *, required: bool = True) -> None:
    value = manifest.get(key, [] if not required else None)
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        errors.append(f"{key} must be a list of non-empty strings")
    elif required and not value:
        errors.append(f"{key} must not be empty")


def _objects(manifest: dict, key: str, errors: list[str], *, required: bool = True) -> list[dict]:
    value = manifest.get(key, [] if not required else None)
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        errors.append(f"{key} must be a list of objects")
        return []
    if required and not value:
        errors.append(f"{key} must not be empty")
    return value


def _validate_apps(apps: list[dict], repo_dir: Path, errors: list[str]) -> None:
    seen: set[str] = set()
    if sum(1 for app in apps if app.get("kind") == "api") > 1:
        errors.append("a template can have at most one api app (every app shares it)")
    for index, app in enumerate(apps):
        label = f"apps[{index}]"
        app_id = app.get("id")
        if not isinstance(app_id, str) or not _ID_RE.match(app_id):
            errors.append(f"{label}.id must be a short lowercase identifier")
        elif app_id in seen:
            errors.append(f"{label}.id {app_id!r} is a duplicate")
        else:
            seen.add(app_id)
        if not isinstance(app.get("name"), str) or not app["name"].strip():
            errors.append(f"{label}.name is required")
        kind = app.get("kind")
        if kind not in APP_KINDS:
            errors.append(f"{label}.kind must be one of {', '.join(APP_KINDS)}")
        rel = _safe_relative(app.get("path"))
        if rel is None:
            errors.append(f"{label}.path {app.get('path')!r} must be a relative path inside repo/")
            continue
        app_dir = repo_dir / rel
        if not app_dir.is_dir():
            errors.append(f"{label}.path {rel.as_posix()} does not exist in repo/")
            continue
        if not (app_dir / "package.json").is_file():
            errors.append(f"{label} needs {rel.as_posix()}/package.json with a dev script")
        if kind == "api":
            migrations = app_dir / "migrations"
            if not migrations.is_dir() or not any(migrations.glob("*.sql")):
                errors.append(f"{label} is an api app and needs {rel.as_posix()}/migrations/*.sql")


def validate_template(template_dir: str | os.PathLike[str]) -> list[str]:
    """Every problem with a template directory; an empty list means it is valid."""

    root = Path(template_dir)
    manifest_path = root / "template.json"
    if not manifest_path.is_file():
        return ["template.json is missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return [f"template.json is not valid JSON: {error}"]
    if not isinstance(manifest, dict):
        return ["template.json must be a JSON object"]

    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    slug = manifest.get("slug")
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        errors.append("slug must be lowercase letters, digits and dashes")
    elif slug != root.name:
        errors.append(f"slug {slug!r} must match the directory name {root.name!r}")
    if not isinstance(manifest.get("version"), str) or not _SEMVER_RE.match(manifest["version"]):
        errors.append("version must be semantic (for example 1.0.0)")
    if manifest.get("category") not in CATEGORIES:
        errors.append(f"category must be one of {', '.join(CATEGORIES)}")
    _text(manifest, "name", errors, limit=60)
    _text(manifest, "tagline", errors, limit=_MAX_TAGLINE)
    _text(manifest, "description", errors)
    _string_list(manifest, "entities", errors)
    _string_list(manifest, "features", errors)
    _string_list(manifest, "stack", errors)
    _string_list(manifest, "screenshots", errors, required=False)

    repo_dir = root / "repo"
    if not repo_dir.is_dir():
        errors.append("repo/ is missing")
    else:
        files, problems = _repo_files(repo_dir)
        errors.extend(problems)
        if not files:
            errors.append("repo/ is empty")
        if PROJECT_MANIFEST in files:
            errors.append(f"repo/{PROJECT_MANIFEST} is reserved: the platform writes it into each project")
        _validate_apps(_objects(manifest, "apps", errors), repo_dir, errors)

    role_ids: set[str] = set()
    for index, role in enumerate(_objects(manifest, "roles", errors)):
        role_id = role.get("id")
        if not isinstance(role_id, str) or not _ID_RE.match(role_id):
            errors.append(f"roles[{index}].id must be a short lowercase identifier")
            continue
        if role_id in role_ids:
            errors.append(f"roles[{index}].id {role_id!r} is a duplicate")
        role_ids.add(role_id)
        for key in ("name", "description"):
            if not isinstance(role.get(key), str) or not role[key].strip():
                errors.append(f"roles[{index}].{key} is required")

    for index, user in enumerate(_objects(manifest, "demo_users", errors)):
        if user.get("role") not in role_ids:
            errors.append(f"demo_users[{index}].role {user.get('role')!r} is not a declared role")
        if not isinstance(user.get("email"), str) or not _EMAIL_RE.match(user["email"]):
            errors.append(f"demo_users[{index}].email must be an email address")
        for key in ("name", "password"):
            if not isinstance(user.get(key), str) or not user[key].strip():
                errors.append(f"demo_users[{index}].{key} is required")

    for index, integration in enumerate(_objects(manifest, "integrations", errors, required=False)):
        for key in ("id", "kind", "provider"):
            if not isinstance(integration.get(key), str) or not integration[key].strip():
                errors.append(f"integrations[{index}].{key} is required")
        if not isinstance(integration.get("mock"), bool):
            errors.append(f"integrations[{index}].mock must be true or false")

    media = [manifest.get("cover")] if manifest.get("cover") is not None else []
    media += [s for s in manifest.get("screenshots", []) if isinstance(s, str)]
    for value in media:
        rel = _safe_relative(value)
        if rel is None or not (root / rel).is_file():
            errors.append(f"media file {value!r} does not exist in the template directory")
    return errors


# --- catalogue ---------------------------------------------------------------------------------


_ASSET_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".avif": "image/avif",
}

_SUMMARY_KEYS = (
    "slug",
    "name",
    "version",
    "category",
    "tagline",
    "apps",
    "entities",
    "features",
    "integrations",
    "stack",
    "cover",
    "screenshots",
    "screens",
)


class TemplateCatalog:
    """The valid templates under one catalogue directory, loaded once and cached.

    Templates ship with a platform release, so the catalogue is read on first use; call
    ``reload()`` after changing templates on disk.
    """

    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        self._root = Path(root) if root is not None else default_catalog_root()
        self._templates: dict[str, dict] | None = None
        self._errors: dict[str, list[str]] = {}

    @property
    def root(self) -> Path:
        return self._root

    def reload(self) -> None:
        templates: dict[str, dict] = {}
        errors: dict[str, list[str]] = {}
        if self._root.is_dir():
            for entry in sorted(self._root.iterdir()):
                if not entry.is_dir() or entry.name.startswith((".", "_")):
                    continue
                problems = validate_template(entry)
                if problems:
                    errors[entry.name] = problems
                    continue
                manifest = json.loads((entry / "template.json").read_text(encoding="utf-8"))
                files, _ = _repo_files(entry / "repo")
                manifest["digest"] = template_digest(entry / "repo")
                manifest["file_count"] = len(files)
                templates[entry.name] = manifest
        self._templates = templates
        self._errors = errors

    def _loaded(self) -> dict[str, dict]:
        if self._templates is None:
            self.reload()
        assert self._templates is not None
        return self._templates

    def errors(self) -> dict[str, list[str]]:
        """Templates that exist on disk but failed validation, with their problems."""

        self._loaded()
        return dict(self._errors)

    def list(self) -> list[dict]:
        """Catalogue cards, sorted by slug. Demo credentials are only in ``get``."""

        cards = []
        for manifest in self._loaded().values():
            card = {key: manifest.get(key) for key in _SUMMARY_KEYS if key in manifest}
            kinds: list[str] = []
            for app in manifest["apps"]:
                if app["kind"] not in kinds:
                    kinds.append(app["kind"])
            card["app_kinds"] = kinds
            card["roles"] = [{"id": r["id"], "name": r["name"]} for r in manifest["roles"]]
            card["digest"] = manifest["digest"]
            card["file_count"] = manifest["file_count"]
            cards.append(card)
        return cards

    def get(self, slug: str) -> dict:
        template = self._loaded().get(slug) if isinstance(slug, str) else None
        if template is None:
            raise TemplateNotFoundError(f"template {slug!r} not found")
        return json.loads(json.dumps(template))

    def asset(self, slug: str, rel_path: str) -> tuple[Path, str]:
        """A cover or screenshot of a template: (file, content type). Only the files the manifest
        declares can be served, so nothing else in the template directory is reachable (R-523)."""

        template = self.get(slug)
        declared = {template.get("cover")} | set(template.get("screenshots") or [])
        declared.discard(None)
        rel = _safe_relative(rel_path)
        if rel is None or rel.as_posix() not in declared:
            raise TemplateNotFoundError(f"template {slug!r} has no asset {rel_path!r}")
        path = (self._root / slug / rel).resolve()
        if not path.is_file() or (self._root / slug).resolve() not in path.parents:
            raise TemplateNotFoundError(f"template {slug!r} has no asset {rel_path!r}")
        return path, _ASSET_TYPES.get(path.suffix.lower(), "application/octet-stream")

    def repo_dir(self, slug: str) -> Path:
        self.get(slug)
        return self._root / slug / "repo"


# --- instantiation -----------------------------------------------------------------------------


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
    process = subprocess.run(
        ["git", *args], cwd=str(repo), env=env, capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        raise TemplateInstantiationError(f"git {args[0]} failed: {process.stderr.strip()[:200]}")
    return process.stdout.strip()


def instantiate_template(
    catalog: TemplateCatalog,
    workspace_store: StudioWorkspaceStore,
    workspace_id: str,
    slug: str,
) -> dict:
    """Copy a template into a new project workspace as that user's own git repository."""

    template = catalog.get(slug)  # TemplateNotFoundError before anything is created
    source = catalog.repo_dir(slug)
    created = not workspace_store.exists(workspace_id)
    with workspace_store.lock(workspace_id):
        target = workspace_store.repo_path(workspace_id)
        if target.is_dir() and any(target.iterdir()):
            raise TemplateTargetNotEmptyError(
                f"workspace {workspace_id} already has code; a template starts a new project"
            )
        try:
            files, _ = _repo_files(source)
            for rel in files:
                destination = target / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / rel, destination)
            if template_digest(target) != template["digest"]:
                raise TemplateInstantiationError("the copied files do not match the template digest")
            # The project describes itself: which apps it has and how to log in to them (R-520).
            # It is part of the user's copy, so later edits can add or change apps.
            (target / PROJECT_MANIFEST).write_text(
                json.dumps(project_manifest(template), indent=2) + "\n", encoding="utf-8"
            )

            _git(target, "init", "-q")
            _git(target, "add", "-A")
            _git(target, "commit", "-q", "-m", f"Template: {template['name']} v{template['version']}")
            commit_sha = _git(target, "rev-parse", "HEAD")
        except Exception as error:
            if created:
                shutil.rmtree(workspace_store.workspace_path(workspace_id), ignore_errors=True)
            else:
                shutil.rmtree(target, ignore_errors=True)
            if isinstance(error, TemplateInstantiationError):
                raise
            raise TemplateInstantiationError(f"could not copy template {slug!r}: {error}") from error

        provenance = {
            "slug": template["slug"],
            "version": template["version"],
            "digest": template["digest"],
        }
        workspace_store.save_state(
            workspace_id,
            {
                "kind": "template",
                "project_id": workspace_id,
                "name": template["name"],
                "description": template["tagline"],
                "template": provenance,
                "entities": list(template["entities"]),
                "file_count": len(files) + 1,
                "commit_sha": commit_sha,
            },
        )
        app_names = ", ".join(app["name"] for app in template["apps"])
        workspace_store.append_turn(
            workspace_id,
            "assistant",
            f"Started from the {template['name']} template (v{template['version']}) with "
            f"{len(template['apps'])} apps: {app_names}. This project is your own copy; the "
            "original template stays unchanged.",
        )

    return {
        "id": workspace_id,
        "name": template["name"],
        "description": template["tagline"],
        "commit_sha": commit_sha,
        "file_count": len(files) + 1,
        "entities": list(template["entities"]),
        "template": provenance,
    }


def project_manifest(template: dict) -> dict:
    """The ``omnistack.json`` written into a project copied from ``template``."""

    return {
        "schema_version": 1,
        "name": template["name"],
        "template": {"slug": template["slug"], "version": template["version"]},
        "apps": [
            {"id": a["id"], "name": a["name"], "kind": a["kind"], "path": a["path"]}
            for a in template["apps"]
        ],
        "roles": [{"id": r["id"], "name": r["name"]} for r in template["roles"]],
        "demo_users": [
            {"role": u["role"], "name": u["name"], "email": u["email"], "password": u["password"]}
            for u in template["demo_users"]
        ],
    }


def is_template_workspace(workspace_store: StudioWorkspaceStore, workspace_id: str) -> dict | None:
    """The workspace's template provenance if it was started from a template, else None."""

    state = workspace_store.get_state(workspace_id) or {}
    if state.get("kind") != "template":
        return None
    return state.get("template") or {}
