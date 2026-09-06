"""In-memory generated file-set — a customer project's source tree as validated records.

Nothing here touches disk. A `GeneratedFile` is one path->content pair with a safe relative path; a
`GeneratedProject` is an immutable, deterministically ordered set of them for one target. A later
Git-service task materializes a project to disk; codegen only produces this pure value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import DuplicateFileError, InvalidGeneratedFileError

_MAX_PATH = 400
_MAX_CONTENT = 2_000_000
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_path(path: str) -> str:
    if not isinstance(path, str) or not path or len(path) > _MAX_PATH:
        raise InvalidGeneratedFileError("path must be a non-empty string within the length limit")
    if path != path.strip() or "\\" in path or _CONTROL.search(path):
        raise InvalidGeneratedFileError("path must be a clean POSIX path without backslashes or control chars")
    if path.startswith("/"):
        raise InvalidGeneratedFileError("path must be relative, not absolute")
    segments = path.split("/")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise InvalidGeneratedFileError("path must not contain empty, '.', or '..' segments")
        if not _SEGMENT.fullmatch(segment):
            raise InvalidGeneratedFileError(f"path segment is not allowed: {segment!r}")
    return path


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    path: str
    content: str
    executable: bool = False

    def __post_init__(self) -> None:
        _validate_path(self.path)
        if not isinstance(self.content, str):
            raise InvalidGeneratedFileError("content must be a string")
        if len(self.content) > _MAX_CONTENT:
            raise InvalidGeneratedFileError("content exceeds the size limit")
        if not isinstance(self.executable, bool):
            raise InvalidGeneratedFileError("executable must be a boolean")


class GeneratedProject:
    """An immutable, deterministically ordered set of generated files for one target."""

    def __init__(self, target: str, files: tuple[GeneratedFile, ...] | list[GeneratedFile] = ()) -> None:
        if not isinstance(target, str) or not target:
            raise InvalidGeneratedFileError("target must be a non-empty string")
        indexed: dict[str, GeneratedFile] = {}
        for generated in files:
            if not isinstance(generated, GeneratedFile):
                raise InvalidGeneratedFileError("files must be GeneratedFile records")
            if generated.path in indexed:
                raise DuplicateFileError(f"duplicate generated path: {generated.path}")
            indexed[generated.path] = generated
        self._target = target
        self._files = tuple(indexed[path] for path in sorted(indexed))

    @property
    def target(self) -> str:
        return self._target

    def files(self) -> tuple[GeneratedFile, ...]:
        return self._files

    def paths(self) -> tuple[str, ...]:
        return tuple(generated.path for generated in self._files)

    def get(self, path: str) -> GeneratedFile:
        for generated in self._files:
            if generated.path == path:
                return generated
        raise KeyError(path)

    def merge(self, other: "GeneratedProject") -> "GeneratedProject":
        if other.target != self._target:
            raise InvalidGeneratedFileError("cannot merge projects with different targets")
        return GeneratedProject(self._target, (*self._files, *other._files))

    def __len__(self) -> int:
        return len(self._files)
