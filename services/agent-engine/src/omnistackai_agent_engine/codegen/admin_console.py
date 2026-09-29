"""PC-100: the generated admin console - an app shell, a real-data dashboard, a page per entity.

Before this task the admin console was the web app's navbar over a dashboard of invented figures
("99.98% system health", "< 24ms latency", a 72% bar on every card) and whatever screens the plan
had; there was no place to manage an entity's records. Now:

- an app shell: a collapsible sidebar listing every entity and page, a top bar, a command menu
  (Ctrl/Cmd+K) and a drawer at phone width;
- a dashboard built only from the API: record counts, a chart of them, records added per day and
  the latest records of each entity;
- a management page per listable entity: a server-sorted, searched and paginated table, row
  selection, bulk delete, CSV export, and create/edit in a drawer whose form is validated from the
  plan's field rules, with related records picked from a list; entities with coordinates get a map.

Only the operations the plan's API really has are offered, through the functions lib/api.ts
exports (``nextjs.entity_api_functions``). Everything is styled with the design tokens, so the
console wears the project's design direction.
"""

from __future__ import annotations

import json
import re

from ..application_ir import ApplicationIR, Entity, FieldType, RelationKind
from .field_validation import parse_field_rules
from .route_wiring import Op
from .schema_sql import table_name

#: Fields the database fills in; shown, never edited.
SYSTEM_FIELDS = frozenset({"id", "created_at", "updated_at", "created_by"})
_FK_KINDS = frozenset({RelationKind.MANY_TO_ONE, RelationKind.ONE_TO_ONE})
_LAT = ("lat", "latitude")
_LNG = ("lng", "lon", "long", "longitude")
_LABEL_PREFERENCE = ("name", "title", "label", "full_name", "display_name", "email", "code", "sku")
_AUTH_ROUTES = ("/login", "/register", "/forgot-password", "/reset-password")


def _title(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    parts = [p for p in re.split(r"[_\s-]+", spaced) if p]
    return " ".join(p if p.isupper() and len(p) > 1 else p[:1].upper() + p[1:].lower() for p in parts)


def _slug(entity: Entity) -> str:
    """The console's route segment for an entity: the plural of its table ("order_item" -> "order_items")."""
    from .nextjs import _plural

    return _plural(table_name(entity.name))


def _plural_label(entity: Entity) -> str:
    return _title(_slug(entity))


def _ts(value: str) -> str:
    return json.dumps(value)


def managed_entities(ir: ApplicationIR) -> list[tuple[Entity, dict[Op, str]]]:
    """Entities the console can manage: those the API can list, in plan order."""
    from .nextjs import entity_api_functions

    functions = entity_api_functions(ir)
    return [(entity, functions[entity.name]) for entity in ir.entities
            if Op.LIST in functions.get(entity.name, {})]


def manage_path(entity: Entity) -> str:
    return f"/manage/{_slug(entity)}"


def _label_key(entity: Entity) -> str:
    strings = [f.name for f in entity.fields if f.type in (FieldType.STRING, FieldType.TEXT)]
    for preferred in _LABEL_PREFERENCE:
        if preferred in strings:
            return preferred
    return strings[0] if strings else "id"


def _coordinates(entity: Entity) -> tuple[str, str] | None:
    numeric = {f.name for f in entity.fields if f.type in (FieldType.FLOAT, FieldType.INT)}
    lat = next((n for n in _LAT if n in numeric), None)
    lng = next((n for n in _LNG if n in numeric), None)
    return (lat, lng) if lat and lng else None


# ── the per-entity page ────────────────────────────────────────────────────────────────────────


def _field_specs(entity: Entity, ir: ApplicationIR, listable: dict[str, dict[Op, str]]) -> tuple[list[str], list[str]]:
    """The FIELDS array entries (as TS object literals) and the imports relations need."""
    specs: list[str] = []
    imports: list[str] = []
    long_kinds = {FieldType.TEXT, FieldType.JSON}
    shown = 0
    for field in entity.fields:
        rules = parse_field_rules(field)
        editable = field.name not in SYSTEM_FIELDS
        in_table = field.name != "id" and field.type not in long_kinds and (shown < 6 or field.name == "created_at")
        if in_table:
            shown += 1
        parts = [
            f"name: {_ts(field.name)}", f"label: {_ts(_title(field.name))}", f"kind: {_ts(field.type.value)}",
            f"required: {'true' if field.required and editable else 'false'}",
            f"editable: {'true' if editable else 'false'}", f"inTable: {'true' if in_table else 'false'}",
        ]
        if rules.enum:
            parts.append(f"enumValues: {json.dumps(list(rules.enum))}")
        if rules.max_length is not None:
            parts.append(f"maxLength: {rules.max_length}")
        if rules.minimum is not None:
            parts.append(f"min: {rules.minimum}")
        if rules.maximum is not None:
            parts.append(f"max: {rules.maximum}")
        specs.append("{ " + ", ".join(parts) + " }")
    for relation in entity.relations:
        if relation.kind not in _FK_KINDS:
            continue
        name = f"{relation.name}_id"
        if any(f.name == name for f in entity.fields):
            continue
        parts = [
            f"name: {_ts(name)}", f"label: {_ts(_title(relation.name))}", 'kind: "uuid"',
            "required: false", "editable: true", "inTable: true",
        ]
        target = next((e for e in ir.entities if e.name == relation.target_entity), None)
        target_list = listable.get(relation.target_entity, {}).get(Op.LIST)
        if target is not None and target_list:
            fn = f"{target_list}WithCount"
            imports.append(fn)
            parts.append(
                f"relation: {{ labelKey: {_ts(_label_key(target))}, "
                f"load: async () => (await {fn}({{ params: {{ limit: 100 }} }})).data as unknown as Row[] }}"
            )
        specs.append("{ " + ", ".join(parts) + " }")
    return specs, imports


def entity_page(entity: Entity, functions: dict[Op, str], ir: ApplicationIR) -> str:
    from .nextjs import entity_api_functions

    listable = entity_api_functions(ir)
    specs, relation_imports = _field_specs(entity, ir, listable)
    list_fn = f"{functions[Op.LIST]}WithCount"
    imports = [list_fn, *relation_imports]
    props = [
        f"      title={{{_ts(_plural_label(entity))}}}",
        f"      singular={{{_ts(_title(entity.name).lower())}}}",
        f"      slug={{{_ts(_slug(entity))}}}",
        "      fields={FIELDS}",
        f"      list={{async (params) => {{ const r = await {list_fn}({{ params }}); "
        "return { data: r.data as unknown as Row[], total: r.total }; }}",
    ]
    if Op.CREATE in functions:
        imports.append(functions[Op.CREATE])
        props.append(f"      create={{(data) => {functions[Op.CREATE]}(data as Partial<{entity.name}>)}}")
    if Op.UPDATE in functions:
        imports.append(functions[Op.UPDATE])
        props.append(f"      update={{(id, data) => {functions[Op.UPDATE]}(id, data as Partial<{entity.name}>)}}")
    if Op.DELETE in functions:
        imports.append(functions[Op.DELETE])
        props.append(f"      remove={{(id) => {functions[Op.DELETE]}(id)}}")
    coordinates = _coordinates(entity)
    if coordinates:
        props.append(f"      coordinates={{{{ lat: {_ts(coordinates[0])}, lng: {_ts(coordinates[1])} }}}}")
    unique_imports = list(dict.fromkeys(imports))
    type_import = f'import type {{ {entity.name} }} from "@/lib/types";\n' if (
        Op.CREATE in functions or Op.UPDATE in functions) else ""
    return (
        '"use client";\n\n'
        f"// Generated by OmniStackAI (PC-100): the {_plural_label(entity).lower()} the API can reach.\n"
        'import { EntityManager, type FieldSpec, type Row } from "@/components/admin/entity-manager";\n'
        f'import {{ {", ".join(unique_imports)} }} from "@/lib/api";\n'
        f"{type_import}\n"
        "const FIELDS: FieldSpec[] = [\n"
        + "".join(f"  {spec},\n" for spec in specs)
        + "];\n\n"
        f"export default function Manage{entity.name}Page() {{\n"
        "  return (\n"
        "    <EntityManager\n"
        + "\n".join(props) + "\n"
        "    />\n"
        "  );\n"
        "}\n"
    )


# ── navigation, shell and dashboard ─────────────────────────────────────────────────────────────


def nav_file(ir: ApplicationIR, has_auth: bool) -> str:
    from .nextjs import _nav_label, _screen_intent

    items = [{"href": "/", "label": "Dashboard", "icon": "dashboard", "group": "Overview"}]
    creates = []
    for entity, functions in managed_entities(ir):
        items.append({"href": manage_path(entity), "label": _plural_label(entity), "icon": "table", "group": "Manage"})
        if Op.CREATE in functions:
            creates.append({"href": f"{manage_path(entity)}?new=1", "label": f"New {_title(entity.name).lower()}"})
    skip = {r.lstrip("/") for r in _AUTH_ROUTES} if has_auth else set()
    for screen in ir.screens:
        # A detail screen needs a record to show; it is reached from its list, not the sidebar. The
        # planner often gives one a form ("order_detail" edits an order), so its name decides too.
        if screen.id in skip or _screen_intent(screen) == "detail" or "detail" in screen.id:
            continue
        items.append({"href": f"/{screen.id}", "label": _nav_label(screen.id), "icon": "page", "group": "Pages"})
    if has_auth:
        items.append({"href": "/users", "label": "Users and roles", "icon": "users", "group": "Access"})
    return (
        "// Generated by OmniStackAI (PC-100): the admin console's navigation, from the plan.\n\n"
        'export type NavIcon = "dashboard" | "table" | "page" | "users";\n'
        'export interface NavItem { href: string; label: string; icon: NavIcon; group: "Overview" | "Manage" | "Pages" | "Access" }\n\n'
        f"export const APP_NAME = {_ts(ir.name)};\n\n"
        f"export const NAV: NavItem[] = {json.dumps(items, indent=2)};\n\n"
        f"export const CREATE_ACTIONS: {{ href: string; label: string }}[] = {json.dumps(creates, indent=2)};\n"
    )


def dashboard_page(ir: ApplicationIR) -> str:
    """The admin home: every figure is read from the API when the page opens."""
    sources: list[str] = []
    imports: list[str] = []
    for entity, functions in managed_entities(ir):
        fn = f"{functions[Op.LIST]}WithCount"
        imports.append(fn)
        field_names = {f.name for f in entity.fields}
        time_key = "created_at" if "created_at" in field_names else None
        sort = '{ limit: 100, sort: "created_at", order: "desc" as const }' if time_key else "{ limit: 100 }"
        sources.append(
            "  {\n"
            f"    key: {_ts(_slug(entity))},\n"
            f"    label: {_ts(_plural_label(entity))},\n"
            f"    href: {_ts(manage_path(entity))},\n"
            f"    createHref: {_ts(manage_path(entity) + '?new=1') if Op.CREATE in functions else 'null'},\n"
            f"    titleKey: {_ts(_label_key(entity))},\n"
            f"    timeKey: {_ts(time_key) if time_key else 'null'},\n"
            f"    load: async () => {{ const r = await {fn}({{ params: {sort} }}); "
            "return { data: r.data as unknown as Record<string, unknown>[], total: r.total }; },\n"
            "  },\n"
        )
    api_import = f'import {{ {", ".join(imports)} }} from "@/lib/api";\n' if imports else ""
    return (
        _DASHBOARD_HEAD
        + api_import
        # Found live: "Store Admin admin" - a name that already says so is not repeated.
        + f"\nconst TITLE = {_ts(ir.name if ir.name.lower().endswith('admin') else ir.name + ' admin')};\n\n"
        + "const SOURCES: Source[] = [\n" + "".join(sources) + "];\n"
        + _DASHBOARD_BODY
    )


def shell_component(has_auth: bool) -> str:
    auth_import = 'import { useAuth } from "@/components/auth-provider";\n' if has_auth else ""
    account = _ACCOUNT_WITH_AUTH if has_auth else _ACCOUNT_WITHOUT_AUTH
    return _SHELL.replace("__AUTH_IMPORT__", auth_import).replace("__ACCOUNT__", account)


def admin_console_files(ir: ApplicationIR, has_auth: bool) -> list[tuple[str, str]]:
    files = [
        ("components/admin/nav.ts", nav_file(ir, has_auth)),
        ("components/admin/admin-shell.tsx", shell_component(has_auth)),
        ("components/admin/entity-manager.tsx", ENTITY_MANAGER),
        ("components/admin/record-map.tsx", RECORD_MAP),
    ]
    for entity, functions in managed_entities(ir):
        files.append((f"app{manage_path(entity)}/page.tsx", entity_page(entity, functions, ir)))
    return files


# ── static components ───────────────────────────────────────────────────────────────────────────

_SHELL = r'''"use client";

// Generated by OmniStackAI (PC-100): the admin console's frame - sidebar, top bar, command menu.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Command } from "cmdk";
import { AnimatePresence, motion } from "framer-motion";
import {
  FileText, LayoutDashboard, Menu, PanelLeftClose, PanelLeftOpen, Plus, Search, ShieldCheck, Table2, X,
  type LucideIcon,
} from "lucide-react";
import { APP_NAME, CREATE_ACTIONS, NAV, type NavIcon, type NavItem } from "./nav";
__AUTH_IMPORT__
const ICONS: Record<NavIcon, LucideIcon> = { dashboard: LayoutDashboard, table: Table2, page: FileText, users: ShieldCheck };
const GROUPS: NavItem["group"][] = ["Overview", "Manage", "Pages", "Access"];
const BARE_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

function NavList({ pathname, collapsed, onNavigate }: { pathname: string; collapsed: boolean; onNavigate?: () => void }) {
  return (
    <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Admin">
      {GROUPS.map((group) => {
        const items = NAV.filter((item) => item.group === group);
        if (items.length === 0) return null;
        return (
          <div key={group} className="mb-5">
            {!collapsed && (
              <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{group}</p>
            )}
            <ul className="space-y-1">
              {items.map((item) => {
                const Icon = ICONS[item.icon];
                const active = isActive(pathname, item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={onNavigate}
                      title={collapsed ? item.label : undefined}
                      aria-current={active ? "page" : undefined}
                      className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                        active ? "bg-primary text-primary-foreground shadow-sm" : "text-foreground/80 hover:bg-muted hover:text-foreground"
                      } ${collapsed ? "justify-center px-2" : ""}`}
                    >
                      <Icon className="h-4 w-4 shrink-0" aria-hidden />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

function Brand({ collapsed }: { collapsed: boolean }) {
  return (
    <Link href="/" className="flex h-14 items-center gap-3 border-b px-4">
      <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-sm font-bold text-primary-foreground">
        {APP_NAME.slice(0, 1).toUpperCase()}
      </span>
      {!collapsed && (
        <span className="truncate font-semibold" style={{ fontFamily: "var(--font-heading, var(--font-sans))" }}>
          {APP_NAME}
        </span>
      )}
    </Link>
  );
}

function CommandMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  const go = (href: string) => { onClose(); router.push(href); };
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 px-4 pt-[12vh]"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onMouseDown={onClose}
        >
          <motion.div
            role="dialog" aria-modal="true" aria-label="Search and jump"
            className="w-full max-w-lg overflow-hidden rounded-xl border bg-popover shadow-2xl"
            initial={{ y: -8, scale: 0.98 }} animate={{ y: 0, scale: 1 }} exit={{ y: -8, scale: 0.98 }}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <Command label="Search and jump" loop>
              <div className="flex items-center gap-2 border-b px-4">
                <Search className="h-4 w-4 text-muted-foreground" aria-hidden />
                <Command.Input autoFocus placeholder="Search pages and actions..." className="h-12 w-full bg-transparent text-sm outline-none" />
              </div>
              <Command.List className="max-h-80 overflow-y-auto p-2">
                <Command.Empty className="px-3 py-6 text-center text-sm text-muted-foreground">Nothing matches.</Command.Empty>
                {CREATE_ACTIONS.length > 0 && (
                  <Command.Group heading="Create" className="px-1 text-xs text-muted-foreground">
                    {CREATE_ACTIONS.map((action) => (
                      <Command.Item key={action.href} value={action.label} onSelect={() => go(action.href)}
                        className="flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground data-[selected=true]:bg-muted">
                        <Plus className="h-4 w-4" aria-hidden /> {action.label}
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}
                <Command.Group heading="Go to" className="px-1 text-xs text-muted-foreground">
                  {NAV.map((item) => {
                    const Icon = ICONS[item.icon];
                    return (
                      <Command.Item key={item.href} value={`${item.label} ${item.group}`} onSelect={() => go(item.href)}
                        className="flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground data-[selected=true]:bg-muted">
                        <Icon className="h-4 w-4" aria-hidden /> {item.label}
                      </Command.Item>
                    );
                  })}
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

__ACCOUNT__

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() || "/";
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => setMobileOpen(false), [pathname]);

  const current = useMemo(
    () => [...NAV].sort((a, b) => b.href.length - a.href.length).find((item) => isActive(pathname, item.href)),
    [pathname],
  );

  if (BARE_ROUTES.includes(pathname)) return <>{children}</>;

  return (
    <div className="flex min-h-screen bg-muted text-foreground">
      <aside className={`sticky top-0 hidden h-screen shrink-0 flex-col border-r bg-card transition-[width] duration-200 md:flex ${collapsed ? "w-[68px]" : "w-64"}`}>
        <Brand collapsed={collapsed} />
        <NavList pathname={pathname} collapsed={collapsed} />
        <button
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          className="m-3 flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <PanelLeftOpen className="h-4 w-4" aria-hidden /> : <><PanelLeftClose className="h-4 w-4" aria-hidden /> Collapse</>}
        </button>
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div className="fixed inset-0 z-40 md:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} aria-hidden />
            <motion.aside
              className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-card shadow-xl"
              initial={{ x: -300 }} animate={{ x: 0 }} exit={{ x: -300 }} transition={{ type: "spring", stiffness: 380, damping: 36 }}
            >
              <div className="flex items-center justify-between pr-2">
                <Brand collapsed={false} />
                <button type="button" onClick={() => setMobileOpen(false)} className="rounded-md p-2 hover:bg-muted" aria-label="Close menu">
                  <X className="h-5 w-5" aria-hidden />
                </button>
              </div>
              <NavList pathname={pathname} collapsed={false} onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-card/90 px-4 backdrop-blur md:px-6">
          <button type="button" onClick={() => setMobileOpen(true)} className="rounded-md p-2 hover:bg-muted md:hidden" aria-label="Open menu">
            <Menu className="h-5 w-5" aria-hidden />
          </button>
          <p className="truncate text-sm font-semibold">{current?.label ?? APP_NAME}</p>
          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="ml-auto flex h-9 w-full max-w-xs items-center gap-2 rounded-md border bg-background px-3 text-sm text-muted-foreground hover:border-foreground/30"
          >
            <Search className="h-4 w-4" aria-hidden />
            <span className="truncate">Search or jump to...</span>
            <kbd className="ml-auto hidden rounded border px-1.5 text-[10px] font-medium sm:inline">Ctrl K</kbd>
          </button>
          <Account />
        </header>
        <main className="min-w-0 flex-1 p-4 md:p-8">{children}</main>
      </div>
      <CommandMenu open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
'''

_ACCOUNT_WITH_AUTH = r'''function Account() {
  const { user, logout } = useAuth();
  if (!user) {
    return (
      <Link href="/login" className="shrink-0 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
        Sign in
      </Link>
    );
  }
  const name = user.full_name || user.email;
  return (
    <div className="flex shrink-0 items-center gap-2">
      <span className="hidden text-right text-xs leading-tight sm:block">
        <span className="block font-medium">{name}</span>
        {user.role && <span className="block text-muted-foreground">{user.role}</span>}
      </span>
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary" aria-hidden>
        {name.slice(0, 1).toUpperCase()}
      </span>
      <button type="button" onClick={logout} className="rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted">
        Sign out
      </button>
    </div>
  );
}'''

_ACCOUNT_WITHOUT_AUTH = r'''function Account() {
  return null;
}'''

_DASHBOARD_HEAD = r'''"use client";

// Generated by OmniStackAI (PC-100): the admin dashboard. Every figure is read from the API.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format, formatDistanceToNow, isValid, parseISO, startOfDay, subDays } from "date-fns";
import { motion } from "framer-motion";
import { AlertCircle, ArrowRight, Plus } from "lucide-react";
'''

_DASHBOARD_BODY = r'''
interface Source {
  key: string;
  label: string;
  href: string;
  createHref: string | null;
  titleKey: string;
  timeKey: string | null;
  load: () => Promise<{ data: Record<string, unknown>[]; total: number }>;
}

interface Loaded {
  total: number | null;
  rows: Record<string, unknown>[];
  failed: boolean;
}

function when(value: unknown): Date | null {
  if (typeof value !== "string") return null;
  const date = parseISO(value);
  return isValid(date) ? date : null;
}

export default function AdminDashboard() {
  const [loaded, setLoaded] = useState<Record<string, Loaded>>({});

  useEffect(() => {
    let alive = true;
    SOURCES.forEach((source) => {
      source.load()
        .then((result) => { if (alive) setLoaded((prev) => ({ ...prev, [source.key]: { total: result.total || result.data.length, rows: result.data, failed: false } })); })
        .catch(() => { if (alive) setLoaded((prev) => ({ ...prev, [source.key]: { total: null, rows: [], failed: true } })); });
    });
    return () => { alive = false; };
  }, []);

  const counts = useMemo(
    () => SOURCES.filter((s) => typeof loaded[s.key]?.total === "number").map((s) => ({ name: s.label, records: loaded[s.key].total as number })),
    [loaded],
  );

  // Records added per day over the last 14 days, from the latest 100 of each kind.
  const timed = SOURCES.filter((s) => s.timeKey);
  const perDay = useMemo(() => {
    const today = startOfDay(new Date());
    const days = Array.from({ length: 14 }, (_, i) => subDays(today, 13 - i));
    return days.map((day) => {
      const point: Record<string, string | number> = { day: format(day, "d MMM") };
      for (const source of timed) {
        point[source.label] = (loaded[source.key]?.rows ?? []).filter((row) => {
          const at = when(row[source.timeKey as string]);
          return at !== null && startOfDay(at).getTime() === day.getTime();
        }).length;
      }
      return point;
    });
  }, [loaded, timed]);
  const anyRecent = perDay.some((point) => timed.some((s) => Number(point[s.label]) > 0));
  const palette = ["var(--color-primary)", "var(--color-accent)", "var(--color-success)", "var(--color-warning)", "var(--color-secondary)"];

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl" style={{ fontFamily: "var(--font-heading, var(--font-sans))" }}>
            {TITLE}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">Everything in the app, read live from its API.</p>
        </div>
      </header>

      {SOURCES.length === 0 ? (
        <p className="rounded-xl border border-dashed bg-card p-10 text-center text-sm text-muted-foreground">
          This app has no records the admin console can list yet.
        </p>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Record counts">
            {SOURCES.map((source, index) => {
              const state = loaded[source.key];
              return (
                <motion.div key={source.key} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04 }}>
                  <Link href={source.href} className="group block rounded-xl border bg-card p-5 shadow-sm transition-shadow hover:shadow-md">
                    <p className="text-sm font-medium text-muted-foreground">{source.label}</p>
                    <p className="mt-2 text-3xl font-bold tabular-nums">
                      {!state ? <span className="inline-block h-8 w-16 animate-pulse rounded bg-muted" /> : state.failed ? "—" : state.total}
                    </p>
                    <p className="mt-3 flex items-center gap-1 text-xs font-medium text-primary">
                      {state?.failed ? <><AlertCircle className="h-3.5 w-3.5" aria-hidden /> Could not load</> : <>Manage <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden /></>}
                    </p>
                  </Link>
                </motion.div>
              );
            })}
          </section>

          <section className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border bg-card p-5 shadow-sm">
              <h2 className="font-semibold">Records by kind</h2>
              <p className="text-xs text-muted-foreground">How many of each the API holds.</p>
              <div className="mt-4 h-64">
                {counts.length === 0 ? (
                  <div className="h-full animate-pulse rounded-lg bg-muted" />
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={counts} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                      <Tooltip cursor={{ fill: "var(--color-surface-hover)" }} />
                      <Bar dataKey="records" fill="var(--color-primary)" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
            <div className="rounded-xl border bg-card p-5 shadow-sm">
              <h2 className="font-semibold">Added in the last 14 days</h2>
              <p className="text-xs text-muted-foreground">From the latest 100 records of each kind.</p>
              <div className="mt-4 h-64">
                {timed.length === 0 || !anyRecent ? (
                  <div className="flex h-full items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
                    {timed.length === 0 ? "These records carry no creation date." : "Nothing added in the last 14 days."}
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={perDay} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                      <XAxis dataKey="day" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} interval={2} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                      <Tooltip />
                      {timed.map((source, i) => (
                        <Area key={source.key} type="monotone" dataKey={source.label} stackId="1"
                          stroke={palette[i % palette.length]} fill={palette[i % palette.length]} fillOpacity={0.18} />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </section>

          <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-3" aria-label="Latest records">
            {SOURCES.map((source) => {
              const state = loaded[source.key];
              const rows = (state?.rows ?? []).slice(0, 5);
              return (
                <div key={source.key} className="rounded-xl border bg-card shadow-sm">
                  <div className="flex items-center justify-between border-b px-5 py-3">
                    <h2 className="text-sm font-semibold">{source.timeKey ? `Latest ${source.label.toLowerCase()}` : source.label}</h2>
                    {source.createHref && (
                      <Link href={source.createHref} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-primary hover:bg-muted">
                        <Plus className="h-3.5 w-3.5" aria-hidden /> Add
                      </Link>
                    )}
                  </div>
                  <ul className="divide-y">
                    {!state && [0, 1, 2].map((i) => <li key={i} className="px-5 py-3"><div className="h-4 w-2/3 animate-pulse rounded bg-muted" /></li>)}
                    {state && rows.length === 0 && (
                      <li className="px-5 py-6 text-center text-sm text-muted-foreground">{state.failed ? "Could not load." : "Nothing here yet."}</li>
                    )}
                    {rows.map((row) => {
                      const at = source.timeKey ? when(row[source.timeKey]) : null;
                      const title = row[source.titleKey];
                      return (
                        <li key={String(row.id)} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                          <span className="truncate">{title === null || title === undefined || title === "" ? String(row.id).slice(0, 8) : String(title)}</span>
                          {at && <span className="shrink-0 text-xs text-muted-foreground">{formatDistanceToNow(at, { addSuffix: true })}</span>}
                        </li>
                      );
                    })}
                  </ul>
                  <Link href={source.href} className="block border-t px-5 py-2.5 text-xs font-medium text-primary hover:bg-muted">
                    Open {source.label.toLowerCase()}
                  </Link>
                </div>
              );
            })}
          </section>
        </>
      )}
    </div>
  );
}
'''

RECORD_MAP = r'''"use client";

// Generated by OmniStackAI (PC-100): records with coordinates on a map. Free OpenFreeMap tiles by
// default; set NEXT_PUBLIC_MAP_STYLE_URL to use your own style.
import { useEffect, useRef } from "react";
import "maplibre-gl/dist/maplibre-gl.css";

export interface MapPoint { id: string; lat: number; lng: number; label: string }

const STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL || "https://tiles.openfreemap.org/styles/liberty";

export function RecordMap({ points }: { points: MapPoint[] }) {
  const container = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let disposed = false;
    let cleanup = () => {};
    (async () => {
      const maplibregl = await import("maplibre-gl");
      if (disposed || !container.current) return;
      const map = new maplibregl.Map({ container: container.current, style: STYLE_URL, center: [0, 20], zoom: 1 });
      map.addControl(new maplibregl.NavigationControl(), "top-right");
      const bounds = new maplibregl.LngLatBounds();
      for (const point of points) {
        new maplibregl.Marker({ color: "#e11d48" })
          .setLngLat([point.lng, point.lat])
          .setPopup(new maplibregl.Popup({ offset: 16 }).setText(point.label))
          .addTo(map);
        bounds.extend([point.lng, point.lat]);
      }
      if (points.length > 0) map.fitBounds(bounds, { padding: 48, maxZoom: 13, duration: 0 });
      cleanup = () => map.remove();
    })();
    return () => { disposed = true; cleanup(); };
  }, [points]);

  return <div ref={container} className="h-[480px] w-full overflow-hidden rounded-xl border" />;
}
'''

ENTITY_MANAGER = r'''"use client";

// Generated by OmniStackAI (PC-100): one management page per entity, driven by the plan. Only the
// operations the API really has are offered; every value on screen comes from the API.
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  flexRender, getCoreRowModel, useReactTable,
  type ColumnDef, type RowSelectionState, type SortingState,
} from "@tanstack/react-table";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { format, isValid, parseISO } from "date-fns";
import { toast } from "sonner";
import { Drawer } from "vaul";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Download, Loader2, Map as MapIcon, Pencil, Plus,
  RefreshCw, Search, Table2, Trash2, X,
} from "lucide-react";
import { ApiError, extractFieldErrors } from "@/lib/api";
import { RecordMap, type MapPoint } from "./record-map";

export type FieldKind = "string" | "text" | "int" | "float" | "bool" | "datetime" | "uuid" | "json" | "attachment";
export type Row = { id: string } & Record<string, unknown>;

export interface FieldSpec {
  name: string;
  label: string;
  kind: FieldKind;
  required: boolean;
  editable: boolean;
  inTable: boolean;
  enumValues?: string[];
  maxLength?: number;
  min?: number;
  max?: number;
  relation?: { load: () => Promise<Row[]>; labelKey: string };
}

// A type alias (not an interface), so it passes where the API client takes a params record.
export type ListParams = { limit: number; offset: number; sort?: string; order?: "asc" | "desc"; q?: string };

export interface EntityManagerProps {
  title: string;
  singular: string;
  slug: string;
  fields: FieldSpec[];
  list: (params: ListParams) => Promise<{ data: Row[]; total: number }>;
  create?: (data: Record<string, unknown>) => Promise<unknown>;
  update?: (id: string, data: Record<string, unknown>) => Promise<unknown>;
  remove?: (id: string) => Promise<unknown>;
  coordinates?: { lat: string; lng: string };
}

type FormValues = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Options = Record<string, Record<string, string>>;

const PAGE_SIZE = 20;
const IMAGE = /\.(png|jpe?g|gif|webp|avif|svg)(\?|$)/i;
const blank = (value: unknown) => (value === "" || value === null ? undefined : value);

function fieldSchema(field: FieldSpec): z.ZodTypeAny {
  if (field.kind === "bool") return z.boolean().optional();
  if (field.kind === "int" || field.kind === "float") {
    let number = z.coerce.number({ invalid_type_error: `${field.label} must be a number` });
    if (field.kind === "int") number = number.int(`${field.label} must be a whole number`);
    if (field.min !== undefined) number = number.min(field.min, `At least ${field.min}`);
    if (field.max !== undefined) number = number.max(field.max, `At most ${field.max}`);
    return z.preprocess(blank, field.required ? number : number.optional());
  }
  if (field.kind === "json") {
    return z.string().optional().refine((value) => {
      if (!value || !value.trim()) return !field.required;
      try { JSON.parse(value); return true; } catch { return false; }
    }, "Enter valid JSON");
  }
  if (field.kind === "attachment") {
    const url = z.string().url("Enter a full link (https://...)");
    return z.preprocess(blank, field.required ? url : url.optional());
  }
  if (field.enumValues && field.enumValues.length > 0) {
    const choice = z.enum(field.enumValues as [string, ...string[]], { errorMap: () => ({ message: "Choose one" }) });
    return z.preprocess(blank, field.required ? choice : choice.optional());
  }
  let text = z.string();
  if (field.maxLength) text = text.max(field.maxLength, `At most ${field.maxLength} characters`);
  if (field.required) return text.trim().min(1, `${field.label} is required`);
  return z.preprocess(blank, text.optional());
}

function toInput(field: FieldSpec, value: unknown): unknown {
  if (value === null || value === undefined) return field.kind === "bool" ? false : "";
  if (field.kind === "datetime" && typeof value === "string") {
    const date = parseISO(value);
    return isValid(date) ? format(date, "yyyy-MM-dd'T'HH:mm") : "";
  }
  if (field.kind === "json") return JSON.stringify(value, null, 2);
  return value;
}

function toPayload(fields: FieldSpec[], values: FormValues): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const field of fields) {
    if (!field.editable) continue;
    const value = values[field.name];
    if (field.kind === "bool") { payload[field.name] = Boolean(value); continue; }
    if (value === undefined || value === "" || (typeof value === "number" && Number.isNaN(value))) continue;
    if (field.kind === "datetime") payload[field.name] = new Date(String(value)).toISOString();
    else if (field.kind === "json") payload[field.name] = JSON.parse(String(value));
    else payload[field.name] = value;
  }
  return payload;
}

function problem(error: unknown): string {
  if (error instanceof ApiError) {
    const data = error.data as { error?: unknown; message?: unknown; detail?: unknown } | string | undefined;
    if (typeof data === "string" && data) return data.slice(0, 200);
    if (data && typeof data === "object") {
      const text = data.error ?? data.message ?? (typeof data.detail === "string" ? data.detail : undefined);
      if (typeof text === "string") return text;
    }
    if (error.status === 401 || error.status === 403) return "You are not allowed to do that. Sign in with an admin account.";
    return `The API answered ${error.status}.`;
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}

function Cell({ field, value, options }: { field: FieldSpec; value: unknown; options: Options }): ReactNode {
  if (value === null || value === undefined || value === "") return <span className="text-muted-foreground">—</span>;
  if (field.relation) return <span>{options[field.name]?.[String(value)] ?? String(value).slice(0, 8)}</span>;
  switch (field.kind) {
    case "bool":
      return (
        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${value ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"}`}>
          {value ? "Yes" : "No"}
        </span>
      );
    case "datetime": {
      const date = typeof value === "string" ? parseISO(value) : null;
      return date && isValid(date) ? <span className="whitespace-nowrap">{format(date, "d MMM yyyy, HH:mm")}</span> : <span>{String(value)}</span>;
    }
    case "int":
    case "float":
      return <span className="tabular-nums">{Number(value).toLocaleString()}</span>;
    case "attachment":
      return IMAGE.test(String(value)) ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={String(value)} alt="" className="h-9 w-9 rounded-md border object-cover" />
      ) : (
        <a href={String(value)} target="_blank" rel="noreferrer" className="text-primary underline">Open</a>
      );
    case "json":
      return <code className="text-xs">{JSON.stringify(value).slice(0, 60)}</code>;
    default: {
      const text = String(value);
      return <span title={text.length > 80 ? text : undefined}>{text.length > 80 ? `${text.slice(0, 80)}...` : text}</span>;
    }
  }
}

function FieldInput({ field, form, options }: { field: FieldSpec; form: ReturnType<typeof useForm<FormValues>>; options: Options }) {
  const base = "w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20";
  const register = form.register(field.name);
  if (field.relation) {
    const choices = Object.entries(options[field.name] ?? {});
    return (
      <select {...register} className={base}>
        <option value="">Choose...</option>
        {choices.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
      </select>
    );
  }
  if (field.enumValues && field.enumValues.length > 0) {
    return (
      <select {...register} className={base}>
        <option value="">Choose...</option>
        {field.enumValues.map((value) => <option key={value} value={value}>{value}</option>)}
      </select>
    );
  }
  switch (field.kind) {
    case "bool":
      return (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register} className="h-4 w-4 accent-[var(--color-primary)]" /> {field.label}
        </label>
      );
    case "text":
    case "json":
      return <textarea {...register} rows={field.kind === "json" ? 6 : 4} className={`${base} ${field.kind === "json" ? "font-mono" : ""}`} />;
    case "int":
    case "float":
      return <input type="number" step={field.kind === "int" ? 1 : "any"} {...register} className={base} />;
    case "datetime":
      return <input type="datetime-local" {...register} className={base} />;
    case "attachment":
      return <input type="url" placeholder="https://..." {...register} className={base} />;
    default:
      return <input type="text" maxLength={field.maxLength} {...register} className={base} />;
  }
}

function RecordForm({ fields, row, options, onSubmit, onCancel, singular }: {
  fields: FieldSpec[]; row: Row | null; options: Options; singular: string;
  onSubmit: (values: Record<string, unknown>, setErrors: (errors: Record<string, string>) => void) => Promise<void>;
  onCancel: () => void;
}) {
  const editable = fields.filter((field) => field.editable);
  const schema = useMemo(() => z.object(Object.fromEntries(editable.map((f) => [f.name, fieldSchema(f)]))), [editable]);
  const defaults = useMemo(
    () => Object.fromEntries(editable.map((f) => [f.name, toInput(f, row ? row[f.name] : undefined)])),
    [editable, row],
  );
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: defaults });
  const { errors, isSubmitting } = form.formState;
  const submit = form.handleSubmit(async (values) => {
    await onSubmit(toPayload(fields, values), (fieldErrors) => {
      for (const [name, message] of Object.entries(fieldErrors)) form.setError(name, { message });
    });
  });
  return (
    <form onSubmit={submit} className="flex h-full flex-col" noValidate>
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
        {editable.map((field) => {
          const error = errors[field.name]?.message;
          return (
            <div key={field.name}>
              {field.kind !== "bool" && (
                <label htmlFor={field.name} className="mb-1.5 block text-sm font-medium">
                  {field.label} {field.required && <span className="text-destructive">*</span>}
                </label>
              )}
              <FieldInput field={field} form={form} options={options} />
              {typeof error === "string" && <p className="mt-1 text-xs text-destructive">{error}</p>}
            </div>
          );
        })}
      </div>
      <div className="flex justify-end gap-2 border-t px-6 py-4">
        <button type="button" onClick={onCancel} className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted">Cancel</button>
        <button type="submit" disabled={isSubmitting} className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-60">
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          {row ? "Save changes" : `Create ${singular}`}
        </button>
      </div>
    </form>
  );
}

export function EntityManager({ title, singular, slug, fields, list, create, update, remove, coordinates }: EntityManagerProps) {
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [failure, setFailure] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [selection, setSelection] = useState<RowSelectionState>({});
  const [options, setOptions] = useState<Options>({});
  const [editing, setEditing] = useState<Row | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [confirming, setConfirming] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState<"table" | "map">("table");

  useEffect(() => { const t = setTimeout(() => { setQuery(search.trim()); setPage(0); }, 300); return () => clearTimeout(t); }, [search]);

  const params = useMemo<ListParams>(() => ({
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    sort: sorting[0]?.id,
    order: sorting[0] ? (sorting[0].desc ? "desc" : "asc") : undefined,
    q: query || undefined,
  }), [page, sorting, query]);

  const load = useCallback(async () => {
    setLoading(true);
    setFailure(null);
    try {
      const result = await list(params);
      setRows(result.data ?? []);
      setTotal(result.total || (result.data ?? []).length);
    } catch (error) {
      setFailure(problem(error));
    } finally {
      setLoading(false);
    }
  }, [list, params]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setSelection({}); }, [params]);

  useEffect(() => {
    for (const field of fields) {
      if (!field.relation) continue;
      const { load: loadOptions, labelKey } = field.relation;
      loadOptions()
        .then((records) => setOptions((prev) => ({
          ...prev,
          [field.name]: Object.fromEntries(records.map((r) => [String(r.id), String(r[labelKey] ?? r.id)])),
        })))
        .catch(() => undefined);
    }
  }, [fields]);

  useEffect(() => {
    if (create && typeof window !== "undefined" && new URLSearchParams(window.location.search).get("new") === "1") {
      setEditing(null);
      setDrawerOpen(true);
    }
  }, [create]);

  const columns = useMemo<ColumnDef<Row>[]>(() => {
    const cols: ColumnDef<Row>[] = [];
    if (remove) {
      cols.push({
        id: "select",
        enableSorting: false,
        header: ({ table }) => (
          <input type="checkbox" aria-label="Select all on this page" className="h-4 w-4 accent-[var(--color-primary)]"
            checked={table.getIsAllPageRowsSelected()} onChange={table.getToggleAllPageRowsSelectedHandler()} />
        ),
        cell: ({ row }) => (
          <input type="checkbox" aria-label="Select row" className="h-4 w-4 accent-[var(--color-primary)]"
            checked={row.getIsSelected()} onChange={row.getToggleSelectedHandler()} />
        ),
      });
    }
    for (const field of fields.filter((f) => f.inTable)) {
      cols.push({
        id: field.name,
        accessorFn: (row) => row[field.name],
        header: field.label,
        cell: ({ getValue }) => <Cell field={field} value={getValue()} options={options} />,
      });
    }
    if (update || remove) {
      cols.push({
        id: "actions",
        enableSorting: false,
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => (
          <div className="flex justify-end gap-1">
            {update && (
              <button type="button" onClick={() => { setEditing(row.original); setDrawerOpen(true); }}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={`Edit ${singular}`}>
                <Pencil className="h-4 w-4" aria-hidden />
              </button>
            )}
            {remove && (
              <button type="button" onClick={() => setConfirming([row.original.id])}
                className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive" aria-label={`Delete ${singular}`}>
                <Trash2 className="h-4 w-4" aria-hidden />
              </button>
            )}
          </div>
        ),
      });
    }
    return cols;
  }, [fields, options, remove, update, singular]);

  const table = useReactTable({
    data: rows,
    columns,
    getRowId: (row) => String(row.id),
    state: { sorting, rowSelection: selection },
    onSortingChange: (next) => { setSorting(next); setPage(0); },
    onRowSelectionChange: setSelection,
    enableRowSelection: Boolean(remove),
    manualSorting: true,
    manualPagination: true,
    sortDescFirst: false,
    getCoreRowModel: getCoreRowModel(),
  });

  const selectedIds = Object.keys(selection).filter((id) => selection[id]);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const to = Math.min(total, page * PAGE_SIZE + rows.length);

  async function save(values: Record<string, unknown>, setErrors: (errors: Record<string, string>) => void) {
    try {
      if (editing && update) await update(editing.id, values);
      else if (create) await create(values);
      toast.success(editing ? `Saved the ${singular}` : `Created the ${singular}`);
      setDrawerOpen(false);
      setEditing(null);
      await load();
    } catch (error) {
      const fieldErrors = extractFieldErrors(error);
      if (Object.keys(fieldErrors).length > 0) setErrors(fieldErrors);
      toast.error(problem(error));
    }
  }

  async function confirmDelete() {
    if (!remove || !confirming) return;
    setBusy(true);
    const results = await Promise.allSettled(confirming.map((id) => remove(id)));
    const failed = results.filter((r) => r.status === "rejected") as PromiseRejectedResult[];
    const done = results.length - failed.length;
    if (done > 0) toast.success(done === 1 ? `Deleted 1 ${singular}` : `Deleted ${done} records`);
    if (failed.length > 0) toast.error(`${failed.length} could not be deleted: ${problem(failed[0].reason)}`);
    setBusy(false);
    setConfirming(null);
    setSelection({});
    await load();
  }

  async function exportCsv() {
    setBusy(true);
    try {
      const all: Row[] = [];
      for (let offset = 0; offset < 5000; offset += 100) {
        const result = await list({ ...params, limit: 100, offset });
        all.push(...(result.data ?? []));
        if ((result.data ?? []).length < 100 || all.length >= (result.total || 0)) break;
      }
      const columnsOut = ["id", ...fields.filter((f) => f.name !== "id").map((f) => f.name)];
      const escape = (value: unknown) => {
        const text = value === null || value === undefined ? "" : typeof value === "object" ? JSON.stringify(value) : String(value);
        return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
      };
      const csv = [columnsOut.join(","), ...all.map((row) => columnsOut.map((c) => escape(row[c])).join(","))].join("\n");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      link.download = `${slug}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
      toast.success(`Exported ${all.length} ${all.length === 1 ? "record" : "records"}`);
    } catch (error) {
      toast.error(problem(error));
    } finally {
      setBusy(false);
    }
  }

  const points: MapPoint[] = useMemo(() => {
    if (!coordinates) return [];
    const labelField = fields.find((f) => f.inTable && (f.kind === "string" || f.kind === "text"));
    return rows.flatMap((row) => {
      const lat = Number(row[coordinates.lat]);
      const lng = Number(row[coordinates.lng]);
      if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return [];
      return [{ id: row.id, lat, lng, label: String((labelField && row[labelField.name]) ?? row.id) }];
    });
  }, [coordinates, fields, rows]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: "var(--font-heading, var(--font-sans))" }}>{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {loading && rows.length === 0 ? "Loading..." : `${total.toLocaleString()} ${total === 1 ? "record" : "records"}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {coordinates && (
            <div className="flex rounded-md border bg-card p-0.5" role="group" aria-label="View">
              <button type="button" onClick={() => setView("table")} aria-pressed={view === "table"}
                className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm ${view === "table" ? "bg-muted font-medium" : "text-muted-foreground"}`}>
                <Table2 className="h-4 w-4" aria-hidden /> Table
              </button>
              <button type="button" onClick={() => setView("map")} aria-pressed={view === "map"}
                className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm ${view === "map" ? "bg-muted font-medium" : "text-muted-foreground"}`}>
                <MapIcon className="h-4 w-4" aria-hidden /> Map
              </button>
            </div>
          )}
          <button type="button" onClick={() => void exportCsv()} disabled={busy || total === 0}
            className="inline-flex items-center gap-2 rounded-md border bg-card px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50">
            <Download className="h-4 w-4" aria-hidden /> Export CSV
          </button>
          {create && (
            <button type="button" onClick={() => { setEditing(null); setDrawerOpen(true); }}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shadow-sm hover:opacity-90">
              <Plus className="h-4 w-4" aria-hidden /> New {singular}
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={`Search ${title.toLowerCase()}...`}
            aria-label={`Search ${title.toLowerCase()}`}
            className="w-full rounded-md border bg-card py-2 pl-9 pr-8 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" />
          {search && (
            <button type="button" onClick={() => setSearch("")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-muted" aria-label="Clear search">
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
        </div>
        <button type="button" onClick={() => void load()} className="rounded-md p-2 text-muted-foreground hover:bg-muted" aria-label="Refresh">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} aria-hidden />
        </button>
        <AnimatePresence>
          {selectedIds.length > 0 && remove && (
            <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
              className="flex items-center gap-2 rounded-md border bg-card px-3 py-1.5 text-sm">
              <span className="font-medium">{selectedIds.length} selected</span>
              <button type="button" onClick={() => setConfirming(selectedIds)}
                className="inline-flex items-center gap-1 rounded px-2 py-1 font-medium text-destructive hover:bg-destructive/10">
                <Trash2 className="h-4 w-4" aria-hidden /> Delete
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {confirming && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm" role="alert">
            <span>
              Delete {confirming.length === 1 ? `this ${singular}` : `${confirming.length} records`}? This cannot be undone.
            </span>
            <span className="flex gap-2">
              <button type="button" onClick={() => setConfirming(null)} className="rounded-md border bg-card px-3 py-1.5 font-medium hover:bg-muted">Cancel</button>
              <button type="button" onClick={() => void confirmDelete()} disabled={busy}
                className="inline-flex items-center gap-2 rounded-md bg-destructive px-3 py-1.5 font-medium text-destructive-foreground disabled:opacity-60">
                {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} Delete
              </button>
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {failure ? (
        <div className="rounded-xl border bg-card p-8 text-center">
          <p className="font-medium">Could not load {title.toLowerCase()}</p>
          <p className="mt-1 text-sm text-muted-foreground">{failure}</p>
          <button type="button" onClick={() => void load()} className="mt-4 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted">Try again</button>
        </div>
      ) : view === "map" && coordinates ? (
        points.length > 0 ? <RecordMap points={points} /> : (
          <p className="rounded-xl border border-dashed bg-card p-10 text-center text-sm text-muted-foreground">No records on this page have coordinates.</p>
        )
      ) : (
        <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
          {/* relative: an sr-only label is absolutely positioned and would otherwise widen the page. */}
          <div className="relative overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-muted/60">
                {table.getHeaderGroups().map((group) => (
                  <tr key={group.id}>
                    {group.headers.map((header) => {
                      const sortable = header.column.getCanSort();
                      const sorted = header.column.getIsSorted();
                      return (
                        <th key={header.id} className="whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                          {sortable ? (
                            <button type="button" onClick={header.column.getToggleSortingHandler()} className="inline-flex items-center gap-1 hover:text-foreground">
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              {sorted === "asc" ? <ArrowUp className="h-3.5 w-3.5" aria-hidden /> : sorted === "desc" ? <ArrowDown className="h-3.5 w-3.5" aria-hidden /> : <ArrowUpDown className="h-3.5 w-3.5 opacity-40" aria-hidden />}
                            </button>
                          ) : flexRender(header.column.columnDef.header, header.getContext())}
                        </th>
                      );
                    })}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y">
                {loading && rows.length === 0 && Array.from({ length: 5 }, (_, i) => (
                  <tr key={`s${i}`}>{columns.map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 animate-pulse rounded bg-muted" /></td>)}</tr>
                ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td colSpan={columns.length} className="px-4 py-14 text-center">
                      <p className="font-medium">{query ? "Nothing matches your search" : `No ${title.toLowerCase()} yet`}</p>
                      {!query && create && (
                        <button type="button" onClick={() => { setEditing(null); setDrawerOpen(true); }}
                          className="mt-3 inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground">
                          <Plus className="h-4 w-4" aria-hidden /> Add the first {singular}
                        </button>
                      )}
                    </td>
                  </tr>
                )}
                {table.getRowModel().rows.map((row) => (
                  <tr key={row.id} className={`transition-colors hover:bg-muted/50 ${row.getIsSelected() ? "bg-primary/5" : ""}`}>
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 align-middle">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 text-sm text-muted-foreground">
            <span>{total === 0 ? "No records" : `Showing ${from}-${to} of ${total.toLocaleString()}`}</span>
            <span className="flex items-center gap-1">
              <button type="button" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
                className="rounded-md border p-1.5 hover:bg-muted disabled:opacity-40" aria-label="Previous page">
                <ChevronLeft className="h-4 w-4" aria-hidden />
              </button>
              <span className="px-2 tabular-nums">Page {page + 1} of {pages}</span>
              <button type="button" onClick={() => setPage((p) => Math.min(pages - 1, p + 1))} disabled={page + 1 >= pages}
                className="rounded-md border p-1.5 hover:bg-muted disabled:opacity-40" aria-label="Next page">
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
            </span>
          </div>
        </div>
      )}

      <Drawer.Root open={drawerOpen} onOpenChange={(open) => { setDrawerOpen(open); if (!open) setEditing(null); }} direction="right">
        <Drawer.Portal>
          <Drawer.Overlay className="fixed inset-0 z-40 bg-black/40" />
          <Drawer.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-card shadow-2xl outline-none">
            <div className="flex items-start justify-between border-b px-6 py-4">
              <div>
                <Drawer.Title className="text-lg font-semibold">{editing ? `Edit ${singular}` : `New ${singular}`}</Drawer.Title>
                <Drawer.Description className="text-sm text-muted-foreground">
                  {editing ? "Change the fields and save." : `Fill in the fields to add a ${singular}.`}
                </Drawer.Description>
              </div>
              <button type="button" onClick={() => setDrawerOpen(false)} className="rounded-md p-1.5 hover:bg-muted" aria-label="Close">
                <X className="h-5 w-5" aria-hidden />
              </button>
            </div>
            {drawerOpen && (
              <RecordForm key={editing?.id ?? "new"} fields={fields} row={editing} options={options} singular={singular}
                onSubmit={save} onCancel={() => setDrawerOpen(false)} />
            )}
          </Drawer.Content>
        </Drawer.Portal>
      </Drawer.Root>
    </div>
  );
}
'''
