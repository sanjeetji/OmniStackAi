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
from .errors import GenerationError
from .files import GeneratedFile, GeneratedProject
from .schema_sql import render_postgres_schema

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


def _handlers_file(apis: list[ApiEndpoint]) -> str:
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


def _main_file(slug: str, apis: list[ApiEndpoint]) -> str:
    lines = ["package main", "", "import ("]
    lines.append('\t"log"')
    lines.append('\t"net/http"')
    if apis:
        lines.append("")
        lines.append(f'\t"{slug}/internal/handlers"')
    lines.append(")")
    lines.append("")
    lines.append("func main() {")
    lines.append("\tmux := http.NewServeMux()")
    lines.append('\tmux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {')
    lines.append('\t\tw.Header().Set("Content-Type", "application/json")')
    lines.append('\t\t_, _ = w.Write([]byte(`{"status":"ok"}`))')
    lines.append("\t})")
    for api in apis:
        lines.append(f'\tmux.HandleFunc("{api.method.value} {api.path}", handlers.{_handler_name(api.method.value, api.path)})')
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

        files: list[GeneratedFile] = [
            GeneratedFile("go.mod", f"module {slug}\n\ngo 1.22\n"),
            GeneratedFile("main.go", _main_file(slug, apis)),
            GeneratedFile("internal/models/models.go", _models_file(ir)),
            GeneratedFile(".gitignore", "/bin/\n*.exe\n.env\n"),
            GeneratedFile(".env.example", f"# Backend config placeholders only. Never commit secrets.\nAPP_NAME={ir.name}\nADDR=:8080\nDATABASE_URL=postgres://localhost:5432/{slug}\n"),
            GeneratedFile("README.md", f"# {ir.name} — Go backend\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR (Go standard library only).\n\n```\ngo run .\n```\n"),
        ]
        for segment in sorted(by_segment):
            files.append(GeneratedFile(f"internal/handlers/{segment}.go", _handlers_file(by_segment[segment])))

        if ir.entities and ir.project_strategy.database_strategy is DatabaseStrategy.POSTGRES:
            files.append(GeneratedFile("migrations/0001_init.sql", render_postgres_schema(ir)))

        return GeneratedProject(self.target.value, tuple(files))
