"""Deterministic OpenAPI 3.1.0 specification generator from Application IR (R-260).

Translates one ApplicationIR into a canonical, machine-readable OpenAPI 3.1.0 document.
Fulfills Brief Section 43 ("Contracts: OpenAPI + generated clients" and packages/contracts/openapi/).

Pure and deterministic — uses standard library json only; no network, no DB.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..application_ir import ApplicationIR, Entity, Field, FieldType
from .field_validation import parse_field_rules
from .route_wiring import Op, fk_relations, wire_endpoint


def _field_to_schema(field: Field) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    if field.type in (FieldType.STRING, FieldType.TEXT):
        schema["type"] = "string"
    elif field.type is FieldType.INT:
        schema["type"] = "integer"
    elif field.type is FieldType.FLOAT:
        schema["type"] = "number"
    elif field.type is FieldType.BOOL:
        schema["type"] = "boolean"
    elif field.type is FieldType.DATETIME:
        schema["type"] = "string"
        schema["format"] = "date-time"
    elif field.type is FieldType.UUID:
        schema["type"] = "string"
        schema["format"] = "uuid"
    elif field.type is FieldType.JSON:
        schema["type"] = "object"
    else:
        schema["type"] = "string"

    rules = parse_field_rules(field)
    if rules.max_length is not None:
        schema["maxLength"] = rules.max_length
    if rules.enum:
        schema["enum"] = list(rules.enum)
    if rules.minimum is not None:
        schema["minimum"] = int(rules.minimum) if field.type is FieldType.INT else float(rules.minimum)
    if rules.maximum is not None:
        schema["maximum"] = int(rules.maximum) if field.type is FieldType.INT else float(rules.maximum)

    return schema


def render_openapi(ir: ApplicationIR) -> dict[str, Any]:
    """Render a complete OpenAPI 3.1.0 document as a Python dictionary from an ApplicationIR."""
    schemas: dict[str, Any] = {}
    for entity in ir.entities:
        props: dict[str, Any] = {}
        for f in entity.fields:
            props[f.name] = _field_to_schema(f)

        for rel in entity.relations:
            if rel.kind.value in ("many_to_one", "one_to_one"):
                fk_col = f"{rel.name}_id"
                if fk_col not in props:
                    props[fk_col] = {"type": "string", "format": "uuid"}

        entity_schema: dict[str, Any] = {
            "type": "object",
            "properties": props,
        }
        req_fields = [f.name for f in entity.fields if f.required]
        if req_fields:
            entity_schema["required"] = req_fields
        schemas[entity.name] = entity_schema

    schemas["ValidationError"] = {
        "type": "object",
        "properties": {
            "field": {"type": "string", "description": "Field that failed validation"},
            "rule": {"type": "string", "description": "Validation rule violated"},
            "message": {"type": "string", "description": "Human-readable error description"},
        },
        "required": ["field", "rule", "message"],
    }
    schemas["ValidationErrorResponse"] = {
        "type": "object",
        "properties": {
            "errors": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/ValidationError"},
            },
        },
        "required": ["errors"],
    }
    schemas["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "detail": {"type": "string", "description": "Error details"},
        },
        "required": ["detail"],
    }

    paths: dict[str, Any] = {}
    repo_entities = frozenset(e.name for e in ir.entities)
    fk_by_entity = fk_relations(ir)

    for api in ir.apis:
        path = api.path
        if path not in paths:
            paths[path] = {}

        method = api.method.value.lower()
        wiring = wire_endpoint(api, repo_entities, fk_by_entity)

        path_params = re.findall(r"\{(\w+)\}", path)
        parameters: list[dict[str, Any]] = []

        for p in path_params:
            parameters.append({
                "name": p,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
                "description": f"Unique identifier for {p}",
            })

        tag = wiring.entity if wiring else (path.strip("/").split("/")[0] or "default")
        plural = (wiring.entity if wiring.entity.endswith("s") else f"{wiring.entity}s") if wiring else ""

        if wiring is not None:
            if wiring.op is Op.LIST:
                op_id = f"list{plural}"
            elif wiring.op is Op.GET:
                op_id = f"get{wiring.entity}"
            elif wiring.op is Op.CREATE:
                op_id = f"create{wiring.entity}"
            elif wiring.op is Op.UPDATE:
                op_id = f"replace{wiring.entity}" if api.method.value == "PUT" else f"update{wiring.entity}"
            elif wiring.op is Op.DELETE:
                op_id = f"delete{wiring.entity}"
            elif wiring.op is Op.LIST_BY:
                rel = wiring.relation or "parent"
                rel_pascal = rel[0].upper() + rel[1:] if rel else ""
                op_id = f"list{plural}By{rel_pascal}"
            else:
                op_id = f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
        else:
            op_id = f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"

        if wiring is not None and wiring.op in (Op.LIST, Op.LIST_BY):
            entity_obj = next((e for e in ir.entities if e.name == wiring.entity), None)
            sort_fields = [f.name for f in entity_obj.fields] if entity_obj else ["id"]
            if "id" not in sort_fields:
                sort_fields.insert(0, "id")

            parameters.extend([
                {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "default": 100},
                    "description": "Maximum number of records to return",
                },
                {
                    "name": "offset",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer", "default": 0},
                    "description": "Number of records to skip",
                },
                {
                    "name": "sort",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "enum": sort_fields, "default": "id"},
                    "description": "Field to sort records by",
                },
                {
                    "name": "order",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string", "enum": ["asc", "desc"], "default": "asc"},
                    "description": "Sort order direction (asc or desc)",
                },
                {
                    "name": "q",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                    "description": "Search query to filter records across text fields",
                },
            ])

        operation: dict[str, Any] = {
            "operationId": op_id,
            "tags": [tag],
            "summary": f"{api.method.value} {path}",
        }
        if parameters:
            operation["parameters"] = parameters

        if method in ("post", "put", "patch"):
            req_entity = None
            if wiring and wiring.op in (Op.CREATE, Op.UPDATE):
                req_entity = wiring.entity
            elif api.request_schema and api.request_schema in repo_entities:
                req_entity = api.request_schema

            if req_entity:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{req_entity}"},
                        },
                    },
                }

        responses: dict[str, Any] = {}
        if wiring is not None:
            if wiring.op in (Op.LIST, Op.LIST_BY):
                responses["200"] = {
                    "description": f"List of {wiring.entity} records",
                    "headers": {
                        "X-Total-Count": {
                            "schema": {"type": "integer"},
                            "description": "Total count of matching records across all pages",
                        },
                    },
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {"$ref": f"#/components/schemas/{wiring.entity}"},
                            },
                        },
                    },
                }
            elif wiring.op is Op.GET:
                responses["200"] = {
                    "description": f"{wiring.entity} details",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{wiring.entity}"},
                        },
                    },
                }
                responses["404"] = {
                    "description": "Record not found",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        },
                    },
                }
            elif wiring.op is Op.CREATE:
                responses["201"] = {
                    "description": f"Created {wiring.entity}",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{wiring.entity}"},
                        },
                    },
                }
                responses["400"] = {
                    "description": "Validation error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"},
                        },
                    },
                }
            elif wiring.op is Op.UPDATE:
                responses["200"] = {
                    "description": f"Updated {wiring.entity}",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{wiring.entity}"},
                        },
                    },
                }
                responses["400"] = {
                    "description": "Validation error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ValidationErrorResponse"},
                        },
                    },
                }
                responses["404"] = {
                    "description": "Record not found",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        },
                    },
                }
            elif wiring.op is Op.DELETE:
                responses["204"] = {
                    "description": "Record deleted successfully",
                }
                responses["404"] = {
                    "description": "Record not found",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        },
                    },
                }
        else:
            responses["200"] = {
                "description": "Successful operation",
            }
            if path_params:
                responses["404"] = {
                    "description": "Record not found",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        },
                    },
                }

        if api.auth:
            responses["401"] = {
                "description": "Unauthorized — missing or invalid Bearer token",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    },
                },
            }
        if api.required_roles:
            responses["403"] = {
                "description": f"Forbidden — required role: {', '.join(api.required_roles)}",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    },
                },
            }

        operation["responses"] = responses

        if api.auth:
            operation["security"] = [{"BearerAuth": list(api.required_roles)}]

        paths[path][method] = operation

    doc: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": ir.name,
            "description": ir.description,
            "version": "1.0.0",
        },
        "paths": paths,
        "components": {
            "schemas": schemas,
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT Bearer token",
                },
            },
        },
    }
    return doc


def render_openapi_json(ir: ApplicationIR, indent: int = 2) -> str:
    """Render OpenAPI 3.1.0 document as deterministic JSON string."""
    return json.dumps(render_openapi(ir), indent=indent) + "\n"
