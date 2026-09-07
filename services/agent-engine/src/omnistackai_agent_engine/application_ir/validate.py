"""Semantic validation and normalization for the Application IR.

`ir.py` validates each record on construction (types, bounded ids, uniqueness, relation targets,
screen roles). This module adds *cross-cutting* semantic checks that are advisory or integrity-level
but not required to construct a valid record — e.g., an API schema that references an undeclared
entity, or a project strategy that disagrees with the declared platforms — and a deterministic
normalizer that returns a canonical (sorted) IR for stable diffs. Pure and offline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .ir import AdminStrategy, ApplicationIR, MobileProfile, Platform, WebStrategy


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Issue:
    severity: Severity
    code: str
    message: str
    location: str


def validate_ir(ir: ApplicationIR) -> tuple[Issue, ...]:
    """Return an ordered tuple of semantic issues. A clean IR yields no errors (possibly no issues)."""

    if not isinstance(ir, ApplicationIR):
        raise TypeError("validate_ir expects an ApplicationIR")

    issues: list[Issue] = []
    declared = {entity.name for entity in ir.entities}
    role_ids = {role.id for role in ir.roles}

    # Integrity: an API schema reference must name a declared entity; a required role must be declared.
    for api in ir.apis:
        location = f"{api.method.value} {api.path}"
        for attribute, label in (
            (api.request_schema, "request_schema"),
            (api.response_schema, "response_schema"),
            (api.error_schema, "error_schema"),
        ):
            if attribute is not None and attribute not in declared:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "unknown_schema_reference",
                        f"{label} references undeclared entity {attribute!r}",
                        location,
                    )
                )
        for role in api.required_roles:
            if role not in role_ids:
                issues.append(
                    Issue(
                        Severity.ERROR,
                        "unknown_role_reference",
                        f"required_roles references undeclared role {role!r}",
                        location,
                    )
                )

    # Consistency: strategy vs declared platforms (both directions), for the tiers that have a 'none'.
    platforms = set(ir.platforms)
    strategy = ir.project_strategy
    for strategy_set, platform, label in (
        (strategy.web_strategy is not WebStrategy.NONE, Platform.WEB, "web_strategy"),
        (strategy.admin_strategy is not AdminStrategy.NONE, Platform.ADMIN, "admin_strategy"),
        (strategy.mobile_profile is not MobileProfile.NONE, Platform.MOBILE, "mobile_profile"),
    ):
        present = platform in platforms
        if strategy_set and not present:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "platform_strategy_mismatch",
                    f"{label} is configured but platform {platform.value!r} is not listed",
                    label,
                )
            )
        elif present and not strategy_set:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "platform_strategy_mismatch",
                    f"platform {platform.value!r} is listed but {label} is 'none'",
                    label,
                )
            )

    return tuple(issues)


def has_errors(issues: tuple[Issue, ...]) -> bool:
    return any(issue.severity is Severity.ERROR for issue in issues)


_PLATFORM_ORDER = list(Platform)


def normalize_ir(ir: ApplicationIR) -> ApplicationIR:
    """Return a canonical ApplicationIR: platforms in enum order and collections sorted stably.

    Entity field order is preserved (it is meaningful); entities, roles, apis, screens, and acceptance
    criteria are sorted by a stable key. Idempotent and lossless through to_dict.
    """

    if not isinstance(ir, ApplicationIR):
        raise TypeError("normalize_ir expects an ApplicationIR")

    return ApplicationIR(
        name=ir.name,
        description=ir.description,
        platforms=tuple(sorted(ir.platforms, key=_PLATFORM_ORDER.index)),
        project_strategy=ir.project_strategy,
        roles=tuple(sorted(ir.roles, key=lambda role: role.id)),
        entities=tuple(sorted(ir.entities, key=lambda entity: entity.name)),
        apis=tuple(sorted(ir.apis, key=lambda api: (api.path, api.method.value))),
        screens=tuple(sorted(ir.screens, key=lambda screen: screen.id)),
        acceptance_criteria=tuple(sorted(ir.acceptance_criteria, key=lambda c: c.requirement_id)),
        schema_version=ir.schema_version,
    )
