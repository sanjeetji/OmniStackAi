"""Errors for the edit loop (project diff + patch apply)."""

from __future__ import annotations


class EditError(Exception):
    """Base class for edit-loop errors."""


class ApplyError(EditError):
    """Raised when applying a diff to disk fails or would escape the target."""
