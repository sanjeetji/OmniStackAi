"""Scope -> Application IRs and transparent pack recommendation (R-431, R-433, R-435).

Second brick of the differentiating spine. R-430's `scope_compiler` *proposes* a multi-app ecosystem;
this module makes it *real*: it maps each proposed `AppSurface` to a valid, `validate_ir`-clean
`ApplicationIR` (built from a curated per-domain data model + a deterministic CRUD deriver whose endpoints
WIRE to real repository-backed handlers), and `build_ecosystem` materializes the chosen build scope as
MULTIPLE owned Git repos by reusing the existing `build_app_from_ir` (assembler + git-service).

Deterministic and offline (no model/network/clock/randomness) so it runs under `task verify`. R-433 adds
deterministic per-surface entity/capability scoping after the model is selected. Relation targets are retained
as read dependencies, while editor screens and writes stay limited to explicitly writable data. R-435 adds
an exact-compatible Solution Pack recommendation to plan metadata but does not apply it to generated output.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace

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
from ..projectplan import build_project_plan
from ..solution_packs import (
    AIDeltaProposal,
    DEFAULT_SOLUTION_PACK_REGISTRY,
    SolutionPackApplicationResult,
    SolutionPackError,
    SolutionPackManifest,
    SolutionPackRecommendation,
    SolutionPackRegistry,
    apply_solution_pack_manifest,
)
from ..verify import verify_plans_for_ir
from .build_app import AppBuildResult, build_app_from_ir
from .surface_form import app_replaces_web, form_for_surface
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

# Business entities intentionally visible on each curated surface. Relation dependencies are added below, so
# this table describes surface intent rather than a denormalized schema copy. Some compact
# domains legitimately need their complete 2-3 entity model on more than one surface.
CURATED_SURFACE_ENTITIES: dict[str, dict[str, tuple[str, ...]]] = {
    "food-delivery": {
        "customer_web": ("Restaurant", "MenuItem", "Order"),
        "merchant_portal": ("Restaurant", "MenuItem", "Order"),
        "driver_portal": ("Order",),
        "admin_dashboard": ("Restaurant", "Order"),
    },
    "rideshare": {
        "customer_pwa": ("Rider", "Driver", "Trip"),
        "driver_portal": ("Driver", "Trip"),
        "admin_dashboard": ("Rider", "Driver", "Trip"),
    },
    "marketplace": {
        "customer_web": ("Seller", "Listing", "Purchase"),
        "seller_portal": ("Seller", "Listing", "Purchase"),
        "admin_dashboard": ("Seller", "Listing", "Purchase"),
    },
    "e-commerce": {
        "customer_web": ("Category", "Product", "Order"),
        "admin_dashboard": ("Category", "Product", "Order"),
    },
    "b2b-saas": {
        "customer_web": ("Workspace", "Project", "Task"),
        "admin_dashboard": ("Workspace",),
    },
    "healthcare-clinic": {
        "customer_web": ("Patient", "Appointment"),
        "provider_portal": ("Patient", "Appointment", "ClinicalNote"),
        "admin_dashboard": ("Patient", "Appointment"),
    },
    "booking": {
        "customer_web": ("Service", "Booking"),
        "provider_portal": ("Service", "Booking"),
        "admin_dashboard": ("Service", "Booking"),
    },
    "learning": {
        "customer_web": ("Course", "Lesson", "Enrollment"),
        "provider_portal": ("Course", "Lesson"),
        "admin_dashboard": ("Course", "Enrollment"),
    },
    "social": {
        "customer_web": ("Member", "Post", "Comment"),
        "admin_dashboard": ("Member", "Post", "Comment"),
    },
    "blog-cms": {
        "public_web": ("Article",),
        "provider_portal": ("Article", "Comment"),
        "admin_dashboard": ("Article",),
    },
}

# Mutation authority is deliberately narrower than visibility. For example, customers can browse a menu but
# only create/update their orders; public readers receive no mutations at all. Row ownership is a later auth
# policy brick, so this matrix does not claim to enforce per-record ownership.
CURATED_SURFACE_WRITABLE_ENTITIES: dict[str, dict[str, tuple[str, ...]]] = {
    "food-delivery": {
        "customer_web": ("Order",),
        "merchant_portal": ("Restaurant", "MenuItem", "Order"),
        "driver_portal": ("Order",),
        "admin_dashboard": ("Restaurant", "Order"),
    },
    "rideshare": {
        "customer_pwa": ("Rider", "Trip"),
        "driver_portal": ("Driver", "Trip"),
        "admin_dashboard": ("Rider", "Driver", "Trip"),
    },
    "marketplace": {
        "customer_web": ("Purchase",),
        "seller_portal": ("Seller", "Listing", "Purchase"),
        "admin_dashboard": ("Seller", "Listing", "Purchase"),
    },
    "e-commerce": {
        "customer_web": ("Order",),
        "admin_dashboard": ("Category", "Product", "Order"),
    },
    "b2b-saas": {
        "customer_web": ("Workspace", "Project", "Task"),
        "admin_dashboard": ("Workspace",),
    },
    "healthcare-clinic": {
        "customer_web": ("Patient", "Appointment"),
        "provider_portal": ("Patient", "Appointment", "ClinicalNote"),
        "admin_dashboard": ("Patient", "Appointment"),
    },
    "booking": {
        "customer_web": ("Booking",),
        "provider_portal": ("Service", "Booking"),
        "admin_dashboard": ("Service", "Booking"),
    },
    "learning": {
        "customer_web": ("Enrollment",),
        "provider_portal": ("Course", "Lesson"),
        "admin_dashboard": ("Course", "Enrollment"),
    },
    "social": {
        "customer_web": ("Member", "Post", "Comment"),
        "admin_dashboard": ("Member", "Post", "Comment"),
    },
    "blog-cms": {
        "public_web": (),
        "provider_portal": ("Article", "Comment"),
        "admin_dashboard": ("Article",),
    },
}

_FK_KINDS = (RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE)


def _word_forms(text: str) -> frozenset[str]:
    """Return conservative lowercase word/singular forms for deterministic entity-name matching."""
    words = re.findall(
        r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|[0-9]+",
        text.replace("_", " "),
    )
    forms = {word.lower() for word in words if word}
    for word in tuple(forms):
        if word.endswith("ies") and len(word) > 3:
            forms.add(word[:-3] + "y")
        elif word.endswith("ing") and len(word) > 5:
            forms.add(word[:-3])
        elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            forms.add(word[:-1])
    return frozenset(forms)


def _primary_entity_names(
    proposal: ScopeProposal,
    surface: AppSurface,
    entities: tuple[Entity, ...],
) -> frozenset[str]:
    available = {entity.name for entity in entities}
    curated = CURATED_SURFACE_ENTITIES.get(proposal.domain, {}).get(surface.kind)
    if curated is not None:
        selected = frozenset(name for name in curated if name in available)
        if selected:
            return selected

    surface_words = _word_forms(
        " ".join((surface.kind, surface.name, surface.actor, surface.description))
    )
    matched = frozenset(
        entity.name
        for entity in entities
        if _word_forms(entity.name) & surface_words
    )
    # Ambiguous intent is not permission to fabricate a partition: preserve the complete validated model.
    return matched or frozenset(available)


def reach_of_new_entities(
    *,
    new_names: frozenset[str],
    entities: tuple[Entity, ...],
    surface_selected: frozenset[str],
) -> frozenset[str]:
    """Which entities added by an edit this surface should carry (R-563).

    Surfaces are scoped from a curated per-domain table, and `_relation_closure` follows relations
    *outward* from what a surface already holds. An entity introduced by an edit points **at** an
    existing entity rather than being pointed at, so neither mechanism reaches it: before this, an
    edit adding `LoyaltyPoint` put it in the database and in no app at all.

    The rule: a new entity reaches every surface that already holds something it points at. If it
    points at nothing any surface holds, it stands alone and reaches every surface.

    That fallback is not invented here — it is what this module already does when scoping is
    ambiguous ("Ambiguous intent is not permission to fabricate a partition"). It is also the
    recoverable direction: an entity shown on one app too many is a visible mistake a user can
    tell us about, while one hidden everywhere looks exactly like an edit that did nothing.
    """
    known = {entity.name for entity in entities}
    by_name = {entity.name: entity for entity in entities}
    reached: set[str] = set()
    for name in new_names:
        entity = by_name.get(name)
        if entity is None:
            continue
        points_at = {relation.target_entity for relation in entity.relations}
        if points_at & surface_selected:
            reached.add(name)
        elif not (points_at & known):
            # Related to nothing we know: a standalone addition, and hiding it would make the
            # edit look like it failed.
            reached.add(name)
    return frozenset(reached)


def _relation_closure(
    entities: tuple[Entity, ...],
    primary_names: frozenset[str],
) -> tuple[Entity, ...]:
    by_name = {entity.name: entity for entity in entities}
    retained = set(primary_names)
    pending = list(primary_names)
    while pending:
        entity = by_name[pending.pop()]
        for relation in entity.relations:
            if relation.target_entity in by_name and relation.target_entity not in retained:
                retained.add(relation.target_entity)
                pending.append(relation.target_entity)
    return tuple(entity for entity in entities if entity.name in retained)


def _writable_entity_names(
    proposal: ScopeProposal,
    surface: AppSurface,
    selected_names: frozenset[str],
) -> frozenset[str]:
    curated = CURATED_SURFACE_WRITABLE_ENTITIES.get(proposal.domain, {}).get(surface.kind)
    if curated is None:
        return selected_names
    return frozenset(name for name in curated if name in selected_names)


# ---------------------------------------------------------------------------
# Deterministic CRUD API / screen derivation (endpoints that wire to repositories)
# ---------------------------------------------------------------------------


def _derive_apis(
    entities: tuple[Entity, ...],
    *,
    writable_entities: frozenset[str],
    role_id: str,
) -> tuple[ApiEndpoint, ...]:
    by_name = {e.name: e for e in entities}
    apis: list[ApiEndpoint] = []
    for entity in entities:
        plural = _plural(_snake(entity.name))
        idp = f"{_lower_camel(entity.name)}Id"
        apis.append(ApiEndpoint(HttpMethod.GET, f"/{plural}", auth=False, response_schema=entity.name))
        apis.append(ApiEndpoint(HttpMethod.GET, f"/{plural}/{{{idp}}}", auth=False, response_schema=entity.name))
        if entity.name in writable_entities:
            required_roles = (role_id,)
            apis.append(
                ApiEndpoint(
                    HttpMethod.POST,
                    f"/{plural}",
                    auth=True,
                    request_schema=entity.name,
                    response_schema=entity.name,
                    required_roles=required_roles,
                )
            )
            apis.append(
                ApiEndpoint(
                    HttpMethod.PUT,
                    f"/{plural}/{{{idp}}}",
                    auth=True,
                    request_schema=entity.name,
                    response_schema=entity.name,
                    required_roles=required_roles,
                )
            )
            apis.append(
                ApiEndpoint(
                    HttpMethod.DELETE,
                    f"/{plural}/{{{idp}}}",
                    auth=True,
                    response_schema=entity.name,
                    required_roles=required_roles,
                )
            )
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


def _derive_screens(
    entities: tuple[Entity, ...],
    role_id: str,
    writable_entities: frozenset[str],
) -> tuple[Screen, ...]:
    screens: list[Screen] = []
    for entity in entities:
        base = _snake(entity.name)
        screens.append(Screen(f"{base}_list", role_id, components=("list",), actions=("open",)))
        if entity.name in writable_entities:
            screens.append(Screen(f"{base}_editor", role_id, components=("form",), actions=("save",)))
    return tuple(screens)


# ---------------------------------------------------------------------------
# Surface -> IR, plan, and build
# ---------------------------------------------------------------------------

_SYNONYM_MAP: dict[str, tuple[str, ...]] = {
    "article": ("post", "article"),
    "post": ("article", "post"),
}


def _primary_entity_names_for_pack(
    proposal: ScopeProposal,
    surface: AppSurface,
    entities: tuple[Entity, ...],
) -> frozenset[str]:
    available = {entity.name for entity in entities}
    # Admin gets all available entities
    if "admin" in surface.kind or surface.actor.lower() in ("admin", "super-admin"):
        return frozenset(available)

    curated = CURATED_SURFACE_ENTITIES.get(proposal.domain, {}).get(surface.kind)
    if curated is not None:
        selected: set[str] = set()
        for name in curated:
            if name in available:
                selected.add(name)
            else:
                for syn in _SYNONYM_MAP.get(name.lower(), ()):
                    for avail in available:
                        if avail.lower() == syn:
                            selected.add(avail)
        if selected:
            return frozenset(selected)

    return _primary_entity_names(proposal, surface, entities)


def _writable_entity_names_for_pack(
    proposal: ScopeProposal,
    surface: AppSurface,
    selected_names: frozenset[str],
) -> frozenset[str]:
    # Admin gets all selected entities as writable
    if "admin" in surface.kind or surface.actor.lower() in ("admin", "super-admin"):
        return selected_names

    curated = CURATED_SURFACE_WRITABLE_ENTITIES.get(proposal.domain, {}).get(surface.kind)
    if curated is None:
        return selected_names
    if len(curated) == 0:
        return frozenset()

    writable: set[str] = set()
    for name in curated:
        if name in selected_names:
            writable.add(name)
        else:
            for syn in _SYNONYM_MAP.get(name.lower(), ()):
                for sel in selected_names:
                    if sel.lower() == syn:
                        writable.add(sel)
    return frozenset(writable)


def synthesize_surface_ir(
    proposal: ScopeProposal,
    surface: AppSurface,
    pack_ir: ApplicationIR,
) -> ApplicationIR:
    """Build a validate_ir-clean ApplicationIR for a surface derived from a Solution Pack's data model."""
    source_entities = pack_ir.entities
    selected_names = _primary_entity_names_for_pack(proposal, surface, source_entities)
    writable_names = _writable_entity_names_for_pack(proposal, surface, selected_names)
    entities = _relation_closure(source_entities, selected_names)
    role_id = _role_id(surface.actor) or "user"
    roles = (_role_for_surface(role_id, entities, writable_names),)

    ir = ApplicationIR(
        name=surface.name,
        description=f"{surface.description} (part of the {proposal.domain} platform generated by OmniStackAI)",
        platforms=pack_ir.platforms,
        project_strategy=pack_ir.project_strategy,
        roles=roles,
        entities=entities,
        apis=_derive_apis(
            entities,
            writable_entities=writable_names,
            role_id=role_id,
        ),
        screens=_derive_screens(
            tuple(entity for entity in entities if entity.name in selected_names),
            role_id,
            writable_names,
        ),
        fixtures=pack_ir.fixtures,
    )
    ir = normalize_ir(ir)
    issues = validate_ir(ir)
    if has_errors(issues):
        detail = "; ".join(f"{i.location}: {i.message}" for i in issues if i.severity.name == "ERROR")
        raise ValueError(f"synthesize_surface_ir produced an invalid IR for '{surface.name}': {detail}")
    return ir


@dataclass(frozen=True)
class SurfaceApp:
    surface: AppSurface
    ir: ApplicationIR
    pack_result: SolutionPackApplicationResult | None = None
    is_synthesized: bool = False

    def to_dict(self) -> dict:
        writable_entities = sorted(
            {
                api.request_schema
                for api in self.ir.apis
                if api.method is not HttpMethod.GET and api.request_schema is not None
            }
        )
        payload = {
            "surface": self.surface.to_dict(),
            "app_name": self.ir.name,
            "slug": _slug(self.ir.name),
            "entities": [e.name for e in self.ir.entities],
            "writable_entities": writable_entities,
            "roles": [role.to_dict() for role in self.ir.roles],
            "api_count": len(self.ir.apis),
            "screen_count": len(self.ir.screens),
        }
        if self.pack_result is not None:
            payload["pack_result"] = self.pack_result.to_dict()
        if self.is_synthesized:
            payload["is_synthesized"] = True
        return payload


@dataclass(frozen=True)
class EcosystemPlan:
    prompt: str
    domain: str
    option_id: str
    apps: tuple[SurfaceApp, ...]
    pack_recommendation: SolutionPackRecommendation

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "domain": self.domain,
            "option_id": self.option_id,
            "apps": [a.to_dict() for a in self.apps],
            "solution_pack_recommendation": self.pack_recommendation.to_dict(),
        }


def _role_for_surface(
    role_id: str,
    entities: tuple[Entity, ...],
    writable_names: frozenset[str],
) -> Role:
    permissions: list[str] = []
    for entity in entities:
        resource = _snake(entity.name)
        permissions.append(f"{resource}:read")
        if entity.name in writable_names:
            permissions.append(f"{resource}:write")
    return Role(role_id, tuple(sorted(permissions)))


def surface_to_ir(
    proposal: ScopeProposal,
    surface: AppSurface,
    *,
    entities: tuple[Entity, ...] | None = None,
    added: frozenset[str] = frozenset(),
) -> ApplicationIR:
    """Build a validate_ir-clean ApplicationIR for one surface of the proposed ecosystem."""
    source_entities = entities or DOMAIN_ENTITIES.get(proposal.domain, DOMAIN_ENTITIES["custom-application"])
    selected_names = _primary_entity_names(proposal, surface, source_entities)
    if added:
        # R-563: entities an edit introduced. Curated scoping cannot know about them — it is a
        # fixed table of names written before the user asked — so their reach is decided by what
        # they point at.
        selected_names = selected_names | reach_of_new_entities(
            new_names=added, entities=source_entities, surface_selected=selected_names
        )
    writable_names = _writable_entity_names(proposal, surface, selected_names)
    entities = _relation_closure(source_entities, selected_names)
    role_id = _role_id(surface.actor) or "user"
    roles = (_role_for_surface(role_id, entities, writable_names),)
    # R-562: whether this surface is an app or a site, decided from the request rather than
    # assumed. Every surface used to be a Next.js web app, so "customer + driver apps" produced
    # four websites and said nothing about it.
    form = form_for_surface(
        kind=surface.kind, actor=surface.actor, name=surface.name, prompt=proposal.prompt
    )
    # A customer's app is built beside their website rather than in place of it (see
    # `app_replaces_web`); `plan_ecosystem` adds that companion. Here the web surface stays web.
    as_mobile = form.is_mobile and app_replaces_web(surface.audience)
    ir = ApplicationIR(
        name=surface.name,
        description=f"{surface.description} (part of the {proposal.domain} platform generated by OmniStackAI)",
        platforms=(Platform.WEB, Platform.BACKEND),
        project_strategy=ProjectStrategy(
            MobileProfile.REACT_NATIVE if as_mobile else MobileProfile.NONE,
            WebStrategy.NONE if as_mobile else WebStrategy.NEXTJS,
            AdminStrategy.NONE,
            BackendStrategy.PYTHON,
            DatabaseStrategy.POSTGRES,
            RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
        ),
        roles=roles,
        entities=entities,
        apis=_derive_apis(
            entities,
            writable_entities=writable_names,
            role_id=role_id,
        ),
        screens=_derive_screens(
            tuple(entity for entity in entities if entity.name in selected_names),
            role_id,
            writable_names,
        ),
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


def _mobile_companion(
    proposal: ScopeProposal,
    surface: AppSurface,
    entities: tuple[Entity, ...] | None,
    added: frozenset[str] = frozenset(),
) -> "SurfaceApp | None":
    """A customer's mobile app, built beside their website rather than instead of it (R-562).

    Returns None unless the request actually asked for an app for this audience. The companion
    carries the same scope as the web surface — it is the same product on a phone, not a different
    one — so it is generated from the same surface with a mobile strategy.
    """
    form = form_for_surface(
        kind=surface.kind, actor=surface.actor, name=surface.name, prompt=proposal.prompt
    )
    if not form.is_mobile or app_replaces_web(surface.audience):
        return None
    mobile_surface = replace(
        surface,
        kind=f"{surface.kind.replace('_web', '').replace('_pwa', '')}_app",
        name=f"{surface.name} (mobile)",
    )
    # Scoped from the *original* surface, not the renamed one. Entity scoping is keyed by surface
    # kind, so deriving from `customer_app` fell through to a word match and dropped MenuItem —
    # a food-delivery customer app that cannot show a menu. The app is the same product on a
    # different device and must see exactly what the website sees.
    ir = surface_to_ir(proposal, surface, entities=entities, added=added)
    ir = replace(
        ir,
        name=mobile_surface.name,
        project_strategy=replace(
            ir.project_strategy,
            mobile_profile=MobileProfile.REACT_NATIVE,
            web_strategy=WebStrategy.NONE,
        ),
    )
    return SurfaceApp(mobile_surface, ir)


def plan_ecosystem(
    proposal: ScopeProposal,
    option_id: str = "complete",
    *,
    entities: tuple[Entity, ...] | None = None,
    added: frozenset[str] = frozenset(),
    pack_result: SolutionPackApplicationResult | None = None,
    pack_manifest: SolutionPackManifest | None = None,
    pack_proposal: AIDeltaProposal | None = None,
    registry: SolutionPackRegistry = DEFAULT_SOLUTION_PACK_REGISTRY,
) -> EcosystemPlan:
    """Turn a ScopeProposal + build-scope option into an EcosystemPlan (one IR per selected surface)."""
    if pack_manifest is not None and pack_result is None:
        pack_result = apply_solution_pack_manifest(
            pack_manifest,
            proposal=pack_proposal,
            registry=registry,
        )

    if pack_result is not None:
        descriptor = registry.get(pack_result.pack_id)
        if descriptor is None or proposal.domain not in descriptor.domains:
            pack_domains = ", ".join(descriptor.domains) if descriptor else "unknown"
            raise SolutionPackError(
                f"Solution pack '{pack_result.pack_id}' for domain(s) '{pack_domains}' "
                f"does not match ecosystem domain '{proposal.domain}'"
            )

    surfaces = _surfaces_for_option(proposal, option_id)

    target_surface_index: int | None = None
    if pack_result is not None and surfaces:
        for idx, s in enumerate(surfaces):
            if s.kind in ("customer_web", "customer_pwa", "public_web"):
                target_surface_index = idx
                break
        if target_surface_index is None:
            target_surface_index = 0

    apps_list: list[SurfaceApp] = []
    for idx, surface in enumerate(surfaces):
        if idx == target_surface_index and pack_result is not None:
            apps_list.append(SurfaceApp(surface, pack_result.ir, pack_result=pack_result, is_synthesized=False))
        elif pack_result is not None:
            synthesized_ir = synthesize_surface_ir(proposal, surface, pack_result.ir)
            apps_list.append(SurfaceApp(surface, synthesized_ir, pack_result=None, is_synthesized=True))
        else:
            apps_list.append(
                SurfaceApp(surface, surface_to_ir(proposal, surface, entities=entities, added=added))
            )
            companion = _mobile_companion(proposal, surface, entities, added=added)
            if companion is not None:
                apps_list.append(companion)
    apps = tuple(apps_list)

    required_targets = tuple(
        sorted(
            {
                target.target
                for app in apps
                for target in build_project_plan(app.ir).apps
            }
        )
    )
    recommendation = registry.recommend(
        proposal.domain,
        required_targets=required_targets,
    )
    return EcosystemPlan(
        prompt=proposal.prompt,
        domain=proposal.domain,
        option_id=option_id,
        apps=apps,
        pack_recommendation=recommendation,
    )


def plan_ecosystem_from_prompt(
    prompt: str,
    option_id: str = "complete",
    *,
    entities: tuple[Entity, ...] | None = None,
    added: frozenset[str] = frozenset(),
) -> EcosystemPlan:
    """Convenience: classify the prompt (deterministically) and plan its ecosystem.

    `entities` and `added` (R-563) let an edit re-plan the same ecosystem over a changed data
    model: the proposal is derived from the prompt and is deterministic, so the surfaces come back
    identical and only their contents move.
    """
    return plan_ecosystem(propose_ecosystem(prompt), option_id, entities=entities, added=added)


@dataclass(frozen=True)
class EcosystemAppBuild:
    surface_kind: str
    app_name: str
    slug: str
    target_dir: str
    file_count: int
    commit_sha: str
    verify_targets: tuple[str, ...] = ()
    pack_id: str | None = None
    pack_version: str | None = None
    derived_ir_sha256: str | None = None
    applied_change_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d = {
            "surface_kind": self.surface_kind,
            "app_name": self.app_name,
            "slug": self.slug,
            "target_dir": self.target_dir,
            "file_count": self.file_count,
            "commit_sha": self.commit_sha,
            "verify_targets": list(self.verify_targets),
        }
        if self.pack_id is not None:
            d["pack_id"] = self.pack_id
            d["pack_version"] = self.pack_version
            d["derived_ir_sha256"] = self.derived_ir_sha256
            d["applied_change_ids"] = list(self.applied_change_ids)
        return d


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
        plans = verify_plans_for_ir(app.ir)
        verify_targets = tuple(sorted({p.target for p in plans}))
        pack_id = app.pack_result.pack_id if app.pack_result else None
        pack_version = app.pack_result.pack_version if app.pack_result else None
        derived_ir_sha256 = app.pack_result.derived_ir_sha256 if app.pack_result else None
        applied_change_ids = (
            app.pack_result.applied_configuration_change_ids + app.pack_result.applied_ai_delta_change_ids
            if app.pack_result else ()
        )
        builds.append(
            EcosystemAppBuild(
                surface_kind=app.surface.kind,
                app_name=app.ir.name,
                slug=unique_slug,
                target_dir=result.target_dir,
                file_count=result.file_count,
                commit_sha=result.commit_sha,
                verify_targets=verify_targets,
                pack_id=pack_id,
                pack_version=pack_version,
                derived_ir_sha256=derived_ir_sha256,
                applied_change_ids=applied_change_ids,
            )
        )
    return EcosystemBuildResult(
        prompt=plan.prompt,
        domain=plan.domain,
        option_id=plan.option_id,
        root_dir=root,
        apps=tuple(builds),
    )
