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
