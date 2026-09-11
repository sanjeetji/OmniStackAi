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

### Structured validation error bodies (R-254)

Replaced the flat `"validation_failed"` string with structured JSON error bodies in the generated Go backend:

- `field_validation.go_validate_file()` emits a `validationError` struct:
  ```go
  type validationError struct {
  	Field   string `json:"field"`
  	Rule    string `json:"rule"`
  	Message string `json:"message"`
  }
  ```
- Emits `validateStruct(w http.ResponseWriter, v any) bool`:
  - On validation error, iterates `validator.ValidationErrors`, constructs `[]validationError` entries with `Field: fe.Field()`, `Rule: fe.Tag()`, and a clear message, and sends `{"errors": [...]}` via `writeJSON(w, http.StatusBadRequest, ...)`, returning `false`.
  - On success, returns `true`.
- Wired CREATE and UPDATE handlers in `backend_go.py` guard with `if !validateStruct(w, m) { return }`.
- Imports `"fmt"` in `internal/handlers/validate.go` for `fmt.Sprintf`.
- Rule-free entities and example IRs remain unchanged (no `validate.go` emitted).
- FastAPI backends with Pydantic already provide structured 422 field error details by default.

### Query parameter pagination on LIST endpoints (R-255)

Added query parameter pagination (`limit` & `offset`) to `GET` list and parent-scoped `LIST_BY` subcollection routes across both Go and FastAPI backends:

- **Go shared handlers (`internal/handlers/handlers.go`)**: emits `parsePagination(r *http.Request) (int, int)` returning `limit` (default `100`, parsed if `>0`) and `offset` (default `0`, parsed if `>=0`) using `strconv.Atoi`.
- **Go wired handlers (`internal/handlers/*.go`)**: `Op.LIST` and `Op.LIST_BY` handlers call `limit, offset := parsePagination(r)` and pass both to `store.List<Entity>` / `store.List<Entity>By<Rel>`.
- **Go store (`internal/store/*.go`)**:
  - `List<Entity>(ctx, db, limit, offset int)`: `SELECT ... ORDER BY id LIMIT $1 OFFSET $2`.
  - `List<Entity>By<Rel>(ctx, db, <rel>ID, limit, offset int)`: `SELECT ... WHERE <rel>_id = $1 ORDER BY id LIMIT $2 OFFSET $3`.
- **FastAPI routers (`app/routers/*.py`)**:
  - `Op.LIST`: `async def get_<entities>(limit: int = 100, offset: int = 0) -> list[dict]:` calling `await <entity>.list_<entity>(limit=limit, offset=offset)`.
  - `Op.LIST_BY`: `async def get_<parents>_<id>_<children>(<id>: str, limit: int = 100, offset: int = 0) -> list[dict]:` calling `await <child>.list_<child>_by_<parent>(<id>, limit=limit, offset=offset)`.
- **FastAPI repositories (`app/repositories/*.py`)**: parameterized `LIMIT %s OFFSET %s` using `(limit, offset)` with defaults 100 and 0.
- All query parameters are optional: clients omitting them get the sensible defaults (100 items starting at offset 0).

### PUT / full-replace update handlers (R-256)

Extended `route_wiring` to recognize `PUT /entities/{id}` alongside `PATCH /entities/{id}`:

- **Route wiring (`route_wiring.py`)**: when `method in ("PATCH", "PUT")`, the path ends in one path parameter, and `request_schema` matches a known entity, maps to `Op.UPDATE`.
- **Go backend (`backend_go.py`)**: emits `func (h *Handlers) Put<Entities><Id>(w http.ResponseWriter, r *http.Request)` which decodes body into `models.<Entity>`, guards with `if !validateStruct(w, m) { return }` if entity has validation rules, calls `store.Update<Entity>`, writes 404 if nil, or 200 + `writeJSON` on success.
- **FastAPI backend (`backend_python.py`)**: emits `@router.put` route handler taking `id_param` and validated `payload: <Entity>`, calling `update_<table>`, raising 404 on not-found or returning row on success.
- Rule-free entities emit no `validateStruct` in PUT handlers. Non-matching shapes stay 501 scaffold. Example IRs unchanged.

### Frontend Typed API Client & Backend CORS Middleware (R-257)

Bridged the generated Next.js frontend (`apps/web`) with Go and FastAPI backend services (`services/api`) for complete full-stack connectivity:

- **Next.js Typed API Client (`apps/web/lib/api.ts`)**:
  - `_api_client_file(ir: ApplicationIR)` emits a type-safe TypeScript client using standard `fetch`.
  - Configurable `BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""`.
  - `ApiOptions`: extends `RequestInit`, adding `token?: string` (Bearer auth) and `params?: Record<string, string | number | boolean | undefined>` (query strings).
  - `ApiError`: carries HTTP `status` and `data` (for structured error bodies).
  - `request<T>(path, options, body)`: encapsulates URL parameter encoding, JSON headers, error handling, and 204 No Content.
  - Generates strongly-typed SDK functions for each IR endpoint:
    - Wired CRUD: `list<Entity>(options?: { params?: { limit?: number, offset?: number } })`, `get<Entity>(id)`, `create<Entity>(data: Partial<Entity>)`, `update<Entity>(id, data: Partial<Entity>)`, `delete<Entity>(id)`, and parent-scoped `list<Entity>sBy<Rel>(parentId, options)`.
    - Custom / unwired endpoints: deterministic camelCase function names with typed path parameters, body, and return types.
    - Exported `api` namespace object bundling all client methods.
  - Updates Next.js `.env.example` to include `NEXT_PUBLIC_API_URL=http://localhost:8080`.
- **Backend CORS Middleware (`services/api`)**:
  - **Go Backend (`main.go`)**: wraps `mux` in `corsMiddleware(next http.Handler)` returning `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods` (`GET, POST, PUT, PATCH, DELETE, OPTIONS`), `Access-Control-Allow-Headers` (`Content-Type, Authorization`), and handles `OPTIONS` preflight with 204 No Content.
  - **FastAPI Backend (`app/main.py`)**: adds `CORSMiddleware` with `allow_origins`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
  - Both backends support `CORS_ALLOWED_ORIGIN` env var (defaulting to `*` in development) and add placeholder to `.env.example`.

### Query Parameter Sorting with SQL Injection Whitelist Protection (R-258)

Added safe, type-checked query parameter sorting across Go, FastAPI, and Next.js targets:

- **Go Store (`internal/store/*.go`)**:
  - `List<Entity>` and `List<Entity>By<Rel>` accept `(ctx, db, limit, offset int, sort, order string)`.
  - Column identifiers cannot be parameterized with `$1`, so the store strictly whitelists `sort` against known entity fields using a Go `switch` statement, safely falling back to `"id"` if invalid or unrecognized.
  - Sort direction defaults to `"ASC"`, matching case-insensitive `"desc"` to `"DESC"`.
  - Emits `fmt.Sprintf("SELECT ... ORDER BY %s %s LIMIT $1 OFFSET $2", col, dir)` (or `LIMIT $2 OFFSET $3` for subcollection lists).
- **Go Handlers (`internal/handlers/*.go`)**:
  - `handlers.go` emits `parseSort(r *http.Request) (string, string)` helper extracting `sort` (default `"id"`) and `order` (default `"asc"`).
  - Wired `Op.LIST` and `Op.LIST_BY` handlers extract `sort, order := parseSort(r)` and pass to the store methods.
- **FastAPI Backend (`services/api`)**:
  - `app/routers/*.py`: `@router.get` list and subcollection routes declare `limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc"` query parameters and forward them to data access repositories.
  - `app/repositories/*.py`: declares module-level `ALLOWED_SORT_FIELDS = [...]`, validates `sort_col = sort if sort in ALLOWED_SORT_FIELDS else "id"`, validates `sort_dir = "DESC" if order.lower() == "desc" else "ASC"`, and executes `SELECT * FROM {TABLE} ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s`.
- **Next.js Client (`apps/web/lib/api.ts`)**:
  - Updates list methods to type `params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc" }`.
  - Built-in URLSearchParams serialization automatically encodes `?sort=...&order=...`.

### Total Count Queries & X-Total-Count Header on LIST Endpoints (R-259)

Added total count database queries and `X-Total-Count` HTTP response header emission on `Op.LIST` and `Op.LIST_BY` endpoints across Go and FastAPI backends, with CORS exposure and typed Next.js client integration:

- **Go Store (`internal/store/*.go`)**:
  - `Count<Entity>(ctx context.Context, db *sql.DB) (int, error)` executing `SELECT COUNT(*) FROM <table>`.
  - `Count<Entity>By<Rel>(ctx context.Context, db *sql.DB, <rel>ID string) (int, error)` executing `SELECT COUNT(*) FROM <table> WHERE <rel>_id = $1`.
- **Go Handlers (`internal/handlers/*.go`)**:
  - `Op.LIST` and `Op.LIST_BY` handlers query `total, err := store.Count...` prior to listing, and emit `w.Header().Set("X-Total-Count", strconv.Itoa(total))` before JSON response serialization.
  - `corsMiddleware` in `main.go` emits `w.Header().Set("Access-Control-Expose-Headers", "X-Total-Count")` so browsers expose the header to client applications.
- **FastAPI Backend (`services/api`)**:
  - `app/repositories/*.py`: emits `async def count_<table>() -> int` and `async def count_<table>_by_<rel>(<rel>_id: str) -> int`.
  - `app/routers/*.py`: imports `Response` from `fastapi`, injects `response: Response` into `Op.LIST` and `Op.LIST_BY` route handlers, queries `total = await <table>.count_...()`, and sets `response.headers["X-Total-Count"] = str(total)`.
  - `app/main.py`: adds `expose_headers=["X-Total-Count"]` to `CORSMiddleware`.
- **Next.js Client (`apps/web/lib/api.ts`)**:
  - Exports `PaginatedResult<T> { data: T; total: number }`.
  - Emits helper `requestWithMeta<T>` which extracts `res.headers.get("X-Total-Count")` (defaulting to 0) and returns `{ data, total }`.
  - Generates `list<Entity>WithCount(...)` and `list<Entity>sBy<Rel>WithCount(...)` returning `Promise<PaginatedResult<<Entity>[]>>`.
  - Standard `list<Entity>(...)` and `list<Entity>sBy<Rel>(...)` methods are preserved returning `Promise<<Entity>[]>` for full backward compatibility.

### OpenAPI 3.1 Contract Generation from Application IR (R-260)

Added deterministic generation of standard OpenAPI 3.1.0 specifications directly from the `ApplicationIR` (Brief Section 43: *Contracts: OpenAPI + generated clients*, `packages/contracts/openapi/`):

- **Core Generator (`codegen/openapi.py`)**:
  - `render_openapi(ir: ApplicationIR) -> dict[str, Any]` and `render_openapi_json(ir: ApplicationIR, indent: int = 2) -> str`:
    - `openapi: "3.1.0"` with title (`ir.name`), description (`ir.description`), and version (`"1.0.0"`).
    - `components.schemas`: converts every entity into an OpenAPI schema with properties mapped from `FieldType` (string, integer, number, boolean, date-time, uuid, object) and validation constraints (`maxLength`, `enum`, `minimum`, `maximum`, `required`). Includes standard `ValidationError`, `ValidationErrorResponse`, and `ErrorResponse` schemas.
    - `components.securitySchemes`: declares `BearerAuth` (HTTP Bearer / JWT).
    - `paths`: maps every `ApiEndpoint` with typed path parameters (`{param}`), query parameters (`limit`, `offset`, `sort`, `order` on LIST endpoints), request bodies referencing entity schemas for CREATE and UPDATE, and standard responses (200, 201, 204, 400, 401, 403, 404).
    - `headers`: documents `X-Total-Count` (integer) on 200 LIST and LIST_BY collection responses.
    - `security`: attaches `BearerAuth` security requirement on operations where `api.auth` is true, documenting role requirements.
- **Customer Monorepo Assembly (`codegen/assembler.py`)**:
  - Emits `contracts/openapi.json` at the root of the assembled customer monorepo, fulfilling the canonical contract location and documenting it in the root `README.md`.
- **Backend Services (`codegen/backend_go.py`, `codegen/backend_python.py`)**:
  - Both Go and FastAPI backend project generators emit `openapi.json` at their project root.

### Full-Text / Keyword Search Filtering on LIST Endpoints (R-261)

Added end-to-end full-text and keyword search filtering via the `q` query parameter across Go, FastAPI, Next.js, and OpenAPI 3.1 targets:

- **Searchable Field Identification (`codegen/data_access.py`)**:
  - Helper `_searchable_fields(entity)` inspects entity fields, selecting those with `FieldType.STRING` or `FieldType.TEXT`.
  - Non-text entities (or entities with 0 string/text fields) gracefully omit search clauses, executing standard queries with zero SQL syntax errors.
- **Go Store (`internal/store/*.go`)**:
  - `List<Entity>` and `Count<Entity>` accept `q string`. When `q != ""` and searchable fields exist, a parameterized `WHERE (col1 ILIKE $1 OR col2 ILIKE $1 ...)` clause is appended.
  - Takes advantage of PostgreSQL parameter reuse (`$1`) so only a single wildcard argument `"%"+q+"%"` is passed to `db.QueryContext` or `db.QueryRowContext`.
  - Subcollections `List<Entity>By<Rel>` and `Count<Entity>By<Rel>` combine relation foreign-key scoping (`WHERE <rel>_id = $1 AND (col1 ILIKE $2 OR ...)`) with search parameterization.
- **Go Handlers (`internal/handlers/*.go`)**:
  - Helper `parseSearch(r *http.Request) string` extracts and trims `r.URL.Query().Get("q")`.
  - Wired `Op.LIST` and `Op.LIST_BY` handlers extract `q := parseSearch(r)` and forward `q` to store `Count...` and `List...` methods.
- **FastAPI Backend (`services/api`)**:
  - `app/repositories/*.py`: `list_<table>` and `count_<table>` accept `q: str | None = None`. When `q` is passed, parameterized `WHERE (col1 ILIKE %s OR ...)` is applied using `f"%{q}%"` wildcard patterns.
  - `app/routers/*.py`: route handlers for `Op.LIST` and `Op.LIST_BY` declare `q: str | None = None` and forward `q=q` to repositories.
- **Next.js Client (`apps/web/lib/api.ts`)**:
  - Updates list methods (`list<Entities>`, `list<Entities>WithCount`, `list<Entities>By<Rel>`, `list<Entities>By<Rel>WithCount`) to type `q?: string` in `params`.
  - URL serialization via `URLSearchParams` automatically URL-encodes search queries.
- **OpenAPI 3.1 Specification (`codegen/openapi.py`)**:
  - Documents optional `q` query parameter (`type: "string"`, description: `"Search query to filter records across text fields"`) on all `Op.LIST` and `Op.LIST_BY` operations.

### React Data-Fetching & Mutation Hooks Generation (R-262)

Added strongly-typed, idiomatic React hooks (`apps/web/lib/hooks.ts`) in the generated Next.js web application:

- **Module Structure (`codegen/nextjs.py`)**:
  - Emitted with `"use client"` directive, enabling direct import by Next.js client components and screens.
  - Standard React 18 built-ins only (`useState`, `useEffect`, `useCallback`, `Dispatch`, `SetStateAction`) — requires zero additional runtime packages.
  - Consumes the typed API client (`lib/api.ts`) and TypeScript interfaces (`lib/types.ts`).
  - Exports public `render_hooks(ir: ApplicationIR) -> str` generator, also registered in `omnistackai_agent_engine.codegen`.
- **Shared Type Interfaces**:
  - `UseListParams`: typed `{ limit?: number; offset?: number; sort?: string; order?: "asc" | "desc"; q?: string }`.
  - `UseListState<T>`: state interface providing `data`, `total`, `loading`, `error`, computed pagination (`page`, `pageSize`, `totalPages`), query updaters (`setParams`, `setPage`, `setSearch`, `setSort`), and `refetch`.
  - `UseDetailState<T>`: state interface providing `data`, `loading`, `error`, and `refetch`.
  - `UseMutationState<TData, TResult>`: state interface providing `loading`, `error`, `mutate`, and `reset`.
- **Generated Hook Types**:
  - `useList<Entities>(initialParams?, options?)`: collection data fetching hook with automatic pagination math (1-based `page`, `totalPages`), keyword search (`setSearch` resetting offset), sorting (`setSort` toggling or setting order), and automatic `refetch` on parameter changes.
  - `use<Entity>(id, options?)`: detail data fetching hook that fetches when `id` is non-empty, resetting to idle/null when `id` is unset.
  - `useCreate<Entity>()`: mutation hook providing `{ create, mutate, loading, error, reset }`.
  - `useUpdate<Entity>()`: mutation hook providing `{ update, mutate, loading, error, reset }`.
  - `useDelete<Entity>()`: mutation hook providing `{ remove, mutate, loading, error, reset }`.
  - `useList<Entities>By<Rel>(parentId, initialParams?, options?)`: subcollection data fetching hook scoped to parent relation foreign key.
- **Unified Export**:
  - Aggregates all emitted entity and subcollection hooks into an exported `hooks` namespace object (`export const hooks = { ... };`).

### Interactive Screen Component Generator with Real Data Binding (R-263)

Upgraded generated Next.js screen pages (`apps/web/app/<screen.id>/page.tsx`) into real, interactive, strongly-typed React client components:

- **Client Directive & Standard React (`codegen/nextjs.py`)**:
  - Every screen page emits `"use client";` at the top, enabling interactive state and browser event handling.
  - Built purely with standard React built-in hooks (`useState`) and Next.js `<Link>` components — introduces zero external styling or component framework dependencies.
  - Emits clean, accessible Vanilla CSS inline styling with modern typography, subtle borders, and responsive card/table layouts.
- **Screen Intent & Entity Detection**:
  - `_match_entity(screen, ir)` maps screens to their corresponding IR entities using multi-token score matching across screen IDs, component tags, and actions, with graceful fallback.
  - `_screen_intent(screen)` classifies screens as `"collection"`, `"form"`, or `"generic"` based on component tags (`list`, `table`, `form`) and screen ID semantics (`editor`, `create`, `list`).
  - `_get_ops_by_entity(ir)` identifies available operations for the matched entity, ensuring screens only import and invoke hooks that are actually wired and exported.
- **Collection Screens (`_collection_screen_page`)**:
  - Connects to `useList<Entities>()` hook from `../lib/hooks`.
  - Renders a live search input bound directly to `setSearch` with form submission and input synchronization.
  - Renders sortable table headers with ascending/descending visual indicators bound to `setSort`.
  - Renders pagination controls (`Previous`, `Next`, `Page X of Y`) bound to `setPage`, with automatic disabled states during loading or boundary pages.
  - Renders loading banners, error alert banners with retry buttons, and empty-state indicators.
  - Renders delete action buttons calling `useDelete<Entity>()` when `Op.DELETE` is wired for the entity.
  - Automatically renders navigation links (e.g. `+ New <Entity>` linking to complementary editor screens).
- **Form / Editor Screens (`_form_screen_page`)**:
  - Connects to `useCreate<Entity>()` hook from `../lib/hooks`.
  - Schema-derived form inputs matching each entity field type:
    - `BOOL` → interactive checkbox input.
    - `TEXT` → multi-line `<textarea>`.
    - `INT` / `FLOAT` → typed `<input type="number">` with appropriate step attributes.
    - `DATETIME` → `<input type="datetime-local">`.
    - `STRING` / other → `<input type="text">`.
  - Schema-driven required field markers (`*`) and HTML validation attributes (`required`).
  - Submission handler with loading state (`Saving...`), error capture banner, and success banner.
  - Reset and cancel navigation controls linking back to complementary list screens or the overview.
- **Graceful Fallback Screens (`_fallback_screen_page`)**:
  - When screens have no matching entities or unwired operations, renders a clean, structured UI displaying role badges, component tags, actions, and navigation links without generating broken imports.
- **Diff Predictability & Verification**:
  - `_screen_page` avoids referencing `ir.description`, keeping screen pages byte-identical across description modifications to ensure hunk-level diff tests (`test_console_snapshot.py`) remain completely green.
  - Public `render_screen_page(screen, ir) -> str` exported in `omnistackai_agent_engine.codegen`.

### Field-Level Validation & Error Feedback in Generated Next.js Forms (R-264)

Enhanced generated form screens and the API client with real-time and server-side field-level validation feedback:

- **API Client Error Extraction (`codegen/nextjs.py`)**:
  - Emits `extractFieldErrors(error: unknown): Record<string, string>` in `apps/web/lib/api.ts`.
  - Normalizes Go backend validation errors (`{"errors": [{"field": "...", "rule": "...", "message": "..."}]}`) into `{ [field]: message }`.
  - Normalizes FastAPI/Pydantic validation errors (`{"detail": [{"loc": ["body", "..."], "msg": "..."}]}`) into `{ [field]: message }`.
  - Returns empty record for non-validation or network errors, allowing safe fallbacks.
- **Form Screen Validation & Error Handling (`_form_screen_page`)**:
  - Declares `const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});`.
  - **Client-Side Pre-Validation**: inside `handleSubmit`, evaluates constraints prior to dispatching network requests:
    - `required`: ensures non-empty string, valid number, or date value.
    - `max_length`: verifies string length against `rules.max_length`.
    - `min` / `max`: checks numeric bounds against declared limits.
    - `enum`: verifies string values against allowed options.
    - On violation, populates `fieldErrors` and halts submission without network latency.
  - **Server-Side Error Mapping**: on API error, calls `extractFieldErrors(err)` and maps backend constraint violations to input states.
  - **Accessible Error Styling**:
    - Invalid inputs dynamically receive red borders (`fieldErrors[f.name] ? "1px solid #ef4444" : "1px solid #cbd5e1"`) and `aria-invalid={!!fieldErrors[f.name]}`.
    - Renders dedicated field error message spans directly beneath inputs (`<span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>`).
  - **Reactive Error Clearing**: input edits (`onChange`) clear `fieldErrors[f.name]` immediately as the user begins typing.
  - **Enum Dropdowns**: fields carrying `enum` validation render `<select>` dropdowns with declared options.
  - **Reset Control**: Reset button clears `fieldErrors` alongside form state and success banners.
  - **Error Banners**: Displays warning banner when field errors are present, while suppressing generic `submitError` banners to keep focus on field-specific feedback.

### Subcollection Navigation & Master-Detail Views in Generated Screens (R-265)

Connects parent entity views (e.g. `Post` in `minimal-blog`) to nested child subcollections (e.g. `Comments`) using typed React hooks and interactive master-detail layouts:

- **Subcollection Relation Detection (`_subcollections_for_parent`)**:
  - Scans `ir.apis` for endpoints wired with `Op.LIST_BY` and associated foreign-key relations (`many_to_one`).
  - Matches the child entity's relation `target_entity` to the parent entity name.
  - Extracts structured metadata: child entity, relation name, `id_param` (e.g. `postId`), hook name (`useList<Entities>By<Rel>`), child plural, and non-FK display fields.
  - Returns empty list for entities without subcollections (e.g. `rideshare-favourites`), ensuring zero overhead or unused imports on leaf entity screens.
- **Collection Screens with Master-Detail (`_collection_screen_page`)**:
  - Automatically imports subcollection hooks (`useList<Children>By<Rel>`) and child types (`import type { <Child> }`) when subcollections exist.
  - Declares selection state: `const [selectedId, setSelectedId] = useState<string | null>(null);`.
  - Wires subcollection hooks at the top level scoped to `selectedId`:
    - When `selectedId` is `null`, hooks idle cleanly with 0 network calls.
    - When a parent row is selected, hooks automatically fetch child items for that parent ID.
  - **Interactive Table Selection**:
    - Master table rows support click-to-select with visual highlight (`background: #eff6ff`).
    - Dedicated "View Details" / "Hide Details" toggle button with `e.stopPropagation()`.
    - Preserves delete operations (`useDelete<Entity>()`) alongside selection controls.
  - **Master-Detail Subcollection Panel**:
    - Unselected prompt: invites user to select a parent row from the table above.
    - Selected header: displays the parent entity name, primary title, and "Deselect" action.
    - **Total Count Badges**: renders live total count badges (`<span style={{ ... }}>{subcol.total}</span>`).
    - **Tabbed Subcollections**: multi-subcollection parent entities render tab buttons with per-collection count badges to switch active child views.
    - **Child Items List**: renders child items with formatted display fields, loading spinners, error alerts, empty states, and manual "Refresh" button.
- **Dedicated Detail Screens (`_detail_screen_page`)**:
  - Handles screens with `intent == "detail"` (`components=("detail",)` or `actions=("view",)`).
  - Wires `use<Entity>(selectedId)` to load parent entity attributes into a structured `<dl>` definition list.
  - Renders the interactive subcollections section scoped to the parent ID with count badges and child items.
- **Strict Diff Invariance**:
  - Neither `_collection_screen_page` nor `_detail_screen_page` references `ir.description`, keeping generated screen files byte-identical across description modifications to ensure patch stability in `test_console_snapshot.py`.

### Update/Edit Mode in Generated Next.js Forms & Collection Screen Edit Actions (R-266)

Closes the full-stack CRUD editing cycle by connecting generated Next.js screens to existing backend update handlers (`PUT`/`PATCH`) and typed React mutation hooks (`useUpdate<Entity>` and `use<Entity>(id)`):

- **Dual-Mode Form Screens (`_form_screen_page`)**:
  - Automatically identifies whether an entity supports updates (`can_update = Op.UPDATE in ops`) and creation (`can_create = Op.CREATE in ops`).
  - When `can_update` is enabled, imports `use<Entity>`, `useUpdate<Entity>`, and `useSearchParams` from `"next/navigation"`.
  - Reads the entity identifier from URL search parameters: `const editId = searchParams.get("id"); const isEdit = Boolean(editId);`.
  - Wires mutation hook `const { update, loading: updating, error: updateError } = useUpdate<Entity>();` and data fetching hook `const { data: initialData, loading: fetchingInitial } = use<Entity>(editId);`.
  - Declares `useEffect` to synchronize fetched `initialData` into `formData` state when loaded in edit mode.
  - Branches `handleSubmit` submission:
    - In edit mode: calls `await update(editId, formData);` and displays update success message.
    - In create mode: calls `await create(formData);`, resets form fields to initial values, and displays create success message.
  - Dynamically adapts UI elements:
    - Page Title: `{isEdit ? "Edit " + name : screen.name}`.
    - Submit Button: `{((submitting || updating) ? "Saving..." : (isEdit ? "Update " + name : "Save " + name))}`.
    - Success Banner: `{isEdit ? name + " updated successfully!" : name + " saved successfully!"}`.
    - Loading Indicator: While fetching initial data in edit mode, the banner renders layout-preserving skeleton field bars (R-293) instead of a "Loading <entity> details..." line.
- **Collection Screen Edit Actions (`_collection_screen_page`)**:
  - When `Op.UPDATE` is wired and a complementary form screen exists, adds an "Edit" action `<Link>` in the table row pointing to `/{form_screen.id}?id=${(item as any).id}`.
  - Attaches `onClick={(e) => e.stopPropagation()}` to prevent row selection toggling when clicking the Edit link.
  - Preserves delete buttons alongside Edit links when `Op.DELETE` is also wired.
- **Subcollection New Child Link**:
  - Master-detail subcollection panel renders a `+ New <Child>` button pointing to `/{child_form.id}?{foreign_key}=${selectedId}` when a form screen exists for the child entity.
- **Diff Invariance & Fallback Cleanliness**:
  - Entities without `Op.UPDATE` (e.g. `minimal-blog` Post) emit zero update hooks, zero search parameter parsing, and pure create-only forms, maintaining byte-for-byte diff stability.
  - Generated code contains no references to `ir.description`.

### Foreign-Key Relation Selectors & Parent Auto-Population in Generated Next.js Forms (R-267)

Eliminates manual UUID copy-pasting and closes the parent-child navigation loop in generated Next.js form screens (`_form_screen_page`):

- **Foreign-Key Relation Detection (`_parent_relations_for_entity`)**:
  - Scans `entity.relations` for `RelationKind.MANY_TO_ONE` target relations and child fields ending in `_id`.
  - Matches the parent entity in `ir.entities` and checks if it supports `Op.LIST`.
  - Resolves parent entity metadata: pluralized name, hook name (`useList<ParentPlural>`), primary display field (`title`/`name`/`id`), and display label.
  - Appends any missing foreign key fields from parent relations to `editable_fields`.
- **Parent List Hook Integration**:
  - Automatically imports unique parent list hooks (`useList<ParentPlural>`) from `"../lib/hooks"`.
  - Wires parent list hooks at component top level: `const <parents>List = useList<Parents>();`.
- **Accessible `<select>` Dropdown Selectors**:
  - Replaces raw text inputs for foreign key fields with accessible `<select>` dropdowns.
  - Displays dynamic placeholder indicating loading state: `{<parents>List.loading ? "Loading <parents>..." : "Select <parent>..."}`.
  - Populates `<option>` tags from `(<parents>List.data || [])` showing parent primary display field (`{String(item.title ?? item.name ?? item.id)}`).
  - Displays visual parent link badge when a parent is selected: `&bull; Selected <Parent> linked`.
  - Wires client-side required validation and per-field error messages (`fieldErrors[fk_field]`) with `aria-invalid` styling.
- **URL Query Parameter Pre-Population**:
  - Automatically reads URL query parameters via `useSearchParams` on form mount.
  - Resolves parameter aliases: `<field_name>`, `<relation>_id`, `<relation>Id`, `<relation>`.
  - Automatically pre-populates `formData[fk]` when navigating from parent master-detail views (`+ New <Child>` links).
- **Diff Invariance & Fallback Cleanliness**:
  - Independent entities without relations (e.g. `minimal-blog` Post) emit zero relation hooks, dropdowns, or badges.
  - Generated screen code contains no references to `ir.description`, preserving snapshot diff stability.

### Subcollection Child Item Deletion & Mutation Feedback in Master-Detail Views (R-268)

Completes the child management cycle in master-detail views by enabling child item deletion with confirmation prompts, loading/disabled states, error feedback alerts, and automatic list refetching:

- **Subcollection Deletion Detection (`SubcollectionInfo.can_delete`)**:
  - Automatically identifies whether a child entity supports `Op.DELETE` via `_get_ops_by_entity(ir)`.
  - Supports fallback entity resolution for `DELETE` endpoints lacking explicit `response_schema` (e.g. `ApiEndpoint(HttpMethod.DELETE, "/comments/{id}")`).
  - Sets `can_delete = True` on `SubcollectionInfo` dataclass instances.
- **Hook Integration in Master-Detail Views**:
  - In `_collection_screen_page` and `_detail_screen_page`, conditionally imports `useDelete<Child>` hooks from `"../lib/hooks"`.
  - Avoids duplicate imports when the parent entity already imported `useDelete<Parent>`.
  - Instantiates delete hooks at component level: `const { remove: remove<Child>, loading: deleting<Child>, error: delete<Child>Error } = useDelete<Child>();`.
- **Mutation Handlers & Refetching**:
  - Emits `handleDelete<Child>` handler with confirmation prompt (`confirm("Are you sure you want to delete this <Child>?")`).
  - Wraps removal in try/catch to capture errors into hook state without uncaught promise rejections.
  - Automatically triggers child subcollection refetch (`<subcol>.refetch()`) upon deletion.
- **Card-Level Delete Action & Mutation Feedback**:
  - Renders an accessible, styled Delete button on each child card with `e.stopPropagation()`, disabled state during mutation (`disabled={deleting<Child>}`), and dynamic label `{deleting<Child> ? "Deleting..." : "Delete"}`.
  - Renders mutation error alert banner (`{delete<Child>Error && ...}`) directly above child items if deletion fails.
- **Clean Fallback & Invariance**:
  - Subcollections whose child entity lacks `Op.DELETE` omit delete hooks and buttons.
  - Strict diff invariance: zero references to `ir.description`, preventing diff drift in `test_console_snapshot.py`.

### Page Size Selector & Contextual Empty State CTAs in Generated Next.js Screens (R-269)

Enriches pagination and zero-state UX in generated Next.js screens with interactive page size selection and contextual call-to-actions:

- **Configurable Page Size in Typed React Hooks (`lib/hooks.ts`)**:
  - `UseListState<T>` interface declares `setPageSize: (size: number) => void;`.
  - Both `useList<Entities>()` and `useList<Children>By<Rel>()` implement `setPageSize = useCallback((newPageSize: number) => { setParams((prev) => ({ ...prev, limit: Math.max(1, newPageSize), offset: 0 })); }, []);`.
  - Automatically returns `pageSize` and `setPageSize` in hook state objects alongside `page`, `totalPages`, and `setPage`.
- **Accessible Page Size Selector in Collection Screens (`_collection_screen_page`)**:
  - Destructures `pageSize` and `setPageSize` from `useList<Plural>()`.
  - Renders a styled, accessible `<select id="pageSizeSelect">` with `aria-label="Select page size"` directly in the table footer alongside pagination buttons.
  - Exposes standard page size options: `10 per page`, `25 per page`, `50 per page`, `100 per page`.
  - Changing selection triggers `setPageSize(Number(e.target.value))` which resets `offset: 0` and queries the updated limit.
- **Contextual Empty States in Table Views**:
  - When `data && data.length === 0`:
    - **Search Active**: when search input is non-empty (`searchInput.trim()`), displays `No <plural> matching "<searchInput>".` with a `Clear search` CTA button that resets `searchInput` and calls `setSearch("")`.
    - **Initial State with Editor**: when no search is active and a complementary `form_screen` exists, displays `No <plural> found yet.` with a styled `+ Create first <Entity>` CTA link pointing to `/{form_screen.id}`.
    - **Fallback**: when no editor screen exists, displays `No <plural> found.`.
- **Subcollection Master-Detail Empty States**:
  - When child data is empty in master-detail panels (`_collection_screen_page` and `_detail_screen_page`):
    - When a complementary child form screen (`child_form`) is detected, renders `No <children> found for this <entity>.` accompanied by a styled `+ Add first <Child>` link pre-populated with parent foreign key (`/{child_form.id}?{sub.id_param}=${selectedId}`).
- **Diff Invariance & Fallback Cleanliness**:
  - 100% standard-library Python, 0 external dependencies, 0 network calls.
  - Zero references to `ir.description`, strictly maintaining snapshot diff invariance.

### Bulk Selection & Batch Deletion in Generated Next.js Collection Screens (R-270)

Enables enterprise-grade multi-record selection and batch operations in generated Next.js master collection screens (`apps/web/app/<screen>/page.tsx`):

- **Multi-Record Selection State & Interactions**:
  - Declares `checkedIds: string[]` state alongside current page ID tracking: `const allCurrentIds = (data ?? []).map((item: any) => item.id).filter(Boolean);`.
  - Calculates select-all status: `const isAllChecked = allCurrentIds.length > 0 && allCurrentIds.every((id: string) => checkedIds.includes(id));`.
  - Implements `handleCheckAll` to batch toggle all items on the active page, `handleToggleRow(id)` to toggle individual rows, and `handleClearSelection()` to reset selection.
  - Individual `handleDelete(id)` cleans up deleted records from selection: `setCheckedIds((prev) => prev.filter((x) => x !== id));`.
- **Contextual Bulk Actions Toolbar**:
  - Rendered dynamically above the table when `checkedIds.length > 0`:
    - Displays selection count badge: `{checkedIds.length} {name/plural} selected`.
    - Renders `Clear selection` button bound to `handleClearSelection`.
    - When `Op.DELETE` is wired, renders `Delete Selected ({checkedIds.length})` action button with progress indicator `{batchDeleting ? "Deleting..." : ...}`.
- **Batch Deletion Lifecycle & Error Handling**:
  - Executes confirmation prompt: `confirm("Are you sure you want to delete " + checkedIds.length + " " + (checkedIds.length === 1 ? name : plural) + "?")`.
  - Manages `batchDeleting: boolean` loading state.
  - Performs concurrent deletion across selected IDs via `Promise.all(checkedIds.map(id => remove(id)))`.
  - On completion: clears `checkedIds`, triggers `refetch()`, and resets loading state.
  - Catches mutation failures into `batchDeleteError: string | null` and renders a dismissible alert banner.
- **Table Header & Row Checkboxes**:
  - `<thead>`: renders master checkbox with `aria-label="Select all"`, `checked={isAllChecked}`, and `onChange={handleCheckAll}`.
  - `<tbody>`: renders row checkbox with `checked={checkedIds.includes((item as any).id)}`, `onChange={() => handleToggleRow((item as any).id)}`, and `e.stopPropagation()` so checking a row doesn't open/close subcollection detail panels.
  - Selected rows highlight with `#f8fafc` background.
  - Table loading and empty state `colSpan` values account for the checkbox column (`+1`).
- **Diff Invariance & Fallback Cleanliness**:
  - Completely non-intrusive: entities lacking `Op.DELETE` cleanly omit the batch delete button while selection remains functional.
  - Zero substring collisions with subcollection selection state (`selectedId`) or controls (`Deselect`).
  - Strict diff invariance: zero references to `ir.description`.

### CSV Data Export & Bulk Export in Generated Next.js Collection Screens (R-271)

Enables client-side RFC 4180 CSV data export and bulk selection export in generated Next.js master collection screens (`apps/web/app/<screen>/page.tsx`):

- **handleExportCsv Helper Function**:
  - Emitted directly in `_collection_screen_page` accepting an optional `selectedOnly: boolean = false` parameter.
  - Filters loaded items against `checkedIds` when `selectedOnly=true`, or exports all loaded records (`data ?? []`).
  - Safely early-returns when `itemsToExport.length === 0`.
- **Strict RFC 4180 CSV Serializer**:
  - Serializes values via inline `toCsvVal(val: unknown)`:
    * Returns empty quotes `""` for `null` and `undefined`.
    * Serializes objects via `JSON.stringify(val)` for clean presentation.
    * Escapes internal double quotes `"` to `""`.
    * Wraps every serialized field in double quotes `"${str.replace(/"/g, '""')}"`.
  - Emits all declared entity fields (`entity.fields`) across both header row and row data mappings.
  - Joins rows using newline characters (`\n`).
- **Browser Download Lifecycle**:
  - Constructs `new Blob([csvContent], { type: "text/csv;charset=utf-8;" })`.
  - Generates object URL via `URL.createObjectURL(blob)`.
  - Dynamically creates an anchor element (`<a>`) with `download` attribute set to `{plural.lower()}_export.csv`.
  - Appends anchor to `document.body`, triggers programmatic `link.click()`, and removes anchor from DOM.
  - Cleans up allocated memory via `URL.revokeObjectURL(url)`.
- **Top Controls Toolbar & Contextual Bulk Bar Integration**:
  - Top controls bar: renders "Export CSV" button alongside Search and Refresh (`disabled={!data || data.length === 0}`).
  - Contextual Bulk Actions Bar: renders "Export Selected ({checkedIds.length})" button when `checkedIds.length > 0`.
  - Symmetrical layout: Export Selected is available whether or not the entity supports DELETE; Delete Selected coexists when deletion is enabled.
- **Diff Invariance & Fallback Cleanliness**:
  - Pure standard-library Python codegen, 100% offline, 0 network, 0 external dependencies.
  - Zero references to `ir.description`, strictly preserving snapshot diff invariance.

### Deep-Linking & Entity Lifecycle in Next.js Detail Screens (R-272)

Enables full-lifecycle deep linking, automated query param fetching, cross-screen navigation, entity editing, deletion, and single-record JSON export across Next.js detail and collection screens (`apps/web/app/<screen>/page.tsx`):

- **Query Param Auto-Loading**:
  - `_detail_screen_page` imports `useSearchParams` from `"next/navigation"` and `useEffect` from `"react"`.
  - Extracts `const queryId = searchParams.get("id");` and initializes `idInput` and `selectedId`.
  - An automated `useEffect` synchronizes `selectedId` and `idInput` whenever `queryId` updates, immediately triggering `use<Entity>(selectedId)` without requiring manual typing.
  - Retains the manual ID input box as an intuitive fallback when no query parameter is provided.
- **Entity Lifecycle Actions in Detail View**:
  - Loaded item card features a dedicated action toolbar:
    * **Single-Record JSON Export**: "Export JSON" button invokes `handleExportJson()`, serializing the loaded item via `Blob([JSON.stringify(item, null, 2)], { type: "application/json" })`, dynamic anchor creation, download attribute (`{name.lower()}_{id}.json`), automated click, and `URL.revokeObjectURL(url)` memory cleanup.
    * **Direct Entity Edit**: When `can_edit` and `form_screen` are present, renders an "Edit {name}" link navigating directly to `/{form_screen.id}?id=${selectedId}`.
    * **Direct Entity Deletion**: When `can_delete` is True, imports and wires `useDelete<Entity>()` with `handleDelete` executing a confirmation dialog, setting loading state (`deletingMain`), error capture (`deleteMainError`), and state reset (`setSelectedId(null); setIdInput("");`).
    * **Mutation Feedback**: Renders an alert banner when record deletion fails.
- **Breadcrumb Navigation**:
  - Detects complementary `collection_screen` for the entity in `ir.screens`.
  - In header breadcrumbs: renders `<Link href="/{collection_screen.id}">&larr; Back to {plural}</Link>`, falling back to `&larr; Overview` when no collection screen is present.
- **Collection Table Integration**:
  - In `_collection_screen_page`: detects dedicated `detail_screen` for the entity in `ir.screens`.
  - When present, renders a styled "View" link button (`/{detail_screen.id}?id=${(item as any).id}`) in the table row actions cell.
- **Diff Invariance & Fallback Cleanliness**:
  - 100% offline, 0 network, 0 external npm dependencies.
  - Zero references to `ir.description`, preserving snapshot diff invariance.

### Global Responsive Navigation Shell & Header Navbar (R-273)

Generates a unified, persistent application navigation header shell (`apps/web/components/navbar.tsx`) and connects it into the root application layout (`apps/web/app/layout.tsx`):

- **Client Component with Reactive Route Detection**:
  - `components/navbar.tsx` is emitted with `"use client";` at the top and imports Next.js `usePathname` from `"next/navigation"`.
  - Defines `isLinkActive(href)` comparing current `pathname` against `"/"` or `href` / `href + "/"`.
  - Dynamically applies active visual cues: active links highlight with `#eff6ff` (blue-50) background, `#1d4ed8` (blue-700) font color, `fontWeight: 600`, and subtle `#bfdbfe` border; inactive links display `#475569` with subtle hover transitions.
- **Application Branding & Overview Navigation**:
  - Displays application logo avatar badge (initial letter of `ir.name` inside a rounded gradient container) and brand title linking to the home overview page (`/`).
  - Includes a dedicated "Overview" link to `/`.
- **Dynamic Screen Navigation & Role Badges**:
  - Automatically identifies all primary destination screens (`collection`, `form`, and `generic`) from `ir.screens`.
  - Parameter-dependent `detail` screens (`_screen_intent(s) == "detail"`) are cleanly excluded from the horizontal top bar, keeping navigation focused.
  - Non-public screen roles (e.g. `admin`, `member`) render an adjacent pill badge.
- **Header Quick-Action CTA Button**:
  - Identifies the first available create form screen in `ir.screens`.
  - Renders a prominent primary button on the right side of the navbar (e.g. `+ New {Entity}` or `+ Create`) with `#2563eb` styling, enabling 1-click creation from any screen in the application.
- **RootLayout Integration**:
  - `app/layout.tsx` imports `<Navbar />` from `../components/navbar` and renders it above `{children}`.
  - Keeps `RootLayout` as a server component exporting Next.js `Metadata`, ensuring optimal metadata streaming and SSR.
  - Applies global typography and background tokens (`#f8fafc` background, system font stack).
- **Quality & Offline Independence**:
  - 100% offline, zero external npm dependencies, pure React/Next.js client/server separation.
  - Strict diff invariance across `ir.description` changes.

### Form Screen Post-Submit Contextual CTAs, Record Navigation & Cancel Actions (R-274)

Upgrades generated Next.js form screens (`apps/web/app/<screen>/page.tsx`) with post-submission contextual navigation links and a Cancel action in the form footer:

- **`lastSavedId` State & ID Capture**:
  - `_form_screen_page` declares `const [lastSavedId, setLastSavedId] = useState<string | null>(null);`.
  - Create branch (both create-only and dual create/update): `const res = await create(formData);` followed by `if (res && (res as any).id) { setLastSavedId(String((res as any).id)); }`.
  - Update branch: `setLastSavedId(editId);` is called after `await update(editId, formData);`.
- **Interactive Success Banner**:
  - Success banner upgraded from a static `<div>` to an interactive action panel.
  - Exact message text (`{isEdit ? "{name} updated successfully!" : "{name} saved successfully!"}`) is preserved in a `<span>` child, keeping existing test assertions invariant.
  - Dismiss button (`&times;`) with `aria-label="Dismiss"` calls `setSuccess(false)`.
  - Contextual "View {name} →" Next.js `Link` rendered to `/{detail_screen.id}?id=${lastSavedId || (isEdit ? editId : null)}` when a detail screen exists for the entity (guarded by id expression truthiness).
  - "← Back to {plural}" Next.js `Link` rendered to `/{list_screen.id}` when a collection screen exists for the entity.
  - "+ Create another {name}" action button (create mode only) calls `setSuccess(false); setLastSavedId(null);` for rapid sequential data entry.
- **Form Footer Cancel Button**:
  - A styled `Cancel` Next.js `Link` button is inserted before the Reset button in the form card footer.
  - Links to `/{list_screen.id}` when a collection screen exists for the entity, or `/` as a safe fallback.
  - Reset `onClick` is extended with `setLastSavedId(null);` to clear saved ID on reset.
- **Detection Logic**:
  - `detail_screen` and `list_screen` are detected from `ir.screens` using `_screen_intent(s)` and entity token matching (`_match_entity`).
- **Quality & Offline Independence**:
  - 100% offline, zero external npm dependencies, no new IR fields.
  - Strict diff invariance across `ir.description` changes.

### Rich Entity-Aware Dashboard Overview Page (R-275)

Upgrades the generated Next.js app's home page (`apps/web/app/page.tsx`) from a static 20-line bare
HTML list into a rich, entity-aware dashboard client component:

- **Client Component**:
  - `"use client";` at the top — matches the pattern of all other generated screen pages and enables React hooks.
  - Imports `Link from "next/link"` for screen navigation.

- **Live Entity Count Cards**:
  - Imports `useList<Plural>` hook for each entity with `Op.LIST` wired (determined via `_get_ops_by_entity`).
  - Calls `useList<Entity>({ limit: 1 })` per listable entity — only `total` is needed, so `limit: 1` minimises data transfer.
  - Displays `.total` as a live 32px count badge with loading fallback (`"…"`) and error fallback (`"—"`).
  - Card styling: white background, `border-radius: 12`, box-shadow, uppercase entity label in `#64748b`, plural subtitle in `#94a3b8`.
  - Entities without `Op.LIST` (e.g. create-only) emit no hook and no card.

- **Screen Navigation Cards**:
  - CSS Grid (`repeat(auto-fill, minmax(240px, 1fr))`) of styled `<Link>` tiles.
  - Detail screens are excluded via `_screen_intent(s) == "detail"` — keeps top-level navigation clean.
  - Each tile shows the screen title (via `_title_case`) and an intent badge (`Collection`, `Form`, or `Screen`).
  - Non-public screens (role not in `("public", "")`) render a role badge pill (`#eff6ff` background, `#1d4ed8` text).

- **Quick Actions Section**:
  - `+ Create {Entity}` blue CTA buttons (`#2563eb`) for each form screen, using `_match_entity` to resolve the entity name.
  - Falls back to `+ {screen title}` when no entity can be resolved.

- **Diff Invariance Fix**:
  - `ir.description` is intentionally NOT embedded in the generated page body (it already appears in `README.md`).
  - This removes a pre-existing diff-invariance violation where changing only `ir.description` caused `app/page.tsx` to differ.
  - `test_console_snapshot.py` updated: `apps/web/app/page.tsx` removed from the expected edit-diff path set.

- **Fallbacks**:
  - When `ir.entities` is empty: no hook imports, no count cards section.
  - When `ir.screens` is empty: no screen navigation section, no quick actions.

- **Quality**:
  - 100% offline, zero external npm dependencies, zero new IR fields.
  - `# noqa: PLR0912` on `_overview_page` (high branch count justified by inline card/section rendering logic).
  - All styles are inline — no changes to `app/globals.css`.

### Detail Screen Record Selector, Prev/Next Navigation & Deep-Link Sync (R-276)

Enhances generated Next.js detail screens (`apps/web/app/<screen>/page.tsx`) with interactive record discovery, sequential navigation, and browser URL synchronization:

- **Interactive Record Selector Dropdown**:
  - When `Op.LIST` is wired for the entity, `_detail_screen_page` imports `useList<Plural>` and invokes `useList<Plural>()`.
  - In the top ID selection bar, renders a styled `<select aria-label="Select {name}">` dropdown with `"-- Choose {name} --"` placeholder and `<option>` elements mapped to loaded records, displaying the best descriptive title field (`title`, `name`, `label`, `email`, or `id`).
  - Selecting an option updates `selectedId`, `idInput`, and synchronizes the URL search parameter.

- **URL Search Param Synchronization (`handleSelectId`)**:
  - Emits `handleSelectId(newId: string | null)` helper that sets `selectedId`, updates `idInput`, and synchronizes `?id=<id>` via `window.history.replaceState` (or deletes `id` when cleared).
  - Both manual "Load {name}" submission and "Clear" button call `handleSelectId`.
  - `handleDelete` removes the `id` search param upon successful record deletion.

- **Sequential Record Navigation (Prev / Next)**:
  - When list data is available and an item is displayed, the card header renders contextual `&larr; Prev` and `Next &rarr;` navigation buttons.
  - Correctly disabled at list boundaries (`disabled={!prevItem}` and `disabled={!nextItem}`) with informative hover tooltips.

- **Recent Records Quick-Pick Empty State**:
  - When `!selectedId`, empty state renders a "Recent {plural}" grid of clickable card tiles displaying title and truncated ID, allowing one-click record selection instead of requiring a manual UUID.

- **Quality & Safety**:
  - Clean fallback when `Op.LIST` is absent or entity contains only an `id` field.
  - 100% offline, zero external npm dependencies, zero new IR fields, strict diff invariance.

### Form Screen Dirty State Tracking, Unsaved Changes Guard & Reset Confirmation (R-277)

Upgrades generated Next.js form screens (`apps/web/app/<screen>/page.tsx`) with deterministic dirty state tracking (`isDirty`), visual warning indicators, confirmation-guarded actions, and native browser `beforeunload` event listeners protecting against accidental data loss:

- **Deterministic `isDirty` Tracking**:
  - Form screen imports `useMemo` from `"react"`.
  - Computes `baselineData` as `initialData` (in edit mode when loaded) or `initialValues` (in create mode).
  - Computes `isDirty` by comparing every key in `formData` against `baselineData` via `useMemo`.
  - Gracefully handles empty string and `undefined` equivalence to avoid false dirty states on initial render.
- **Visual Warnings**:
  - Form header renders an amber "Unsaved changes" visual badge (`#fef3c7` / `#92400e`) next to the screen title when `isDirty && !success`.
  - Form footer renders an amber notice (`&bull; You have unsaved changes`) when `isDirty && !success`.
- **Confirmation-Guarded Actions**:
  - `Cancel` link button prompts with `confirm("You have unsaved changes. Discard them and leave?")` when `isDirty`.
  - `Reset` button prompts with `confirm("Discard all changes and reset form?")` when `isDirty`, resetting state cleanly while maintaining `setLastSavedId(null)`.
- **Native Browser `beforeunload` Guard**:
  - Emits a `useEffect` hook registering a native window `beforeunload` listener while `isDirty && !submitting && !success`.
  - Triggers the browser's native unsaved changes prompt on page refresh or tab close.
  - Automatically cleaned up on unmount or when dirty state clears.
- **Post-Submit State Cleanup**:
  - Form submission success (`setSuccess(true)`) naturally suppresses dirty state warnings and allows immediate navigation.
- **Quality & Safety**:
  - 100% offline, zero external npm dependencies, zero new IR fields, strict diff invariance.

### Collection Screen Boolean & Enum Field Filtering (R-278, R-282, R-283)

Generated Next.js collection screens provide interactive boolean/enum controls, now backed by R-282's
server-side query filtering so results are correct across pagination:

- **Filterable Field Detection (`_filterable_fields_for_entity`)**:
  - Detects fields of type `FieldType.BOOL` and string fields with `enum:a|b|c` validation rules.
  - Automatically excludes `id` and relation foreign key fields from filter pills.
- **Server-Side Filter State & Requests (R-283)**:
  - Filterable top-level hooks use `UseCollectionListParams.filters: Record<string, string>` and expose
    `setFilter(field, value)` / `clearFilters()`; both reset `offset` to page one.
  - A generated per-entity allowlist accepts only the exact boolean (`true`/`false`) and enum values from
    the IR. Empty/`all` removes a field.
  - The hook flattens active filters into `ApiOptions.params`, so the API client emits the R-282
    `?<field>=<value>` query parameters before backend pagination.
  - Valid active filters hydrate/sync through the R-280 URL deep-link flow. Unknown fields and invalid
    values from the URL are ignored.
  - The screen reads `params.filters`, computes the active count, and renders `data ?? []` directly;
    the old `useMemo`/page-local `data.filter` path is gone.
- **Accessible Filter Toolbar**:
  - Rendered above the table and below the search input.
  - For boolean fields: renders segmented pill buttons (`[ All ] [ {Field}: Yes ] [ {Field}: No ]`) with dark `#0f172a` active styling and white text.
  - For enum fields: renders a styled `<select aria-label="Filter by {Field}">` with `-- All {Field}s --` and option values.
  - Displays an active filter count chip (`{activeFilterCount} active`) in `#eff6ff`/`#1d4ed8` and a "Reset" button when filters are active.
- **Dedicated Empty Filter State**:
  - When the server returns no rows while filters are active, displays
    `"No {plural} match the active filter criteria."` with a `"Clear all filters"` action button.
- **Quality & Safety**:
  - Clean fallback: entities without boolean or enum fields emit zero filter controls/options.
  - Scoped to top-level `Op.LIST`; FK-scoped `LIST_BY` hooks/endpoints are unchanged.
  - 100% offline, zero external npm dependencies, zero new IR fields, strict diff invariance.

### Server-Side Field Filters for FK-Scoped Subcollections (R-284)

Generated `LIST_BY` endpoints now accept the same IR-derived boolean and enum equality filters as
top-level `LIST`, while keeping foreign-key scope mandatory:

- `field_validation.filter_fields(entity)` remains the single allowlist shared by both backends and
  OpenAPI. Identifiers come only from validated IR fields; user values are never interpolated into SQL.
- Python relation-scoped repository helpers begin with `<relation>_id = %s`, append optional keyword
  search and active equality predicates deterministically, and return the same predicate/parameter list
  to both `list_*_by_*` and `count_*_by_*`. FastAPI routes expose `bool | None` and `str | None` query
  parameters and forward identical filters to both calls.
- Go emits a shared `<table>By<Relation>Filters(relationID, q, filters)` helper. Relation ID is always
  `$1`; a present `q` uses the next placeholder; allowlisted filter values follow via `len(args)+1`;
  limit and offset are numbered after all predicates. List and count use the same helper, and handlers
  call `parseFilters` only for filterable child entities.
- OpenAPI 3.1 `LIST_BY` operations document boolean schemas for bool fields and string schemas with
  explicit enum values for enum fields.
- Non-filterable subcollections retain their previous signatures and SQL, and output remains
  byte-identical across description-only IR changes. Generated Next.js subcollection filter state is a
  separate follow-up.

### Generated Next.js Wiring for Scoped Server Filters (R-285)

Generated parent collection and detail views now consume the R-284 `LIST_BY` filter contract instead of
filtering a loaded child page in browser memory:

- Filterable `useList<Child>By<Parent>` hooks use `UseCollectionListParams` / `UseCollectionListState`,
  validate values against the same generated boolean/enum option allowlist, and expose `setFilter` and
  `clearFilters`; both operations reset `offset` to zero.
- Before calling `list<Children>By<Parent>WithCount(parentId, ...)`, the hook separates its internal
  `filters` map and flattens active entries into request params. The parent relation ID remains the path
  argument, while search, sort, limit, offset, and allowlisted filters remain query parameters.
- Both the parent collection master-detail panel and dedicated parent detail screen render boolean
  filter pills, enum selects, an active-filter count, Reset, and a filtered-empty Clear filters action.
  The child rows map the server response directly, so results remain correct across pagination.
- Non-filterable child hooks and screens retain their prior output, and description-only IR changes stay
  byte-identical. No Application IR, backend, dependency, or database behavior changed.

### Race-Safe Generated Subcollection Refetches (R-286)

Generated `useList<Child>By<Parent>` hooks now prevent older LIST_BY requests from overwriting state
after rapid parent, search, sort, pagination, or filter changes:

- Every hook owns an `AbortController` ref and aborts it at the start of the next refetch. This occurs
  before the missing-parent early return, so deselecting a parent also cancels outstanding work.
- Valid requests install a fresh controller and pass `signal: controller.signal` after caller options,
  making the hook's internal cancellation signal authoritative while preserving request params and the
  parent path argument.
- A signal check after the response prevents stale data/total writes. Aborted and `AbortError` failures
  are ignored, only the active request clears loading, and effect cleanup aborts on dependency change or
  unmount.
- Filterable hooks retain the R-285 flattened query params; non-filterable hooks retain their public
  types and state shape. No Application IR, API, backend, dependency, or database behavior changed.

### Race-Safe Generated Detail Refetches (R-287)

The generated `use<Entity>` single-record detail hook now prevents an older GET from overwriting the
currently selected record during rapid record-selector / prev-next / deep-link / id changes — closing the
last generated data-fetch path without cancellation (LIST is R-280, LIST_BY is R-286):

- The hook owns an `AbortController` ref; `refetch` calls `abortRef.current?.abort()` before the
  `if (!id)` reset, so clearing the selection also cancels in-flight work. The missing-id branch resets
  `data`, `error`, and `loading`.
- A valid id installs a fresh controller and issues
  `api.get<Entity>(id, { ...options, signal: controller.signal })` — the internal signal is passed AFTER
  caller options so a caller cannot replace the hook's cancellation signal. (The generated API client
  already forwards `signal` through `request(...)`'s `...init` spread, so no client change was needed.)
- A `controller.signal.aborted` check guards the success write, the `catch` ignores aborted/`AbortError`
  failures, only the active request clears loading, and effect cleanup aborts on id change or unmount.
- The public hook name/params/return, `useList<Entities>` and `useList<Child>By<Parent>` hooks, backend,
  and Application IR are unchanged; description-only IR generation stays byte-identical.

### Deduplicated In-Flight Generated Mutation Requests (R-288)

The generated `useCreate<Entity>` / `useUpdate<Entity>` / `useDelete<Entity>` hooks now dedupe concurrent
invocations, extending race-safety from fetches (R-280/R-286/R-287) to writes so a double-clicked
Create/Save/Delete (or a programmatic re-call) cannot fire a duplicate POST/PUT/DELETE:

- Each hook owns `const pendingRef = useRef<Promise<T> | null>(null)` (T = `<Entity>` for create/update,
  `void` for delete). The callback's first statement is `if (pendingRef.current) return
  pendingRef.current;`, so a call arriving while a request is in flight awaits the same promise instead
  of starting a second request.
- The existing try/catch/finally body runs inside an IIFE captured as `pendingRef.current = request;` and
  returned; `finally` keeps `setLoading(false)` and adds `pendingRef.current = null;`.
- The callback signatures, the underlying `api.create|update|delete<Entity>(...)` calls, and the return
  shape (`{ create|update|remove, mutate, loading, error, reset }`) are unchanged; errors still set error
  state and reject. Fetch hooks, the generated API client, backend, and Application IR are untouched, and
  description-only IR generation stays byte-identical.

### Debounced Live Subcollection Search (R-289)

The generated subcollection (master-detail) search is now live and debounced (300ms), matching the
top-level collection search (R-280). R-281 shipped it submit-only; making it live is safe now that R-286
made the `useList<Child>By<Parent>` hook race-safe (superseded LIST_BY requests are aborted):

- `_subcol_search_names(s_var)` derives the state/setter names (`<s_var>Search` / `set<S_var>Search`);
  `_subcol_search_state(s_var)` emits, next to each subcollection hook declaration, a controlled
  `const [<state>, <setter>] = useState("")` plus a `setTimeout`/`clearTimeout` 300ms debounce
  `useEffect` that commits `<state>.trim()` to `<s_var>.setSearch`, guarded by `<state> !== (params.q ??
  "")` so an unchanged value is not recommitted.
- `_subcol_controls`'s search input is now controlled (`value`/`onChange`) instead of uncontrolled
  `defaultValue`+`FormData`; the form submit still commits immediately (Enter). Both the collection
  master-detail and detail screens carry it (both already import `useState`+`useEffect`); entities
  without a subcollection emit none.
- The `useList<Child>By<Parent>` hook, generated API client, backend, Application IR, and the
  sort/filter/pagination controls are unchanged; description-only IR generation stays byte-identical.

### Optimistic Delete with Rollback in the Collection Screen (R-290)

Generated collection deletes are optimistic — the affected rows vanish immediately and reappear only if
the server rejects, instead of waiting for the round-trip. Safe because mutation hooks are deduped
(R-288) and the list fetch is race-safe (R-280):

- The screen owns `const [pendingDeleteIds, setPendingDeleteIds] = useState<string[]>([]);` (emitted like
  the existing `checkedIds` selection state) and computes `const visibleRows = displayData.filter((item:
  any) => !pendingDeleteIds.includes(String((item as any).id)));`, which the table row map iterates.
- `handleDelete(id)` adds `String(id)` to `pendingDeleteIds` before `await remove(id)` and, in `catch`,
  removes it (row reappears) before the existing `toast.error`. `handleBatchDelete()` snapshots
  `const ids = checkedIds.map(String)`, adds them, and rolls them back in `catch`.
- A reconcile `useEffect(() => { setPendingDeleteIds((prev) => prev.filter((id) => (data ?? []).some((x:
  any) => String(x.id) === id))); }, [data]);` prunes ids once `refetch` has removed them — the row stays
  hidden through the round-trip, then the id is pruned when it is already gone from `data` (no flash-back,
  no unbounded growth).
- Detail-screen/subcollection delete, the mutation/list hooks, the generated API client, backend, and
  Application IR are unchanged; description-only IR generation stays byte-identical.

### Optimistic Subcollection Child Delete with Rollback (R-291)

Extends R-290's optimistic delete to the subcollection (master-detail) child lists in both the collection
master-detail and detail screens — deleting a child row hides it immediately and reappears (with the
existing error toast) only if the server rejects:

- `_subcol_delete_names(s_var)` derives `<s_var>Deleting` / `set<S_var>Deleting`. For each deletable
  subcollection, the generated screen emits `const [<s_var>Deleting, set<S_var>Deleting] =
  useState<string[]>([]);` and a reconcile `useEffect(() => { set<S_var>Deleting((prev) => prev.filter(
  (did) => (<s_var>.data ?? []).some((x: any) => String(x.id) === did))); }, [<s_var>.data]);`.
- The child delete handler adds `String(id)` to the overlay before `await remove<Child>(id)` and, in
  `catch`, removes it (row reappears) before the existing `toast.error`.
- The child row map source becomes `(<s_var>.data ?? []).filter((child: any) => !<s_var>Deleting.includes(
  String((child as any).id)))` when the subcollection is deletable, else `<s_var>.data` unchanged.
- Safe on the deduped mutation hooks (R-288) and the race-safe R-286 `useList<Child>By<Parent>` hook.
  Non-deletable subcollections, the hooks, the generated API client, backend, and Application IR are
  unchanged; description-only IR generation stays byte-identical.

### Loading Skeletons for Generated Screens (R-292)

The data-loading states render layout-preserving skeleton placeholders (static inline-styled gray rounded
bars) instead of a plain "Loading..." line — no CSS `@keyframes`, no new component/file, no dependency:

- Collection table: the `{loading && !data}` spanning cell maps `[0..4]` skeleton bars
  (`height: 14, background: "#e2e8f0", borderRadius: 4, margin: "10px 0", opacity: 1 - i * 0.15`).
- Subcollection (master-detail) lists (both render sites): the `{<s_var>.loading && !<s_var>.data}` block
  maps `[0..2]` skeleton blocks (`height: 44, background: "#f1f5f9"`).
- Detail-screen main: the `{loading}` block maps `[0..3]` skeleton lines of varying width
  (`width: `${88 - i * 14}%``).
- The refresh-button "Loading..." labels, empty/error states, and data rendering are unchanged; no
  hook/API-client/backend/Application-IR change; description-only IR generation stays byte-identical.

### Loading Skeletons for Form Initial Load & Detail Record-Selector (R-293)

Completes the R-292 coverage by replacing the two remaining plain "Loading..." text spots with the same
layout-preserving skeleton placeholders (no CSS `@keyframes`, no new component/file, no dependency):

- Form edit-mode initial load (`_form_screen_page`): the `{isEdit && fetchingInitial && (…)}` banner
  maps `[0, 1, 2]` skeleton field bars (`height: 34, background: "#e2e8f0", borderRadius: 6, opacity:
  1 - i * 0.2`) inside its existing flex-column banner, instead of "Loading `<name>` details...".
- Detail record-selector list (`_detail_screen_page`): the `{loadingList && (…)}` block maps `[0, 1, 2]`
  skeleton cards (`height: 56, background: "#f1f5f9", borderRadius: 6, opacity: 1 - i * 0.2`) in the same
  `repeat(auto-fill, minmax(220px, 1fr))` grid as the "recent records" cards, instead of
  "Loading `<plural>`...".
- The R-292 collection/subcollection/detail-main skeletons, all other loading states, empty/error states,
  and data rendering are unchanged; no hook/API-client/backend/Application-IR change; description-only IR
  generation stays byte-identical. Loading skeletons now cover every generated data-loading state.

### App Router Resilience Special Files (R-294)

`NextjsWebAdapter.generate()` emits the four Next.js App Router "special files" — the framework wires them
automatically, so no route/IR/hook change is needed. All four are static, inline-styled to match the app
aesthetic, dependency-free, and never reference `ir.name`/`ir.description` (so generation stays
deterministic, description-only-stable, and they never enter the console-snapshot description-edit diff):

- **`app/error.tsx`** (`"use client"`): route-segment error boundary
  `Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void })` that logs via
  `useEffect(() => console.error(error), [error])` and renders a recovery card — an optional
  `error.digest` reference line, a `reset()`-bound "Try again" button, and a "Back to overview"
  `<Link href="/">`.
- **`app/global-error.tsx`** (`"use client"`): root-layout error boundary that renders its OWN
  `<html lang="en"><body>` (required — it replaces the root layout) with the same `reset()` recovery.
- **`app/not-found.tsx`** (server component): a "404 / Page not found" page with a `<Link href="/">` back
  to the overview.
- **`app/loading.tsx`** (server component): a route-level Suspense fallback mapping `[0..5]` skeleton
  cards (`height: 96, background: "#f1f5f9", opacity: 1 - i * 0.12`) in a
  `repeat(auto-fill, minmax(220px, 1fr))` grid plus a header bar (`height: 32, background: "#e2e8f0"`),
  reusing the R-292/293 skeleton palette.

Templates are module constants (`_ERROR_PAGE`, `_GLOBAL_ERROR_PAGE`, `_NOT_FOUND_PAGE`, `_LOADING_PAGE`)
with `render_error_page`/`render_global_error_page`/`render_not_found_page`/`render_loading_page`
accessors exported from `codegen`, mirroring `render_toast_component`. No existing generated file, hook,
API client, backend, or Application-IR change.

### Consistent Error + Retry Affordance Across Fetch States (R-295)

The generated collection list already rendered a "Retry" button (calling `refetch()`) in its error
banner. R-295 brings the remaining data-fetch error states to parity, so every failed load offers
recovery — no hook/API-client/backend/IR change is needed because `refetch` already exists on every
affected hook (`use<Entity>` and `useList<Child>By<Parent>`):

- **Detail-screen main error** (`_detail_screen_page`): renders `Error loading <name>: {error.message}`
  inside a `<span>` beside a `<button onClick={() => refetch()}>Retry</button>` in a flex row (`refetch`
  is destructured from `use<Entity>(selectedId)`).
- **Both subcollection (master-detail) error banners** (the collection master-detail block in
  `_collection_screen_page` and the detail block in `_detail_screen_page`, byte-identical → updated via
  `replace_all`): render `Error: {<s_var>.error.message}` inside a `<span>` beside a
  `<button onClick={() => <s_var>.refetch()}>Retry</button>`.

Retry buttons reuse the collection error banner's flex layout and dark-red (`#991b1b`) styling. The
collection top-level error banner is unchanged, as are loading/empty/data-render states, delete-error
toasts, and form field errors; description-only IR generation stays byte-identical.

### Generated Web App Accessibility Pass (R-296)

Elevates the generated Next.js web application to enterprise accessibility standards (WCAG 2.1 AA / WAI-ARIA best practices) across all screen types without changing public hook APIs, generated API client, or backend semantics:

- **Error Banners (Live Regions & Alert Roles)**:
  - Collection top-level fetch error banner, detail screen main error banner, subcollection (master-detail) error banners in both views, and form submission error banner emit `role="alert"` and `aria-live="assertive"`, ensuring that assistive technologies announce errors immediately upon occurrence.
- **Accessible Search Inputs**:
  - Collection list search `<input>` emits `aria-label="Search <plural>"`.
  - Subcollection list search `<input>` emits `aria-label="Search <child_plural>"`.
- **Sortable Table Column Headers (WAI-ARIA Sort State)**:
  - In `_collection_screen_page`, each sortable column `<th>` emits:
    `aria-sort={params.sort === "<field>" ? (params.order === "desc" ? "descending" : "ascending") : "none"}`.
- **Accessible Pagination Controls**:
  - Collection pagination footer is wrapped in `<nav aria-label="Pagination">` with `aria-label="Previous page"` and `aria-label="Next page"` buttons.
  - Subcollection pagination buttons emit `aria-label="Previous page"` and `aria-label="Next page"`.
- **Status Announcements for Empty States**:
  - Contextual empty-state text containers in collection lists and subcollections emit `role="status"` for polite assistive announcements.
- **Quality & Safety**:
  - 100% offline, zero dependencies, all existing text strings, retry buttons, skeletons, and hook signatures strictly preserved; strict diff-invariance across `ir.description`.

### Global Notification Toast System & Action Feedback (R-279)

Adds a lightweight, accessible, and self-contained client-side toast notification system to generated Next.js web applications:

- **`ToastProvider` & `useToast` Hook (`apps/web/components/toast.tsx`)**:
  - Client component (`"use client";`) with zero external dependencies.
  - Implements `createContext`, `useContext`, `useState`, `useCallback`, and `useEffect`.
  - Exports `ToastProvider`, `useToast`, `ToastType = "success" | "error" | "info"`, `ToastItem`, and `ToastContextValue`.
  - Methods: `addToast(message, type, duration)`, `removeToast(id)`, and typed convenience helpers: `toast.success()`, `toast.error()`, and `toast.info()`.
  - Viewport: fixed bottom-right container (`position: "fixed"`, `bottom: 24`, `right: 24`, `zIndex: 9999`, `aria-live="polite"`).
  - Floating toast cards with auto-dismiss timers (default 4000ms), manual dismiss `×` button, and distinct status color accents:
    - Success: Emerald accent (`#a7f3d0`/`#15803d`/`✓`).
    - Error: Rose/Red accent (`#fecaca`/`#b91c1c`/`✕`).
    - Info: Blue accent (`#bfdbfe`/`#1d4ed8`/`ℹ`).
- **RootLayout Integration (`apps/web/app/layout.tsx`)**:
  - Imports `ToastProvider` from `../components/toast` and wraps the layout shell (`<Navbar />` and `{children}`).
- **Screen Action Feedback Wiring**:
  - **Collection screens**:
    - CSV export: emits `toast.info("Exporting {plural} to CSV...")`.
    - Single delete: emits `toast.success("Deleted {entity} successfully")` / `toast.error(err.message)`.
    - Batch delete: emits `toast.success("Successfully deleted {count} {plural}")` / `toast.error(err.message)`.
    - Subcollection delete: emits `toast.success("Deleted {child} successfully")` / `toast.error(err.message)`.
  - **Detail screens**:
    - JSON export: emits `toast.info("Exporting {entity} record to JSON...")`.
    - Main delete: emits `toast.success("Deleted {entity} successfully")` / `toast.error(err.message)`.
    - Subcollection delete: emits `toast.success("Deleted {child} successfully")` / `toast.error(err.message)`.
  - **Form screens**:
    - Submit create/update: emits `toast.success("{Entity} {created|updated} successfully")` / `toast.error(err.message)`.
## Keyboard navigation & shortcuts (R-297, R-298, R-299)

Generated Next.js collection, detail, and form screens support power-user keyboard navigation and shortcuts without adding external dependencies:

- **Collection screens (R-297)**:
  - **Search focus (`/`)**: Pressing `/` outside editable elements (`INPUT`, `TEXTAREA`, `SELECT`, `contentEditable`) focuses the search input via `searchInputRef = useRef<HTMLInputElement>(null)` and prevents default character insertion.
  - **Search reset (`Escape`)**: Pressing `Escape` when focused inside the search input resets `searchInput`, calls `setSearch("")` to clear committed filter state, and blurs the input.
  - **Filter reset (`Escape`)**: Pressing `Escape` outside editable elements when active filters are present (`activeFilterCount > 0`) calls `clearFilters()`.
  - **Event listener lifecycle**: Attached to `window` with proper cleanup on unmount, correctly listing dependencies (`[setSearch, activeFilterCount, clearFilters]`).

- **Detail screens (R-298)**:
  - **Record navigation (`ArrowLeft` / `[` and `ArrowRight` / `]`)**: Pressing `ArrowLeft` or `[` navigates to the previous record when available (`prevItem && handleSelectId(prevItem.id)`); pressing `ArrowRight` or `]` navigates to the next record when available (`nextItem && handleSelectId(nextItem.id)`).
  - **Edit mode shortcut (`e` / `E`)**: Pressing `e` or `E` jumps directly to edit mode when record update capability and an associated form screen exist (`can_edit && form_screen && selectedId`).
  - **Deselection (`Escape`)**: Pressing `Escape` outside editable elements deselects the current record (`handleSelectId(null)`).
  - **Input guards**: Keystrokes are ignored when focused inside editable elements (`INPUT`, `TEXTAREA`, `SELECT`, `contentEditable`).
  - **Event listener lifecycle**: Attached to `window` with proper cleanup on unmount, with comprehensive dependency arrays.

- **Form screens (R-299)**:
  - **Save shortcuts (`Cmd+Enter` / `Ctrl+Enter` & `Cmd+S` / `Ctrl+S`)**: Pressing `Cmd+Enter` or `Ctrl+Enter` triggers `form.requestSubmit()` across inputs and textareas; pressing `Cmd+S` or `Ctrl+S` triggers `form.requestSubmit()` and suppresses browser "Save Page As..." dialogs.
  - **Input blur (`Escape`)**: Pressing `Escape` while focused inside an editable control (`INPUT`, `TEXTAREA`, `SELECT`) blurs the field.
  - **Cancel navigation (`Escape`)**: Pressing `Escape` outside editable controls prompts to discard unsaved changes (if `isDirty`) and navigates back to `cancel_href`.
  - **Submission guards**: Prevents duplicate trigger if already saving (`!submitting` / `!(submitting || updating)`).
  - **Event listener lifecycle**: Attached to `window` with proper cleanup on unmount with dependencies (`[isDirty, submitting, updating]`).
- **Safety & Quality**: 100% offline, standard-library-only platform code, zero new IR fields, byte-identical diff invariance across `ir.description`.

### Generated Form Screen Input Constraints, Native HTML Validation & Live Character Counters (R-300)

NextjsWebAdapter derives native HTML constraints from entity field validation rules (`parse_field_rules(f)`) for generated form screens (`apps/web/app/<screen>/page.tsx`):

- **Native HTML Input Constraints**:
  - String and text fields with `max_length` rules emit native `maxLength={rules.max_length}` on `<input>` and `<textarea>` elements.
  - Numeric fields (integer and float) with `minimum` and/or `maximum` rules emit native `min={rules.minimum}` and `max={rules.maximum}` attributes on `<input type="number">`.
- **Live Character Counters**:
  - Text fields and textareas with `max_length` render a dynamic character counter below the field: `{String(formData["<name>"] ?? "").length} / {rules.max_length}`.
  - Adaptive warning threshold: the counter text turns amber (`#b45309`) when input length reaches or exceeds 90% of `max_length`.
  - Helper hint displays `Max {rules.max_length} characters` alongside the counter.
- **Range Badges**:
  - Numeric inputs with validation bounds display a styled range badge `Range: {min} to {max}` (or `Min: {min}` / `Max: {max}`) in the field helper container.
- **Test Compatibility & Diff Invariance**:
  - Preserves the exact `{fieldErrors.<name> && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.<name>}</span>}` error span, rendering constraints and counters in a complementary container below.
  - Fields without constraints remain 100% byte-identical.
  - 100% offline, stdlib-only Python codegen, zero network or model calls, byte-identical diff invariance across `ir.description`.

### Generated Web Search Input Clear Affordances & Form Screen First-Field AutoFocus (R-301)

NextjsWebAdapter enhances search ergonomics and form input workflow across generated Next.js web application screens (`apps/web/app/<screen>/page.tsx`):

- **Collection Screen Search Clear Button**:
  - In `_collection_screen_page`, the search input is wrapped in an accessible relative container with an interactive inline Clear (`×`) button rendered when `searchInput` is non-empty (`aria-label="Clear search"`).
  - Clicking Clear clears local input state (`setSearchInput("")`), commits empty search to the hook (`setSearch("")`), and refocuses the input (`searchInputRef.current?.focus()`).
- **Subcollection Master-Detail Search Clear Button**:
  - In `_subcol_controls`, the subcollection search input is wrapped in a relative container with an interactive inline Clear (`×`) button clearing local search state and committing to the hook on click (`aria-label="Clear <child_plural> search"`).
- **Form Screen First-Field AutoFocus**:
  - In `_form_screen_page`, the first editable field (`idx == 0` among `editable_fields`) automatically emits `autoFocus` on its interactive control (whether text input, textarea, numeric input, parent relation select, or checkbox), enabling immediate keyboard input upon navigating to create or edit screens. Subsequent fields omit `autoFocus`.
- **Quality & Safety**:
  - 100% offline, standard-library-only platform code, zero new IR fields, byte-identical diff invariance across `ir.description`.

### Generated Collection Screen Boolean & Enum Visual Status Badges & Detail Screen One-Click Copy-to-Clipboard Affordances (R-302)

NextjsWebAdapter elevates visual hierarchy, data readability, and operational workflow across generated Next.js web application screens (`apps/web/app/<screen>/page.tsx`):

- **Collection Screen Visual Status Badges**:
  - Boolean fields (`FieldType.BOOL`) render styled status pill badges: emerald background (`#dcfce7`), emerald text (`#166534`), and text "Yes" if truthy; slate background (`#f1f5f9`), slate text (`#64748b`), and text "No" if falsy.
  - Enum fields (with validation rule `enum:a|b|c`) render blue categorical pill badges (`#eff6ff` background, `#1d4ed8` text, `1px solid #bfdbfe` border).
  - Applied consistently across collection table cells, master-detail subcollection cards, and detail screen subcollection tabs.
- **Detail Screen One-Click Copy Affordances**:
  - In record card header, renders an accessible "Copy ID" button beside the record title (`aria-label="Copy ID to clipboard"`).
  - In definition list (`<dl>`), renders inline "Copy" affordance on `id` and UUID foreign key fields (`aria-label="Copy <field_label> to clipboard"`), and renders status badges for boolean and enum fields.
  - Implemented robust `handleCopy(text, label)` using `navigator?.clipboard?.writeText` with graceful `document.execCommand("copy")` fallback and toast feedback (`toast.success` / `toast.error`).
- **Quality & Safety**:
  - 100% offline, stdlib-only Python codegen, zero network or model calls, byte-identical diff invariance across `ir.description`.

### Generated Dashboard Overview Interactive Entity Links, Operational Health Badge & Metrics Chips (R-303)

NextjsWebAdapter elevates developer and user experience across generated Next.js dashboard overview pages (`apps/web/app/page.tsx` via `_overview_page`):

- **Interactive Entity Summary Cards**:
  - Listable entities with `Op.LIST` dynamically map to their primary collection screen and wrap in accessible `<Link href="/{col_screen.id}">` tiles.
  - Cards render uppercase entity tag, navigation indicator arrow (`&rarr;`), prominent live record total (`{var}.total`), and interactive `View all &rarr;` affordance.
  - Unlinked entities without a collection screen render as styled summary `<div>` cards, preserving backward compatibility.
- **Operational Health Badge & Summary Metrics**:
  - App header upgraded to a responsive flex layout featuring a live "System Operational" status pill (`#f0fdf4`, `#166534`, border `#bbf7d0`) with pulsing green dot indicator (`#22c55e`).
  - Summary metric counters display total entity count (`{count} Entities`) and total screen count (`{count} Screens`).
- **Screen Navigation & Empty States**:
  - Screen navigation cards render navigation indicator arrows (`&rarr;`) alongside screen titles.
  - Accessible zero-state fallback card rendered when neither entities nor screens are configured.
- **Quality & Safety**:
### Generated Accessible Confirmation Dialog — Replace window.confirm() with ConfirmDialog Component (R-304)

NextjsWebAdapter replaces crude, blocking `window.confirm()` browser dialogs with an accessible, styled modal confirmation dialog component (`apps/web/components/confirm-dialog.tsx`) and `useConfirm` hook across all generated screens:

- **Reusable Modal Confirmation Component (`components/confirm-dialog.tsx`)**:
  - `ConfirmDialog` component renders modal backdrop overlay, dialog card container, title header, message body, and Confirm/Cancel action buttons.
  - WAI-ARIA compliance: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`.
  - Focus management: traps Tab/Shift+Tab focus within dialog, focuses Confirm button on open, restores focus on close.
  - Keyboard interaction: closes/cancels dialog on `Escape` key press; clicking backdrop closes/cancels dialog.
  - Visual variants: supports danger intent (crimson confirm button `#dc2626` for deletes) and neutral/primary intent (`#2563eb`).
  - `useConfirm` hook: returns `confirmAsync(title, message, options) -> Promise<boolean>` resolving true on Confirm, false on Cancel/Dismiss, and `confirmProps` spread onto `<ConfirmDialog {...confirmProps} />`.
- **Collection Screens (`_collection_screen_page`)**:
  - Single item delete handler replaced with `await confirmAsync(...)`.
  - Batch/bulk delete handler replaced with `await confirmAsync(...)`.
  - Subcollection child delete handler replaced with `await confirmAsync(...)`.
  - Conditionally imports `useConfirm` and `ConfirmDialog` when deletable actions exist.
  - Renders `<ConfirmDialog {...confirmProps} />` in screen JSX.
- **Detail Screens (`_detail_screen_page`)**:
  - Record delete handler replaced with `await confirmAsync(...)`.
  - Master-detail subcollection child delete replaced with `await confirmAsync(...)`.
  - Conditionally imports `useConfirm` and `ConfirmDialog` when deletable actions exist.
  - Renders `<ConfirmDialog {...confirmProps} />` in screen JSX.
- **Form Screens (`_form_screen_page`)**:
  - Unsaved changes guard on Cancel button navigation replaced with `await confirmAsync(...)`.
  - Unsaved changes guard on `Escape` key press replaced with `await confirmAsync(...)`.
  - Form Reset button confirmation prompt replaced with `await confirmAsync(...)`.
  - Imports `useConfirm` and `ConfirmDialog`.
  - Renders `<ConfirmDialog {...confirmProps} />` in screen JSX.
- **Quality & Safety**:
  - 100% offline, stdlib-only Python codegen, zero runtime npm dependencies, zero network or model calls, byte-identical diff invariance across `ir.description`.

### Generated Keyboard Shortcuts Help Modal & Global Discovery Affordance (R-305)

Emits a dedicated keyboard shortcuts cheat sheet modal dialog and wires global discoverability into the application navigation bar:

- **Component Generation (`apps/web/components/shortcuts-dialog.tsx`)**:
  - Emits client component (`"use client";`) with zero external dependencies.
  - Categorized shortcut reference:
    - **Global**: `?` (Open keyboard shortcuts help), `Esc` (Dismiss dialog / modal).
    - **Collection Screens**: `/` (Focus search input), `Esc` (Clear active search & reset filters).
    - **Detail Screens**: `[` or `←` (Navigate to previous record), `]` or `→` (Navigate to next record), `e` (Edit current record), `Esc` (Deselect record / close detail).
    - **Form Screens**: `Cmd + Enter` / `Ctrl + Enter` (Save & Submit form), `Cmd + S` / `Ctrl + S` (Save & Submit form), `Esc` (Blur active field / Cancel form).
  - Clean modal styling with backdrop overlay (`rgba(15, 23, 42, 0.45)`, `backdropFilter: "blur(2px)"`), card container (`maxWidth: 580`), styled `<kbd>` key badges (`#f1f5f9` bg, `#334155` text, border `#cbd5e1`, box-shadow `0 1px 0 #94a3b8`), and responsive grid layout.
  - Accessible semantics: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="shortcuts-dialog-title"`, `Escape` key dismissal, backdrop click dismissal, and header close button (`&times;`).
- **Global Header Discoverability (`apps/web/components/navbar.tsx`)**:
  - Mounts `<ShortcutsDialog open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />`.
  - Wires global `keydown` event listener for `?` (Shift + `/`), ignoring events triggered inside editable elements (`INPUT`, `TEXTAREA`, `SELECT`, `contentEditable`).
  - Renders a visible, styled `Shortcuts (?)` trigger button with keyboard icon (`aria-label="Keyboard shortcuts"`) in the top navigation actions bar.
- **Diff Predictability & Safety**:
  - Completely static modal template; zero references to `ir.description` ensuring hunk-level diff invariance.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` and exported in `codegen.__init__` as `render_shortcuts_dialog_component`.

### Generated Accessible Breadcrumb Navigation Component & Screen Hierarchy (R-306)

Emits a reusable Breadcrumbs component and integrates hierarchical wayfinding in generated detail and form screens:

- **Component Generation (`apps/web/components/breadcrumbs.tsx`)**:
  - Emits client component (`"use client";`) with zero external dependencies.
  - Conforms to WAI-ARIA 1.2 breadcrumb design pattern:
    - `<nav aria-label="Breadcrumb">` wrapper with subtle bottom margin.
    - `<ol>` flex container with `listStyle: "none"`, removing default list margins/padding.
    - `<li>` items with inline flex alignment.
    - Separator (`/`) with `aria-hidden="true"` and muted color (`#94a3b8`).
    - Terminal/current page marked with `aria-current="page"`, dark slate font (`#0f172a`), and semi-bold weight (`600`).
    - Ancestor pages render as accessible Next.js `<Link>` elements (`#64748b` text with hover transition).
  - Exports typed interfaces `BreadcrumbItem` (`label: string; href?: string`) and `BreadcrumbsProps` (`items: BreadcrumbItem[]`).
- **Detail Screen Integration (`_detail_screen_page`)**:
  - Mounts `<Breadcrumbs items={breadcrumbs} />` at the top of detail screens.
  - Composes hierarchical path: Overview (`/`) &rarr; Collection (`/{col_screen.id}` when available) &rarr; Current record (`{name} #{selectedId}` or `{name} Details`).
  - Preserves existing `&larr; Back to {plural}` link for backwards compatibility with prior contracts.
- **Form Screen Integration (`_form_screen_page`)**:
  - Mounts `<Breadcrumbs items={breadcrumbs} />` at the top of form screens.
  - Composes hierarchical path: Overview (`/`) &rarr; Collection (`/{list_screen.id}` when available) &rarr; Action (`Edit {name}` or `New {name}`).
  - Preserves existing `&larr; Back to {plural}` link.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` and exported in `codegen.__init__` as `render_breadcrumbs_component`.

## Generated Accessible EmptyState Component & Screen Zero-State Integrations (R-307)

`NextjsWebAdapter` provides a standardized, accessible empty state presentation across generated Next.js web applications:

- **Reusable EmptyState Component (`apps/web/components/empty-state.tsx`)**:
  - Conforms to WAI-ARIA with `role="status"` and `aria-live="polite"` on the container.
  - Built-in accessible vector SVG icons (`"folder"`, `"search"`, `"document"`, `"inbox"`) with `aria-hidden="true"` and `#94a3b8` stroke color, plus custom `React.ReactNode` support.
  - Action button/link dispatch:
    - Primary action renders `<Link>` when `href` is supplied, or `<button>` when `onClick` is supplied (styled with `#2563eb` accent).
    - Secondary action renders `<Link>` or `<button>` with outline styling (`#ffffff` background, `1px solid #cbd5e1`).
  - Exports typed interfaces `EmptyStateAction` and `EmptyStateProps`.
  - Inline styled using platform design tokens (`#0f172a`, `#64748b`, `#2563eb`, `#cbd5e1`, `#ffffff`).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` and exported in `codegen.__init__` as `render_empty_state_component`.

## Generated Collection Screen JSON Data Export & Bulk Selection Export Controls (R-308)

`NextjsWebAdapter` adds formatted JSON data export controls across generated collection screens:

- **JSON Data Export Helper (`handleExportJson`)**:
  - Emits `handleExportJson(selectedOnly: boolean = false)` in `_collection_screen_page`.
  - Filters loaded records against `checkedIds` when `selectedOnly=true`, or exports all loaded records (`data ?? []`).
  - Formats JSON payload via `JSON.stringify(itemsToExport, null, 2)` with 2-space indentation.
  - Generates download blob using `application/json;charset=utf-8;` MIME type.
  - Triggers browser download with filename formatted as `{plural.lower()}_export.json`.
  - Cleans up Object URL memory lifecycle via `URL.revokeObjectURL(url)`.
  - Dispatches feedback toast notification via `toast.info("Exported JSON successfully")`.
- **Top Toolbar & Contextual Bulk Action Bar Integration**:
  - Top toolbar renders an accessible `Export JSON` button beside `Export CSV` (`disabled={!data || data.length === 0}`).
  - Bulk action bar renders an accessible `Export JSON ({checkedIds.length})` button when items are selected.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.

## Generated Accessible Reusable Pagination Component (R-309)

`NextjsWebAdapter` emits a standalone, accessible, reusable Pagination component (`apps/web/components/pagination.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `PaginationProps` interface:
    - `page: number`: Current active page index (1-based).
    - `pageSize: number`: Items per page.
    - `total: number`: Total number of records across all pages.
    - `totalPages: number`: Calculated total number of pages.
    - `onPageChange: (page: number) => void`: Callback for page navigation.
    - `onPageSizeChange?: (pageSize: number) => void`: Optional callback for page size changes.
    - `pageSizeOptions?: number[]`: Array of selectable page sizes (defaults to `[10, 25, 50, 100]`).
    - `disabled?: boolean`: Disables all controls when loading or performing mutations.
    - `compact?: boolean`: Compact mode for constrained spaces (drawers, cards, subcollections).
    - `itemLabel?: string`: Custom label for item counts (e.g. "records", "posts").
- **WAI-ARIA 1.2 Compliance & Keyboard Usability**:
  - Outer container is `<nav aria-label="Pagination">`.
  - Previous and Next buttons have explicit `aria-label="Previous page"` and `aria-label="Next page"`.
  - Active page number button receives `aria-current="page"`.
  - Page size select is labelled by `<label htmlFor="pageSizeSelect">` with `aria-label="Select page size"`.
  - Dynamic ellipsis calculation (`getPageNumbers`) shows direct jump buttons for reachable pages and `...` indicators for large page counts.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/pagination.tsx` and exported in `codegen.__init__` as `render_pagination_component`.

## Generated Accessible Reusable Tabs Component (R-310)

`NextjsWebAdapter` emits a standalone, accessible, reusable Tabs component (`apps/web/components/tabs.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `TabItem` interface:
    - `id: string`: Unique identifier for the tab.
    - `label: string`: Human-readable label displayed on the tab button.
    - `badge?: string | number`: Optional count badge displayed alongside tab label.
    - `disabled?: boolean`: Disables selection and keyboard focus for this tab.
  - Exports `TabsProps` interface:
    - `tabs: TabItem[]`: List of tab items.
    - `activeTab: string`: Currently active tab ID.
    - `onChange: (tabId: string) => void`: Callback when tab is changed.
    - `variant?: "line" | "pills"`: Visual styling variant (defaults to `"line"`).
    - `ariaLabel?: string`: Accessible label for the `<nav role="tablist">` container (defaults to `"Tabs"`).
    - `className?: string`: Optional custom CSS class name.
  - Exports `TabPanelProps` interface:
    - `id: string`: Matching tab ID corresponding to `TabItem.id`.
    - `activeTab: string`: Currently active tab ID.
    - `children: React.ReactNode`: Tab panel body content.
    - `className?: string`: Optional custom CSS class name.
- **WAI-ARIA 1.2 Tabs Compliance & Keyboard Usability**:
  - Tablist container: `<nav role="tablist" aria-orientation="horizontal">`.
  - Tab buttons: `<button role="tab" id={`tab-${tab.id}`} aria-controls={`tabpanel-${tab.id}`} aria-selected={isActive} tabIndex={isActive ? 0 : -1}>`.
  - Tab panel container: `<div role="tabpanel" id={`tabpanel-${id}`} aria-labelledby={`tab-${id}`} hidden={activeTab !== id}>`.
  - Full keyboard navigation:
    - `ArrowRight`: Focuses and activates next non-disabled tab (loops to first).
    - `ArrowLeft`: Focuses and activates previous non-disabled tab (loops to last).
    - `Home`: Focuses and activates first non-disabled tab.
    - `End`: Focuses and activates last non-disabled tab.
    - DOM focus synchronised automatically via `tabRefs.current[nextTab.id]?.focus()`.
- **Styling & Visual Design**:
  - `"line"` variant: Bottom border line indicator (`borderBottom: 2px solid #2563eb` when active, transparent when inactive).
  - `"pills"` variant: Rounded pill background (`background: #2563eb`, `color: #ffffff` when active; hover/slate background when inactive).
  - Badge counter pills with variant-aware color contrast.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/tabs.tsx` and exported in `codegen.__init__` as `render_tabs_component`.

## Generated Collection Table Display Density Toggle (R-311)

`NextjsWebAdapter` enhances generated Next.js collection screens (`_collection_screen_page`) with interactive, accessible table display density controls:

- **Density State & Calculation**:
  - Emits `const [density, setDensity] = useState<"compact" | "comfortable" | "spacious">("comfortable");`
  - Computes `densityPadding`:
    - `"compact"`: `"6px 12px"`
    - `"spacious"`: `"16px 20px"`
    - `"comfortable"` (default): `"12px 16px"`
  - Computes `densityFontSize`:
    - `"compact"`: `13`
    - `"comfortable"` / `"spacious"`: `14`
- **Accessible Toolbar Segmented Control**:
  - Emits an accessible button group in the collection toolbar: `<div role="group" aria-label="Table display density">`.
  - Three toggle buttons: `Compact`, `Comfortable`, `Spacious`.
  - Each button provides `type="button"`, `aria-label="{Density} density"`, and dynamic `aria-pressed={density === ...}`.
  - Active button rendered with dark fill (`#0f172a`, `#ffffff`), inactive with clean border and hover.
- **Table & Row Presentation**:
  - Table element emits `data-density={density}` and `fontSize: densityFontSize`.
  - Table row data cells (`<td>`) dynamically apply `padding: densityPadding` across checkbox, data fields, and action buttons.
  - Strictly preserves backward compatibility for Actions header (`<th style={{ padding: "12px 16px", textAlign: "right", fontWeight: 600, color: "#475569" }}>Actions</th>`).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.

## Generated Accessible Reusable Badge Component (R-312)

`NextjsWebAdapter` emits a standalone, accessible, reusable Badge & Status Pill component (`apps/web/components/badge.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `BadgeVariant = "success" | "warning" | "error" | "info" | "neutral"`.
  - Exports `BadgeSize = "sm" | "md"`.
  - Exports `BadgeProps` interface:
    - `children: React.ReactNode`: Content displayed inside the badge.
    - `variant?: BadgeVariant`: Semantic visual variant (defaults to `"neutral"`).
    - `size?: BadgeSize`: Display size (defaults to `"md"`).
    - `dot?: boolean`: Whether to render a leading status dot indicator (defaults to `false`).
    - `pulse?: boolean`: Whether to add a subtle pulse opacity to the dot (defaults to `false`).
    - `style?: React.CSSProperties`: Optional custom styles.
    - `className?: string`: Optional custom CSS class name.
    - `ariaLabel?: string`: Accessible label for assistive technology.
- **WAI-ARIA Status Semantics & Design**:
  - Renders `<span role="status" aria-label={ariaLabel}>`.
  - Leading status dot rendered with `aria-hidden="true"` and matching variant color.
  - Sizing profiles:
    - `"sm"`: `11px` font size, `1px 6px` padding, `5px` dot.
    - `"md"`: `12px` font size, `2px 8px` padding, `6px` dot.
  - High-contrast enterprise color tokens:
    - `success`: `#dcfce7` bg, `#166534` text, `#bbf7d0` border, `#22c55e` dot.
    - `warning`: `#fef3c7` bg, `#92400e` text, `#fde68a` border, `#f59e0b` dot.
    - `error`: `#fee2e2` bg, `#991b1b` text, `#fecaca` border, `#ef4444` dot.
    - `info`: `#eff6ff` bg, `#1d4ed8` text, `#bfdbfe` border, `#3b82f6` dot.
    - `neutral`: `#f1f5f9` bg, `#475569` text, `#e2e8f0` border, `#94a3b8` dot.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/badge.tsx` and exported in `codegen.__init__` as `render_badge_component`.

## Generated Collection Table Column Visibility Dropdown (R-313)

`NextjsWebAdapter` enhances generated Next.js collection screens (`_collection_screen_page`) with interactive, accessible column visibility dropdown controls:

- **State Management & Minimum Column Guard**:
  - Emits `visibleColumns` state initialized to `true` for all display fields (`useState<Record<string, boolean>>({ ... })`).
  - Emits `showColumnPicker` boolean state.
  - Implements `toggleColumn(colName: string)` with safety guard: prevents hiding the last remaining column if `currentVisible.length <= 1`.
- **Accessible Toolbar Menu**:
  - Emits dropdown trigger button: `<button type="button" aria-haspopup="true" aria-expanded={showColumnPicker} aria-label="Toggle column visibility">`.
  - Dropdown container: `<div role="menu" aria-label="Column visibility options">`.
  - Accessible checkbox label per column: `<input type="checkbox" aria-label="Toggle {Column} column" checked={visibleColumns[col] !== false} onChange={() => toggleColumn(col)} />`.
- **Dynamic Table Rendering**:
  - Conditionally renders `<th>` table headers and `<td>` data cells wrapped in `{visibleColumns[field.name] !== false && (...)}`.
  - Preserves row selection checkboxes, Actions/Details column, and `colSpan` integrity for loading skeletons and empty states.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.

## Generated Accessible Reusable Tooltip Component (R-314)

`NextjsWebAdapter` emits a standalone, accessible, reusable Tooltip component (`apps/web/components/tooltip.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `TooltipPosition = "top" | "bottom" | "left" | "right"`.
  - Exports `TooltipProps` interface:
    - `content: React.ReactNode`: Content displayed in the floating tooltip popup.
    - `children: React.ReactElement`: Trigger element wrapped by the tooltip.
    - `position?: TooltipPosition`: Placement direction (defaults to `"top"`).
    - `delayMs?: number`: Hover delay before showing (defaults to `200ms`).
    - `className?: string`: Optional custom CSS class name.
    - `style?: React.CSSProperties`: Optional container custom styling.
- **WAI-ARIA 1.2 Tooltip Semantics**:
  - Generates dynamic unique ID via `useId()`.
  - Clones trigger child element with `aria-describedby={visible ? tooltipId : undefined}`.
  - Tooltip container renders `<span id={tooltipId} role="tooltip">`.
  - Handles both mouse hover (`onMouseEnter`/`onMouseLeave`) and keyboard focus (`onFocus`/`onBlur`).
  - Dismisses on `Escape` keydown when tooltip is visible.
  - Position styling offsets for `"top"`, `"bottom"`, `"left"`, and `"right"`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/tooltip.tsx` and exported in `codegen.__init__` as `render_tooltip_component`.

### 15. Accessible Reusable Card Component (`components/card.tsx`, R-315)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Card component (`apps/web/components/card.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `CardVariant = "default" | "bordered" | "flat" | "elevated"`.
  - Exports `CardPadding = "none" | "sm" | "md" | "lg"`.
  - Compound components exported: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`.
  - Exports `CardProps`, `CardHeaderProps`, `CardTitleProps`, `CardDescriptionProps`, `CardContentProps`, and `CardFooterProps` interfaces.
- **Polymorphic Elements & Semantic HTML**:
  - `Card` supports `as?: "div" | "article" | "section"` (defaults to `"div"`).
  - `CardTitle` supports `as?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "div"` (defaults to `"h3"`).
- **Interactive Click & Keyboard Accessibility**:
  - When `onClick` is provided, automatically adds `role="button"`, `tabIndex={0}`, hover shadow transitions, and keyboard triggers (`Enter` and `Space`).
  - Supports `ariaLabel` / `aria-label` pass-through.
- **Compound Subcomponents & Layout Slots**:
  - `CardHeader` provides title, description, and right-aligned `action` slot.
  - `CardFooter` provides alignment presets (`"left" | "right" | "between" | "center"`).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/card.tsx` and exported in `codegen.__init__` as `render_card_component`.

### 16. Accessible Reusable Alert Component (`components/alert.tsx`, R-316)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Alert component (`apps/web/components/alert.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `AlertVariant = "info" | "success" | "warning" | "error"`.
  - Compound components exported: `Alert`, `AlertTitle`, `AlertDescription`.
  - Exports `AlertProps`, `AlertTitleProps`, and `AlertDescriptionProps` interfaces.
- **WAI-ARIA Alert & Status Semantics**:
  - Applies `role="alert"` and `aria-live="assertive"` for `"error"` variant.
  - Applies `role="status"` and `aria-live="polite"` for `"info"`, `"success"`, and `"warning"` variants.
- **Built-in Accessible Vector Icons**:
  - SVG icons with `aria-hidden="true"` rendered automatically matching the active variant color.
- **Dismissible Behavior & Action Slots**:
  - `dismissible` boolean with accessible close button (`aria-label="Dismiss alert"`) and `onDismiss` callback.
  - `action` slot for contextual buttons or links.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/alert.tsx` and exported in `codegen.__init__` as `render_alert_component`.

### 17. Accessible Reusable Skeleton Loader Component (`components/skeleton.tsx`, R-317)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Skeleton component (`apps/web/components/skeleton.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `SkeletonVariant = "text" | "circular" | "rectangular" | "rounded"`.
  - Exports `SkeletonAnimation = "pulse" | "wave" | "none"`.
  - Compound components exported: `Skeleton`, `SkeletonText`, `SkeletonCard`, `SkeletonTable`.
  - Exports `SkeletonProps`, `SkeletonTextProps`, `SkeletonCardProps`, and `SkeletonTableProps` interfaces.
- **WAI-ARIA Loading & Status Semantics**:
  - Applies `role="status"`, `aria-busy="true"`, and `aria-live="polite"` to loader containers.
  - Emits visually-hidden screen reader announcement (`<span style={srOnlyStyle}>{ariaLabel}</span>`) with customizable or default `"Loading..."` text.
- **Visual Shapes & Animations**:
  - Supports shapes with tailored border-radius styling (circular 50%, text 4px, rounded 8px, rectangular 0px).
  - Configurable animations (`pulse`, `wave`, `none`) with embedded keyframes.
  - Includes `@media (prefers-reduced-motion: reduce)` media query handling to disable animation for motion-sensitive users.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/skeleton.tsx` and exported in `codegen.__init__` as `render_skeleton_component`.

### 18. Accessible Reusable Drawer / Sheet Component (`components/drawer.tsx`, R-318)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Drawer / Sheet component (`apps/web/components/drawer.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `DrawerPosition = "left" | "right" | "top" | "bottom"`.
  - Exports `DrawerSize = "sm" | "md" | "lg" | "xl" | "full"`.
  - Compound components exported: `Drawer`, `DrawerHeader`, `DrawerTitle`, `DrawerDescription`, `DrawerContent`, `DrawerFooter`.
  - Exports `DrawerProps`, `DrawerHeaderProps`, `DrawerTitleProps`, `DrawerDescriptionProps`, `DrawerContentProps`, and `DrawerFooterProps` interfaces.
- **WAI-ARIA 1.2 Modal Dialog Semantics**:
  - Emits `role="dialog"` and `aria-modal="true"` on root backdrop container.
  - Dynamically binds `aria-labelledby` and `aria-describedby` via `useId()`.
  - Includes accessible close button with `aria-label="Close drawer"`.
- **Keyboard & Interaction Handling**:
  - Dismisses on `Escape` keydown when open (`closeOnEscape`).
  - Dismisses on backdrop overlay click (`closeOnBackdropClick`).
  - Locks background scroll (`document.body.style.overflow = "hidden"`) during visibility.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
### 19. Accessible Reusable Avatar Component (`components/avatar.tsx`, R-319)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Avatar component (`apps/web/components/avatar.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `AvatarShape = "circle" | "rounded" | "square"`.
  - Exports `AvatarSize = "xs" | "sm" | "md" | "lg" | "xl"`.
  - Exports `AvatarStatus = "online" | "offline" | "busy" | "away"`.
  - Compound components exported: `Avatar`, `AvatarGroup`.
  - Exports `AvatarProps` and `AvatarGroupProps` interfaces.
- **WAI-ARIA Image & Status Semantics**:
  - Root container emits `role="img"` with descriptive `aria-label` derived from `alt`, `name`, or status.
  - Presence indicator dot emits decorative or semantic status info with high-contrast borders.
  - Fallback silhouettes include `aria-hidden="true"` SVG graphics.
- **3-Tier Fallback Cascade**:
  - Image element with native `onError` transition to fallback on network error or broken source.
  - Initials fallback with deterministic background color hashing from `name` prop.
  - Generic vector silhouette fallback for anonymous users when no `name` or `src` is provided.
- **Compound AvatarGroup**:
  - Supports overlapping negative margins (`marginLeft: -8px` to `-12px` according to size).
  - Configurable `max` limit with `+N` excess overflow badge.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/avatar.tsx` and exported in `codegen.__init__` as `render_avatar_component`.

### 20. Accessible Reusable Toggle Switch Component (`components/toggle.tsx`, R-320)

`NextjsWebAdapter` emits a standalone, accessible, reusable Toggle Switch component (`apps/web/components/toggle.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Exports `ToggleSize = "sm" | "md" | "lg"`.
  - Exports `ToggleProps` interface supporting controlled (`checked`, `onChange`) and uncontrolled (`defaultChecked`) operation modes.
  - Exports `Toggle` component and `ToggleSwitch` alias.
- **WAI-ARIA 1.2 Switch Semantics & Keyboard Navigation**:
  - Track emits `role="switch"`, `aria-checked={isChecked}`, `aria-disabled={disabled}`, `tabIndex={disabled ? -1 : 0}`.
  - Full keyboard accessibility: handles `Space` and `Enter` key presses with `e.preventDefault()`.
  - Binds optional `label` and `description` slots with `useId()` (`aria-labelledby`, `aria-describedby`).
- **Visual Design & Sizes**:
  - Standardized size configurations:
    - `sm`: 32x18px track, 14px thumb, 14px translate.
    - `md`: 44x24px track, 20px thumb, 20px translate.
    - `lg`: 56x30px track, 26px thumb, 26px translate.
  - Smooth CSS transitions (`0.2s ease`) on track background color and thumb translation.
  - Accessible focus outline and disabled states.
- **HTML Form Integration**:
  - Hidden `<input type="hidden" name={name} value={isChecked ? "true" : "false"} />` rendered when `name` prop is provided.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/toggle.tsx` and exported in `codegen.__init__` as `render_toggle_component`.

### 21. Accessible Reusable Accordion Component (`components/accordion.tsx`, R-321)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Accordion component (`apps/web/components/accordion.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Compound components exported: `Accordion`, `AccordionItem`, `AccordionTrigger`, `AccordionContent`.
  - Exports `AccordionType = "single" | "multiple"`.
  - Exports `AccordionVariant = "default" | "bordered" | "separated"`.
  - Exports `AccordionProps`, `AccordionItemProps`, `AccordionTriggerProps`, `AccordionContentProps` interfaces.
  - Supported controlled (`value`, `onValueChange`) and uncontrolled (`defaultValue`) operation modes.
- **WAI-ARIA 1.2 Accordion Semantics & Interactions**:
  - Trigger button emits `aria-expanded={isOpen}`, `aria-controls={contentId}`, and dynamic `id`.
  - Content panel emits `role="region"`, `id={contentId}`, `aria-labelledby={triggerId}`, and `hidden={!isOpen}`.
  - Animated chevron indicator emits `aria-hidden="true"` with CSS transform `rotate(180deg)` when open.
  - Supports collapsible configuration in single mode (allowing all sections to be collapsed).
  - Supports disabled items with proper `disabled` and `aria-disabled` handling.
- **Visual Styling & Variants**:
  - `default`: Clean bottom border divider between items.
  - `bordered`: Enclosing border around the accordion with internal separators.
  - `separated`: Distinct floating card-style items separated by vertical gaps.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/accordion.tsx` and exported in `codegen.__init__` as `render_accordion_component`.

### 22. Accessible Reusable Dropdown Menu Component (`components/dropdown-menu.tsx`, R-322)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Dropdown Menu component (`apps/web/components/dropdown-menu.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Compound components exported: `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuSeparator`, `DropdownMenuLabel`.
  - Exports `DropdownMenuAlign = "start" | "end" | "center"`.
  - Exports `DropdownMenuSide = "top" | "bottom" | "left" | "right"`.
  - Exports `DropdownMenuProps`, `DropdownMenuTriggerProps`, `DropdownMenuContentProps`, `DropdownMenuItemProps`, `DropdownMenuSeparatorProps`, `DropdownMenuLabelProps`.
- **WAI-ARIA 1.2 Menu Semantics & Interactions**:
  - Trigger emits `aria-haspopup="menu"`, `aria-expanded={isOpen}`, `aria-controls={contentId}`.
  - Content container emits `role="menu"`, `id={contentId}`, `aria-labelledby={triggerId}`, `tabIndex={-1}`.
  - Items emit `role="menuitem"`, `aria-disabled={disabled ? "true" : undefined}`, `tabIndex={disabled ? -1 : 0}`.
  - Separators emit `role="separator"`.
  - Full keyboard navigation: `ArrowDown` and `ArrowUp` cycle through enabled items, `Home` moves to first, `End` to last, `Escape` closes menu and restores trigger focus, `Enter`/`Space` activates item action.
  - Outside click dismiss listener via `document.addEventListener("mousedown")`.
- **Styling, Actions & Variants**:
  - Positions calculated for all `side` and `align` combinations with customizable `sideOffset`.
  - Supports `disabled` states with visual cursor/color changes and keyboard skipping.
  - Supports `destructive` action styling (red text and light-red hover backgrounds).
  - Supports optional `shortcut` monospace badge and `icon` slots.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/dropdown-menu.tsx` and exported in `codegen.__init__` as `render_dropdown_menu_component`.

### 23. Accessible Reusable Popover Component (`components/popover.tsx`, R-323)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Popover component (`apps/web/components/popover.tsx`):

- **Component Architecture & TypeScript Interfaces**:
  - Emitted with `"use client"` directive.
  - Compound components exported: `Popover`, `PopoverTrigger`, `PopoverContent`, `PopoverClose`, `PopoverArrow`.
  - Exports `PopoverAlign = "start" | "end" | "center"`.
  - Exports `PopoverSide = "top" | "bottom" | "left" | "right"`.
  - Exports `PopoverProps`, `PopoverTriggerProps`, `PopoverContentProps`, `PopoverCloseProps`, `PopoverArrowProps`.
  - Supports controlled (`open`, `onOpenChange`) and uncontrolled (`defaultOpen`) operation modes.
- **WAI-ARIA Dialog Semantics & Interactions**:
  - Trigger emits `aria-haspopup="dialog"`, `aria-expanded={isOpen}`, `aria-controls={contentId}`.
  - Content container emits `role="dialog"`, `aria-modal="true"`, `id={contentId}`, `aria-labelledby={triggerId}`.
  - Outside click dismiss listener via `document.addEventListener("mousedown")`.
  - Escape key dismiss listener with focus restoration to trigger button.
  - `PopoverClose` button emits accessible `aria-label="Close popover"`.
  - `PopoverArrow` decorative pointing indicator emits `aria-hidden="true"`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/popover.tsx` and exported in `codegen.__init__` as `render_popover_component`.

### 24. Design Tokens & CSS Custom Properties Theming Engine (`styles/tokens.css`, R-324)

`NextjsWebAdapter` emits a standalone, production-grade Design Tokens and CSS custom properties theming engine (`apps/web/styles/tokens.css`):

- **Color Palettes (Light & Dark Themes)**:
  - Default Light Mode (`:root`): semantic colors for Brand/Primary (`--color-primary`, `--color-primary-hover`, `--color-primary-focus`, `--color-primary-subtle`, `--color-primary-foreground`), Secondary, Accent, Neutral Scale (50 to 900), Surfaces & Backgrounds (`--color-background`, `--color-surface`, `--color-surface-subtle`, `--color-surface-elevated`), Typography (`--color-text`, `--color-text-muted`, `--color-text-subtle`, `--color-text-inverse`), Borders, and Status Feedback (Success, Warning, Danger/Error, Info).
  - Dark Mode Overrides: activated via `[data-theme="dark"]`, `:root.dark`, `body.dark`, and `@media (prefers-color-scheme: dark)` with `:root:not([data-theme="light"])` user override support.
- **Scale Tokens**:
  - Spacing scale: `--space-0` through `--space-24` (0 to 6rem / 96px).
  - Typography scale: `--font-sans`, `--font-mono`, `--font-size-xs` through `--font-size-4xl`, weights light to bold, line heights none to loose.
  - Border Radii: `--radius-none` through `--radius-full`.
  - Elevation Shadows: `--shadow-none` through `--shadow-xl`, plus `--shadow-inner`.
  - Z-Index Scale: `--z-hide` (-1) through `--z-tooltip` (1700).
  - Motion & Transitions: `--transition-fast`, `--transition-normal`, `--transition-slow`.
- **Accessibility & Reduced Motion**:
  - Automatically resets animation and transition durations to `0ms` under `@media (prefers-reduced-motion: reduce)`.
- **Global Integration**:
  - Imported into `apps/web/app/globals.css` (`@import "../styles/tokens.css";`) with unified root typography and box-sizing rules.
  - Loaded via `app/layout.tsx`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero runtime npm dependencies.
  - Registered in `NextjsWebAdapter.generate()` and exported in `codegen.__init__` as `render_design_tokens` and `render_globals_css`.

### 25. Theme Switcher & Mode Toggle Component (`components/theme-toggle.tsx`, R-325)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Theme Switcher component (`apps/web/components/theme-toggle.tsx`):

- **Architecture & State Management**:
  - Emitted with `"use client"` directive.
  - Exports `ThemeMode = "light" | "dark" | "system"` and `ResolvedTheme = "light" | "dark"`.
  - `ThemeProvider` context provider coordinates `theme` mode, resolved active theme, `localStorage` persistence, and listens to `window.matchMedia("(prefers-color-scheme: dark)")` for dynamic system shifts.
  - `useTheme()` hook provides `{ theme, resolvedTheme, setTheme, toggleTheme }`.
- **Components & Accessibility**:
  - `ThemeToggle`: Compact button component with built-in vector SVG Sun / Moon icons (`aria-hidden="true"`), size presets (`"sm"` | `"md"` | `"lg"`), accessible dynamic `aria-label`, and keyboard activation.
  - `ThemeSelect`: Accessible segmented radio control with WAI-ARIA `role="radiogroup"`, `role="radio"`, and `aria-checked` semantics.
  - `ThemeScript`: Head injection script component executing before DOM hydration to eliminate Flash of Unstyled Content (FOUC).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/theme-toggle.tsx` and exported in `codegen.__init__` as `render_theme_toggle_component`.

### 26. Accessible Reusable Dialog / Modal Component (`components/dialog.tsx`, R-326)

`NextjsWebAdapter` emits a standalone, accessible, reusable compound Dialog / Modal component (`apps/web/components/dialog.tsx`):

- **Architecture & Compound Subcomponents**:
  - Emitted with `"use client"` directive.
  - Compound parts: `Dialog` (root provider), `DialogTrigger`, `DialogPortal`, `DialogOverlay`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogBody`, `DialogFooter`, `DialogClose`.
  - Supports both controlled (`open`, `onOpenChange`) and uncontrolled (`defaultOpen`) usage.
  - `useDialog()` hook exposes `{ open, setOpen, titleId, descriptionId, closeOnEscape, closeOnBackdropClick, triggerRef }`.
- **WAI-ARIA Semantics & Accessibility**:
  - Modal container features `role="dialog"`, `aria-modal="true"`, `tabIndex={-1}`, and dynamic `aria-labelledby` / `aria-describedby` wiring.
  - Listens for `Escape` keydown to dismiss with configurable `closeOnEscape` (default `true`).
  - Backdrop overlay click dismiss with configurable `closeOnBackdropClick` (default `true`).
  - Focus restoration returns DOM focus to `triggerRef` when closed.
  - Background document body scroll lock prevents scrolling while modal is active.
  - Includes optional accessible close button (`aria-label="Close dialog"`) with SVG 'X' icon.
- **Size Presets & Styling**:
  - `sizeMap` presets: `"sm"` (400px), `"md"` (500px), `"lg"` (640px), `"xl"` (768px), `"full"` (min(95vw, 1200px)).
  - Clean elevation styling with smooth backdrop blur (`rgba(15, 23, 42, 0.5)`).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/dialog.tsx` and exported in `codegen.__init__` as `render_dialog_component`.

### 27. Accessible Reusable Form Controls & Input Primitives (`components/form-controls.tsx`, R-327)

`NextjsWebAdapter` emits a standalone, accessible, reusable Form Controls and Input primitives suite (`apps/web/components/form-controls.tsx`):

- **Architecture & Compound Subcomponents**:
  - Emitted with `"use client"` directive.
  - Subcomponents: `Input` (`forwardRef`), `Textarea` (`forwardRef`), `Select` (`forwardRef`), `Checkbox` (`forwardRef`), `RadioGroup`, `Radio`, `Label`, `FormField`, `FormMessage`, `FormHelperText`.
  - Size variants: `InputSize = "sm" | "md" | "lg"`.
- **Input & Textarea Features**:
  - `Input` supports size presets, left `prefix` slot, right `suffix` slot, and optional clear button (`onClear` with `aria-label="Clear input"`).
  - `Textarea` supports auto/custom rows and live character counter (`showCount`, `maxLength`) with amber warning indicator at 90% threshold.
- **Select, Checkbox, & Radio Group**:
  - `Select` supports options array rendering, placeholder support (`disabled hidden`), custom SVG chevron indicator, and disabled states.
  - `Checkbox` supports checked, unchecked, and indeterminate (`el.indeterminate`) states with focus rings.
  - `RadioGroup` and `Radio` coordinate via `RadioGroupContext`, providing WAI-ARIA `role="radiogroup"`, `role="radio"`, `aria-checked`, and full keyboard arrow navigation (`ArrowDown`, `ArrowUp`, `ArrowRight`, `ArrowLeft`).
- **Form Layout, Validation, & WAI-ARIA**:
  - `Label` supports required asterisk indicator (`*`, `aria-hidden="true"`).
  - `FormField` coordinates automated ID generation via `useId()`, linking `htmlFor` on `Label` and passing `aria-invalid` and `aria-describedby` to children.
  - `FormMessage` renders validation errors with `role="alert"` and `aria-live="polite"`.
  - `FormHelperText` renders descriptive hints.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/form-controls.tsx` and exported in `codegen.__init__` as `render_form_controls_component`.

### 28. Accessible Reusable Date Picker Component (`components/date-picker.tsx`, R-328)

`NextjsWebAdapter` emits a standalone, accessible, reusable Date Picker and Calendar component suite (`apps/web/components/date-picker.tsx`):

- **Architecture & Components**:
  - Emitted with `"use client"` directive.
  - Exports `DatePicker` (`forwardRef`), `Calendar`, `formatDate`, `isSameDay`, `isToday`.
  - Type definitions: `DateFormatter`, `CalendarProps`, `DatePickerProps`.
- **Calendar Month Grid & Traversal**:
  - Month and year navigation header with previous/next month (`<`, `>`) and year (`<<`, `>>`) controls with accessible `aria-label`s.
  - Weekday headers with `<abbr>` and accessible full day labels (`Su` - `Sa`).
  - Calendar day grid with WAI-ARIA `role="grid"`, `role="row"`, `role="gridcell"`, `aria-selected`, `aria-current="date"`, and `aria-disabled`.
  - Full keyboard navigation: Left/Right Arrow (+/- 1 day), Up/Down Arrow (+/- 7 days), PageUp/PageDown (+/- 1 month or year with Shift), Home/End (start/end of week), Enter/Space (select date).
  - Quick-select "Today" action and optional "Clear" button.
- **DatePicker Trigger & Floating Popover**:
  - Accessible trigger button styled as input field with calendar SVG icon, `aria-haspopup="dialog"`, `aria-expanded`, formatted date text, and placeholder fallback.
  - Clearable button affordance (`clearable` with `aria-label="Clear date"`).
  - Floating popover container with `role="dialog"`, `aria-modal="false"`, `aria-label="Choose date"`, dismiss on outside click, and dismiss on Escape with focus restoration.
  - Placement styling (`bottom-start`, `bottom-end`, `top-start`, `top-end`).
  - Error and helper text rendering with `role="alert"` and `aria-describedby` wiring.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React, TypeScript, and CSS custom properties).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/date-picker.tsx` and exported in `codegen.__init__` as `render_date_picker_component`.

### 29. Accessible Reusable Data Grid / Table Component (`components/data-grid.tsx`, R-329)

`NextjsWebAdapter` emits a standalone, accessible, reusable Data Grid and Table component suite (`apps/web/components/data-grid.tsx`):

- **Architecture & Generic Typing**:
  - Emitted with `"use client"` directive.
  - Exports `DataGrid` component with generic row type `<T extends Record<string, any>>`.
  - Type definitions: `ColumnDef<T>`, `DataGridProps<T>`, `SortDirection`, `SortState`, `DataGridDensity`.
- **Sortable Column Headers**:
  - Column headers support interactive sort toggling with cycle (`asc` -> `desc` -> `none`).
  - WAI-ARIA `aria-sort` semantics (`"ascending"`, `"descending"`, or `"none"`).
  - Visual sort indicator SVGs (up arrow, down arrow, and dual arrows for unsorted sortable state).
  - Full keyboard trigger support (`Enter` and `Space` keys).
- **Row Selection & Checkboxes**:
  - Select-all header checkbox with indeterminate state tracking via `ref.indeterminate`.
  - Row selection checkboxes with `aria-label="Select row N"`.
  - Selected rows receive `aria-selected={true}` and brand-tinted background highlight.
  - `onSelectionChange` callback returning `selectedKeys` and `selectedRows`.
- **Display Density & Layout Modes**:
  - Three display density presets: `"compact"` (6px 12px padding, 13px font), `"comfortable"` (12px 16px padding, 14px font), and `"spacious"` (16px 20px padding, 15px font).
  - Sticky header support (`stickyHeader = true`) with fixed position `<thead>` and border preservation.
  - Striped rows support (`striped = true`) for alternating row readability.
  - Hover highlight transitions on rows (`hoverable = true`).
- **Loading Skeleton & Empty States**:
  - Integrated loading skeleton state with animated pulsing rows, `role="status"`, and `aria-busy="true"`.
  - Fallback empty state rendering when data array is empty.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React, TypeScript, and CSS custom properties).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/data-grid.tsx` and exported in `codegen.__init__` as `render_data_grid_component`.

### 30. Accessible Command Palette / Search Menu Component (`components/command-palette.tsx`, R-330)

`NextjsWebAdapter` emits a standalone, accessible, reusable Command Palette and Search Menu component suite (`apps/web/components/command-palette.tsx`):

- **Architecture & Component Exports**:
  - Emitted with `"use client"` directive.
  - Exports `CommandPalette` component and default export.
  - Type definitions: `CommandItem`, `CommandGroup`, `CommandPaletteProps`.
- **Global Shortcut & Search Filtering**:
  - Global `Cmd+K` / `Ctrl+K` keyboard shortcut listener (`triggerShortcut?: boolean`, default `true`) to toggle palette visibility.
  - Instant query filtering across item `label`, `description`, `group`, and `keywords`.
  - Search input with clear button affordance and ESC badge.
- **Keyboard Navigation & Traversal**:
  - Full keyboard traversal: `ArrowDown`/`ArrowUp` (with boundary wrapping and disabled item skipping), `Home`/`End` (jump to first/last selectable item), `Enter` (select active item), `Escape` (dismiss and restore previous focus).
  - Automated list scrolling via `scrollIntoView({ block: "nearest" })`.
- **WAI-ARIA Combobox Semantics**:
  - Modal overlay: `role="dialog"`, `aria-modal="true"`, `aria-label="Command palette"`.
  - Search input: `role="combobox"`, `aria-autocomplete="list"`, `aria-expanded="true"`, `aria-haspopup="listbox"`, `aria-controls`, `aria-activedescendant`.
  - Results container: `role="listbox"`, `aria-label="Commands"`.
  - Items: `role="option"`, unique `id`, `aria-selected`, `aria-disabled`.
  - Groups: `role="group"` with `aria-labelledby` linking group headings.
- **Visual Features & Polish**:
  - Shortcut badges (`<kbd>`) on command items.
  - Configurable `emptyMessage` fallback when no items match search query.
  - Modal backdrop with dark tint, `backdropFilter: "blur(4px)"`, and body scroll lock management.
  - Footer navigation hints (`↑↓ navigate`, `↵ select`, `esc close`).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React, TypeScript, and CSS custom properties).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/command-palette.tsx` and exported in `codegen.__init__` as `render_command_palette_component`.

### 31. Accessible Reusable Slider & Range Component (`components/slider.tsx`, R-331)

`NextjsWebAdapter` emits a standalone, accessible, reusable Slider and Range component suite (`apps/web/components/slider.tsx`):

- **Architecture & Component Exports**:
  - Emitted with `"use client"` directive.
  - Exports `Slider` component and default export.
  - Type definitions: `SliderOrientation`, `SliderValue`, `SliderMark`, `SliderProps`.
- **Single & Range Selection Modes**:
  - Automatically detects range mode when `value` or `defaultValue` is an array `[min, max]`.
  - Enforces thumb crossover prevention: Thumb 0 is clamped to never exceed Thumb 1; Thumb 1 is clamped to never fall below Thumb 0.
- **Pointer Drag & Interactions**:
  - Pointer events (`onPointerDown`, `pointermove`, `pointerup`) on track and thumbs with `touch-action: none`.
  - Calculates proportional value from client coordinates matching orientation (`horizontal` or `vertical`).
- **Keyboard Navigation & Boundary Snapping**:
  - `ArrowRight` / `ArrowUp`: increments by `step`.
  - `ArrowLeft` / `ArrowDown`: decrements by `step`.
  - `PageUp`: increments by large step (10x step).
  - `PageDown`: decrements by large step (10x step).
  - `Home`: snaps to minimum valid value.
  - `End`: snaps to maximum valid value.
- **WAI-ARIA Slider Semantics**:
  - Thumbs: `role="slider"`, `tabIndex={disabled ? -1 : 0}`.
  - `aria-valuenow`, `aria-valuemin`, `aria-valuemax`.
  - `aria-orientation="horizontal" | "vertical"`.
  - `aria-disabled={disabled}`.
  - `aria-label` and `aria-valuetext` formatting.
- **Visual Marks & Value Badge**:
  - Tick mark dots and labels (`marks`) positioned along track.
  - Formatted value badge (`showValue`, `formatValue`).
  - Active highlight fill and thumb focus ring.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React, TypeScript, and CSS custom properties).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/slider.tsx` and exported in `codegen.__init__` as `render_slider_component`.

---

## 32. Generated Accessible Reusable Progress & Spinner Component (R-332)

Next.js web applications generated by OmniStackAI now include a production-grade, accessible Progress indicator and loading animation component suite (`components/progress.tsx`):

- **Architecture & Interfaces**:
  - Exports `ProgressBar` (and `Progress` alias), `CircularProgress`, and `Spinner`.
  - Type definitions: `ProgressVariant`, `ProgressSize`, `ProgressBarProps`, `CircularProgressProps`, `SpinnerProps`.
- **Linear Progress Bar (`ProgressBar`)**:
  - Determinate mode: numeric `value`, `min`, `max`, `showValue`, `formatValue`.
  - Indeterminate mode: continuous animated shimmer/pulse bar when `value` is omitted/undefined.
  - WAI-ARIA progressbar semantics: `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext` (with `aria-valuenow` omitted in indeterminate mode per WAI-ARIA specification).
  - Striped and animated striped gradients (`striped`, `animated`).
  - Size presets (`sm`, `md`, `lg`) and semantic color variants (`default`, `primary`, `success`, `warning`, `error`, `info`).
  - Accessible label support via `label`, `aria-label`, or `aria-labelledby`.
- **Circular Progress Indicator (`CircularProgress`)**:
  - SVG circle with exact mathematical circumference and stroke offset calculations (`2 * Math.PI * radius`).
  - Determinate mode: percentage stroke-dashoffset with smooth CSS transition and `-90deg` start angle.
  - Indeterminate mode: continuous spinning SVG sweep animation.
  - Center label / percentage display (`showValue`, `label`).
- **Accessible Lightweight Spinner (`Spinner`)**:
  - Ultra-lightweight rotating SVG loader circle with `role="status"` and `aria-live="polite"`.
  - Visually hidden screen-reader accessible announcement (`sr-only` span, default "Loading...").
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React, TypeScript, and CSS custom properties).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/progress.tsx` and exported in `codegen.__init__` as `render_progress_component`.

---

## 33. Generated Accessible Reusable Rating & Review Component (R-333)

Next.js web applications generated by OmniStackAI now include a standalone, accessible Rating & Review component suite (`components/rating.tsx`):

- **Architecture & Interfaces**:
  - Exports `Rating` component and default export.
  - Type definitions: `RatingSize`, `RatingIcon`, `RatingProps`.
- **Interactive Rating Selection & Hover Preview**:
  - Hover preview (`onHover`, temporary score highlight on pointer movement, reset on mouse leave).
  - Click-to-set rating selection (`onChange`).
  - Fractional rating support (`allowHalf`) with precise half-increment coordinate detection.
- **Keyboard Navigation & WAI-ARIA Slider Semantics**:
  - `ArrowRight` / `ArrowUp`: increments score by step.
  - `ArrowLeft` / `ArrowDown`: decrements score by step.
  - `Home`: resets to 0; `End`: jumps to maximum score.
  - `role="slider"`, `tabIndex`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`, `aria-readonly`, `aria-disabled`.
- **Built-in Vector Icons**:
  - Inline SVG vector icons (`star`, `heart`, `thumb`) with precise overlay fill clipping for fractional rendering.
  - Read-only (`readOnly`) and disabled (`disabled`) modes.
  - Optional score display formatting (`showScore`, `formatScore`).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/rating.tsx` and exported in `codegen.__init__` as `render_rating_component`.

---

## 34. Generated Accessible Reusable Stepper / Multi-step Wizard Component (R-334)

Next.js web applications generated by OmniStackAI now include a standalone, accessible Stepper / Multi-step Wizard component suite (`components/stepper.tsx`):

- **Architecture & Interfaces**:
  - Exports `Stepper`, `StepContent`, `useStepperState`, and default export.
  - Type definitions: `StepperOrientation`, `StepStatus`, `StepperVariant`, `StepDef`, `StepperProps`, `StepContentProps`, `UseStepperStateOptions`, `UseStepperStateReturn`.
- **Stepper Navigation & Variants**:
  - `StepperOrientation`: `"horizontal"` | `"vertical"`.
  - `StepperVariant`: `"default"` | `"dots"` | `"progress"`.
  - `StepStatus`: `"idle"` | `"active"` | `"completed"` | `"error"`.
  - Built-in SVG indicator icons for completed (check) and error states.
  - Step connectors with completion-proportional progress fill.
  - `useStepperState` hook managing `activeStep`, `goNext`, `goPrev`, `goTo`, `canGoNext`, `canGoPrev`.
- **WAI-ARIA Tablist / Tabpanel Pattern**:
  - `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`, `role="tabpanel"`, `aria-labelledby`, `aria-disabled`.
  - Full keyboard navigation: `ArrowRight`/`Left` (horizontal), `ArrowDown`/`Up` (vertical), `Home`, `End`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/stepper.tsx` and exported in `codegen.__init__` as `render_stepper_component`.

---

## 35. Generated Accessible Reusable File Upload / Dropzone Component (R-335)

Next.js web applications generated by OmniStackAI now include a standalone, accessible File Upload / Dropzone component suite (`components/file-upload.tsx`):

- **Architecture & Interfaces**:
  - Exports `FileUpload` and default export.
  - Type definitions: `FileUploadStatus`, `FileUploadVariant`, `FileEntry`, `FileUploadProps`.
- **Drag-and-Drop & File Constraints**:
  - Drag-over visual feedback on drag enter, leave, and drop events.
  - Click-to-browse file selection via hidden `<input type="file">`.
  - Keyboard trigger (`Enter`, `Space`) to open native file dialog.
  - Validation: MIME types/extensions (`accept`), max file size (`maxSize`), max file count (`maxFiles`).
  - File preview list with formatted file sizes (`formatBytes`), image thumbnail preview, upload progressbar (`role="progressbar"`), and remove button.
  - Avatar variant with circular crop styling and camera overlay icon.
- **WAI-ARIA Accessibility**:
  - `role="button"`, `tabIndex={0}`, `aria-label`, `aria-describedby`, `aria-live="polite"`, `aria-disabled`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/file-upload.tsx` and exported in `codegen.__init__` as `render_file_upload_component`.

---

## 36. Generated Accessible Reusable Timeline / Activity Feed Component (R-336)

Next.js web applications generated by OmniStackAI now include a standalone, accessible Timeline / Activity Feed component suite (`components/timeline.tsx`):

- **Architecture & Interfaces**:
  - Exports `Timeline` and default export.
  - Type definitions: `TimelineVariant`, `TimelineItemStatus`, `TimelineItem`, `TimelineProps`.
- **Timeline Variants & Connectors**:
  - `TimelineVariant`: `"default"` | `"compact"` | `"centered"`.
  - `TimelineItemStatus`: `"pending"` | `"active"` | `"completed"` | `"error"` | `"warning"`.
  - Vertical connector lines between entries with status-colored fill (green for completed steps).
  - Centered variant featuring alternating left and right item placement.
  - Compact variant with tightened spacing for dense event feeds.
  - Timestamp rendering inside semantic `<time>` element.
  - Custom icon slot override (`item.icon`) and action button slot (`item.action`).
- **Built-in Status Icons & WAI-ARIA Semantics**:
  - Built-in inline vector status icons: completed (check circle), error (X circle), warning (alert circle), active (pulsing dot), pending (clock).
  - `role="list"` on timeline container, `role="listitem"` on each item, `aria-label`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/timeline.tsx` and exported in `codegen.__init__` as `render_timeline_component`.

---

## 37. Generated Accessible Futuristic Reusable Stat & Metric KPI Card Component (R-337)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Stat & Metric KPI Card component suite (`components/stat-card.tsx`):

- **Architecture & Interfaces**:
  - Exports `StatCard` and default export.
  - Subcomponents: `StatCard.Group`, `StatCard.TrendDelta`, `StatCard.Sparkline`.
  - Type definitions: `StatCardVariant`, `StatCardTrend`, `StatCardProps`, `StatCardGroupProps`, `TrendDeltaProps`, `SparklineProps`.
- **Variants & Visual Hierarchy**:
  - `StatCardVariant`: `"default"` | `"glass"` | `"outline"` | `"accent"`.
  - Glassmorphic backdrop blur styling (`backdrop-filter: blur(12px)`), futuristic border highlights, and hover elevation micro-interactions.
  - Directional trend delta pill (`StatCard.TrendDelta`) supporting `"up"`, `"down"`, and `"neutral"` with customized inline SVG directional arrows and delta pill color accents (emerald, rose, slate).
- **Pure Mathematical SVG Sparklines (`StatCard.Sparkline`)**:
  - Standalone zero-dependency SVG sparkline generator using Catmull-Rom cubic bezier (`C`) control point calculation (`computeSplinePath`).
  - Smooth area fill `<linearGradient>` with gradient fade to transparent.
  - Interactive pointer hover cursor vertical guide rule and tooltip overlay rendering data coordinates without external charting libraries.
- **WAI-ARIA Accessibility & Semantic Structure**:
  - Semantic `<section>` or `<article>` container with `aria-label`, `tabIndex={0}`, role semantics (`role="region"`), and clear keyboard navigation support.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/stat-card.tsx` and exported in `codegen.__init__` as `render_stat_card_component`.

---

## 38. Generated Accessible Reusable Hierarchical Tree View Component (R-338)

Next.js web applications generated by OmniStackAI now include a standalone, accessible Hierarchical Tree View component suite (`components/tree-view.tsx`):

- **Architecture & Interfaces**:
  - Exports `TreeView` and default export.
  - Type definitions: `TreeNode`, `TreeViewVariant`, `TreeViewProps`.
  - Node schema: `id`, `label`, optional `icon`, recursive `children`, `disabled`, `badge`, and arbitrary `data` payload.
- **Visual Presentation & Variants**:
  - `TreeViewVariant`: `"default"` | `"bordered"` | `"ghost"` | `"lines"`.
  - Hierarchical guide lines (`showLines` or `variant="lines"`): vertical dotted/solid connector lines running through children containers with horizontal L-shaped branch ticks leading to each item.
  - Smooth Chevron rotation animations on folder toggle (`rotate(90deg)` transition).
  - Contextual default icons: `FolderClosedIcon` (collapsed folder), `FolderOpenIcon` (expanded folder), and `FileTextIcon` (leaf node).
- **Search Filtering & Branch Auto-Expansion**:
  - Built-in search input (`showSearch`) or controlled `filter` prop.
  - Automatically matches nodes by label and retains matching branches.
  - Automatically expands ancestor nodes so matching leaf items are immediately visible.
  - Substring highlight using semantic `<mark>` styling.
- **Selection Modes**:
  - Single-select mode: `selectedId` with `onSelect(node)` callback.
  - Multi-select mode: `multiSelect={true}` with custom high-contrast checkboxes and `onMultiSelect(nodes)` callback.
- **WAI-ARIA 1.2 Tree View Accessibility & Keyboard Navigation**:
  - `role="tree"` on container with `aria-label` and `aria-multiselectable`.
  - `role="treeitem"` on each row with `aria-expanded`, `aria-selected`, `aria-level`, `aria-posinset`, `aria-setsize`, `aria-disabled`.
  - `role="group"` on recursive child branch containers.
  - Keyboard navigation:
    - `ArrowDown` / `ArrowUp`: Traverse visible tree items.
    - `ArrowRight`: Expand collapsed node or descend into first child.
    - `ArrowLeft`: Collapse expanded node or ascend to parent.
    - `Home` / `End`: Jump to first / last visible item.
    - `Enter` / `Space`: Select active node.
    - `*`: Expand all siblings at active level.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/tree-view.tsx` and exported in `codegen.__init__` as `render_tree_view_component`.

---

## 39. Generated Accessible Futuristic Reusable Tag & Chip Input Tokenizer Component (R-339)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Tag and Chip Tokenizer component suite (`components/tag-input.tsx`):

- **Architecture & Interfaces**:
  - Exports `TagInput` and default export.
  - Subcomponents: `TagInput.Chip`, `TagInput.Suggestions`.
  - Type definitions: `TagItem`, `TagInputVariant`, `TagInputSize`, `TagInputProps`, `TagChipProps`, `TagSuggestionsProps`.
  - Tag schema: `id`, `label`, optional `color`, `icon`, `disabled`, and arbitrary `data` payload.
- **Visual Presentation & Futuristic Variants**:
  - `TagInputVariant`: `"default"` | `"glass"` | `"neon"` | `"bordered"`.
  - Glassmorphic backdrop blur styling (`backdrop-filter: blur(12px)`), futuristic border highlights, and neon glow accents (`box-shadow: 0 0 12px rgba(...)`).
  - Size variants: `"sm"`, `"md"`, `"lg"`.
  - Tag removal buttons with micro-interaction hover scaling and clear SVG `x` icons.
- **Tokenizer Mechanics & Delimiter Parsing**:
  - Automatic delimiter parsing: `Enter`, comma (`,`), and `Tab` tokens input into chips.
  - Paste handling: pasting comma-separated or newline-separated strings splits and creates multiple tags automatically.
  - Duplicate detection: rejects duplicate labels (case-insensitive option) with visual shake/border feedback animation.
  - Tag constraints: `maxTags` enforcement with counter indicator and disabled input when limit is reached.
  - Validation: optional `validate` function to enforce custom regex / format requirements (e.g. valid email, slug, alphanumeric).
- **Autocomplete Suggestions & Keyboard Traversal**:
  - Autocomplete suggestion dropdown filtered dynamically against current input text.
  - Chip navigation with keyboard: when input is empty, `ArrowLeft` / `ArrowRight` traverses existing tag chips, highlighting the active chip.
  - `Backspace` / `Delete` removes the highlighted chip (or the last chip if at end of input).
  - WAI-ARIA 1.2 Combobox / Listbox compliance: `<input role="combobox">`, `aria-autocomplete="list"`, `aria-expanded`, `aria-controls`, suggestions popup with `role="listbox"` and `role="option"`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/tag-input.tsx` and exported in `codegen.__init__` as `render_tag_input_component`.

---

## 40. Generated Accessible Futuristic Reusable Code Block & Syntax Presentation Component (R-340)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Code Block & Syntax Presentation component suite (`components/code-block.tsx`):

- **Architecture & Interfaces**:
  - Exports `CodeBlock` compound component and default export.
  - Subcomponents: `CodeBlock.Header`, `CodeBlock.Content`, `CodeBlock.Line`, `CodeBlock.CopyButton`.
  - Type definitions: `CodeSnippet`, `CodeBlockVariant`, `CodeBlockSize`, `TokenType`, `CodeToken`, `CodeBlockProps`, `CodeBlockHeaderProps`, `CodeBlockContentProps`, `CodeBlockLineProps`, `CodeBlockCopyButtonProps`.
- **Zero-Dependency Built-In Lexical Tokenizer**:
  - Tokenizes keywords, built-in types, strings (single, double, backticks), numbers, comments, booleans, functions, operators, and punctuation.
  - Language support: TypeScript, JavaScript, Python, JSON, SQL, Bash/Shell, HTML/CSS, YAML, Go, and Git Diff.
  - Memoized line-by-line token parsing ensuring high performance without third-party heavy dependencies.
- **Multi-Tab Snippet Switcher & Header Controls**:
  - Support for single snippet or multiple snippets (`snippets` array) with tab switcher.
  - Active tab highlighting with cyan glow border and `role="tablist"` / `role="tab"` WAI-ARIA semantics.
  - macOS/terminal window dots indicator (red, yellow, green) for `"terminal"` variant.
  - Language badge and file name display.
- **Line Numbering, Highlighting & Diff Mode**:
  - Line numbers with customizable starting index (`startLineNumber`) and toggleability (`showLineNumbers`).
  - Highlighting lines & ranges (`highlightLines={[2, 4, "7-10"]}`) with glowing background and left accent bar.
  - Git diff mode (`diffMode={true}` or auto-detected `diff` language) rendering additions in emerald green (`+`) and deletions in rose red (`-`).
- **Interactive Action Toolbar**:
  - One-click copy-to-clipboard (`navigator.clipboard.writeText`) with micro-animation checkmark feedback and 2-second auto-reset.
  - Word wrap toggle (`wrapLines`) switching between horizontal pre scroll and wrap.
  - Expandable/collapsible max-height view (`maxHeight={300}`) with bottom gradient fade mask and expand button with line count.
- **Futuristic Visual Variants**:
  - `CodeBlockVariant`: `"terminal"` | `"glass"` | `"neon"` | `"minimal"`.
  - Glassmorphic backdrop blur styling (`backdrop-filter: blur(16px)`), deep obsidian backgrounds, and neon cyan glow border highlights.
- **WAI-ARIA Accessibility**:
  - `role="region"` container with descriptive `aria-label`.
  - Code viewport `<pre tabIndex={0}>` enabling full keyboard scrolling.
  - Accessible button announcements and polite live regions.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/code-block.tsx` and exported in `codegen.__init__` as `render_code_block_component`.

---

## 41. Generated Accessible Futuristic Reusable Radial Gauge & Activity Rings Component (R-341)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Radial Gauge & Activity Rings component suite (`components/radial-gauge.tsx`):

- **Architecture & Interfaces**:
  - Exports `RadialGauge` compound component (with subcomponents `RadialGauge.Rings` and `RadialGauge.Ring`) and default export.
  - Separate top-level export `ActivityRings`.
  - Type definitions: `RadialGaugeProps`, `RadialGaugeRing`, `RadialGaugeRingProps`, `ActivityRingsProps`, `RadialGaugeVariant` ("neon" | "glass" | "gradient" | "minimal"), `RadialGaugeSize` ("sm" | "md" | "lg" | "xl"), `RadialThreshold`.
- **Pure SVG Arc Trigonometry (Zero Dependencies)**:
  - Polar to Cartesian coordinates helper: `polarToCartesian(centerX, centerY, radius, angleInDegrees)`.
  - SVG path arc descriptor helper: `describeArc(x, y, radius, startAngle, endAngle)` generating smooth, mathematically exact `A` arc commands with large-arc-flag detection.
  - Configurable angle sweeps: 240° (standard gauge), 270° (three-quarter gauge), and 360° (full circle ring).
- **Dynamic Threshold Color Transitions & Goal Markers**:
  - Threshold transition engine (`resolveThresholdColor`): resolves gauge color according to value breakpoints (e.g. green < 60, amber < 85, red >= 85).
  - Target goal markers: renders a radial line tick at specified target value angle (`target={80}`) with label indicator.
  - Glowing endpoint dot: smooth animated glowing coordinate dot positioned at the arc's current tip.
- **Concentric Multi-Ring Activity Mode (`ActivityRings`)**:
  - Multiple concentric metric rings (e.g. CPU, Memory, Storage, or Move, Exercise, Stand).
  - Dynamic radius distribution guaranteeing zero overlap across radii.
  - Interactive legend with value/max metrics, color swatches, and labels.
- **Futuristic Visual Variants & Sizing**:
  - `RadialGaugeVariant`: `"neon"` (vibrant cyan glow with drop-shadow filter), `"glass"` (glassmorphic translucent track with backdrop blur), `"gradient"` (linear/radial SVG gradients), `"minimal"` (clean high-contrast modern line aesthetic).
  - `RadialGaugeSize`: `"sm"` (120px), `"md"` (180px), `"lg"` (240px), `"xl"` (320px), or custom arbitrary numeric size.
- **WAI-ARIA Accessibility**:
  - `role="meter"` semantics on single gauges with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, and `aria-valuetext`.
  - Group semantics `role="group"` on multi-ring activity mode with descriptive `aria-label`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/radial-gauge.tsx` and exported in `codegen.__init__` as `render_radial_gauge_component`.

---

## 42. Generated Accessible Futuristic Reusable Segmented Control & Mode Switcher Component (R-342)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Segmented Control & Mode Switcher component suite (`components/segmented-control.tsx`):

- **Architecture & Interfaces**:
  - Exports `SegmentedControl` compound component (with subcomponent `SegmentedControl.Option`) and default export.
  - Type definitions: `SegmentedControlOption`, `SegmentedControlVariant` ("neon" | "glass" | "pills" | "minimal"), `SegmentedControlSize` ("sm" | "md" | "lg"), `SegmentedControlOrientation` ("horizontal" | "vertical"), `SegmentedControlProps`, `SegmentedControlOptionItemProps`.
- **Animated Sliding Active Pill Indicator**:
  - Precision bounding rect calculation (`getBoundingClientRect`) tracking active option coordinates relative to container.
  - Smooth physics-based animation with cubic bezier easing (`cubic-bezier(0.4, 0, 0.2, 1)`).
  - Window resize listener ensuring indicator remains accurately anchored on viewport dimensions change.
- **Rich Option Items**:
  - Support for custom labels, leading icon slots, notification badges, and disabled options.
  - Native hidden `<input type="hidden">` integration ensuring seamless compatibility with standard form submissions.
- **Futuristic Visual Variants & Sizing**:
  - `SegmentedControlVariant`: `"neon"` (deep obsidian track, glowing cyan indicator, subtle cyan ambient shadow), `"glass"` (translucent frosted backdrop blur `12px`), `"pills"` (high-contrast rounded pill tabs), `"minimal"` (clean borderless design).
  - `SegmentedControlSize`: `"sm"` (28px height, 12px text), `"md"` (36px height, 14px text), `"lg"` (44px height, 16px text).
  - `SegmentedControlOrientation`: `"horizontal"` or `"vertical"` layouts.
- **WAI-ARIA Accessibility & Keyboard Navigation**:
  - `role="radiogroup"` on container with `aria-label`, `aria-labelledby`, and `aria-orientation`.
  - `role="radio"` on options with `aria-checked`, `aria-disabled`, and roving `tabIndex` (`0` for selected, `-1` for unselected).
  - Full keyboard cycling: `ArrowLeft`/`ArrowRight` (or `ArrowUp`/`ArrowDown`), `Home`, and `End` keys cycle through enabled options and auto-focus target button.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/segmented-control.tsx` and exported in `codegen.__init__` as `render_segmented_control_component`.

---

## 43. Generated Accessible Futuristic Reusable Carousel & Slider Showcase Component (R-343)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Carousel & Slider Showcase component suite (`components/carousel.tsx`):

- **Architecture & Compound Structure**:
  - Exports `Carousel` compound component with subcomponents: `Carousel.Content`, `Carousel.Slide`, `Carousel.Previous`, `Carousel.Next`, `Carousel.Indicators`, `Carousel.Progress`, and `Carousel.AutoplayToggle`.
  - Type definitions: `CarouselVariant` ("neon" | "glass" | "cards" | "minimal"), `CarouselTransition` ("slide" | "fade"), `CarouselOrientation` ("horizontal" | "vertical"), `CarouselIndicatorType` ("dots" | "fraction" | "progress" | "none"), `CarouselContextValue`, `CarouselProps`, `CarouselContentProps`, `CarouselSlideProps`, `CarouselPreviousProps`, `CarouselNextProps`, `CarouselIndicatorsProps`, `CarouselProgressProps`, `CarouselAutoplayToggleProps`.
  - Hook: `useCarousel()` accessing context state.
- **Gestures & Autoplay**:
  - Pure touch swipe gesture handling (`onTouchStart`, `onTouchEnd`) with 40px delta threshold.
  - Autoplay interval timer with auto-pause on mouse hover (`pauseOnHover`) and keyboard focus (`pauseOnFocus`).
  - Accessible play/pause toggle button with inline SVG icons (`PlayIcon`, `PauseIcon`).
- **Futuristic Visual Variants & Transitions**:
  - `CarouselVariant`: `"neon"` (cyberpunk glowing border `rgba(6, 182, 212, 0.35)` and cyan accent indicators), `"glass"` (translucent frosted backdrop blur `16px`), `"cards"` (3D perspective card deck with scale transform `scale(0.92)` on inactive items), `"minimal"` (clean borderless presentation).
  - `CarouselTransition`: `"slide"` (smooth track `translateX`/`translateY` with cubic bezier easing) and `"fade"` (cross-dissolve opacity transitions).
  - Indicator styles: elongated active pill dots, fraction counter (`1 / 5`), or animated progression bar.
- **WAI-ARIA Accessibility & Keyboard Navigation**:
  - Adheres to WAI-ARIA 1.2 Carousel Design Pattern: `role="region"` and `aria-roledescription="carousel"` on container, `role="group"` and `aria-roledescription="slide"` on slides.
  - `aria-hidden` on off-screen/inactive slides and `aria-live` polite announcement region.
  - Accessible previous/next buttons with SVG chevron arrows.
  - Keyboard traversal: `ArrowLeft`/`ArrowRight` (or `ArrowUp`/`ArrowDown`), `Home`, and `End` jump keys.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/carousel.tsx` and exported in `codegen.__init__` as `render_carousel_component`.

---

## 44. Generated Accessible Futuristic Reusable Resizable Panels & Splitter Component (R-344)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Resizable Panels & Splitter component suite (`components/resizable.tsx`):

- **Architecture & Compound Structure**:
  - Exports `ResizablePanelGroup` (with `Resizable` alias), `ResizablePanel`, and `ResizableHandle`.
  - Type definitions: `ResizableDirection` ("horizontal" | "vertical"), `ResizableVariant` ("neon" | "glass" | "bordered" | "minimal"), `ResizablePanelGroupProps`, `ResizablePanelProps`, `ResizableHandleProps`, `ResizablePanelContextValue`.
  - Hook: `useResizablePanelGroup()` accessing group state and resize handlers.
- **Pointer & Touch Dragging**:
  - Pure React pointer and touch event handling (`pointerdown`, `pointermove`, `pointerup`, `touchstart`, `touchmove`, `touchend`).
  - Real-time container bounding box calculation with live percentage sizing.
  - Smooth cursor state updates (`col-resize` / `row-resize`) during active drag.
- **Panel Constraints & Collapsible Behavior**:
  - Enforces `minSize` and `maxSize` percentage constraints.
  - Supports collapsible panels with `collapsible`, `collapsedSize`, `onCollapse`, and `onExpand` callbacks.
  - Double-click handle shortcut or keyboard `Enter` to toggle panel collapse.
- **Futuristic Visual Variants & Styling**:
  - `ResizableVariant`: `"neon"` (cyberpunk divider line with glowing cyan hover/active glow and subtle ambient shadow), `"glass"` (translucent frosted divider with backdrop blur `12px`), `"bordered"` (sleek slate divider with centered grip dots affordance), `"minimal"` (clean 1px line with expanded invisible hit-area).
  - Centered inline SVG grip affordance (`GripDotsIcon` / `GripLinesIcon`) indicating draggable separator.
- **WAI-ARIA Accessibility & Keyboard Navigation**:
  - Adheres to WAI-ARIA Separator (Window Splitter) Pattern: `role="separator"`, `aria-orientation`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`, `tabIndex={0}`.
  - Keyboard adjustment: `ArrowLeft`/`ArrowRight` (or `ArrowUp`/`ArrowDown`) with 1% step (5% with `Shift`), `Home` to collapse, `End` to expand to maximum size, `Enter` to toggle collapse.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/resizable.tsx` and exported in `codegen.__init__` as `render_resizable_component`.

---

## 45. Generated Accessible Futuristic Reusable Color Picker & Palette Swatch Component (R-345)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Color Picker & Palette Swatch component suite (`components/color-picker.tsx`):

- **Architecture & Compound Structure**:
  - Exports `ColorPicker` with compound aliases: `ColorPicker.Area` (`ColorArea`), `ColorPicker.HueSlider` (`HueSlider`), `ColorPicker.AlphaSlider` (`AlphaSlider`), `ColorPicker.Swatches` (`ColorSwatches`), `ColorPicker.Inputs` (`ColorInputs`), and `ColorPicker.EyeDropper` (`ColorEyeDropper`).
  - Type definitions: `ColorPickerFormat` ("hex" | "rgb" | "hsl"), `ColorPickerVariant` ("neon" | "glass" | "bordered" | "minimal"), `ColorPickerSize` ("sm" | "md" | "lg"), `ColorSwatch`, `ColorPickerProps`, `ColorAreaProps`, `ColorSliderProps`, `ColorSwatchesProps`, `ColorPickerContextValue`.
  - Hook: `useColorPickerContext()` providing active color state, RGBA/HSVA/HSLA values, and update handlers.
- **Pure Zero-Dependency Color Mathematics**:
  - Pure mathematical conversion algorithms without third-party libraries: `hsvToRgb`, `rgbToHsv`, `rgbToHsl`, `parseHexColor`, `toHex`.
  - Full support for 3-, 6-, and 8-digit hexadecimal colors, RGB, and HSL.
- **Interactive Spectrum & Sliders**:
  - 2D Saturation / Value gradient area with interactive 2D thumb coordinates and pointer/touch tracking.
  - 1D Hue bar slider (0° to 360°) with continuous linear rainbow gradient.
  - 1D Alpha opacity slider (0 to 100%) with checkered transparency underlay and current hue gradient.
- **Format Switcher & Numeric Controls**:
  - Format toggle pill switching between HEX, RGB, and HSL formats.
  - Dedicated numeric input fields for R/G/B/A and H/S/L/A channels with range validation.
- **Preset Palette Swatches & EyeDropper**:
  - Configurable palette swatches with keyboard navigation and active selection indicators (`role="listbox"`, `role="option"`, `aria-selected`).
  - Native browser EyeDropper API integration (`new window.EyeDropper()`) with automatic fallback when unsupported.
- **Futuristic Visual Variants & Styling**:
  - `ColorPickerVariant`: `"neon"` (cyberpunk glowing border with current color accent glow), `"glass"` (translucent frosted backdrop blur `12px`), `"bordered"` (clean border frame with slate neutral borders), and `"minimal"` (compact inline trigger).
- **WAI-ARIA Accessibility & Keyboard Navigation**:
  - Spectrum and sliders adhere to WAI-ARIA slider semantics: `role="slider"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`, `aria-label`.
  - Arrow keys (`ArrowLeft`, `ArrowRight`, `ArrowUp`, `ArrowDown`) navigate 2D spectrum and sliders with 1% and 10% steps, `Home` and `End` jump to extremes.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/color-picker.tsx` and exported in `codegen.__init__` as `render_color_picker_component`.

---

## 46. Generated Accessible Futuristic Reusable PIN & OTP Code Input Component (R-346)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic PIN & OTP Code Input component suite (`components/pin-input.tsx`):

- **Architecture & Compound Structure**:
  - Exports `PinInput` with compound aliases: `PinInput.Group` (`PinInputGroup`), `PinInput.Slot` (`PinInputSlot`), and `PinInput.Separator` (`PinInputSeparator`).
  - Type definitions: `PinInputVariant` ("neon" | "glass" | "bordered" | "minimal"), `PinInputSize` ("sm" | "md" | "lg"), `PinInputType` ("numeric" | "alphanumeric" | "password"), `PinInputProps`, `PinInputGroupProps`, `PinInputSlotProps`, `PinInputSeparatorProps`, `PinInputContextValue`.
  - Hook: `usePinInputContext()` providing shared input state, slot refs, and keydown/paste handlers.
- **Smart Keystroke Navigation & Auto-Advance**:
  - Multi-slot discrete character entry: typing a valid character immediately advances focus to the subsequent slot.
  - Auto-retreat: pressing `Backspace` clears the current slot or retreats to and clears the preceding slot.
  - Arrow navigation: `ArrowLeft` and `ArrowRight` traverse across slots without altering input values.
  - `Home` and `End` jump directly to the first and last slots respectively.
- **Intelligent Clipboard Paste Distribution**:
  - Automatically parses pasted text from clipboard, sanitizes according to `type` (`numeric` vs `alphanumeric`), distributes characters sequentially across empty/existing slots, and places focus on the last populated slot.
  - Triggers `onComplete(code)` callback when all slots are populated.
- **Masking & Security Modes**:
  - Supports `mask={true}` or `type="password"` concealing character values behind dots (`•`).
  - Hidden input field (`<input type="hidden" name={name} value={fullCode} />`) ensuring native HTML `<form>` submissions work seamlessly.
  - Mobile & browser autofill enabled via `autoComplete="one-time-code"` and `inputMode="numeric"`.
- **Futuristic Visual Variants & Styling**:
  - `PinInputVariant`: `"neon"` (cyberpunk glowing border with cyan/purple active slot aura and subtle pulse), `"glass"` (translucent frosted backdrop blur `12px`), `"bordered"` (clean slate border frame), and `"minimal"` (bottom-line underline slots).
  - 3 size presets: `"sm"` (34x40px), `"md"` (44x50px), `"lg"` (54x60px).
- **WAI-ARIA Accessibility**:
  - Container uses `role="group"` with accessible `aria-label`.
  - Individual slot inputs provide explicit screen-reader position labels (e.g. `"Verification code digit 1 of 6"`).
  - Group separator spans declare `aria-hidden="true"`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/pin-input.tsx` and exported in `codegen.__init__` as `render_pin_input_component`.

---

## 47. Generated Accessible Futuristic Reusable Speed Dial & Floating Action Button Component (R-347)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, futuristic Speed Dial & Floating Action Button component suite (`components/speed-dial.tsx`):

- **Architecture & Compound Structure**:
  - Exports `SpeedDial` with compound subcomponents: `SpeedDial.Trigger` (`SpeedDialTrigger`), `SpeedDial.Action` (`SpeedDialAction`), and `SpeedDial.Content` (`SpeedDialContent`).
  - Type definitions: `SpeedDialDirection` ("up" | "down" | "left" | "right"), `SpeedDialVariant` ("neon" | "glass" | "bordered" | "minimal"), `SpeedDialSize` ("sm" | "md" | "lg"), `SpeedDialActionItem`, `SpeedDialProps`, `SpeedDialTriggerProps`, `SpeedDialActionProps`, `SpeedDialContentProps`, `SpeedDialContextValue`.
  - Hook: `useSpeedDial()` providing shared state, direction, variant, size, and keyboard navigation controls.
  - Dual usage model: declarative via `actions={[...]}` prop array or compound JSX structure (`<SpeedDial><SpeedDial.Trigger /><SpeedDial.Content><SpeedDial.Action ... /></SpeedDial.Content></SpeedDial>`).
- **Primary FAB & Morphing Toggle Animation**:
  - Primary floating action button trigger with circular geometry and smooth 45° rotation toggle animation (`transform: open ? "rotate(45deg)" : "rotate(0deg)"`).
  - Supports custom active/closed icon pairs (`icon`, `activeIcon`) or built-in SVG plus/cross icon.
- **Directional Cascades & Staggered Motion**:
  - 4 directional cascades (`"up"`, `"down"`, `"left"`, `"right"`) with absolute coordinate anchoring relative to the primary trigger button.
  - Staggered scaling and opacity animations on open/close (`scale(1)` vs `scale(0.8)`).
  - Action item labels with badge styling positioned alongside the action icons.
- **Backdrop & Dismissal**:
  - Optional backdrop overlay (`backdrop?: boolean`) with subtle blur (`2px`) and click-to-dismiss.
  - Click-outside detection (`handlePointerDown` for mousedown and touchstart) dismissing dial smoothly.
  - Auto-closes on action selection (`closeOnSelect={true}`, default) while restoring focus to the primary trigger button.
- **Futuristic Visual Variants & Sizing**:
  - 4 futuristic visual variants: `"neon"` (cyberpunk glowing border and cyan pulse glow), `"glass"` (translucent frosted backdrop blur `16px`), `"bordered"` (clean slate border frame), and `"minimal"` (flat circular button).
  - 3 size presets: `"sm"` (trigger 40px / action 32px), `"md"` (trigger 48px / action 40px), `"lg"` (trigger 56px / action 48px).
- **WAI-ARIA 1.2 Menu Accessibility & Keyboard Navigation**:
  - Trigger declares `aria-haspopup="menu"`, `aria-expanded={open}`, `aria-controls={menuId}`.
  - Content container uses `role="menu"`, `aria-labelledby={triggerId}`, and `aria-orientation`.
  - Action items use `role="menuitem"` with `tabIndex={open ? 0 : -1}`.
  - Full keyboard navigation: `Escape` closes the menu and returns focus to the trigger; `ArrowUp`/`ArrowDown`/`ArrowLeft`/`ArrowRight` cycles through action items; `Home`/`End` jumps to boundaries; `Tab` closes menu.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/speed-dial.tsx` and exported in `codegen.__init__` as `render_speed_dial_component`.

---

## 48. Generated Accessible Futuristic Reusable Context Menu Suite (R-348)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-class, and futuristic Context Menu compound component suite (`components/context-menu.tsx`):

- **Architecture & Compound Structure**:
  - Exports `ContextMenu` with compound subcomponents: `ContextMenu.Trigger` (`ContextMenuTrigger`), `ContextMenu.Content` (`ContextMenuContent`), `ContextMenu.Item` (`ContextMenuItem`), `ContextMenu.CheckboxItem` (`ContextMenuCheckboxItem`), `ContextMenu.RadioGroup` (`ContextMenuRadioGroup`), `ContextMenu.RadioItem` (`ContextMenuRadioItem`), `ContextMenu.Separator` (`ContextMenuSeparator`), `ContextMenu.Label` (`ContextMenuLabel`), `ContextMenu.Sub` (`ContextMenuSub`), `ContextMenu.SubTrigger` (`ContextMenuSubTrigger`), `ContextMenu.SubContent` (`ContextMenuSubContent`).
  - Type definitions: `ContextMenuVariant` ("neon" | "glass" | "bordered" | "minimal"), `ContextMenuSize` ("sm" | "md" | "lg"), `ContextMenuProps`, `ContextMenuTriggerProps`, `ContextMenuContentProps`, `ContextMenuItemProps`, `ContextMenuCheckboxItemProps`, `ContextMenuRadioGroupProps`, `ContextMenuRadioItemProps`, `ContextMenuSeparatorProps`, `ContextMenuLabelProps`, `ContextMenuSubProps`, `ContextMenuSubTriggerProps`, `ContextMenuSubContentProps`, `ContextMenuContextValue`, `ContextMenuSubContextValue`.
  - Hook: `useContextMenu()` providing shared menu state, coordinates, variant, size, and close handlers.
- **Viewport Boundary Clamping & Collision Prevention**:
  - Captures right-click `(clientX, clientY)` coordinates on trigger element.
  - Uses fixed viewport coordinates clamped against `window.innerWidth` and `window.innerHeight` so the menu never renders off-screen or induces scrollbars.
- **Submenus & Hierarchical Nesting**:
  - `ContextMenu.Sub`, `ContextMenu.SubTrigger`, and `ContextMenu.SubContent` allow arbitrarily nested hierarchical cascading menus.
  - Opens on hover or `ArrowRight`; closes on `ArrowLeft` or `Escape`, restoring focus to the parent subtrigger.
- **Selection Controls & Indicators**:
  - `ContextMenuCheckboxItem` with vector checkmark icon indicating checked state.
  - `ContextMenuRadioGroup` with `ContextMenuRadioItem` single-select radio dot indicator.
  - Keyboard shortcut badges (`shortcut="⌘C"`) rendered with `<kbd>` elements.
  - Destructive item variant styling for delete/danger actions.
- **WAI-ARIA 1.2 Menu Accessibility & Keyboard Navigation**:
  - Semantic roles: `role="menu"`, `role="menuitem"`, `role="menuitemcheckbox"`, `role="menuitemradio"`, `role="separator"`, `role="group"`.
  - Accessible states: `aria-orientation="vertical"`, `aria-checked`, `aria-disabled`, `aria-haspopup="menu"`, `aria-expanded`.
  - Comprehensive keyboard navigation: `ArrowDown`/`ArrowUp` cycles through items; `ArrowRight` opens submenu; `ArrowLeft` closes submenu; `Home`/`End` jumps to boundaries; `Escape` dismisses menu; `Enter`/`Space` activates item.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
---

## 49. Generated Accessible Futuristic Reusable Hover Card Suite (R-349)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Hover Card / Preview Card compound component suite (`components/hover-card.tsx`):

- **Architecture & Compound Structure**:
  - Exports `HoverCard` with compound subcomponents: `HoverCard.Trigger` (`HoverCardTrigger`), `HoverCard.Content` (`HoverCardContent`), `HoverCard.Arrow` (`HoverCardArrow`), and `useHoverCard()`.
  - Type definitions: `HoverCardVariant` ("neon" | "glass" | "bordered" | "minimal"), `HoverCardSize` ("sm" | "md" | "lg"), `HoverCardSide` ("top" | "bottom" | "left" | "right"), `HoverCardAlign` ("start" | "center" | "end"), `HoverCardProps`, `HoverCardTriggerProps`, `HoverCardContentProps`, `HoverCardArrowProps`, `HoverCardContextValue`.
  - Hook: `useHoverCard()` providing open state, trigger/content element references, delay timers, and orientation controls.
- **Timing Coordination & Cursor Transit**:
  - Configurable entrance and exit delays (`openDelay` default 300ms, `closeDelay` default 200ms) with automated timer cleanup.
  - Hovering over trigger begins entrance timer; moving mouse directly from trigger to content keeps card open seamlessly without premature dismissal.
- **Collision Avoidance & Boundary Clamping**:
  - Dynamically measures trigger and content bounding client rects.
  - Automatically flips sides when overflowing screen edges (`bottom` -> `top`, `top` -> `bottom`, `right` -> `left`, `left` -> `right`).
  - Clamps X/Y coordinates against `window.innerWidth` and `window.innerHeight` with safety padding.
- **Visual Variants, Sizes & Directional Notch**:
  - 4 futuristic visual variants: `"neon"` (cyan cyberpunk border glow), `"glass"` (translucent frosted backdrop blur `16px`), `"bordered"` (crisp slate frame), and `"minimal"` (clean subtle shadow).
  - 3 size presets: `"sm"` (maxWidth 260px), `"md"` (maxWidth 320px), `"lg"` (maxWidth 400px).
  - Directional SVG pointer arrow (`HoverCard.Arrow`) pointing toward trigger.
- **WAI-ARIA 1.2 Dialog Accessibility & Keyboard Navigation**:
  - Trigger uses `aria-haspopup="dialog"`, `aria-expanded`, `aria-controls`.
  - Content uses `role="dialog"`, `aria-labelledby`, `tabIndex={-1}`.
  - Full keyboard accessibility: `Escape` immediately dismisses hover card and restores focus to trigger.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/hover-card.tsx` and exported in `codegen.__init__` as `render_hover_card_component`.

---

## 50. Generated Accessible Futuristic Reusable Scroll Area Suite (R-350)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Scroll Area compound component suite (`components/scroll-area.tsx`):

- **Architecture & Compound Structure**:
  - Exports `ScrollArea` with compound subcomponents: `ScrollArea.Viewport` (`ScrollViewport`), `ScrollArea.Scrollbar` (`Scrollbar`), `ScrollArea.Thumb` (`ScrollThumb`), `ScrollArea.Corner` (`ScrollCorner`), and `useScrollArea()`.
  - Type definitions: `ScrollAreaVariant` ("neon" | "glass" | "bordered" | "minimal"), `ScrollAreaSize` ("sm" | "md" | "lg"), `ScrollAreaVisibility` ("auto" | "always" | "scroll" | "hover"), `ScrollAreaOrientation` ("vertical" | "horizontal" | "both"), `ScrollAreaProps`, `ScrollViewportProps`, `ScrollbarProps`, `ScrollThumbProps`, `ScrollCornerProps`, `ScrollAreaContextValue`.
  - Hook: `useScrollArea()` exposing viewport ref, scroll offsets (`scrollLeft`, `scrollTop`), scroll dimensions (`scrollWidth`, `scrollHeight`, `clientWidth`, `clientHeight`), thumb sizes and offsets, dragging states, hover state, scrolling state, and smooth scroll methods (`scrollTo`, `scrollToTop`, `scrollToBottom`, `scrollBy`).
- **Cross-Browser Scrollbar Concealment**:
  - Conceals native OS/browser scrollbars completely across Firefox (`scrollbarWidth: "none"`), IE/Edge Legacy (`msOverflowStyle: "none"`), and WebKit/Blink browsers (`&::-webkit-scrollbar { display: "none" }`).
  - Native touch-momentum and trackpad scrolling preserved via `-webkit-overflow-scrolling: touch`.
- **Proportional Thumb Sizing & Pointer Drag Tracking**:
  - Thumb sizes calculate dynamically as `(viewportSize / scrollSize) * trackSize`, clamped to a minimum thumb size (18px) for accessibility.
  - Interactive pointer drag tracking (`onPointerDown`, `setPointerCapture`, `releasePointerCapture`) computes exact delta offsets against track dimensions for pixel-perfect scrolling.
  - Clicking directly on the scrollbar track performs a smooth animated jump to that coordinate.
- **Visibility Modes**:
  - `"auto"`: Scrollbars display automatically only when content overflows the viewport dimensions.
  - `"always"`: Scrollbars remain visible regardless of content overflow.
  - `"scroll"`: Scrollbars appear dynamically while actively scrolling and fade out smoothly after 1 second of inactivity.
  - `"hover"`: Scrollbars appear smoothly when the pointer enters the scroll area container.
- **Visual Variants & Sizes**:
  - 4 futuristic visual variants: `"neon"` (cyan cyberpunk border glow with glowing thumb), `"glass"` (translucent frosted backdrop blur `12px`), `"bordered"` (crisp slate frame with subtle thumb border), and `"minimal"` (clean borderless subtle thumb).
  - 3 size presets: `"sm"` (4px scrollbar track), `"md"` (8px scrollbar track), `"lg"` (12px scrollbar track with rounded capsule thumb).
- **WAI-ARIA 1.2 Accessibility & Keyboard Navigation**:
  - Scrollbar rendered with `role="scrollbar"`, `aria-orientation="vertical"|"horizontal"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax`, and `aria-controls`.
  - Viewport is focusable (`tabIndex={0}`) and supports standard keyboard navigation: `ArrowDown`/`ArrowUp`, `ArrowLeft`/`ArrowRight`, `PageDown`/`PageUp`, `Home`, and `End`.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/scroll-area.tsx` and exported in `codegen.__init__` as `render_scroll_area_component`.

---

## 51. Generated Accessible Futuristic Reusable Collapsible Component (R-351)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Collapsible / Disclosure compound component suite (`components/collapsible.tsx`):

- **Architecture & Compound Structure**:
  - Exports `Collapsible` with compound subcomponents: `Collapsible.Trigger` (`CollapsibleTrigger`), `Collapsible.Content` (`CollapsibleContent`), and `useCollapsible()`.
  - Type definitions: `CollapsibleVariant` ("neon" | "glass" | "bordered" | "minimal"), `CollapsibleSize` ("sm" | "md" | "lg"), `CollapsibleProps`, `CollapsibleTriggerProps`, `CollapsibleContentProps`, `CollapsibleContextValue`.
  - Hook: `useCollapsible()` exposing open state (`open`), setter (`setOpen`), toggle handler (`toggle`), `disabled` flag, `variant`, `size`, `triggerId`, `contentId`, and `isControlled`.
- **Smooth CSS Grid Row Expansion**:
  - Emits container with `display: "grid"`, `gridTemplateRows: open ? "1fr" : "0fr"`, and `transition: "grid-template-rows 250ms cubic-bezier(0.4, 0, 0.2, 1)"` around an `overflow: "hidden"` inner container.
  - Expands smoothly to dynamic content heights without layout jumps or arbitrary max-height caps.
- **Indicator Chevron & Custom Slots**:
  - Built-in SVG vector chevron with 180° rotation on open (`transform: open ? "rotate(180deg)" : "rotate(0deg)"`).
  - Supports custom indicator replacement via `indicator` prop and full suppression via `hideIndicator`.
- **WAI-ARIA 1.2 Disclosure Pattern & Keyboard Navigation**:
  - Trigger renders `<button type="button" aria-expanded={open} aria-controls={contentId} id={triggerId} aria-disabled={disabled}>`.
  - Content renders `<div id={contentId} role="region" aria-labelledby={triggerId} hidden={!open && !forceMount} data-state={open ? "open" : "closed"}>`.
  - Full keyboard accessibility: pressing `Enter` or `Space` on the trigger toggles the disclosure.
- **Visual Variants & Sizes**:
  - 4 futuristic visual variants: `"neon"` (cyan cyberpunk border glow), `"glass"` (translucent frosted backdrop blur `12px`), `"bordered"` (crisp slate frame), and `"minimal"` (clean borderless).
  - 3 size presets: `"sm"` (padding 8px 12px, font 13px), `"md"` (padding 12px 16px, font 14px), `"lg"` (padding 16px 20px, font 16px).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/collapsible.tsx` and exported in `codegen.__init__` as `render_collapsible_component`.

---

## 52. Generated Accessible Futuristic Reusable Aspect Ratio Viewport Container Component (R-352)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Aspect Ratio viewport container component (`components/aspect-ratio.tsx`):

- **Zero Cumulative Layout Shift (CLS) Architecture**:
  - Outer container calculates percentage-based padding bottom (`paddingBottom: `${(1 / numericRatio) * 100}%``) to reserve viewport layout space immediately before remote images, videos, canvas, or iframes load.
  - Emits modern CSS `aspectRatio: `${numericRatio}`` inline property for browser hardware layout acceleration.
  - Inner container renders with absolute full-bleed coordinates (`position: "absolute"`, `inset: 0`, `width: "100%"`, `height: "100%"`), guaranteeing child media fills the viewport precisely.
- **Ratio Presets & Numeric Flexibility**:
  - Supports `AspectRatioPreset`: `"16/9"` (video widescreen), `"4/3"` (standard), `"1/1"` (square), `"21/9"` (ultrawide), `"9/16"` (mobile story / reel), `"3/2"` (photo landscape), `"2/3"` (photo portrait).
  - Also accepts raw numbers (width / height, e.g. `16 / 9 = 1.7777`), parsed safely via internal `parseRatio`.
- **Overflow Clipping & Ref Forwarding**:
  - `overflowHidden` defaults to `true` to cleanly clip media content with rounded container corners.
  - Full React `forwardRef<HTMLDivElement, AspectRatioProps>` implementation targeting the outer wrapper element.
- **Visual Styling Variants**:
  - 4 futuristic visual variants:
    - `"neon"`: Cyberpunk slate container with cyan glowing border (`rgba(6, 182, 212, 0.4)`) and dual inner/outer ambient glow (`rgba(6, 182, 212, 0.25)`).
    - `"glass"`: Translucent frosted container with backdrop blur filter (`blur(12px)`), subtle border, and elevation shadow.
    - `"bordered"`: Clean dark slate container with crisp contrast border.
    - `"minimal"`: Fully transparent container without borders or backgrounds.
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/aspect-ratio.tsx` and exported in `codegen.__init__` as `render_aspect_ratio_component`.

---

## 53. Generated Accessible Futuristic Reusable Separator / Divider Component (R-353)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Separator / Divider component (`components/separator.tsx`):

- **WAI-ARIA 1.2 Separator Semantics**:
  - Emits decorative mode (`decorative={true}`, default) using `role="none"` and `aria-hidden="true"` to prevent screen-reader clutter in visual dividers.
  - Emits semantic mode (`decorative={false}`) using `role="separator"` and explicit `aria-orientation={orientation}` ("horizontal" | "vertical").
- **Orientations & Dimensions**:
  - `orientation="horizontal"`: Full width (`width: "100%"`) with configurable thickness height.
  - `orientation="vertical"`: Full container height (`height: "100%"`, `display: "inline-block"`, `alignSelf: "stretch"`).
- **Thickness Configuration**:
  - Supports presets `"thin"` (1px), `"md"` (2px), and `"thick"` (4px), or custom integer/float numbers in pixels.
- **Labeled Divider Mode**:
  - Horizontal separators accept `label` or `children` (e.g. "OR", "CONTINUE WITH", section headers).
  - Configurable `labelAlign`: `"start"`, `"center"` (default), `"end"`.
  - Line segments automatically expand using `flexGrow: 1` around a styled badge label.
- **Visual Styling Variants**:
  - 5 futuristic visual variants:
    - `"neon"`: Glowing cyan border line (`rgba(6, 182, 212, 0.6)`) with ambient glow (`boxShadow: "0 0 8px rgba(6, 182, 212, 0.5)"`).
    - `"glass"`: Translucent subtle frosted divider with backdrop blur (`blur(4px)`).
    - `"gradient"`: Linear accent fade divider from transparent to cyan accent to transparent.
    - `"bordered"`: Crisp high-contrast divider (`rgba(255, 255, 255, 0.15)`).
    - `"minimal"`: Subtle slate divider (`rgba(148, 163, 184, 0.2)`).
- **Diff Predictability & Safety**:
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/separator.tsx` and exported in `codegen.__init__` as `render_separator_component`.

## 54. Generated Accessible Futuristic Reusable Keyboard Keycap & Shortcut Badge Component (R-354)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Keyboard Keycap & Shortcut Badge component (`components/kbd.tsx`):

- **Semantic `<kbd>` HTML Elements & WAI-ARIA**:
  - Emits semantic `<kbd>` element with `role="group"`, `aria-label`, and `aria-keyshortcuts` support.
  - Data attributes `data-variant` and `data-size` for extensible styling inspection.
- **Automatic Modifier Key Translation**:
  - Translates common text key names to canonical keyboard symbols automatically (`autoFormatSymbols={true}`):
    - `"meta"` / `"command"` / `"cmd"` -> `"⌘"`
    - `"shift"` -> `"⇧"`
    - `"ctrl"` -> `"⌃"`
    - `"alt"` / `"option"` -> `"⌥"`
    - `"enter"` / `"return"` -> `"↵"`
    - `"backspace"` -> `"⌫"`
    - `"tab"` -> `"⇥"`
    - `"esc"` / `"escape"` -> `"Esc"`
    - Arrow keys (`"↑"`, `"↓"`, `"←"`, `"→"`), `"space"` -> `"␣"`, `"capslock"` -> `"⇪"`.
- **4 Size Scales**:
  - `"xs"`: 10px font, 16px min-width/height (ideal for inline tooltips and compact menus).
  - `"sm"`: 11px font, 20px min-width/height (ideal for dropdowns and command palettes).
  - `"md"`: 12px font, 24px min-width/height (default).
  - `"lg"`: 14px font, 28px min-width/height (ideal for hero shortcut callouts and help dialogs).
- **5 Visual Styling Variants**:
  - `"default"`: Classic 3D elevated keycap with bottom border and tactile box-shadow.
  - `"outline"`: Crisp bordered transparent keycap.
  - `"subtle"`: Soft slate background with subtle border.
  - `"ghost"`: Low-contrast minimalist keycap.
  - `"neon"`: Cyberpunk theme with glowing cyan borders (`rgba(56, 189, 248, 0.5)`) and neon shadow aura (`0 0 8px rgba(56, 189, 248, 0.25)`).
- **Composite Key Combinations & Subcomponents**:
  - `Kbd`: Primary keycap component supporting single keys or `keys` array with configurable `separator`.
  - `KbdGroup`: Composite flex container with `role="group"` propagating uniform size and variant across child keycaps.
  - `KbdShortcut`: Convenience parser component accepting strings like `"⌘+K"` or `"Ctrl+Shift+P"`.
- **Ref Forwarding & React Standards**:
  - All components implement `forwardRef` and explicit `displayName`.
  - 100% diff-invariant across `ir.description` changes; zero external npm packages (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/kbd.tsx` and exported in `codegen.__init__` as `render_kbd_component`.

## 55. Generated Accessible Futuristic Reusable Radio Group Suite (R-355)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Radio Group compound component suite (`components/radio-group.tsx`):

- **WAI-ARIA 1.2 Radio Group Pattern**:
  - Container emits `role="radiogroup"`, `aria-orientation`, `aria-disabled`, and `aria-required`.
  - Individual items emit `role="radio"`, `aria-checked={checked}`, `aria-disabled={disabled}`, and roving `tabIndex={checked ? 0 : -1}`.
- **Full Keyboard Navigation**:
  - `ArrowDown` / `ArrowRight`: Moves focus and selection to the next enabled radio option with cyclic wrap-around.
  - `ArrowUp` / `ArrowLeft`: Moves focus and selection to the previous enabled radio option with cyclic wrap-around.
  - `Space`: Selects the currently focused radio item.
  - Programmatic DOM focus management synchronizing focus ring and selection state.
- **Layout Orientations**:
  - Vertical (default): stacked options with ergonomic vertical gap.
  - Horizontal: inline flex layout wrapping options smoothly.
- **4 Visual Styling Variants**:
  - `"default"`: Sleek dark circular indicator with blue accent fill and inner white dot.
  - `"card"`: Selectable interactive card surface with border highlight, title, and optional description text.
  - `"pill"`: Compact rounded badge button format with active filled state.
  - `"neon"`: Cyberpunk futuristic neon cyan theme with luminous glow aura (`boxShadow: 0 0 10px rgba(6, 182, 212, 0.45)`).
- **3 Size Scales**:
  - `"sm"`: Compact 14px indicator / 12px text.
  - `"md"`: Balanced 18px indicator / 14px text (default).
  - `"lg"`: Prominent 22px indicator / 16px text.
- **Controlled & Uncontrolled Value Management**:
  - Supports `value` and `defaultValue` with `onValueChange` callback.
  - Emits `<input type="hidden" name={name} value={currentValue} />` for seamless integration into standard HTML form submissions.
- **Compound Component Architecture & React Standards**:
  - Subcomponents: `RadioGroup`, `RadioGroupItem`, `Radio = RadioGroupItem`, and `useRadioGroup` context hook.
  - Both `RadioGroup` and `RadioGroupItem` implement `forwardRef` and explicit `displayName`.
  - 100% diff-invariant across `ir.description` changes; zero external npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/radio-group.tsx` and exported in `codegen.__init__` as `render_radio_group_component`.

## 56. Generated Accessible Futuristic Reusable Checkbox & Checkbox Group Primitive (R-356)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Checkbox & Checkbox Group compound component suite (`components/checkbox.tsx`):

- **WAI-ARIA 1.2 Checkbox Pattern & Group Semantics**:
  - Checkbox emits `role="checkbox"`, `aria-checked={isIndeterminate ? "mixed" : isChecked}`, `aria-disabled`, `aria-required`, and `tabIndex={disabled ? -1 : 0}`.
  - CheckboxGroup emits `role="group"`, `aria-orientation`, and `aria-disabled`.
- **Tri-State / Indeterminate Support**:
  - Supports `checked: boolean | "indeterminate"` with dedicated `CheckedState` type.
  - Renders custom SVG minus/dash indicator for indeterminate state and custom SVG polyline checkmark for checked state.
- **Keyboard Space Toggling**:
  - Pressing `Space` key activates `toggle()` and calls `e.preventDefault()` to prevent undesirable browser page scroll.
- **Layout Orientations & Group Management**:
  - `CheckboxGroup` manages multiple selections (`value: string[]`, `onValueChange: (val: string[]) => void`).
  - Supports vertical (default) and horizontal layouts with flex wrapping.
  - Supports `options` convenience array prop alongside nested children.
- **4 Visual Styling Variants**:
  - `"default"`: Minimalist rounded square box with high-contrast blue fill and clean checkmark.
  - `"card"`: Selectable interactive card container with title, description, and indicator box.
  - `"pill"`: Rounded badge button format with active color fill.
  - `"neon"`: Cyberpunk futuristic neon cyan theme with luminous box shadow glow (`boxShadow: 0 0 10px rgba(56, 189, 248, 0.5)`).
- **3 Size Scales**:
  - `"sm"`: 14px indicator box, 10px icon, 12px label text.
  - `"md"`: 18px indicator box, 12px icon, 14px label text (default).
  - `"lg"`: 22px indicator box, 14px icon, 16px label text.
- **Form Submission Integration**:
  - Emits `<input type="hidden" name={effectiveName} value={isChecked ? value : ""} />` for seamless HTML form submission integration.
- **Compound Exports & React Standards**:
  - Exports `Checkbox`, `CheckboxGroup`, `CheckboxItem = Checkbox`, and `useCheckboxGroup` context hook.
  - Both `Checkbox` and `CheckboxGroup` implement `forwardRef` and explicit `displayName`.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/checkbox.tsx` and exported in `codegen.__init__` as `render_checkbox_component`.

## Accessible Futuristic Reusable Announcement Banner & Callout Suite (`components/banner.tsx`, R-357)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Announcement Banner & Callout compound component suite (`components/banner.tsx`):

- **WAI-ARIA Live Region Semantics**:
  - Banner container emits `role="status"` or `role="alert"` (for error/warning variants) and `aria-live="polite"` or `aria-live="assertive"`.
  - Close button emits `aria-label="Dismiss banner"`.
- **4 Layout Positions**:
  - `"top"`: Sticky viewport top header banner.
  - `"bottom"`: Sticky viewport bottom footer banner.
  - `"inline"`: Standard document flow card banner with rounded corners.
  - `"floating"`: Elevated center-aligned toast banner with elevated drop shadow.
- **6 Visual Styling Variants**:
  - `"info"`: Clean blue accent theme.
  - `"success"`: Crisp emerald green accent theme.
  - `"warning"`: Vibrant amber warning theme.
  - `"error"`: High-contrast rose red alert theme.
  - `"neon"`: Cyberpunk futuristic cyan theme with ambient box shadow glow (`0 0 20px rgba(56, 189, 248, 0.25)`).
  - `"gradient"`: Futuristic deep violet-to-cyan gradient background.
- **3 Size Scales**:
  - `"sm"`: 8px 12px padding, 12px font, 13px title, 14px icon.
  - `"md"`: 12px 16px padding, 14px font, 15px title, 16px icon (default).
  - `"lg"`: 16px 20px padding, 15px font, 16px title, 18px icon.
- **Interactive Capabilities**:
  - Dismissible with smooth exit transition (`dismissible?: boolean`, `onDismiss?: () => void`).
  - Action CTA slot container (`BannerAction`).
  - Built-in SVG icons (`InfoIcon`, `SuccessIcon`, `WarningIcon`, `ErrorIcon`, `NeonIcon`, `CloseIcon`).
- **Compound Exports & React Standards**:
  - Exports `Banner`, `BannerIcon`, `BannerAction`, `BannerCloseButton`, `AnnouncementBanner`, and `Callout`.
  - Full React `forwardRef` and explicit `displayName` on all subcomponents.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/banner.tsx` and exported in `codegen.__init__` as `render_banner_component`.

## Accessible Futuristic Reusable Searchable Combobox & Autocomplete Primitive (`components/combobox.tsx`, R-358)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-grade, and futuristic Searchable Combobox & Autocomplete compound component suite (`components/combobox.tsx`):

- **WAI-ARIA 1.2 Combobox & Listbox Pattern Compliance**:
  - Container emits `role="combobox"`, `aria-expanded={isOpen}`, `aria-haspopup="listbox"`, `aria-controls={listboxId}`, `aria-activedescendant={activeOptionId}`, `aria-disabled`, `tabIndex`.
  - Listbox dropdown emits `role="listbox"`, `aria-multiselectable={multiple || undefined}`, and unique ID.
  - Option items emit `role="option"`, `aria-selected={isSelected}`, `aria-disabled`, and `data-highlighted`.
- **Keyboard Navigation & Traversal**:
  - `ArrowDown` / `ArrowUp` cyclically traverses visible filtered options.
  - `Enter` selects highlighted option.
  - `Escape` closes listbox dropdown.
  - `Home` / `End` jumps to bounds.
- **Live Type-Ahead Search Filtering**:
  - Real-time case-insensitive filtering across label, description, and keywords.
- **Single-Select & Multi-Select Modes**:
  - Single selection with placeholder and clean label readout.
  - Multi-select mode with removable tag chips (`XIcon`).
  - Clear button affordance (`allowClear`) for quick one-click reset.
- **4 Visual Styling Variants**:
  - `"default"`: Sleek minimal border with focus highlight ring.
  - `"card"`: Distinctive option card styling.
  - `"glass"`: Frosted glassmorphism background with blur.
  - `"neon"`: Cyberpunk futuristic glowing cyan theme (`boxShadow: 0 0 15px rgba(56, 189, 248, 0.3)`).
- **3 Size Scales**:
  - `"sm"`: 32px height, 12px font, 20px tag height.
  - `"md"`: 38px height, 14px font, 24px tag height (default).
  - `"lg"`: 44px height, 16px font, 28px tag height.
- **Form Submission Integration & Standards**:
  - Emits `<input type="hidden" name={name} value={...} />` for native HTML form submission compatibility.
  - Exports `Combobox`, `Autocomplete = Combobox`.
  - Full React `forwardRef` and explicit `displayName`.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/combobox.tsx` and exported in `codegen.__init__` as `render_combobox_component`.

## Accessible Futuristic Reusable Calendar & Event Scheduler Suite (`components/calendar.tsx`, R-366)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-and-mobile-grade, and futuristic Calendar & Event Scheduler compound component suite (`components/calendar.tsx`):

- **WAI-ARIA 1.2 Grid Pattern Compliance**:
  - Container emits `role="grid"`, `aria-label={ariaLabel || "Calendar"}`.
  - Weekday header emits `role="row"` with header items emitting `role="columnheader"` and `aria-label`.
  - Date grid rows emit `role="row"` with day cells emitting `role="gridcell"`, `aria-selected={isSelected}`, `aria-current={isTodayDate ? "date" : undefined}`, and `tabIndex`.
- **Multi-View Modes**:
  - Month Grid View: 7-column calendar matrix with days from adjacent months properly muted, current month days active, today circular highlight badge, and event pills.
  - Agenda List View: chronological event stream displaying event titles, descriptions, dates, and start/end time badges.
- **Zero-Dependency Built-in Date Math**:
  - Pure date calculation utilities: `getMonthMatrix`, `isSameDay`, `isToday`, `isSameMonth`, `getDaysInMonth`, `toISODateString`.
- **Event Pills & Overflow Management**:
  - Daily event pills with customizable event colors, start time indicators, and title truncation.
  - Overflow indicator badge (`+N more`) when events exceed `maxEventsPerDay`.
- **Header Navigation & View Mode Switcher**:
  - Previous Month, Next Month, and Today jump controls.
  - Month/Year heading title.
  - View switcher buttons toggling between Month and Agenda views.
- **4 Visual Styling Variants**:
  - `"default"`: Clean neutral surface with subtle border and focus rings.
  - `"card"`: Elevated container card styling with soft drop-shadow.
  - `"glass"`: Translucent frosted glassmorphism background with backdropFilter blur.
  - `"neon"`: Cyberpunk futuristic dark surface with glowing cyan accent ring (`boxShadow: 0 0 16px rgba(6, 182, 212, 0.25)`).
- **3 Size Scales**:
  - `"sm"`: Compact calendar cells (36px min-height) with 12px fonts.
  - `"md"`: Standard calendar cells (60px min-height) with 14px fonts.
  - `"lg"`: Spacious calendar cells (84px min-height) with 16px fonts.
- **Form Submission Integration & Standards**:
  - Emits `<input type="hidden" name={name} value={...} />` for native HTML form submission compatibility when `name` prop is provided.
  - Exports `Calendar`, `Scheduler = Calendar`, `EventCalendar = Calendar`, and default export.
  - Full React `forwardRef` and explicit `displayName`.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/calendar.tsx` and exported in `codegen.__init__` as `render_calendar_component`.

## Accessible Futuristic Reusable Kanban Board & Task Flow Matrix Suite (`components/kanban.tsx`, R-367)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-and-mobile-grade, and futuristic Kanban Board & Task Flow Matrix compound component suite (`components/kanban.tsx`):

- **WAI-ARIA 1.2 Region & Listbox Semantics**:
  - Container emits `role="region"`, `aria-label={ariaLabel || "Kanban Board"}`.
  - Lane container emits `role="group"`, `aria-label="Workflow stages"`.
  - Column emits `role="region"`, `aria-label={`${column.title} column`}`.
  - Card list emits `role="listbox"`, `aria-label={`${column.title} items`}`.
  - Cards emit `role="option"`, `aria-selected={false}`, `tabIndex={0}`, with keyboard Enter / Space activation.
- **HTML5 Drag & Drop Movement**:
  - Cards are `draggable={allowDragDrop}` with `handleDragStart`, `handleDragOver`, `handleDragLeave`, `handleDrop`, `handleDragEnd`.
  - Visual dashed drop-target indicator state on drag over.
- **Column WIP Limits & Collapsing**:
  - Work-In-Progress (WIP) limit warnings with visual alert circle icon when column card count exceeds `limit`.
  - Smooth collapsible columns with icon-only collapsed state.
- **Built-in Search Filtering**:
  - Case-insensitive search filtering across card titles, descriptions, tags, and assignee names.
- **Priority Badges & Assignee Cards**:
  - Priority styles with distinctive color mappings (`urgent`, `high`, `medium`, `low`).
  - Assignee circular avatar badges and due date clock pills.
- **4 Visual Styling Variants**:
  - `"default"`: Clean neutral surface with subtle border and focus rings.
  - `"card"`: Elevated container card styling with soft drop-shadow.
  - `"glass"`: Translucent frosted glassmorphism background with backdropFilter blur.
  - `"neon"`: Cyberpunk futuristic dark surface with glowing cyan accent ring (`boxShadow: 0 0 16px rgba(6, 182, 212, 0.2)`).
- **3 Size Scales**:
  - `"sm"`: Compact columns (260px width) with 12px fonts.
  - `"md"`: Standard columns (300px width) with 14px fonts.
  - `"lg"`: Spacious columns (340px width) with 16px fonts.
- **Form Submission Integration & Standards**:
  - Emits `<input type="hidden" name={name} value={JSON.stringify(items)} />` for native HTML form submission compatibility when `name` prop is provided.
  - Exports `Kanban`, `KanbanBoard = Kanban`, `TaskBoard = Kanban`, and default export.
  - Full React `forwardRef` and explicit `displayName`.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/kanban.tsx` and exported in `codegen.__init__` as `render_kanban_component`.

## Accessible Futuristic High-Performance Infinite Virtual List & Windowed Scroller Suite (`components/virtual-list.tsx`, R-368)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-and-mobile-grade, and futuristic High-Performance Infinite Virtual List & Windowed Scroller compound component suite (`components/virtual-list.tsx`):

- **Mathematical Windowing & Dynamic Offsets**:
  - Automatically calculates visible slice indices `[startIndex, endIndex]` based on container `scrollTop`, `clientHeight`, and item height.
  - Supports both fixed numeric `itemHeight` and dynamic callback function `(index, item) => number` with binary search over prefix sums.
  - Phantom container preserving total scroll height with zero-layout-shift absolute transform positioning.
  - Configurable `overscan` buffer rendering extra items above and below the visible viewport to eliminate blank flashing during fast scrolling.
- **Infinite Scrolling & Threshold Detection**:
  - Distance threshold monitoring (`endReachedThreshold`, default 150px) triggering `onEndReached` with duplicate call guards when approaching the list end.
  - Built-in SVG loading spinner when `isLoading` is active.
- **Fast-Scrolling State Detection**:
  - Live `isScrolling` boolean passed into `renderItem` info to allow optional lightweight skeleton placeholder rendering during rapid kinetic scrolls.
- **Imperative Scroll Handle**:
  - Ref exposes imperative methods: `scrollTo(offset)`, `scrollToIndex(index, align)`, `scrollToTop()`, `scrollToBottom()`.
- **WAI-ARIA 1.2 Feed & Article Semantics**:
  - Outer feed emits `role="feed"`, `aria-busy={isLoading}`, `aria-label`.
  - Item wrappers emit `role="article"`, `aria-posinset={index + 1}`, `aria-setsize={items.length}`.
- **4 Visual Styling Variants**:
  - `"default"`: Clean neutral surface with subtle border.
  - `"card"`: Elevated card styling with soft drop-shadow.
  - `"glass"`: Translucent frosted glassmorphism background with backdropFilter blur.
  - `"neon"`: Cyberpunk futuristic dark surface with glowing cyan accent border (`boxShadow: 0 0 16px rgba(6, 182, 212, 0.2)`).
- **3 Size Scales**:
  - `"sm"`: Compact padding (6px) with 12px fonts.
  - `"md"`: Standard padding (10px) with 14px fonts.
  - `"lg"`: Spacious padding (16px) with 16px fonts.
- **Standards & Composition**:
  - Exports `VirtualList`, `VirtualScroller = VirtualList`, `WindowedList = VirtualList`, and default export.
  - Full React `forwardRef` and explicit `displayName`.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/virtual-list.tsx` and exported in `codegen.__init__` as `render_virtual_list_component`.
 
+## Accessible Futuristic Query Filter Builder & Dynamic Rule Bar Suite (`components/filter-builder.tsx`, R-369)
+
+Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-and-mobile-grade, and futuristic Query Filter Builder & Dynamic Rule Bar compound component suite (`components/filter-builder.tsx`):
+
+- **Recursive Group & Rule Hierarchy**:
+  - Supports deeply nested logical expression trees (`FilterGroup`, `FilterRule`) with configurable maximum depth guard (`maxDepth`, default 3).
+  - Combinator switcher (`AND` / `OR`) per group level with distinct visual active pill buttons.
+  - Add Rule and Add Subgroup action buttons per nested group level.
+  - Delete rule and delete subgroup actions with minimum root rule constraint enforcement.
+- **Dynamic Type-Aware Operators & Field Value Inputs**:
+  - Operators dynamically resolved per field type:
+    - `string`: equals, not_equals, contains, not_contains, starts_with, ends_with, is_empty, is_not_empty.
+    - `number`: equals, not_equals, greater_than, less_than, greater_than_or_equal, less_than_or_equal.
+    - `date`: equals, not_equals, greater_than, less_than.
+    - `boolean`: is_true, is_false.
+    - `select`: equals, not_equals, in.
+  - Value input controls adapt dynamically: text input for strings, numeric input with spin controls for numbers, date picker input for dates, select dropdown options for select types, and automatic value clearing for unary operators (`is_empty`, `is_not_empty`, `is_true`, `is_false`).
+- **Summary Bar & Header Actions**:
+  - Filter rule count badge indicator ("N rules").
+  - "Clear All" action resetting group back to empty initial root rule.
+- **WAI-ARIA 1.2 Region & Group Semantics**:
+  - Outer filter builder container emits `role="region"`, `aria-label="Query Filter Builder"`.
+  - Each nested rule group emits `role="group"`, `aria-label="Filter group [combinator]"`.
+- **5 Built-in Zero-Dependency Vector Icons**:
+  - `PlusIcon`, `TrashIcon`, `FolderPlusIcon`, `XCircleIcon`, `FilterIcon`.
+- **4 Visual Styling Variants**:
+  - `"default"`: Clean neutral surface with subtle border.
+  - `"card"`: Elevated card styling with soft drop-shadow.
+  - `"glass"`: Translucent frosted glassmorphism background with backdropFilter blur.
+  - `"neon"`: Cyberpunk futuristic dark surface with glowing cyan accent border (`boxShadow: 0 0 16px rgba(6, 182, 212, 0.2)`).
+- **3 Size Scales**:
+  - `"sm"`: Compact padding (6px-8px) with 12px fonts and 28px control heights.
+  - `"md"`: Standard padding (10px-12px) with 14px fonts and 34px control heights.
+  - `"lg"`: Spacious padding (14px-16px) with 16px fonts and 40px control heights.
+- **Standards & Composition**:
+  - Exports `FilterBuilder`, `QueryFilterBuilder = FilterBuilder`, `RuleBuilder = FilterBuilder`, and default export.
+  - Native form submission integration via hidden input (`name`).
+  - Full React `forwardRef` and explicit `displayName`.
+  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
+  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/filter-builder.tsx` and exported in `codegen.__init__` as `render_filter_builder_component`.

## Accessible Futuristic Data Visualization & SVG Chart Suite (`components/chart.tsx`, R-370)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-and-mobile-grade, and futuristic Data Visualization and SVG Chart compound component suite (`components/chart.tsx`):

- **6 Chart Types in a Unified Engine**:
  - `Bar`: Vertical or horizontal bars with configurable slot width, padding, rounded corners (`rx={4}`), hover opacity highlights, and optional value labels.
  - `Line`: Continuous polyline or smooth bezier curve (`generateSmoothPath`) with circular data point markers and hover pulse radius expansion.
  - `Area`: Linear gradient area fill (`<defs><linearGradient>`) fading from series color to transparent underneath the curve.
  - `Donut`: Concentric circular donut slices computed using polar-to-cartesian trigonometry (`describeDonutSlice`), configurable cutout hole ratio (`donutHoleRatio`, default 0.6), and dynamic center readout metric displaying either active hovered slice or total dataset sum.
  - `Pie`: Full solid circular pie distribution with interactive slice explosion offsets.
  - `Sparkline`: Ultra-compact, inline trendline chart (no grid, no legend, no padding) designed for stat cards and table cell visualizers.
- **Interactive Inspection & Controls**:
  - Interactive floating tooltip card tracking mouse/touch coordinates with series color indicators, exact values, formatted currency/numbers, and percentage shares.
  - Interactive legend with click-to-toggle series visibility.
  - Automated axis tick generation with formatted value scales and subtle dashed grid lines.
- **WAI-ARIA 1.2 Graphics Semantics & Accessibility**:
  - Outer container emits `role="region"`, `aria-label={title}`.
  - SVG element emits `role="img"`, `aria-label`.
  - Automated visually hidden HTML data table fallback (`className="sr-only"`) for screen readers.
- **4 Visual Styling Variants**:
  - `"default"`: Clean neutral dark surface with subtle border.
  - `"card"`: Elevated card container with soft drop-shadow.
  - `"glass"`: Translucent frosted glassmorphism background with `backdropFilter: blur(12px)`.
  - `"neon"`: Cyberpunk futuristic dark surface with glowing cyan accent border and SVG glow dropshadows (`drop-shadow(0 0 8px rgba(6, 182, 212, 0.5))`).
- **3 Size Scales**:
  - `"sm"`: 180px height, 11px fonts, 12px padding.
  - `"md"`: 260px height, 12px fonts, 16px padding.
  - `"lg"`: 360px height, 14px fonts, 24px padding.
- **Standards & Composition**:
  - Exports `Chart`, `BarChart`, `LineChart`, `AreaChart`, `DonutChart`, `PieChart`, `Sparkline`, and default export.
  - Full React `forwardRef` and explicit `displayName` across all exports.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/chart.tsx` and exported in `codegen.__init__` as `render_chart_component`.

## Accessible Futuristic Time Picker & Time Range Suite (`components/time-picker.tsx`, R-371)

Next.js web applications generated by OmniStackAI now include a standalone, accessible, desktop-and-mobile-grade, and futuristic Time Picker & Time Range compound component suite (`components/time-picker.tsx`):

- **12-Hour & 24-Hour Dual Format Modes**:
  - Full support for 12-hour format with AM/PM period selector button and 24-hour military/international format.
  - Zero-dependency time parsing and formatting utilities (`parseTimeString`, `formatTimeString`, `getNowTimeString`).
  - Configurable optional seconds column (`showSeconds`) and custom step intervals (`stepMinutes`, `stepSeconds`).
- **Interactive Column Scrollers & Auto-Scroll**:
  - Dedicated `TimeColumn` listbox subcomponents for hours, minutes, seconds, and AM/PM with auto-scroll into view upon selection.
  - Quick-select preset chips ("Now", "09:00 AM", "12:00 PM", "05:00 PM") for instant one-click time assignment.
- **Dual Range Mode (`TimeRangePicker`)**:
  - Dual start and end time picker integration with start <= end range validation.
  - Emits separate hidden inputs (`{name}_start`, `{name}_end`) for native HTML form submissions.
- **Inline & Popover Modes**:
  - Popover dropdown trigger with outside click and Escape key dismissal.
  - Direct inline embedding mode (`inline={true}`) for permanent calendar / scheduling panels.
- **WAI-ARIA 1.2 Combobox & Listbox Semantics**:
  - Trigger emits `role="combobox"`, `aria-expanded`, `aria-haspopup="dialog"`.
  - Panel emits `role="dialog"`.
  - Column containers emit `role="listbox"`, `aria-label`.
  - Individual time buttons emit `role="option"`, `aria-selected`.
- **5 Built-in Zero-Dependency Vector Icons**:
  - `ClockIcon`, `ChevronUpIcon`, `ChevronDownIcon`, `XIcon`, `CheckIcon`.
- **4 Visual Styling Variants**:
  - `"default"`: Clean neutral dark surface with subtle border.
  - `"card"`: Elevated card container with soft drop-shadow.
  - `"glass"`: Translucent frosted glassmorphism background with `backdropFilter: blur(12px)`.
  - `"neon"`: Cyberpunk futuristic dark surface with glowing cyan accent border (`boxShadow: 0 0 16px rgba(6, 182, 212, 0.25)`).
- **3 Size Scales**:
  - `"sm"`: 32px height, 12px font, compact columns.
  - `"md"`: 38px height, 14px font, standard columns.
  - `"lg"`: 44px height, 16px font, spacious columns.
- **Standards & Composition**:
  - Exports `TimePicker`, `TimeRangePicker`, `TimeInput`, `TimeColumn`, `ClockIcon`, and default export.
  - Full React `forwardRef` and explicit `displayName` across all exports.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies (pure React).
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/time-picker.tsx` and exported in `codegen.__init__` as `render_time_picker_component`.

### Digital Signature Pad & Drawing Canvas Primitive (`components/signature-pad.tsx`)

Accessible, futuristic, desktop-and-mobile-grade HTML5 canvas digital signature pad compound component suite:
- **Zero Runtime Dependencies**: Native HTML5 `<canvas>` 2D rendering without any external npm packages.
- **Silk-Smooth Drawing**:
  - Quadratic bezier curve stroke interpolation for naturally curved, smooth pen strokes.
  - Pointer Events API (`pointerdown`, `pointermove`, `pointerup`, `pointerleave`, `pointercancel`) with CSS `touch-action: none` supporting stylus pressure, touch, and mouse input.
  - High-DPI Retina `devicePixelRatio` scaling preventing stroke blurriness on Retina/4K displays.
- **Stroke Stack & Dual Export**:
  - Multi-level undo/redo stroke stack (`canUndo()`, `canRedo()`, `undo()`, `redo()`).
  - Clear action (`clear()`, `isEmpty()`).
  - Raster PNG dataURL export (`toDataURL(type, quality)`).
  - Vector SVG export (`toSVG()`) generating crisp scalable vector `<path>` elements.
- **Signing Affordances**:
  - Subtle dashed signing guide line with configurable text ("Sign on line above") and starting anchor mark.
  - Pristine placeholder prompt overlay.
  - Responsive header toolbar with stroke counter badge and action buttons (Undo, Redo, Clear, Download).
- **Form Integration**:
  - Transparent synchronization with native HTML forms via hidden `<input type="hidden" name={name} value={...} />`.
- **WAI-ARIA 1.2 Accessibility**:
  - `role="application"`, `aria-roledescription="drawing canvas"`, `aria-label="Signature Pad"`, `aria-label="Signature drawing area"`.
- **4 Visual Variants**:
  - `"default"`: Subtle dark slate container with crisp borders.
  - `"card"`: Elevated solid dark card with deep shadow.
  - `"glass"`: Translucent backdrop blur with frosted glass effect.
  - `"neon"`: Cyberpunk glowing borders and cyan accents.
- **3 Size Scales**:
  - `"sm"`: 140px canvas height.
  - `"md"`: 200px canvas height.
  - `"lg"`: 280px canvas height.
- **Standards & Composition**:
  - Exports `SignaturePad`, `SignatureCanvas`, `DrawingPad`, and default export.
  - Full React `forwardRef` and explicit `displayName` across all exports.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/signature-pad.tsx` and exported in `codegen.__init__` as `render_signature_pad_component`.

### Diff Viewer & Code/Text Comparison Suite (`components/diff-viewer.tsx`)

Accessible, futuristic, desktop-and-mobile-grade text and code comparison compound component suite:
- **Zero Runtime Dependencies**: Pure mathematical Longest Common Subsequence (LCS) diffing algorithm without third-party packages.
- **Dual Comparison Modes**:
  - **Split View**: Side-by-side dual-pane layout with horizontally synchronized lines and filler gaps for additions/deletions.
  - **Unified View**: Compact single-column layout with dual old/new line numbers and `+` / `-` markers.
- **Fine-Grained Highlighting**:
  - Full line difference classification (`added`, `deleted`, `unchanged`).
  - Word-level intraline character diffing highlighting granular changes within modified lines.
- **Unchanged Lines Folding**:
  - Automatically folds large contiguous blocks of unchanged code exceeding `foldThreshold` into expandable banners with configurable leading and trailing `contextLines`.
- **Statistics & Copy Actions**:
  - File header displaying filename, addition (`+N`) and deletion (`-N`) counters, and view mode toggles.
  - Integrated copy buttons for raw patch, original file, and modified file.
- **WAI-ARIA 1.2 Accessibility**:
  - `role="region"`, `role="table"`, `role="row"`, `role="cell"`, `aria-label="Code diff viewer"`, `aria-roledescription="diff view"`.
- **4 Visual Variants**:
  - `"default"`: Subtle dark slate container with crisp borders.
  - `"card"`: Elevated solid dark card with deep shadow.
  - `"glass"`: Translucent backdrop blur with frosted glass effect.
  - `"neon"`: Cyberpunk glowing borders and cyan/emerald/rose accents.
- **3 Size Scales**:
  - `"sm"`: Compact 11px/12px font and tight row padding.
  - `"md"`: Standard 12px/13px font and comfortable row padding.
  - `"lg"`: Spacious 14px font and generous row padding.
- **Standards & Composition**:
  - Exports `DiffViewer`, `CodeDiff`, `TextDiff`, and default export.
  - Full React `forwardRef` and explicit `displayName` across all exports.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/diff-viewer.tsx` and exported in `codegen.__init__` as `render_diff_viewer_component`.

### Org Chart & Hierarchy Flow Diagram Suite (`components/org-chart.tsx`)

Accessible, futuristic, desktop-and-mobile-grade organizational chart and hierarchy flow diagram compound component suite:
- **Zero Runtime Dependencies**: Pure React 18+ and native CSS/SVG connector stems without third-party diagramming packages.
- **Dual Layout Orientations**:
  - **Vertical Mode**: Top-to-bottom hierarchy with parent centered above horizontal crossbars and drop stems into child branches.
  - **Horizontal Mode**: Left-to-right hierarchy with parent on the left, vertical crossbars, and horizontal stems into child cards.
- **Subtree Collapsing & Report Counts**:
  - Node cards feature expand/collapse toggle buttons on the connector edge with rotation transitions.
  - Automatic calculation of direct and total indirect reports displayed in pill badges.
- **Search & Ancestor Auto-Expansion**:
  - Built-in search input filtering by employee name, role, department, or email.
  - Matched nodes receive glowing highlight rings and automatically expand all ancestor path nodes for instant discovery.
- **Node Selection & Actions**:
  - Interactive card click selection handler (`onNodeClick`, `selectedId`).
  - Action menu trigger button (`...`) for custom employee/role workflows.
- **WAI-ARIA 1.2 Accessibility**:
  - `role="tree"`, `role="treeitem"`, `aria-label="Organization Chart"`, `aria-expanded`, `aria-selected`.
- **4 Visual Variants**:
  - `"default"`: Clean dark slate container with crisp borders.
  - `"card"`: Elevated solid card with rich shadow.
  - `"glass"`: Translucent backdrop blur with frosted glass effect.
  - `"neon"`: Cyberpunk glowing cyan borders and neon-lit connectors.
- **3 Size Scales**:
  - `"sm"`: Compact card (180px width, 11px font).
  - `"md"`: Standard card (220px width, 13px font).
  - `"lg"`: Spacious card (260px width, 14px font).
- **Standards & Composition**:
  - Exports `OrgChart`, `HierarchyTree`, `OrgNode`, and default export.
  - Full React `forwardRef` and explicit `displayName` across all exports.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/org-chart.tsx` and exported in `codegen.__init__` as `render_org_chart_component`.

### Heatmap & Activity Contribution Matrix Suite (`components/heatmap.tsx`)

Accessible, futuristic, desktop-and-mobile-grade heatmap and activity contribution matrix compound component suite:
- **Zero Runtime Dependencies**: Pure React 18+ and native HTML/SVG elements without heavy third-party visualization libraries (`d3`, `visx`).
- **Dual Matrix Layout Modes**:
  - **Calendar / Activity Matrix**: GitHub-style 52-week activity contribution grid organized by weeks with weekday labels (Mon, Wed, Fri) and dynamic month headers.
  - **Dense Grid Matrix**: 2D coordinate matrix for 24x7 hourly load, resource utilization, server metrics, or arbitrary categorical dimensions with X and Y labels.
- **5 Cyberpunk & Natural Color Palettes**:
  - `emerald`: Classic GitHub green gradient.
  - `cyan`: Futuristic cyberpunk neon cyan.
  - `violet`: Cosmic deep purple & indigo.
  - `amber`: Solar thermal gold & orange.
  - `rose`: Critical activity crimson & ruby.
- **Dynamic & Quantile Intensity Bucketing**:
  - 5 intensity levels (0: empty, 1: low, 2: medium, 3: high, 4: peak) with automatic quantile threshold normalization or explicit custom threshold cutoffs.
- **Interactive Floating Tooltips & Keyboard Navigation**:
  - Native floating tooltip on hover/focus displaying formatted date/coordinates, count, and customizable label.
  - Full keyboard traversal with Arrow keys (`ArrowLeft`, `ArrowRight`, `ArrowUp`, `ArrowDown`) and cell selection (`onCellClick`, `selectedCell`).
- **WAI-ARIA 1.2 Grid Accessibility**:
  - `role="grid"`, `role="row"`, `role="gridcell"`, `aria-selected`, `aria-label`.
- **Integrated Legend**:
  - Reusable `HeatmapLegend` component displaying "Less" -> "More" gradient scale and count summaries.
- **4 Visual Variants**:
  - `"default"`: Clean slate container with sharp grid borders.
  - `"card"`: Elevated solid dark card with soft drop shadow.
  - `"glass"`: Translucent backdrop blur with frosted glass effect.
  - `"neon"`: Cyberpunk glowing cell borders and neon intensity radiance.
- **3 Size Scales**:
  - `"sm"`: 10px cells, 2px gap, 10px font.
  - `"md"`: 14px cells, 3px gap, 12px font.
  - `"lg"`: 20px cells, 4px gap, 14px font.
- **Standards & Composition**:
  - Exports `Heatmap`, `ActivityCalendar`, `ContributionGraph`, `HeatmapLegend`, `HeatmapCell`, and default export.
  - Full React `forwardRef` and explicit `displayName` across all exports.
  - 100% diff-invariant across `ir.description` changes; zero external runtime npm dependencies.
  - Registered in `NextjsWebAdapter.generate()` as a `GeneratedFile` at `components/heatmap.tsx` and exported in `codegen.__init__` as `render_heatmap_component`.















