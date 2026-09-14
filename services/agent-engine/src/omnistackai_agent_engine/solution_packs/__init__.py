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
from .ai_delta import (
    AIDeltaProposal,
    build_ai_delta_messages,
    generate_ai_delta_proposal,
    parse_ai_delta_proposal,
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

from .builder import SolutionPackBuildResult, build_solution_pack_project
from .package import (
    PACKAGE_SCHEMA_VERSION,
    SolutionPackPackage,
    parse_solution_pack_package,
    verify_package,
)
from .ecosystem_pack import (
    ECOSYSTEM_PACK_SCHEMA_VERSION,
    EcosystemSurfacePackage,
    EcosystemPackPackage,
    compute_ecosystem_checksum,
    parse_ecosystem_pack_package,
    verify_ecosystem_pack,
    synthesize_ecosystem_pack,
)
from .ecosystem_registry import (
    DEFAULT_ECOSYSTEM_PACK_REGISTRY,
    EcosystemPack,
    EcosystemPackRecommendation,
    EcosystemPackRegistry,
    build_default_ecosystem_packs,
)
from .ecosystem_auth import (
    CrossAppAuthMatrix,
    EcosystemAuthContract,
    EcosystemRoleBinding,
    generate_surface_tokens,
    mint_ecosystem_token,
    synthesize_ecosystem_auth,
    verify_ecosystem_token,
)
from .ecosystem_state import (
    CrossAppEndpointBinding,
    EcosystemStateBinding,
    EntityStateFlow,
    SharedEntityBinding,
    StateTransition,
    SurfaceEnvBinding,
    synthesize_ecosystem_state,
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
    "AIDeltaProposal",
    "build_ai_delta_messages",
    "generate_ai_delta_proposal",
    "parse_ai_delta_proposal",
    "SolutionPackBuildResult",
    "build_solution_pack_project",
    "PACKAGE_SCHEMA_VERSION",
    "SolutionPackPackage",
    "parse_solution_pack_package",
    "verify_package",
    "ECOSYSTEM_PACK_SCHEMA_VERSION",
    "EcosystemSurfacePackage",
    "EcosystemPackPackage",
    "compute_ecosystem_checksum",
    "parse_ecosystem_pack_package",
    "verify_ecosystem_pack",
    "synthesize_ecosystem_pack",
    "EcosystemPack",
    "EcosystemPackRecommendation",
    "EcosystemPackRegistry",
    "build_default_ecosystem_packs",
    "DEFAULT_ECOSYSTEM_PACK_REGISTRY",
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
