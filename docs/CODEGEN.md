# Code generation boundary (Brief §16/§17/§46/§75)

Code generation turns an **Application IR** into a customer project's source. The boundary is pure and
deterministic: adapters produce an in-memory file-set; nothing is written to disk or executed here (a
later Git-service task materializes it).

Package: `omnistackai_agent_engine.codegen` (standard library only; depends on `application_ir`).

## Pieces

- **`GeneratedFile`** — one `path` → `content` record. The path is validated as a safe relative POSIX
  path: no absolute paths, no `..` traversal, no backslashes or control characters, bounded length,
  each segment `[A-Za-z0-9._-]`. Optional `executable` flag. Content is a bounded string.
- **`GeneratedProject`** — an immutable, **deterministically ordered** (sorted by path) set of
  `GeneratedFile`s for one `target`. Duplicate paths raise `DuplicateFileError`. Exposes `get`,
  `paths`, `files`, `__len__`, and `merge` (same target only).
- **`FrameworkAdapter`** — the runtime-checkable contract every generator implements:
  `target: GenerationTarget` and `generate(ir) -> GeneratedProject`.
- **`AdapterRegistry`** — registers adapters by target; product/agent code selects an adapter only via
  the registry (`get(target)`), never a concrete class. Stable `DuplicateAdapterError` /
  `UnsupportedTargetError`.
- **`GenerationTarget`** — bounded enum: `nextjs-web`, `nextjs-admin`, `backend-go`, `backend-python`,
  `backend-node`, `flutter`, `react-native`, `native-android`, `native-ios`.

## Why in-memory and deterministic

Generation is a pure function `IR → GeneratedProject`, so it is fully unit-testable offline by
asserting emitted file paths and contents — no install, no build, no disk. This keeps generation
reproducible and diffable before anything is written to a customer repo (R-228).

## First adapter: Next.js web (R-227)

`NextjsWebAdapter` (target `nextjs-web`) turns an Application IR into a real Next.js App Router
TypeScript project:

- **Config:** `package.json` (next/react), `tsconfig.json`, `next.config.mjs` with security headers,
  `.gitignore`, `.env.example` (placeholders only), `README.md`.
- **Types:** each IR entity → a TypeScript interface in `lib/types.ts` (field-type mapping;
  non-required fields become optional; relations become typed references, `[]` for to-many).
- **APIs:** each IR API → an App Router `route.ts` handler, grouped one file per route directory, with
  `{param}` mapped to Next's `[param]` dynamic segment and one exported `GET/POST/...` per method
  (scaffolded to a `501 not_implemented` response for now).
- **Screens:** each IR screen → an `app/<id>/page.tsx`; `app/page.tsx` is an overview of the app,
  entities, and screens.

The file-path validator (`GeneratedFile`) allows framework route filename characters (`[]()@+`) so
Next.js/Expo route conventions are valid, while still rejecting absolute paths, `..`, backslashes, and
control characters. The generated project is what a Next.js toolchain would install and build; this
platform verifies it offline by asserting the emitted files (no install/build here).

## Second adapter: Python backend (R-229)

`PythonBackendAdapter` (target `backend-python`) turns an Application IR into a real FastAPI backend:

- **Models:** each entity → a Pydantic model in `app/models.py` (types mapped; non-required fields
  become `Optional[...] = None`).
- **Routes:** IR APIs → FastAPI routes grouped into `app/routers/<segment>.py` by first path segment;
  `{param}` path params become typed function arguments; scaffold bodies raise `501 not_implemented`.
- **App:** `app/main.py` includes each router and a `/healthz` endpoint; plus `app/config.py`,
  `requirements.txt`, `README.md`, `.gitignore`, `.env.example` (placeholders only).

## Third adapter: Go backend (R-230)

`GoBackendAdapter` (target `backend-go`) turns an Application IR into a real Go standard-library
`net/http` service (no third-party deps):

- **Models:** each entity → a Go struct in `internal/models/models.go` (types mapped; exported fields
  with `json` tags; non-required fields become pointers with `,omitempty`).
- **Routes:** IR APIs → Go 1.22 method+pattern registrations in `main.go`
  (`mux.HandleFunc("POST /favourites/drivers/{driverId}", handlers.PostFavouritesDriversDriverId)`);
  handlers grouped into `internal/handlers/<segment>.go`, returning `501 not implemented`, with path
  params available via `r.PathValue(...)`.
- **App:** `main.go` registers each route + a `GET /healthz` and serves on a configurable addr; plus
  `go.mod` (`go 1.22`), `README.md`, `.gitignore`, `.env.example` (placeholders only).

With R-227 (Next.js web), R-229 (FastAPI) and R-230 (Go) registered together, **one Application IR
emits web + Python + Go from a single source of truth** — the multi-target differentiator across
languages. All three are pure/offline: verified by asserting emitted files; the Git service (R-228)
materializes any of them into a customer-owned repo.

## Customer project assembler (R-232)

`assemble_project(ir, registry=None)` turns one IR into a **complete customer monorepo** (Brief
§6/§34/§35): it selects the adapters implied by `project_strategy` (`web_strategy == nextjs` →
`apps/web`; `backend_strategy` go/python → `services/api`), generates each, re-paths its files under
the monorepo layout, and returns a single `GeneratedProject` (target `customer-monorepo`) with a root
`README.md` (listing the assembled apps and anything not yet assembled — node backend, admin, mobile)
and a root `.gitignore`. `default_registry()` provides an `AdapterRegistry` pre-loaded with all three
adapters.

End to end, **one Application IR becomes one customer-owned monorepo repository**: `assemble_project`
→ `git_service.create_repository` produces, e.g., a 24-file repo with `apps/web/` (Next.js) and
`services/api/` (Go) and a single commit authored by the customer. Pure/offline; nothing is installed,
built, run, or written to disk except by the Git service into the caller's target directory.

## PostgreSQL schema / migration (R-238)

`render_postgres_schema(ir)` (in `codegen/schema_sql.py`) turns the IR entities + relations into a
deterministic SQL DDL migration — the generated backend's persistence layer:

- **Tables:** one `CREATE TABLE` per entity, snake_cased table name (`FavouriteDriver` → `favourite_driver`).
- **Columns:** each field → a column typed from `FieldType` (STRING/TEXT→`TEXT`, INT→`BIGINT`,
  FLOAT→`DOUBLE PRECISION`, BOOL→`BOOLEAN`, DATETIME→`TIMESTAMPTZ`, UUID→`UUID`, JSON→`JSONB`); required
  fields get `NOT NULL`.
- **Primary key:** the entity's own `id` field if it declares one (UUID gets `DEFAULT gen_random_uuid()`),
  else a prepended surrogate `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- **Foreign keys:** `many_to_one`/`one_to_one` relations → a `<name>_id UUID REFERENCES <target>(id)`
  column; `many_to_many` → one deterministic join table with a composite primary key.
- **Uniqueness & indexes (R-249):** a `Field` with `unique=True` (never the `id` PK) renders a `UNIQUE`
  column constraint; each `Entity.indexes` entry renders one `CREATE [UNIQUE] INDEX <name> ON <table>
  (<cols>);` after the tables, with a deterministic default name (`<table>_<cols>_idx`, or `_key` when
  unique) when the index is unnamed.
- **Field validation (R-250/R-251/R-252):** `Field.validation` rules (`codegen/field_validation.py`)
  flow into all three model/schema targets. Schema: a STRING with `max_length:n` → `VARCHAR(n)`, an
  `enum:a|b|c` → `CHECK (col IN ('a','b','c'))`, and numeric `min:n`/`max:n` → `CHECK (col >= n)`/
  `CHECK (col <= n)`. FastAPI Pydantic: `Field(max_length=n, ge=…, le=…)` and a `Literal[...]` type —
  Pydantic enforces these at request time automatically. Go models: a go-playground
  `validate:"max=…,oneof=… …,gte=…,lte=…"` struct tag on each field with rules (rule-free fields keep a
  plain `json` tag).
- **Go validation enforcement (R-252):** the Go tags are now enforced at request time. When at least one
  wired CREATE handler's entity carries rules, the Go backend declares
  `github.com/go-playground/validator/v10` in its own `go.mod`, emits `internal/handlers/validate.go`
  (`var validate = validator.New()` + a `validateStruct(v any) (int, string)` helper returning
  `400`/`"validation_failed"` on a tag violation), and calls `validateStruct(m)` in each such CREATE
  handler — right after the JSON decode and before the `store.Create…` call, `400`-ing on failure. The
  validator dependency lives only in the generated project; rule-free projects emit none of this and stay
  byte-identical. The schema still enforces at the DB for both backends, so validation now holds at three
  layers (request model, request handler, and database). Unknown rules are ignored.

Both backend adapters (FastAPI and Go) emit it as `migrations/0001_init.sql` exactly when the IR has
entities and `database_strategy == postgres` — no previously emitted file changes. Output is byte-stable,
so the R-237 edit loop diffs the migration automatically when the IR entities change. Nothing connects
to or runs a database; this only emits SQL text.

### Seed data (R-248)

`render_postgres_seed(ir)` (in `codegen/seed_sql.py`) turns the IR **fixtures** into an honest
`migrations/0002_seed.sql`: one `INSERT INTO <table> (<cols>) VALUES (<literals>);` per fixture row.
Columns are the row's keys sorted alphabetically; **only columns present in the row are inserted** — the
platform never invents, defaults, or guesses a value (omitted columns fall to the schema's DB default /
NULL). It owns the SQL literal quoting (the only such helper in the codebase): single quotes are
doubled, `bool → TRUE/FALSE`, `None → NULL`, numbers are bare, and `dict/list → '<json>'::jsonb`. Both
backends emit it inside the same `has_db` block as `0001_init.sql`, but only when the IR declares
fixtures — so a fixture-free IR (e.g. `rideshare-favourites`) gets no `0002_seed.sql`. Deterministic and
offline; nothing connects to or runs a database. `task builder:demo -- minimal-blog` prints it.

## Data-access / repository layer (R-239)

`codegen/data_access.py` gives the generated backend a real persistence layer over the R-238 tables,
emitted (alongside the migration) when the IR has entities and `database_strategy == postgres`:

- **Python (FastAPI):** `app/db.py` (an async `psycopg` connection helper reading `DATABASE_URL`, dict
  rows) and `app/repositories/<entity>.py` per entity with `list/get/create/delete`. `requirements.txt`
  gains `psycopg`.
- **Go:** `internal/store/store.go` (a `database/sql` opener using the pgx driver) and
  `internal/store/<entity>.go` per entity with `List/Get/Create/Delete` scanning into the generated
  `models.<Entity>` structs. `go.mod` gains the pgx `require`; the model import path matches the module.

Every query **value** is parameterized (`%s` for psycopg, `$N` for pgx) — no value is ever
string-interpolated into SQL; only fixed IR-derived table/column identifiers appear inline. An entity
with only an `id` column creates via `DEFAULT VALUES`. Pure and deterministic — nothing connects to or
queries a database. The R-237 edit loop diffs the repositories when the IR entities change.

## Route wiring — handlers call the repositories (R-240)

`codegen/route_wiring.py` connects the generated HTTP handlers to the R-239 data-access layer, but only
for the **unambiguous CRUD shapes** — so the platform never emits plausible-but-wrong behaviour. An
endpoint's entity comes from its `response_schema` (else `request_schema`); the operation is inferred:

| Endpoint shape | Wired to |
|----------------|----------|
| `GET /things` (no path param), entity known | `list_*` → 200 JSON array |
| `GET /things/{id}` (single param) | `get_*` → 200, or 404 |
| `POST /things` with a `request_schema` (no param) | `create_*` from the body → 201 |
| `DELETE /things/{id}` (single param) | `delete_*` → 204, or 404 |
| `GET /parents/{id}/children` — child has exactly one FK relation (R-244) | `list_*_by_<rel>(id)` → parent-scoped list |
| anything else (multi-param, custom, ambiguous FK) | left as a labelled `501` scaffold |

The sub-collection case (R-244) filters the child table by the relation's FK column
(`WHERE <rel>_id = <param>`, value parameterized). The data-access layer emits a matching filtered list
per FK relation — Python `list_<table>_by_<rel>`, Go `List<Entity>By<Rel>`. It wires only when the child
entity has **exactly one** many_to_one/one_to_one relation (otherwise the target is ambiguous and the
endpoint stays `501`).

- **Python (FastAPI):** wired routes `import` the repository/model and `await` the repository call;
  create takes a Pydantic body (`payload.model_dump()`). Unwired routes keep the `501` scaffold.
- **Go:** handlers become methods on a `Handlers` struct holding a `*sql.DB` (`internal/handlers/
  handlers.go` with a `New` constructor and a `writeJSON` helper); `main.go` calls `store.Open()` and
  registers `h.<Handler>`. Wired methods call the `store`, decode the body into `models.<Entity>` for
  create, and return the right status; unwired ones stay `501`.

Emitted only when the IR has entities and `database_strategy == postgres` (otherwise backends keep the
plain scaffold handlers, unchanged). Deterministic and offline — nothing runs.

## Authentication guards (R-241) + JWT verification (R-242)

`codegen/auth_guard.py` makes the IR's per-endpoint `auth` flag real: every endpoint with `auth: true`
enforces a guard that **verifies a JWT (HS256)** using a `JWT_SECRET` read from the environment —
`401` on a missing/invalid/expired token, `500` when `JWT_SECRET` is unset. The secret is **never**
hard-coded or defaulted; it only ever comes from the environment.

- **Python (FastAPI):** emits `app/auth.py` — `require_auth` uses PyJWT (`jwt.decode(..,
  algorithms=["HS256"])`) and returns the verified claims; each `auth: true` route declares
  `dependencies=[Depends(require_auth)]`. `requirements.txt` gains `PyJWT`, `.env.example` gains an empty
  `JWT_SECRET`.
- **Go:** emits `internal/handlers/auth.go` — `RequireAuth(next)` parses the token with
  `github.com/golang-jwt/jwt/v5`, rejecting non-HMAC tokens; `main.go` wraps exactly the `auth: true`
  registrations with `handlers.RequireAuth(...)`. `go.mod` gains the golang-jwt `require`, `.env.example`
  gains `JWT_SECRET`.

The IR `roles` are surfaced as a generated constant (Python `ROLES` tuple, Go `Roles` slice). Emitted
only when the IR declares at least one `auth: true` endpoint (both DB and non-DB backends); deterministic
and offline — no token is signed or verified at generation time.

### Per-endpoint role enforcement (R-243)

An `ApiEndpoint` may declare `required_roles` (role ids). The guard then enforces that the verified
token carries at least one of them, else **403**:

- **Python:** `app/auth.py` gains a `require_roles(*required)` dependency factory (verify the token via
  `require_auth`, then require the `roles` claim to intersect `required`); routes with roles declare
  `dependencies=[Depends(require_roles("author"))]`.
- **Go:** `RequireRoles(next, required...)` verifies the token (shared `verifyToken`) then checks the
  `roles` claim via `hasAnyRole`; `main.go` wraps those endpoints with `handlers.RequireRoles(h, "…")`.

`required_roles` implies `auth: true`, and each role must be a declared `Role` (`validate_ir` errors on
an unknown role). Endpoints without roles keep the plain `require_auth`/`RequireAuth` guard.

### PATCH/update handlers (R-253)

`route_wiring` gains `Op.UPDATE`. A `PATCH /entities/{id}` endpoint is wired when:

- HTTP method is `PATCH`
- The path ends in exactly one path parameter (`{…}`)
- `request_schema` names a known repo entity

Everything else stays a clearly labelled 501 scaffold (same conservative policy as CREATE/DELETE).

**Go (`net/http`):** `data_access._go_entity_store` emits `Update<Entity>(ctx, db, id string,
m models.<Entity>) (*models.<Entity>, error)` — a single `UPDATE … SET col=$1, … WHERE id=$N
RETURNING <col_list>` with a `Scan` into a fresh struct. Returns `nil, nil` on `sql.ErrNoRows`.
The handler (in `_handlers_file_wired`) decodes the body, calls `validateStruct(m)` if the entity
has validation rules (reusing the R-252 helper — 400 on failure), calls `store.Update<Entity>`,
writes 404 if `nil`, or 200 + `writeJSON(updated)` on success. `has_validation` also activates for
UPDATE handlers — the validator dependency is emitted whenever any wired CREATE or UPDATE handler's
entity carries rules.

**FastAPI (Python):** `data_access._python_repository` emits `update_<table>(id, data)` — a
parameterized `UPDATE … SET col=%s, … WHERE id=%s RETURNING *` using only the data keys (excluding
`id`); returns `None` (via `fetchone()`) when no row matched. The router emits `@router.patch`
with `id_param: str` + `payload: <Entity>` → `await update_<table>(id_param, payload.model_dump())`
→ `HTTPException(404)` on `None`.

All SQL values are parameterized (`$N` / `%s`); identifiers are fixed IR-derived strings. Additive
and offline — no platform dependency, nothing installed, built, run, or connected to a database.
