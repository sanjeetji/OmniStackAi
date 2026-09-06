"""Stable, boundary-safe errors for the Git service."""


class GitServiceError(Exception):
    """Base error for materializing and initializing customer repositories."""

    code = "git_service_error"


class MaterializeError(GitServiceError):
    code = "materialize_error"


class TargetNotEmptyError(GitServiceError):
    code = "target_not_empty"


class RepositoryError(GitServiceError):
    code = "repository_error"
