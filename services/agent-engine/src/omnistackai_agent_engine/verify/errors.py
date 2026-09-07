"""Errors for the verifiable-engineering verify-plan layer."""

from __future__ import annotations


class VerifyError(Exception):
    """Base class for verify-plan errors."""


class UnsupportedVerifyTargetError(VerifyError):
    """Raised when no verify plan exists for a generation target."""
