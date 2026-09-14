"""Public Solution Pack registry and customization-manifest contracts (R-434 to R-436)."""

from .manifest import (
    MANIFEST_SCHEMA_VERSION,
    MAX_MANIFEST_CHANGES,
    ChangeArea,
    ChangeOperation,
    ChangeSource,
    SolutionPackChange,
    SolutionPackManifest,
    create_solution_pack_manifest,
    parse_solution_pack_manifest,
)

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
    "MANIFEST_SCHEMA_VERSION",
    "MAX_MANIFEST_CHANGES",
    "ChangeArea",
    "ChangeOperation",
    "ChangeSource",
    "SolutionPackChange",
    "SolutionPackManifest",
    "create_solution_pack_manifest",
    "parse_solution_pack_manifest",
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
