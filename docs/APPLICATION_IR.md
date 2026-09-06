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

## Scope

v1 covers the Brief §9 minimum model. Flows, integrations, architecture rules, repo modules, and the
build matrix are extension points for later Tracker IDs. Code generation is a separate concern: the
framework adapter contract and the first adapter (Next.js) consume this IR in following tasks.
