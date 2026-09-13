"""Ecosystem Scope Compiler — deterministic domain classification + multi-app scope proposal (R-430).

First brick of the differentiating spine (Master Architecture Spec, section 2 "Product Intelligence &
Ecosystem Scope Compiler"). Competitors turn "create a food delivery app" into a single customer screen;
OmniStackAI proposes the whole business ecosystem (customer app + merchant portal + driver portal + admin
dashboard) BEFORE expensive generation, asking at most 1-3 high-materiality questions.

This module is the DETERMINISTIC core: a curated keyword-heuristic classifier over a `DOMAIN_LIBRARY`, and
a `propose_ecosystem` that assembles a framework-neutral `ScopeProposal`. It has no model, network, clock,
or randomness, so it is pure (same prompt -> byte-identical proposal) and runs under `task verify`. Any
cheap-LLM refinement is a later, opt-in brick (mirroring `nl_to_ir.py` core vs `live_run.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Framework-neutral scope value objects
# ---------------------------------------------------------------------------

_CUSTOMER = "customer"
_OPERATOR = "operator"


@dataclass(frozen=True)
class Actor:
    """A human role that uses the ecosystem (Customer, Merchant, Driver, Admin, ...)."""

    name: str
    description: str

    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description}


@dataclass(frozen=True)
class AppSurface:
    """One application in the ecosystem (a customer web app, a merchant portal, an admin dashboard, ...).

    `audience` is "customer" (the end consumer) or "operator" (merchant/driver/staff/admin). It drives the
    "Customer Experience Only" build-scope option.
    """

    kind: str
    name: str
    audience: str
    actor: str
    description: str

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "audience": self.audience,
            "actor": self.actor,
            "description": self.description,
        }


@dataclass(frozen=True)
class ScopeOption:
    """A selectable build scope (Complete Business Platform / Customer Experience Only / Custom)."""

    id: str
    label: str
    description: str
    recommended: bool
    surfaces: tuple[AppSurface, ...]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "recommended": self.recommended,
            "surfaces": [s.to_dict() for s in self.surfaces],
        }


@dataclass(frozen=True)
class ScopeProposal:
    """The compiled ecosystem scope for a prompt."""

    prompt: str
    domain: str
    domain_confidence: float
    business_model: str
    actors: tuple[Actor, ...]
    surfaces: tuple[AppSurface, ...]
    options: tuple[ScopeOption, ...]
    questions: tuple[str, ...]
    matched_keywords: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "domain": self.domain,
            "domain_confidence": self.domain_confidence,
            "business_model": self.business_model,
            "actors": [a.to_dict() for a in self.actors],
            "surfaces": [s.to_dict() for s in self.surfaces],
            "options": [o.to_dict() for o in self.options],
            "questions": list(self.questions),
            "matched_keywords": list(self.matched_keywords),
        }


@dataclass(frozen=True)
class DomainMatch:
    """Result of deterministic domain classification."""

    domain: str
    score: int
    matched_keywords: tuple[str, ...]


# ---------------------------------------------------------------------------
# Curated domain library
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DomainSpec:
    domain: str
    business_model: str
    keywords: tuple[str, ...]
    surfaces: tuple[AppSurface, ...]
    questions: tuple[str, ...]
    example_prompt: str

    @property
    def actors(self) -> tuple[Actor, ...]:
        """Actors derived from the surfaces (deduped, order-preserving)."""
        seen: dict[str, Actor] = {}
        for surface in self.surfaces:
            seen.setdefault(surface.actor, Actor(surface.actor, f"{surface.actor} of the {self.domain} platform"))
        return tuple(seen.values())


def _s(kind: str, name: str, audience: str, actor: str, description: str) -> AppSurface:
    return AppSurface(kind=kind, name=name, audience=audience, actor=actor, description=description)


# Keyword weighting: a multi-word phrase is more specific than a single token, so it scores higher.
def _weight(keyword: str) -> int:
    return 3 if " " in keyword else 1


DOMAIN_LIBRARY: tuple[DomainSpec, ...] = (
    DomainSpec(
        domain="food-delivery",
        business_model="Two-sided delivery marketplace (customers, merchants) with a courier fleet",
        keywords=(
            "food delivery",
            "deliver food",
            "order food",
            "restaurant",
            "restaurants",
            "courier",
            "couriers",
            "takeaway",
            "menu",
        ),
        surfaces=(
            _s("customer_web", "Customer Ordering App", _CUSTOMER, "Customer", "Browse restaurants, build a cart, checkout, and track the order."),
            _s("merchant_portal", "Merchant Portal", _OPERATOR, "Merchant", "Manage the menu, availability, and the order lifecycle."),
            _s("driver_portal", "Courier Dispatch App", _OPERATOR, "Driver", "Accept assignments and update delivery status."),
            _s("admin_dashboard", "Super-Admin Dashboard", _OPERATOR, "Admin", "Platform operations, commissions, disputes, and analytics."),
        ),
        questions=(
            "Should couriers be your own fleet, or third-party/self-managed drivers?",
            "Do merchants need self-service menu management, or will an admin manage menus?",
        ),
        example_prompt="Create a food delivery app where customers order from restaurants and couriers deliver",
    ),
    DomainSpec(
        domain="rideshare",
        business_model="On-demand transportation marketplace matching riders and drivers",
        keywords=(
            "rideshare",
            "ride sharing",
            "ride hailing",
            "ride-hailing",
            "taxi",
            "rider",
            "riders",
            "driver",
            "drivers",
            "trip",
            "trips",
            "passenger",
        ),
        surfaces=(
            _s("customer_pwa", "Rider App", _CUSTOMER, "Rider", "Request a ride, see the driver en route, and pay."),
            _s("driver_portal", "Driver App", _OPERATOR, "Driver", "Go online, accept trips, and navigate/complete rides."),
            _s("admin_dashboard", "Operations Dashboard", _OPERATOR, "Admin", "Dispatch oversight, pricing, safety, and analytics."),
        ),
        questions=(
            "Is pricing fixed, distance-based, or surge/dynamic?",
            "Do you need live map tracking in the first build?",
        ),
        example_prompt="A rideshare app connecting riders with drivers for on-demand trips",
    ),
    DomainSpec(
        domain="marketplace",
        business_model="Multi-vendor marketplace connecting buyers and independent sellers",
        keywords=(
            "marketplace",
            "multi-vendor",
            "multi vendor",
            "buyers",
            "sellers",
            "vendors",
            "listings",
        ),
        surfaces=(
            _s("customer_web", "Buyer Storefront", _CUSTOMER, "Buyer", "Discover listings, purchase, and review sellers."),
            _s("seller_portal", "Seller Portal", _OPERATOR, "Seller", "Create listings, manage inventory, and fulfil orders."),
            _s("admin_dashboard", "Marketplace Admin", _OPERATOR, "Admin", "Onboard sellers, moderate listings, and manage payouts."),
        ),
        questions=(
            "Should sellers self-onboard, or be approved by an admin first?",
            "Does the platform take a commission on each sale?",
        ),
        example_prompt="A multi-vendor marketplace where sellers post listings and buyers purchase",
    ),
    DomainSpec(
        domain="e-commerce",
        business_model="Single-brand online store selling products directly to shoppers",
        keywords=(
            "e-commerce",
            "ecommerce",
            "online store",
            "storefront",
            "shopping cart",
            "products",
            "checkout",
            "catalog",
        ),
        surfaces=(
            _s("customer_web", "Storefront", _CUSTOMER, "Shopper", "Browse the catalog, add to cart, and check out."),
            _s("admin_dashboard", "Store Admin", _OPERATOR, "Admin", "Manage products, inventory, orders, and fulfilment."),
        ),
        questions=(
            "Do you need digital products, physical shipping, or both?",
        ),
        example_prompt="An online store with a product catalog, shopping cart and checkout",
    ),
    DomainSpec(
        domain="b2b-saas",
        business_model="Subscription B2B SaaS with team workspaces and role-based access",
        keywords=(
            "saas",
            "b2b",
            "workspace",
            "workspaces",
            "subscription",
            "tenant",
            "multi-tenant",
            "team dashboard",
        ),
        surfaces=(
            _s("customer_web", "Product Web App", _CUSTOMER, "User", "The core product used by a customer's team members."),
            _s("admin_dashboard", "Platform Admin", _OPERATOR, "Admin", "Tenant management, billing, and usage analytics."),
        ),
        questions=(
            "Is billing per-seat, usage-based, or flat subscription?",
            "Do customer organizations manage their own users/roles?",
        ),
        example_prompt="A multi-tenant B2B SaaS workspace with subscription billing for teams",
    ),
    DomainSpec(
        domain="healthcare-clinic",
        business_model="Clinic operations connecting patients, clinicians, and administration",
        keywords=(
            "clinic",
            "patient",
            "patients",
            "doctor",
            "doctors",
            "clinician",
            "healthcare",
            "medical",
            "telehealth",
        ),
        surfaces=(
            _s("customer_web", "Patient Portal", _CUSTOMER, "Patient", "Book appointments, view records, and message the clinic."),
            _s("provider_portal", "Clinician Console", _OPERATOR, "Clinician", "Manage the schedule, consultations, and patient notes."),
            _s("admin_dashboard", "Clinic Admin", _OPERATOR, "Admin", "Staff, billing, compliance, and reporting."),
        ),
        questions=(
            "Does the first build need video/telehealth consultations?",
            "Are there compliance requirements (e.g. HIPAA/records handling) to design for now?",
        ),
        example_prompt="A healthcare clinic app for patients to book doctors, with a clinician console",
    ),
    DomainSpec(
        domain="booking",
        business_model="Appointment/reservation platform connecting customers and service providers",
        keywords=(
            "booking",
            "bookings",
            "reservation",
            "reservations",
            "appointment",
            "appointments",
            "scheduling",
            "book a",
        ),
        surfaces=(
            _s("customer_web", "Booking App", _CUSTOMER, "Customer", "Find availability, book, reschedule, and pay."),
            _s("provider_portal", "Provider Portal", _OPERATOR, "Provider", "Manage services, availability, and confirmed bookings."),
            _s("admin_dashboard", "Admin Dashboard", _OPERATOR, "Admin", "Providers, policies, payments, and analytics."),
        ),
        questions=(
            "Should customers pay/deposit at booking time?",
            "Do providers self-manage their availability?",
        ),
        example_prompt="A booking app where customers reserve appointments with service providers",
    ),
    DomainSpec(
        domain="learning",
        business_model="Learning platform (LMS) connecting students and instructors",
        keywords=(
            "lms",
            "course",
            "courses",
            "learning platform",
            "students",
            "instructor",
            "instructors",
            "lessons",
            "curriculum",
        ),
        surfaces=(
            _s("customer_web", "Student App", _CUSTOMER, "Student", "Enroll, take lessons, submit work, and track progress."),
            _s("provider_portal", "Instructor Studio", _OPERATOR, "Instructor", "Author courses, grade work, and view learner analytics."),
            _s("admin_dashboard", "Admin Dashboard", _OPERATOR, "Admin", "Catalog, enrolments, and platform reporting."),
        ),
        questions=(
            "Are courses self-paced, cohort-based, or live?",
            "Is content free, paid per-course, or subscription?",
        ),
        example_prompt="A learning platform (LMS) where instructors publish courses and students take lessons",
    ),
    DomainSpec(
        domain="social",
        business_model="Community/social network with a feed, membership, and moderation",
        keywords=(
            "social network",
            "social app",
            "community",
            "feed",
            "followers",
            "following",
            "timeline",
            "friends",
        ),
        surfaces=(
            _s("customer_web", "Member App", _CUSTOMER, "Member", "Post to the feed, follow others, and interact."),
            _s("admin_dashboard", "Moderation Console", _OPERATOR, "Admin", "Members, reported content moderation, and analytics."),
        ),
        questions=(
            "Is the feed public, followers-only, or group-based?",
            "Do you need content moderation tools in the first build?",
        ),
        example_prompt="A social network app with a feed, followers and a community of members",
    ),
    DomainSpec(
        domain="blog-cms",
        business_model="Content platform where authors publish and readers consume",
        keywords=(
            "blog",
            "cms",
            "content management",
            "articles",
            "author",
            "authors",
            "publishing",
            "newsletter",
        ),
        surfaces=(
            _s("public_web", "Public Site", _CUSTOMER, "Reader", "Read published articles and subscribe."),
            _s("provider_portal", "Author Studio", _OPERATOR, "Author", "Draft, edit, and publish content."),
            _s("admin_dashboard", "CMS Admin", _OPERATOR, "Admin", "Authors, taxonomy, and site settings."),
        ),
        questions=(
            "Do multiple authors need an editorial/review workflow?",
        ),
        example_prompt="A blog CMS where authors publish articles and readers subscribe",
    ),
)

_MIN_SCORE = 1
_CONFIDENCE_NORM = 6.0  # score at/above which confidence saturates to 1.0


# ---------------------------------------------------------------------------
# Classification + proposal
# ---------------------------------------------------------------------------


def classify_domain(prompt: str) -> Optional[DomainMatch]:
    """Deterministically classify a prompt to a domain via weighted keyword scoring.

    Case-insensitive; a multi-word keyword scores higher than a single token. The highest-scoring
    domain at or above the threshold wins; ties are broken by `DOMAIN_LIBRARY` order (stable). Returns
    ``None`` when nothing matches.
    """
    text = " ".join((prompt or "").lower().split())
    best: Optional[DomainMatch] = None
    for spec in DOMAIN_LIBRARY:
        score = 0
        matched: list[str] = []
        for keyword in spec.keywords:
            if keyword in text:
                score += _weight(keyword)
                matched.append(keyword)
        if score >= _MIN_SCORE and (best is None or score > best.score):
            best = DomainMatch(domain=spec.domain, score=score, matched_keywords=tuple(matched))
    return best


def _spec_for(domain: str) -> Optional[DomainSpec]:
    for spec in DOMAIN_LIBRARY:
        if spec.domain == domain:
            return spec
    return None


_FALLBACK_SURFACES: tuple[AppSurface, ...] = (
    _s("customer_web", "Web App", _CUSTOMER, "User", "The primary user-facing web application."),
    _s("admin_dashboard", "Admin Dashboard", _OPERATOR, "Admin", "Manage content, users, and settings."),
)


def _build_options(surfaces: tuple[AppSurface, ...]) -> tuple[ScopeOption, ...]:
    customer_surfaces = tuple(s for s in surfaces if s.audience == _CUSTOMER)
    options = [
        ScopeOption(
            id="complete",
            label="Complete Business Platform",
            description="Every app in the ecosystem: " + ", ".join(s.name for s in surfaces) + ".",
            recommended=True,
            surfaces=surfaces,
        )
    ]
    # Only offer "Customer Experience Only" when it is a strict, non-empty subset.
    if customer_surfaces and len(customer_surfaces) < len(surfaces):
        options.append(
            ScopeOption(
                id="customer-only",
                label="Customer Experience Only",
                description="Just the customer-facing app(s): " + ", ".join(s.name for s in customer_surfaces) + ".",
                recommended=False,
                surfaces=customer_surfaces,
            )
        )
    options.append(
        ScopeOption(
            id="custom",
            label="Custom / Multi-Surface Configuration",
            description="Start from all surfaces and toggle which apps to build.",
            recommended=False,
            surfaces=surfaces,
        )
    )
    return tuple(options)


def propose_ecosystem(prompt: str) -> ScopeProposal:
    """Compile a prompt into a framework-neutral `ScopeProposal` (deterministic, no model/network)."""
    match = classify_domain(prompt)
    if match is not None:
        spec = _spec_for(match.domain)
    else:
        spec = None

    if spec is not None and match is not None:
        surfaces = spec.surfaces
        confidence = round(min(1.0, match.score / _CONFIDENCE_NORM), 2)
        return ScopeProposal(
            prompt=prompt,
            domain=spec.domain,
            domain_confidence=confidence,
            business_model=spec.business_model,
            actors=spec.actors,
            surfaces=surfaces,
            options=_build_options(surfaces),
            questions=spec.questions,
            matched_keywords=match.matched_keywords,
        )

    # No domain matched: a usable single-app custom scope.
    surfaces = _FALLBACK_SURFACES
    actors = tuple(
        Actor(s.actor, f"{s.actor} of the application") for s in surfaces
    )
    return ScopeProposal(
        prompt=prompt,
        domain="custom-application",
        domain_confidence=0.0,
        business_model="Custom application (no known domain detected)",
        actors=actors,
        surfaces=surfaces,
        options=_build_options(surfaces),
        questions=("What are the main user roles, and does this need an admin dashboard?",),
        matched_keywords=(),
    )
