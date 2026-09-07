"""Materialize a GeneratedProject to disk and initialize a customer-owned Git repository.

Writes only inside the caller-provided target directory (never the platform repo), uses the local
`git` CLI with an explicit commit identity (no global git config), and makes no network call. This
closes the first end-to-end builder slice: Application IR -> GeneratedProject -> owned Git repo.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..codegen import GeneratedProject
from .errors import MaterializeError, RepositoryError, TargetNotEmptyError


@dataclass(frozen=True, slots=True)
class MaterializeResult:
    target_dir: str
    file_count: int


@dataclass(frozen=True, slots=True)
class RepositoryResult:
    target_dir: str
    commit_sha: str
    file_count: int


def materialize_project(
    project: GeneratedProject, target_dir: str | os.PathLike[str], *, overwrite: bool = False
) -> MaterializeResult:
    """Write every generated file under ``target_dir``, refusing escapes and (unless overwrite) a
    non-empty target."""

    if not isinstance(project, GeneratedProject):
        raise MaterializeError("project must be a GeneratedProject")
    target = Path(target_dir).resolve()
    if target.exists():
        if not target.is_dir():
            raise MaterializeError("target exists and is not a directory")
        if any(target.iterdir()) and not overwrite:
            raise TargetNotEmptyError("target directory is not empty")
    target.mkdir(parents=True, exist_ok=True)

    for generated in project.files():
        destination = (target / generated.path).resolve()
        try:
            destination.relative_to(target)
        except ValueError as error:  # defense-in-depth; paths are already validated safe
            raise MaterializeError(f"refusing to write outside the target: {generated.path}") from error
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(generated.content, encoding="utf-8")
        if generated.executable:
            destination.chmod(0o755)

    return MaterializeResult(str(target), len(project))


def create_repository(
    project: GeneratedProject,
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    commit_message: str = "Initial commit",
    overwrite: bool = False,
) -> RepositoryResult:
    """Materialize the project, then `git init` + stage + one commit as the given customer identity."""

    if not author_name or not author_email:
        raise RepositoryError("author_name and author_email are required")
    result = materialize_project(project, target_dir, overwrite=overwrite)
    target = Path(result.target_dir)

    identity = (author_name, author_email)
    _git(target, ["init", "-q"])
    _git(target, ["add", "-A"])
    _git(target, ["commit", "-q", "-m", commit_message], identity=identity)
    commit_sha = _git(target, ["rev-parse", "HEAD"], identity=identity).strip()
    return RepositoryResult(str(target), commit_sha, result.file_count)


def commit_all(
    target_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    message: str,
) -> RepositoryResult:
    """Stage every change under an existing repo and record one commit as the given identity.

    Used to record an applied edit (see the edit loop). The working tree must already contain the
    changes; this only `git add -A` + `git commit`. No network call is made.
    """

    if not author_name or not author_email:
        raise RepositoryError("author_name and author_email are required")
    if not message:
        raise RepositoryError("a commit message is required")
    target = Path(target_dir).resolve()
    if not (target / ".git").exists():
        raise RepositoryError("target is not a git repository")

    identity = (author_name, author_email)
    _git(target, ["add", "-A"])
    _git(target, ["commit", "-q", "-m", message], identity=identity)
    commit_sha = _git(target, ["rev-parse", "HEAD"], identity=identity).strip()
    tracked = _git(target, ["ls-files"]).splitlines()
    return RepositoryResult(str(target), commit_sha, len(tracked))


def _git(cwd: Path, args: list[str], *, identity: tuple[str, str] | None = None) -> str:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if identity is not None:
        name, email = identity
        env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = name
        env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = email
    process = subprocess.run(
        ["git", *args], cwd=str(cwd), env=env, capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        raise RepositoryError(f"git {args[0]} failed with exit code {process.returncode}")
    return process.stdout
