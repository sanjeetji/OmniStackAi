"""Intake: turn a plain-English app description into an Application IR.

The first brick of the OmniStackAI "chat -> create an app" front door.
"""

from .build_app import (
    AppBuildResult,
    app_build_result_to_dict,
    build_app_from_ir,
    build_app_from_prompt,
    build_app_from_prompt_stream,
)
from .errors import IntakeError, IntakeResponseError
from .provider_resolution import resolve_generation_provider_from_env
from .nl_to_ir import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_TEMPLATE_EXAMPLE,
    DEFAULT_TIMEOUT_SECONDS,
    IntakeResult,
    build_intake_messages,
    generate_ir,
    generate_ir_stream,
    parse_ir_response,
)
from .scope_compiler import (
    DOMAIN_LIBRARY,
    Actor,
    AppSurface,
    DomainMatch,
    DomainSpec,
    ScopeOption,
    ScopeProposal,
    classify_domain,
    propose_ecosystem,
)
from .ecosystem import (
    DOMAIN_ENTITIES,
    EcosystemAppBuild,
    EcosystemBuildResult,
    EcosystemPlan,
    SurfaceApp,
    build_ecosystem,
    plan_ecosystem,
    plan_ecosystem_from_prompt,
    surface_to_ir,
)
from .scope_refinement import (
    DEFAULT_REFINEMENT_MAX_OUTPUT_TOKENS,
    DEFAULT_REFINEMENT_TIMEOUT_SECONDS,
    ScopeRefinementResult,
    build_scope_refinement_messages,
    parse_scope_refinement_response,
    plan_refined_ecosystem,
    refine_ecosystem,
)

__all__ = [
    "IntakeError",
    "IntakeResponseError",
    "IntakeResult",
    "build_intake_messages",
    "parse_ir_response",
    "generate_ir",
    "generate_ir_stream",
    "AppBuildResult",
    "app_build_result_to_dict",
    "build_app_from_ir",
    "build_app_from_prompt",
    "build_app_from_prompt_stream",
    "resolve_generation_provider_from_env",
    "DEFAULT_TEMPLATE_EXAMPLE",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_TIMEOUT_SECONDS",
    # Ecosystem Scope Compiler (R-430)
    "propose_ecosystem",
    "classify_domain",
    "ScopeProposal",
    "ScopeOption",
    "AppSurface",
    "Actor",
    "DomainMatch",
    "DomainSpec",
    "DOMAIN_LIBRARY",
    # Ecosystem planner/builder (R-431)
    "plan_ecosystem",
    "plan_ecosystem_from_prompt",
    "surface_to_ir",
    "build_ecosystem",
    "EcosystemPlan",
    "SurfaceApp",
    "EcosystemBuildResult",
    "EcosystemAppBuild",
    "DOMAIN_ENTITIES",
    # Opt-in unknown-domain refinement (R-432)
    "ScopeRefinementResult",
    "build_scope_refinement_messages",
    "parse_scope_refinement_response",
    "refine_ecosystem",
    "plan_refined_ecosystem",
    "DEFAULT_REFINEMENT_MAX_OUTPUT_TOKENS",
    "DEFAULT_REFINEMENT_TIMEOUT_SECONDS",
]
