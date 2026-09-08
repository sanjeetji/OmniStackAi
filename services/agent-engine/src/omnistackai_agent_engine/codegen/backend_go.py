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
from .data_access import PGX_REQUIRE, go_data_access_files
from .errors import GenerationError
from .files import GeneratedFile, GeneratedProject
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
            if field.required:
                lines.append(f'\t{go_name} {go} `json:"{field.name}"`')
            else:
                lines.append(f'\t{go_name} *{go} `json:"{field.name},omitempty"`')
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
        ")\n\n"
        "// Handlers carries the shared dependencies for the HTTP handlers.\n"
        "type Handlers struct {\n\tDB *sql.DB\n}\n\n"
        "func New(db *sql.DB) *Handlers {\n\treturn &Handlers{DB: db}\n}\n\n"
        "func writeJSON(w http.ResponseWriter, status int, v any) {\n"
        '\tw.Header().Set("Content-Type", "application/json")\n'
        "\tw.WriteHeader(status)\n"
        "\t_ = json.NewEncoder(w).Encode(v)\n"
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
) -> str:
    """Handlers as methods on *Handlers; unambiguous CRUD calls the store, the rest stay 501."""

    wirings = [(api, wire_endpoint(api, repo_entities, fk_by_entity)) for api in apis]
    uses_store = any(w is not None for _, w in wirings)
    uses_models = any(w is not None and w.op is Op.CREATE for _, w in wirings)

    imports = ['\t"net/http"']
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
            lines.append(f"\titems, err := store.List{wiring.entity}(r.Context(), h.DB, 100)")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append("\twriteJSON(w, http.StatusOK, items)")
        elif wiring.op is Op.LIST_BY:
            rel_pascal = _pascal(wiring.relation)
            lines.append(f'\titems, err := store.List{wiring.entity}By{rel_pascal}(r.Context(), h.DB, r.PathValue("{wiring.id_param}"), 100)')
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
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
            lines.append(f"\tid, err := store.Create{wiring.entity}(r.Context(), h.DB, m)")
            lines.append("\tif err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t\treturn\n\t}")
            lines.append('\twriteJSON(w, http.StatusCreated, map[string]string{"id": id})')
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
    lines.append("\tlog.Fatal(http.ListenAndServe(addr, mux))")
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
        go_mod = f"module {slug}\n\ngo 1.22\n"
        if has_db:
            go_mod += f"\nrequire {PGX_REQUIRE}\n"
        if has_auth:
            go_mod += f"\nrequire {GOLANG_JWT_REQUIRE}\n"

        stack_note = (
            "Go net/http with a PostgreSQL data-access layer (pgx driver)."
            if has_db
            else "Go standard library only."
        )
        env_example = f"# Backend config placeholders only. Never commit secrets.\nAPP_NAME={ir.name}\nADDR=:8080\nDATABASE_URL=postgres://localhost:5432/{slug}\n"
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

        repo_entities = frozenset(entity.name for entity in ir.entities) if has_db else frozenset()
        fk_by_entity = fk_relations(ir) if has_db else None
        if has_db:
            files.append(GeneratedFile("internal/handlers/handlers.go", _handlers_shared_file()))
        for segment in sorted(by_segment):
            content = (
                _handlers_file_wired(by_segment[segment], repo_entities, slug, fk_by_entity)
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

        return GeneratedProject(self.target.value, tuple(files))
