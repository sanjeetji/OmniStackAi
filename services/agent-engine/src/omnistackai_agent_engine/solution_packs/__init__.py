"""Public Solution Pack registry contract (R-434)."""

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
