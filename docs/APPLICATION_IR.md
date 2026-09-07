# Application IR (Brief §9)

The Application IR is the **framework-neutral source of truth** between user intent and generated
targets. It is pure, validated data — no network, no framework knowledge, no code generation — and it
is what every codegen framework adapter (Next.js, Go/Python, Flutter, React Native, native) will
consume.

Package: `omnistackai_agent_engine.application_ir` (Python 3.13 standard library only).

## Model (v1)

- `ApplicationIR` — `name`, `description`, `platforms` (`mobile`/`web`/`admin`/`backend`),
  `project_strategy`, `roles`, `entities`, `apis`, `screens`, `acceptance_criteria`, `schema_version`.
- `ProjectStrategy` — mobile/web/admin/backend/database/repo strategy enums.
- `Entity` — `name`, `fields` (`Field`: name, type, required, validation), `relations`
  (`Relation`: name, target entity, kind).
- `ApiEndpoint` — method, path, auth, request/response/error schema references.
- `Role`, `Screen`, `AcceptanceCriterion`.

## Guarantees

- **Immutable + validated on construction.** Identifiers are bounded and well-formed; enums are
  checked; entity/field/role/screen ids and `method+path` are unique.
- **Cross-validated.** A relation must target a declared entity; a screen's role must reference a
  declared role. Violations raise `InvalidIRError` (stable `code = "invalid_ir"`).
- **Versioned + round-trippable.** `to_dict()` emits plain JSON-friendly values; `from_dict()`
  reconstructs and rejects an unknown/newer `schema_version` with `UnsupportedIRVersionError`
  (`IR_SCHEMA_VERSION = 1`). `to_dict → from_dict → to_dict` is lossless.

## Example

```python
from omnistackai_agent_engine.application_ir import (
    ApplicationIR, Platform, ProjectStrategy, Entity, Field, FieldType, ApiEndpoint, HttpMethod,
    MobileProfile, WebStrategy, AdminStrategy, BackendStrategy, DatabaseStrategy, RepoStrategy,
)

ir = ApplicationIR(
    name="Rideshare Favourites",
    description="Customers can favourite drivers.",
    platforms=(Platform.WEB, Platform.BACKEND),
    project_strategy=ProjectStrategy(
        MobileProfile.NONE, WebStrategy.NEXTJS, AdminStrategy.NONE,
        BackendStrategy.GO, DatabaseStrategy.POSTGRES, RepoStrategy.CUSTOMER_PROJECT_MONOREPO,
    ),
    entities=(Entity("Driver", (Field("id", FieldType.UUID), Field("name", FieldType.STRING))),),
    apis=(ApiEndpoint(HttpMethod.GET, "/drivers", auth=True, response_schema="Driver"),),
)
doc = ir.to_dict()            # JSON/YAML-friendly
ApplicationIR.from_dict(doc)  # validated round-trip
```

## Validation, normalization, and examples (R-231)

Beyond per-record construction validation, the package adds cross-cutting helpers:

- `validate_ir(ir) -> tuple[Issue, ...]` — semantic checks that are integrity- or advisory-level:
  an API `request/response/error_schema` that references an **undeclared entity** is an `error`
  (`unknown_schema_reference`); a web/admin/mobile strategy set without its platform (or a platform
  listed without its strategy) is a `warning` (`platform_strategy_mismatch`). Each `Issue` has a
  `severity` (`error`/`warning`), stable `code`, `message`, and `location`. `has_errors(issues)` is a
  convenience. A clean IR yields no errors. The validator never weakens the hard construction checks.
- `normalize_ir(ir) -> ApplicationIR` — a canonical form: platforms in enum order; roles, entities,
  apis, screens, and acceptance criteria sorted by a stable key (entity **field order preserved**).
  Idempotent and lossless through `to_dict` — useful for stable diffs and reproducible output.
- `example_ir(name)` / `EXAMPLES` — realistic, construction-valid sample IRs (`rideshare-favourites`,
  `minimal-blog`) that pass `validate_ir` with no errors and generate via all three adapters.

## Scope

v1 covers the Brief §9 minimum model. Flows, integrations, architecture rules, repo modules, and the
build matrix are extension points for later Tracker IDs. Code generation is a separate concern: the
framework adapter contract and the Next.js / FastAPI / Go adapters consume this IR.
