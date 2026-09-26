"""Go backend framework adapter.

Turns an Application IR into a real, idiomatic Go standard-library net/http service as a
`GeneratedProject`: structs from entities, Go 1.22 method+pattern routes from the IR APIs (grouped by
resource), a main with a health endpoint, and packaging files. Pure and deterministic — nothing is
installed, built, run, or written to disk here. Proves one IR -> web + Python + Go targets.
"""

from __future__ import annotations

import re

from ..application_ir import ApplicationIR, ApiEndpoint, DatabaseStrategy, FieldType
from .adapter import GenerationTarget
from .auth_guard import GOLANG_JWT_REQUIRE, go_auth_file, needs_auth
from .auth_templates import AUTH_CONTRACT, EMAIL_ENV_EXAMPLE, GO_AUTH_HANDLERS, is_account_route
from .field_validation import VALIDATOR_REQUIRE, filter_fields, go_validate_file, go_validate_tag, parse_field_rules
from .data_access import PGX_REQUIRE, go_data_access_files
from .errors import GenerationError
from .files import GeneratedFile, GeneratedProject
from .openapi import render_openapi_json
from .workflow_routes import transition_routes
from .route_wiring import Op, fk_relations, wire_endpoint
from .schema_sql import render_postgres_schema
from .seed_sql import render_postgres_seed

_GO_TYPE: dict[FieldType, str] = {
    FieldType.STRING: "string",
    FieldType.TEXT: "string",
    FieldType.UUID: "string",
    FieldType.INT: "int64",
    FieldType.FLOAT: "float64",
    FieldType.BOOL: "bool",
    FieldType.DATETIME: "time.Time",
    FieldType.JSON: "json.RawMessage",
    FieldType.ATTACHMENT: "string",
}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app"


def _segment(path: str) -> str:
    first = path.strip("/").split("/")[0] if path.strip("/") else ""
    module = re.sub(r"\W+", "_", first).strip("_").lower()
    return module or "root"


def _pascal(value: str) -> str:
    # Uppercase the first letter of each part but preserve internal casing (driverId -> DriverId).
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _transition_handler_name(route) -> str:
    """`PublishPost`: the transition then the entity, matching how CRUD handlers are named."""
    return f"{_pascal(route.transition.name)}{route.workflow.entity}"


def _handler_name(method: str, path: str) -> str:
    tail = "".join(_pascal(seg) for seg in path.strip("/").split("/") if seg)
    return f"{method.capitalize()}{tail or 'Root'}"


def _path_params(path: str) -> list[str]:
    return re.findall(r"\{(\w+)\}", path)


def _validated_entities(ir: ApplicationIR) -> frozenset[str]:
    """Entity names with at least one field carrying go-playground validation rules (R-252)."""

    return frozenset(
        entity.name
        for entity in ir.entities
        if any(go_validate_tag(field, parse_field_rules(field)) for field in entity.fields)
    )


def _gofmt_tidy(generated: GeneratedFile) -> GeneratedFile:
    """Apply the whitespace rules gofmt enforces, to a generated Go file.

    Only two of them, because they are the two our emitters broke: a file ends with exactly one
    newline after its last statement, and consecutive blank lines collapse to one. This is not a
    formatter — the alignment gofmt does inside a struct is produced by the emitter that knows the
    columns. It is the part that is purely about how lines were joined together.
    """
    if not generated.path.endswith(".go") or generated.base64_encoded:
        return generated
    out: list[str] = []
    for line in generated.content.splitlines():
        if not line.strip() and out and not out[-1].strip():
            continue  # a second blank line in a row
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return GeneratedFile(generated.path, "\n".join(out) + "\n")


def _models_file(ir: ApplicationIR) -> str:
    needs_json = any(f.type is FieldType.JSON for e in ir.entities for f in e.fields)
    # R-502: audit timestamps always use time.Time, so always import "time" when entities exist.
    needs_time = bool(ir.entities) or any(f.type is FieldType.DATETIME for e in ir.entities for f in e.fields)
    lines = ["package models", ""]
    import_names: list[str] = []
    if needs_time:
        import_names.append("time")
    if needs_json:
        import_names.append("encoding/json")
    if import_names:
        lines.append("import (")
        lines.extend(f'\t"{name}"' for name in import_names)
        lines.append(")")
        lines.append("")
    if not ir.entities:
        lines.append("// No entities in the IR.")
        return "\n".join(lines) + "\n"
    for entity in ir.entities:
        declared_names = {field.name for field in entity.fields}
        lines.append(f"type {entity.name} struct {{")
        # R-587: collected first so the columns can be padded. gofmt aligns the names, types and
        # tags of a contiguous run of fields, and emitting single spaces meant every generated
        # backend arrived unformatted — an editor set to format on save rewrites the file the
        # first time a Go developer opens it.
        rows: list[tuple[str, str, str]] = []
        for field in entity.fields:
            go = _GO_TYPE[field.type]
            go_name = _pascal(field.name)
            tag = go_validate_tag(field, parse_field_rules(field))
            validate = f' validate:"{tag}"' if tag else ""
            if field.required:
                rows.append((go_name, go, f'`json:"{field.name}"{validate}`'))
            else:
                rows.append((go_name, f"*{go}", f'`json:"{field.name},omitempty"{validate}`'))
        # R-502: audit timestamp fields — omitted if the IR already declares them.
        if "created_at" not in declared_names:
            rows.append(("CreatedAt", "time.Time", '`json:"created_at"`'))
        if "updated_at" not in declared_names:
            rows.append(("UpdatedAt", "time.Time", '`json:"updated_at"`'))
        name_width = max((len(name) for name, _, _ in rows), default=0)
        type_width = max((len(kind) for _, kind, _ in rows), default=0)
        for name, kind, tag in rows:
            lines.append(f"\t{name.ljust(name_width)} {kind.ljust(type_width)} {tag}")
        lines.append("}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _handlers_shared_file(has_filters: bool = False) -> str:
    filters_helper = (
        "\n"
        "// parseFilters collects the raw query parameters so a store can apply the whitelisted ones\n"
        "// (per-field equality filters). The store only reads the field keys it declares, so unknown\n"
        "// query params are ignored and never reach SQL as identifiers.\n"
        "func parseFilters(r *http.Request) map[string]string {\n"
        "\tout := map[string]string{}\n"
        "\tfor k, v := range r.URL.Query() {\n"
        "\t\tif len(v) > 0 {\n"
        "\t\t\tout[k] = v[0]\n"
        "\t\t}\n"
        "\t}\n"
        "\treturn out\n"
        "}\n"
    ) if has_filters else ""
    return (
        "package handlers\n\n"
        "import (\n"
        '\t"database/sql"\n'
        '\t"encoding/json"\n'
        '\t"net/http"\n'
        '\t"strconv"\n'
        '\t"strings"\n'
        ")\n\n"
        "// Handlers carries the shared dependencies for the HTTP handlers.\n"
        "type Handlers struct {\n\tDB *sql.DB\n}\n\n"
        "func New(db *sql.DB) *Handlers {\n\treturn &Handlers{DB: db}\n}\n\n"
        "func writeJSON(w http.ResponseWriter, status int, v any) {\n"
        '\tw.Header().Set("Content-Type", "application/json")\n'
        "\tw.WriteHeader(status)\n"
        "\t_ = json.NewEncoder(w).Encode(v)\n"
        "}\n\n"
        "func parsePagination(r *http.Request) (int, int) {\n"
        "\tlimit := 100\n"
        "\toffset := 0\n"
        '\tif v := r.URL.Query().Get("limit"); v != "" {\n'
        "\t\tif n, err := strconv.Atoi(v); err == nil && n > 0 {\n"
        "\t\t\tlimit = n\n"
        "\t\t}\n"
        "\t}\n"
        '\tif v := r.URL.Query().Get("offset"); v != "" {\n'
        "\t\tif n, err := strconv.Atoi(v); err == nil && n >= 0 {\n"
        "\t\t\toffset = n\n"
        "\t\t}\n"
        "\t}\n"
        "\treturn limit, offset\n"
        "}\n\n"
        "func parseSort(r *http.Request) (string, string) {\n"
        '\tsort := r.URL.Query().Get("sort")\n'
        '\tif sort == "" {\n'
        '\t\tsort = "id"\n'
        "\t}\n"
        '\torder := r.URL.Query().Get("order")\n'
        '\tif strings.ToLower(order) == "desc" {\n'
        '\t\torder = "desc"\n'
        "\t} else {\n"
        '\t\torder = "asc"\n'
        "\t}\n"
        "\treturn sort, order\n"
        "}\n\n"
        "func parseSearch(r *http.Request) string {\n"
        '\treturn strings.TrimSpace(r.URL.Query().Get("q"))\n'
        "}\n"
        + filters_helper
    )


def _handlers_file(apis: list[ApiEndpoint]) -> str:
    """Unwired scaffold handlers (no database): free functions returning 501."""

    lines = ["package handlers", "", 'import "net/http"', ""]
    for api in apis:
        auth = "required" if api.auth else "public"
        lines.append(f"// {api.method.value} {api.path} (auth: {auth}) — scaffolded from the Application IR.")
        lines.append(f"func {_handler_name(api.method.value, api.path)}(w http.ResponseWriter, r *http.Request) {{")
        for param in _path_params(api.path):
            lines.append(f'\t// {param} := r.PathValue("{param}")')
        lines.append('\thttp.Error(w, "not implemented", http.StatusNotImplemented)')
        lines.append("}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _handlers_file_wired(
    apis: list[ApiEndpoint],
    repo_entities: frozenset[str],
    slug: str,
    fk_by_entity: dict[str, tuple[str, ...]] | None = None,
    validated_entities: frozenset[str] = frozenset(),
    filtered_entities: frozenset[str] = frozenset(),
    transitions: tuple = (),
) -> str:
    """Handlers as methods on *Handlers; unambiguous CRUD calls the store, the rest stay 501."""

    wirings = [(api, wire_endpoint(api, repo_entities, fk_by_entity)) for api in apis]
    uses_store = any(w is not None for _, w in wirings) or bool(transitions)
    uses_models = any(w is not None and w.op in (Op.CREATE, Op.UPDATE) for _, w in wirings)
    uses_lists = any(w is not None and w.op in (Op.LIST, Op.LIST_BY) for _, w in wirings)

    imports = ['\t"net/http"']
    if uses_lists:
        imports.append('\t"strconv"')
    if uses_models:
        imports.insert(0, '\t"encoding/json"')
    module_imports = []
    if uses_models:
        module_imports.append(f'\t"{slug}/internal/models"')
    if uses_store:
        module_imports.append(f'\t"{slug}/internal/store"')

    lines = ["package handlers", "", "import ("]
    lines += imports
    if module_imports:
        lines.append("")
        lines += module_imports
    lines.append(")")
    lines.append("")

    for api, wiring in wirings:
        name = _handler_name(api.method.value, api.path)
        auth = "required" if api.auth else "public"
        sig = f"func (h *Handlers) {name}(w http.ResponseWriter, r *http.Request) {{"
        lines.append(sig)
        if wiring is None:
            lines.append(f"\t// {api.method.value} {api.path} (auth: {auth}) — scaffold; no unambiguous entity mapping.")
            lines.append('\thttp.Error(w, "not implemented", http.StatusNotImplemented)')
        elif wiring.op is Op.LIST:
            lines.append("\tlimit, offset := parsePagination(r)")
            lines.append("\tsort, order := parseSort(r)")
            lines.append("\tq := parseSearch(r)")
            if wiring.entity in filtered_entities:
                lines.append("\tfilters := parseFilters(r)")
                count_call = f"store.Count{wiring.entity}(r.Context(), h.DB, q, filters)"
                list_call = f"store.List{wiring.entity}(r.Context(), h.DB, limit, offset, sort, order, q, filters)"
            else:
                count_call = f"store.Count{wiring.entity}(r.Context(), h.DB, q)"
                list_call = f"store.List{wiring.entity}(r.Context(), h.DB, limit, offset, sort, order, q)"
            lines.append(f"\ttotal, err := {count_call}")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append(f"\titems, err := {list_call}")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append('\tw.Header().Set("X-Total-Count", strconv.Itoa(total))')
            lines.append("\twriteJSON(w, http.StatusOK, items)")
        elif wiring.op is Op.LIST_BY:
            rel_pascal = _pascal(wiring.relation)
            lines.append("\tlimit, offset := parsePagination(r)")
            lines.append("\tsort, order := parseSort(r)")
            lines.append("\tq := parseSearch(r)")
            if wiring.entity in filtered_entities:
                lines.append("\tfilters := parseFilters(r)")
                count_call = f'store.Count{wiring.entity}By{rel_pascal}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"), q, filters)'
                list_call = f'store.List{wiring.entity}By{rel_pascal}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"), limit, offset, sort, order, q, filters)'
            else:
                count_call = f'store.Count{wiring.entity}By{rel_pascal}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"), q)'
                list_call = f'store.List{wiring.entity}By{rel_pascal}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"), limit, offset, sort, order, q)'
            lines.append(f"\ttotal, err := {count_call}")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append(f"\titems, err := {list_call}")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append('\tw.Header().Set("X-Total-Count", strconv.Itoa(total))')
            lines.append("\twriteJSON(w, http.StatusOK, items)")
        elif wiring.op is Op.GET:
            lines.append(f'\titem, err := store.Get{wiring.entity}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"))')
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append("\tif item == nil {\n\t\thttp.NotFound(w, r)\n\t\treturn\n\t}")
            lines.append("\twriteJSON(w, http.StatusOK, item)")
        elif wiring.op is Op.CREATE:
            lines.append(f"\tvar m models.{wiring.entity}")
            lines.append("\tif err := json.NewDecoder(r.Body).Decode(&m); err != nil {")
            lines.append('\t\thttp.Error(w, "invalid body", http.StatusBadRequest)\n\t\treturn\n\t}')
            if wiring.entity in validated_entities:
                lines.append("\tif !validateStruct(w, m) {\n\t\treturn\n\t}")
            lines.append(f"\tid, err := store.Create{wiring.entity}(r.Context(), h.DB, m)")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append('\twriteJSON(w, http.StatusCreated, map[string]string{"id": id})')
        elif wiring.op is Op.UPDATE:
            lines.append(f'\tid := r.PathValue("{wiring.id_param}")')
            lines.append(f"\tvar m models.{wiring.entity}")
            lines.append("\tif err := json.NewDecoder(r.Body).Decode(&m); err != nil {")
            lines.append('\t\thttp.Error(w, "invalid body", http.StatusBadRequest)\n\t\treturn\n\t}')
            if wiring.entity in validated_entities:
                lines.append("\tif !validateStruct(w, m) {\n\t\treturn\n\t}")
            lines.append(f"\tupdated, err := store.Update{wiring.entity}(r.Context(), h.DB, id, m)")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append("\tif updated == nil {\n\t\thttp.NotFound(w, r)\n\t\treturn\n\t}")
            lines.append("\twriteJSON(w, http.StatusOK, updated)")
        else:  # Op.DELETE
            lines.append(f'\tok, err := store.Delete{wiring.entity}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"))')
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append("\tif !ok {\n\t\thttp.NotFound(w, r)\n\t\treturn\n\t}")
            lines.append("\tw.WriteHeader(http.StatusNoContent)")
        lines.append("}")
        lines.append("")

    # R-589: the lifecycle transitions, refused here rather than merely hidden in the interface —
    # the same rule the Python backend applies. Go's guard is middleware at the route (see main.go),
    # so this handler enforces the from-state and leaves the role to RequireRoles.
    for route in transitions:
        allowed = route.transition.sources or route.workflow.states
        field_pascal = _pascal(route.workflow.field)
        allowed_go = ", ".join(f'"{state}"' for state in allowed)
        lines.append(f"func (h *Handlers) {_transition_handler_name(route)}(w http.ResponseWriter, r *http.Request) {{")
        lines.append(f'\titem, err := store.Get{route.workflow.entity}(r.Context(), h.DB, r.PathValue("{route.id_param}"))')
        lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
        lines.append("\tif item == nil {\n\t\thttp.NotFound(w, r)\n\t\treturn\n\t}")
        lines.append(f"\tallowed := map[string]bool{{{', '.join(f'{s}: true' for s in allowed_go.split(', '))}}}")
        lines.append(f"\tif !allowed[item.{field_pascal}] {{")
        lines.append(f'\t\thttp.Error(w, "cannot {route.transition.name} from "+item.{field_pascal}+"; allowed from: {", ".join(allowed)}", http.StatusConflict)')
        lines.append("\t\treturn\n\t}")
        lines.append(f'\tupdated, err := store.Set{route.workflow.entity}{field_pascal}(r.Context(), h.DB, r.PathValue("{route.id_param}"), "{route.transition.to}")')
        lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
        lines.append("\twriteJSON(w, http.StatusOK, updated)")
        lines.append("}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _main_file(slug: str, apis: list[ApiEndpoint], *, has_db: bool = False, transitions: tuple = (), has_auth: bool = False) -> str:
    lines = ["package main", "", "import ("]
    lines.append('\t"log"')
    lines.append('\t"net/http"')
    lines.append('\t"os"')
    module_imports = []
    if apis or (has_auth and has_db):
        module_imports.append(f'\t"{slug}/internal/handlers"')
    if has_db:
        module_imports.append(f'\t"{slug}/internal/store"')
    if module_imports:
        lines.append("")
        lines += module_imports
    lines.append(")")
    lines.append("")
    lines.append("func corsMiddleware(next http.Handler) http.Handler {")
    lines.append("\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {")
    lines.append('\t\torigin := os.Getenv("CORS_ALLOWED_ORIGIN")')
    lines.append('\t\tif origin == "" {')
    lines.append('\t\t\torigin = "*"')
    lines.append("\t\t}")
    lines.append('\t\tw.Header().Set("Access-Control-Allow-Origin", origin)')
    lines.append('\t\tw.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")')
    lines.append('\t\tw.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")')
    lines.append('\t\tw.Header().Set("Access-Control-Expose-Headers", "X-Total-Count")')
    lines.append("\t\tif r.Method == http.MethodOptions {")
    lines.append("\t\t\tw.WriteHeader(http.StatusNoContent)")
    lines.append("\t\t\treturn")
    lines.append("\t\t}")
    lines.append("\t\tnext.ServeHTTP(w, r)")
    lines.append("\t})")
    lines.append("}")
    lines.append("")
    lines.append("func main() {")
    if has_db:
        lines.append("\tdb, err := store.Open()")
        lines.append("\tif err != nil {\n\t\tlog.Fatal(err)\n\t}")
        lines.append("\tdefer db.Close()")
        lines.append("\th := handlers.New(db)")
        lines.append("")
    lines.append("\tmux := http.NewServeMux()")
    lines.append('\tmux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {')
    lines.append('\t\tw.Header().Set("Content-Type", "application/json")')
    lines.append('\t\t_, _ = w.Write([]byte(`{"status":"ok"}`))')
    lines.append("\t})")
    for api in apis:
        target = f"h.{_handler_name(api.method.value, api.path)}" if has_db else f"handlers.{_handler_name(api.method.value, api.path)}"
        if api.required_roles:
            role_args = ", ".join(f'"{role}"' for role in api.required_roles)
            target = f"handlers.RequireRoles({target}, {role_args})"
        elif api.auth:
            target = f"handlers.RequireAuth({target})"
        lines.append(f'\tmux.HandleFunc("{api.method.value} {api.path}", {target})')
    # R-589: transition routes, role-guarded at the route like every other handler.
    for route in transitions:
        target = f"h.{_transition_handler_name(route)}"
        if route.roles:
            role_args = ", ".join(f'"{role}"' for role in route.roles)
            target = f"handlers.RequireRoles({target}, {role_args})"
        lines.append(f'\tmux.HandleFunc("POST {route.path}", {target})')
    # R-591: the account flow. It needs the users table, so it exists only with a database.
    if has_auth and has_db:
        for handler, (method, path) in _AUTH_ROUTES:
            lines.append(f'\tmux.HandleFunc("{method} {path}", h.{handler})')
    lines.append('\tport := os.Getenv("PORT")')
    lines.append('\tif port == "" {')
    lines.append('\t\tport = "8080"')
    lines.append('\t}')
    lines.append('\taddr := ":" + port')
    lines.append('\tif envAddr := os.Getenv("ADDR"); envAddr != "" {')
    lines.append('\t\taddr = envAddr')
    lines.append('\t}')
    lines.append('\tlog.Printf("listening on %s", addr)')
    lines.append("\tlog.Fatal(http.ListenAndServe(addr, corsMiddleware(mux)))")
    lines.append("}")
    return "\n".join(lines) + "\n"


_AUTH_ROUTES = (
    ("AuthRegister", AUTH_CONTRACT["register"]),
    ("AuthLogin", AUTH_CONTRACT["login"]),
    ("AuthMe", AUTH_CONTRACT["me"]),
    ("AuthLogout", AUTH_CONTRACT["logout"]),
    ("AuthForgotPassword", AUTH_CONTRACT["forgot"]),
    ("AuthResetPassword", AUTH_CONTRACT["reset"]),
)


class GoBackendAdapter:
    """Generates a Go net/http backend from an Application IR."""

    @property
    def target(self) -> GenerationTarget:
        return GenerationTarget.BACKEND_GO

    def generate(self, ir: ApplicationIR) -> GeneratedProject:
        if not isinstance(ir, ApplicationIR):
            raise GenerationError("ir must be an ApplicationIR")

        slug = _slug(ir.name)
        has_db = bool(ir.entities) and ir.project_strategy.database_strategy is DatabaseStrategy.POSTGRES
        has_auth = needs_auth(ir)
        # R-591: with the account flow generated, it owns /auth/*; a plan's own copy would register
        # the same pattern twice, and Go's ServeMux panics on that at start-up.
        apis = [api for api in ir.apis if not (has_auth and has_db and is_account_route(api.path))]

        by_segment: dict[str, list[ApiEndpoint]] = {}
        for api in apis:
            by_segment.setdefault(_segment(api.path), []).append(api)

        repo_entities = frozenset(entity.name for entity in ir.entities) if has_db else frozenset()
        fk_by_entity = fk_relations(ir) if has_db else None
        # Validation is enforced only where it can act: a wired CREATE handler whose entity has rules.
        validated_entities = _validated_entities(ir) if has_db else frozenset()
        has_validation = bool(validated_entities) and any(
            (wiring := wire_endpoint(api, repo_entities, fk_by_entity)) is not None
            and wiring.op in (Op.CREATE, Op.UPDATE)
            and wiring.entity in validated_entities
            for api in apis
        )

        go_mod = f"module {slug}\n\ngo 1.22\n"
        if has_db:
            go_mod += f"\nrequire {PGX_REQUIRE}\n"
        if has_auth:
            go_mod += f"\nrequire {GOLANG_JWT_REQUIRE}\n"
        if has_validation:
            go_mod += f"\nrequire {VALIDATOR_REQUIRE}\n"

        stack_note = (
            "Go net/http with a PostgreSQL data-access layer (pgx driver)."
            if has_db
            else "Go standard library only."
        )
        env_example = f"# Backend config placeholders only. Never commit secrets.\nAPP_NAME={ir.name}\nADDR=:8080\nDATABASE_URL=postgres://localhost:5432/{slug}\nCORS_ALLOWED_ORIGIN=*\n"
        if has_auth:
            env_example += "JWT_SECRET=\n"
            if has_db:
                env_example += EMAIL_ENV_EXAMPLE
        env_example += "STORAGE_ENDPOINT=http://localhost:9000\nSTORAGE_BUCKET=uploads\nSTORAGE_ACCESS_KEY=minioadmin\nSTORAGE_SECRET_KEY=minioadmin\n"
        files: list[GeneratedFile] = [
            GeneratedFile("go.mod", go_mod),
            GeneratedFile("main.go", _main_file(slug, apis, has_db=has_db, transitions=transition_routes(ir) if has_db else (), has_auth=has_auth)),
            GeneratedFile("internal/models/models.go", _models_file(ir)),
            GeneratedFile(".gitignore", "/bin/\n*.exe\n.env\n"),
            GeneratedFile(".env.example", env_example),
            GeneratedFile(
                "README.md",
                # R-561: this used to say `go run .` alone, which fails on a fresh clone with
                # "missing go.sum entry" for every dependency — go.sum cannot be generated here
                # because it holds hashes of module archives we do not download. `go mod tidy`
                # rather than `go mod download`: the generated go.mod lists direct requires only,
                # so downloading the build list still leaves the transitive ones missing and the
                # build failing with the same error. Tidy resolves them from the imports and
                # writes go.sum, which is the same "install first" step the Python backend had.
                f"# {ir.name} — Go backend\n\n{ir.description}\n\nGenerated by OmniStackAI from "
                f"the Application IR ({stack_note})\n\nResolve the dependencies once, then run:\n\n"
                "```\ngo mod tidy\ngo run .\n```\n",
            ),
        ]

        if has_auth:
            files.append(GeneratedFile("internal/handlers/auth.go", go_auth_file(ir)))
            if has_db:
                files.append(GeneratedFile("internal/handlers/auth_routes.go", GO_AUTH_HANDLERS))
        if has_validation:
            files.append(GeneratedFile("internal/handlers/validate.go", go_validate_file()))

        filtered_entities = (
            frozenset(entity.name for entity in ir.entities if filter_fields(entity)) if has_db else frozenset()
        )
        has_filters = bool(filtered_entities)
        if has_db:
            files.append(GeneratedFile("internal/handlers/handlers.go", _handlers_shared_file(has_filters)))
        for segment in sorted(by_segment):
            content = (
                _handlers_file_wired(
                    by_segment[segment], repo_entities, slug, fk_by_entity, validated_entities, filtered_entities,
                    tuple(r for r in transition_routes(ir) if r.path.strip('/').split('/')[0] == segment),
                )
                if has_db
                else _handlers_file(by_segment[segment])
            )
            files.append(GeneratedFile(f"internal/handlers/{segment}.go", content))

        if has_db:
            files.append(GeneratedFile("migrations/0001_init.sql", render_postgres_schema(ir)))
            for path, content in go_data_access_files(ir, slug):
                files.append(GeneratedFile(path, content))
            seed = render_postgres_seed(ir)
            if seed:
                files.append(GeneratedFile("migrations/0002_seed.sql", seed))

        if ir.apis:
            files.append(GeneratedFile("openapi.json", render_openapi_json(ir)))

        # R-587: normalise every .go file in one place rather than trusting each emitter to end
        # cleanly. Four of them did not, and a Go developer's editor rewrites an unformatted file
        # the first time they open it — on code they never touched. Doing it here means a future
        # emitter cannot reintroduce the problem by forgetting.
        return GeneratedProject(self.target.value, tuple(_gofmt_tidy(f) for f in files))
