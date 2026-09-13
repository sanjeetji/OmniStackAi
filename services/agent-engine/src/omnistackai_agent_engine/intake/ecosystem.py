"""Scope -> Application IRs: materialize a multi-app ecosystem from one prompt (R-431).

Second brick of the differentiating spine. R-430's `scope_compiler` *proposes* a multi-app ecosystem;
this module makes it *real*: it maps each proposed `AppSurface` to a valid, `validate_ir`-clean
`ApplicationIR` (built from a curated per-domain data model + a deterministic CRUD deriver whose endpoints
WIRE to real repository-backed handlers), and `build_ecosystem` materializes the chosen build scope as
MULTIPLE owned Git repos by reusing the existing `build_app_from_ir` (assembler + git-service).

Deterministic and offline (no model/network/clock/randomness) so it runs under `task verify`. Any cheap-LLM
data-model refinement for prompts outside the curated domains is a later, opt-in brick.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ..application_ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    BackendStrategy,
    DatabaseStrategy,
    Entity,
    Field,
    FieldType,
    HttpMethod,
    MobileProfile,
    Platform,
    ProjectStrategy,
    Relation,
    RelationKind,
    RepoStrategy,
    Role,
    Screen,
    WebStrategy,
    normalize_ir,
    validate_ir,
)
from ..application_ir.validate import has_errors
from .build_app import AppBuildResult, build_app_from_ir
from .scope_compiler import AppSurface, ScopeProposal, propose_ecosystem

# ---------------------------------------------------------------------------
# Small deterministic string helpers
# ---------------------------------------------------------------------------


def _snake(name: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0 and not name[i - 1].isupper():
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def _lower_camel(name: str) -> str:
    return name[:1].lower() + name[1:]


def _plural(snake: str) -> str:
    if snake.endswith("y") and (len(snake) < 2 or snake[-2] not in "aeiou"):
        return snake[:-1] + "ies"
    if snake.endswith(("s", "x", "z", "ch", "sh")):
        return snake + "es"
    return snake + "s"


def _slug(text: str) -> str:
    chars = [c.lower() if c.isalnum() else "-" for c in text]
    slug = "".join(chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "app"


def _role_id(actor_name: str) -> str:
    return _slug(actor_name).replace("-", "_")


# ---------------------------------------------------------------------------
# Curated per-domain data models (compact but real; typed fields + FK relations)
# ---------------------------------------------------------------------------

_ID = Field("id", FieldType.UUID)


def _rel(name: str, target: str) -> Relation:
    return Relation(name, target, RelationKind.MANY_TO_ONE)


DOMAIN_ENTITIES: dict[str, tuple[Entity, ...]] = {
    "food-delivery": (
        Entity("Restaurant", (_ID, Field("name", FieldType.STRING), Field("cuisine", FieldType.STRING, required=False), Field("is_open", FieldType.BOOL))),
        Entity("MenuItem", (_ID, Field("name", FieldType.STRING), Field("price", FieldType.FLOAT), Field("available", FieldType.BOOL)), relations=(_rel("restaurant", "Restaurant"),)),
        Entity("Order", (_ID, Field("status", FieldType.STRING), Field("total", FieldType.FLOAT), Field("placed_at", FieldType.DATETIME, required=False)), relations=(_rel("restaurant", "Restaurant"),)),
    ),
    "rideshare": (
        Entity("Rider", (_ID, Field("name", FieldType.STRING), Field("phone", FieldType.STRING, required=False))),
        Entity("Driver", (_ID, Field("name", FieldType.STRING), Field("rating", FieldType.FLOAT, required=False), Field("is_online", FieldType.BOOL))),
        Entity("Trip", (_ID, Field("status", FieldType.STRING), Field("fare", FieldType.FLOAT, required=False), Field("requested_at", FieldType.DATETIME, required=False)), relations=(_rel("rider", "Rider"),)),
    ),
    "marketplace": (
        Entity("Seller", (_ID, Field("name", FieldType.STRING), Field("approved", FieldType.BOOL))),
        Entity("Listing", (_ID, Field("title", FieldType.STRING), Field("price", FieldType.FLOAT), Field("active", FieldType.BOOL)), relations=(_rel("seller", "Seller"),)),
        Entity("Purchase", (_ID, Field("quantity", FieldType.INT), Field("total", FieldType.FLOAT)), relations=(_rel("listing", "Listing"),)),
    ),
    "e-commerce": (
        Entity("Category", (_ID, Field("name", FieldType.STRING))),
        Entity("Product", (_ID, Field("name", FieldType.STRING), Field("price", FieldType.FLOAT), Field("stock", FieldType.INT), Field("active", FieldType.BOOL)), relations=(_rel("category", "Category"),)),
        Entity("Order", (_ID, Field("status", FieldType.STRING), Field("total", FieldType.FLOAT), Field("placed_at", FieldType.DATETIME, required=False))),
    ),
    "b2b-saas": (
        Entity("Workspace", (_ID, Field("name", FieldType.STRING), Field("plan", FieldType.STRING, required=False))),
        Entity("Project", (_ID, Field("name", FieldType.STRING), Field("status", FieldType.STRING)), relations=(_rel("workspace", "Workspace"),)),
        Entity("Task", (_ID, Field("title", FieldType.STRING), Field("done", FieldType.BOOL)), relations=(_rel("project", "Project"),)),
    ),
    "healthcare-clinic": (
        Entity("Patient", (_ID, Field("name", FieldType.STRING), Field("date_of_birth", FieldType.DATETIME, required=False))),
        Entity("Appointment", (_ID, Field("status", FieldType.STRING), Field("scheduled_at", FieldType.DATETIME)), relations=(_rel("patient", "Patient"),)),
        Entity("ClinicalNote", (_ID, Field("body", FieldType.TEXT)), relations=(_rel("appointment", "Appointment"),)),
    ),
    "booking": (
        Entity("Service", (_ID, Field("name", FieldType.STRING), Field("duration_minutes", FieldType.INT), Field("price", FieldType.FLOAT))),
        Entity("Booking", (_ID, Field("status", FieldType.STRING), Field("scheduled_at", FieldType.DATETIME)), relations=(_rel("service", "Service"),)),
    ),
    "learning": (
        Entity("Course", (_ID, Field("title", FieldType.STRING), Field("published", FieldType.BOOL))),
        Entity("Lesson", (_ID, Field("title", FieldType.STRING), Field("ordering", FieldType.INT)), relations=(_rel("course", "Course"),)),
        Entity("Enrollment", (_ID, Field("progress", FieldType.FLOAT)), relations=(_rel("course", "Course"),)),
    ),
    "social": (
        Entity("Member", (_ID, Field("handle", FieldType.STRING), Field("bio", FieldType.TEXT, required=False))),
        Entity("Post", (_ID, Field("body", FieldType.TEXT), Field("created_at", FieldType.DATETIME, required=False)), relations=(_rel("member", "Member"),)),
        Entity("Comment", (_ID, Field("body", FieldType.TEXT)), relations=(_rel("post", "Post"),)),
    ),
    "blog-cms": (
        Entity("Article", (_ID, Field("title", FieldType.STRING), Field("body", FieldType.TEXT), Field("published", FieldType.BOOL))),
        Entity("Comment", (_ID, Field("body", FieldType.TEXT)), relations=(_rel("article", "Article"),)),
    ),
    # Fallback for the `custom-application` scope (no known domain).
    "custom-application": (
        Entity("Item", (_ID, Field("name", FieldType.STRING), Field("description", FieldType.TEXT, required=False), Field("active", FieldType.BOOL))),
    ),
}

_FK_KINDS = (RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE)


# ---------------------------------------------------------------------------
# Deterministic CRUD API / screen derivation (endpoints that wire to repositories)
# ---------------------------------------------------------------------------


def _derive_apis(entities: tuple[Entity, ...]) -> tuple[ApiEndpoint, ...]:
    by_name = {e.name: e for e in entities}
    apis: list[ApiEndpoint] = []
    for entity in entities:
        plural = _plural(_snake(entity.name))
        idp = f"{_lower_camel(entity.name)}Id"
        apis.append(ApiEndpoint(HttpMethod.GET, f"/{plural}", auth=False, response_schema=entity.name))
        apis.append(ApiEndpoint(HttpMethod.POST, f"/{plural}", auth=True, request_schema=entity.name, response_schema=entity.name))
        apis.append(ApiEndpoint(HttpMethod.GET, f"/{plural}/{{{idp}}}", auth=False, response_schema=entity.name))
        apis.append(ApiEndpoint(HttpMethod.PUT, f"/{plural}/{{{idp}}}", auth=True, request_schema=entity.name, response_schema=entity.name))
        apis.append(ApiEndpoint(HttpMethod.DELETE, f"/{plural}/{{{idp}}}", auth=True, response_schema=entity.name))
    # Sub-collection list for a child with exactly one FK relation -> parent-scoped list wiring.
    for entity in entities:
        fks = [r for r in entity.relations if r.kind in _FK_KINDS]
        if len(fks) != 1:
            continue
        parent = by_name.get(fks[0].target_entity)
        if parent is None:
            continue
        parent_plural = _plural(_snake(parent.name))
        child_plural = _plural(_snake(entity.name))
        pidp = f"{_lower_camel(parent.name)}Id"
        apis.append(ApiEndpoint(HttpMethod.GET, f"/{parent_plural}/{{{pidp}}}/{child_plural}", auth=False, response_schema=entity.name))
    return tuple(apis)


def _derive_screens(entities: tuple[Entity, ...], role_id: str) -> tuple[Screen, ...]:
    screens: list[Screen] = []
    for entity in entities:
        base = _snake(entity.name)
        screens.append(Screen(f"{base}_list", role_id, components=("list",), actions=("open",)))
        screens.append(Screen(f"{base}_editor", role_id, components=("form",), actions=("save",)))
    return tuple(screens)


# ---------------------------------------------------------------------------
# Surface -> IR, plan, and build
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SurfaceApp:
    surface: AppSurface
    ir: ApplicationIR

    def to_dict(self) -> dict:
        return {
            "surface": self.surface.to_dict(),
            "app_name": self.ir.name,
            "slug": _slug(self.ir.name),
            "entities": [e.name for e in self.ir.entities],
            "api_count": len(self.ir.apis),
            "screen_count": len(self.ir.screens),
        }


@dataclass(frozen=True)
class EcosystemPlan:
    prompt: str
    domain: str
    option_id: str
    apps: tuple[SurfaceApp, ...]

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "domain": self.domain,
            "option_id": self.option_id,
            "apps": [a.to_dict() for a in self.apps],
        }


def _roles_for(proposal: ScopeProposal) -> tuple[Role, ...]:
    seen: dict[str, Role] = {}
    for actor in proposal.actors:
        rid = _role_id(actor.name)
        # Admin/operators read+write; customers read+write their own data too.
        seen.setdefault(rid, Role(rid, ("read", "write")))
    if not seen:
        seen["user"] = Role("user", ("read", "write"))
    return tuple(seen.values())


def surface_to_ir(
    proposal: ScopeProposal,
    surface: AppSurface,
    *,
    entities: tuple[Entity, ...] | None = None,
) -> ApplicationIR:
    """Build a validate_ir-clean ApplicationIR for one surface of the proposed ecosystem."""
    entities = entities or DOMAIN_ENTITIES.get(proposal.domain, DOMAIN_ENTITIES["custom-application"])
    roles = _roles_for(proposal)
    role_id = _role_id(surface.actor)
    if role_id not in {r.id for r in roles}:
        role_id = roles[0].id
    ir = ApplicationIR(
        name=surface.name,
        description=f"{surface.description} (part of the {proposal.domain} platform generated by OmniStackAI)",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.NONE,
            WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=roles,
        entities=entities,
        apis=_derive_apis(entities),
        screens=_derive_screens(entities, role_id),
    )
    ir = normalize_ir(ir)
    issues = validate_ir(ir)
    if has_errors(issues):
        detail = "; ".join(f"{i.location}: {i.message}" for i in issues if i.severity.name == "ERROR")
        raise ValueError(f"surface_to_ir produced an invalid IR for '{surface.name}': {detail}")
    return ir


def _surfaces_for_option(proposal: ScopeProposal, option_id: str) -> tuple[AppSurface, ...]:
    for option in proposal.options:
        if option.id == option_id:
            return option.surfaces
    # Unknown option id -> the whole ecosystem.
    return proposal.surfaces


def plan_ecosystem(
    proposal: ScopeProposal,
    option_id: str = "complete",
    *,
    entities: tuple[Entity, ...] | None = None,
) -> EcosystemPlan:
    """Turn a ScopeProposal + build-scope option into an EcosystemPlan (one IR per selected surface)."""
    surfaces = _surfaces_for_option(proposal, option_id)
    apps = tuple(
        SurfaceApp(surface, surface_to_ir(proposal, surface, entities=entities))
        for surface in surfaces
    )
    return EcosystemPlan(prompt=proposal.prompt, domain=proposal.domain, option_id=option_id, apps=apps)


def plan_ecosystem_from_prompt(prompt: str, option_id: str = "complete") -> EcosystemPlan:
    """Convenience: classify the prompt (deterministically) and plan its ecosystem."""
    return plan_ecosystem(propose_ecosystem(prompt), option_id)


@dataclass(frozen=True)
class EcosystemAppBuild:
    surface_kind: str
    app_name: str
    slug: str
    target_dir: str
    file_count: int
    commit_sha: str

    def to_dict(self) -> dict:
        return {
            "surface_kind": self.surface_kind,
            "app_name": self.app_name,
            "slug": self.slug,
            "target_dir": self.target_dir,
            "file_count": self.file_count,
            "commit_sha": self.commit_sha,
        }


@dataclass(frozen=True)
class EcosystemBuildResult:
    prompt: str
    domain: str
    option_id: str
    root_dir: str
    apps: tuple[EcosystemAppBuild, ...]

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "domain": self.domain,
            "option_id": self.option_id,
            "root_dir": self.root_dir,
            "apps": [a.to_dict() for a in self.apps],
        }


def build_ecosystem(
    plan: EcosystemPlan,
    out_dir: str | os.PathLike[str],
    *,
    author_name: str,
    author_email: str,
    overwrite: bool = False,
) -> EcosystemBuildResult:
    """Materialize each app in the plan as its own owned Git repo under ``out_dir/<slug>/``."""
    root = os.fspath(out_dir)
    used: dict[str, int] = {}
    builds: list[EcosystemAppBuild] = []
    for app in plan.apps:
        slug = _slug(app.ir.name)
        # Guarantee unique directories even if two surfaces share a name.
        count = used.get(slug, 0)
        used[slug] = count + 1
        unique_slug = slug if count == 0 else f"{slug}-{count + 1}"
        target = os.path.join(root, unique_slug)
        result: AppBuildResult = build_app_from_ir(
            app.ir,
            target,
            author_name=author_name,
            author_email=author_email,
            prompt=plan.prompt,
            overwrite=overwrite,
        )
        builds.append(
            EcosystemAppBuild(
                surface_kind=app.surface.kind,
                app_name=app.ir.name,
                slug=unique_slug,
                target_dir=result.target_dir,
                file_count=result.file_count,
                commit_sha=result.commit_sha,
            )
        )
    return EcosystemBuildResult(
        prompt=plan.prompt,
        domain=plan.domain,
        option_id=plan.option_id,
        root_dir=root,
        apps=tuple(builds),
    )
