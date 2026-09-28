"""Git service: materialize a GeneratedProject to disk as a customer-owned repository."""

from .errors import GitServiceError, MaterializeError, RepositoryError, TargetNotEmptyError
from .materialize import (
    MaterializeResult,
    RepositoryResult,
    commit_all,
    untrack_node_modules_links,
    create_repository,
    materialize_project,
)

__all__ = [
    "GitServiceError",
    "MaterializeError",
    "MaterializeResult",
    "RepositoryError",
    "RepositoryResult",
    "TargetNotEmptyError",
    "commit_all",
    "untrack_node_modules_links",
    "create_repository",
    "materialize_project",
]
