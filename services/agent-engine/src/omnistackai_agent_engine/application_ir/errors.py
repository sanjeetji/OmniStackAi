"""Stable, boundary-safe errors for the Application IR."""


class ApplicationIRError(Exception):
    """Base error for Application IR construction and serialization."""

    code = "application_ir_error"


class InvalidIRError(ApplicationIRError):
    code = "invalid_ir"


class UnsupportedIRVersionError(ApplicationIRError):
    code = "unsupported_ir_version"
