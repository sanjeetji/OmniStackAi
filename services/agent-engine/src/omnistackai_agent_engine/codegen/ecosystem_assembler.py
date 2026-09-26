"""Assemble a planned ecosystem into one monorepo over one API and one database (R-554).

`plan_ecosystem_from_prompt` has long planned four role-scoped surfaces for a food-delivery
prompt — a customer ordering app, a merchant portal, a courier dispatch app and a super-admin
dashboard, each with its own entity scope and its own role. `intake.build_ecosystem` then
materialises each one as **its own separate Git repo with its own backend and its own database**.
That is four disconnected apps rather than an ecosystem: the courier's app cannot see the
customer's order, which is the entire point of the thing.

This assembles the same plan the way the hand-built templates are built: every surface under
`apps/<id>/`, over one `services/api`, one database and one OpenAPI contract.

The backend is generated from the **union** of every surface's IR. That is what makes the thing
hold together — a courier app calling `GET /orders` needs the route to exist even though the
courier's own IR is a subset. Each app is still generated from its own scoped IR, so the courier
app ships no menu editor; only the server knows everything.

`build_ecosystem` is left exactly as it is. Separate repos are a legitimate shape for someone who
wants four independent products; this is the shape for someone who wants one.
"""

from __future__ import annotations

from dataclasses import replace

from ..application_ir import (
    AdminStrategy,
    ApiEndpoint,
    ApplicationIR,
    Entity,
    MobileProfile,
    Role,
    WebStrategy,
)
from .assembler import _prefixed, _slug
from .brand_project import brand_files
from .files import GeneratedFile, GeneratedProject
from .nextjs import NextjsAdminAdapter, NextjsWebAdapter
from .react_native import ReactNativeAdapter
from .openapi import render_openapi_json

#: Where each planned surface lands. `web` and `admin` are deliberate: R-553's runner gives them
#: their established ids, ports and base paths, and the console renders them specially, so the
#: customer-facing app and the admin dashboard keep the names everything already understands.
SURFACE_DIRECTORIES: dict[str, str] = {
    "customer_web": "web",
    "customer_pwa": "web",
    "public_web": "web",
    "admin_dashboard": "admin",
    "merchant_portal": "merchant",
    "provider_portal": "provider",
    "driver_portal": "driver",
    "operations_console": "ops",
}


def surface_directory(kind: str, taken: set[str]) -> str:
    """The app directory for a surface kind, unique within the project."""
    base = SURFACE_DIRECTORIES.get(kind) or _slug(kind).replace("_", "-") or "app"
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def _merge_entities(irs: list[ApplicationIR]) -> tuple[Entity, ...]:
    """Every entity any surface knows about, each with the superset of its fields.

    Superset rather than first-wins: surfaces scope entities, and one of them holding a column the
    others do not is exactly the case this has to survive. A backend missing a column silently
    breaks whichever surface needed it.
    """
    merged: dict[str, Entity] = {}
    for ir in irs:
        for entity in ir.entities:
            existing = merged.get(entity.name)
            if existing is None:
                merged[entity.name] = entity
                continue
            known = {field.name for field in existing.fields}
            extra = tuple(field for field in entity.fields if field.name not in known)
            if extra:
                merged[entity.name] = replace(existing, fields=existing.fields + extra)
    return tuple(merged[name] for name in sorted(merged))


def _merge_roles(irs: list[ApplicationIR]) -> tuple[Role, ...]:
    """Every role in the ecosystem. Each surface declares only its own, and the server needs all."""
    merged: dict[str, Role] = {}
    for ir in irs:
        for role in ir.roles:
            merged.setdefault(role.id, role)
    return tuple(merged[key] for key in sorted(merged))


def _merge_apis(irs: list[ApplicationIR]) -> tuple[ApiEndpoint, ...]:
    """Every endpoint any surface calls, with the union of the roles allowed to call it.

    Union of roles, not the first one seen: `GET /orders` reached by both a customer and a courier
    must admit both, or one of them gets a 403 against a route its own IR promised it.
    """
    merged: dict[tuple[str, str], ApiEndpoint] = {}
    for ir in irs:
        for api in ir.apis:
            key = (api.method.value, api.path)
            existing = merged.get(key)
            if existing is None:
                merged[key] = api
                continue
            roles = tuple(sorted(set(existing.required_roles) | set(api.required_roles)))
            merged[key] = replace(
                existing,
                required_roles=roles,
                # An endpoint any surface can reach unauthenticated is public; the stricter
                # surface's own guard still applies in its own app.
                auth=existing.auth and api.auth,
            )
    return tuple(merged[key] for key in sorted(merged))


def union_ir(plan) -> ApplicationIR:
    """The IR the shared backend is generated from: everything every surface needs.

    Screens are deliberately dropped — they belong to the app that renders them, and a backend has
    no use for them. Keeping them would only invite a surface's pages to be generated twice.
    """
    irs = [app.ir for app in plan.apps]
    if not irs:
        raise ValueError("an ecosystem plan must contain at least one surface")
    base = irs[0]
    return replace(
        base,
        name=base.name,
        entities=_merge_entities(irs),
        roles=_merge_roles(irs),
        apis=_merge_apis(irs),
        screens=(),
        project_strategy=replace(
            base.project_strategy,
            # The backend only: each surface's UI is generated from its own IR, below.
            web_strategy=WebStrategy.NONE,
            admin_strategy=AdminStrategy.NONE,
        ),
    )


def assemble_ecosystem(plan, *, provider=None, prompt: str = "") -> GeneratedProject:
    """One monorepo: every surface under `apps/<id>/`, over one `services/api` and one database."""
    from .assembler import assemble_project  # local import: assembler imports this module's siblings

    if not plan.apps:
        raise ValueError("an ecosystem plan must contain at least one surface")

    shared = union_ir(plan)
    files: list[GeneratedFile] = []

    # The backend, generated from the union so every surface's calls resolve against it.
    backend = assemble_project(shared, prompt=prompt)
    files += [f for f in backend.files() if f.path.startswith("services/api/")]

    taken: set[str] = set()
    app_dirs: list[tuple[str, str]] = []
    for app in plan.apps:
        directory = surface_directory(app.surface.kind, taken)
        taken.add(directory)
        app_dirs.append((directory, app.ir.name))
        # R-562: a surface the planner marked mobile is built as a React Native app. Before this
        # every surface took a Next.js adapter, so a prompt asking for a driver app produced a
        # driver *website* — the request answered with something else, silently.
        if app.ir.project_strategy.mobile_profile is MobileProfile.REACT_NATIVE:
            adapter = ReactNativeAdapter()
        elif directory == "admin":
            # The admin dashboard gets the console flavour — a dashboard home rather than a
            # landing page — which is the same distinction R-541 drew for a single project.
            adapter = NextjsAdminAdapter()
        else:
            adapter = NextjsWebAdapter()
        generated = (
            adapter.generate(app.ir, provider=provider, prompt=prompt)
            if provider is not None and not isinstance(adapter, ReactNativeAdapter)
            else adapter.generate(app.ir)
        )
        files += _prefixed(generated, f"apps/{directory}")

    # One brand, one contract, one README for the whole ecosystem.
    files += brand_files(shared, _slug(shared.name))
    if shared.apis:
        files.append(GeneratedFile("contracts/openapi.json", render_openapi_json(shared)))
    files.append(GeneratedFile("README.md", _ecosystem_readme(plan, shared, app_dirs)))
    files.append(
        GeneratedFile(".gitignore", "node_modules/\n.next/\n.venv\n__pycache__/\nbin/\n.env\n")
    )
    return GeneratedProject("customer-monorepo", tuple(files))


def _ecosystem_readme(plan, shared: ApplicationIR, app_dirs: list[tuple[str, str]]) -> str:
    lines = [
        f"# {shared.name}",
        "",
        f"{shared.description}",
        "",
        "One product, several apps. Every app here talks to the same API and the same database, so",
        "an order placed in one is visible in the others.",
        "",
        "## Apps",
        "",
        "| Directory | App | Built as | Role |",
        "| --- | --- | --- | --- |",
    ]
    for (directory, name), app in zip(app_dirs, plan.apps):
        roles = ", ".join(role.id for role in app.ir.roles) or "-"
        # R-562: say which of these is a phone app and which is a website. A user who asked for
        # "customer + driver apps" should be able to see that they got them, without opening four
        # directories to find out.
        built = (
            "React Native app"
            if app.ir.project_strategy.mobile_profile is MobileProfile.REACT_NATIVE
            else "web app"
        )
        lines.append(f"| `apps/{directory}` | {name} | {built} | {roles} |")
    lines += [
        "| `services/api` | Shared API | backend | serves every app above |",
        "",
        "## Why one API",
        "",
        "Each app is generated from its own scoped view of the domain — the courier's app has no",
        "menu editor, because a courier never edits a menu. The **server** knows everything: its",
        "schema is the union of what every app needs, so a route one app calls always exists, and",
        "a role allowed to call it in one app is allowed in the server too.",
        "",
        "## Running it",
        "",
        "The platform's preview starts every app above on its own port against one database. To run",
        "it yourself, start `services/api` first, then each app in `apps/`.",
        "",
        "## Branding",
        "",
        "`brand.json` at this root is the one place the name, colour, font and corner style are",
        "defined; every app derives from it. See `brand/README.md`.",
        "",
    ]
    return "\n".join(lines)
