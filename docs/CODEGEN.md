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
    - Reset button: emits `toast.info("Form values reset to initial state")`.
- **Quality & Safety**:
  - 100% offline, zero external npm dependencies, zero new IR fields, strict diff invariance across `ir.description`.







