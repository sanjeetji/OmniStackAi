"""Next.js (App Router, TypeScript) framework adapter.

Turns an Application IR into a real Next.js project as a `GeneratedProject`: config, TypeScript
interfaces from entities, App Router API route handlers from the IR APIs, a page per screen, and an
overview page. Pure and deterministic — nothing is installed, built, run, or written to disk here.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from ..application_ir import ApplicationIR, ApiEndpoint, Entity, Field, FieldType, Screen
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
    lines.append('import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";')
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
        "  setSearch: (q: string) => void;",
        '  setSort: (sort: string, order?: "asc" | "desc") => void;',
        "  refetch: () => Promise<void>;",
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
    fk_by_entity = fk_relations(ir)

    ops_by_entity: dict[str, set[Op]] = {e.name: set() for e in ir.entities}
    subcollections: list[tuple[str, str, str]] = []
    seen_subcols: set[tuple[str, str]] = set()

    for api_endpoint in ir.apis:
        wiring = wire_endpoint(api_endpoint, repo_entities, fk_by_entity)
        if wiring is not None:
            ops_by_entity.setdefault(wiring.entity, set()).add(wiring.op)
            if wiring.op is Op.LIST_BY and wiring.relation:
                key = (wiring.entity, wiring.relation)
                if key not in seen_subcols:
                    seen_subcols.add(key)
                    subcollections.append((wiring.entity, wiring.relation, wiring.id_param or "id"))

    hook_names: list[str] = []

    for entity in ir.entities:
        name = entity.name
        plural = name if name.endswith("s") else f"{name}s"
        ops = ops_by_entity.get(name, set())

        # 1. useList<Entities>
        if Op.LIST in ops:
            hook_name = f"useList{plural}"
            hook_names.append(hook_name)
            lines.extend([
                f"export function {hook_name}(",
                "  initialParams: UseListParams = {},",
                "  options?: ApiOptions",
                f"): UseListState<{name}> {{",
                "  const [params, setParams] = useState<UseListParams>({",
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
                "  const refetch = useCallback(async () => {",
                "    setLoading(true);",
                "    setError(null);",
                "    try {",
                f"      const res = await api.list{plural}WithCount({{ params, ...options }});",
                "      setData(res.data);",
                "      setTotal(res.total);",
                "    } catch (err) {",
                "      setError(err instanceof Error ? err : new Error(String(err)));",
                "    } finally {",
                "      setLoading(false);",
                "    }",
                "  }, [params, options]);",
                "",
                "  useEffect(() => {",
                "    refetch();",
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
                "    setSearch,",
                "    setSort,",
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
                "  const refetch = useCallback(async () => {",
                "    if (!id) {",
                "      setData(null);",
                "      setLoading(false);",
                "      return;",
                "    }",
                "    setLoading(true);",
                "    setError(null);",
                "    try {",
                f"      const item = await api.get{name}(id, options);",
                "      setData(item);",
                "    } catch (err) {",
                "      setError(err instanceof Error ? err : new Error(String(err)));",
                "    } finally {",
                "      setLoading(false);",
                "    }",
                "  }, [id, options]);",
                "",
                "  useEffect(() => {",
                "    refetch();",
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
                "",
                "  const create = useCallback(",
                f"    async (data: Partial<{name}>, options?: ApiOptions): Promise<{name}> => {{",
                "      setLoading(true);",
                "      setError(null);",
                "      try {",
                f"        return await api.create{name}(data, options);",
                "      } catch (err) {",
                "        const e = err instanceof Error ? err : new Error(String(err));",
                "        setError(e);",
                "        throw e;",
                "      } finally {",
                "        setLoading(false);",
                "      }",
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
                "",
                "  const update = useCallback(",
                f"    async (id: string, data: Partial<{name}>, options?: ApiOptions): Promise<{name}> => {{",
                "      setLoading(true);",
                "      setError(null);",
                "      try {",
                f"        return await api.update{name}(id, data, options);",
                "      } catch (err) {",
                "        const e = err instanceof Error ? err : new Error(String(err));",
                "        setError(e);",
                "        throw e;",
                "      } finally {",
                "        setLoading(false);",
                "      }",
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
                "",
                "  const remove = useCallback(",
                "    async (id: string, options?: ApiOptions): Promise<void> => {",
                "      setLoading(true);",
                "      setError(null);",
                "      try {",
                f"        await api.delete{name}(id, options);",
                "      } catch (err) {",
                "        const e = err instanceof Error ? err : new Error(String(err));",
                "        setError(e);",
                "        throw e;",
                "      } finally {",
                "        setLoading(false);",
                "      }",
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
        lines.extend([
            f"export function {hook_name}(",
            f"  {id_p}: string | null | undefined,",
            "  initialParams: UseListParams = {},",
            "  options?: ApiOptions",
            f"): UseListState<{child_entity}> {{",
            "  const [params, setParams] = useState<UseListParams>({",
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
            "  const refetch = useCallback(async () => {",
            f"    if (!{id_p}) {{",
            "      setData(null);",
            "      setTotal(0);",
            "      setLoading(false);",
            "      return;",
            "    }",
            "    setLoading(true);",
            "    setError(null);",
            "    try {",
            f"      const res = await api.list{plural}By{rel_pascal}WithCount({id_p}, {{ params, ...options }});",
            "      setData(res.data);",
            "      setTotal(res.total);",
            "    } catch (err) {",
            "      setError(err instanceof Error ? err : new Error(String(err)));",
            "    } finally {",
            "      setLoading(false);",
            "    }",
            f"  }}, [{id_p}, params, options]);",
            "",
            "  useEffect(() => {",
            "    refetch();",
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
            "    setSearch,",
            "    setSort,",
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
    return ops_by_entity


@dataclass(frozen=True)
class SubcollectionInfo:
    child_entity: Entity
    relation: str
    id_param: str
    hook_name: str
    child_plural: str
    display_fields: tuple[Field, ...]


def _subcollections_for_parent(parent_name: str, ir: ApplicationIR) -> list[SubcollectionInfo]:
    repo_entities = frozenset(e.name for e in ir.entities)
    fk_by_entity = fk_relations(ir)
    entities_by_name = {e.name: e for e in ir.entities}

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

            result.append(
                SubcollectionInfo(
                    child_entity=child_ent,
                    relation=wiring.relation,
                    id_param=wiring.id_param or "id",
                    hook_name=hook_name,
                    child_plural=child_plural,
                    display_fields=display_fields,
                )
            )
    return result


def _collection_screen_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op]) -> str:
    name = entity.name
    plural = name if name.endswith("s") else f"{name}s"
    can_delete = Op.DELETE in ops
    page_name = f"{_pascal(screen.id)}Page"
    title = _title_case(screen.id)

    subcollections = _subcollections_for_parent(name, ir)
    has_subcollections = bool(subcollections)

    # Check for a complementary form/editor screen in ir.screens
    form_screen: Screen | None = None
    for s in ir.screens:
        if s.id != screen.id:
            s_entity = _match_entity(s, ir)
            if s_entity and s_entity.name == entity.name and _screen_intent(s) == "form":
                form_screen = s
                break

    # Select fields to display in table columns (skip 'id' unless it's the only field, limit to 5)
    display_fields = [f for f in entity.fields if f.name != "id"]
    if not display_fields:
        display_fields = list(entity.fields[:1])
    display_fields = display_fields[:5]

    hooks_import = f"useList{plural}"
    if can_delete:
        hooks_import += f", useDelete{name}"

    lines: list[str] = [
        '"use client";',
        "",
        'import { useState } from "react";',
        'import Link from "next/link";',
        f'import {{ {hooks_import} }} from "../lib/hooks";',
    ]

    if has_subcollections:
        subcol_hook_names = [sub.hook_name for sub in subcollections]
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
        "    totalPages,",
        "    params,",
        "    setPage,",
        "    setSearch,",
        "    setSort,",
        "    refetch,",
        f"  }} = useList{plural}();",
    ])

    if can_delete:
        lines.extend([
            f"  const {{ remove }} = useDelete{name}();",
            "  const handleDelete = async (id: string) => {",
            f'    if (confirm("Are you sure you want to delete this {name}?")) {{',
            "      await remove(id);",
            "      refetch();",
            "    }",
            "  };",
        ])

    lines.append('  const [searchInput, setSearchInput] = useState(params.q ?? "");')

    if has_subcollections:
        lines.append('  const [selectedId, setSelectedId] = useState<string | null>(null);')
        if len(subcollections) > 1:
            lines.append('  const [activeTab, setActiveTab] = useState<number>(0);')
        for sub in subcollections:
            s_var = f"{sub.child_entity.name.lower()}sSubcol"
            lines.append(f"  const {s_var} = {sub.hook_name}(selectedId);")
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
        "          <input",
        '            type="search"',
        "            value={searchInput}",
        "            onChange={(e) => {",
        "              setSearchInput(e.target.value);",
        "              setSearch(e.target.value);",
        "            }}",
        f'            placeholder="Search {plural}..."',
        '            style={{ flex: 1, padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, outline: "none" }}',
        "          />",
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
        "      </section>",
        "",
        "      {error && (",
        '        <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#991b1b", marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "center" }}>',
        "          <span>Error: {error.message}</span>",
        '          <button onClick={() => refetch()} style={{ padding: "4px 8px", background: "#991b1b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 12 }}>Retry</button>',
        "        </div>",
        "      )}",
        "",
        '      <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, overflow: "hidden", background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>',
        '        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 14 }}>',
        '          <thead style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>',
        "            <tr>",
    ])

    for f in display_fields:
        col_label = _title_case(f.name)
        lines.extend([
            '              <th onClick={() => setSort("' + f.name + '")} style={{ padding: "12px 16px", fontWeight: 600, color: "#475569", cursor: "pointer", userSelect: "none" }}>',
            '                ' + col_label + ' {params.sort === "' + f.name + '" ? (params.order === "desc" ? "↓" : "↑") : ""}',
            "              </th>",
        ])

    can_edit = (Op.UPDATE in ops) and (form_screen is not None)
    has_actions_col = can_delete or has_subcollections or can_edit
    if has_actions_col:
        actions_header = "Actions" if (can_delete or can_edit) else "Details"
        lines.append(
            f'              <th style={{{{ padding: "12px 16px", textAlign: "right", fontWeight: 600, color: "#475569" }}}}>{actions_header}</th>'
        )

    lines.extend([
        "            </tr>",
        "          </thead>",
        "          <tbody>",
        "            {loading && !data && (",
        "              <tr>",
        f'                <td colSpan={{{len(display_fields) + (1 if has_actions_col else 0)}}} style={{{{ padding: 32, textAlign: "center", color: "#64748b" }}}}>',
        f"                  Loading {plural}... ",
        "                </td>",
        "              </tr>",
        "            )}",
        "            {data && data.length === 0 && (",
        "              <tr>",
        f'                <td colSpan={{{len(display_fields) + (1 if has_actions_col else 0)}}} style={{{{ padding: 32, textAlign: "center", color: "#64748b" }}}}>',
        f"                  No {plural} found.",
        "                </td>",
        "              </tr>",
        "            )}",
        "            {data && data.map((item, idx) => (",
    ])

    if has_subcollections:
        lines.append('              <tr key={(item as any).id ?? idx} onClick={() => setSelectedId(selectedId === (item as any).id ? null : (item as any).id)} style={{ borderBottom: "1px solid #f1f5f9", cursor: "pointer", background: selectedId === (item as any).id ? "#eff6ff" : undefined }}>')
    else:
        lines.append('              <tr key={(item as any).id ?? idx} style={{ borderBottom: "1px solid #f1f5f9" }}>')

    for f in display_fields:
        if f.type == FieldType.BOOL:
            val_expr = (
                '<span style={{ padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 600, '
                'background: (item as any).' + f.name + ' ? "#dcfce7" : "#f1f5f9", '
                'color: (item as any).' + f.name + ' ? "#166534" : "#64748b" }}>'
                '{(item as any).' + f.name + ' ? "Yes" : "No"}</span>'
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

        lines.append('                <td style={{ padding: "12px 16px", color: "#1e293b" }}>' + val_expr + '</td>')

    if has_actions_col:
        lines.append('                <td style={{ padding: "12px 16px", textAlign: "right", whiteSpace: "nowrap" }}>')
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
        '        <div style={{ display: "flex", gap: 8 }}>',
        "          <button",
        "            onClick={() => setPage(page - 1)}",
        "            disabled={page <= 1 || loading}",
        '            style={{ padding: "6px 12px", border: "1px solid #cbd5e1", borderRadius: 6, background: page <= 1 ? "#f1f5f9" : "#fff", color: page <= 1 ? "#94a3b8" : "#0f172a", fontSize: 14, cursor: page <= 1 ? "default" : "pointer" }}',
        "          >",
        "            Previous",
        "          </button>",
        "          <button",
        "            onClick={() => setPage(page + 1)}",
        "            disabled={page >= totalPages || loading}",
        '            style={{ padding: "6px 12px", border: "1px solid #cbd5e1", borderRadius: 6, background: page >= totalPages ? "#f1f5f9" : "#fff", color: page >= totalPages ? "#94a3b8" : "#0f172a", fontSize: 14, cursor: page >= totalPages ? "default" : "pointer" }}',
        "          >",
        "            Next",
        "          </button>",
        "        </div>",
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
                f'                  <div style={{{{ padding: 16, textAlign: "center", color: "#64748b", fontSize: 14 }}}}>Loading {sub.child_plural.lower()}...</div>',
                "                )}",
                f"                {{{s_var}.error && (",
                f'                  <div style={{{{ padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#991b1b", fontSize: 13, marginBottom: 12 }}}}>Error: {{{s_var}.error.message}}</div>',
                "                )}",
                f"                {{{s_var}.data && {s_var}.data.length === 0 && (",
                f'                  <div style={{{{ padding: 16, textAlign: "center", color: "#64748b", fontSize: 14, background: "#f8fafc", borderRadius: 6 }}}}>No {sub.child_plural.lower()} found for this {name.lower()}.</div>',
                "                )}",
                f"                {{{s_var}.data && {s_var}.data.length > 0 && (",
                '                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>',
                f"                    {{{s_var}.data.map((child, cIdx) => (",
                '                      <div key={(child as any).id ?? cIdx} style={{ padding: 12, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14 }}>',
            ])
            for df in sub.display_fields:
                df_label = _title_case(df.name)
                lines.append(
                    f'                        <div style={{{{ color: "#334155" }}}}><strong>{df_label}:</strong> {{String((child as any).{df.name} ?? "-")}}</div>'
                )
            lines.extend([
                "                      </div>",
                "                    ))}",
                "                  </div>",
                "                )}",
                "              </div>",
                "            )}",
            ])

        lines.extend([
            "          </div>",
            "        )}",
            "      </section>",
        ])

    lines.extend([
        "    </main>",
        "  );",
        "}",
        "",
    ])

    return "\n".join(lines)


def _form_screen_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op]) -> str:
    name = entity.name
    plural = name if name.endswith("s") else f"{name}s"
    page_name = f"{_pascal(screen.id)}Page"
    title = _title_case(screen.id)

    # Check for a complementary list screen in ir.screens
    list_screen: Screen | None = None
    for s in ir.screens:
        if s.id != screen.id:
            s_entity = _match_entity(s, ir)
            if s_entity and s_entity.name == entity.name and _screen_intent(s) == "collection":
                list_screen = s
                break

    # Fields to include in form
    editable_fields = [f for f in entity.fields if f.name not in ("id", "created_at", "updated_at")]
    if not editable_fields:
        editable_fields = list(entity.fields)

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
    uses_search_params = can_update or bool(fk_fields)

    lines: list[str] = [
        '"use client";',
        "",
    ]
    if uses_search_params:
        lines.append('import { useEffect, useState } from "react";')
        lines.append('import { useSearchParams } from "next/navigation";')
    else:
        lines.append('import { useState } from "react";')

    lines.append('import Link from "next/link";')
    if can_create:
        lines.append(f'import {{ useCreate{name} }} from "../lib/hooks";')
    if can_update:
        update_hooks = []
        if has_get:
            update_hooks.append(f"use{name}")
        update_hooks.append(f"useUpdate{name}")
        lines.append(f'import {{ {", ".join(update_hooks)} }} from "../lib/hooks";')

    lines.extend([
        'import { extractFieldErrors } from "../lib/api";',
        f'import type {{ {name} }} from "../lib/types";',
        "",
        f"export default function {page_name}() {{",
    ])

    if can_create:
        lines.append(f"  const {{ create, loading: submitting, error: submitError, reset }} = useCreate{name}();")
    else:
        lines.append("  const submitting = false, submitError = null, reset = () => {};")

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

    lines.extend([
        f"  const [formData, setFormData] = useState<Partial<{name}>>({initial_obj});",
        '  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});',
        "  const [success, setSuccess] = useState(false);",
        "",
    ])

    if can_update and has_get:
        lines.extend([
            "  useEffect(() => {",
            "    if (initialData) {",
            "      setFormData(initialData);",
            "    }",
            "  }, [initialData]);",
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
        flabel = _title_case(f.name)
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
            "      } else {",
            "        await create(formData);",
            f"        setFormData({initial_obj});",
            "      }",
        ])
    elif can_update:
        lines.extend([
            "      if (editId) {",
            "        await update(editId, formData);",
            "      }",
        ])
    else:
        lines.extend([
            "      await create(formData);",
            f"      setFormData({initial_obj});",
        ])
    lines.extend([
        "      setSuccess(true);",
        "    } catch (err) {",
        "      const serverErrors = extractFieldErrors(err);",
        "      if (Object.keys(serverErrors).length > 0) {",
        "        setFieldErrors(serverErrors);",
        "      }",
        "    }",
        "  };",
        "",
        "  return (",
        '    <main style={{ maxWidth: 640, margin: "0 auto", padding: "32px 16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>',
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
    ])
    if can_update:
        lines.append(f'        <h1 style={{{{ margin: 0, fontSize: 26, fontWeight: 700, color: "#0f172a" }}}}>{{isEdit ? "Edit {name}" : "{title}"}}</h1>')
    else:
        lines.append(f'        <h1 style={{{{ margin: 0, fontSize: 26, fontWeight: 700, color: "#0f172a" }}}}>{title}</h1>')
    lines.extend([
        "      </header>",
        "",
    ])

    if can_update:
        lines.extend([
            "      {success && (",
            '        <div style={{ padding: "12px 16px", background: "#f0fdf4", border: "1px solid #bbf7d0", color: "#166534", borderRadius: 8, marginBottom: 20 }}>',
            f'          {{isEdit ? "{name} updated successfully!" : "{name} saved successfully!"}}',
            "        </div>",
            "      )}",
        ])
    else:
        lines.extend([
            "      {success && (",
            '        <div style={{ padding: "12px 16px", background: "#f0fdf4", border: "1px solid #bbf7d0", color: "#166534", borderRadius: 8, marginBottom: 20 }}>',
            f"          {name} saved successfully!",
            "        </div>",
            "      )}",
        ])

    if can_update:
        lines.extend([
            "      {(submitError || (isEdit && updateError)) && Object.keys(fieldErrors).length === 0 && (",
            '        <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", borderRadius: 8, marginBottom: 20 }}>',
            "          Error: {((isEdit ? updateError : submitError) || submitError)?.message}",
            "        </div>",
            "      )}",
        ])
    else:
        lines.extend([
            "      {submitError && Object.keys(fieldErrors).length === 0 && (",
            '        <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", borderRadius: 8, marginBottom: 20 }}>',
            "          Error: {submitError.message}",
            "        </div>",
            "      )}",
        ])

    if can_update and has_get:
        lines.extend([
            "      {isEdit && fetchingInitial && (",
            '        <div style={{ padding: "12px 16px", background: "#f8fafc", border: "1px solid #e2e8f0", color: "#64748b", borderRadius: 8, marginBottom: 20, fontSize: 14 }}>',
            f'          Loading {name.lower()} details...',
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

    for f in editable_fields:
        label = _title_case(f.name)
        rules = parse_field_rules(f)
        req_star = ' <span style={{ color: "#dc2626" }}>*</span>' if f.required else ""
        req_attr = " required" if f.required else ""

        if f.type == FieldType.BOOL:
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 14, fontWeight: 500, color: "#334155" }}>',
                '            <input',
                '              type="checkbox"',
                '              checked={Boolean((formData as any).' + f.name + ')}',
                '              onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.checked })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '              style={{ width: 16, height: 16, cursor: "pointer" }}',
                '              aria-invalid={!!fieldErrors.' + f.name + '}',
                '            />',
                '            <span>' + label + '</span>',
                '          </label>',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
                '        </div>',
            ])
        elif f.type == FieldType.TEXT:
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <textarea',
                '            rows={4}',
                '            value={String((formData as any).' + f.name + ' ?? "")}',
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '            placeholder="Enter ' + label.lower() + '..."' + req_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          />',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
                '        </div>',
            ])
        elif f.type in (FieldType.INT, FieldType.FLOAT):
            step = "any" if f.type == FieldType.FLOAT else "1"
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <input',
                '            type="number"',
                '            step="' + step + '"',
                '            value={(formData as any).' + f.name + ' !== undefined && (formData as any).' + f.name + ' !== null ? String((formData as any).' + f.name + ') : ""}',
                '            onChange={(e) => { const v = e.target.value; setFormData((prev) => ({ ...prev, ' + f.name + ': v === "" ? undefined : Number(v) })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '            placeholder="Enter ' + label.lower() + '..."' + req_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          />',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
                '        </div>',
            ])
        elif f.type == FieldType.DATETIME:
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <input',
                '            type="datetime-local"',
                '            value={String((formData as any).' + f.name + ' ?? "")}',
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}' + req_attr,
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
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}' + req_attr,
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
            lines.extend([
                '        <div style={{ marginBottom: 16 }}>',
                '          <label style={{ display: "block", marginBottom: 6, fontSize: 14, fontWeight: 500, color: "#334155" }}>' + label + req_star + '</label>',
                '          <input',
                '            type="text"',
                '            value={String((formData as any).' + f.name + ' ?? "")}',
                '            onChange={(e) => { setFormData((prev) => ({ ...prev, ' + f.name + ': e.target.value })); if (fieldErrors.' + f.name + ') setFieldErrors((prev) => ({ ...prev, ' + f.name + ': "" })); }}',
                '            placeholder="Enter ' + label.lower() + '..."' + req_attr,
                '            style={{ width: "100%", padding: "8px 12px", border: fieldErrors.' + f.name + ' ? "1px solid #ef4444" : "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, boxSizing: "border-box", outline: "none" }}',
                '            aria-invalid={!!fieldErrors.' + f.name + '}',
                '          />',
                '          {fieldErrors.' + f.name + ' && <span style={{ color: "#ef4444", fontSize: 12, marginTop: 4, display: "block" }}>{fieldErrors.' + f.name + '}</span>}',
                '        </div>',
            ])

    if can_create and can_update:
        submitting_expr = "(submitting || updating)"
        btn_label = f'({submitting_expr} ? "Saving..." : (isEdit ? "Update {name}" : "Save {name}"))'
    elif can_update:
        submitting_expr = "updating"
        btn_label = f'(updating ? "Saving..." : "Update {name}")'
    else:
        submitting_expr = "submitting"
        btn_label = f'(submitting ? "Saving..." : "Save {name}")'

    reset_call = f"setFormData(isEdit && initialData ? initialData : {initial_obj})" if (can_update and has_get) else f"setFormData({initial_obj})"

    lines.extend([
        '        <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 24, paddingTop: 16, borderTop: "1px solid #f1f5f9" }}>',
        '          <button',
        '            type="button"',
        f'            onClick={{() => {{ reset(); {reset_call}; setFieldErrors({{}}); setSuccess(false); }}}}',
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
        '    </main>',
        '  );',
        '}',
        '',
    ])

    return "\n".join(lines)


def _detail_screen_page(screen: Screen, entity: Entity, ir: ApplicationIR, ops: set[Op]) -> str:
    name = entity.name
    plural = name if name.endswith("s") else f"{name}s"
    page_name = f"{_pascal(screen.id)}Page"
    title = _title_case(screen.id)
    subcollections = _subcollections_for_parent(name, ir)
    has_subcollections = bool(subcollections)

    hooks_to_import: list[str] = []
    if Op.GET in ops:
        hooks_to_import.append(f"use{name}")

    lines: list[str] = [
        '"use client";',
        "",
        'import { useState } from "react";',
        'import Link from "next/link";',
    ]

    if hooks_to_import:
        lines.append(f'import {{ {", ".join(hooks_to_import)} }} from "../lib/hooks";')
    if has_subcollections:
        subcol_hook_names = [sub.hook_name for sub in subcollections]
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
        '  const [idInput, setIdInput] = useState<string>("");',
        '  const [selectedId, setSelectedId] = useState<string | null>(null);',
    ])

    if Op.GET in ops:
        lines.append(f"  const {{ data: item, loading, error, refetch }} = use{name}(selectedId);")

    if has_subcollections:
        if len(subcollections) > 1:
            lines.append('  const [activeTab, setActiveTab] = useState<number>(0);')
        for sub in subcollections:
            s_var = f"{sub.child_entity.name.lower()}sSubcol"
            lines.append(f"  const {s_var} = {sub.hook_name}(selectedId);")

    lines.extend([
        "",
        "  return (",
        '    <main style={{ maxWidth: 840, margin: "0 auto", padding: "32px 16px", fontFamily: "system-ui, -apple-system, sans-serif" }}>',
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

    for nav in screen.navigation:
        lines.append(
            f'          <Link href="/{nav}" style={{{{ padding: "8px 14px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 6, textDecoration: "none", fontSize: 14 }}}}>{_pascal(nav)}</Link>'
        )

    lines.extend([
        "        </div>",
        "      </header>",
        "",
        '      <section style={{ marginBottom: 24, padding: 16, background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, display: "flex", gap: 8, alignItems: "center" }}>',
        "        <input",
        '          type="text"',
        "          value={idInput}",
        "          onChange={(e) => setIdInput(e.target.value)}",
        f'          placeholder="Enter {name} ID..."',
        '          style={{ flex: 1, padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 14, outline: "none" }}',
        "        />",
        "        <button",
        "          onClick={() => setSelectedId(idInput.trim() || null)}",
        '          style={{ padding: "8px 16px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontSize: 14, fontWeight: 500, cursor: "pointer" }}',
        "        >",
        f"          Load {name}",
        "        </button>",
        "      </section>",
        "",
    ])

    if Op.GET in ops:
        lines.extend([
            "      {loading && (",
            f'        <div style={{ padding: 24, textAlign: "center", color: "#64748b" }}>Loading {name}...</div>',
            "      )}",
            "      {error && (",
            '        <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, color: "#991b1b", marginBottom: 20 }}>',
            f"          Error loading {name}: {{error.message}}",
            "        </div>",
            "      )}",
            "      {item && (",
            '        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: 24, marginBottom: 24, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>',
            f'          <h2 style={{ margin: "0 0 16px 0", fontSize: 20, fontWeight: 700, color: "#0f172a" }}>',
            f"            {{String((item as any).{best_title_f} ?? (item as any).id)}}",
            "          </h2>",
            '          <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 16px", fontSize: 14 }}>',
        ])
        for f in entity.fields:
            flabel = _title_case(f.name)
            lines.extend([
                f'            <dt style={{ fontWeight: 600, color: "#475569" }}>{flabel}:</dt>',
                f'            <dd style={{ margin: 0, color: "#1e293b" }}>{{String((item as any).{f.name} ?? "-")}}</dd>',
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
                "                  <button",
                f"                    onClick={{() => {s_var}.refetch()}}",
                f"                    disabled={{{s_var}.loading}}",
                f'                    style={{{{ padding: "4px 8px", border: "1px solid #cbd5e1", background: "#fff", color: "#334155", borderRadius: 4, fontSize: 12, cursor: {s_var}.loading ? "default" : "pointer" }}}}',
                "                  >",
                f'                    {{{s_var}.loading ? "Loading..." : "Refresh"}}',
                "                  </button>",
                "                </div>",
                f"                {{{s_var}.loading && !{s_var}.data && (",
                f'                  <div style={{{{ padding: 16, textAlign: "center", color: "#64748b", fontSize: 14 }}}}>Loading {sub.child_plural.lower()}...</div>',
                "                )}",
                f"                {{{s_var}.error && (",
                f'                  <div style={{{{ padding: "8px 12px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, color: "#991b1b", fontSize: 13, marginBottom: 12 }}}}>Error: {{{s_var}.error.message}}</div>',
                "                )}",
                f"                {{{s_var}.data && {s_var}.data.length === 0 && (",
                f'                  <div style={{{{ padding: 16, textAlign: "center", color: "#64748b", fontSize: 14, background: "#f8fafc", borderRadius: 6 }}}}>No {sub.child_plural.lower()} found for this {name.lower()}.</div>',
                "                )}",
                f"                {{{s_var}.data && {s_var}.data.length > 0 && (",
                '                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>',
                f"                    {{{s_var}.data.map((child, cIdx) => (",
                '                      <div key={(child as any).id ?? cIdx} style={{ padding: 12, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 6, fontSize: 14 }}>',
            ])
            for df in sub.display_fields:
                df_label = _title_case(df.name)
                lines.append(
                    f'                        <div style={{{{ color: "#334155" }}}}><strong>{df_label}:</strong> {{String((child as any).{df.name} ?? "-")}}</div>'
                )
            lines.extend([
                "                      </div>",
                "                    ))}",
                "                  </div>",
                "                )}",
                "              </div>",
                "            )}",
            ])

        lines.extend([
            "          </div>",
            "        )}",
            "      </section>",
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
            GeneratedFile(".env.example", "# Public env vars only. Never commit secrets.\nNEXT_PUBLIC_APP_NAME=" + ir.name + "\nNEXT_PUBLIC_API_URL=http://localhost:8080\n"),
            GeneratedFile("README.md", f"# {ir.name}\n\n{ir.description}\n\nGenerated by OmniStackAI from the Application IR.\n\n```\npnpm install\npnpm dev\n```\n"),
            GeneratedFile("app/layout.tsx", _LAYOUT % (_escape_ts(ir.name), _escape_ts(ir.description))),
            GeneratedFile("app/globals.css", "body { font-family: system-ui, sans-serif; margin: 0; }\n"),
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
