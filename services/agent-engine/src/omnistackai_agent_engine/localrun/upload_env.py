"""PC-102: which storage and file sources a generated app gets, from the platform's .env.

The founder's choice (2026-09-29): Cloudflare R2 for development and production, AWS S3 as the
production alternative, the local disk when no keys are set. ``OMNISTACKAI_STORAGE_TARGET``
decides the order:

- ``dev`` (default): R2 dev bucket, then the local disk;
- ``prod``: R2 prod bucket, then AWS S3, then the local disk.

A store counts only when all of its keys are set. The app itself only ever sees the generic
``S3_*`` settings, so it runs unchanged against any of them - production needs keys, not code.

Cloud drives come through Uppy Companion, which runs only when ``OMNISTACKAI_COMPANION_SECRET`` is
set; each drive is offered only when its client ID and secret are. No value here is ever logged:
every secret is returned in ``secrets`` for the caller to mask.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

_PROVIDERS = (
    # (source name in the upload window, Companion's env pair, the platform's .env pair)
    ("google-drive", ("GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET")),
    ("dropbox", ("DROPBOX_APP_KEY", "DROPBOX_APP_SECRET")),
    ("onedrive", ("ONEDRIVE_CLIENT_ID", "ONEDRIVE_CLIENT_SECRET")),
    ("box", ("BOX_CLIENT_ID", "BOX_CLIENT_SECRET")),
)


@dataclass(frozen=True)
class UploadEnvironment:
    store: str  # "r2-dev" | "r2-prod" | "s3" | "local"
    api: tuple[tuple[str, str], ...]
    web: tuple[tuple[str, str], ...]
    companion: tuple[tuple[str, str], ...] = ()
    companion_port: int = 0
    secrets: tuple[str, ...] = field(default=(), repr=False)

    @property
    def companion_enabled(self) -> bool:
        return bool(self.companion)


def _get(source: Mapping[str, str], name: str) -> str:
    return (source.get(name) or "").strip()


def _r2(source: Mapping[str, str], which: str) -> dict[str, str] | None:
    names = {k: f"OMNISTACKAI_R2_{which}_{k}" for k in ("ACCOUNT_ID", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY", "BUCKET")}
    values = {k: _get(source, v) for k, v in names.items()}
    if not all(values.values()):
        return None
    return {
        "S3_ENDPOINT": f"https://{values['ACCOUNT_ID']}.r2.cloudflarestorage.com",
        "S3_REGION": "auto",
        "S3_BUCKET": values["BUCKET"],
        "S3_ACCESS_KEY_ID": values["ACCESS_KEY_ID"],
        "S3_SECRET_ACCESS_KEY": values["SECRET_ACCESS_KEY"],
        "S3_PUBLIC_URL": _get(source, f"OMNISTACKAI_R2_{which}_PUBLIC_URL"),
    }


def _s3(source: Mapping[str, str]) -> dict[str, str] | None:
    names = ("S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET")
    values = {n: _get(source, f"OMNISTACKAI_{n}") for n in names}
    if not all(values.values()):
        return None
    return {**values, "S3_PUBLIC_URL": _get(source, "OMNISTACKAI_S3_PUBLIC_URL")}


def resolve_store(source: Mapping[str, str]) -> tuple[str, dict[str, str] | None]:
    """(store name, its S3 settings) for the configured target; ("local", None) when none is set."""
    target = (_get(source, "OMNISTACKAI_STORAGE_TARGET") or "dev").lower()
    order = (("r2-prod", lambda: _r2(source, "PROD")), ("s3", lambda: _s3(source))) if target == "prod" \
        else (("r2-dev", lambda: _r2(source, "DEV")),)
    for name, settings in order:
        found = settings()
        if found:
            return name, found
    return "local", None


def upload_environment(
    *,
    project_key: str,
    api_url: str,
    has_companion: bool,
    source: Mapping[str, str] | None = None,
) -> UploadEnvironment:
    """The settings for one project's apps. ``api_url`` is where the API listens (Companion posts there)."""
    source = os.environ if source is None else source
    store, settings = resolve_store(source)
    local_root = _get(source, "OMNISTACKAI_LOCAL_STORAGE_DIR") or str(Path.home() / ".omnistackai" / "uploads")
    api: dict[str, str] = {"LOCAL_STORAGE_DIR": str(Path(local_root).expanduser() / project_key)}
    secrets: list[str] = []
    if settings:
        # One folder per project in the shared bucket, so a project's files can be found and deleted.
        api.update({"STORAGE_DRIVER": "s3", "STORAGE_PREFIX": project_prefix(project_key),
                    **{k: v for k, v in settings.items() if v}})
        secrets.append(settings["S3_SECRET_ACCESS_KEY"])
    else:
        api["STORAGE_DRIVER"] = "local"

    sources = ["camera"]
    companion: dict[str, str] = {}
    port = 0
    companion_secret = _get(source, "OMNISTACKAI_COMPANION_SECRET")
    if has_companion and companion_secret:
        companion_url = _get(source, "OMNISTACKAI_COMPANION_URL") or "http://localhost:3020"
        port = urlparse(companion_url).port or 3020
        companion = {
            "PORT": str(port),
            "COMPANION_URL": companion_url,
            "COMPANION_SECRET": companion_secret,
            "COMPANION_UPLOAD_URLS": f"{api_url.rstrip('/')}/uploads",
            "COMPANION_CLIENT_ORIGINS": ",".join(_client_origins(source)),
        }
        secrets.append(companion_secret)
        sources.append("url")
        for name, (key_env, secret_env) in _PROVIDERS:
            key, value = _get(source, f"OMNISTACKAI_{key_env}"), _get(source, f"OMNISTACKAI_{secret_env}")
            if key and value:
                companion[key_env], companion[secret_env] = key, value
                secrets.append(value)
                sources.append(name)
    web = {
        "NEXT_PUBLIC_UPLOAD_SOURCES": ",".join(sources),
        "NEXT_PUBLIC_COMPANION_URL": companion.get("COMPANION_URL", ""),
        "NEXT_PUBLIC_REMOTE_UPLOAD_ENDPOINT": f"{api_url.rstrip('/')}/uploads" if companion else "",
    }
    return UploadEnvironment(
        store=store,
        api=tuple(sorted(api.items())),
        web=tuple(sorted(web.items())),
        companion=tuple(sorted(companion.items())),
        companion_port=port,
        secrets=tuple(s for s in secrets if s),
    )


def project_prefix(project_key: str) -> str:
    return f"projects/{project_key}"


def project_key_for(repo_root: Path | str) -> str:
    """The key a project's files live under - the same for its previews and its published app."""
    from .plan import _database_name

    return _database_name(Path(repo_root))


def purge_project_files(project_key: str, source: Mapping[str, str] | None = None,
                        only: tuple[str, ...] = ("local", "r2-dev", "r2-prod", "s3")) -> dict[str, object]:
    """Delete a project's uploads everywhere the platform may have put them: the local disk and the
    project's folder in each configured store (R2 dev, R2 prod, AWS S3). Returns what was removed;
    a store that cannot be reached is reported, never raised, so deleting a project still completes."""
    import shutil

    from .s3_lite import S3Error, delete_prefix, target_from_settings

    source = dict(os.environ if source is None else source)
    report: dict[str, object] = {}
    local_root = _get(source, "OMNISTACKAI_LOCAL_STORAGE_DIR") or str(Path.home() / ".omnistackai" / "uploads")
    folder = Path(local_root).expanduser() / project_key
    if "local" in only and folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
        report["local"] = "deleted"
    stores = {"r2-dev": _r2(source, "DEV"), "r2-prod": _r2(source, "PROD"), "s3": _s3(source)}
    for name, settings in stores.items():
        if not settings or name not in only:
            continue
        try:
            report[name] = delete_prefix(target_from_settings(settings), project_prefix(project_key) + "/")
        except S3Error as error:
            report[name] = f"not cleaned: {error}"
    return report


def production_settings(source: Mapping[str, str] | None = None, project_key: str = "") -> tuple[dict[str, str], dict[str, str]]:
    """(the app's private settings, the compose settings) for a published app.

    Publishing is production, so the order is always R2 prod, then AWS S3, then the local disk
    (a volume in the published stack) - the development bucket is never used by a live app.
    """
    source = dict(os.environ if source is None else source)
    source["OMNISTACKAI_STORAGE_TARGET"] = "prod"
    store, settings = resolve_store(source)
    app: dict[str, str] = {"STORAGE_DRIVER": "s3", **{k: v for k, v in settings.items() if v}} if settings \
        else {"STORAGE_DRIVER": "local"}
    if settings and project_key:
        app["STORAGE_PREFIX"] = project_prefix(project_key)
    sources = ["camera"]
    secret = _get(source, "OMNISTACKAI_COMPANION_SECRET")
    if secret:
        app["COMPANION_SECRET"] = secret
        sources.append("url")
        for name, (key_env, secret_env) in _PROVIDERS:
            key, value = _get(source, f"OMNISTACKAI_{key_env}"), _get(source, f"OMNISTACKAI_{secret_env}")
            if key and value:
                app[key_env], app[secret_env] = key, value
                sources.append(name)
    return app, {"UPLOAD_SOURCES": ",".join(sources), "STORAGE": store}


def _client_origins(source: Mapping[str, str]) -> list[str]:
    console = _get(source, "OMNISTACKAI_CONSOLE_PORT") or "4321"
    return [f"http://127.0.0.1:{console}", f"http://localhost:{console}"]
