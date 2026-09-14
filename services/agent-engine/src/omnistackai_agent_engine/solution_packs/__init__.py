"""Public Solution Pack registry, manifest, and application contracts (R-434 to R-437)."""

from .manifest import (
    LEGACY_MANIFEST_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    MAX_MANIFEST_CHANGES,
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    SolutionPackChange,
    SolutionPackManifest,
    create_solution_pack_manifest,
    parse_solution_pack_manifest,
    validate_solution_pack_manifest,
)
from .application import SolutionPackApplicationResult, apply_solution_pack_manifest

from .registry import (
    BASELINE_SOLUTION_PACKS,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    MINIMAL_BLOG_PACK,
    RIDESHARE_FAVOURITES_PACK,
    SolutionPack,
    SolutionPackError,
    SolutionPackRecommendation,
    SolutionPackRegistry,
    canonical_ir_digest,
)

__all__ = [
    "LEGACY_MANIFEST_SCHEMA_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "MAX_MANIFEST_CHANGES",
    "ChangeArea",
    "ChangeOperation",
    "ChangeSource",
    "SolutionPackChange",
    "SolutionPackManifest",
    "create_solution_pack_manifest",
    "parse_solution_pack_manifest",
    "validate_solution_pack_manifest",
    "SolutionPackApplicationResult",
    "apply_solution_pack_manifest",
    "SolutionPack",
    "SolutionPackError",
    "SolutionPackRecommendation",
    "SolutionPackRegistry",
    "canonical_ir_digest",
    "MINIMAL_BLOG_PACK",
    "RIDESHARE_FAVOURITES_PACK",
    "BASELINE_SOLUTION_PACKS",
    "DEFAULT_SOLUTION_PACK_REGISTRY",
]
