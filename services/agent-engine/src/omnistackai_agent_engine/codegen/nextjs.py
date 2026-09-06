"""Next.js (App Router, TypeScript) framework adapter.

Turns an Application IR into a real Next.js project as a `GeneratedProject`: config, TypeScript
interfaces from entities, App Router API route handlers from the IR APIs, a page per screen, and an
overview page. Pure and deterministic — nothing is installed, built, run, or written to disk here.
"""

from __future__ import annotations

import json
import re

from ..application_ir import ApplicationIR, ApiEndpoint, Entity, FieldType, Screen
from .adapter import GenerationTarget
from .errors import GenerationError
from .files import GeneratedFile, GeneratedProject

_FIELD_TS: dict[FieldType, str] = {
    FieldType.STRING: "string",
    FieldType.TEXT: "string",
    FieldType.UUID: "string",
    FieldType.DATETIME: "string",
    FieldType.INT: "number",
    FieldType.FLOAT: "number",
    FieldType.BOOL: "boolean",
    FieldType.JSON: "unknown",
}


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "app"


def _route_dir(path: str) -> str:
    """Map an IR API path to a Next.js App Router directory (`{param}` -> `[param]`)."""

    segments = [seg for seg in path.split("/") if seg]
    mapped = [re.sub(r"^\{(.+)\}$", r"[\1]", seg) for seg in segments]
    return "/".join(mapped)


def _entity_interface(entity: Entity) -> str:
    lines = [f"export interface {entity.name} {{"]
    for field in entity.fields:
        optional = "" if field.required else "?"
        lines.append(f"  {field.name}{optional}: {_FIELD_TS[field.type]};")
    for relation in entity.relations:
        many = relation.kind.value in ("one_to_many", "many_to_many")
        suffix = "[]" if many else ""
        lines.append(f"  {relation.name}?: {relation.target_entity}{suffix};")
    lines.append("}")
    return "\n".join(lines)


def _types_file(ir: ApplicationIR) -> str:
    header = "// Generated from the Application IR. Do not edit by hand.\n"
    if not ir.entities:
        return header + "export {};\n"
    return header + "\n\n".join(_entity_interface(e) for e in ir.entities) + "\n"


def _route_file(apis: list[ApiEndpoint]) -> str:
    lines = ['import { NextResponse } from "next/server";', ""]
    for api in apis:
        auth = "required" if api.auth else "public"
        lines.append(f"// {api.method.value} {api.path}  (auth: {auth})")
        lines.append(f"export async function {api.method.value}(request: Request) {{")
        lines.append("  // TODO: implement. Scaffolded from the Application IR.")
        lines.append('  return NextResponse.json({ ok: false, error: "not_implemented" }, { status: 501 });')
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def _screen_page(screen: Screen) -> str:
    components = ", ".join(screen.components) or "none"
    actions = ", ".join(screen.actions) or "none"
    return (
        f"export default function {_pascal(screen.id)}Page() {{\n"
        f"  return (\n"
        f'    <main style={{{{ padding: 24 }}}}>\n'
        f"      <h1>{screen.id}</h1>\n"
        f"      <p>Role: {screen.role}</p>\n"
        f"      <p>Components: {components}</p>\n"
        f"      <p>Actions: {actions}</p>\n"
        f"    </main>\n"
        f"  );\n"
        f"}}\n"
    )


def _pascal(value: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[_-]+", value)) or "Screen"


def _overview_page(ir: ApplicationIR) -> str:
    entity_items = "".join(
        f"        <li>{e.name} ({len(e.fields)} fields)</li>\n" for e in ir.entities
    ) or "        <li>No entities</li>\n"
    screen_items = "".join(
        f'        <li><a href="/{s.id}">{s.id}</a> — {s.role}</li>\n' for s in ir.screens
    ) or "        <li>No screens</li>\n"
    return (
        "export default function HomePage() {\n"
        "  return (\n"
        '    <main style={{ padding: 24, maxWidth: 720, margin: "0 auto" }}>\n'
        f"      <h1>{ir.name}</h1>\n"
        f"      <p>{ir.description}</p>\n"
        f"      <p>Platforms: {', '.join(p.value for p in ir.platforms)}</p>\n"
        "      <h2>Entities</h2>\n"
        "      <ul>\n" + entity_items + "      </ul>\n"
        "      <h2>Screens</h2>\n"
        "      <ul>\n" + screen_items + "      </ul>\n"
        f"      <p>{len(ir.apis)} API route(s) generated.</p>\n"
        "    </main>\n"
        "  );\n"
        "}\n"
    )


_LAYOUT = (
    'import type { Metadata } from "next";\n\n'
    "export const metadata: Metadata = {\n"
    '  title: "%s",\n'
    '  description: "%s",\n'
    "};\n\n"
    "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
    "  return (\n"
    '    <html lang="en">\n'
    "      <body>{children}</body>\n"
    "    </html>\n"
    "  );\n"
    "}\n"
)

_NEXT_CONFIG = (
    "/** @type {import('next').NextConfig} */\n"
    "const securityHeaders = [\n"
    '  { key: "X-Content-Type-Options", value: "nosniff" },\n'
    '  { key: "X-Frame-Options", value: "DENY" },\n'
    '  { key: "Referrer-Policy", value: "no-referrer" },\n'
    "];\n\n"
    "const nextConfig = {\n"
    "  reactStrictMode: true,\n"
    "  poweredByHeader: false,\n"
    "  async headers() {\n"
    '    return [{ source: "/:path*", headers: securityHeaders }];\n'
    "  },\n"
    "};\n\n"
    "export default nextConfig;\n"
)

_TSCONFIG = {
    "compilerOptions": {
        "target": "ES2022", "lib": ["dom", "dom.iterable", "ES2022"], "strict": True,
        "noEmit": True, "esModuleInterop": True, "module": "esnext", "moduleResolution": "bundler",
        "resolveJsonModule": True, "isolatedModules": True, "jsx": "preserve", "incremental": True,
        "plugins": [{"name": "next"}], "paths": {"@/*": ["./*"]},
    },
    "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
    "exclude": ["node_modules"],
}


class NextjsWebAdapter:
    """Generates a Next.js App Router TypeScript project from an Application IR."""

    @property
    def target(self) -> GenerationTarget:
        return GenerationTarget.NEXTJS_WEB

    def generate(self, ir: ApplicationIR) -> GeneratedProject:
        if not isinstance(ir, ApplicationIR):
            raise GenerationError("ir must be an ApplicationIR")

        slug = _slug(ir.name)
        package_json = {
            "name": slug,
            "version": "0.1.0",
            "private": True,
            "scripts": {"dev": "next dev", "build": "next build", "start": "next start"},
            "dependencies": {"next": "15.5.4", "react": "18.3.1", "react-dom": "18.3.1"},
            "devDependencies": {
                "@types/node": "22.10.2", "@types/react": "18.3.12",
                "@types/react-dom": "18.3.1", "typescript": "5.6.3",
            },
        }

        files: list[GeneratedFile] = [
            GeneratedFile("package.json", json.dumps(package_json, indent=2) + "\n"),
            GeneratedFile("tsconfig.json", json.dumps(_TSCONFIG, indent=2) + "\n"),
            GeneratedFile("next.config.mjs", _NEXT_CONFIG),
            GeneratedFile(".gitignore", "node_modules/\n.next/\nout/\nnext-env.d.ts\n.env*.local\n"),
            GeneratedFile(".env.example", "# Public env vars only. Never commit secrets.\nNEXT_PUBLIC_APP_NAME=" + ir.name + "\n"),
            GeneratedFile("README.md", f"# {ir.name}\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR.\n\n```\npnpm install\npnpm dev\n```\n"),
            GeneratedFile("app/layout.tsx", _LAYOUT % (_escape_ts(ir.name), _escape_ts(ir.description))),
            GeneratedFile("app/globals.css", "body { font-family: system-ui, sans-serif; margin: 0; }\n"),
            GeneratedFile("app/page.tsx", _overview_page(ir)),
            GeneratedFile("lib/types.ts", _types_file(ir)),
        ]

        for screen in ir.screens:
            files.append(GeneratedFile(f"app/{screen.id}/page.tsx", _screen_page(screen)))

        by_dir: dict[str, list[ApiEndpoint]] = {}
        for api in ir.apis:
            route_dir = _route_dir(api.path) or "api"
            by_dir.setdefault(route_dir, []).append(api)
        for route_dir, apis in by_dir.items():
            files.append(GeneratedFile(f"app/{route_dir}/route.ts", _route_file(apis)))

        return GeneratedProject(self.target.value, tuple(files))


def _escape_ts(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
