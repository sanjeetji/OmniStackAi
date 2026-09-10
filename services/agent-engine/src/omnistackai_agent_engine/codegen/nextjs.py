"""Next.js (App Router, TypeScript) framework adapter.

Turns an Application IR into a real Next.js project as a `GeneratedProject`: config, TypeScript
interfaces from entities, App Router API route handlers from the IR APIs, a page per screen, and an
overview page. Pure and deterministic — nothing is installed, built, run, or written to disk here.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from ..application_ir import ApiEndpoint, ApplicationIR, Entity, Field, FieldType, HttpMethod, RelationKind, Screen
from .adapter import GenerationTarget
from .errors import GenerationError
from .field_validation import parse_field_rules
from .files import GeneratedFile, GeneratedProject
from .route_wiring import Op, fk_relations, wire_endpoint

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


def _slug_to_pascal(path: str) -> str:
    parts = re.split(r"[{}\-_/]+", path)
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Root"


def _api_client_file(ir: ApplicationIR) -> str:
    """Generate a strongly-typed TypeScript API client (lib/api.ts) from the Application IR."""
    lines = [
        "// Generated from the Application IR by OmniStackAI. Do not edit by hand.",
        "",
    ]
    if ir.entities:
        entity_names = sorted(e.name for e in ir.entities)
        lines.append(f'import type {{ {", ".join(entity_names)} }} from "./types";')
        lines.append("")

    lines.extend([
        'const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";',
        "",
        'export interface ApiOptions extends Omit<RequestInit, "body"> {',
        "  token?: string;",
        "  params?: Record<string, string | number | boolean | undefined>;",
        "}",
        "",
        "export interface PaginatedResult<T> {",
        "  data: T;",
        "  total: number;",
        "}",
        "",
        "export class ApiError extends Error {",
        "  constructor(public status: number, public data: unknown) {",
        "    super(`API Error ${status}`);",
        '    this.name = "ApiError";',
        "  }",
        "}",
        "",
        "export function extractFieldErrors(error: unknown): Record<string, string> {",
        "  const result: Record<string, string> = {};",
        '  if (!error || typeof error !== "object") return result;',
        "",
        '  const data = "data" in error ? (error as { data: unknown }).data : error;',
        '  if (!data || typeof data !== "object") return result;',
        "",
        "  // Go backend format: { errors: [{ field: \"title\", message: \"...\" }] }",
        '  if ("errors" in data && Array.isArray((data as { errors: unknown[] }).errors)) {',
        '    for (const item of (data as { errors: unknown[] }).errors) {',
        '      if (item && typeof item === "object" && "field" in item && "message" in item) {',
        '        const field = String((item as { field: unknown }).field);',
        '        const msg = String((item as { message: unknown }).message);',
        "        if (field && msg) result[field] = msg;",
        "      }",
        "    }",
        "    return result;",
        "  }",
        "",
        "  // FastAPI / Pydantic format: { detail: [{ loc: [\"body\", \"title\"], msg: \"...\" }] }",
        '  if ("detail" in data && Array.isArray((data as { detail: unknown[] }).detail)) {',
        '    for (const item of (data as { detail: unknown[] }).detail) {',
        '      if (item && typeof item === "object") {',
        '        const loc = (item as { loc?: unknown[] }).loc;',
        '        const msg = (item as { msg?: unknown }).msg;',
        '        if (Array.isArray(loc) && loc.length > 0 && typeof msg === "string") {',
        "          const field = String(loc[loc.length - 1]);",
        "          if (field) result[field] = msg;",
        "        }",
        "      }",
        "    }",
        "    return result;",
        "  }",
        "",
        "  return result;",
        "}",
        "",
        "async function requestWithMeta<T>(path: string, options: ApiOptions = {}, body?: unknown): Promise<PaginatedResult<T>> {",
        "  const { token, params, headers: customHeaders, ...init } = options;",
        "  let url = `${BASE_URL}${path}`;",
        "  if (params) {",
        "    const searchParams = new URLSearchParams();",
        "    for (const [key, val] of Object.entries(params)) {",
        "      if (val !== undefined) {",
        "        searchParams.set(key, String(val));",
        "      }",
        "    }",
        "    const qs = searchParams.toString();",
        "    if (qs) {",
        '      url += (url.includes("?") ? "&" : "?") + qs;',
        "    }",
        "  }",
        "",
        "  const headers: Record<string, string> = {",
        '    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),',
        "    ...(customHeaders as Record<string, string>),",
        "  };",
        "  if (token) {",
        '    headers["Authorization"] = `Bearer ${token}`;',
        "  }",
        "",
        "  const res = await fetch(url, {",
        "    ...init,",
        "    headers,",
        "    body: body !== undefined ? JSON.stringify(body) : undefined,",
        "  });",
        "",
        "  if (!res.ok) {",
        "    let errorData: unknown;",
        "    try {",
        "      errorData = await res.json();",
        "    } catch {",
        "      errorData = await res.text();",
        "    }",
        "    throw new ApiError(res.status, errorData);",
        "  }",
        "",
        '  const totalHeader = res.headers.get("X-Total-Count");',
        "  const total = totalHeader ? parseInt(totalHeader, 10) : 0;",
        "  if (res.status === 204) {",
        "    return { data: undefined as unknown as T, total };",
        "  }",
        "  const data = (await res.json()) as T;",
        "  return { data, total };",
        "}",
        "",
        "async function request<T>(path: string, options: ApiOptions = {}, body?: unknown): Promise<T> {",
        "  const res = await requestWithMeta<T>(path, options, body);",
        "  return res.data;",
        "}",
        "",
    ])

    repo_entities = frozenset(e.name for e in ir.entities)
    fk_by_entity = fk_relations(ir)
    fn_names: list[str] = []
    seen_names: set[str] = set()

    for api in ir.apis:
        wiring = wire_endpoint(api, repo_entities, fk_by_entity)
        path_params = re.findall(r"\{(\w+)\}", api.path)
        method = api.method.value

        fn_name: str
        if wiring is not None:
            plural = wiring.entity if wiring.entity.endswith("s") else f"{wiring.entity}s"
            if wiring.op is Op.LIST:
                fn_name = f"list{plural}"
            elif wiring.op is Op.GET:
                fn_name = f"get{wiring.entity}"
            elif wiring.op is Op.CREATE:
                fn_name = f"create{wiring.entity}"
            elif wiring.op is Op.UPDATE:
                fn_name = f"update{wiring.entity}"
            elif wiring.op is Op.DELETE:
                fn_name = f"delete{wiring.entity}"
            elif wiring.op is Op.LIST_BY:
                rel = _pascal(wiring.relation or "parent")
                fn_name = f"list{plural}By{rel}"
            else:
                fn_name = f"{method.lower()}{_slug_to_pascal(api.path)}"
        else:
            # Fallback: if DELETE /<entity_plural>/{id} or /<entity>/{id} without response_schema
            matched_del_ent: Entity | None = None
            if api.method == HttpMethod.DELETE and len(path_params) == 1:
                segments = [seg for seg in api.path.strip("/").split("/") if seg]
                if len(segments) == 2 and segments[1].startswith("{") and segments[1].endswith("}"):
                    entity_seg = segments[0].lower()
                    matched_del_ent = next(
                        (e for e in ir.entities if e.name.lower() == entity_seg or f"{e.name.lower()}s" == entity_seg),
                        None,
                    )
            if matched_del_ent is not None:
                fn_name = f"delete{matched_del_ent.name}"
            else:
                fn_name = f"{method.lower()}{_slug_to_pascal(api.path)}"

        if fn_name in seen_names:
            fn_name = f"{method.lower()}{_slug_to_pascal(api.path)}"
            counter = 2
            orig = fn_name
            while fn_name in seen_names:
                fn_name = f"{orig}_{counter}"
                counter += 1

        seen_names.add(fn_name)
        fn_names.append(fn_name)

        if path_params:
            interpolated = re.sub(r"\{(\w+)\}", r"${encodeURIComponent(\1)}", api.path)
            url_expr = f"`{interpolated}`"
        else:
            url_expr = f'"{api.path}"'

        auth_note = " (auth: required)" if api.auth else ""
        lines.append(f"// {method} {api.path}{auth_note}")

        if wiring is not None and wiring.op is Op.LIST:
            lines.append(
                f"export async function {fn_name}("
                f"options?: ApiOptions & {{ params?: {{ limit?: number; offset?: number; sort?: string; order?: \"asc\" | \"desc\"; q?: string }} }}"
                f"): Promise<{wiring.entity}[]> {{"
            )
            lines.append(f'  return request<{wiring.entity}[]>({url_expr}, {{ method: "GET", ...options }});')
            lines.append("}")
            lines.append("")
            lines.append(
                f"export async function {fn_name}WithCount("
                f"options?: ApiOptions & {{ params?: {{ limit?: number; offset?: number; sort?: string; order?: \"asc\" | \"desc\"; q?: string }} }}"
                f"): Promise<PaginatedResult<{wiring.entity}[]>> {{"
            )
            lines.append(f'  return requestWithMeta<{wiring.entity}[]>({url_expr}, {{ method: "GET", ...options }});')
            lines.append("}")
            lines.append("")
        elif wiring is not None and wiring.op is Op.LIST_BY:
            id_p = wiring.id_param or "id"
            lines.append(
                f"export async function {fn_name}("
                f"{id_p}: string, "
                f"options?: ApiOptions & {{ params?: {{ limit?: number; offset?: number; sort?: string; order?: \"asc\" | \"desc\"; q?: string }} }}"
                f"): Promise<{wiring.entity}[]> {{"
            )
            lines.append(f'  return request<{wiring.entity}[]>({url_expr}, {{ method: "GET", ...options }});')
            lines.append("}")
            lines.append("")
            lines.append(
                f"export async function {fn_name}WithCount("
                f"{id_p}: string, "
                f"options?: ApiOptions & {{ params?: {{ limit?: number; offset?: number; sort?: string; order?: \"asc\" | \"desc\"; q?: string }} }}"
                f"): Promise<PaginatedResult<{wiring.entity}[]>> {{"
            )
            lines.append(f'  return requestWithMeta<{wiring.entity}[]>({url_expr}, {{ method: "GET", ...options }});')
            lines.append("}")
            lines.append("")
        elif wiring is not None and wiring.op is Op.GET:
            id_p = wiring.id_param or "id"
            lines.append(
                f"export async function {fn_name}("
                f"{id_p}: string, options?: ApiOptions"
                f"): Promise<{wiring.entity}> {{"
            )
            lines.append(f'  return request<{wiring.entity}>({url_expr}, {{ method: "GET", ...options }});')
            lines.append("}")
            lines.append("")
        elif wiring is not None and wiring.op is Op.CREATE:
            lines.append(
                f"export async function {fn_name}("
                f"data: Partial<{wiring.entity}>, options?: ApiOptions"
                f"): Promise<{wiring.entity}> {{"
            )
            lines.append(f'  return request<{wiring.entity}>({url_expr}, {{ method: "POST", ...options }}, data);')
            lines.append("}")
            lines.append("")
        elif wiring is not None and wiring.op is Op.UPDATE:
            id_p = wiring.id_param or "id"
            lines.append(
                f"export async function {fn_name}("
                f"{id_p}: string, data: Partial<{wiring.entity}>, options?: ApiOptions"
                f"): Promise<{wiring.entity}> {{"
            )
            lines.append(f'  return request<{wiring.entity}>({url_expr}, {{ method: "{method}", ...options }}, data);')
            lines.append("}")
            lines.append("")
        elif wiring is not None and wiring.op is Op.DELETE:
            id_p = wiring.id_param or "id"
            lines.append(
                f"export async function {fn_name}("
                f"{id_p}: string, options?: ApiOptions"
                f"): Promise<void> {{"
            )
            lines.append(f'  return request<void>({url_expr}, {{ method: "DELETE", ...options }});')
            lines.append("}")
            lines.append("")
        else:
            has_body = method in ("POST", "PUT", "PATCH")
            req_type = f"Partial<{api.request_schema}>" if api.request_schema in repo_entities else "unknown"
            if api.response_schema in repo_entities:
                resp_type = api.response_schema
            elif not api.response_schema and method == "DELETE":
                resp_type = "void"
            else:
                resp_type = "unknown"

            params_decl = [f"{p}: string" for p in path_params]
            if has_body:
                params_decl.append(f"data?: {req_type}")
            params_decl.append("options?: ApiOptions")

            body_arg = ", data" if has_body else ""
            lines.append(
                f"export async function {fn_name}({', '.join(params_decl)}): Promise<{resp_type}> {{"
            )
            lines.append(
                f'  return request<{resp_type}>({url_expr}, {{ method: "{method}", ...options }}{body_arg});'
            )
            lines.append("}")
            lines.append("")

    lines.append("export const api = {")
    for name in fn_names:
        lines.append(f"  {name},")
    lines.append("};")
    lines.append("")

    return "\n".join(lines)


def _hooks_file(ir: ApplicationIR) -> str:
    """Generate strongly-typed React data-fetching & mutation hooks (lib/hooks.ts)."""
    lines = [
        '"use client";',
        "",
        "// Generated from the Application IR by OmniStackAI. Do not edit by hand.",
        "",
    ]
    if not ir.entities:
        lines.append("export {};\n")
        return "\n".join(lines)

    entity_names = sorted(e.name for e in ir.entities)
    lines.append('import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";')
    lines.append(f'import type {{ {", ".join(entity_names)} }} from "./types";')
    lines.append('import { api, type ApiOptions } from "./api";')
    lines.append("")
    lines.extend([
        "export interface UseListParams {",
        "  limit?: number;",
        "  offset?: number;",
        "  sort?: string;",
        '  order?: "asc" | "desc";',
        "  q?: string;",
        "}",
        "",
        "export interface UseCollectionListParams extends UseListParams {",
        "  filters?: Record<string, string>;",
        "}",
        "",
        "export interface UseListState<T> {",
        "  data: T[] | null;",
        "  total: number;",
        "  loading: boolean;",
        "  error: Error | null;",
        "  page: number;",
        "  pageSize: number;",
        "  totalPages: number;",
        "  params: UseListParams;",
        "  setParams: Dispatch<SetStateAction<UseListParams>>;",
        "  setPage: (page: number) => void;",
        "  setPageSize: (size: number) => void;",
        "  setSearch: (q: string) => void;",
        '  setSort: (sort: string, order?: "asc" | "desc") => void;',
        "  refetch: () => Promise<void>;",
        "}",
        "",
        'export interface UseCollectionListState<T> extends Omit<UseListState<T>, "params" | "setParams"> {',
        "  params: UseCollectionListParams;",
        "  setParams: Dispatch<SetStateAction<UseCollectionListParams>>;",
        "  setFilter: (field: string, value: string) => void;",
        "  clearFilters: () => void;",
        "}",
        "",
        "export interface UseDetailState<T> {",
        "  data: T | null;",
        "  loading: boolean;",
        "  error: Error | null;",
        "  refetch: () => Promise<void>;",
        "}",
        "",
        "export interface UseMutationState<TData, TResult = TData> {",
        "  loading: boolean;",
        "  error: Error | null;",
        "  mutate: (data: TData, options?: ApiOptions) => Promise<TResult>;",
        "  reset: () => void;",
        "}",
        "",
    ])

    repo_entities = frozenset(e.name for e in ir.entities)
    entities_by_name = {e.name: e for e in ir.entities}
    fk_by_entity = fk_relations(ir)

    ops_by_entity = _get_ops_by_entity(ir)
    subcollections: list[tuple[str, str, str]] = []
    seen_subcols: set[tuple[str, str]] = set()

    for api_endpoint in ir.apis:
        wiring = wire_endpoint(api_endpoint, repo_entities, fk_by_entity)
        if wiring is not None:
            if wiring.op is Op.LIST_BY and wiring.relation:
                key = (wiring.entity, wiring.relation)
                if key not in seen_subcols:
                    seen_subcols.add(key)
                    subcollections.append((wiring.entity, wiring.relation, wiring.id_param or "id"))

    hook_names: list[str] = []
    emitted_filter_options: set[str] = set()

    for entity in ir.entities:
        name = entity.name
        plural = name if name.endswith("s") else f"{name}s"
        ops = ops_by_entity.get(name, set())
        filterable_fields = _filterable_fields_for_entity(entity)

        # 1. useList<Entities>
        if Op.LIST in ops:
            hook_name = f"useList{plural}"
            hook_names.append(hook_name)
            params_type = "UseCollectionListParams" if filterable_fields else "UseListParams"
            state_type = "UseCollectionListState" if filterable_fields else "UseListState"
            filter_options_name = f"{name[:1].lower() + name[1:]}FilterOptions"
            if filterable_fields:
                filter_options = {field.name: options for field, _, options in filterable_fields}
                lines.extend([
                    f"const {filter_options_name}: Record<string, readonly string[]> = {json.dumps(filter_options, sort_keys=True)};",
                    "",
                ])
                emitted_filter_options.add(filter_options_name)
            lines.extend([
                f"export function {hook_name}(",
                f"  initialParams: {params_type} = {{}},",
                "  options?: ApiOptions",
                f"): {state_type}<{name}> {{",
                f"  const [params, setParams] = useState<{params_type}>({{",
                "    limit: 100,",
                "    offset: 0,",
                '    sort: "id",',
                '    order: "asc",',
                "    ...initialParams,",
                "  });",
                f"  const [data, setData] = useState<{name}[] | null>(null);",
                "  const [total, setTotal] = useState<number>(0);",
                "  const [loading, setLoading] = useState<boolean>(true);",
                "  const [error, setError] = useState<Error | null>(null);",
                "",
                "  const limit = params.limit ?? 100;",
                "  const offset = params.offset ?? 0;",
                "  const page = Math.floor(offset / limit) + 1;",
                "  const pageSize = limit;",
                "  const totalPages = Math.max(1, Math.ceil(total / limit));",
                "",
                "  const setPage = useCallback((newPage: number) => {",
                "    const clampedPage = Math.max(1, newPage);",
                "    setParams((prev) => ({",
                "      ...prev,",
                "      offset: (clampedPage - 1) * (prev.limit ?? 100),",
                "    }));",
                "  }, []);",
                "",
                "  const setPageSize = useCallback((newPageSize: number) => {",
                "    setParams((prev) => ({",
                "      ...prev,",
                "      limit: Math.max(1, newPageSize),",
                "      offset: 0,",
                "    }));",
                "  }, []);",
                "",
                "  const setSearch = useCallback((q: string) => {",
                "    setParams((prev) => ({",
                "      ...prev,",
                "      q,",
                "      offset: 0,",
                "    }));",
                "  }, []);",
                "",
                '  const setSort = useCallback((sort: string, order?: "asc" | "desc") => {',
                "    setParams((prev) => ({",
                "      ...prev,",
                "      sort,",
                '      order: order ?? (prev.sort === sort && prev.order === "asc" ? "desc" : "asc"),',
                "      offset: 0,",
                "    }));",
                "  }, []);",
                "",
                *([
                    "  const setFilter = useCallback((field: string, value: string) => {",
                    "    setParams((prev) => {",
                    "      const filters = { ...(prev.filters ?? {}) };",
                    f'      if (value && value !== "all" && {filter_options_name}[field]?.includes(value)) {{',
                    "        filters[field] = value;",
                    "      } else {",
                    "        delete filters[field];",
                    "      }",
                    "      return {",
                    "        ...prev,",
                    "        filters: Object.keys(filters).length > 0 ? filters : undefined,",
                    "        offset: 0,",
                    "      };",
                    "    });",
                    "  }, []);",
                    "",
                    "  const clearFilters = useCallback(() => {",
                    "    setParams((prev) => ({ ...prev, filters: undefined, offset: 0 }));",
                    "  }, []);",
                    "",
                ] if filterable_fields else []),
                "  // R-280: abort the previous in-flight request so out-of-order responses cannot clobber state.",
                "  const abortRef = useRef<AbortController | null>(null);",
                "  const refetch = useCallback(async () => {",
                "    abortRef.current?.abort();",
                "    const controller = new AbortController();",
                "    abortRef.current = controller;",
                "    setLoading(true);",
                "    setError(null);",
                *([
                    "    const { filters, ...baseParams } = params;",
                    "    const requestParams = { ...baseParams, ...(filters ?? {}) };",
                ] if filterable_fields else []),
                "    try {",
                f"      const res = await api.list{plural}WithCount({{ {'params: requestParams' if filterable_fields else 'params'}, signal: controller.signal, ...options }});",
                "      if (controller.signal.aborted) return;",
                "      setData(res.data);",
                "      setTotal(res.total);",
                "    } catch (err) {",
                '      if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;',
                "      setError(err instanceof Error ? err : new Error(String(err)));",
                "    } finally {",
                "      if (!controller.signal.aborted) setLoading(false);",
                "    }",
                "  }, [params, options]);",
                "",
                "  useEffect(() => {",
                "    refetch();",
                "    return () => abortRef.current?.abort();",
                "  }, [refetch]);",
                "",
                "  // R-280: hydrate list state from the URL once on mount (deep-linkable views).",
                "  useEffect(() => {",
                '    if (typeof window === "undefined") return;',
                "    const sp = new URLSearchParams(window.location.search);",
                f"    const next: {params_type} = {{}};",
                '    const qv = sp.get("q");',
                "    if (qv !== null) next.q = qv;",
                '    const sortV = sp.get("sort");',
                "    if (sortV) next.sort = sortV;",
                '    const orderV = sp.get("order");',
                '    if (orderV === "asc" || orderV === "desc") next.order = orderV;',
                '    const sizeV = Number(sp.get("pageSize"));',
                "    if (Number.isFinite(sizeV) && sizeV > 0) next.limit = sizeV;",
                '    const pageV = Number(sp.get("page"));',
                "    if (Number.isFinite(pageV) && pageV > 1) next.offset = (pageV - 1) * (next.limit ?? 100);",
                *([
                    "    const filters: Record<string, string> = {};",
                    f"    for (const [field, allowed] of Object.entries({filter_options_name})) {{",
                    "      const value = sp.get(field);",
                    "      if (value && allowed.includes(value)) filters[field] = value;",
                    "    }",
                    "    if (Object.keys(filters).length > 0) next.filters = filters;",
                ] if filterable_fields else []),
                "    if (Object.keys(next).length > 0) setParams((prev) => ({ ...prev, ...next }));",
                "    // eslint-disable-next-line react-hooks/exhaustive-deps",
                "  }, []);",
                "",
                "  // R-280: reflect list state in the URL so refresh/bookmark/share restore the view.",
                "  useEffect(() => {",
                '    if (typeof window === "undefined") return;',
                "    const url = new URL(window.location.href);",
                "    const limitV = params.limit ?? 100;",
                "    const offsetV = params.offset ?? 0;",
                "    const pageV = Math.floor(offsetV / limitV) + 1;",
                "    const setOrDelete = (k: string, v: string | null) => {",
                "      if (v) url.searchParams.set(k, v);",
                "      else url.searchParams.delete(k);",
                "    };",
                '    setOrDelete("q", params.q ? params.q : null);',
                '    setOrDelete("sort", params.sort && params.sort !== "id" ? params.sort : null);',
                '    setOrDelete("order", params.order && params.order !== "asc" ? params.order : null);',
                '    setOrDelete("page", pageV > 1 ? String(pageV) : null);',
                '    setOrDelete("pageSize", limitV !== 100 ? String(limitV) : null);',
                *([
                    f"    for (const field of Object.keys({filter_options_name})) {{",
                    "      setOrDelete(field, params.filters?.[field] ?? null);",
                    "    }",
                ] if filterable_fields else []),
                '    window.history.replaceState({}, "", url.toString());',
                "  }, [params]);",
                "",
                "  return {",
                "    data,",
                "    total,",
                "    loading,",
                "    error,",
                "    page,",
                "    pageSize,",
                "    totalPages,",
                "    params,",
                "    setParams,",
                "    setPage,",
                "    setPageSize,",
                "    setSearch,",
                "    setSort,",
                *(["    setFilter,", "    clearFilters,"] if filterable_fields else []),
                "    refetch,",
                "  };",
                "}",
                "",
            ])

        # 2. use<Entity>
        if Op.GET in ops:
            hook_name = f"use{name}"
            hook_names.append(hook_name)
            lines.extend([
                f"export function {hook_name}(",
                "  id: string | null | undefined,",
                "  options?: ApiOptions",
                f"): UseDetailState<{name}> {{",
                f"  const [data, setData] = useState<{name} | null>(null);",
                "  const [loading, setLoading] = useState<boolean>(Boolean(id));",
                "  const [error, setError] = useState<Error | null>(null);",
                "",
                "  // R-287: cancel a superseded detail request so a stale GET cannot overwrite the current record.",
                "  const abortRef = useRef<AbortController | null>(null);",
                "  const refetch = useCallback(async () => {",
                "    abortRef.current?.abort();",
                "    if (!id) {",
                "      setData(null);",
                "      setError(null);",
                "      setLoading(false);",
                "      return;",
                "    }",
                "    const controller = new AbortController();",
                "    abortRef.current = controller;",
                "    setLoading(true);",
                "    setError(null);",
                "    try {",
                f"      const item = await api.get{name}(id, {{ ...options, signal: controller.signal }});",
                "      if (controller.signal.aborted) return;",
                "      setData(item);",
                "    } catch (err) {",
                '      if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;',
                "      setError(err instanceof Error ? err : new Error(String(err)));",
                "    } finally {",
                "      if (!controller.signal.aborted) setLoading(false);",
                "    }",
                "  }, [id, options]);",
                "",
                "  useEffect(() => {",
                "    refetch();",
                "    return () => abortRef.current?.abort();",
                "  }, [refetch]);",
                "",
                "  return { data, loading, error, refetch };",
                "}",
                "",
            ])

        # 3. useCreate<Entity>
        if Op.CREATE in ops:
            hook_name = f"useCreate{name}"
            hook_names.append(hook_name)
            lines.extend([
                f"export function {hook_name}() {{",
                "  const [loading, setLoading] = useState<boolean>(false);",
                "  const [error, setError] = useState<Error | null>(null);",
                f"  const pendingRef = useRef<Promise<{name}> | null>(null);",
                "",
                "  const create = useCallback(",
                f"    async (data: Partial<{name}>, options?: ApiOptions): Promise<{name}> => {{",
                "      // R-288: dedupe concurrent submits so a double-click cannot fire a duplicate write.",
                "      if (pendingRef.current) return pendingRef.current;",
                "      setLoading(true);",
                "      setError(null);",
                "      const request = (async () => {",
                "        try {",
                f"          return await api.create{name}(data, options);",
                "        } catch (err) {",
                "          const e = err instanceof Error ? err : new Error(String(err));",
                "          setError(e);",
                "          throw e;",
                "        } finally {",
                "          setLoading(false);",
                "          pendingRef.current = null;",
                "        }",
                "      })();",
                "      pendingRef.current = request;",
                "      return request;",
                "    },",
                "    []",
                "  );",
                "",
                "  const reset = useCallback(() => {",
                "    setError(null);",
                "    setLoading(false);",
                "  }, []);",
                "",
                "  return { create, mutate: create, loading, error, reset };",
                "}",
                "",
            ])

        # 4. useUpdate<Entity>
        if Op.UPDATE in ops:
            hook_name = f"useUpdate{name}"
            hook_names.append(hook_name)
            lines.extend([
                f"export function {hook_name}() {{",
                "  const [loading, setLoading] = useState<boolean>(false);",
                "  const [error, setError] = useState<Error | null>(null);",
                f"  const pendingRef = useRef<Promise<{name}> | null>(null);",
                "",
                "  const update = useCallback(",
                f"    async (id: string, data: Partial<{name}>, options?: ApiOptions): Promise<{name}> => {{",
                "      // R-288: dedupe concurrent submits so a double-click cannot fire a duplicate write.",
                "      if (pendingRef.current) return pendingRef.current;",
                "      setLoading(true);",
                "      setError(null);",
                "      const request = (async () => {",
                "        try {",
                f"          return await api.update{name}(id, data, options);",
                "        } catch (err) {",
                "          const e = err instanceof Error ? err : new Error(String(err));",
                "          setError(e);",
                "          throw e;",
                "        } finally {",
                "          setLoading(false);",
                "          pendingRef.current = null;",
                "        }",
                "      })();",
                "      pendingRef.current = request;",
                "      return request;",
                "    },",
                "    []",
                "  );",
                "",
                "  const reset = useCallback(() => {",
                "    setError(null);",
                "    setLoading(false);",
                "  }, []);",
                "",
                "  return { update, mutate: update, loading, error, reset };",
                "}",
                "",
            ])

        # 5. useDelete<Entity>
        if Op.DELETE in ops:
            hook_name = f"useDelete{name}"
            hook_names.append(hook_name)
            lines.extend([
                f"export function {hook_name}() {{",
                "  const [loading, setLoading] = useState<boolean>(false);",
                "  const [error, setError] = useState<Error | null>(null);",
                "  const pendingRef = useRef<Promise<void> | null>(null);",
                "",
                "  const remove = useCallback(",
                "    async (id: string, options?: ApiOptions): Promise<void> => {",
                "      // R-288: dedupe concurrent submits so a double-click cannot fire a duplicate write.",
                "      if (pendingRef.current) return pendingRef.current;",
                "      setLoading(true);",
                "      setError(null);",
                "      const request = (async () => {",
                "        try {",
                f"          await api.delete{name}(id, options);",
                "        } catch (err) {",
                "          const e = err instanceof Error ? err : new Error(String(err));",
                "          setError(e);",
                "          throw e;",
                "        } finally {",
                "          setLoading(false);",
                "          pendingRef.current = null;",
                "        }",
                "      })();",
                "      pendingRef.current = request;",
                "      return request;",
                "    },",
                "    []",
                "  );",
                "",
                "  const reset = useCallback(() => {",
                "    setError(null);",
                "    setLoading(false);",
                "  }, []);",
                "",
                "  return { remove, mutate: remove, loading, error, reset };",
                "}",
                "",
            ])

    # 6. Subcollections
    for child_entity, relation, id_p in subcollections:
        plural = child_entity if child_entity.endswith("s") else f"{child_entity}s"
        rel_pascal = _pascal(relation)
        hook_name = f"useList{plural}By{rel_pascal}"
        hook_names.append(hook_name)
        child_model = entities_by_name[child_entity]
        filterable_fields = _filterable_fields_for_entity(child_model)
        params_type = "UseCollectionListParams" if filterable_fields else "UseListParams"
        state_type = "UseCollectionListState" if filterable_fields else "UseListState"
        filter_options_name = f"{child_entity[:1].lower() + child_entity[1:]}FilterOptions"
        if filterable_fields and filter_options_name not in emitted_filter_options:
            filter_options = {field.name: options for field, _, options in filterable_fields}
            lines.extend([
                f"const {filter_options_name}: Record<string, readonly string[]> = {json.dumps(filter_options, sort_keys=True)};",
                "",
            ])
            emitted_filter_options.add(filter_options_name)
        lines.extend([
            f"export function {hook_name}(",
            f"  {id_p}: string | null | undefined,",
            f"  initialParams: {params_type} = {{}},",
            "  options?: ApiOptions",
            f"): {state_type}<{child_entity}> {{",
            f"  const [params, setParams] = useState<{params_type}>({{",
            "    limit: 100,",
            "    offset: 0,",
            '    sort: "id",',
            '    order: "asc",',
            "    ...initialParams,",
            "  });",
            f"  const [data, setData] = useState<{child_entity}[] | null>(null);",
            "  const [total, setTotal] = useState<number>(0);",
            f"  const [loading, setLoading] = useState<boolean>(Boolean({id_p}));",
            "  const [error, setError] = useState<Error | null>(null);",
            "",
            "  const limit = params.limit ?? 100;",
            "  const offset = params.offset ?? 0;",
            "  const page = Math.floor(offset / limit) + 1;",
            "  const pageSize = limit;",
            "  const totalPages = Math.max(1, Math.ceil(total / limit));",
            "",
            "  const setPage = useCallback((newPage: number) => {",
            "    const clampedPage = Math.max(1, newPage);",
            "    setParams((prev) => ({",
            "      ...prev,",
            "      offset: (clampedPage - 1) * (prev.limit ?? 100),",
            "    }));",
            "  }, []);",
            "",
            "  const setPageSize = useCallback((newPageSize: number) => {",
            "    setParams((prev) => ({",
            "      ...prev,",
            "      limit: Math.max(1, newPageSize),",
            "      offset: 0,",
            "    }));",
            "  }, []);",
            "",
            "  const setSearch = useCallback((q: string) => {",
            "    setParams((prev) => ({",
            "      ...prev,",
            "      q,",
            "      offset: 0,",
            "    }));",
            "  }, []);",
            "",
            '  const setSort = useCallback((sort: string, order?: "asc" | "desc") => {',
            "    setParams((prev) => ({",
            "      ...prev,",
            "      sort,",
            '      order: order ?? (prev.sort === sort && prev.order === "asc" ? "desc" : "asc"),',
            "      offset: 0,",
            "    }));",
            "  }, []);",
            "",
            *([
                "  const setFilter = useCallback((field: string, value: string) => {",
                "    setParams((prev) => {",
                "      const filters = { ...(prev.filters ?? {}) };",
                f'      if (value && value !== "all" && {filter_options_name}[field]?.includes(value)) {{',
                "        filters[field] = value;",
                "      } else {",
                "        delete filters[field];",
                "      }",
                "      return { ...prev, filters: Object.keys(filters).length > 0 ? filters : undefined, offset: 0 };",
                "    });",
                "  }, []);",
                "",
                "  const clearFilters = useCallback(() => {",
                "    setParams((prev) => ({ ...prev, filters: undefined, offset: 0 }));",
                "  }, []);",
                "",
            ] if filterable_fields else []),
            "  // R-286: cancel superseded relation-scoped requests before they can overwrite child state.",
            "  const abortRef = useRef<AbortController | null>(null);",
            "  const refetch = useCallback(async () => {",
            "    abortRef.current?.abort();",
            f"    if (!{id_p}) {{",
            "      setData(null);",
            "      setTotal(0);",
            "      setLoading(false);",
            "      return;",
            "    }",
            "    const controller = new AbortController();",
            "    abortRef.current = controller;",
            "    setLoading(true);",
            "    setError(null);",
            *([
                "    const { filters, ...baseParams } = params;",
                "    const requestParams = { ...baseParams, ...(filters ?? {}) };",
            ] if filterable_fields else []),
            "    try {",
            f"      const res = await api.list{plural}By{rel_pascal}WithCount({id_p}, {{ {'params: requestParams' if filterable_fields else 'params'}, ...options, signal: controller.signal }});",
            "      if (controller.signal.aborted) return;",
            "      setData(res.data);",
            "      setTotal(res.total);",
            "    } catch (err) {",
            '      if (controller.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;',
            "      setError(err instanceof Error ? err : new Error(String(err)));",
            "    } finally {",
            "      if (!controller.signal.aborted) setLoading(false);",
            "    }",
            f"  }}, [{id_p}, params, options]);",
            "",
            "  useEffect(() => {",
            "    refetch();",
            "    return () => abortRef.current?.abort();",
            "  }, [refetch]);",
            "",
            "  return {",
            "    data,",
            "    total,",
            "    loading,",
            "    error,",
            "    page,",
            "    pageSize,",
            "    totalPages,",
            "    params,",
            "    setParams,",
            "    setPage,",
            "    setPageSize,",
            "    setSearch,",
            "    setSort,",
            *(["    setFilter,", "    clearFilters,"] if filterable_fields else []),
            "    refetch,",
            "  };",
            "}",
            "",
        ])

    if hook_names:
        lines.append("export const hooks = {")
        for h in hook_names:
            lines.append(f"  {h},")
        lines.append("};")
        lines.append("")

    return "\n".join(lines)


def render_hooks(ir: ApplicationIR) -> str:
    """Public generator for Next.js React hooks (lib/hooks.ts)."""
    return _hooks_file(ir)


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


def _title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[_-]+", value)) or "Page"


def _pascal(value: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[_-]+", value)) or "Screen"


def _snake(value: str) -> str:
    stepped = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    stepped = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stepped)
    return stepped.lower()


def _match_entity(screen: Screen, ir: ApplicationIR) -> Entity | None:
    if not ir.entities:
        return None

    sid = screen.id.lower()
    sid_tokens = set(re.split(r"[_\-]+", sid))
    sid_stem = sid.rstrip("s")
    cmp_tokens: set[str] = set()
    for c in screen.components:
        cmp_tokens.update(re.split(r"[_\-]+", c.lower()))

    best_entity: Entity | None = None
    best_score = -1

    for entity in ir.entities:
        ename = entity.name.lower()
        eplural = (entity.name if entity.name.endswith("s") else f"{entity.name}s").lower()
        estem = ename.rstrip("s")

        score = 0
        if sid == ename or sid == eplural:
            score += 100
        elif ename in sid or eplural in sid:
            score += 60
        elif estem in sid or sid_stem in ename or sid_stem in eplural:
            score += 50
        elif sid in ename or sid in eplural:
            score += 40

        if ename in sid_tokens or eplural in sid_tokens or estem in sid_tokens:
            score += 30

        for token in cmp_tokens:
            if token in (ename, eplural, estem):
                score += 20
            elif token in ename or ename in token:
                score += 10

        for act in screen.actions:
            act_lower = act.lower()
            if act_lower in (ename, eplural, estem):
                score += 15

        if score > best_score:
            best_score = score
            best_entity = entity

    if best_score > 0 and best_entity is not None:
        return best_entity
    return ir.entities[0]


def _screen_intent(screen: Screen) -> str:
    sid = screen.id.lower()
    cmps = [c.lower() for c in screen.components]
    acts = [a.lower() for a in screen.actions]

    is_form = (
        "form" in cmps
        or any(term in sid for term in ("editor", "create", "edit", "new", "compose"))
        or any(term in acts for term in ("save", "submit", "publish", "create"))
    )
    is_collection = (
        "list" in cmps
        or "table" in cmps
        or "grid" in cmps
        or any(term in sid for term in ("list", "catalog", "browse", "index", "all", "collection"))
    )
    is_detail = (
        "detail" in cmps
        or "view" in cmps
        or any(term in sid for term in ("detail", "view", "item"))
    )

    if any(term in sid for term in ("editor", "create", "edit", "new")):
        return "form"
    if "list" in sid:
        return "collection"
    if is_collection:
        return "collection"
    if is_form:
        return "form"
    if is_detail:
        return "detail"
    return "generic"


def _get_ops_by_entity(ir: ApplicationIR) -> dict[str, set[Op]]:
    repo_entities = {e.name: [f.name for f in e.fields] for e in ir.entities}
    fk_by_entity = fk_relations(ir)
    ops_by_entity: dict[str, set[Op]] = {}
    for api_endpoint in ir.apis:
        wiring = wire_endpoint(api_endpoint, repo_entities, fk_by_entity)
        if wiring is not None:
            ops_by_entity.setdefault(wiring.entity, set()).add(wiring.op)
        elif api_endpoint.method == HttpMethod.DELETE:
            segments = [seg for seg in api_endpoint.path.strip("/").split("/") if seg]
            if len(segments) == 2 and segments[1].startswith("{") and segments[1].endswith("}"):
                entity_seg = segments[0].lower()
                for ent_name in repo_entities:
                    if ent_name.lower() == entity_seg or f"{ent_name.lower()}s" == entity_seg:
                        ops_by_entity.setdefault(ent_name, set()).add(Op.DELETE)
                        break
    return ops_by_entity


@dataclass(frozen=True)
class SubcollectionInfo:
    child_entity: Entity
    relation: str
    id_param: str
    hook_name: str
    child_plural: str
    display_fields: tuple[Field, ...]
    can_delete: bool = False


def _subcollections_for_parent(parent_name: str, ir: ApplicationIR) -> list[SubcollectionInfo]:
    repo_entities = frozenset(e.name for e in ir.entities)
    fk_by_entity = fk_relations(ir)
    entities_by_name = {e.name: e for e in ir.entities}
    ops_by_entity = _get_ops_by_entity(ir)

    seen: set[tuple[str, str]] = set()
    result: list[SubcollectionInfo] = []

    for api_endpoint in ir.apis:
        wiring = wire_endpoint(api_endpoint, repo_entities, fk_by_entity)
        if wiring is not None and wiring.op is Op.LIST_BY and wiring.relation:
            child_name = wiring.entity
            key = (child_name, wiring.relation)
            if key in seen:
                continue
            seen.add(key)

            child_ent = entities_by_name.get(child_name)
            if child_ent is None:
                continue

            rel = next((r for r in child_ent.relations if r.name == wiring.relation), None)
            if rel is None or rel.target_entity != parent_name:
                continue

            child_plural = child_name if child_name.endswith("s") else f"{child_name}s"
            rel_pascal = _pascal(wiring.relation)
            hook_name = f"useList{child_plural}By{rel_pascal}"

            fk_field_names = {
                f"{wiring.relation}_id",
                f"{wiring.relation}Id",
                wiring.relation.lower() + "_id",
            }
            display_fields = tuple(
                f for f in child_ent.fields
                if f.name != "id" and f.name not in fk_field_names
            )
            if not display_fields:
                display_fields = tuple(f for f in child_ent.fields if f.name != "id")
            if not display_fields:
                display_fields = child_ent.fields[:1]
            display_fields = display_fields[:4]

            can_delete = Op.DELETE in ops_by_entity.get(child_name, set())

            result.append(
                SubcollectionInfo(
                    child_entity=child_ent,
                    relation=wiring.relation,
                    id_param=wiring.id_param or "id",
                    hook_name=hook_name,
                    child_plural=child_plural,
                    display_fields=display_fields,
                    can_delete=can_delete,
                )
            )
    return result


def _subcol_search_names(s_var: str) -> tuple[str, str]:
    """R-289: the controlled search state + setter names for a subcollection (derived from its hook var)."""
    return f"{s_var}Search", "set" + s_var[0].upper() + s_var[1:] + "Search"


def _subcol_delete_names(s_var: str) -> tuple[str, str]:
    """R-291: the optimistic-delete overlay state + setter names for a subcollection (from its hook var)."""
    return f"{s_var}Deleting", "set" + s_var[0].upper() + s_var[1:] + "Deleting"


def _subcol_search_state(s_var: str) -> list[str]:
    """R-289: component-level controlled search state + a fixed 300ms debounce committing to the
    subcollection hook's setSearch. Safe now that R-286 made LIST_BY refetches race-safe; mirrors the
    top-level R-280 debounce. Emitted once per subcollection, next to its hook declaration."""
    state, setter = _subcol_search_names(s_var)
    return [
        f'  const [{state}, {setter}] = useState("");',
        "  useEffect(() => {",
        "    const timer = setTimeout(() => {",
        f'      if ({state} !== ({s_var}.params.q ?? "")) {s_var}.setSearch({state}.trim());',
        "    }, 300);",
        "    return () => clearTimeout(timer);",
        "    // eslint-disable-next-line react-hooks/exhaustive-deps",
        f"  }}, [{state}, {s_var}.params.q]);",
    ]


def _subcol_controls(sub: "SubcollectionInfo", s_var: str) -> list[str]:
    """R-281/R-289: a debounced controlled search form + a sort <select> for a subcollection list, driven
    by the already-exposed useList<Child>By<Parent> setters (setSearch / setSort). The search input is
    controlled by the R-289 per-subcollection state; the form submit commits immediately (Enter)."""
    child_lower = sub.child_plural.lower()
    search_state, search_setter = _subcol_search_names(s_var)
    sort_fields = ["id"] + [f.name for f in sub.display_fields if f.name != "id"]
    filterable_fields = _filterable_fields_for_entity(sub.child_entity)
    lines = [
        f"                {{{s_var}.data && (",
        '                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>',
        "                    <form",
        f'                      onSubmit={{(e) => {{ e.preventDefault(); {s_var}.setSearch({search_state}.trim()); }}}}',
        '                      style={{ display: "flex", gap: 6, flex: 1, minWidth: 200 }}',
        "                    >",
        '                      <div style={{ position: "relative", flex: 1, display: "flex", alignItems: "center" }}>',
        "                        <input",
        '                          type="search"',
        f'                          aria-label="Search {child_lower}"',
        f'                          value={{{search_state}}}',
        f'                          onChange={{(e) => {search_setter}(e.target.value)}}',
        f'                          placeholder="Search {child_lower}..."',
        '                          style={{ width: "100%", padding: "6px 24px 6px 10px", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: 13, boxSizing: "border-box" }}',
        "                        />",
        f'                        {{Boolean({search_state}) && (',
        "                          <button",
        '                            type="button"',
        f'                            onClick={{() => {{ {search_setter}(""); {s_var}.setSearch(""); }}}}',
        f'                            aria-label="Clear {child_lower} search"',
        '                            style={{ position: "absolute", right: 6, background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: 14, lineHeight: 1, padding: 2 }}',
        "                          >",
        "                            &times;",
        "                          </button>",
        "                        )}",
        "                      </div>",
        '                      <button type="submit" style={{ padding: "6px 12px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, fontSize: 13, fontWeight: 500, cursor: "pointer" }}>Search</button>',
        "                    </form>",
        "                    <select",
        f'                      aria-label="Sort {child_lower}"',
        f'                      value={{`${{{s_var}.params.sort ?? "id"}}:${{{s_var}.params.order ?? "asc"}}`}}',
        f'                      onChange={{(e) => {{ const [sf, so] = e.target.value.split(":"); {s_var}.setSort(sf, so as "asc" | "desc"); }}}}',
        '                      style={{ padding: "6px 10px", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: 13, background: "#fff" }}',
        "                    >",
    ]
    for f_name in sort_fields:
        label = _title_case(f_name)
        lines.append(f'                      <option value="{f_name}:asc">{label} ↑</option>')
        lines.append(f'                      <option value="{f_name}:desc">{label} ↓</option>')
    lines.extend([
        "                    </select>",
        "                  </div>",
    ])
    if filterable_fields:
        lines.extend([
            '                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 12, padding: "8px 10px", background: "#f8fafc", borderRadius: 6 }}>',
            '                    <span style={{ fontSize: 12, fontWeight: 600, color: "#475569" }}>Filters:</span>',
        ])
        for field, kind, options in filterable_fields:
            label = _title_case(field.name)
            if kind == "boolean":
                lines.extend([
                    f'                    <button type="button" onClick={{() => {s_var}.setFilter("{field.name}", "all")}} style={{{{ padding: "3px 8px", border: "1px solid #cbd5e1", borderRadius: 12, fontSize: 12, cursor: "pointer", background: !{s_var}.params.filters?.{field.name} ? "#0f172a" : "#fff", color: !{s_var}.params.filters?.{field.name} ? "#fff" : "#475569" }}}}>All</button>',
                    f'                    <button type="button" onClick={{() => {s_var}.setFilter("{field.name}", "true")}} style={{{{ padding: "3px 8px", border: "1px solid #cbd5e1", borderRadius: 12, fontSize: 12, cursor: "pointer", background: {s_var}.params.filters?.{field.name} === "true" ? "#0f172a" : "#fff", color: {s_var}.params.filters?.{field.name} === "true" ? "#fff" : "#475569" }}}}>{label}: Yes</button>',
                    f'                    <button type="button" onClick={{() => {s_var}.setFilter("{field.name}", "false")}} style={{{{ padding: "3px 8px", border: "1px solid #cbd5e1", borderRadius: 12, fontSize: 12, cursor: "pointer", background: {s_var}.params.filters?.{field.name} === "false" ? "#0f172a" : "#fff", color: {s_var}.params.filters?.{field.name} === "false" ? "#fff" : "#475569" }}}}>{label}: No</button>',
                ])
            else:
                lines.extend([
                    "                    <select",
                    f'                      aria-label="Filter {child_lower} by {label}"',
                    f'                      value={{{s_var}.params.filters?.{field.name} ?? "all"}}',
                    f'                      onChange={{(e) => {s_var}.setFilter("{field.name}", e.target.value)}}',
                    '                      style={{ padding: "4px 8px", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: 12, background: "#fff" }}',
                    "                    >",
                    f'                      <option value="all">All {label}s</option>',
                    ])
                for option in options:
                    lines.append(f'                      <option value="{option}">{_title_case(option)}</option>')
                lines.append("                    </select>")
        lines.extend([
            f"                    {{Object.keys({s_var}.params.filters ?? {{}}).length > 0 && (",
            '                      <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#1d4ed8" }}>',
            f"                        {{Object.keys({s_var}.params.filters ?? {{}}).length}} active",
            f'                        <button type="button" onClick={{{s_var}.clearFilters}} style={{{{ padding: "3px 7px", border: "1px solid #93c5fd", background: "#fff", color: "#1d4ed8", borderRadius: 4, fontSize: 12, cursor: "pointer" }}}}>Reset</button>',
            "                      </span>",
            "                    )}",
            "                  </div>",
        ])
    lines.append("                )}")
    return lines


def _subcol_filtered_empty(sub: "SubcollectionInfo", s_var: str) -> list[str]:
    """R-285: recovery state when a server-filtered subcollection returns no rows."""
    if not _filterable_fields_for_entity(sub.child_entity):
        return []
    return [
        f"                {{{s_var}.data && {s_var}.data.length === 0 && Object.keys({s_var}.params.filters ?? {{}}).length > 0 && (",
        '                  <div style={{ padding: 18, textAlign: "center", color: "#64748b", fontSize: 14, background: "#f8fafc", borderRadius: 6, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>',
        f"                    <div role=\"status\">No {sub.child_plural} match the active filter criteria.</div>",
        f'                    <button type="button" onClick={{{s_var}.clearFilters}} style={{{{ padding: "5px 10px", border: "1px solid #cbd5e1", background: "#fff", color: "#2563eb", borderRadius: 4, fontSize: 12, cursor: "pointer" }}}}>Clear filters</button>',
        "                  </div>",
        "                )}",
    ]


def _subcol_pagination(s_var: str) -> list[str]:
    """R-281: a Prev / Page X of Y (N total) / Next footer for a subcollection list, driven by the
    already-exposed useList<Child>By<Parent> setPage / page / totalPages / total."""
    return [
        f"                {{{s_var}.totalPages > 1 && (",
        '                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12, gap: 8 }}>',
        "                    <button",
        f"                      onClick={{() => {s_var}.setPage({s_var}.page - 1)}}",
        f"                      disabled={{{s_var}.page <= 1 || {s_var}.loading}}",
        '                      aria-label="Previous page"',
        f'                      style={{{{ padding: "4px 10px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 4, fontSize: 12, cursor: ({s_var}.page <= 1 || {s_var}.loading) ? "default" : "pointer" }}}}',
        "                    >",
        "                      Previous",
        "                    </button>",
        f'                    <span style={{{{ fontSize: 12, color: "#64748b" }}}}>Page {{{s_var}.page}} of {{{s_var}.totalPages}} ({{{s_var}.total}} total)</span>',
        "                    <button",
        f"                      onClick={{() => {s_var}.setPage({s_var}.page + 1)}}",
        f"                      disabled={{{s_var}.page >= {s_var}.totalPages || {s_var}.loading}}",
        '                      aria-label="Next page"',
        f'                      style={{{{ padding: "4px 10px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 4, fontSize: 12, cursor: ({s_var}.page >= {s_var}.totalPages || {s_var}.loading) ? "default" : "pointer" }}}}',
        "                    >",
        "                      Next",
        "                    </button>",
        "                  </div>",
        "                )}",
    ]


@dataclass(frozen=True)
class ParentRelationInfo:
    field_name: str
    relation_name: str
    parent_entity: Entity
    parent_plural: str
    hook_name: str
    title_field: str
    label: str


def _parent_relations_for_entity(entity: Entity, ir: ApplicationIR) -> list[ParentRelationInfo]:
    entities_by_name = {e.name: e for e in ir.entities}
    ops_by_entity = _get_ops_by_entity(ir)

    existing_field_names = {f.name for f in entity.fields}
    result: list[ParentRelationInfo] = []
    seen_fields: set[str] = set()

    for rel in getattr(entity, "relations", ()):
        if rel.kind is not RelationKind.MANY_TO_ONE:
            continue
        parent = entities_by_name.get(rel.target_entity)
        if parent is None:
            continue
        parent_ops = ops_by_entity.get(parent.name, set())
        if Op.LIST not in parent_ops:
            continue

        fk_field: str | None = None
        for candidate in (
            f"{rel.name}_id",
            f"{rel.name}Id",
            rel.name,
            f"{parent.name.lower()}_id",
            f"{_snake(parent.name)}_id",
        ):
            if candidate in existing_field_names:
                fk_field = candidate
                break
        if fk_field is None:
            fk_field = f"{rel.name}_id"

        if fk_field in seen_fields:
            continue
        seen_fields.add(fk_field)

        parent_plural = parent.name if parent.name.endswith("s") else f"{parent.name}s"
        hook_name = f"useList{parent_plural}"
        best_title_f = next((f.name for f in parent.fields if f.name in ("title", "name", "label", "email")), None)
        if not best_title_f:
            best_title_f = next((f.name for f in parent.fields if f.name != "id"), "id")

        label = _title_case(rel.name)
        result.append(
            ParentRelationInfo(
                field_name=fk_field,
                relation_name=rel.name,
                parent_entity=parent,
                parent_plural=parent_plural,
                hook_name=hook_name,
                title_field=best_title_f,
                label=label,
            )
        )

    for f in entity.fields:
        if f.name.endswith("_id") and f.name not in seen_fields:
            stem = f.name[:-3]
            parent = next(
                (
                    e for e in ir.entities
                    if e.name.lower() == stem.lower() or _snake(e.name) == stem.lower()
                ),
                None,
            )
            if parent is not None and Op.LIST in ops_by_entity.get(parent.name, set()):
                parent_plural = parent.name if parent.name.endswith("s") else f"{parent.name}s"
                hook_name = f"useList{parent_plural}"
                best_title_f = next((f.name for f in parent.fields if f.name in ("title", "name", "label", "email")), None)
                if not best_title_f:
                    best_title_f = next((f.name for f in parent.fields if f.name != "id"), "id")
                seen_fields.add(f.name)
                result.append(
                    ParentRelationInfo(
                        field_name=f.name,
                        relation_name=stem,
                        parent_entity=parent,
                        parent_plural=parent_plural,
                        hook_name=hook_name,
                        title_field=best_title_f,
                        label=_title_case(stem),
                    )
                )

    return result


def _filterable_fields_for_entity(entity: Entity) -> list[tuple[Field, str, list[str]]]:
    """Returns list of (field, kind, options) for boolean and enum fields.
    kind is 'boolean' (options ['true', 'false']) or 'enum' (options parsed from validation rule).
    """
    res: list[tuple[Field, str, list[str]]] = []
    for f in entity.fields:
        if f.name == "id":
            continue
        if f.type in (FieldType.BOOL, "bool"):
            res.append((f, "boolean", ["true", "false"]))
        else:
            enum_rule = next((r for r in f.validation if r.startswith("enum:")), None)
            if enum_rule:
                opts = [o.strip() for o in enum_rule.split(":", 1)[1].split("|") if o.strip()]
                if opts:
                    res.append((f, "enum", opts))
    return res


def _field_value_jsx(field: Field, expr: str) -> str:
    """R-302: renders an accessible formatted value or badge for a field expression.

    - Boolean fields render an emerald/slate status pill badge.
    - Enum fields render a blue categorical pill badge.
    - Datetime fields format to local date string.
    - Long text fields truncate gracefully at 60 chars.
    - Numeric fields format numbers with fallback to '-'.
    - Other string fields format text with fallback to '-'.
    """
    enum_rules = parse_field_rules(field)
    if field.type in (FieldType.BOOL, "bool"):
        return (
            '<span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 600, '
            f'background: {expr} ? "#dcfce7" : "#f1f5f9", '
            f'color: {expr} ? "#166534" : "#64748b" }}>'
            f'{{{expr} ? "Yes" : "No"}}</span>'
        )
    if enum_rules.enum:
        return (
            f'{{{expr} !== undefined && {expr} !== null ? ('
            '<span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 600, '
            'background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" }}>'
            f'{{String({expr})}}</span>'
            ') : "-"}'
        )
    if field.type == FieldType.DATETIME:
        return f'{{{expr} ? new Date({expr}).toLocaleDateString() : "-"}}'
    if field.type == FieldType.TEXT:
        return (
            f'{{{expr} ? (String({expr}).length > 60 ? '
            f'String({expr}).slice(0, 60) + "..." : String({expr})) : "-"}}'
        )
    if field.type in (FieldType.INT, FieldType.FLOAT):
        return f'{{{expr} !== undefined && {expr} !== null ? String({expr}) : "-"}}'
    return f'{{{expr} !== undefined ? String({expr}) : "-"}}'


def _collection_screen_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op]) -> str:  # noqa: PLR0912
    name = entity.name
    plural = name if name.endswith("s") else f"{name}s"
    can_delete = Op.DELETE in ops
    page_name = f"{_pascal(screen.id)}Page"
    title = _title_case(screen.id)

    subcollections = _subcollections_for_parent(name, ir)
    has_subcollections = bool(subcollections)
    filterable_fields = _filterable_fields_for_entity(entity)

    # Check for complementary screens in ir.screens
    form_screen: Screen | None = None
    detail_screen: Screen | None = None
    for s in ir.screens:
        if s.id != screen.id:
            s_entity = _match_entity(s, ir)
            if s_entity and s_entity.name == entity.name:
                s_intent = _screen_intent(s)
                if s_intent == "form" and not form_screen:
                    form_screen = s
                elif s_intent == "detail" and not detail_screen:
                    detail_screen = s

    # Select fields to display in table columns (skip 'id' unless it's the only field, limit to 5)
    display_fields = [f for f in entity.fields if f.name != "id"]
    if not display_fields:
        display_fields = list(entity.fields[:1])
    display_fields = display_fields[:5]

    hooks_import = f"useList{plural}"
    if can_delete:
        hooks_import += f", useDelete{name}"

    uses_confirm = can_delete or any(sub.can_delete for sub in subcollections)

    lines: list[str] = [
        '"use client";',
        "",
        'import { useEffect, useState } from "react";',
        'import { useRef } from "react";',
        'import Link from "next/link";',
        'import { useToast } from "../components/toast";',
        *([
            'import { useConfirm, ConfirmDialog } from "../components/confirm-dialog";',
        ] if uses_confirm else []),
        f'import {{ {hooks_import} }} from "../lib/hooks";',
    ]

    if has_subcollections:
        subcol_hook_names = [sub.hook_name for sub in subcollections]
        for sub in subcollections:
            if sub.can_delete:
                del_hook = f"useDelete{sub.child_entity.name}"
                if del_hook not in subcol_hook_names and (not can_delete or del_hook != f"useDelete{name}"):
                    subcol_hook_names.append(del_hook)
        lines.append(f'import {{ {", ".join(subcol_hook_names)} }} from "../lib/hooks";')

    lines.append(f'import type {{ {name} }} from "../lib/types";')

    if has_subcollections:
        child_type_names = list(dict.fromkeys(sub.child_entity.name for sub in subcollections if sub.child_entity.name != name))
        if child_type_names:
            lines.append(f'import type {{ {", ".join(child_type_names)} }} from "../lib/types";')

    lines.extend([
        "",
        f"export default function {page_name}() {{",
        f"  const {{",
        "    data,",
        "    total,",
        "    loading,",
        "    error,",
        "    page,",
        "    pageSize,",
        "    totalPages,",
        "    params,",
        "    setPage,",
        "    setPageSize,",
        "    setSearch,",
        "    setSort,",
        *(["    setFilter,", "    clearFilters,"] if filterable_fields else []),
        "    refetch,",
        f"  }} = useList{plural}();",
        "  const { toast } = useToast();",
    ])

    if filterable_fields:
        lines.extend([
            "  const filterValues = params.filters ?? {};",
            "  const activeFilterCount = Object.keys(filterValues).length;",
            "  const displayData = data ?? [];",
        ])
    else:
        lines.extend([
            "  const displayData = data ?? [];",
        ])


    lines.extend([
        "  const [checkedIds, setCheckedIds] = useState<string[]>([]);",
        "  // R-290: optimistically hide rows being deleted; the reconcile effect prunes ids once refetch removes them.",
        "  const [pendingDeleteIds, setPendingDeleteIds] = useState<string[]>([]);",
        "  useEffect(() => {",
        "    setPendingDeleteIds((prev) => prev.filter((id) => (data ?? []).some((x: any) => String(x.id) === id)));",
        "  }, [data]);",
        "  const visibleRows = displayData.filter((item: any) => !pendingDeleteIds.includes(String((item as any).id)));",
        "  const allCurrentIds = (data ?? []).map((item: any) => item.id).filter(Boolean);",
        "  const isAllChecked = allCurrentIds.length > 0 && allCurrentIds.every((id: string) => checkedIds.includes(id));",
        "  const handleCheckAll = () => {",
        "    if (isAllChecked) {",
        "      setCheckedIds((prev) => prev.filter((id) => !allCurrentIds.includes(id)));",
        "    } else {",
        "      setCheckedIds((prev) => Array.from(new Set([...prev, ...allCurrentIds])));",
        "    }",
        "  };",
        "  const handleToggleRow = (id: string) => {",
        "    setCheckedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));",
        "  };",
        "  const handleClearSelection = () => {",
        "    setCheckedIds([]);",
        "  };",
        '  const [density, setDensity] = useState<"compact" | "comfortable" | "spacious">("comfortable");',
        '  const densityPadding = density === "compact" ? "6px 12px" : density === "spacious" ? "16px 20px" : "12px 16px";',
        '  const densityFontSize = density === "compact" ? 13 : 14;',
        '  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>({ ' + ", ".join(f'"{f.name}": true' for f in display_fields) + ' });',
        '  const [showColumnPicker, setShowColumnPicker] = useState<boolean>(false);',
        '  const toggleColumn = (colName: string) => {',
        '    setVisibleColumns((prev) => {',
        '      const currentVisible = Object.keys(prev).filter((k) => prev[k]);',
        '      if (prev[colName] && currentVisible.length <= 1) {',
        '        return prev;',
        '      }',
        '      return { ...prev, [colName]: !prev[colName] };',
        '    });',
        '  };',
    ])

    csv_headers_ts = ", ".join(f'"{f.name}"' for f in entity.fields)
    csv_row_ts = ", ".join(f"toCsvVal((item as any).{f.name})" for f in entity.fields)

    lines.extend([
        "  const handleExportCsv = (selectedOnly: boolean = false) => {",
        "    const itemsToExport = selectedOnly",
        "      ? (data ?? []).filter((item: any) => checkedIds.includes(item.id))",
        "      : (data ?? []);",
        "    if (itemsToExport.length === 0) return;",
        "    const toCsvVal = (val: unknown): string => {",
        '      if (val === null || val === undefined) return \'""\';',
        '      const str = typeof val === "object" ? JSON.stringify(val) : String(val);',
        '      return `"${str.replace(/"/g, \'""\')}"`;',
        "    };",
        f"    const headers = [{csv_headers_ts}];",
        f"    const rows = itemsToExport.map((item: any) => [{csv_row_ts}].join(\",\"));",
        '    const csvContent = [headers.join(","), ...rows].join("\\n");',
        '    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });',
        "    const url = URL.createObjectURL(blob);",
        '    const link = document.createElement("a");',
        '    link.setAttribute("href", url);',
        f'    link.setAttribute("download", "{plural.lower()}_export.csv");',
        "    document.body.appendChild(link);",
        "    link.click();",
        "    document.body.removeChild(link);",
        "    URL.revokeObjectURL(url);",
        '    toast.info("Exported CSV successfully");',
        "  };",
        "",
        "  const handleExportJson = (selectedOnly: boolean = false) => {",
        "    const itemsToExport = selectedOnly",
        "      ? (data ?? []).filter((item: any) => checkedIds.includes(item.id))",
        "      : (data ?? []);",
        "    if (itemsToExport.length === 0) return;",
        '    const jsonContent = JSON.stringify(itemsToExport, null, 2);',
        '    const blob = new Blob([jsonContent], { type: "application/json;charset=utf-8;" });',
        "    const url = URL.createObjectURL(blob);",
        '    const link = document.createElement("a");',
        '    link.setAttribute("href", url);',
        f'    link.setAttribute("download", "{plural.lower()}_export.json");',
        "    document.body.appendChild(link);",
        "    link.click();",
        "    document.body.removeChild(link);",
        "    URL.revokeObjectURL(url);",
        '    toast.info("Exported JSON successfully");',
        "  };",
    ])

    if can_delete:
        lines.extend([
            f"  const {{ remove }} = useDelete{name}();",
            "  const [batchDeleting, setBatchDeleting] = useState<boolean>(false);",
            "  const [batchDeleteError, setBatchDeleteError] = useState<string | null>(null);",
            "  // R-304: accessible async confirmation dialog.",
            "  const { confirmAsync, confirmProps } = useConfirm();",
            "",
            "  const handleDelete = async (id: string) => {",
            f'    const ok = await confirmAsync("Delete {name}", "Are you sure you want to delete this {name}? This action cannot be undone.");',
            "    if (!ok) return;",
            "      setPendingDeleteIds((prev) => [...prev, String(id)]);",
            "      try {",
            "        await remove(id);",
            "        setCheckedIds((prev) => prev.filter((x) => x !== id));",
            "        refetch();",
            f'        toast.success("{name} deleted successfully");',
            "      } catch (err) {",
            "        setPendingDeleteIds((prev) => prev.filter((x) => x !== String(id)));",
            f'        toast.error(err instanceof Error ? err.message : "Failed to delete {name}");',
            "      }",
            "  };",
            "",
            "  const handleBatchDelete = async () => {",
            "    if (checkedIds.length === 0) return;",
            f'    const batchMsg = `Are you sure you want to delete ${{checkedIds.length}} ${{checkedIds.length === 1 ? "{name}" : "{plural}"}}? This action cannot be undone.`;',
            f'    const batchOk = await confirmAsync(`Delete ${{checkedIds.length}} ${{checkedIds.length === 1 ? "{name}" : "{plural}"}}`, batchMsg);',
            "    if (!batchOk) return;",
            "    const ids = checkedIds.map(String);",
            "    setBatchDeleting(true);",
            "    setBatchDeleteError(null);",
            "    setPendingDeleteIds((prev) => [...prev, ...ids]);",
            "    try {",
            "      await Promise.all(checkedIds.map((id) => remove(id)));",
            "      const count = checkedIds.length;",
            "      setCheckedIds([]);",
            "      refetch();",
            f'      toast.success(`Deleted ${{count}} ${{count === 1 ? "{name}" : "{plural}"}} successfully`);',
            "    } catch (err) {",
            "      setPendingDeleteIds((prev) => prev.filter((x) => !ids.includes(x)));",
            "      setBatchDeleteError(err instanceof Error ? err.message : \"Failed to delete selected items\");",
            "      toast.error(err instanceof Error ? err.message : \"Failed to delete selected items\");",
            "    } finally {",
            "      setBatchDeleting(false);",
            "    }",
            "  };",
        ])

    lines.append('  const [searchInput, setSearchInput] = useState(params.q ?? "");')
    lines.append('  const searchInputRef = useRef<HTMLInputElement>(null);')
    lines.extend([
        "  // R-280: debounce committed search so typing does not fetch on every keystroke.",
        "  useEffect(() => {",
        "    const timer = setTimeout(() => {",
        '      if (searchInput !== (params.q ?? "")) setSearch(searchInput);',
        "    }, 300);",
        "    return () => clearTimeout(timer);",
        "  }, [searchInput, params.q, setSearch]);",
        "  // R-280: reflect the deep-linked / hydrated search term back into the input box.",
        "  useEffect(() => {",
        '    setSearchInput(params.q ?? "");',
        "  }, [params.q]);",
        "  // R-297: collection keyboard navigation & shortcuts ('/' to focus search, 'Escape' to clear).",
        "  useEffect(() => {",
        "    const handleKeyDown = (e: KeyboardEvent) => {",
        '      const target = e.target as HTMLElement | null;',
        '      const isEditable = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable);',
        '      if (e.key === "/" && !isEditable) {',
        "        e.preventDefault();",
        "        searchInputRef.current?.focus();",
        '      } else if (e.key === "Escape") {',
        "        if (document.activeElement === searchInputRef.current) {",
        '          setSearchInput("");',
        '          setSearch("");',
        "          searchInputRef.current?.blur();",
        *(["        } else if (!isEditable && activeFilterCount > 0) {", "          clearFilters();"] if filterable_fields else []),
        "        }",
        "      }",
        "    };",
        '    window.addEventListener("keydown", handleKeyDown);',
        '    return () => window.removeEventListener("keydown", handleKeyDown);',
    ])
    shortcut_deps = ["setSearch"]
    if filterable_fields:
        shortcut_deps.extend(["activeFilterCount", "clearFilters"])
    lines.append(f'  }}, [{", ".join(shortcut_deps)}]);')

    if has_subcollections:
        lines.append('  const [selectedId, setSelectedId] = useState<string | null>(null);')
        if len(subcollections) > 1:
            lines.append('  const [activeTab, setActiveTab] = useState<number>(0);')
        for sub in subcollections:
            s_var = f"{sub.child_entity.name.lower()}sSubcol"
            lines.append(f"  const {s_var} = {sub.hook_name}(selectedId);")
            lines.extend(_subcol_search_state(s_var))

        child_entities_with_delete = list(dict.fromkeys(
            sub.child_entity.name for sub in subcollections if sub.can_delete
        ))
        for c_name in child_entities_with_delete:
            lines.append(
                f"  const {{ remove: remove{c_name}, loading: deleting{c_name}, error: delete{c_name}Error }} = useDelete{c_name}();"
            )

        c_names = [sub.child_entity.name for sub in subcollections]
        def _col_del_handler_name(sub: SubcollectionInfo) -> str:
            if c_names.count(sub.child_entity.name) > 1:
                return f"handleDelete{_pascal(sub.relation)}{sub.child_entity.name}"
            return f"handleDelete{sub.child_entity.name}"

        for sub in subcollections:
            if sub.can_delete:
                h_name = _col_del_handler_name(sub)
                c_name = sub.child_entity.name
                s_var = f"{sub.child_entity.name.lower()}sSubcol"
                _del_state, _del_setter = _subcol_delete_names(s_var)
                lines.extend([
                    # R-291: optimistic child delete — hide the row immediately, roll back on error.
                    f"  const [{_del_state}, {_del_setter}] = useState<string[]>([]);",
                    "  useEffect(() => {",
                    f"    {_del_setter}((prev) => prev.filter((did) => ({s_var}.data ?? []).some((x: any) => String(x.id) === did)));",
                    f"  }}, [{s_var}.data]);",
                    f"  const {h_name} = async (id: string) => {{",
                    f'    const ok = await confirmAsync("Delete {c_name}", "Are you sure you want to delete this {c_name}? This action cannot be undone.");',
                    "    if (!ok) return;",
                    f"      {_del_setter}((prev) => [...prev, String(id)]);",
                    "      try {",
                    f"        await remove{c_name}(id);",
                    f"        {s_var}.refetch();",
                    f'        toast.success("{c_name} deleted successfully");',
                    "      } catch (err) {",
                    f"        {_del_setter}((prev) => prev.filter((x) => x !== String(id)));",
                    f'        toast.error(err instanceof Error ? err.message : "Failed to delete {c_name}");',
                    "      }",
                    "  };",
                ])

        best_title_f = next((f.name for f in entity.fields if f.name in ("title", "name", "label", "email")), None)
        if not best_title_f:
            best_title_f = next((f.name for f in entity.fields if f.name != "id"), "id")
        lines.append("  const selectedItem = data?.find((item) => (item as any).id === selectedId);")

    lines.extend([
        "",
        "  return (",
        '    <main style={{ maxWidth: 960, margin: "0 auto", padding: "32px 16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>',
        '      <header style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>',
        "        <div>",
        '          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>',
        '            <Link href="/" style={{ color: "#2563eb", textDecoration: "none", fontSize: 13, fontWeight: 500 }}>&larr; Overview</Link>',
        '            <span style={{ color: "#94a3b8" }}>/</span>',
        f'            <span style={{ fontSize: 12, padding: "2px 8px", background: "#f1f5f9", color: "#475569", borderRadius: 4, fontWeight: 600 }}>{screen.role}</span>',
        "          </div>",
        f'          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#0f172a" }}>{title}</h1>',
        "        </div>",
        '        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>',
    ])

    if form_screen:
        lines.append(
            f'          <Link href="/{form_screen.id}" style={{{{ padding: "8px 16px", background: "#2563eb", color: "#fff", borderRadius: 6, textDecoration: "none", fontSize: 14, fontWeight: 500 }}}}>+ New {name}</Link>'
        )

    for nav in screen.navigation:
        if not form_screen or nav != form_screen.id:
            lines.append(
                f'          <Link href="/{nav}" style={{{{ padding: "8px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, textDecoration: "none", fontSize: 14 }}}}>{_pascal(nav)}</Link>'
            )

    lines.extend([
        "        </div>",
        "      </header>",
        "",
        '      <section style={{ marginBottom: 20, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>',
        "        <form",
        "          onSubmit={(e) => {",
        "            e.preventDefault();",
        "            setSearch(searchInput);",
        "          }}",
        '          style={{ display: "flex", gap: 8, flex: 1, minWidth: 260 }}',
        "        >",
        '          <div style={{ position: "relative", flex: 1, display: "flex", alignItems: "center" }}>',
        "            <input",
        '              type="search"',
        "              ref={searchInputRef}",
        f'              aria-label="Search {plural}"',
        "              value={searchInput}",
        "              onChange={(e) => {{",
        "                setSearchInput(e.target.value);",
        "              }}}}",
        f'              placeholder="Search {plural}..."',
        '              style={{ width: "100%", padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, outline: "none", boxSizing: "border-box" }}',
        "            />",
        "            {Boolean(searchInput) && (",
        "              <button",
        '                type="button"',
        '                onClick={() => {{ setSearchInput(""); setSearch(""); searchInputRef.current?.focus(); }}}}',
        '                aria-label="Clear search"',
        '                style={{ position: "absolute", right: 8, background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: 2 }}',
        "              >",
        "                &times;",
        "              </button>",
        "            )}",
        "          </div>",
        '          <button type="submit" style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, fontWeight: 500, cursor: "pointer" }}>',
        "            Search",
        "          </button>",
        "        </form>",
        "        <button",
        "          onClick={() => refetch()}",
        "          disabled={loading}",
        '          style={{ padding: "8px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, fontSize: 14, cursor: loading ? "default" : "pointer" }}',
        "        >",
        '          {loading ? "Loading..." : "Refresh"}',
        "        </button>",
        "        <button",
        '          type="button"',
        "          onClick={() => handleExportCsv(false)}",
        "          disabled={!data || data.length === 0}",
        '          style={{ padding: "8px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, fontSize: 14, cursor: (!data || data.length === 0) ? "default" : "pointer" }}',
        "        >",
        '          Export CSV',
        "        </button>",
        "        <button",
        '          type="button"',
        "          onClick={() => handleExportJson(false)}",
        "          disabled={!data || data.length === 0}",
        '          style={{ padding: "8px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, fontSize: 14, cursor: (!data || data.length === 0) ? "default" : "pointer" }}',
        "        >",
        '          Export JSON',
        "        </button>",
        '        <div style={{ position: "relative", display: "inline-block" }}>',
        '          <button',
        '            type="button"',
        '            aria-haspopup="true"',
        '            aria-expanded={showColumnPicker}',
        '            aria-label="Toggle column visibility"',
        '            onClick={() => setShowColumnPicker((prev) => !prev)}',
        '            style={{ padding: "8px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, fontSize: 14, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6 }}',
        '          >',
        '            Columns &#9662;',
        '          </button>',
        '          {showColumnPicker && (',
        '            <div',
        '              role="menu"',
        '              aria-label="Column visibility options"',
        '              style={{ position: "absolute", right: 0, top: "100%", marginTop: 4, background: "#fff", border: "1px solid #cbd5e1", borderRadius: 8, boxShadow: "0 4px 12px rgba(0,0,0,0.1)", padding: "8px 0", minWidth: 160, zIndex: 20 }}',
        '            >',
        *([
            item
            for f in display_fields
            for item in [
                '              <label style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 14px", cursor: "pointer", fontSize: 13, color: "#334155" }}>',
                '                <input',
                '                  type="checkbox"',
                f'                  aria-label="Toggle {_title_case(f.name)} column"',
                f'                  checked={{visibleColumns["{f.name}"] !== false}}',
                f'                  onChange={{() => toggleColumn("{f.name}")}}',
                '                  style={{ cursor: "pointer" }}',
                '                />',
                f'                <span>{_title_case(f.name)}</span>',
                '              </label>',
            ]
        ]),
        '            </div>',
        '          )}',
        '        </div>',
        '        <div role="group" aria-label="Table display density" style={{ display: "inline-flex", borderRadius: 6, border: "1px solid #cbd5e1", overflow: "hidden", fontSize: 12, fontWeight: 500, marginLeft: "auto" }}>',
        '          <button',
        '            type="button"',
        '            aria-label="Compact density"',
        '            aria-pressed={density === "compact"}',
        '            onClick={() => setDensity("compact")}',
        '            style={{ padding: "6px 10px", border: "none", background: density === "compact" ? "#0f172a" : "#fff", color: density === "compact" ? "#fff" : "#475569", cursor: "pointer" }}',
        '          >',
        '            Compact',
        '          </button>',
        '          <button',
        '            type="button"',
        '            aria-label="Comfortable density"',
        '            aria-pressed={density === "comfortable"}',
        '            onClick={() => setDensity("comfortable")}',
        '            style={{ padding: "6px 10px", border: "none", borderLeft: "1px solid #cbd5e1", background: density === "comfortable" ? "#0f172a" : "#fff", color: density === "comfortable" ? "#fff" : "#475569", cursor: "pointer" }}',
        '          >',
        '            Comfortable',
        '          </button>',
        '          <button',
        '            type="button"',
        '            aria-label="Spacious density"',
        '            aria-pressed={density === "spacious"}',
        '            onClick={() => setDensity("spacious")}',
        '            style={{ padding: "6px 10px", border: "none", borderLeft: "1px solid #cbd5e1", background: density === "spacious" ? "#0f172a" : "#fff", color: density === "spacious" ? "#fff" : "#475569", cursor: "pointer" }}',
        '          >',
        '            Spacious',
        '          </button>',
        '        </div>',
        "      </section>",
        "",
    ])

    if filterable_fields:
        lines.extend([
            '      <div style={{ marginBottom: 16, padding: "10px 14px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>',
            '        <span style={{ fontSize: 13, fontWeight: 600, color: "#475569" }}>Filters:</span>',
        ])
        for f, kind, opts in filterable_fields:
            f_label = _title_case(f.name)
            if kind == "boolean":
                lines.extend([
                    '        <div style={{ display: "inline-flex", borderRadius: 6, border: "1px solid #cbd5e1", overflow: "hidden", fontSize: 12, fontWeight: 500 }}>',
                    '          <button',
                    '            type="button"',
                    f'            onClick={{() => setFilter("{f.name}", "all")}}',
                    f'            style={{{{ padding: "4px 10px", border: "none", background: (!filterValues["{f.name}"] || filterValues["{f.name}"] === "all") ? "#0f172a" : "#fff", color: (!filterValues["{f.name}"] || filterValues["{f.name}"] === "all") ? "#fff" : "#475569", cursor: "pointer" }}}}',
                    '          >',
                    '            All',
                    '          </button>',
                    '          <button',
                    '            type="button"',
                    f'            onClick={{() => setFilter("{f.name}", "true")}}',
                    f'            style={{{{ padding: "4px 10px", border: "none", borderLeft: "1px solid #cbd5e1", background: filterValues["{f.name}"] === "true" ? "#0f172a" : "#fff", color: filterValues["{f.name}"] === "true" ? "#fff" : "#475569", cursor: "pointer" }}}}',
                    '          >',
                    f'            {f_label}: Yes',
                    '          </button>',
                    '          <button',
                    '            type="button"',
                    f'            onClick={{() => setFilter("{f.name}", "false")}}',
                    f'            style={{{{ padding: "4px 10px", border: "none", borderLeft: "1px solid #cbd5e1", background: filterValues["{f.name}"] === "false" ? "#0f172a" : "#fff", color: filterValues["{f.name}"] === "false" ? "#fff" : "#475569", cursor: "pointer" }}}}',
                    '          >',
                    f'            {f_label}: No',
                    '          </button>',
                    '        </div>',
                ])
            elif kind == "enum":
                lines.extend([
                    '        <select',
                    f'          aria-label="Filter by {f_label}"',
                    f'          value={{filterValues["{f.name}"] || "all"}}',
                    f'          onChange={{(e) => setFilter("{f.name}", e.target.value)}}',
                    f'          style={{{{ padding: "4px 10px", borderRadius: 6, border: "1px solid #cbd5e1", background: "#fff", color: "#334155", fontSize: 12, cursor: "pointer", outline: "none" }}}}',
                    '        >',
                    f'          <option value="all">All {f_label}s</option>',
                ])
                for opt in opts:
                    lines.append(f'          <option value="{opt}">{_title_case(opt)}</option>')
                lines.append('        </select>')

        lines.extend([
            '        {activeFilterCount > 0 && (',
            '          <span style={{ fontSize: 12, padding: "2px 8px", background: "#eff6ff", color: "#1d4ed8", borderRadius: 12, fontWeight: 600 }}>',
            '            {activeFilterCount} active',
            '          </span>',
            '        )}',
            '        {activeFilterCount > 0 && (',
            '          <button',
            '            type="button"',
            '            onClick={clearFilters}',
            '            style={{ background: "none", border: "none", color: "#2563eb", fontSize: 13, cursor: "pointer", padding: "4px 8px", textDecoration: "underline" }}',
            '          >',
            '            Reset',
            '          </button>',
            '        )}',
            '      </div>',
            '',
        ])

    lines.extend([
        "      {error && (",
        '        <div role="alert" aria-live="assertive" style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#991b1b", marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "center" }}>',
        "          <span>Error: {error.message}</span>",
        '          <button onClick={() => refetch()} style={{ padding: "4px 8px", background: "#991b1b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}>Retry</button>',
        "        </div>",
        "      )}",
        "",
    ])

    lines.extend([
        "      {checkedIds.length > 0 && (",
        '        <div style={{ marginBottom: 16, padding: "10px 16px", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 8, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>',
        '          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>',
        '            <span style={{ fontSize: 14, fontWeight: 600, color: "#1e40af" }}>',
        f'              {{checkedIds.length}} {{checkedIds.length === 1 ? "{name}" : "{plural}"}} selected',
        "            </span>",
        "            <button",
        '              type="button"',
        "              onClick={handleClearSelection}",
        '              style={{ padding: "4px 8px", background: "none", border: "1px solid #93c5fd", color: "#1d4ed8", borderRadius: 4, fontSize: 12, cursor: "pointer" }}',
        "            >",
        "              Clear selection",
        "            </button>",
        "          </div>",
        '          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>',
        "            <button",
        '              type="button"',
        "              onClick={() => handleExportCsv(true)}",
        '              style={{ padding: "6px 14px", border: "1px solid #93c5fd", background: "#fff", color: "#1d4ed8", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: "pointer" }}',
        "            >",
        f'              {{`Export Selected (${{checkedIds.length}})`}}',
        "            </button>",
            "            <button",
            '              type="button"',
            "              onClick={() => handleExportJson(true)}",
            '              style={{ padding: "6px 14px", border: "1px solid #93c5fd", background: "#fff", color: "#1d4ed8", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: "pointer" }}',
            "            >",
            f'              {{`Export JSON (${{checkedIds.length}})`}}',
            "            </button>",
    ])

    if can_delete:
        lines.extend([
            "            <button",
            '              type="button"',
            "              onClick={handleBatchDelete}",
            "              disabled={batchDeleting}",
            '              style={{ padding: "6px 14px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: batchDeleting ? "default" : "pointer" }}',
            "            >",
            f'              {{batchDeleting ? "Deleting..." : `Delete Selected (${{checkedIds.length}})`}}',
            "            </button>",
        ])

    lines.extend([
        "          </div>",
        "        </div>",
        "      )}",
    ])

    if can_delete:
        lines.extend([
            "",
            "      {batchDeleteError && (",
            '        <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#991b1b", marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>',
            '          <span>Error deleting selected items: {batchDeleteError}</span>',
            '          <button onClick={() => setBatchDeleteError(null)} style={{ padding: "4px 8px", background: "#991b1b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}>Dismiss</button>',
            "        </div>",
            "      )}",
        ])

    lines.extend([
        "",
        '      <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden", background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>',
        '        <table data-density={density} style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: densityFontSize }}>',
        '          <thead style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>',
        "            <tr>",
        '              <th style={{ padding: "12px 16px", width: 40, textAlign: "center" }}>',
        '                <input',
        '                  type="checkbox"',
        '                  aria-label="Select all"',
        '                  checked={isAllChecked}',
        '                  onChange={handleCheckAll}',
        '                  style={{ cursor: "pointer" }}',
        '                />',
        '              </th>',
    ])

    for f in display_fields:
        col_label = _title_case(f.name)
        lines.extend([
            '              {visibleColumns["' + f.name + '"] !== false && (',
            '                <th onClick={() => setSort("' + f.name + '")} aria-sort={params.sort === "' + f.name + '" ? (params.order === "desc" ? "descending" : "ascending") : "none"} style={{ padding: "12px 16px", fontWeight: 600, color: "#475569", cursor: "pointer", userSelect: "none" }}>',
            '                  ' + col_label + ' {params.sort === "' + f.name + '" ? (params.order === "desc" ? "↓" : "↑") : ""}',
            "                </th>",
            "              )}",
        ])

    can_edit = (Op.UPDATE in ops) and (form_screen is not None)
    has_actions_col = can_delete or has_subcollections or can_edit or (detail_screen is not None)
    if has_actions_col:
        actions_header = "Actions" if (can_delete or can_edit or detail_screen is not None) else "Details"
        lines.append(
            f'              <th style={{{{ padding: "12px 16px", textAlign: "right", fontWeight: 600, color: "#475569" }}}}>{actions_header}</th>'
        )

    lines.extend([
        "            </tr>",
        "          </thead>",
        "          <tbody>",
        "            {loading && !data && (",
        "              <tr>",
        f'                <td colSpan={{{1 + len(display_fields) + (1 if has_actions_col else 0)}}} style={{{{ padding: 16 }}}}>',
        "                  {/* R-292: loading skeleton rows */}",
        "                  {[0, 1, 2, 3, 4].map((i) => (",
        '                    <div key={i} style={{ height: 14, background: "#e2e8f0", borderRadius: 4, margin: "10px 0", opacity: 1 - i * 0.15 }} />',
        "                  ))}",
        "                </td>",
        "              </tr>",
        "            )}",
    ])

    empty_cond = "{data && displayData.length === 0 && (" if filterable_fields else "{data && data.length === 0 && ("
    lines.extend([
        f"            {empty_cond}",
        "              <tr>",
        f'                <td colSpan={{{1 + len(display_fields) + (1 if has_actions_col else 0)}}} style={{{{ padding: 32, textAlign: "center", color: "#64748b" }}}}>',
    ])

    if filterable_fields:
        lines.extend([
            "                  {activeFilterCount > 0 ? (",
            '                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>',
            f"                      <div role=\"status\">No {plural} match the active filter criteria.</div>",
            "                      <button",
            '                        type="button"',
            "                        onClick={clearFilters}",
            '                        style={{ padding: "6px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#2563eb", borderRadius: 6, fontSize: 13, cursor: "pointer", fontWeight: 500 }}',
            "                      >",
            "                        Clear all filters",
            "                      </button>",
            "                    </div>",
            "                  ) : searchInput.trim() ? (",
        ])
    else:
        lines.append("                  {searchInput.trim() ? (")

    lines.extend([
        '                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>',
        f"                      <div role=\"status\">No {plural} matching &ldquo;{{searchInput}}&rdquo;.</div>",
        "                      <button",
        '                        type="button"',
        "                        onClick={() => {",
        '                          setSearchInput("");',
        '                          setSearch("");',
        "                        }}",
        '                        style={{ padding: "6px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#2563eb", borderRadius: 6, fontSize: 13, cursor: "pointer", fontWeight: 500 }}',
        "                      >",
        "                        Clear search",
        "                      </button>",
        "                    </div>",
    ])

    if form_screen:
        lines.extend([
            "                  ) : (",
            '                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>',
            f"                      <div role=\"status\">No {plural} found yet.</div>",
            '                      <Link',
            f'                        href="/{form_screen.id}"',
            '                        style={{ display: "inline-block", padding: "8px 16px", background: "#2563eb", color: "#fff", borderRadius: 6, fontSize: 14, textDecoration: "none", fontWeight: 500 }}',
            '                      >',
            f"                        + Create first {name}",
            '                      </Link>',
            "                    </div>",
            "                  )}",
        ])
    else:
        lines.extend([
            "                  ) : (",
            f"                    <div role=\"status\">No {plural} found.</div>",
            "                  )}",
        ])

    lines.extend([
        "                </td>",
        "              </tr>",
        "            )}",
    ])

    # R-290: render the pending-delete-filtered rows (visibleRows) so optimistically removed rows vanish.
    lines.append("            {data && visibleRows.map((item, idx) => (")


    if has_subcollections:
        lines.append('              <tr key={(item as any).id ?? idx} onClick={() => setSelectedId(selectedId === (item as any).id ? null : (item as any).id)} style={{ borderBottom: "1px solid #f1f5f9", cursor: "pointer", background: selectedId === (item as any).id ? "#eff6ff" : (checkedIds.includes((item as any).id) ? "#f8fafc" : undefined) }}>')
    else:
        lines.append('              <tr key={(item as any).id ?? idx} style={{ borderBottom: "1px solid #f1f5f9", background: checkedIds.includes((item as any).id) ? "#f8fafc" : undefined }}>')

    lines.extend([
        '                <td style={{ padding: densityPadding, textAlign: "center", width: 40 }} onClick={(e) => e.stopPropagation()}>',
        '                  <input',
        '                    type="checkbox"',
        '                    aria-label={`Select ${(item as any).id ?? idx}`}',
        '                    checked={checkedIds.includes((item as any).id)}',
        '                    onChange={() => handleToggleRow((item as any).id)}',
        '                    style={{ cursor: "pointer" }}',
        '                  />',
        '                </td>',
    ])

    for f in display_fields:
        enum_rules = parse_field_rules(f)
        if f.type == FieldType.BOOL:
            val_expr = (
                '<span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 600, '
                'background: (item as any).' + f.name + ' ? "#dcfce7" : "#f1f5f9", '
                'color: (item as any).' + f.name + ' ? "#166534" : "#64748b" }}>'
                '{(item as any).' + f.name + ' ? "Yes" : "No"}</span>'
            )
        elif enum_rules.enum:
            val_expr = (
                '{(item as any).' + f.name + ' !== undefined && (item as any).' + f.name + ' !== null ? ('
                '<span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 600, '
                'background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" }}>'
                '{String((item as any).' + f.name + ')}</span>'
                ') : "-"}'
            )
        elif f.type == FieldType.DATETIME:
            val_expr = '{(item as any).' + f.name + ' ? new Date((item as any).' + f.name + ').toLocaleDateString() : "-"}'
        elif f.type == FieldType.TEXT:
            val_expr = (
                '{(item as any).' + f.name + ' ? (String((item as any).' + f.name + ').length > 60 ? '
                'String((item as any).' + f.name + ').slice(0, 60) + "..." : String((item as any).' + f.name + ')) : "-"}'
            )
        elif f.type in (FieldType.INT, FieldType.FLOAT):
            val_expr = '{(item as any).' + f.name + ' !== undefined && (item as any).' + f.name + ' !== null ? String((item as any).' + f.name + ') : "-"}'
        else:
            val_expr = '{(item as any).' + f.name + ' !== undefined ? String((item as any).' + f.name + ') : "-"}'

        lines.extend([
            '                {visibleColumns["' + f.name + '"] !== false && (',
            '                  <td style={{ padding: densityPadding, color: "#1e293b" }}>' + val_expr + '</td>',
            '                )}',
        ])

    if has_actions_col:
        lines.append('                <td style={{ padding: densityPadding, textAlign: "right", whiteSpace: "nowrap" }}>')
        if detail_screen:
            margin_style = " marginRight: 8," if (has_subcollections or can_edit or can_delete) else ""
            lines.extend([
                '                  <Link',
                f"                    href={{`/{detail_screen.id}?id=${{(item as any).id}}`}}",
                '                    onClick={(e) => e.stopPropagation()}',
                f'                    style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: "#fff", color: "#2563eb", borderRadius: 4, fontSize: 12, textDecoration: "none", display: "inline-block",{margin_style} }}}}',
                '                  >',
                '                    View',
                '                  </Link>',
            ])
        if has_subcollections:
            margin_style = " marginRight: 8," if (can_edit or can_delete) else ""
            lines.extend([
                '                  <button',
                '                    onClick={(e) => {',
                '                      e.stopPropagation();',
                '                      setSelectedId(selectedId === (item as any).id ? null : (item as any).id);',
                '                    }}',
                f'                    style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: selectedId === (item as any).id ? "#2563eb" : "#fff", color: selectedId === (item as any).id ? "#fff" : "#334155", borderRadius: 4, fontSize: 12, cursor: "pointer",{margin_style} }}}}',
                '                  >',
                '                    {selectedId === (item as any).id ? "Hide Details" : "View Details"}',
                '                  </button>',
            ])
        if can_edit and form_screen:
            margin_style = " marginRight: 8," if can_delete else ""
            lines.extend([
                '                  <Link',
                f"                    href={{`/{form_screen.id}?id=${{(item as any).id}}`}}",
                '                    onClick={(e) => e.stopPropagation()}',
                f'                    style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: "#fff", color: "#2563eb", borderRadius: 4, fontSize: 12, textDecoration: "none", display: "inline-block",{margin_style} }}}}',
                '                  >',
                '                    Edit',
                '                  </Link>',
            ])
        if can_delete:
            lines.append('                  <button onClick={(e) => { e.stopPropagation(); handleDelete((item as any).id); }} style={{ padding: "4px 8px", border: "1px solid #fecaca", background: "#fff", color: "#dc2626", borderRadius: 4, fontSize: 12, cursor: "pointer" }}>Delete</button>')
        lines.append('                </td>')

    lines.extend([
        "              </tr>",
        "            ))}",
        "          </tbody>",
        "        </table>",
        "      </div>",
        "",
        '      <footer style={{ marginTop: 20, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>',
        '        <span style={{ fontSize: 14, color: "#64748b" }}>',
        '          Page {page} of {totalPages} ({total} total)',
        "        </span>",
        '        <nav aria-label="Pagination" style={{ display: "flex", alignItems: "center", gap: 12 }}>',
        '          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>',
        '            <label htmlFor="pageSizeSelect" style={{ fontSize: 13, color: "#64748b" }}>',
        "              Per page:",
        "            </label>",
        "            <select",
        '              id="pageSizeSelect"',
        '              aria-label="Select page size"',
        "              value={pageSize}",
        "              onChange={(e) => setPageSize(Number(e.target.value))}",
        '              style={{ padding: "4px 8px", border: "1px solid #cbd5e1", borderRadius: 6, background: "#fff", fontSize: 13, color: "#334155", cursor: "pointer" }}',
        "            >",
        '              <option value={10}>10 per page</option>',
        '              <option value={25}>25 per page</option>',
        '              <option value={50}>50 per page</option>',
        '              <option value={100}>100 per page</option>',
        "            </select>",
        "          </div>",
        '          <div style={{ display: "flex", gap: 8 }}>',
        "            <button",
        "              onClick={() => setPage(page - 1)}",
        "              disabled={page <= 1 || loading}",
        '              aria-label="Previous page"',
        '              style={{ padding: "6px 12px", border: "1px solid #cbd5e1", borderRadius: 6, background: page <= 1 ? "#f1f5f9" : "#fff", color: page <= 1 ? "#94a3b8" : "#0f172a", fontSize: 14, cursor: page <= 1 ? "default" : "pointer" }}',
        "            >",
        "              Previous",
        "            </button>",
        "            <button",
        "              onClick={() => setPage(page + 1)}",
        "              disabled={page >= totalPages || loading}",
        '              aria-label="Next page"',
        '              style={{ padding: "6px 12px", border: "1px solid #cbd5e1", borderRadius: 6, background: page >= totalPages ? "#f1f5f9" : "#fff", color: page >= totalPages ? "#94a3b8" : "#0f172a", fontSize: 14, cursor: page >= totalPages ? "default" : "pointer" }}',
        "            >",
        "              Next",
        "            </button>",
        "          </div>",
        "        </nav>",
        "      </footer>",
    ])

    if has_subcollections:
        sub_labels = ", ".join(sub.child_plural for sub in subcollections)
        lines.extend([
            "",
            '      <section style={{ marginTop: 24, border: "1px solid #e2e8f0", borderRadius: 8, background: "#fff", padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>',
            "        {!selectedId ? (",
            '          <div style={{ textAlign: "center", padding: "20px 16px", color: "#64748b" }}>',
            f'            <p style={{{{ margin: 0, fontSize: 14 }}}}>Select a {name} from the table above to view associated {sub_labels}.</p>',
            "          </div>",
            "        ) : (",
            "          <div>",
            '            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, paddingBottom: 12, borderBottom: "1px solid #e2e8f0", flexWrap: "wrap", gap: 8 }}>',
            "              <div>",
            '                <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>',
            f"                  Selected {name}",
            "                </span>",
            '                <h3 style={{ margin: "2px 0 0 0", fontSize: 18, fontWeight: 700, color: "#0f172a" }}>',
            f"                  {{selectedItem ? String((selectedItem as any).{best_title_f} ?? selectedId) : selectedId}}",
            "                </h3>",
            "              </div>",
            "              <button",
            "                onClick={() => setSelectedId(null)}",
            '                style={{ padding: "4px 10px", border: "1px solid #cbd5e1", background: "#f8fafc", color: "#475569", borderRadius: 4, fontSize: 12, cursor: "pointer" }}',
            "              >",
            "                Deselect",
            "              </button>",
            "            </div>",
        ])

        if len(subcollections) > 1:
            lines.append('            <div style={{ display: "flex", gap: 8, marginBottom: 16, borderBottom: "1px solid #e2e8f0", paddingBottom: 8 }}>')
            for idx, sub in enumerate(subcollections):
                s_var = f"{sub.child_entity.name.lower()}sSubcol"
                lines.extend([
                    "              <button",
                    f"                onClick={{() => setActiveTab({idx})}}",
                    "                style={{",
                    '                  padding: "6px 12px",',
                    '                  border: "none",',
                    f'                  background: activeTab === {idx} ? "#2563eb" : "#f1f5f9",',
                    f'                  color: activeTab === {idx} ? "#fff" : "#475569",',
                    '                  borderRadius: 6,',
                    '                  fontSize: 13,',
                    '                  fontWeight: 500,',
                    '                  cursor: "pointer",',
                    '                  display: "flex",',
                    '                  alignItems: "center",',
                    '                  gap: 6,',
                    "                }}",
                    "              >",
                    f"                <span>{sub.child_plural}</span>",
                    f'                <span style={{{{ padding: "2px 6px", background: activeTab === {idx} ? "rgba(255,255,255,0.2)" : "#e2e8f0", color: activeTab === {idx} ? "#fff" : "#475569", borderRadius: 10, fontSize: 11, fontWeight: 600 }}}}>',
                    f"                  {{{s_var}.total}}",
                    "                </span>",
                    "              </button>",
                ])
            lines.append("            </div>")

        for idx, sub in enumerate(subcollections):
            s_var = f"{sub.child_entity.name.lower()}sSubcol"
            tab_guard = f"activeTab === {idx}" if len(subcollections) > 1 else "true"
            child_form = next(
                (s for s in ir.screens if _screen_intent(s) == "form" and (_match_entity(s, ir) and _match_entity(s, ir).name == sub.child_entity.name)),
                None,
            )
            lines.extend([
                f"            {{{tab_guard} && (",
                "              <div>",
                '                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>',
                '                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>',
                f'                    <h4 style={{{{ margin: 0, fontSize: 16, fontWeight: 600, color: "#1e293b" }}}}>{sub.child_plural}</h4>',
                f'                    <span style={{{{ padding: "2px 8px", background: "#e0e7ff", color: "#3730a3", borderRadius: 12, fontSize: 12, fontWeight: 600 }}}}>',
                f"                      {{{s_var}.total}}",
                "                    </span>",
                "                  </div>",
            ])
            if child_form:
                lines.extend([
                    '                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>',
                    '                    <Link',
                    f"                      href={{`/{child_form.id}?{sub.id_param}=${{selectedId}}`}}",
                    '                      style={{ padding: "4px 8px", background: "#2563eb", color: "#fff", borderRadius: 4, fontSize: 12, textDecoration: "none", fontWeight: 500 }}',
                    '                    >',
                    f'                      + New {sub.child_entity.name}',
                    '                    </Link>',
                    "                    <button",
                    f"                      onClick={{() => {s_var}.refetch()}}",
                    f"                      disabled={{{s_var}.loading}}",
                    f'                      style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 4, fontSize: 12, cursor: {s_var}.loading ? "default" : "pointer" }}}}',
                    "                    >",
                    f'                      {{{s_var}.loading ? "Loading..." : "Refresh"}}',
                    "                    </button>",
                    "                  </div>",
                    "                </div>",
                ])
            else:
                lines.extend([
                    "                  <button",
                    f"                    onClick={{() => {s_var}.refetch()}}",
                    f"                    disabled={{{s_var}.loading}}",
                    f'                    style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 4, fontSize: 12, cursor: {s_var}.loading ? "default" : "pointer" }}}}',
                    "                  >",
                    f'                    {{{s_var}.loading ? "Loading..." : "Refresh"}}',
                    "                  </button>",
                    "                </div>",
                ])
            lines.extend([
                f"                {{{s_var}.loading && !{s_var}.data && (",
                '                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>',
                "                    {[0, 1, 2].map((i) => (",
                '                      <div key={i} style={{ height: 44, background: "#f1f5f9", borderRadius: 6, opacity: 1 - i * 0.2 }} />',
                "                    ))}",
                "                  </div>",
                "                )}",
                f"                {{{s_var}.error && (",
                f'                  <div role="alert" aria-live="assertive" style={{{{ padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#991b1b", fontSize: 13, marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}}}>',
                f"                    <span>Error: {{{s_var}.error.message}}</span>",
                f'                    <button onClick={{() => {s_var}.refetch()}} style={{{{ padding: "2px 8px", background: "#991b1b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}}}>Retry</button>',
                "                  </div>",
                "                )}",
            ])
            if sub.can_delete:
                c_name = sub.child_entity.name
                lines.extend([
                    f"                {{delete{c_name}Error && (",
                    f'                  <div role="alert" aria-live="assertive" style={{{{ padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#991b1b", fontSize: 13, marginBottom: 12 }}}}>Error deleting {c_name.lower()}: {{delete{c_name}Error.message}}</div>',
                    "                )}",
                ])
            lines.extend(_subcol_controls(sub, s_var))
            lines.extend(_subcol_filtered_empty(sub, s_var))
            empty_guard = f"{s_var}.data && {s_var}.data.length === 0"
            if _filterable_fields_for_entity(sub.child_entity):
                empty_guard += f" && Object.keys({s_var}.params.filters ?? {{}}).length === 0"
            lines.extend([
                f"                {{{empty_guard} && (",
            ])
            if child_form:
                lines.extend([
                    '                  <div style={{ padding: 24, textAlign: "center", color: "#64748b", fontSize: 14, background: "#f8fafc", borderRadius: 6, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>',
                    f'                    <div role="status">No {sub.child_plural.lower()} found for this {name.lower()}.</div>',
                    '                    <Link',
                    f"                      href={{`/{child_form.id}?{sub.id_param}=${{selectedId}}`}}",
                    '                      style={{ display: "inline-block", padding: "6px 12px", background: "#2563eb", color: "#fff", borderRadius: 4, fontSize: 12, textDecoration: "none", fontWeight: 500 }}',
                    '                    >',
                    f"                      + Add first {sub.child_entity.name}",
                    '                    </Link>',
                    '                  </div>',
                ])
            else:
                lines.append(
                    f'                  <div role="status" style={{{{ padding: 16, textAlign: "center", color: "#64748b", fontSize: 14, background: "#f8fafc", borderRadius: 6 }}}}>No {sub.child_plural.lower()} found for this {name.lower()}.</div>'
                )
            lines.append("                )}")
            # R-291: deletable subcollections render the optimistic-delete-filtered child list.
            _child_map_src = (
                f"({s_var}.data ?? []).filter((child: any) => !{_subcol_delete_names(s_var)[0]}.includes(String((child as any).id)))"
                if sub.can_delete else f"{s_var}.data"
            )
            lines.extend([
                f"                {{{s_var}.data && {s_var}.data.length > 0 && (",
                '                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>',
                f"                    {{{_child_map_src}.map((child, cIdx) => (",
            ])
            if sub.can_delete:
                h_name = _col_del_handler_name(sub)
                c_name = sub.child_entity.name
                lines.extend([
                    '                      <div key={(child as any).id ?? cIdx} style={{ padding: 12, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>',
                    '                        <div style={{ flex: 1 }}>',
                ])
                for df in sub.display_fields:
                    df_label = _title_case(df.name)
                    df_val = _field_value_jsx(df, f"(child as any).{df.name}")
                    lines.append(
                        f'                          <div style={{{{ color: "#334155" }}}}><strong>{df_label}:</strong> {df_val}</div>'
                    )
                lines.extend([
                    '                        </div>',
                    '                        <button',
                    f'                          onClick={{(e) => {{ e.stopPropagation(); {h_name}((child as any).id); }}}}',
                    f'                          disabled={{deleting{c_name}}}',
                    f'                          style={{{{ padding: "4px 8px", background: "#fee2e2", color: "#b91c1c", border: "1px solid #fca5a5", borderRadius: 4, fontSize: 12, fontWeight: 500, cursor: deleting{c_name} ? "default" : "pointer" }}}}',
                    '                        >',
                    f'                          {{deleting{c_name} ? "Deleting..." : "Delete"}}',
                    '                        </button>',
                    '                      </div>',
                ])
            else:
                lines.append(
                    '                      <div key={(child as any).id ?? cIdx} style={{ padding: 12, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14 }}>'
                )
                for df in sub.display_fields:
                    df_label = _title_case(df.name)
                    df_val = _field_value_jsx(df, f"(child as any).{df.name}")
                    lines.append(
                        f'                        <div style={{{{ color: "#334155" }}}}><strong>{df_label}:</strong> {df_val}</div>'
                    )
                lines.append('                      </div>')
            lines.extend([
                "                    ))}",
                "                  </div>",
                "                )}",
            ])
            lines.extend(_subcol_pagination(s_var))
            lines.extend([
                "              </div>",
                "            )}",
            ])

        lines.extend([
            "          </div>",
            "        )}",
            "      </section>",
        ])

    if uses_confirm:
        lines.extend([
            "      {/* R-304: accessible modal confirmation dialog */}",
            "      <ConfirmDialog {...confirmProps} />",
        ])

    lines.extend([
        "    </main>",
        "  );",
        "}",
        "",
    ])

    return "\n".join(lines)


def _form_screen_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op]) -> str:  # noqa: PLR0912
    name = entity.name
    plural = name if name.endswith("s") else f"{name}s"
    page_name = f"{_pascal(screen.id)}Page"
    title = _title_case(screen.id)

    # Check for complementary list and detail screens in ir.screens
    list_screen: Screen | None = None
    detail_screen: Screen | None = None
    for s in ir.screens:
        if s.id != screen.id:
            s_entity = _match_entity(s, ir)
            if s_entity and s_entity.name == entity.name:
                intent = _screen_intent(s)
                if intent == "collection" and list_screen is None:
                    list_screen = s
                elif intent == "detail" and detail_screen is None:
                    detail_screen = s

    # Fields to include in form
    editable_fields = [f for f in entity.fields if f.name not in ("id", "created_at", "updated_at")]
    if not editable_fields:
        editable_fields = list(entity.fields)

    parent_relations = _parent_relations_for_entity(entity, ir)
    parent_rel_by_field: dict[str, ParentRelationInfo] = {r.field_name: r for r in parent_relations}

    # Ensure any parent relation foreign key not yet in editable_fields is appended
    existing_field_names = {f.name for f in entity.fields}
    for r in parent_relations:
        if r.field_name not in existing_field_names:
            editable_fields.append(Field(name=r.field_name, type=FieldType.UUID, required=True))

    # Build initial form state dict
    defaults: list[str] = []
    for f in editable_fields:
        if f.type == FieldType.BOOL:
            defaults.append(f"{f.name}: false")
        elif f.type in (FieldType.INT, FieldType.FLOAT):
            defaults.append(f"{f.name}: undefined")
        else:
            defaults.append(f'{f.name}: ""')
    initial_obj = "{" + ", ".join(defaults) + "}"

    can_create = Op.CREATE in ops
    can_update = Op.UPDATE in ops
    has_get = Op.GET in ops

    fk_fields = [f.name for f in entity.fields if f.name.endswith("_id")]
    for rel in getattr(entity, "relations", ()):
        fk_fields.append(f"{rel.name}_id")
        fk_fields.append(f"{rel.name}Id")
    uses_search_params = can_update or bool(fk_fields) or bool(parent_relations)

    lines: list[str] = [
        '"use client";',
        "",
        'import { useEffect, useMemo, useState } from "react";',
    ]
    if uses_search_params:
        lines.append('import { useSearchParams } from "next/navigation";')

    lines.append('import Link from "next/link";')
    lines.append('import { useToast } from "../components/toast";')
    lines.append('import { Breadcrumbs } from "../components/breadcrumbs";')
    imported_hooks: set[str] = set()
    if can_create:
        imported_hooks.add(f"useCreate{name}")
        lines.append(f'import {{ useCreate{name} }} from "../lib/hooks";')
    if can_update:
        update_hooks = []
        if has_get:
            update_hooks.append(f"use{name}")
            imported_hooks.add(f"use{name}")
        update_hooks.append(f"useUpdate{name}")
        imported_hooks.add(f"useUpdate{name}")
        lines.append(f'import {{ {", ".join(update_hooks)} }} from "../lib/hooks";')

    parent_hooks = sorted({r.hook_name for r in parent_relations if r.hook_name not in imported_hooks})
    if parent_hooks:
        lines.append(f'import {{ {", ".join(parent_hooks)} }} from "../lib/hooks";')

    lines.extend([
        'import { extractFieldErrors } from "../lib/api";',
        'import { useConfirm, ConfirmDialog } from "../components/confirm-dialog";',
        f'import type {{ {name} }} from "../lib/types";',
        "",
        f"export default function {page_name}() {{",
        "  const { toast } = useToast();",
        "  const { confirmAsync, confirmProps } = useConfirm();",
    ])

    if can_create:
        lines.append(f"  const {{ create, loading: submitting, error: submitError, reset }} = useCreate{name}();")
    else:
        lines.append("  const submitting = false, submitError = null, reset = () => {};")

    # Parent list hooks for relation dropdowns
    unique_parents: dict[str, tuple[str, str]] = {}
    for r in parent_relations:
        if r.parent_entity.name not in unique_parents:
            unique_parents[r.parent_entity.name] = (
                r.hook_name,
                r.parent_plural[:1].lower() + r.parent_plural[1:] + "List",
            )
    for hook_name, list_var in unique_parents.values():
        lines.append(f"  const {list_var} = {hook_name}();")

    if can_update:
        lines.extend([
            f"  const {{ update, loading: updating, error: updateError }} = useUpdate{name}();",
            "  const searchParams = useSearchParams();",
            '  const editId = searchParams.get("id");',
            "  const isEdit = Boolean(editId);",
        ])
        if has_get:
            lines.append(f"  const {{ data: initialData, loading: fetchingInitial }} = use{name}(editId);")
    elif uses_search_params:
        lines.extend([
            "  const searchParams = useSearchParams();",
            "  const isEdit = false;",
            "  const editId = null;",
        ])

    breadcrumbs_items = [
        '    { label: "Overview", href: "/" },',
    ]
    if list_screen:
        breadcrumbs_items.append(f'    {{ label: "{plural}", href: "/{list_screen.id}" }},')
    if can_update:
        breadcrumbs_items.append(f'    {{ label: isEdit ? "Edit {name}" : "New {name}" }},')
    else:
        breadcrumbs_items.append(f'    {{ label: "New {name}" }},')

    initial_values_expr = f"const initialValues: Partial<{name}> = {initial_obj};"
    lines.extend([
        f"  {initial_values_expr}",
        f"  const [formData, setFormData] = useState<Partial<{name}>>(initialValues);",
        '  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});',
        "  const [success, setSuccess] = useState(false);",
        "  const [lastSavedId, setLastSavedId] = useState<string | null>(null);",
        "",
        "  const breadcrumbs = [",
        *breadcrumbs_items,
        "  ];",
        "",
    ])

    if can_update and has_get:
        lines.extend([
            "  const baselineData = useMemo(() => {",
            "    return (isEdit && initialData) ? initialData : initialValues;",
            "  }, [isEdit, initialData]);",
            "",
            "  useEffect(() => {",
            "    if (initialData) {",
            "      setFormData(initialData);",
            "    }",
            "  }, [initialData]);",
            "",
        ])
    else:
        lines.extend([
            "  const baselineData = initialValues;",
            "",
        ])

    lines.extend([
        "  const isDirty = useMemo(() => {",
        "    return Object.keys(formData).some((key) => {",
        "      const cur = (formData as any)[key];",
        "      const base = (baselineData as any)[key];",
        '      if (cur === undefined && (base === undefined || base === "")) return false;',
        '      if (cur === "" && (base === undefined || base === "")) return false;',
        "      return cur !== base;",
        "    });",
        "  }, [formData, baselineData]);",
        "",
        "  useEffect(() => {",
        "    const handleBeforeUnload = (e: BeforeUnloadEvent) => {",
        "      if (isDirty && !submitting && !success) {",
        "        e.preventDefault();",
        '        e.returnValue = "";',
        "      }",
        "    };",
        '    window.addEventListener("beforeunload", handleBeforeUnload);',
        '    return () => window.removeEventListener("beforeunload", handleBeforeUnload);',
        "  }, [isDirty, submitting, success]);",
        "",
    ])

    cancel_href = f"/{list_screen.id}" if list_screen else "/"
    if can_create and can_update:
        submitting_guard = "!(submitting || updating)"
        submitting_deps = "submitting, updating"
    elif can_update:
        submitting_guard = "!updating"
        submitting_deps = "updating"
    else:
        submitting_guard = "!submitting"
        submitting_deps = "submitting"

    lines.extend([
        "  useEffect(() => {",
        "    const handleKeyDown = (e: KeyboardEvent) => {",
        '      if ((e.metaKey || e.ctrlKey) && (e.key === "Enter" || e.key === "s" || e.key === "S")) {',
        "        e.preventDefault();",
        f"        if ({submitting_guard}) {{",
        '          const form = document.querySelector("form");',
        "          if (form) {",
        '            form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));',
        "          }",
        "        }",
        '      } else if (e.key === "Escape") {',
        "        const active = document.activeElement as HTMLElement | null;",
        '        if (active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) {',
        "          active.blur();",
        "          return;",
        "        }",
        "        if (!isDirty) {",
        f'          window.location.href = "{cancel_href}";',
        "        } else {",
        '          confirmAsync("Discard Changes", "You have unsaved changes. Discard them and leave?").then((ok) => {',
        "            if (ok) {",
        f'              window.location.href = "{cancel_href}";',
        "            }",
        "          });",
        "        }",
        "      }",
        "    };",
        '    window.addEventListener("keydown", handleKeyDown);',
        '    return () => window.removeEventListener("keydown", handleKeyDown);',
        f"  }}, [isDirty, {submitting_deps}]);",
        "",
    ])


    if uses_search_params:
        lines.extend([
            "  useEffect(() => {",
            "    if (!isEdit) {",
            "      const updates: Record<string, any> = {};",
            "      searchParams.forEach((val, key) => {",
            "        if (val) updates[key] = val;",
            "      });",
        ])
        for r in parent_relations:
            base = r.relation_name
            aliases = [f'"{r.field_name}"', f'"{base}_id"', f'"{base}Id"', f'"{base}"']
            seen_a: set[str] = set()
            unique_aliases = [a for a in aliases if not (a in seen_a or seen_a.add(a))]
            expr = " || ".join(f"searchParams.get({a})" for a in unique_aliases)
            lines.extend([
                f'      const {base}Param = {expr};',
                f'      if ({base}Param && !updates["{r.field_name}"]) {{',
                f'        updates["{r.field_name}"] = {base}Param;',
                '      }',
            ])
        lines.extend([
            "      if (Object.keys(updates).length > 0) {",
            "        setFormData((prev) => ({ ...prev, ...updates }));",
            "      }",
            "    }",
            "  }, [searchParams, isEdit]);",
            "",
        ])

    lines.extend([
        "  const handleSubmit = async (e: React.FormEvent) => {",
        "    e.preventDefault();",
        "    setSuccess(false);",
        "",
        "    const clientErrors: Record<string, string> = {};",
    ])

    for f in editable_fields:
        rules = parse_field_rules(f)
        rel = parent_rel_by_field.get(f.name)
        flabel = _title_case(rel.relation_name) if rel else _title_case(f.name)
        val_access = f"(formData as any).{f.name}"
        if f.required:
            if f.type in (FieldType.STRING, FieldType.TEXT):
                lines.extend([
                    f"    if (!{val_access} || !String({val_access}).trim()) {{",
                    f'      clientErrors.{f.name} = "{flabel} is required";',
                    "    }",
                ])
            elif f.type in (FieldType.INT, FieldType.FLOAT):
                lines.extend([
                    f"    if ({val_access} === undefined || {val_access} === null || isNaN(Number({val_access}))) {{",
                    f'      clientErrors.{f.name} = "{flabel} is required";',
                    "    }",
                ])
            elif f.type == FieldType.DATETIME:
                lines.extend([
                    f"    if (!{val_access}) {{",
                    f'      clientErrors.{f.name} = "{flabel} is required";',
                    "    }",
                ])
            else:
                lines.extend([
                    f"    if (!{val_access} || !String({val_access}).trim()) {{",
                    f'      clientErrors.{f.name} = "{flabel} is required";',
                    "    }",
                ])
        if rules.max_length and f.type in (FieldType.STRING, FieldType.TEXT):
            lines.extend([
                f"    if ({val_access} && String({val_access}).length > {rules.max_length}) {{",
                f'      clientErrors.{f.name} = "{flabel} must not exceed {rules.max_length} characters";',
                "    }",
            ])
        if rules.minimum and f.type in (FieldType.INT, FieldType.FLOAT):
            lines.extend([
                f"    if ({val_access} !== undefined && Number({val_access}) < {rules.minimum}) {{",
                f'      clientErrors.{f.name} = "{flabel} must be at least {rules.minimum}";',
                "    }",
            ])
        if rules.maximum and f.type in (FieldType.INT, FieldType.FLOAT):
            lines.extend([
                f"    if ({val_access} !== undefined && Number({val_access}) > {rules.maximum}) {{",
                f'      clientErrors.{f.name} = "{flabel} must be at most {rules.maximum}";',
                "    }",
            ])
        if rules.enum and f.type in (FieldType.STRING, FieldType.TEXT):
            opts_json = json.dumps(list(rules.enum))
            enum_str = ", ".join(rules.enum)
            lines.extend([
                f"    if ({val_access} && !{opts_json}.includes(String({val_access}))) {{",
                f'      clientErrors.{f.name} = "{flabel} must be one of: {enum_str}";',
                "    }",
            ])

    lines.extend([
        "    if (Object.keys(clientErrors).length > 0) {",
        "      setFieldErrors(clientErrors);",
        "      return;",
        "    }",
        "",
        "    setFieldErrors({});",
        "    try {",
    ])
    if can_create and can_update:
        lines.extend([
            "      if (isEdit && editId) {",
            "        await update(editId, formData);",
            "        setLastSavedId(editId);",
            "      } else {",
            "        const res = await create(formData);",
            "        if (res && (res as any).id) {",
            "          setLastSavedId(String((res as any).id));",
            "        }",
            f"        setFormData({initial_obj});",
            "      }",
        ])
    elif can_update:
        lines.extend([
            "      if (editId) {",
            "        await update(editId, formData);",
            "        setLastSavedId(editId);",
            "      }",
        ])
    else:
        lines.extend([
            "      const res = await create(formData);",
            "      if (res && (res as any).id) {",
            "        setLastSavedId(String((res as any).id));",
            "      }",
            f"      setFormData({initial_obj});",
        ])
    lines.extend([
        "      setSuccess(true);",
    ])
    if can_update:
        lines.append(f'      toast.success(isEdit ? "{name} updated successfully" : "{name} created successfully");')
    else:
        lines.append(f'      toast.success("{name} created successfully");')
    lines.extend([
        "    } catch (err) {",
        "      const serverErrors = extractFieldErrors(err);",
        "      if (Object.keys(serverErrors).length > 0) {",
        "        setFieldErrors(serverErrors);",
        "      }",
    ])
    if can_update:
        lines.append(f'      toast.error(err instanceof Error ? err.message : (isEdit ? "Failed to update {name}" : "Failed to create {name}"));')
    else:
        lines.append(f'      toast.error(err instanceof Error ? err.message : "Failed to create {name}");')
    lines.extend([
        "    }",
        "  };",
        "",
        "  return (",
        '    <main style={{ maxWidth: 640, margin: "0 auto", padding: "32px 16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>',
        "      <Breadcrumbs items={breadcrumbs} />",
        '      <header style={{ marginBottom: 24 }}>',
        '        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>',
    ])

    if list_screen:
        lines.append(
            f'          <Link href="/{list_screen.id}" style={{{{ color: "#2563eb", textDecoration: "none", fontSize: 13, fontWeight: 500 }}}}>&larr; Back to {plural}</Link>'
        )
    else:
        lines.append(
            '          <Link href="/" style={{ color: "#2563eb", textDecoration: "none", fontSize: 13, fontWeight: 500 }}>&larr; Overview</Link>'
        )

    lines.extend([
        '          <span style={{ color: "#94a3b8" }}>/</span>',
        f'          <span style={{ fontSize: 12, padding: "2px 8px", background: "#f1f5f9", color: "#475569", borderRadius: 4, fontWeight: 600 }}>{screen.role}</span>',
        "        </div>",
        '        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>',
    ])
    if can_update:
        lines.append(f'          <h1 style={{{{ margin: 0, fontSize: 26, fontWeight: 700, color: "#0f172a" }}}}>{{isEdit ? "Edit {name}" : "{title}"}}</h1>')
    else:
        lines.append(f'          <h1 style={{{{ margin: 0, fontSize: 26, fontWeight: 700, color: "#0f172a" }}}}>{title}</h1>')
    lines.extend([
        "          {isDirty && !success && (",
        '            <span style={{ fontSize: 12, padding: "3px 8px", background: "#fef3c7", color: "#92400e", borderRadius: 4, fontWeight: 600 }}>',
        "              Unsaved changes",
        "            </span>",
        "          )}",
        "        </div>",
        "      </header>",
        "",
    ])

    # Build contextual actions for success banner
    success_actions_jsx: list[str] = []
    if detail_screen:
        id_expr = "lastSavedId || (isEdit ? editId : null)" if can_update else "lastSavedId"
        success_actions_jsx.append(
            f'          {{{id_expr} && (\n'
            f'            <Link\n'
            f'              href={{`/{detail_screen.id}?id=${{{id_expr}}}`}}\n'
            '              style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "5px 12px", background: "#166534", color: "#ffffff", borderRadius: 6, fontSize: 13, fontWeight: 500, textDecoration: "none" }}\n'
            '            >\n'
            f'              View {name} &rarr;\n'
            '            </Link>\n'
            '          )}}'
        )
    if list_screen:
        success_actions_jsx.append(
            f'          <Link\n'
            f'            href="/{list_screen.id}"\n'
            '            style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "5px 12px", background: "#ffffff", border: "1px solid #bbf7d0", color: "#166534", borderRadius: 6, fontSize: 13, fontWeight: 500, textDecoration: "none" }}\n'
            '          >\n'
            f'            &larr; Back to {plural}\n'
            '          </Link>'
        )
    if can_create and can_update:
        success_actions_jsx.append(
            '          {!isEdit && (\n'
            '            <button\n'
            '              type="button"\n'
            '              onClick={() => { setSuccess(false); setLastSavedId(null); }}\n'
            '              style={{ padding: "5px 12px", background: "#ffffff", border: "1px solid #bbf7d0", color: "#166534", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: "pointer" }}\n'
            '            >\n'
            f'              + Create another {name}\n'
            '            </button>\n'
            '          )}'
        )
    elif can_create:
        success_actions_jsx.append(
            '          <button\n'
            '            type="button"\n'
            '            onClick={() => { setSuccess(false); setLastSavedId(null); }}\n'
            '            style={{ padding: "5px 12px", background: "#ffffff", border: "1px solid #bbf7d0", color: "#166534", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: "pointer" }}\n'
            '            >\n'
            f'            + Create another {name}\n'
            '          </button>'
        )

    actions_block = ""
    if success_actions_jsx:
        actions_block = (
            '\n          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, flexWrap: "wrap" }}>\n'
            + "\n".join(success_actions_jsx)
            + "\n          </div>"
        )

    msg_jsx = f'{{isEdit ? "{name} updated successfully!" : "{name} saved successfully!"}}' if can_update else f'{name} saved successfully!'

    lines.extend([
        "      {success && (",
        '        <div style={{ padding: "14px 18px", background: "#f0fdf4", border: "1px solid #bbf7d0", color: "#166534", borderRadius: 8, marginBottom: 20 }}>',
        '          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>',
        f'            <span>{msg_jsx}</span>',
        '            <button',
        '              type="button"',
        '              onClick={() => setSuccess(false)}',
        '              style={{ background: "transparent", border: "none", color: "#166534", cursor: "pointer", fontSize: 18, lineHeight: 1, padding: "0 4px" }}',
        '              aria-label="Dismiss"',
        '            >',
        '              &times;',
        '            </button>',
        '          </div>' + actions_block,
        "        </div>",
        "      )}",
    ])

    if can_update:
        lines.extend([
            "      {(submitError || (isEdit && updateError)) && Object.keys(fieldErrors).length === 0 && (",
            '        <div role="alert" aria-live="assertive" style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", borderRadius: 8, marginBottom: 20 }}>',
            "          Error: {((isEdit ? updateError : submitError) || submitError)?.message}",
            "        </div>",
            "      )}",
        ])
    else:
        lines.extend([
            "      {submitError && Object.keys(fieldErrors).length === 0 && (",
            '        <div role="alert" aria-live="assertive" style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", borderRadius: 8, marginBottom: 20 }}>',
            "          Error: {submitError.message}",
            "        </div>",
            "      )}",
        ])

    if can_update and has_get:
        lines.extend([
            "      {isEdit && fetchingInitial && (",
            '        <div style={{ padding: "12px 16px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, marginBottom: 20, display: "flex", flexDirection: "column", gap: 12 }}>',
            "          {/* R-293: loading skeleton for the edit-mode initial fetch */}",
            "          {[0, 1, 2].map((i) => (",
            '            <div key={i} style={{ height: 34, background: "#e2e8f0", borderRadius: 6, opacity: 1 - i * 0.2 }} />',
            "          ))}",
            "        </div>",
            "      )}",
        ])

    lines.extend([
        "      {Object.keys(fieldErrors).length > 0 && (",
        '        <div style={{ padding: "12px 16px", background: "#fff7ed", border: "1px solid #fed7aa", color: "#9a3412", borderRadius: 8, marginBottom: 20, fontSize: 14 }}>',
        "          Please correct the highlighted errors below before submitting.",
        "        </div>",
        "      )}",
        "",
        "      <form",
        "        onSubmit={handleSubmit}",
        '        style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}',
        "      >",
    ])

    for idx, f in enumerate(editable_fields):
        label = _title_case(f.name)
        rules = parse_field_rules(f)
        req_star = ' <span style={{ color: "#dc2626" }}>*</span>' if f.required else ""
        req_attr = " required" if f.required else ""
        autofocus_attr = " autoFocus" if idx == 0 else ""

        if f.name in parent_rel_by_field:
            rel = parent_rel_by_field[f.name]
            p_var = unique_parents[rel.parent_entity.name][1]
            p_name = rel.parent_entity.name
            p_title = rel.title_field
            rel_label = _title_case(rel.relation_name)
            loading_text = f"Loading {p_name.lower()}s..."
            select_text = f"Select {p_name.lower()}..."
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                f'          <label style={{{{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}}}>{rel_label}{req_star}</label>',
                '          <select',
                f'            value={{String((formData as any).{f.name} ?? "")}}',
                f'            onChange={{(e) => {{{{ setFormData((prev) => ({{{{ ...prev, {f.name}: e.target.value }}}})); if (fieldErrors.{f.name}) setFieldErrors((prev) => ({{{{ ...prev, {f.name}: "" }}}})); }}}}',
                f'            style={{{{ width: "100%", padding: "8px 12px", border: fieldErrors.{f.name} ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none", background: "#fff" }}}}',
                f'            aria-invalid={{!!fieldErrors.{f.name}}}' + req_attr + autofocus_attr,
                '          >',
                f'            <option value="">{{{p_var}.loading ? "{loading_text}" : "{select_text}"}}</option>',
                f'            {{({p_var}.data || []).map((item) => (',
                '              <option key={item.id} value={item.id}>',
                f'                {{String((item as any).{p_title} ?? (item as any).name ?? item.id)}}',
                '              </option>',
                '            ))}',
                '          </select>',
                f'          {{Boolean((formData as any).{f.name}) && (',
                f'            <span style={{{{ fontSize: 12, color: "#059669", marginTop: 4, display: "block", fontWeight: 500 }}}}>',
                f'              &bull; Selected {rel_label} linked',
                '            </span>',
                '          )}',
                f'          {{fieldErrors.{f.name} && <span style={{{{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}}}>{{fieldErrors.{f.name}}}</span>}}',
                '        </div>',
            ])
        elif f.type == FieldType.BOOL:
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14, fontWeight: 500, color: "#334155" }}>',
                '            <input',
                '              type="checkbox"',
                '              checked={Boolean((formData as any).' + f.name + ')}',
                '              onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.checked })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '              style={{ width: 16, height: 16, cursor: "pointer" }}',
                '              aria-invalid={!!fieldErrors.' + f.name + '}' + autofocus_attr,
                '            />',
                '            <span>' + label + '</span>',
                '          </label>',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
                '        </div>',
            ])
        elif f.type == FieldType.TEXT:
            max_attr = f" maxLength={{{rules.max_length}}}" if rules.max_length else ""
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <textarea',
                '            rows={4}',
                '            value={String((formData as any).' + f.name + ' ?? "")}',
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '            placeholder="Enter ' + label.lower() + '..."' + req_attr + max_attr + autofocus_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          />',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
            ])
            if rules.max_length:
                amber_threshold = int(rules.max_length * 0.9)
                lines.extend([
                    '          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>',
                    '            <span style={{ fontSize: 12, color: "#94a3b8" }}>Max ' + str(rules.max_length) + ' characters</span>',
                    '            <span style={{ fontSize: 12, color: String((formData as any).' + f.name + ' ?? "").length >= ' + str(amber_threshold) + ' ? "#b45309" : "#94a3b8", marginLeft: "auto" }}>',
                    '              {String((formData as any).' + f.name + ' ?? "").length} / ' + str(rules.max_length),
                    '            </span>',
                    '          </div>',
                ])
            lines.append('        </div>')
        elif f.type in (FieldType.INT, FieldType.FLOAT):
            step = "any" if f.type == FieldType.FLOAT else "1"
            min_attr = f" min={{{rules.minimum}}}" if rules.minimum is not None else ""
            max_attr = f" max={{{rules.maximum}}}" if rules.maximum is not None else ""
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <input',
                '            type="number"',
                '            step="' + step + '"',
                '            value={(formData as any).' + f.name + ' !== undefined && (formData as any).' + f.name + ' !== null ? String((formData as any).' + f.name + ') : ""}',
                '            onChange={(e) => { const v = e.target.value; setFormData((prev) => ({ ...prev, ' + f.name + ': v === "" ? undefined : Number(v) })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '            placeholder="Enter ' + label.lower() + '..."' + req_attr + min_attr + max_attr + autofocus_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          />',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
            ])
            has_range = rules.minimum is not None or rules.maximum is not None
            if has_range:
                min_label = str(rules.minimum) if rules.minimum is not None else "-\u221e"
                max_label = str(rules.maximum) if rules.maximum is not None else "+\u221e"
                lines.extend([
                    '          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>',
                    '            <span style={{ fontSize: 12, color: "#94a3b8" }}>Range: ' + min_label + ' to ' + max_label + '</span>',
                    '          </div>',
                ])
            lines.append('        </div>')
        elif f.type == FieldType.DATETIME:
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <input',
                '            type="datetime-local"',
                '            value={String((formData as any).' + f.name + ' ?? "")}',
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}' + req_attr + autofocus_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          />',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
                '        </div>',
            ])
        elif rules.enum and f.type in (FieldType.STRING, FieldType.TEXT):
            opt_lines = "\n".join(
                f'            <option value="{opt}">{opt}</option>'
                for opt in rules.enum
            )
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <select',
                '            value={String((formData as any).' + f.name + ' ?? "")}',
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}' + req_attr + autofocus_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none", background: "#fff" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          >',
                '            <option value="">Select ' + label.lower() + '...</option>',
                opt_lines,
                '          </select>',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
                '        </div>',
            ])
        else:
            max_attr = f" maxLength={{{rules.max_length}}}" if rules.max_length else ""
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <input',
                '            type="text"',
                '            value={String((formData as any).' + f.name + ' ?? "")}',
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '            placeholder="Enter ' + label.lower() + '..."' + req_attr + max_attr + autofocus_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          />',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
            ])
            if rules.max_length:
                amber_threshold = int(rules.max_length * 0.9)
                lines.extend([
                    '          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>',
                    '            <span style={{ fontSize: 12, color: "#94a3b8" }}>Max ' + str(rules.max_length) + ' characters</span>',
                    '            <span style={{ fontSize: 12, color: String((formData as any).' + f.name + ' ?? "").length >= ' + str(amber_threshold) + ' ? "#b45309" : "#94a3b8", marginLeft: "auto" }}>',
                    '              {String((formData as any).' + f.name + ' ?? "").length} / ' + str(rules.max_length),
                    '            </span>',
                    '          </div>',
                ])
            lines.append('        </div>')



    if can_create and can_update:
        submitting_expr = "(submitting || updating)"
        btn_label = f'({submitting_expr} ? "Saving..." : (isEdit ? "Update {name}" : "Save {name}"))'
    elif can_update:
        submitting_expr = "updating"
        btn_label = f'(updating ? "Saving..." : "Update {name}")'
    else:
        submitting_expr = "submitting"
        btn_label = f'(submitting ? "Saving..." : "Save {name}")'

    reset_call = f"setFormData(isEdit && initialData ? initialData : initialValues)" if (can_update and has_get) else "setFormData(initialValues)"
    cancel_href = f"/{list_screen.id}" if list_screen else "/"

    lines.extend([
        '        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", alignItems: "center", marginTop: 24, paddingTop: 16, borderTop: "1px solid #f1f5f9", flexWrap: "wrap" }}>',
        "          {isDirty && !success && (",
        '            <span style={{ fontSize: 12, color: "#b45309", marginRight: "auto", fontWeight: 500 }}>',
        "              &bull; You have unsaved changes",
        "            </span>",
        "          )}",
        '          <Link',
        f'            href="{cancel_href}"',
        '            onClick={async (e) => {',
        '              if (isDirty) {',
        '                e.preventDefault();',
        '                const ok = await confirmAsync("Discard Changes", "You have unsaved changes. Discard them and leave?");',
        '                if (ok) {',
        f'                  window.location.href = "{cancel_href}";',
        '                }',
        '              }',
        "            }}",
        '            style={{ padding: "8px 16px", border: "1px solid #cbd5e1", background: "#fff", color: "#475569", borderRadius: 6, fontSize: 14, textDecoration: "none", display: "inline-flex", alignItems: "center" }}',
        '          >',
        '            Cancel',
        '          </Link>',
        '          <button',
        '            type="button"',
        f'            onClick={{async () => {{ const ok = !isDirty || await confirmAsync("Reset Form", "Discard all changes and reset form?"); if (ok) {{ reset(); {reset_call}; setFieldErrors({{}}); setSuccess(false); setLastSavedId(null); toast.info("Form reset to original values"); }} }}}}',
        '            style={{ padding: "8px 16px", border: "1px solid #cbd5e1", background: "#fff", color: "#475569", borderRadius: 6, fontSize: 14, cursor: "pointer" }}',
        '          >',
        '            Reset',
        '          </button>',
        '          <button',
        '            type="submit"',
        f'            disabled={{{submitting_expr}}}',
        f'            style={{{{ padding: "8px 20px", background: {submitting_expr} ? "#93c5fd" : "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, fontWeight: 500, cursor: {submitting_expr} ? "default" : "pointer" }}}}',
        '          >',
        f'            {{{btn_label}}}',
        '          </button>',
        '        </div>',
        '      </form>',
        '      {/* R-304: accessible modal confirmation dialog */}',
        '      <ConfirmDialog {...confirmProps} />',
        '    </main>',
        '  );',
        '}',
        '',
    ])

    return "\n".join(lines)


def _detail_screen_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op]) -> str:  # noqa: PLR0912
    name = entity.name
    plural = name if name.endswith("s") else f"{name}s"
    page_name = f"{_pascal(screen.id)}Page"
    title = _title_case(screen.id)
    subcollections = _subcollections_for_parent(name, ir)
    has_subcollections = bool(subcollections)

    collection_screen: Screen | None = None
    form_screen: Screen | None = None
    for s in ir.screens:
        if s.id != screen.id:
            s_entity = _match_entity(s, ir)
            if s_entity and s_entity.name == entity.name:
                s_intent = _screen_intent(s)
                if s_intent == "collection" and not collection_screen:
                    collection_screen = s
                elif s_intent == "form" and not form_screen:
                    form_screen = s

    can_edit = (Op.UPDATE in ops) and (form_screen is not None)
    can_delete = Op.DELETE in ops
    can_list = Op.LIST in ops

    hooks_to_import: list[str] = []
    if Op.GET in ops:
        hooks_to_import.append(f"use{name}")
    if can_list:
        hooks_to_import.append(f"useList{plural}")
    if can_delete:
        hooks_to_import.append(f"useDelete{name}")

    uses_confirm_detail = can_delete or any(sub.can_delete for sub in subcollections)

    lines: list[str] = [
        '"use client";',
        "",
        'import { useState, useEffect } from "react";',
        'import { useSearchParams } from "next/navigation";',
        'import Link from "next/link";',
        'import { useToast } from "../components/toast";',
        'import { Breadcrumbs } from "../components/breadcrumbs";',
        *([
            'import { useConfirm, ConfirmDialog } from "../components/confirm-dialog";',
        ] if uses_confirm_detail else []),
    ]

    if hooks_to_import:
        lines.append(f'import {{ {", ".join(hooks_to_import)} }} from "../lib/hooks";')
    if has_subcollections:
        subcol_hook_names = [sub.hook_name for sub in subcollections]
        for sub in subcollections:
            if sub.can_delete:
                del_hook = f"useDelete{sub.child_entity.name}"
                if del_hook not in subcol_hook_names:
                    subcol_hook_names.append(del_hook)
        lines.append(f'import {{ {", ".join(subcol_hook_names)} }} from "../lib/hooks";')

    lines.append(f'import type {{ {name} }} from "../lib/types";')

    if has_subcollections:
        child_type_names = list(dict.fromkeys(sub.child_entity.name for sub in subcollections if sub.child_entity.name != name))
        if child_type_names:
            lines.append(f'import type {{ {", ".join(child_type_names)} }} from "../lib/types";')

    best_title_f = next((f.name for f in entity.fields if f.name in ("title", "name", "label", "email")), None)
    if not best_title_f:
        best_title_f = next((f.name for f in entity.fields if f.name != "id"), "id")

    lines.extend([
        "",
        f"export default function {page_name}() {{",
        "  const { toast } = useToast();",
        "  const searchParams = useSearchParams();",
        '  const queryId = searchParams.get("id");',
        '  const [idInput, setIdInput] = useState<string>(queryId ?? "");',
        "  const [selectedId, setSelectedId] = useState<string | null>(queryId ?? null);",
        "",
        "  const breadcrumbs = [",
        '    { label: "Overview", href: "/" },',
        *(
            [f'    {{ label: "{plural}", href: "/{collection_screen.id}" }},']
            if collection_screen
            else []
        ),
        f'    {{ label: selectedId ? `{name} #${{selectedId}}` : "{name} Details" }},',
        "  ];",
        "",
        "  useEffect(() => {",
        "    if (queryId) {",
        "      setSelectedId(queryId);",
        "      setIdInput(queryId);",
        "    }",
        "  }, [queryId]);",
        "",
        "  const handleSelectId = (newId: string | null) => {",
        "    setSelectedId(newId);",
        '    setIdInput(newId ?? "");',
        '    if (typeof window !== "undefined") {',
        "      const url = new URL(window.location.href);",
        "      if (newId) {",
        '        url.searchParams.set("id", newId);',
        "      } else {",
        '        url.searchParams.delete("id");',
        "      }",
        '      window.history.replaceState({}, "", url.toString());',
        "    }",
        "  };",
    ])

    if can_list:
        lines.extend([
            f"  const {{ data: listItems, loading: loadingList }} = useList{plural}();",
            "  const currentIndex = (listItems && selectedId)",
            "    ? listItems.findIndex((x: any) => String(x.id) === String(selectedId))",
            "    : -1;",
            "  const prevItem = (listItems && currentIndex > 0) ? listItems[currentIndex - 1] : null;",
            "  const nextItem = (listItems && currentIndex >= 0 && currentIndex < listItems.length - 1)",
            "    ? listItems[currentIndex + 1]",
            "    : null;",
        ])

    if Op.GET in ops:
        lines.append(f"  const {{ data: item, loading, error, refetch }} = use{name}(selectedId);")

    if can_delete:
        lines.extend([
            f"  const {{ remove: removeMain, loading: deletingMain, error: deleteMainError }} = useDelete{name}();",
            "  // R-304: accessible async confirmation dialog.",
            "  const { confirmAsync, confirmProps } = useConfirm();",
            "  const handleDelete = async () => {",
            "    if (!selectedId) return;",
            f'    const ok = await confirmAsync("Delete {name}", "Are you sure you want to delete this {name}? This action cannot be undone.");',
            "    if (!ok) return;",
            "    try {",
            "      await removeMain(selectedId);",
            "      setSelectedId(null);",
            '      setIdInput("");',
            '      if (typeof window !== "undefined") {',
            "        const url = new URL(window.location.href);",
            '        url.searchParams.delete("id");',
            '        window.history.replaceState({}, "", url.toString());',
            "      }",
            f'      toast.success("{name} deleted successfully");',
            "    } catch (err) {",
            f'      toast.error(err instanceof Error ? err.message : "Failed to delete {name}");',
            "    }",
            "  };",
        ])

    lines.extend([
        "  const handleCopy = async (text: string, label: string) => {",
        "    try {",
        '      if (navigator?.clipboard?.writeText) {',
        "        await navigator.clipboard.writeText(text);",
        "      } else {",
        '        const textarea = document.createElement("textarea");',
        "        textarea.value = text;",
        "        document.body.appendChild(textarea);",
        "        textarea.select();",
        '        document.execCommand("copy");',
        "        document.body.removeChild(textarea);",
        "      }",
        '      toast.success(`Copied ${label} to clipboard`);',
        "    } catch {",
        '      toast.error(`Failed to copy ${label} to clipboard`);',
        "    }",
        "  };",
        "  const handleExportJson = () => {",
        "    if (!item) return;",
        '    const blob = new Blob([JSON.stringify(item, null, 2)], { type: "application/json" });',
        "    const url = URL.createObjectURL(blob);",
        '    const link = document.createElement("a");',
        '    link.setAttribute("href", url);',
        f'    link.setAttribute("download", `{name.lower()}_${{(item as any).id ?? "detail"}}.json`);',
        "    document.body.appendChild(link);",
        "    link.click();",
        "    document.body.removeChild(link);",
        "    URL.revokeObjectURL(url);",
        '    toast.info("Exported JSON successfully");',
        "  };",
        "  // R-298: detail screen keyboard navigation & shortcuts (prev/next record, edit mode, deselect).",
        "  useEffect(() => {",
        "    const handleKeyDown = (e: KeyboardEvent) => {",
        '      const target = e.target as HTMLElement | null;',
        '      const isEditable = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable);',
        "      if (isEditable) return;",
    ])
    if can_list:
        lines.extend([
            '      if (e.key === "ArrowLeft" || e.key === "[") {',
            "        if (prevItem) {",
            "          e.preventDefault();",
            "          handleSelectId(prevItem.id);",
            "        }",
            '      } else if (e.key === "ArrowRight" || e.key === "]") {',
            "        if (nextItem) {",
            "          e.preventDefault();",
            "          handleSelectId(nextItem.id);",
            "        }",
            "      }",
        ])
    if can_edit and form_screen:
        lines.extend([
            '      if (e.key === "e" || e.key === "E") {',
            "        if (selectedId && typeof window !== \"undefined\") {",
            "          e.preventDefault();",
            f'          window.location.href = `/{form_screen.id}?id=${{selectedId}}`;',
            "        }",
            "      }",
        ])
    lines.extend([
        '      if (e.key === "Escape") {',
        "        if (selectedId) {",
        "          e.preventDefault();",
        "          handleSelectId(null);",
        "        }",
        "      }",
        "    };",
        '    window.addEventListener("keydown", handleKeyDown);',
        '    return () => window.removeEventListener("keydown", handleKeyDown);',
    ])
    detail_kbd_deps = ["selectedId"]
    if can_list:
        detail_kbd_deps.extend(["prevItem", "nextItem"])
    lines.append(f'  }}, [{", ".join(detail_kbd_deps)}]);')

    if has_subcollections:
        if len(subcollections) > 1:
            lines.append('  const [activeTab, setActiveTab] = useState<number>(0);')
        for sub in subcollections:
            s_var = f"{sub.child_entity.name.lower()}sSubcol"
            lines.append(f"  const {s_var} = {sub.hook_name}(selectedId);")
            lines.extend(_subcol_search_state(s_var))

        child_entities_with_delete = list(dict.fromkeys(
            sub.child_entity.name for sub in subcollections if sub.can_delete
        ))
        for c_name in child_entities_with_delete:
            lines.append(
                f"  const {{ remove: remove{c_name}, loading: deleting{c_name}, error: delete{c_name}Error }} = useDelete{c_name}();"
            )

        c_names = [sub.child_entity.name for sub in subcollections]
        def _detail_del_handler_name(sub: SubcollectionInfo) -> str:
            if c_names.count(sub.child_entity.name) > 1:
                return f"handleDelete{_pascal(sub.relation)}{sub.child_entity.name}"
            return f"handleDelete{sub.child_entity.name}"

        for sub in subcollections:
            if sub.can_delete:
                h_name = _detail_del_handler_name(sub)
                c_name = sub.child_entity.name
                s_var = f"{sub.child_entity.name.lower()}sSubcol"
                _del_state, _del_setter = _subcol_delete_names(s_var)
                lines.extend([
                    # R-291: optimistic child delete — hide the row immediately, roll back on error.
                    f"  const [{_del_state}, {_del_setter}] = useState<string[]>([]);",
                    "  useEffect(() => {",
                    f"    {_del_setter}((prev) => prev.filter((did) => ({s_var}.data ?? []).some((x: any) => String(x.id) === did)));",
                    f"  }}, [{s_var}.data]);",
                    f"  const {h_name} = async (id: string) => {{",
                    f'    const ok = await confirmAsync("Delete {c_name}", "Are you sure you want to delete this {c_name}? This action cannot be undone.");',
                    "    if (!ok) return;",
                    f"      {_del_setter}((prev) => [...prev, String(id)]);",
                    "      try {",
                    f"        await remove{c_name}(id);",
                    f"        {s_var}.refetch();",
                    f'        toast.success("{c_name} deleted successfully");',
                    "      } catch (err) {",
                    f"        {_del_setter}((prev) => prev.filter((x) => x !== String(id)));",
                    f'        toast.error(err instanceof Error ? err.message : "Failed to delete {c_name}");',
                    "      }",
                    "  };",
                ])

    lines.extend([
        "",
        "  return (",
        '    <main style={{ maxWidth: 840, margin: "0 auto", padding: "32px 16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>',
        "      <Breadcrumbs items={breadcrumbs} />",
        '      <header style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>',
        "        <div>",
        '          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>',
    ])

    if collection_screen:
        lines.append(
            f'            <Link href="/{collection_screen.id}" style={{{{ color: "#2563eb", textDecoration: "none", fontSize: 13, fontWeight: 500 }}}}>&larr; Back to {plural}</Link>'
        )
    else:
        lines.append(
            '            <Link href="/" style={{ color: "#2563eb", textDecoration: "none", fontSize: 13, fontWeight: 500 }}>&larr; Overview</Link>'
        )

    lines.extend([
        '            <span style={{ color: "#94a3b8" }}>/</span>',
        f'            <span style={{ fontSize: 12, padding: "2px 8px", background: "#f1f5f9", color: "#475569", borderRadius: 4, fontWeight: 600 }}>{screen.role}</span>',
        "          </div>",
        f'          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#0f172a" }}>{title}</h1>',
        "        </div>",
        '        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>',
    ])

    for nav in screen.navigation:
        lines.append(
            f'          <Link href="/{nav}" style={{{{ padding: "8px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, textDecoration: "none", fontSize: 14 }}}}>{_pascal(nav)}</Link>'
        )

    lines.extend([
        "        </div>",
        "      </header>",
        "",
        '      <section style={{ marginBottom: 24, padding: 16, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>',
        "        <input",
        '          type="text"',
        "          value={idInput}",
        "          onChange={(e) => setIdInput(e.target.value)}",
        f'          placeholder="Enter {name} ID..."',
        '          style={{ flex: 1, minWidth: 180, padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, outline: "none" }}',
        "        />",
        "        <button",
        "          onClick={() => handleSelectId(idInput.trim() || null)}",
        '          style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, fontWeight: 500, cursor: "pointer" }}',
        "        >",
        f"          Load {name}",
        "        </button>",
    ])

    if can_list:
        lines.extend([
            '        <span style={{ color: "#94a3b8", fontSize: 13 }}>or</span>',
            "        <select",
            f'          aria-label="Select {name}"',
            '          value={selectedId ?? ""}',
            "          onChange={(e) => handleSelectId(e.target.value || null)}",
            '          style={{ padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, background: "#fff", color: "#334155", outline: "none", cursor: "pointer", maxWidth: 220 }}',
            "        >",
            f'          <option value="">-- Choose {name} --</option>',
            "          {listItems?.map((it: any) => (",
            '            <option key={it.id} value={it.id}>',
            f"              {{String((it as any).{best_title_f} ?? it.id)}}",
            "            </option>",
            "          ))}",
            "        </select>",
        ])

    lines.extend([
        "        {selectedId && (",
        "          <button",
        '            type="button"',
        "            onClick={() => handleSelectId(null)}",
        '            style={{ padding: "8px 12px", border: "1px solid #cbd5e1", background: "#f8fafc", color: "#64748b", borderRadius: 6, fontSize: 13, cursor: "pointer" }}',
        "          >",
        "            Clear",
        "          </button>",
        "        )}",
        "      </section>",
        "",
    ])

    if can_list:
        lines.extend([
            "      {!selectedId && (",
            '        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 24, textAlign: "center", boxShadow: "0 1px 3px rgba(0,0,0,0.05)", marginBottom: 24 }}>',
            f'          <p style={{{{ margin: "0 0 16px 0", color: "#64748b", fontSize: 14 }}}}>Select a {name} above or pick from recent records:</p>',
            "          {loadingList && (",
            '            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12 }}>',
            "              {[0, 1, 2].map((i) => (",
            '                <div key={i} style={{ height: 56, background: "#f1f5f9", borderRadius: 6, opacity: 1 - i * 0.2 }} />',
            "              ))}",
            "            </div>",
            "          )}",
            "          {listItems && listItems.length > 0 ? (",
            '            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 12, textAlign: "left" }}>',
            "              {listItems.slice(0, 6).map((rec: any) => (",
            "                <button",
            "                  key={rec.id}",
            '                  type="button"',
            "                  onClick={() => handleSelectId(rec.id)}",
            '                  style={{ padding: "12px 14px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, cursor: "pointer", display: "flex", flexDirection: "column", gap: 4, textAlign: "left" }}',
            "                >",
            f'                  <span style={{{{ fontWeight: 600, fontSize: 14, color: "#1e293b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}}}>{{String((rec as any).{best_title_f} ?? rec.id)}}</span>',
            '                  <span style={{ fontSize: 12, color: "#64748b" }}>ID: {String(rec.id).slice(0, 8)}...</span>',
            "                </button>",
            "              ))}",
            "            </div>",
            "          ) : (",
            f'            !loadingList && <p style={{{{ margin: 0, color: "#94a3b8", fontSize: 13 }}}}>No {plural} found.</p>',
            "          )}",
            "        </div>",
            "      )}",
            "",
        ])

    if Op.GET in ops:
        lines.extend([
            "      {loading && (",
            '        <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 12 }}>',
            "          {[0, 1, 2, 3].map((i) => (",
            '            <div key={i} style={{ height: 14, background: "#e2e8f0", borderRadius: 4, width: `${88 - i * 14}%` }} />',
            "          ))}",
            "        </div>",
            "      )}",
            "      {error && (",
            '        <div role="alert" aria-live="assertive" style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#991b1b", marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>',
            f"          <span>Error loading {name}: {{error.message}}</span>",
            '          <button onClick={() => refetch()} style={{ padding: "4px 8px", background: "#991b1b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}>Retry</button>',
            "        </div>",
            "      )}",
            "      {item && (",
            '        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 24, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>',
            '          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>',
            '            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>',
            f'              <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: "#0f172a" }}>',
            f"                {{String((item as any).{best_title_f} ?? (item as any).id)}}",
            "              </h2>",
            "              <button",
            '                type="button"',
            '                onClick={() => handleCopy(String((item as any).id), "ID")}',
            '                aria-label="Copy ID to clipboard"',
            '                title="Copy ID to clipboard"',
            '                style={{ padding: "3px 8px", background: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: 12, color: "#475569", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 4 }}',
            "              >",
            "                <span>📋</span> Copy ID",
            "              </button>",
            "            </div>",
            '            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>',
        ])

        if can_list:
            lines.extend([
                '              <div style={{ display: "flex", gap: 4, alignItems: "center", marginRight: 4 }}>',
                "                <button",
                '                  type="button"',
                "                  onClick={() => prevItem && handleSelectId(prevItem.id)}",
                "                  disabled={!prevItem}",
                f'                  title={{prevItem ? `Previous: ${{String((prevItem as any).{best_title_f} ?? prevItem.id)}}` : "No previous record"}}',
                '                  style={{ padding: "6px 10px", border: "1px solid #cbd5e1", background: "#fff", color: prevItem ? "#334155" : "#94a3b8", borderRadius: 6, fontSize: 13, cursor: prevItem ? "pointer" : "default" }}',
                "                >",
                "                  &larr; Prev",
                "                </button>",
                "                <button",
                '                  type="button"',
                "                  onClick={() => nextItem && handleSelectId(nextItem.id)}",
                "                  disabled={!nextItem}",
                f'                  title={{nextItem ? `Next: ${{String((nextItem as any).{best_title_f} ?? nextItem.id)}}` : "No next record"}}',
                '                  style={{ padding: "6px 10px", border: "1px solid #cbd5e1", background: "#fff", color: nextItem ? "#334155" : "#94a3b8", borderRadius: 6, fontSize: 13, cursor: nextItem ? "pointer" : "default" }}',
                "                >",
                "                  Next &rarr;",
                "                </button>",
                "              </div>",
            ])

        lines.extend([
            "              <button",
            '                type="button"',
            "                onClick={handleExportJson}",
            '                style={{ padding: "6px 12px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: "pointer" }}',
            "              >",
            "                Export JSON",
            "              </button>",
        ])

        if can_edit and form_screen:
            lines.extend([
                "              <Link",
                f"                href={{`/{form_screen.id}?id=${{selectedId}}`}}",
                '                style={{ padding: "6px 12px", border: "1px solid #cbd5e1", background: "#fff", color: "#2563eb", borderRadius: 6, fontSize: 13, fontWeight: 500, textDecoration: "none" }}',
                "              >",
                f"                Edit {name}",
                "              </Link>",
            ])

        if can_delete:
            lines.extend([
                "              <button",
                '                type="button"',
                "                onClick={handleDelete}",
                "                disabled={deletingMain}",
                '                style={{ padding: "6px 12px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 500, cursor: deletingMain ? "default" : "pointer" }}',
                "              >",
                f'                {{deletingMain ? "Deleting..." : "Delete {name}"}}',
                "              </button>",
            ])

        lines.extend([
            "            </div>",
            "          </div>",
        ])

        if can_delete:
            lines.extend([
                "          {deleteMainError && (",
                '            <div style={{ padding: "10px 14px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#991b1b", marginBottom: 16, fontSize: 13 }}>',
                f"              Error deleting {name}: {{deleteMainError.message}}",
                "            </div>",
                "          )}",
            ])

        lines.append('          <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 16px", fontSize: 14 }}>')
        for f in entity.fields:
            flabel = _title_case(f.name)
            is_id_field = f.name == "id" or f.type == FieldType.UUID or f.name.endswith("_id")
            val_jsx = _field_value_jsx(f, f"(item as any).{f.name}")
            if is_id_field:
                dd_content = (
                    f'            <dd style={{{{ margin: 0, color: "#1e293b", display: "flex", alignItems: "center", gap: 8 }}}}>'
                    f'              <span>{val_jsx}</span>'
                    f'              {{(item as any).{f.name} && ('
                    f'                <button'
                    f'                  type="button"'
                    f'                  onClick={{() => handleCopy(String((item as any).{f.name}), "{flabel}")}}'
                    f'                  aria-label="Copy {flabel} to clipboard"'
                    f'                  title="Copy {flabel} to clipboard"'
                    f'                  style={{{{ padding: "2px 6px", background: "transparent", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: 11, color: "#64748b", cursor: "pointer" }}}}'
                    f'                >'
                    f'                  Copy'
                    f'                </button>'
                    f'              )}}'
                    f'            </dd>'
                )
                lines.extend([
                    f'            <dt style={{ fontWeight: 600, color: "#475569" }}>{flabel}:</dt>',
                    dd_content,
                ])
            else:
                lines.extend([
                    f'            <dt style={{ fontWeight: 600, color: "#475569" }}>{flabel}:</dt>',
                    f'            <dd style={{ margin: 0, color: "#1e293b" }}>{val_jsx}</dd>',
                ])
        lines.extend([
            "          </dl>",
            "        </div>",
            "      )}",
        ])

    if has_subcollections:
        sub_labels = ", ".join(sub.child_plural for sub in subcollections)
        lines.extend([
            '      <section style={{ border: "1px solid #e2e8f0", borderRadius: 8, background: "#fff", padding: 20, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>',
            "        {!selectedId ? (",
            '          <div style={{ textAlign: "center", padding: "20px 16px", color: "#64748b" }}>',
            f'            <p style={{{{ margin: 0, fontSize: 14 }}}}>Enter a {name} ID above to view associated {sub_labels}.</p>',
            "          </div>",
        ])
        lines.append("        ) : (")
        lines.append("          <div>")

        if len(subcollections) > 1:
            lines.append('            <div style={{ display: "flex", gap: 8, marginBottom: 16, borderBottom: "1px solid #e2e8f0", paddingBottom: 8 }}>')
            for idx, sub in enumerate(subcollections):
                s_var = f"{sub.child_entity.name.lower()}sSubcol"
                lines.extend([
                    "              <button",
                    f"                onClick={{() => setActiveTab({idx})}}",
                    "                style={{",
                    '                  padding: "6px 12px",',
                    '                  border: "none",',
                    f'                  background: activeTab === {idx} ? "#2563eb" : "#f1f5f9",',
                    f'                  color: activeTab === {idx} ? "#fff" : "#475569",',
                    '                  borderRadius: 6,',
                    '                  fontSize: 13,',
                    '                  fontWeight: 500,',
                    '                  cursor: "pointer",',
                    '                  display: "flex",',
                    '                  alignItems: "center",',
                    '                  gap: 6,',
                    "                }}",
                    "              >",
                    f"                <span>{sub.child_plural}</span>",
                    f'                <span style={{{{ padding: "2px 6px", background: activeTab === {idx} ? "rgba(255,255,255,0.2)" : "#e2e8f0", color: activeTab === {idx} ? "#fff" : "#475569", borderRadius: 10, fontSize: 11, fontWeight: 600 }}}}>',
                    f"                  {{{s_var}.total}}",
                    "                </span>",
                    "              </button>",
                ])
            lines.append("            </div>")

        for idx, sub in enumerate(subcollections):
            s_var = f"{sub.child_entity.name.lower()}sSubcol"
            tab_guard = f"activeTab === {idx}" if len(subcollections) > 1 else "true"
            child_form = next(
                (s for s in ir.screens if _screen_intent(s) == "form" and (_match_entity(s, ir) and _match_entity(s, ir).name == sub.child_entity.name)),
                None,
            )
            lines.extend([
                f"            {{{tab_guard} && (",
                "              <div>",
                '                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>',
                '                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>',
                f'                    <h4 style={{{{ margin: 0, fontSize: 16, fontWeight: 600, color: "#1e293b" }}}}>{sub.child_plural}</h4>',
                f'                    <span style={{{{ padding: "2px 8px", background: "#e0e7ff", color: "#3730a3", borderRadius: 12, fontSize: 12, fontWeight: 600 }}}}>',
                f"                      {{{s_var}.total}}",
                "                    </span>",
                "                  </div>",
            ])
            if child_form:
                lines.extend([
                    '                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>',
                    '                    <Link',
                    f"                      href={{`/{child_form.id}?{sub.id_param}=${{selectedId}}`}}",
                    '                      style={{ padding: "4px 8px", background: "#2563eb", color: "#fff", borderRadius: 4, fontSize: 12, textDecoration: "none", fontWeight: 500 }}',
                    '                    >',
                    f'                      + New {sub.child_entity.name}',
                    '                    </Link>',
                    "                    <button",
                    f"                      onClick={{() => {s_var}.refetch()}}",
                    f"                      disabled={{{s_var}.loading}}",
                    f'                      style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 4, fontSize: 12, cursor: {s_var}.loading ? "default" : "pointer" }}}}',
                    "                    >",
                    f'                      {{{s_var}.loading ? "Loading..." : "Refresh"}}',
                    "                    </button>",
                    "                  </div>",
                    "                </div>",
                ])
            else:
                lines.extend([
                    "                  <button",
                    f"                    onClick={{() => {s_var}.refetch()}}",
                    f"                    disabled={{{s_var}.loading}}",
                    f'                    style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 4, fontSize: 12, cursor: {s_var}.loading ? "default" : "pointer" }}}}',
                    "                  >",
                    f'                    {{{s_var}.loading ? "Loading..." : "Refresh"}}',
                    "                  </button>",
                    "                </div>",
                ])
            lines.extend([
                f"                {{{s_var}.loading && !{s_var}.data && (",
                '                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>',
                "                    {[0, 1, 2].map((i) => (",
                '                      <div key={i} style={{ height: 44, background: "#f1f5f9", borderRadius: 6, opacity: 1 - i * 0.2 }} />',
                "                    ))}",
                "                  </div>",
                "                )}",
                f"                {{{s_var}.error && (",
                f'                  <div role="alert" aria-live="assertive" style={{{{ padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#991b1b", fontSize: 13, marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}}}>',
                f"                    <span>Error: {{{s_var}.error.message}}</span>",
                f'                    <button onClick={{() => {s_var}.refetch()}} style={{{{ padding: "2px 8px", background: "#991b1b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}}}>Retry</button>',
                "                  </div>",
                "                )}",
            ])
            if sub.can_delete:
                c_name = sub.child_entity.name
                lines.extend([
                    f"                {{delete{c_name}Error && (",
                    f'                  <div role="alert" aria-live="assertive" style={{{{ padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#991b1b", fontSize: 13, marginBottom: 12 }}}}>Error deleting {c_name.lower()}: {{delete{c_name}Error.message}}</div>',
                    "                )}",
                ])
            lines.extend(_subcol_controls(sub, s_var))
            lines.extend(_subcol_filtered_empty(sub, s_var))
            empty_guard = f"{s_var}.data && {s_var}.data.length === 0"
            if _filterable_fields_for_entity(sub.child_entity):
                empty_guard += f" && Object.keys({s_var}.params.filters ?? {{}}).length === 0"
            lines.extend([
                f"                {{{empty_guard} && (",
            ])
            if child_form:
                lines.extend([
                    '                  <div style={{ padding: 24, textAlign: "center", color: "#64748b", fontSize: 14, background: "#f8fafc", borderRadius: 6, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>',
                    f'                    <div role="status">No {sub.child_plural.lower()} found for this {name.lower()}.</div>',
                    '                    <Link',
                    f"                      href={{`/{child_form.id}?{sub.id_param}=${{selectedId}}`}}",
                    '                      style={{ display: "inline-block", padding: "6px 12px", background: "#2563eb", color: "#fff", borderRadius: 4, fontSize: 12, textDecoration: "none", fontWeight: 500 }}',
                    '                    >',
                    f"                      + Add first {sub.child_entity.name}",
                    '                    </Link>',
                    '                  </div>',
                ])
            else:
                lines.append(
                    f'                  <div role="status" style={{{{ padding: 16, textAlign: "center", color: "#64748b", fontSize: 14, background: "#f8fafc", borderRadius: 6 }}}}>No {sub.child_plural.lower()} found for this {name.lower()}.</div>'
                )
            lines.append("                )}")
            # R-291: deletable subcollections render the optimistic-delete-filtered child list.
            _child_map_src = (
                f"({s_var}.data ?? []).filter((child: any) => !{_subcol_delete_names(s_var)[0]}.includes(String((child as any).id)))"
                if sub.can_delete else f"{s_var}.data"
            )
            lines.extend([
                f"                {{{s_var}.data && {s_var}.data.length > 0 && (",
                '                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>',
                f"                    {{{_child_map_src}.map((child, cIdx) => (",
            ])
            if sub.can_delete:
                h_name = _detail_del_handler_name(sub)
                c_name = sub.child_entity.name
                lines.extend([
                    '                      <div key={(child as any).id ?? cIdx} style={{ padding: 12, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14, display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>',
                    '                        <div style={{ flex: 1 }}>',
                ])
                for df in sub.display_fields:
                    df_label = _title_case(df.name)
                    df_val = _field_value_jsx(df, f"(child as any).{df.name}")
                    lines.append(
                        f'                          <div style={{{{ color: "#334155" }}}}><strong>{df_label}:</strong> {df_val}</div>'
                    )
                lines.extend([
                    '                        </div>',
                    '                        <button',
                    f'                          onClick={{(e) => {{ e.stopPropagation(); {h_name}((child as any).id); }}}}',
                    f'                          disabled={{deleting{c_name}}}',
                    f'                          style={{{{ padding: "4px 8px", background: "#fee2e2", color: "#b91c1c", border: "1px solid #fca5a5", borderRadius: 4, fontSize: 12, fontWeight: 500, cursor: deleting{c_name} ? "default" : "pointer" }}}}',
                    '                        >',
                    f'                          {{deleting{c_name} ? "Deleting..." : "Delete"}}',
                    '                        </button>',
                    '                      </div>',
                ])
            else:
                lines.append(
                    '                      <div key={(child as any).id ?? cIdx} style={{ padding: 12, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14 }}>'
                )
                for df in sub.display_fields:
                    df_label = _title_case(df.name)
                    df_val = _field_value_jsx(df, f"(child as any).{df.name}")
                    lines.append(
                        f'                        <div style={{{{ color: "#334155" }}}}><strong>{df_label}:</strong> {df_val}</div>'
                    )
                lines.append('                      </div>')
            lines.extend([
                "                    ))}",
                "                  </div>",
                "                )}",
            ])
            lines.extend(_subcol_pagination(s_var))
            lines.extend([
                "              </div>",
                "            )}",
            ])

        lines.extend([
            "          </div>",
            "        )}",
            "      </section>",
        ])

    if uses_confirm_detail:
        lines.extend([
            "      {/* R-304: accessible modal confirmation dialog */}",
            "      <ConfirmDialog {...confirmProps} />",
        ])

    lines.extend([
        "    </main>",
        "  );",
        "}",
        "",
    ])

    return "\n".join(lines)


def _fallback_screen_page(screen: Screen, ir: ApplicationIR, entity: Entity | None = None) -> str:
    page_name = f"{_pascal(screen.id)}Page"
    title = _title_case(screen.id)
    components = ", ".join(screen.components) or "none"
    actions = ", ".join(screen.actions) or "none"

    lines: list[str] = [
        '"use client";',
        "",
        'import Link from "next/link";',
        "",
        f"export default function {page_name}() {{",
        "  return (",
        '    <main style={{ maxWidth: 720, margin: "0 auto", padding: "32px 16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>',
        '      <header style={{ marginBottom: 24 }}>',
        '        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>',
        '          <Link href="/" style={{ color: "#2563eb", textDecoration: "none", fontSize: 13, fontWeight: 500 }}>&larr; Overview</Link>',
        '          <span style={{ color: "#94a3b8" }}>/</span>',
        f'          <span style={{ fontSize: 12, padding: "2px 8px", background: "#f1f5f9", color: "#475569", borderRadius: 4, fontWeight: 600 }}>{screen.role}</span>',
        "        </div>",
        f'        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, color: "#0f172a" }}>{title}</h1>',
        "      </header>",
        '      <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>',
        f'        <p style={{ margin: "0 0 12px 0", color: "#475569" }}><strong>Role:</strong> {screen.role}</p>',
        f'        <p style={{ margin: "0 0 12px 0", color: "#475569" }}><strong>Components:</strong> {components}</p>',
        f'        <p style={{ margin: "0 0 16px 0", color: "#475569" }}><strong>Actions:</strong> {actions}</p>',
    ]

    if screen.navigation:
        lines.append('        <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid #f1f5f9", display: "flex", gap: 8, flexWrap: "wrap" }}>')
        for nav in screen.navigation:
            lines.append(
                f'          <Link href="/{nav}" style={{{{ padding: "6px 12px", border: "1px solid #cbd5e1", background: "#f8fafc", color: "#334155", borderRadius: 6, textDecoration: "none", fontSize: 13 }}}}>{_pascal(nav)}</Link>'
            )
        lines.append("        </div>")

    lines.extend([
        "      </div>",
        "    </main>",
        "  );",
        "}",
        "",
    ])

    return "\n".join(lines)


def _screen_page(screen: Screen, ir: ApplicationIR) -> str:
    entity = _match_entity(screen, ir)
    if entity is None:
        return _fallback_screen_page(screen, ir, None)

    intent = _screen_intent(screen)
    ops_by_entity = _get_ops_by_entity(ir)
    ops = ops_by_entity.get(entity.name, set())

    if intent == "collection" and Op.LIST in ops:
        return _collection_screen_page(screen, entity, ir, ops)
    elif intent == "form" and (Op.CREATE in ops or Op.UPDATE in ops):
        return _form_screen_page(screen, entity, ir, ops)
    elif intent == "detail" and (Op.GET in ops or Op.LIST in ops):
        return _detail_screen_page(screen, entity, ir, ops)
    else:
        return _fallback_screen_page(screen, ir, entity)


def render_screen_page(screen: Screen, ir: ApplicationIR) -> str:
    """Public helper to render a single screen page."""
    return _screen_page(screen, ir)



def _overview_page(ir: ApplicationIR) -> str:  # noqa: PLR0912
    """Generate a rich entity-aware dashboard overview page (app/page.tsx).

    The page is a client component so it can call useList hooks for live counts.
    ir.description is intentionally NOT embedded — it already lives in README.md
    and its absence preserves byte-for-byte diff invariance across IR description edits.
    """
    ops_by_entity = _get_ops_by_entity(ir)
    escaped_name = _escape_ts(ir.name)

    # Entities with Op.LIST wired — these get live count cards.
    listable: list[tuple[Entity, str]] = []  # (entity, plural)
    for entity in ir.entities:
        if Op.LIST in ops_by_entity.get(entity.name, set()):
            plural = entity.name if entity.name.endswith("s") else f"{entity.name}s"
            listable.append((entity, plural))

    # Primary screens (non-detail) for navigation cards.
    nav_screens: list[Screen] = []
    form_screens: list[tuple[Screen, Entity | None]] = []
    col_screens_by_entity: dict[str, Screen] = {}
    for s in ir.screens:
        intent = _screen_intent(s)
        if intent == "detail":
            continue
        nav_screens.append(s)
        if intent == "form":
            entity = _match_entity(s, ir)
            form_screens.append((s, entity))
        elif intent == "collection":
            s_entity = _match_entity(s, ir)
            if s_entity and s_entity.name not in col_screens_by_entity:
                col_screens_by_entity[s_entity.name] = s

    # ── Imports ──────────────────────────────────────────────────────────────
    lines: list[str] = ['"use client";', ""]
    has_links = bool(nav_screens or col_screens_by_entity or form_screens)
    if has_links:
        lines.append('import Link from "next/link";')
    if listable:
        hook_names = [f"useList{plural}" for _, plural in listable]
        lines.append(f'import {{ {", ".join(hook_names)} }} from "../lib/hooks";')
    lines.append("")

    # ── Component open ────────────────────────────────────────────────────────
    lines.append("export default function HomePage() {")

    # One useList call per listable entity (limit: 1 — we only need the total count).
    for entity, plural in listable:
        var = f"{entity.name[0].lower()}{entity.name[1:]}List"
        lines.append(f'  const {var} = useList{plural}({{ limit: 1 }});')

    lines.append("  return (")

    # ── Page shell ────────────────────────────────────────────────────────────
    listable_count = len(listable)
    screen_count = len(ir.screens)
    entity_label = f"{listable_count} {'Entity' if listable_count == 1 else 'Entities'}"
    screen_label = f"{screen_count} {'Screen' if screen_count == 1 else 'Screens'}"

    lines.extend([
        '    <main style={{ minHeight: "100vh", background: "#f8fafc", padding: "32px 24px" }}>',
        "",
        "      {/* ── App header ─────────────────────────────────────── */}",
        '      <section style={{ marginBottom: 40, display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>',
        "        <div>",
        f'          <h1 style={{{{ fontSize: 28, fontWeight: 700, color: "#0f172a", margin: "0 0 8px" }}}}>{escaped_name}</h1>',
        '          <p style={{ color: "#64748b", margin: 0, fontSize: 15 }}>Dashboard overview</p>',
        "        </div>",
        '        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>',
        '          <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 14px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 9999, fontSize: 13, fontWeight: 500, color: "#166534" }}>',
        '            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#22c55e", display: "inline-block" }} />',
        "            System Operational",
        "          </div>",
        f'          <span style={{{{ fontSize: 12, padding: "6px 12px", background: "#ffffff", border: "1px solid #e2e8f0", color: "#475569", borderRadius: 9999, fontWeight: 600 }}}}>{entity_label}</span>',
        f'          <span style={{{{ fontSize: 12, padding: "6px 12px", background: "#ffffff", border: "1px solid #e2e8f0", color: "#475569", borderRadius: 9999, fontWeight: 600 }}}}>{screen_label}</span>',
        "        </div>",
        "      </section>",
        "",
    ])

    # ── Zero state fallback ───────────────────────────────────────────────────
    if not listable and not nav_screens:
        lines.extend([
            "      {/* ── Empty state fallback ───────────────────────────── */}",
            '      <section style={{ background: "#ffffff", borderRadius: 12, padding: "48px 24px", textAlign: "center", border: "1px dashed #cbd5e1", maxWidth: 540, margin: "40px auto" }}>',
            f'        <h2 style={{{{ fontSize: 18, fontWeight: 600, color: "#1e293b", margin: "0 0 8px" }}}}>Welcome to {escaped_name}</h2>',
            '        <p style={{ fontSize: 14, color: "#64748b", margin: 0 }}>No entities or screens configured yet.</p>',
            "      </section>",
            "",
        ])

    # ── Entity count cards ────────────────────────────────────────────────────
    if listable:
        lines.extend([
            "      {/* ── Entity summary cards ───────────────────────────── */}",
            '      <section style={{ marginBottom: 40 }}>',
            '        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#1e293b", marginBottom: 16 }}>Entities</h2>',
            '        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>',
        ])
        for entity, plural in listable:
            var = f"{entity.name[0].lower()}{entity.name[1:]}List"
            escaped_entity_name = _escape_ts(entity.name)
            escaped_plural = _escape_ts(plural)
            col_s = col_screens_by_entity.get(entity.name)
            if col_s:
                lines.extend([
                    "          {/* " + entity.name + " card */}",
                    f'          <Link href="/{col_s.id}" aria-label="View {escaped_plural} collection" style={{{{',
                    '            display: "block", background: "#ffffff", borderRadius: 12,',
                    '            padding: "20px 24px", textDecoration: "none",',
                    '            boxShadow: "0 1px 3px rgba(0,0,0,0.08)", border: "1px solid #e2e8f0"',
                    "          }}>",
                    '            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>',
                    f'              <p style={{{{ fontSize: 13, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 1, margin: 0 }}}}>{escaped_entity_name}</p>',
                    '              <span style={{ fontSize: 12, color: "#94a3b8" }}>&rarr;</span>',
                    "            </div>",
                    '            <p style={{ fontSize: 32, fontWeight: 700, color: "#0f172a", margin: "0 0 4px" }}>',
                    f"              {{{var}.loading ? \"…\" : {var}.error ? \"—\" : {var}.total}}",
                    "            </p>",
                    '            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>',
                    f'              <p style={{{{ fontSize: 13, color: "#94a3b8", margin: 0 }}}}>{escaped_plural}</p>',
                    '              <span style={{ fontSize: 12, color: "#2563eb", fontWeight: 500 }}>View all &rarr;</span>',
                    "            </div>",
                    "          </Link>",
                ])
            else:
                lines.extend([
                    "          {/* " + entity.name + " card */}",
                    "          <div style={{",
                    '            background: "#ffffff", borderRadius: 12, padding: "20px 24px",',
                    '            boxShadow: "0 1px 3px rgba(0,0,0,0.08)", border: "1px solid #e2e8f0"',
                    "          }}>",
                    f'            <p style={{{{ fontSize: 13, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 1, margin: "0 0 8px" }}}}>{escaped_entity_name}</p>',
                    f'            <p style={{{{ fontSize: 32, fontWeight: 700, color: "#0f172a", margin: "0 0 4px" }}}}>',
                    f'              {{{var}.loading ? "…" : {var}.error ? "—" : {var}.total}}',
                    "            </p>",
                    f'            <p style={{{{ fontSize: 13, color: "#94a3b8", margin: 0 }}}}>{escaped_plural}</p>',
                    "          </div>",
                ])
        lines.extend([
            "        </div>",
            "      </section>",
            "",
        ])

    # ── Screen navigation cards ────────────────────────────────────────────────
    if nav_screens:
        lines.extend([
            "      {/* ── Screen navigation ─────────────────────────────── */}",
            '      <section style={{ marginBottom: 40 }}>',
            '        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#1e293b", marginBottom: 16 }}>Screens</h2>',
            '        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 16 }}>',
        ])
        for s in nav_screens:
            title = _title_case(s.id)
            intent = _screen_intent(s)
            intent_label = {"collection": "Collection", "form": "Form", "generic": "Screen"}.get(intent, "Screen")
            is_public = s.role in ("public", "")
            escaped_title = _escape_ts(title)
            escaped_intent_label = _escape_ts(intent_label)
            lines.extend([
                "          {/* " + s.id + " */}",
                f'          <Link href="/{s.id}" style={{{{',
                '            display: "block", background: "#ffffff", borderRadius: 12,',
                '            padding: "20px 24px", textDecoration: "none",',
                '            boxShadow: "0 1px 3px rgba(0,0,0,0.08)", border: "1px solid #e2e8f0"',
                "          }}>",
                '            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>',
                f'              <p style={{{{ fontSize: 15, fontWeight: 600, color: "#1e293b", margin: 0 }}}}>{escaped_title}</p>',
                '              <span style={{ fontSize: 14, color: "#94a3b8" }}>&rarr;</span>',
                "            </div>",
                f'            <p style={{{{ fontSize: 13, color: "#64748b", margin: 0 }}}}>{escaped_intent_label}',
            ])
            if not is_public:
                escaped_role = _escape_ts(s.role)
                lines.append(
                    f'              <span style={{{{ background: "#eff6ff", color: "#1d4ed8", borderRadius: 4,'
                    f' padding: "2px 6px", fontSize: 11, fontWeight: 600, marginLeft: 8 }}}}>{escaped_role}</span>'
                )
            lines.extend([
                "            </p>",
                "          </Link>",
            ])
        lines.extend([
            "        </div>",
            "      </section>",
            "",
        ])

    # ── Quick actions ──────────────────────────────────────────────────────────
    if form_screens:
        lines.extend([
            "      {/* ── Quick actions ────────────────────────────────── */}",
            '      <section>',
            '        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#1e293b", marginBottom: 16 }}>Quick Actions</h2>',
            '        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>',
        ])
        for s, entity in form_screens:
            label = f"+ Create {entity.name}" if entity else f"+ {_title_case(s.id)}"
            escaped_label = _escape_ts(label)
            lines.extend([
                f'          <Link href="/{s.id}" style={{{{',
                '            background: "#2563eb", color: "#ffffff", borderRadius: 8,',
                '            padding: "10px 20px", textDecoration: "none",',
                '            fontSize: 14, fontWeight: 600',
                "          }}>",
                f'            {escaped_label}',
                "          </Link>",
            ])
        lines.extend([
            "        </div>",
            "      </section>",
            "",
        ])

    # ── Close ─────────────────────────────────────────────────────────────────
    lines.extend([
        "    </main>",
        "  );",
        "}",
        "",
    ])

    return "\n".join(lines)


def _navbar_component(ir: ApplicationIR) -> str:
    """Generate a responsive application navigation header shell (components/navbar.tsx)."""
    brand_initial = ir.name[:1].upper() if ir.name else "O"
    escaped_name = _escape_ts(ir.name)

    primary_screens: list[Screen] = []
    create_form: Screen | None = None

    for s in ir.screens:
        intent = _screen_intent(s)
        if intent == "detail":
            continue
        primary_screens.append(s)
        if intent == "form" and create_form is None:
            create_form = s

    nav_links_jsx: list[str] = [
        '            <Link href="/" style={navLinkStyle(isLinkActive("/"))}>',
        '              Overview',
        '            </Link>',
    ]

    for s in primary_screens:
        s_title = _title_case(s.id)
        s_role = s.role.strip()
        role_badge = ""
        if s_role and s_role.lower() not in ("public", "anon", "anonymous", ""):
            role_badge = (
                f' <span style={{{{ fontSize: 10, padding: "1px 5px", background: "#f1f5f9", '
                f'color: "#64748b", borderRadius: 4, fontWeight: 600 }}}}>{s_role}</span>'
            )
        nav_links_jsx.extend([
            f'            <Link href="/{s.id}" style={{navLinkStyle(isLinkActive("/{s.id}"))}}>',
            f'              {s_title}{role_badge}',
            '            </Link>',
        ])

    nav_links_str = "\n".join(nav_links_jsx)

    create_button_jsx = ""
    if create_form:
        entity = _match_entity(create_form, ir)
        if entity:
            cta_label = f"+ New {entity.name}"
        else:
            cta_label = f"+ {_title_case(create_form.id)}"
        create_button_jsx = (
            f'          <Link\n'
            f'            href="/{create_form.id}"\n'
            '            style={{\n'
            '              display: "inline-flex",\n'
            '              alignItems: "center",\n'
            '              gap: 4,\n'
            '              padding: "6px 14px",\n'
            '              background: "#2563eb",\n'
            '              color: "#ffffff",\n'
            '              borderRadius: 6,\n'
            '              fontSize: 13,\n'
            '              fontWeight: 600,\n'
            '              textDecoration: "none",\n'
            '              boxShadow: "0 1px 2px 0 rgba(37, 99, 235, 0.2)",\n'
            '            }}\n'
            '          >\n'
            f'            {cta_label}\n'
            '          </Link>\n'
        )

    actions_jsx = (
        '        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>\n'
        '          <button\n'
        '            type="button"\n'
        '            onClick={() => setShortcutsOpen(true)}\n'
        '            title="Keyboard shortcuts (?)"\n'
        '            aria-label="View keyboard shortcuts"\n'
        '            style={{\n'
        '              display: "inline-flex",\n'
        '              alignItems: "center",\n'
        '              gap: 6,\n'
        '              padding: "5px 10px",\n'
        '              borderRadius: 6,\n'
        '              border: "1px solid #cbd5e1",\n'
        '              background: "#ffffff",\n'
        '              color: "#475569",\n'
        '              fontSize: 12,\n'
        '              fontWeight: 500,\n'
        '              cursor: "pointer",\n'
        '            }}\n'
        '          >\n'
        '            <span>&#x2328;</span>\n'
        '            <span>Shortcuts</span>\n'
        '            <kbd style={{ fontSize: 10, padding: "1px 4px", background: "#f1f5f9", borderRadius: 3, border: "1px solid #e2e8f0", color: "#64748b" }}>?</kbd>\n'
        '          </button>\n'
        f'{create_button_jsx}'
        '        </div>\n'
    )

    return (
        '"use client";\n\n'
        'import { useState, useEffect } from "react";\n'
        'import Link from "next/link";\n'
        'import { usePathname } from "next/navigation";\n'
        'import { ShortcutsDialog } from "./shortcuts-dialog";\n\n'
        'export function Navbar() {\n'
        '  const pathname = usePathname();\n'
        '  const [shortcutsOpen, setShortcutsOpen] = useState(false);\n\n'
        '  useEffect(() => {\n'
        '    const handleKeyDown = (e: KeyboardEvent) => {\n'
        '      const target = e.target as HTMLElement | null;\n'
        '      const isEditable = target && (\n'
        '        target.tagName === "INPUT" ||\n'
        '        target.tagName === "TEXTAREA" ||\n'
        '        target.tagName === "SELECT" ||\n'
        '        target.isContentEditable\n'
        '      );\n'
        '      if (!isEditable && e.key === "?" && !e.metaKey && !e.ctrlKey && !e.altKey) {\n'
        '        e.preventDefault();\n'
        '        setShortcutsOpen((prev) => !prev);\n'
        '      }\n'
        '    };\n'
        '    window.addEventListener("keydown", handleKeyDown);\n'
        '    return () => window.removeEventListener("keydown", handleKeyDown);\n'
        '  }, []);\n\n'
        '  const isLinkActive = (href: string) => {\n'
        '    if (href === "/") {\n'
        '      return pathname === "/";\n'
        '    }\n'
        '    return pathname === href || pathname.startsWith(href + "/");\n'
        '  };\n\n'
        '  const navLinkStyle = (active: boolean) => ({\n'
        '    display: "inline-flex",\n'
        '    alignItems: "center",\n'
        '    gap: 6,\n'
        '    padding: "6px 12px",\n'
        '    borderRadius: 6,\n'
        '    fontSize: 13,\n'
        '    fontWeight: active ? 600 : 500,\n'
        '    color: active ? "#1d4ed8" : "#475569",\n'
        '    background: active ? "#eff6ff" : "transparent",\n'
        '    textDecoration: "none",\n'
        '    border: active ? "1px solid #bfdbfe" : "1px solid transparent",\n'
        '    transition: "all 0.15s ease",\n'
        '  });\n\n'
        '  return (\n'
        '    <header\n'
        '      role="banner"\n'
        '      style={{\n'
        '        position: "sticky",\n'
        '        top: 0,\n'
        '        zIndex: 50,\n'
        '        background: "#ffffff",\n'
        '        borderBottom: "1px solid #e2e8f0",\n'
        '        boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",\n'
        '      }}\n'
        '    >\n'
        '      <div\n'
        '        style={{\n'
        '          maxWidth: 1200,\n'
        '          margin: "0 auto",\n'
        '          padding: "0 16px",\n'
        '          height: 56,\n'
        '          display: "flex",\n'
        '          alignItems: "center",\n'
        '          justifyContent: "space-between",\n'
        '          gap: 16,\n'
        '        }}\n'
        '      >\n'
        '        <div style={{ display: "flex", alignItems: "center", gap: 20, minWidth: 0 }}>\n'
        '          <Link\n'
        '            href="/"\n'
        '            style={{\n'
        '              display: "inline-flex",\n'
        '              alignItems: "center",\n'
        '              gap: 8,\n'
        '              textDecoration: "none",\n'
        '              flexShrink: 0,\n'
        '            }}\n'
        '          >\n'
        '            <span\n'
        '              style={{\n'
        '                display: "inline-flex",\n'
        '                alignItems: "center",\n'
        '                justifyContent: "center",\n'
        '                width: 28,\n'
        '                height: 28,\n'
        '                borderRadius: 6,\n'
        '                background: "linear-gradient(135deg, #2563eb, #1d4ed8)",\n'
        '                color: "#ffffff",\n'
        '                fontWeight: 700,\n'
        '                fontSize: 14,\n'
        '              }}\n'
        '            >\n'
        f'              {brand_initial}\n'
        '            </span>\n'
        '            <span\n'
        '              style={{\n'
        '                fontWeight: 700,\n'
        '                fontSize: 15,\n'
        '                color: "#0f172a",\n'
        '                letterSpacing: "-0.01em",\n'
        '              }}\n'
        '            >\n'
        f'              {escaped_name}\n'
        '            </span>\n'
        '          </Link>\n\n'
        '          <nav\n'
        '            role="navigation"\n'
        '            aria-label="Main Navigation"\n'
        '            style={{\n'
        '              display: "flex",\n'
        '              alignItems: "center",\n'
        '              gap: 4,\n'
        '              overflowX: "auto",\n'
        '            }}\n'
        '          >\n'
        f'{nav_links_str}\n'
        '          </nav>\n'
        '        </div>\n\n'
        f'{actions_jsx}'
        '      </div>\n'
        '      <ShortcutsDialog isOpen={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />\n'
        '    </header>\n'
        '  );\n'
        '}\n'
    )


_TOAST_COMPONENT = (
    '"use client";\n\n'
    'import React, { createContext, useContext, useState, useCallback, useEffect } from "react";\n\n'
    'export type ToastType = "success" | "error" | "info";\n\n'
    'export interface ToastItem {\n'
    '  id: string;\n'
    '  message: string;\n'
    '  type: ToastType;\n'
    '  duration?: number;\n'
    '}\n\n'
    'export interface ToastContextValue {\n'
    '  toasts: ToastItem[];\n'
    '  addToast: (message: string, type?: ToastType, duration?: number) => void;\n'
    '  removeToast: (id: string) => void;\n'
    '  toast: {\n'
    '    success: (message: string, duration?: number) => void;\n'
    '    error: (message: string, duration?: number) => void;\n'
    '    info: (message: string, duration?: number) => void;\n'
    '  };\n'
    '}\n\n'
    'const ToastContext = createContext<ToastContextValue | null>(null);\n\n'
    'function ToastCard({\n'
    '  item,\n'
    '  onDismiss,\n'
    '}: {\n'
    '  item: ToastItem;\n'
    '  onDismiss: (id: string) => void;\n'
    '}) {\n'
    '  const duration = item.duration ?? 4000;\n\n'
    '  useEffect(() => {\n'
    '    if (duration <= 0) return;\n'
    '    const timer = setTimeout(() => {\n'
    '      onDismiss(item.id);\n'
    '    }, duration);\n'
    '    return () => clearTimeout(timer);\n'
    '  }, [item.id, duration, onDismiss]);\n\n'
    '  const typeStyles: Record<\n'
    '    ToastType,\n'
    '    { border: string; bg: string; badgeBg: string; badgeColor: string; icon: string }\n'
    '  > = {\n'
    '    success: {\n'
    '      border: "1px solid #a7f3d0",\n'
    '      bg: "#f0fdf4",\n'
    '      badgeBg: "#dcfce7",\n'
    '      badgeColor: "#15803d",\n'
    '      icon: "✓",\n'
    '    },\n'
    '    error: {\n'
    '      border: "1px solid #fecaca",\n'
    '      bg: "#fef2f2",\n'
    '      badgeBg: "#fee2e2",\n'
    '      badgeColor: "#b91c1c",\n'
    '      icon: "✕",\n'
    '    },\n'
    '    info: {\n'
    '      border: "1px solid #bfdbfe",\n'
    '      bg: "#eff6ff",\n'
    '      badgeBg: "#dbeafe",\n'
    '      badgeColor: "#1d4ed8",\n'
    '      icon: "ℹ",\n'
    '    },\n'
    '  };\n\n'
    '  const style = typeStyles[item.type] || typeStyles.info;\n\n'
    '  return (\n'
    '    <div\n'
    '      role="status"\n'
    '      style={{\n'
    '        pointerEvents: "auto",\n'
    '        display: "flex",\n'
    '        alignItems: "center",\n'
    '        justifyContent: "space-between",\n'
    '        gap: 12,\n'
    '        padding: "10px 14px",\n'
    '        background: style.bg,\n'
    '        border: style.border,\n'
    '        borderRadius: 8,\n'
    '        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",\n'
    '        color: "#0f172a",\n'
    '        fontSize: 13,\n'
    '        fontWeight: 500,\n'
    '        lineHeight: 1.4,\n'
    '      }}\n'
    '    >\n'
    '      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>\n'
    '        <span\n'
    '          style={{\n'
    '            display: "inline-flex",\n'
    '            alignItems: "center",\n'
    '            justifyContent: "center",\n'
    '            width: 20,\n'
    '            height: 20,\n'
    '            borderRadius: "50%",\n'
    '            background: style.badgeBg,\n'
    '            color: style.badgeColor,\n'
    '            fontSize: 11,\n'
    '            fontWeight: 700,\n'
    '            flexShrink: 0,\n'
    '          }}\n'
    '        >\n'
    '          {style.icon}\n'
    '        </span>\n'
    '        <span>{item.message}</span>\n'
    '      </div>\n'
    '      <button\n'
    '        type="button"\n'
    '        onClick={() => onDismiss(item.id)}\n'
    '        aria-label="Dismiss notification"\n'
    '        style={{\n'
    '          border: "none",\n'
    '          background: "transparent",\n'
    '          color: "#94a3b8",\n'
    '          cursor: "pointer",\n'
    '          padding: 2,\n'
    '          display: "inline-flex",\n'
    '          alignItems: "center",\n'
    '          justifyContent: "center",\n'
    '          fontSize: 16,\n'
    '          lineHeight: 1,\n'
    '        }}\n'
    '      >\n'
    '        &times;\n'
    '      </button>\n'
    '    </div>\n'
    '  );\n'
    '}\n\n'
    'export function ToastProvider({ children }: { children: React.ReactNode }) {\n'
    '  const [toasts, setToasts] = useState<ToastItem[]>([]);\n\n'
    '  const removeToast = useCallback((id: string) => {\n'
    '    setToasts((prev) => prev.filter((t) => t.id !== id));\n'
    '  }, []);\n\n'
    '  const addToast = useCallback(\n'
    '    (message: string, type: ToastType = "info", duration = 4000) => {\n'
    '      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;\n'
    '      setToasts((prev) => [...prev, { id, message, type, duration }]);\n'
    '    },\n'
    '    []\n'
    '  );\n\n'
    '  const toast = {\n'
    '    success: useCallback(\n'
    '      (message: string, duration?: number) => addToast(message, "success", duration),\n'
    '      [addToast]\n'
    '    ),\n'
    '    error: useCallback(\n'
    '      (message: string, duration?: number) => addToast(message, "error", duration),\n'
    '      [addToast]\n'
    '    ),\n'
    '    info: useCallback(\n'
    '      (message: string, duration?: number) => addToast(message, "info", duration),\n'
    '      [addToast]\n'
    '    ),\n'
    '  };\n\n'
    '  return (\n'
    '    <ToastContext.Provider value={{ toasts, addToast, removeToast, toast }}>\n'
    '      {children}\n'
    '      <div\n'
    '        aria-live="polite"\n'
    '        style={{\n'
    '          position: "fixed",\n'
    '          bottom: 24,\n'
    '          right: 24,\n'
    '          zIndex: 9999,\n'
    '          display: "flex",\n'
    '          flexDirection: "column",\n'
    '          gap: 8,\n'
    '          pointerEvents: "none",\n'
    '          maxWidth: 420,\n'
    '          width: "calc(100% - 48px)",\n'
    '        }}\n'
    '      >\n'
    '        {toasts.map((t) => (\n'
    '          <ToastCard key={t.id} item={t} onDismiss={removeToast} />\n'
    '        ))}\n'
    '      </div>\n'
    '    </ToastContext.Provider>\n'
    '  );\n'
    '}\n\n'
    'export function useToast(): ToastContextValue {\n'
    '  const ctx = useContext(ToastContext);\n'
    '  if (!ctx) {\n'
    '    return {\n'
    '      toasts: [],\n'
    '      addToast: () => {},\n'
    '      removeToast: () => {},\n'
    '      toast: {\n'
    '        success: () => {},\n'
    '        error: () => {},\n'
    '        info: () => {},\n'
    '      },\n'
    '    };\n'
    '  }\n'
    '  return ctx;\n'
    '}\n'
)


def render_toast_component() -> str:
    """Return the static TypeScript implementation of the ToastProvider and useToast hook."""
    return _TOAST_COMPONENT


# --- Accessible ConfirmDialog modal component (R-304) -------------------------------------------
# Static, inline-styled, dependency-free, ARIA-compliant replacement for window.confirm().
# Never references ir.name/ir.description; always emitted as components/confirm-dialog.tsx.

_CONFIRM_DIALOG_COMPONENT = (
    '"use client";\n\n'
    'import { useCallback, useEffect, useRef, useState } from "react";\n\n'
    '// R-304: Accessible modal confirmation dialog replacing window.confirm().\n'
    '// useConfirm returns confirmAsync(title, message) -> Promise<boolean>.\n'
    '// Render <ConfirmDialog {...confirmProps} /> once at the bottom of any page that calls confirmAsync().\n\n'
    'export interface ConfirmDialogProps {\n'
    '  isOpen: boolean;\n'
    '  title: string;\n'
    '  message: string;\n'
    '  onConfirm: () => void;\n'
    '  onCancel: () => void;\n'
    '}\n\n'
    'export function ConfirmDialog({ isOpen, title, message, onConfirm, onCancel }: ConfirmDialogProps) {\n'
    '  const confirmBtnRef = useRef<HTMLButtonElement>(null);\n\n'
    '  // Focus the Confirm button when the dialog opens.\n'
    '  useEffect(() => {\n'
    '    if (isOpen) {\n'
    '      setTimeout(() => confirmBtnRef.current?.focus(), 0);\n'
    '    }\n'
    '  }, [isOpen]);\n\n'
    '  // Dismiss on Escape key.\n'
    '  useEffect(() => {\n'
    '    if (!isOpen) return;\n'
    '    const handleKeyDown = (e: KeyboardEvent) => {\n'
    '      if (e.key === "Escape") {\n'
    '        e.preventDefault();\n'
    '        onCancel();\n'
    '      }\n'
    '    };\n'
    '    window.addEventListener("keydown", handleKeyDown);\n'
    '    return () => window.removeEventListener("keydown", handleKeyDown);\n'
    '  }, [isOpen, onCancel]);\n\n'
    '  if (!isOpen) return null;\n\n'
    '  return (\n'
    '    <>\n'
    '      {/* Backdrop overlay */}\n'
    '      <div\n'
    '        aria-hidden="true"\n'
    '        onClick={onCancel}\n'
    '        style={{\n'
    '          position: "fixed",\n'
    '          inset: 0,\n'
    '          background: "rgba(15, 23, 42, 0.45)",\n'
    '          zIndex: 1000,\n'
    '        }}\n'
    '      />\n'
    '      {/* Dialog panel */}\n'
    '      <div\n'
    '        role="dialog"\n'
    '        aria-modal="true"\n'
    '        aria-labelledby="confirm-dialog-title"\n'
    '        aria-describedby="confirm-dialog-message"\n'
    '        style={{\n'
    '          position: "fixed",\n'
    '          top: "50%",\n'
    '          left: "50%",\n'
    '          transform: "translate(-50%, -50%)",\n'
    '          zIndex: 1001,\n'
    '          background: "#ffffff",\n'
    '          borderRadius: 10,\n'
    '          boxShadow: "0 20px 60px rgba(0, 0, 0, 0.18), 0 4px 16px rgba(0, 0, 0, 0.10)",\n'
    '          padding: "28px 32px",\n'
    '          minWidth: 340,\n'
    '          maxWidth: 480,\n'
    '          width: "calc(100vw - 48px)",\n'
    '        }}\n'
    '      >\n'
    '        <h2\n'
    '          id="confirm-dialog-title"\n'
    '          style={{ margin: "0 0 10px", fontSize: 17, fontWeight: 700, color: "#0f172a" }}\n'
    '        >\n'
    '          {title}\n'
    '        </h2>\n'
    '        <p\n'
    '          id="confirm-dialog-message"\n'
    '          style={{ margin: "0 0 24px", fontSize: 14, color: "#475569", lineHeight: 1.55 }}\n'
    '        >\n'
    '          {message}\n'
    '        </p>\n'
    '        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>\n'
    '          <button\n'
    '            type="button"\n'
    '            onClick={onCancel}\n'
    '            style={{\n'
    '              padding: "8px 18px",\n'
    '              background: "#f8fafc",\n'
    '              color: "#475569",\n'
    '              border: "1px solid #e2e8f0",\n'
    '              borderRadius: 6,\n'
    '              fontSize: 14,\n'
    '              fontWeight: 500,\n'
    '              cursor: "pointer",\n'
    '            }}\n'
    '          >\n'
    '            Cancel\n'
    '          </button>\n'
    '          <button\n'
    '            ref={confirmBtnRef}\n'
    '            type="button"\n'
    '            onClick={onConfirm}\n'
    '            style={{\n'
    '              padding: "8px 18px",\n'
    '              background: "#dc2626",\n'
    '              color: "#ffffff",\n'
    '              border: "none",\n'
    '              borderRadius: 6,\n'
    '              fontSize: 14,\n'
    '              fontWeight: 600,\n'
    '              cursor: "pointer",\n'
    '            }}\n'
    '          >\n'
    '            Confirm\n'
    '          </button>\n'
    '        </div>\n'
    '      </div>\n'
    '    </>\n'
    '  );\n'
    '}\n\n'
    'interface ConfirmState {\n'
    '  isOpen: boolean;\n'
    '  title: string;\n'
    '  message: string;\n'
    '  resolve: ((ok: boolean) => void) | null;\n'
    '}\n\n'
    'const _initial: ConfirmState = { isOpen: false, title: "", message: "", resolve: null };\n\n'
    'export function useConfirm() {\n'
    '  const [state, setState] = useState<ConfirmState>(_initial);\n\n'
    '  const confirmAsync = useCallback((title: string, message: string): Promise<boolean> => {\n'
    '    return new Promise<boolean>((resolve) => {\n'
    '      setState({ isOpen: true, title, message, resolve });\n'
    '    });\n'
    '  }, []);\n\n'
    '  const handleConfirm = useCallback(() => {\n'
    '    state.resolve?.(true);\n'
    '    setState(_initial);\n'
    '  }, [state]);\n\n'
    '  const handleCancel = useCallback(() => {\n'
    '    state.resolve?.(false);\n'
    '    setState(_initial);\n'
    '  }, [state]);\n\n'
    '  const confirmProps: ConfirmDialogProps = {\n'
    '    isOpen: state.isOpen,\n'
    '    title: state.title,\n'
    '    message: state.message,\n'
    '    onConfirm: handleConfirm,\n'
    '    onCancel: handleCancel,\n'
    '  };\n\n'
    '  return { confirmAsync, confirmProps };\n'
    '}\n'
)


def render_confirm_dialog_component() -> str:
    """Return the static TypeScript implementation of the ConfirmDialog component and useConfirm hook."""
    return _CONFIRM_DIALOG_COMPONENT


# --- Reusable keyboard shortcuts dialog (R-305) --------------------------------------------------
# Static, inline-styled, dependency-free modal cheat sheet for power-user keyboard navigation.

_SHORTCUTS_DIALOG_COMPONENT = (
    '"use client";\n\n'
    'import React, { useEffect } from "react";\n\n'
    'export interface ShortcutsDialogProps {\n'
    '  isOpen: boolean;\n'
    '  onClose: () => void;\n'
    '}\n\n'
    'export interface ShortcutItem {\n'
    '  keys: string[];\n'
    '  description: string;\n'
    '}\n\n'
    'export interface ShortcutGroup {\n'
    '  title: string;\n'
    '  items: ShortcutItem[];\n'
    '}\n\n'
    'export const SHORTCUT_GROUPS: ShortcutGroup[] = [\n'
    '  {\n'
    '    title: "Global Navigation",\n'
    '    items: [\n'
    '      { keys: ["?"], description: "Show / hide keyboard shortcuts guide" },\n'
    '      { keys: ["Esc"], description: "Close modal / dismiss / clear" },\n'
    '    ],\n'
    '  },\n'
    '  {\n'
    '    title: "Collection Screens",\n'
    '    items: [\n'
    '      { keys: ["/"], description: "Focus search input" },\n'
    '      { keys: ["Esc"], description: "Clear active search or filter criteria" },\n'
    '    ],\n'
    '  },\n'
    '  {\n'
    '    title: "Record Detail Screens",\n'
    '    items: [\n'
    '      { keys: ["[", "]"], description: "Navigate to previous / next record" },\n'
    '      { keys: ["\\u2190", "\\u2192"], description: "Navigate previous / next (arrow keys)" },\n'
    '      { keys: ["e"], description: "Edit current record in form" },\n'
    '      { keys: ["Esc"], description: "Deselect active record" },\n'
    '    ],\n'
    '  },\n'
    '  {\n'
    '    title: "Form Editor Screens",\n'
    '    items: [\n'
    '      { keys: ["\\u2318+Enter", "Ctrl+Enter"], description: "Submit / save form" },\n'
    '      { keys: ["\\u2318+S", "Ctrl+S"], description: "Save form changes" },\n'
    '      { keys: ["Esc"], description: "Blur active input or discard changes" },\n'
    '    ],\n'
    '  },\n'
    '];\n\n'
    'export function ShortcutsDialog({ isOpen, onClose }: ShortcutsDialogProps) {\n'
    '  useEffect(() => {\n'
    '    if (!isOpen) return;\n\n'
    '    const handleKeyDown = (e: KeyboardEvent) => {\n'
    '      if (e.key === "Escape") {\n'
    '        e.stopPropagation();\n'
    '        onClose();\n'
    '      }\n'
    '    };\n\n'
    '    window.addEventListener("keydown", handleKeyDown);\n'
    '    return () => window.removeEventListener("keydown", handleKeyDown);\n'
    '  }, [isOpen, onClose]);\n\n'
    '  if (!isOpen) return null;\n\n'
    '  return (\n'
    '    <div\n'
    '      role="dialog"\n'
    '      aria-modal="true"\n'
    '      aria-labelledby="shortcuts-dialog-title"\n'
    '      onClick={onClose}\n'
    '      style={{\n'
    '        position: "fixed",\n'
    '        inset: 0,\n'
    '        background: "rgba(15, 23, 42, 0.6)",\n'
    '        backdropFilter: "blur(2px)",\n'
    '        zIndex: 9999,\n'
    '        display: "flex",\n'
    '        alignItems: "center",\n'
    '        justifyContent: "center",\n'
    '        padding: 16,\n'
    '      }}\n'
    '    >\n'
    '      <div\n'
    '        onClick={(e) => e.stopPropagation()}\n'
    '        style={{\n'
    '          background: "#ffffff",\n'
    '          borderRadius: 12,\n'
    '          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",\n'
    '          border: "1px solid #e2e8f0",\n'
    '          width: "100%",\n'
    '          maxWidth: 560,\n'
    '          maxHeight: "85vh",\n'
    '          overflowY: "auto",\n'
    '          padding: 24,\n'
    '          boxSizing: "border-box",\n'
    '        }}\n'
    '      >\n'
    '        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20, borderBottom: "1px solid #f1f5f9", paddingBottom: 12 }}>\n'
    '          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>\n'
    '            <span style={{ fontSize: 18 }}>&#x2328;</span>\n'
    '            <h2 id="shortcuts-dialog-title" style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#0f172a" }}>\n'
    '              Keyboard Shortcuts\n'
    '            </h2>\n'
    '          </div>\n'
    '          <button\n'
    '            type="button"\n'
    '            onClick={onClose}\n'
    '            aria-label="Close shortcuts dialog"\n'
    '            style={{\n'
    '              background: "transparent",\n'
    '              border: "none",\n'
    '              color: "#64748b",\n'
    '              cursor: "pointer",\n'
    '              fontSize: 20,\n'
    '              lineHeight: 1,\n'
    '              padding: "4px 8px",\n'
    '              borderRadius: 4,\n'
    '            }}\n'
    '          >\n'
    '            &times;\n'
    '          </button>\n'
    '        </div>\n\n'
    '        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>\n'
    '          {SHORTCUT_GROUPS.map((group) => (\n'
    '            <div key={group.title}>\n'
    '              <h3 style={{ margin: "0 0 10px 0", fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b" }}>\n'
    '                {group.title}\n'
    '              </h3>\n'
    '              <div style={{ display: "flex", flexDirection: "column", gap: 8, background: "#f8fafc", padding: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}>\n'
    '                {group.items.map((item, idx) => (\n'
    '                  <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>\n'
    '                    <span style={{ fontSize: 13, color: "#334155" }}>{item.description}</span>\n'
    '                    <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>\n'
    '                      {item.keys.map((k, kIdx) => (\n'
    '                        <kbd\n'
    '                          key={kIdx}\n'
    '                          style={{\n'
    '                            display: "inline-block",\n'
    '                            padding: "2px 6px",\n'
    '                            fontSize: 11,\n'
    '                            fontWeight: 600,\n'
    '                            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",\n'
    '                            color: "#0f172a",\n'
    '                            background: "#ffffff",\n'
    '                            border: "1px solid #cbd5e1",\n'
    '                            borderRadius: 4,\n'
    '                            boxShadow: "0 1px 0 rgba(0,0,0,0.06)",\n'
    '                          }}\n'
    '                        >\n'
    '                          {k}\n'
    '                        </kbd>\n'
    '                      ))}\n'
    '                    </div>\n'
    '                  </div>\n'
    '                ))}\n'
    '              </div>\n'
    '            </div>\n'
    '          ))}\n'
    '        </div>\n\n'
    '        <div style={{ marginTop: 20, paddingTop: 12, borderTop: "1px solid #f1f5f9", display: "flex", justifyContent: "flex-end" }}>\n'
    '          <button\n'
    '            type="button"\n'
    '            onClick={onClose}\n'
    '            style={{\n'
    '              padding: "6px 14px",\n'
    '              background: "#2563eb",\n'
    '              color: "#ffffff",\n'
    '              border: "none",\n'
    '              borderRadius: 6,\n'
    '              fontSize: 13,\n'
    '              fontWeight: 500,\n'
    '              cursor: "pointer",\n'
    '            }}\n'
    '          >\n'
    '            Got it\n'
    '          </button>\n'
    '        </div>\n'
    '      </div>\n'
    '    </div>\n'
    '  );\n'
    '}\n'
)


def render_shortcuts_dialog_component() -> str:
    """Return the static TypeScript implementation of the ShortcutsDialog component."""
    return _SHORTCUTS_DIALOG_COMPONENT


# --- Breadcrumbs navigation component (R-306) --------------------------------------------------
# Reusable, accessible breadcrumbs trail conforming to WAI-ARIA 1.2 breadcrumb design pattern.
# Emits <nav aria-label="Breadcrumb">, <ol>, <li>, separator (/), and aria-current="page".
# Purely static and 100% diff-invariant across ir.description.

_BREADCRUMBS_COMPONENT = (
    '"use client";\n\n'
    'import React from "react";\n'
    'import Link from "next/link";\n\n'
    "export interface BreadcrumbItem {\n"
    "  label: string;\n"
    "  href?: string;\n"
    "}\n\n"
    "export interface BreadcrumbsProps {\n"
    "  items: BreadcrumbItem[];\n"
    "}\n\n"
    "export function Breadcrumbs({ items }: BreadcrumbsProps) {\n"
    "  if (!items || items.length === 0) return null;\n\n"
    "  return (\n"
    '    <nav aria-label="Breadcrumb" style={{ marginBottom: 16 }}>\n'
    "      <ol\n"
    "        style={{\n"
    '          display: "flex",\n'
    '          alignItems: "center",\n'
    '          flexWrap: "wrap",\n'
    '          listStyle: "none",\n'
    "          margin: 0,\n"
    "          padding: 0,\n"
    "          fontSize: 13,\n"
    "        }}\n"
    "      >\n"
    "        {items.map((item, index) => {\n"
    "          const isLast = index === items.length - 1;\n"
    "          return (\n"
    "            <li\n"
    "              key={index}\n"
    "              style={{\n"
    '                display: "inline-flex",\n'
    '                alignItems: "center",\n'
    "              }}\n"
    "            >\n"
    "              {index > 0 && (\n"
    "                <span\n"
    '                  aria-hidden="true"\n'
    "                  style={{\n"
    '                    margin: "0 8px",\n'
    '                    color: "#94a3b8",\n'
    '                    userSelect: "none",\n'
    "                  }}\n"
    "                >\n"
    "                  /\n"
    "                </span>\n"
    "              )}\n"
    "              {isLast || !item.href ? (\n"
    "                <span\n"
    '                  aria-current={isLast ? "page" : undefined}\n'
    "                  style={{\n"
    '                    color: isLast ? "#0f172a" : "#64748b",\n'
    "                    fontWeight: isLast ? 600 : 400,\n"
    "                  }}\n"
    "                >\n"
    "                  {item.label}\n"
    "                </span>\n"
    "              ) : (\n"
    "                <Link\n"
    "                  href={item.href}\n"
    "                  style={{\n"
    '                    color: "#64748b",\n'
    '                    textDecoration: "none",\n'
    "                    fontWeight: 500,\n"
    '                    transition: "color 0.15s ease",\n'
    "                  }}\n"
    "                >\n"
    "                  {item.label}\n"
    "                </Link>\n"
    "              )}\n"
    "            </li>\n"
    "          );\n"
    "        })}\n"
    "      </ol>\n"
    "    </nav>\n"
    "  );\n"
    "}\n"
)


def render_breadcrumbs_component() -> str:
    """Return the static TypeScript implementation of the Breadcrumbs component."""
    return _BREADCRUMBS_COMPONENT


# --- Reusable accessible empty state component (R-307) -------------------------------------------
# Static, inline-styled, zero-dependency zero-state illustration and action card.
# Conforms to WAI-ARIA with role="status" and aria-live="polite".
# Never references ir.name/ir.description to guarantee diff invariance.

_EMPTY_STATE_COMPONENT = (
    '"use client";\n\n'
    'import React from "react";\n'
    'import Link from "next/link";\n\n'
    "export interface EmptyStateAction {\n"
    "  label: string;\n"
    "  href?: string;\n"
    "  onClick?: () => void;\n"
    "}\n\n"
    "export interface EmptyStateProps {\n"
    "  title: string;\n"
    "  description?: string;\n"
    '  icon?: "folder" | "search" | "document" | "inbox" | React.ReactNode;\n'
    "  action?: EmptyStateAction;\n"
    "  secondaryAction?: EmptyStateAction;\n"
    "  style?: React.CSSProperties;\n"
    "  className?: string;\n"
    "}\n\n"
    "function renderIcon(icon: EmptyStateProps[\"icon\"]) {\n"
    '  if (!icon || icon === "folder") {\n'
    "    return (\n"
    "      <svg\n"
    '        aria-hidden="true"\n'
    '        width="48"\n'
    '        height="48"\n'
    '        viewBox="0 0 24 24"\n'
    '        fill="none"\n'
    '        stroke="#94a3b8"\n'
    '        strokeWidth="1.5"\n'
    '        strokeLinecap="round"\n'
    '        strokeLinejoin="round"\n'
    "      >\n"
    '        <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />\n'
    "      </svg>\n"
    "    );\n"
    "  }\n"
    '  if (icon === "search") {\n'
    "    return (\n"
    "      <svg\n"
    '        aria-hidden="true"\n'
    '        width="48"\n'
    '        height="48"\n'
    '        viewBox="0 0 24 24"\n'
    '        fill="none"\n'
    '        stroke="#94a3b8"\n'
    '        strokeWidth="1.5"\n'
    '        strokeLinecap="round"\n'
    '        strokeLinejoin="round"\n'
    "      >\n"
    '        <circle cx="11" cy="11" r="8" />\n'
    '        <path d="m21 21-4.3-4.3" />\n'
    "      </svg>\n"
    "    );\n"
    "  }\n"
    '  if (icon === "document") {\n'
    "    return (\n"
    "      <svg\n"
    '        aria-hidden="true"\n'
    '        width="48"\n'
    '        height="48"\n'
    '        viewBox="0 0 24 24"\n'
    '        fill="none"\n'
    '        stroke="#94a3b8"\n'
    '        strokeWidth="1.5"\n'
    '        strokeLinecap="round"\n'
    '        strokeLinejoin="round"\n'
    "      >\n"
    '        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />\n'
    '        <polyline points="14 2 14 8 20 8" />\n'
    '        <line x1="16" x2="8" y1="13" y2="13" />\n'
    '        <line x1="16" x2="8" y1="17" y2="17" />\n'
    '        <line x1="10" x2="8" y1="9" y2="9" />\n'
    "      </svg>\n"
    "    );\n"
    "  }\n"
    '  if (icon === "inbox") {\n'
    "    return (\n"
    "      <svg\n"
    '        aria-hidden="true"\n'
    '        width="48"\n'
    '        height="48"\n'
    '        viewBox="0 0 24 24"\n'
    '        fill="none"\n'
    '        stroke="#94a3b8"\n'
    '        strokeWidth="1.5"\n'
    '        strokeLinecap="round"\n'
    '        strokeLinejoin="round"\n'
    "      >\n"
    '        <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />\n'
    '        <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />\n'
    "      </svg>\n"
    "    );\n"
    "  }\n"
    "  return <span aria-hidden=\"true\">{icon}</span>;\n"
    "}\n\n"
    "export function EmptyState({\n"
    "  title,\n"
    "  description,\n"
    '  icon = "folder",\n'
    "  action,\n"
    "  secondaryAction,\n"
    "  style,\n"
    "  className,\n"
    "}: EmptyStateProps) {\n"
    "  return (\n"
    "    <div\n"
    '      role="status"\n'
    '      aria-live="polite"\n'
    "      className={className}\n"
    "      style={{\n"
    '        display: "flex",\n'
    '        flexDirection: "column",\n'
    '        alignItems: "center",\n'
    '        justifyContent: "center",\n'
    '        textAlign: "center",\n'
    '        padding: "40px 24px",\n'
    '        background: "#ffffff",\n'
    '        border: "1px dashed #cbd5e1",\n'
    "        borderRadius: 12,\n"
    "        maxWidth: 520,\n"
    '        margin: "24px auto",\n'
    "        boxSizing: \"border-box\",\n"
    "        ...style,\n"
    "      }}\n"
    "    >\n"
    '      <div style={{ marginBottom: 16 }}>{renderIcon(icon)}</div>\n'
    '      <h3 style={{ fontSize: 16, fontWeight: 600, color: "#0f172a", margin: "0 0 8px" }}>\n'
    "        {title}\n"
    "      </h3>\n"
    "      {description && (\n"
    '        <p style={{ fontSize: 14, color: "#64748b", margin: "0 0 20px", maxWidth: 400, lineHeight: 1.5 }}>\n'
    "          {description}\n"
    "        </p>\n"
    "      )}\n"
    "      {(action || secondaryAction) && (\n"
    '        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", justifyContent: "center", marginTop: description ? 0 : 16 }}>\n'
    "          {action && (\n"
    "            action.href ? (\n"
    "              <Link\n"
    "                href={action.href}\n"
    "                style={{\n"
    '                  display: "inline-flex",\n'
    '                  alignItems: "center",\n'
    '                  padding: "8px 16px",\n'
    '                  background: "#2563eb",\n'
    '                  color: "#ffffff",\n'
    "                  borderRadius: 6,\n"
    "                  fontSize: 13,\n"
    "                  fontWeight: 500,\n"
    '                  textDecoration: "none",\n'
    '                  transition: "background 0.15s ease",\n'
    "                }}\n"
    "              >\n"
    "                {action.label}\n"
    "              </Link>\n"
    "            ) : (\n"
    "              <button\n"
    '                type="button"\n'
    "                onClick={action.onClick}\n"
    "                style={{\n"
    '                  padding: "8px 16px",\n'
    '                  background: "#2563eb",\n'
    '                  color: "#ffffff",\n'
    '                  border: "none",\n'
    "                  borderRadius: 6,\n"
    "                  fontSize: 13,\n"
    "                  fontWeight: 500,\n"
    '                  cursor: "pointer",\n'
    "                }}\n"
    "              >\n"
    "                {action.label}\n"
    "              </button>\n"
    "            )\n"
    "          )}\n"
    "          {secondaryAction && (\n"
    "            secondaryAction.href ? (\n"
    "              <Link\n"
    "                href={secondaryAction.href}\n"
    "                style={{\n"
    '                  display: "inline-flex",\n'
    '                  alignItems: "center",\n'
    '                  padding: "8px 16px",\n'
    '                  background: "#ffffff",\n'
    '                  color: "#475569",\n'
    '                  border: "1px solid #cbd5e1",\n'
    "                  borderRadius: 6,\n"
    "                  fontSize: 13,\n"
    "                  fontWeight: 500,\n"
    '                  textDecoration: "none",\n'
    "                }}\n"
    "              >\n"
    "                {secondaryAction.label}\n"
    "              </Link>\n"
    "            ) : (\n"
    "              <button\n"
    '                type="button"\n'
    "                onClick={secondaryAction.onClick}\n"
    "                style={{\n"
    '                  padding: "8px 16px",\n'
    '                  background: "#ffffff",\n'
    '                  color: "#475569",\n'
    '                  border: "1px solid #cbd5e1",\n'
    "                  borderRadius: 6,\n"
    "                  fontSize: 13,\n"
    "                  fontWeight: 500,\n"
    '                  cursor: "pointer",\n'
    "                }}\n"
    "              >\n"
    "                {secondaryAction.label}\n"
    "              </button>\n"
    "            )\n"
    "          )}\n"
    "        </div>\n"
    "      )}\n"
    "    </div>\n"
    "  );\n"
    "}\n"
)


def render_empty_state_component() -> str:
    """Return the static TypeScript implementation of the EmptyState component."""
    return _EMPTY_STATE_COMPONENT


_PAGINATION_COMPONENT = (
    '"use client";\n\n'
    'import React from "react";\n\n'
    "export interface PaginationProps {\n"
    "  page: number;\n"
    "  pageSize: number;\n"
    "  total: number;\n"
    "  totalPages: number;\n"
    "  onPageChange: (page: number) => void;\n"
    "  onPageSizeChange?: (pageSize: number) => void;\n"
    "  pageSizeOptions?: number[];\n"
    "  disabled?: boolean;\n"
    "  compact?: boolean;\n"
    "  itemLabel?: string;\n"
    "}\n\n"
    'function getPageNumbers(currentPage: number, totalPages: number): (number | "ellipsis")[] {\n'
    "  if (totalPages <= 7) {\n"
    "    return Array.from({ length: totalPages }, (_, i) => i + 1);\n"
    "  }\n"
    '  const pages: (number | "ellipsis")[] = [1];\n'
    "  if (currentPage > 3) {\n"
    '    pages.push("ellipsis");\n'
    "  }\n"
    "  const start = Math.max(2, currentPage - 1);\n"
    "  const end = Math.min(totalPages - 1, currentPage + 1);\n"
    "  for (let i = start; i <= end; i++) {\n"
    "    pages.push(i);\n"
    "  }\n"
    "  if (currentPage < totalPages - 2) {\n"
    '    pages.push("ellipsis");\n'
    "  }\n"
    "  pages.push(totalPages);\n"
    "  return pages;\n"
    "}\n\n"
    "export function Pagination({\n"
    "  page,\n"
    "  pageSize,\n"
    "  total,\n"
    "  totalPages,\n"
    "  onPageChange,\n"
    "  onPageSizeChange,\n"
    "  pageSizeOptions = [10, 25, 50, 100],\n"
    "  disabled = false,\n"
    "  compact = false,\n"
    "  itemLabel,\n"
    "}: PaginationProps) {\n"
    "  const pageNumbers = !compact && totalPages > 1 ? getPageNumbers(page, totalPages) : [];\n\n"
    "  return (\n"
    '    <nav aria-label="Pagination"\n'
    "      style={{\n"
    '        display: "flex",\n'
    '        justifyContent: "space-between",\n'
    '        alignItems: "center",\n'
    '        flexWrap: "wrap",\n'
    "        gap: 12,\n"
    '        padding: "12px 0",\n'
    "      }}\n"
    "    >\n"
    '      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>\n'
    '        <span style={{ fontSize: 13, color: "#64748b" }}>\n'
    '          Page {page} of {Math.max(1, totalPages)} ({total} {itemLabel || "total"})\n'
    "        </span>\n"
    "        {onPageSizeChange && !compact && (\n"
    '          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>\n'
    '            <label htmlFor="pageSizeSelect" style={{ fontSize: 13, color: "#64748b" }}>\n'
    "              Per page:\n"
    "            </label>\n"
    "            <select\n"
    '              id="pageSizeSelect"\n'
    '              aria-label="Select page size"\n'
    "              value={pageSize}\n"
    "              onChange={(e) => onPageSizeChange(Number(e.target.value))}\n"
    "              disabled={disabled}\n"
    "              style={{\n"
    '                padding: "4px 8px",\n'
    '                border: "1px solid #cbd5e1",\n'
    "                borderRadius: 6,\n"
    '                background: "#fff",\n'
    "                fontSize: 13,\n"
    '                color: "#334155",\n'
    '                cursor: disabled ? "not-allowed" : "pointer",\n'
    '                outline: "none",\n'
    "              }}\n"
    "            >\n"
    "              {pageSizeOptions.map((opt) => (\n"
    "                <option key={opt} value={opt}>\n"
    "                  {opt} per page\n"
    "                </option>\n"
    "              ))}\n"
    "            </select>\n"
    "          </div>\n"
    "        )}\n"
    "      </div>\n\n"
    '      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>\n'
    "        <button\n"
    '          type="button"\n'
    "          onClick={() => onPageChange(page - 1)}\n"
    "          disabled={page <= 1 || disabled}\n"
    '          aria-label="Previous page"\n'
    "          style={{\n"
    '            padding: compact ? "4px 8px" : "6px 12px",\n'
    '            border: "1px solid #cbd5e1",\n'
    "            borderRadius: 6,\n"
    '            background: page <= 1 || disabled ? "#f1f5f9" : "#fff",\n'
    '            color: page <= 1 || disabled ? "#94a3b8" : "#0f172a",\n'
    "            fontSize: compact ? 12 : 13,\n"
    "            fontWeight: 500,\n"
    '            cursor: page <= 1 || disabled ? "not-allowed" : "pointer",\n'
    '            transition: "all 0.15s ease",\n'
    "          }}\n"
    "        >\n"
    "          Previous\n"
    "        </button>\n\n"
    "        {!compact &&\n"
    "          pageNumbers.map((p, idx) => {\n"
    '            if (p === "ellipsis") {\n'
    "              return (\n"
    "                <span\n"
    '                  key={`ellipsis-${idx}`}\n'
    '                  style={{ padding: "0 4px", color: "#94a3b8", fontSize: 13 }}\n'
    '                  aria-hidden="true"\n'
    "                >\n"
    "                  &hellip;\n"
    "                </span>\n"
    "              );\n"
    "            }\n"
    "            const isCurrent = p === page;\n"
    "            return (\n"
    "              <button\n"
    "                key={p}\n"
    '                type="button"\n'
    "                onClick={() => onPageChange(p)}\n"
    "                disabled={disabled}\n"
    '                aria-label={`Page ${p}`}\n'
    '                aria-current={isCurrent ? "page" : undefined}\n'
    "                style={{\n"
    "                  minWidth: 32,\n"
    "                  height: 32,\n"
    '                  padding: "0 6px",\n'
    '                  border: isCurrent ? "1px solid #2563eb" : "1px solid #cbd5e1",\n'
    "                  borderRadius: 6,\n"
    '                  background: isCurrent ? "#2563eb" : "#fff",\n'
    '                  color: isCurrent ? "#fff" : "#334155",\n'
    "                  fontSize: 13,\n"
    "                  fontWeight: isCurrent ? 600 : 400,\n"
    '                  cursor: disabled ? "not-allowed" : "pointer",\n'
    '                  transition: "all 0.15s ease",\n'
    "                }}\n"
    "              >\n"
    "                {p}\n"
    "              </button>\n"
    "            );\n"
    "          })}\n\n"
    "        <button\n"
    '          type="button"\n'
    "          onClick={() => onPageChange(page + 1)}\n"
    "          disabled={page >= totalPages || disabled}\n"
    '          aria-label="Next page"\n'
    "          style={{\n"
    '            padding: compact ? "4px 8px" : "6px 12px",\n'
    '            border: "1px solid #cbd5e1",\n'
    "            borderRadius: 6,\n"
    '            background: page >= totalPages || disabled ? "#f1f5f9" : "#fff",\n'
    '            color: page >= totalPages || disabled ? "#94a3b8" : "#0f172a",\n'
    "            fontSize: compact ? 12 : 13,\n"
    "            fontWeight: 500,\n"
    '            cursor: page >= totalPages || disabled ? "not-allowed" : "pointer",\n'
    '            transition: "all 0.15s ease",\n'
    "          }}\n"
    "        >\n"
    "          Next\n"
    "        </button>\n"
    "      </div>\n"
    "    </nav>\n"
    "  );\n"
    "}\n"
)


def render_pagination_component() -> str:
    """Return the static TypeScript implementation of the Pagination component."""
    return _PAGINATION_COMPONENT


_TABS_COMPONENT = (
    '"use client";\n\n'
    'import React, { useRef } from "react";\n\n'
    "export interface TabItem {\n"
    "  id: string;\n"
    "  label: string;\n"
    "  count?: number;\n"
    "  disabled?: boolean;\n"
    "}\n\n"
    "export interface TabsProps {\n"
    "  tabs: TabItem[];\n"
    "  activeTab: string;\n"
    "  onChange: (id: string) => void;\n"
    "  ariaLabel?: string;\n"
    '  variant?: "line" | "pills";\n'
    "}\n\n"
    "export interface TabPanelProps {\n"
    "  id: string;\n"
    "  activeTab: string;\n"
    "  children: React.ReactNode;\n"
    "  className?: string;\n"
    "  style?: React.CSSProperties;\n"
    "}\n\n"
    "export function Tabs({\n"
    "  tabs,\n"
    "  activeTab,\n"
    "  onChange,\n"
    '  ariaLabel = "Tabs",\n'
    '  variant = "line",\n'
    "}: TabsProps) {\n"
    "  const tabListRef = useRef<HTMLDivElement>(null);\n\n"
    "  const enabledTabs = tabs.filter((t) => !t.disabled);\n\n"
    "  const handleKeyDown = (e: React.KeyboardEvent) => {\n"
    "    if (enabledTabs.length === 0) return;\n"
    "    const currentIndex = enabledTabs.findIndex((t) => t.id === activeTab);\n"
    "    if (currentIndex === -1) return;\n\n"
    "    let nextIndex = -1;\n"
    '    if (e.key === "ArrowRight") {\n'
    "      e.preventDefault();\n"
    "      nextIndex = (currentIndex + 1) % enabledTabs.length;\n"
    '    } else if (e.key === "ArrowLeft") {\n'
    "      e.preventDefault();\n"
    "      nextIndex = (currentIndex - 1 + enabledTabs.length) % enabledTabs.length;\n"
    '    } else if (e.key === "Home") {\n'
    "      e.preventDefault();\n"
    "      nextIndex = 0;\n"
    '    } else if (e.key === "End") {\n'
    "      e.preventDefault();\n"
    "      nextIndex = enabledTabs.length - 1;\n"
    "    }\n\n"
    "    if (nextIndex !== -1) {\n"
    "      const targetTab = enabledTabs[nextIndex];\n"
    "      onChange(targetTab.id);\n"
    "      const tabElement = tabListRef.current?.querySelector<HTMLButtonElement>(`#tab-${targetTab.id}`);\n"
    "      tabElement?.focus();\n"
    "    }\n"
    "  };\n\n"
    '  const isPills = variant === "pills";\n'
    '  const isLine = !isPills;\n\n'
    "  return (\n"
    "    <div\n"
    "      ref={tabListRef}\n"
    '      role="tablist"\n'
    "      aria-label={ariaLabel}\n"
    "      onKeyDown={handleKeyDown}\n"
    "      style={{\n"
    '        display: "flex",\n'
    "        gap: isLine ? 24 : 8,\n"
    '        borderBottom: isLine ? "1px solid #e2e8f0" : "none",\n'
    '        padding: isLine ? "0 0 2px" : "4px 0",\n'
    '        alignItems: "center",\n'
    '        flexWrap: "wrap",\n'
    "      }}\n"
    "    >\n"
    "      {tabs.map((tab) => {\n"
    "        const isActive = tab.id === activeTab;\n"
    "        return (\n"
    "          <button\n"
    "            key={tab.id}\n"
    '            role="tab"\n'
    "            id={`tab-${tab.id}`}\n"
    "            aria-selected={isActive}\n"
    "            aria-controls={`tabpanel-${tab.id}`}\n"
    "            tabIndex={isActive ? 0 : -1}\n"
    "            disabled={tab.disabled}\n"
    "            onClick={() => !tab.disabled && onChange(tab.id)}\n"
    "            style={{\n"
    '              display: "inline-flex",\n'
    '              alignItems: "center",\n'
    "              gap: 8,\n"
    '              padding: isLine ? "8px 4px" : "6px 14px",\n'
    '              border: "none",\n'
    '              borderBottom: isLine && isActive ? "2px solid #2563eb" : (isLine ? "2px solid transparent" : "none"),\n'
    "              borderRadius: isLine ? 0 : 6,\n"
    '              background: !isLine && isActive ? "#2563eb" : (!isLine ? "#f1f5f9" : "transparent"),\n'
    '              color: isActive ? (isLine ? "#2563eb" : "#ffffff") : (tab.disabled ? "#cbd5e1" : "#64748b"),\n'
    "              fontSize: 14,\n"
    "              fontWeight: isActive ? 600 : 500,\n"
    '              cursor: tab.disabled ? "not-allowed" : "pointer",\n'
    '              transition: "all 0.15s ease",\n'
    '              outline: "none",\n'
    "            }}\n"
    "          >\n"
    "            <span>{tab.label}</span>\n"
    "            {tab.count !== undefined && (\n"
    "              <span\n"
    "                style={{\n"
    "                  fontSize: 11,\n"
    '                  padding: "1px 6px",\n'
    "                  borderRadius: 10,\n"
    "                  fontWeight: 600,\n"
    "                  background: isActive\n"
    '                    ? (isLine ? "#eff6ff" : "rgba(255, 255, 255, 0.25)")\n'
    '                    : "#e2e8f0",\n'
    "                  color: isActive\n"
    '                    ? (isLine ? "#1d4ed8" : "#ffffff")\n'
    '                    : "#475569",\n'
    "                }}\n"
    "              >\n"
    "                {tab.count}\n"
    "              </span>\n"
    "            )}\n"
    "          </button>\n"
    "        );\n"
    "      })}\n"
    "    </div>\n"
    "  );\n"
    "}\n\n"
    "export function TabPanel({\n"
    "  id,\n"
    "  activeTab,\n"
    "  children,\n"
    "  className,\n"
    "  style,\n"
    "}: TabPanelProps) {\n"
    "  return (\n"
    "    <div\n"
    '      role="tabpanel"\n'
    "      id={`tabpanel-${id}`}\n"
    "      aria-labelledby={`tab-${id}`}\n"
    "      tabIndex={0}\n"
    "      hidden={activeTab !== id}\n"
    "      className={className}\n"
    "      style={{\n"
    "        paddingTop: 16,\n"
    '        outline: "none",\n'
    "        ...style,\n"
    "      }}\n"
    "    >\n"
    "      {activeTab === id && children}\n"
    "    </div>\n"
    "  );\n"
    "}\n"
)


def render_tabs_component() -> str:
    """Return the static TypeScript implementation of the Tabs component."""
    return _TABS_COMPONENT


_BADGE_COMPONENT = (
    '"use client";\n\n'
    'import React from "react";\n\n'
    'export type BadgeVariant = "success" | "warning" | "error" | "info" | "neutral";\n'
    'export type BadgeSize = "sm" | "md";\n\n'
    "export interface BadgeProps {\n"
    "  children: React.ReactNode;\n"
    "  variant?: BadgeVariant;\n"
    "  size?: BadgeSize;\n"
    "  dot?: boolean;\n"
    "  pulse?: boolean;\n"
    "  style?: React.CSSProperties;\n"
    "  className?: string;\n"
    "  ariaLabel?: string;\n"
    "}\n\n"
    "const VARIANT_STYLES: Record<BadgeVariant, { bg: string; text: string; border: string; dot: string }> = {\n"
    "  success: {\n"
    '    bg: "#dcfce7",\n'
    '    text: "#166534",\n'
    '    border: "#bbf7d0",\n'
    '    dot: "#22c55e",\n'
    "  },\n"
    "  warning: {\n"
    '    bg: "#fef3c7",\n'
    '    text: "#92400e",\n'
    '    border: "#fde68a",\n'
    '    dot: "#f59e0b",\n'
    "  },\n"
    "  error: {\n"
    '    bg: "#fee2e2",\n'
    '    text: "#991b1b",\n'
    '    border: "#fecaca",\n'
    '    dot: "#ef4444",\n'
    "  },\n"
    "  info: {\n"
    '    bg: "#eff6ff",\n'
    '    text: "#1d4ed8",\n'
    '    border: "#bfdbfe",\n'
    '    dot: "#3b82f6",\n'
    "  },\n"
    "  neutral: {\n"
    '    bg: "#f1f5f9",\n'
    '    text: "#475569",\n'
    '    border: "#e2e8f0",\n'
    '    dot: "#94a3b8",\n'
    "  },\n"
    "};\n\n"
    "export function Badge({\n"
    "  children,\n"
    '  variant = "neutral",\n'
    '  size = "md",\n'
    "  dot = false,\n"
    "  pulse = false,\n"
    "  style,\n"
    "  className,\n"
    "  ariaLabel,\n"
    "}: BadgeProps) {\n"
    "  const config = VARIANT_STYLES[variant] || VARIANT_STYLES.neutral;\n"
    '  const isSm = size === "sm";\n\n'
    "  return (\n"
    "    <span\n"
    '      role="status"\n'
    "      aria-label={ariaLabel}\n"
    "      className={className}\n"
    "      style={{\n"
    '        display: "inline-flex",\n'
    '        alignItems: "center",\n'
    "        gap: isSm ? 4 : 6,\n"
    '        padding: isSm ? "1px 6px" : "2px 8px",\n'
    "        borderRadius: 9999,\n"
    "        fontSize: isSm ? 11 : 12,\n"
    "        fontWeight: 600,\n"
    "        lineHeight: 1.25,\n"
    "        background: config.bg,\n"
    "        color: config.text,\n"
    "        border: `1px solid ${config.border}`,\n"
    '        userSelect: "none",\n'
    "        ...style,\n"
    "      }}\n"
    "    >\n"
    "      {dot && (\n"
    "        <span\n"
    '          aria-hidden="true"\n'
    "          style={{\n"
    "            width: isSm ? 5 : 6,\n"
    "            height: isSm ? 5 : 6,\n"
    '            borderRadius: "50%",\n'
    "            background: config.dot,\n"
    '            display: "inline-block",\n'
    "            flexShrink: 0,\n"
    "            opacity: pulse ? 0.9 : 1,\n"
    "          }}\n"
    "        />\n"
    "      )}\n"
    "      {children}\n"
    "    </span>\n"
    "  );\n"
    "}\n\n"
    "export default Badge;\n"
)


def render_badge_component() -> str:
    """Return the static TypeScript implementation of the Badge component."""
    return _BADGE_COMPONENT


_TOOLTIP_COMPONENT = (
    '"use client";\n\n'
    'import React, { useState, useRef, useEffect, useId } from "react";\n\n'
    'export type TooltipPosition = "top" | "bottom" | "left" | "right";\n\n'
    "export interface TooltipProps {\n"
    "  content: React.ReactNode;\n"
    "  children: React.ReactElement;\n"
    "  position?: TooltipPosition;\n"
    "  delayMs?: number;\n"
    "  className?: string;\n"
    "  style?: React.CSSProperties;\n"
    "}\n\n"
    "export function Tooltip({\n"
    "  content,\n"
    "  children,\n"
    '  position = "top",\n'
    "  delayMs = 200,\n"
    "  className,\n"
    "  style,\n"
    "}: TooltipProps) {\n"
    "  const [visible, setVisible] = useState(false);\n"
    "  const timerRef = useRef<NodeJS.Timeout | null>(null);\n"
    "  const tooltipId = useId();\n\n"
    "  const show = () => {\n"
    "    timerRef.current = setTimeout(() => {\n"
    "      setVisible(true);\n"
    "    }, delayMs);\n"
    "  };\n\n"
    "  const hide = () => {\n"
    "    if (timerRef.current) {\n"
    "      clearTimeout(timerRef.current);\n"
    "      timerRef.current = null;\n"
    "    }\n"
    "    setVisible(false);\n"
    "  };\n\n"
    "  useEffect(() => {\n"
    "    return () => {\n"
    "      if (timerRef.current) {\n"
    "        clearTimeout(timerRef.current);\n"
    "      }\n"
    "    };\n"
    "  }, []);\n\n"
    "  useEffect(() => {\n"
    "    const handleKeyDown = (e: KeyboardEvent) => {\n"
    '      if (e.key === "Escape" && visible) {\n'
    "        hide();\n"
    "      }\n"
    "    };\n"
    '    window.addEventListener("keydown", handleKeyDown);\n'
    '    return () => window.removeEventListener("keydown", handleKeyDown);\n'
    "  }, [visible]);\n\n"
    "  const positionStyles: Record<TooltipPosition, React.CSSProperties> = {\n"
    "    top: {\n"
    '      bottom: "100%",\n'
    '      left: "50%",\n'
    '      transform: "translateX(-50%)",\n'
    "      marginBottom: 6,\n"
    "    },\n"
    "    bottom: {\n"
    '      top: "100%",\n'
    '      left: "50%",\n'
    '      transform: "translateX(-50%)",\n'
    "      marginTop: 6,\n"
    "    },\n"
    "    left: {\n"
    '      right: "100%",\n'
    '      top: "50%",\n'
    '      transform: "translateY(-50%)",\n'
    "      marginRight: 6,\n"
    "    },\n"
    "    right: {\n"
    '      left: "100%",\n'
    '      top: "50%",\n'
    '      transform: "translateY(-50%)",\n'
    "      marginLeft: 6,\n"
    "    },\n"
    "  };\n\n"
    "  return (\n"
    "    <span\n"
    '      style={{ position: "relative", display: "inline-flex", ...style }}\n'
    "      className={className}\n"
    "      onMouseEnter={show}\n"
    "      onMouseLeave={hide}\n"
    "      onFocus={show}\n"
    "      onBlur={hide}\n"
    "    >\n"
    "      {React.cloneElement(children, {\n"
    '        "aria-describedby": visible ? tooltipId : undefined,\n'
    "      })}\n"
    "      {visible && (\n"
    "        <span\n"
    "          id={tooltipId}\n"
    '          role="tooltip"\n'
    "          style={{\n"
    '            position: "absolute",\n'
    "            zIndex: 50,\n"
    '            padding: "4px 8px",\n'
    "            fontSize: 12,\n"
    '            lineHeight: "16px",\n'
    '            color: "#ffffff",\n'
    '            backgroundColor: "#0f172a",\n'
    "            borderRadius: 4,\n"
    '            whiteSpace: "nowrap",\n'
    '            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",\n'
    '            pointerEvents: "none",\n'
    "            ...positionStyles[position],\n"
    "          }}\n"
    "        >\n"
    "          {content}\n"
    "        </span>\n"
    "      )}\n"
    "    </span>\n"
    "  );\n"
    "}\n\n"
    "export default Tooltip;\n"
)


def render_tooltip_component() -> str:
    """Return the static TypeScript implementation of the Tooltip component."""
    return _TOOLTIP_COMPONENT






# --- App Router resilience special files (R-294) -----------------------------------------------
# Static, inline-styled, dependency-free. They never reference ir.name/ir.description, so generation
# stays deterministic and description-only-stable, and they never enter the console-snapshot edit diff.

_ERROR_PAGE = (
    '"use client";\n\n'
    'import { useEffect } from "react";\n'
    'import Link from "next/link";\n\n'
    "export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {\n"
    "  useEffect(() => {\n"
    "    console.error(error);\n"
    "  }, [error]);\n\n"
    "  return (\n"
    '    <main style={{ maxWidth: 560, margin: "80px auto", padding: "0 24px", textAlign: "center", fontFamily: "system-ui, -apple-system, sans-serif" }}>\n'
    '      <p style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#b91c1c", margin: "0 0 12px" }}>Error</p>\n'
    '      <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0f172a", margin: "0 0 8px" }}>Something went wrong</h1>\n'
    '      <p style={{ color: "#64748b", margin: "0 0 24px", lineHeight: 1.6 }}>An unexpected error occurred while rendering this page. You can try again, or return to the overview.</p>\n'
    "      {error?.digest ? (\n"
    '        <p style={{ color: "#94a3b8", fontSize: 12, margin: "0 0 24px" }}>Reference: {error.digest}</p>\n'
    "      ) : null}\n"
    '      <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>\n'
    '        <button onClick={() => reset()} style={{ padding: "10px 20px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 8, fontWeight: 600, cursor: "pointer" }}>Try again</button>\n'
    '        <Link href="/" style={{ padding: "10px 20px", background: "#fff", color: "#0f172a", border: "1px solid #e2e8f0", borderRadius: 8, fontWeight: 600, textDecoration: "none" }}>Back to overview</Link>\n'
    "      </div>\n"
    "    </main>\n"
    "  );\n"
    "}\n"
)

_GLOBAL_ERROR_PAGE = (
    '"use client";\n\n'
    'import { useEffect } from "react";\n\n'
    "export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {\n"
    "  useEffect(() => {\n"
    "    console.error(error);\n"
    "  }, [error]);\n\n"
    "  return (\n"
    '    <html lang="en">\n'
    '      <body style={{ margin: 0, background: "#f8fafc", color: "#0f172a", fontFamily: "system-ui, -apple-system, sans-serif" }}>\n'
    '        <main style={{ maxWidth: 560, margin: "80px auto", padding: "0 24px", textAlign: "center" }}>\n'
    '          <p style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#b91c1c", margin: "0 0 12px" }}>Application error</p>\n'
    '          <h1 style={{ fontSize: 26, fontWeight: 700, margin: "0 0 8px" }}>Something went wrong</h1>\n'
    '          <p style={{ color: "#64748b", margin: "0 0 24px", lineHeight: 1.6 }}>A critical error occurred. Please try again.</p>\n'
    '          <button onClick={() => reset()} style={{ padding: "10px 20px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 8, fontWeight: 600, cursor: "pointer" }}>Try again</button>\n'
    "        </main>\n"
    "      </body>\n"
    "    </html>\n"
    "  );\n"
    "}\n"
)

_NOT_FOUND_PAGE = (
    'import Link from "next/link";\n\n'
    "export default function NotFound() {\n"
    "  return (\n"
    '    <main style={{ maxWidth: 560, margin: "80px auto", padding: "0 24px", textAlign: "center", fontFamily: "system-ui, -apple-system, sans-serif" }}>\n'
    '      <p style={{ fontSize: 48, fontWeight: 800, color: "#cbd5e1", margin: "0 0 8px" }}>404</p>\n'
    '      <h1 style={{ fontSize: 26, fontWeight: 700, color: "#0f172a", margin: "0 0 8px" }}>Page not found</h1>\n'
    '      <p style={{ color: "#64748b", margin: "0 0 24px", lineHeight: 1.6 }}>The page you are looking for does not exist or may have been moved.</p>\n'
    '      <Link href="/" style={{ padding: "10px 20px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 8, fontWeight: 600, textDecoration: "none" }}>Back to overview</Link>\n'
    "    </main>\n"
    "  );\n"
    "}\n"
)

_LOADING_PAGE = (
    "export default function Loading() {\n"
    "  return (\n"
    '    <main style={{ maxWidth: 960, margin: "0 auto", padding: 24 }} aria-busy="true" aria-live="polite">\n'
    '      <div style={{ height: 32, width: "40%", background: "#e2e8f0", borderRadius: 6, marginBottom: 20 }} />\n'
    '      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>\n'
    "        {[0, 1, 2, 3, 4, 5].map((i) => (\n"
    '          <div key={i} style={{ height: 96, background: "#f1f5f9", borderRadius: 8, opacity: 1 - i * 0.12 }} />\n'
    "        ))}\n"
    "      </div>\n"
    "    </main>\n"
    "  );\n"
    "}\n"
)


def render_error_page() -> str:
    """Return the static app/error.tsx route-segment error boundary (client component)."""
    return _ERROR_PAGE


def render_global_error_page() -> str:
    """Return the static app/global-error.tsx root-layout error boundary (client component)."""
    return _GLOBAL_ERROR_PAGE


def render_not_found_page() -> str:
    """Return the static app/not-found.tsx 404 page (server component)."""
    return _NOT_FOUND_PAGE


def render_loading_page() -> str:
    """Return the static app/loading.tsx route-level Suspense skeleton fallback (server component)."""
    return _LOADING_PAGE


_LAYOUT = (
    'import type { Metadata } from "next";\n'
    'import { Navbar } from "../components/navbar";\n'
    'import { ToastProvider } from "../components/toast";\n\n'
    "export const metadata: Metadata = {\n"
    '  title: "%s",\n'
    '  description: "%s",\n'
    "};\n\n"
    "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
    "  return (\n"
    '    <html lang="en">\n'
    '      <body style={{ margin: 0, background: "#f8fafc", color: "#0f172a", fontFamily: "system-ui, -apple-system, sans-serif" }}>\n'
    "        <ToastProvider>\n"
    "          <Navbar />\n"
    "          {children}\n"
    "        </ToastProvider>\n"
    "      </body>\n"
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
            GeneratedFile(".env.example", "# Public env vars only. Never commit secrets.\nNEXT_PUBLIC_APP_NAME=" + ir.name + "\nNEXT_PUBLIC_API_URL=http://localhost:8080\n"),
            GeneratedFile("README.md", f"# {ir.name}\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR.\n\n```\npnpm install\npnpm dev\n```\n"),
            GeneratedFile("app/layout.tsx", _LAYOUT % (_escape_ts(ir.name), _escape_ts(ir.description))),
            GeneratedFile("components/navbar.tsx", _navbar_component(ir)),
            GeneratedFile("components/toast.tsx", _TOAST_COMPONENT),
            GeneratedFile("components/confirm-dialog.tsx", _CONFIRM_DIALOG_COMPONENT),
            GeneratedFile("components/shortcuts-dialog.tsx", _SHORTCUTS_DIALOG_COMPONENT),
            GeneratedFile("components/breadcrumbs.tsx", _BREADCRUMBS_COMPONENT),
            GeneratedFile("components/empty-state.tsx", _EMPTY_STATE_COMPONENT),
            GeneratedFile("components/pagination.tsx", _PAGINATION_COMPONENT),
            GeneratedFile("components/tabs.tsx", _TABS_COMPONENT),
            GeneratedFile("components/badge.tsx", _BADGE_COMPONENT),
            GeneratedFile("components/tooltip.tsx", _TOOLTIP_COMPONENT),
            GeneratedFile("app/globals.css", "body { font-family: system-ui, sans-serif; margin: 0; }\n"),
            GeneratedFile("app/error.tsx", _ERROR_PAGE),
            GeneratedFile("app/global-error.tsx", _GLOBAL_ERROR_PAGE),
            GeneratedFile("app/not-found.tsx", _NOT_FOUND_PAGE),
            GeneratedFile("app/loading.tsx", _LOADING_PAGE),
            GeneratedFile("app/page.tsx", _overview_page(ir)),
            GeneratedFile("lib/types.ts", _types_file(ir)),
            GeneratedFile("lib/api.ts", _api_client_file(ir)),
            GeneratedFile("lib/hooks.ts", _hooks_file(ir)),
        ]

        for screen in ir.screens:
            files.append(GeneratedFile(f"app/{screen.id}/page.tsx", _screen_page(screen, ir)))

        by_dir: dict[str, list[ApiEndpoint]] = {}
        for api in ir.apis:
            route_dir = _route_dir(api.path) or "api"
            by_dir.setdefault(route_dir, []).append(api)
        for route_dir, apis in by_dir.items():
            files.append(GeneratedFile(f"app/{route_dir}/route.ts", _route_file(apis)))

        return GeneratedProject(self.target.value, tuple(files))


def _escape_ts(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
