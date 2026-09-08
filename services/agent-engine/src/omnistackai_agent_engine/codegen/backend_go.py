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
from .field_validation import VALIDATOR_REQUIRE, go_validate_file, go_validate_tag, parse_field_rules
from .data_access import PGX_REQUIRE, go_data_access_files
from .errors import GenerationError
from .files import GeneratedFile, GeneratedProject
from .openapi import render_openapi_json
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


def _models_file(ir: ApplicationIR) -> str:
    needs_time = any(f.type is FieldType.DATETIME for e in ir.entities for f in e.fields)
    needs_json = any(f.type is FieldType.JSON for e in ir.entities for f in e.fields)
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
        lines.append(f"type {entity.name} struct {{")
        for field in entity.fields:
            go = _GO_TYPE[field.type]
            go_name = _pascal(field.name)
            tag = go_validate_tag(field, parse_field_rules(field))
            validate = f' validate:"{tag}"' if tag else ""
            if field.required:
                lines.append(f'\t{go_name} {go} `json:"{field.name}"{validate}`')
            else:
                lines.append(f'\t{go_name} *{go} `json:"{field.name},omitempty"{validate}`')
        lines.append("}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _handlers_shared_file() -> str:
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
) -> str:
    """Handlers as methods on *Handlers; unambiguous CRUD calls the store, the rest stay 501."""

    wirings = [(api, wire_endpoint(api, repo_entities, fk_by_entity)) for api in apis]
    uses_store = any(w is not None for _, w in wirings)
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
            lines.append(f"\ttotal, err := store.Count{wiring.entity}(r.Context(), h.DB, q)")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append(f"\titems, err := store.List{wiring.entity}(r.Context(), h.DB, limit, offset, sort, order, q)")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append('\tw.Header().Set("X-Total-Count", strconv.Itoa(total))')
            lines.append("\twriteJSON(w, http.StatusOK, items)")
        elif wiring.op is Op.LIST_BY:
            rel_pascal = _pascal(wiring.relation)
            lines.append("\tlimit, offset := parsePagination(r)")
            lines.append("\tsort, order := parseSort(r)")
            lines.append("\tq := parseSearch(r)")
            lines.append(f'\ttotal, err := store.Count{wiring.entity}By{rel_pascal}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"), q)')
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append(f'\titems, err := store.List{wiring.entity}By{rel_pascal}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"), limit, offset, sort, order, q)')
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
    return "\n".join(lines) + "\n"


def _main_file(slug: str, apis: list[ApiEndpoint], *, has_db: bool = False) -> str:
    lines = ["package main", "", "import ("]
    lines.append('\t"log"')
    lines.append('\t"net/http"')
    lines.append('\t"os"')
    module_imports = []
    if apis:
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
    lines.append('\taddr := ":8080"')
    lines.append('\tlog.Printf("listening on %s", addr)')
    lines.append("\tlog.Fatal(http.ListenAndServe(addr, corsMiddleware(mux)))")
    lines.append("}")
    return "\n".join(lines) + "\n"


class GoBackendAdapter:
    """Generates a Go net/http backend from an Application IR."""

    @property
    def target(self) -> GenerationTarget:
        return GenerationTarget.BACKEND_GO

    def generate(self, ir: ApplicationIR) -> GeneratedProject:
        if not isinstance(ir, ApplicationIR):
            raise GenerationError("ir must be an ApplicationIR")

        slug = _slug(ir.name)
        apis = list(ir.apis)

        by_segment: dict[str, list[ApiEndpoint]] = {}
        for api in apis:
            by_segment.setdefault(_segment(api.path), []).append(api)

        has_db = bool(ir.entities) and ir.project_strategy.database_strategy is DatabaseStrategy.POSTGRES
        has_auth = needs_auth(ir)

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
        files: list[GeneratedFile] = [
            GeneratedFile("go.mod", go_mod),
            GeneratedFile("main.go", _main_file(slug, apis, has_db=has_db)),
            GeneratedFile("internal/models/models.go", _models_file(ir)),
            GeneratedFile(".gitignore", "/bin/\n*.exe\n.env\n"),
            GeneratedFile(".env.example", env_example),
            GeneratedFile("README.md", f"# {ir.name} — Go backend\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR ({stack_note})\n\n```\ngo run .\n```\n"),
        ]

        if has_auth:
            files.append(GeneratedFile("internal/handlers/auth.go", go_auth_file(ir)))
        if has_validation:
            files.append(GeneratedFile("internal/handlers/validate.go", go_validate_file()))

        if has_db:
            files.append(GeneratedFile("internal/handlers/handlers.go", _handlers_shared_file()))
        for segment in sorted(by_segment):
            content = (
                _handlers_file_wired(by_segment[segment], repo_entities, slug, fk_by_entity, validated_entities)
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

        return GeneratedProject(self.target.value, tuple(files))
