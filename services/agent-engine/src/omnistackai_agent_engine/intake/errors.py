"""Errors raised by the prompt -> Application IR intake agent."""

from __future__ import annotations


class IntakeError(Exception):
    """Base error for the intake agent (bad input or unusable model output)."""


class IntakeResponseError(IntakeError):
    """The model's response could not be turned into a valid Application IR."""
