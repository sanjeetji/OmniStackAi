"""Interpret the IR Field.validation rule strings for the generators (R-250).

A field's `validation` tuple may carry small deterministic rules that the schema and model generators
honour:

- ``max_length:<int>``   — a string length cap (schema VARCHAR(n); Pydantic Field(max_length=n); Go max)
- ``enum:<a>|<b>|<c>``   — an allowed-value set (schema CHECK (...); Pydantic Literal[...]; Go oneof)
- ``min:<number>``       — a numeric lower bound (schema CHECK (col >= n); Pydantic ge=n; Go gte)
- ``max:<number>``       — a numeric upper bound (schema CHECK (col <= n); Pydantic le=n; Go lte)

`parse_field_rules` extracts the recognised rules and ignores anything else, so unknown/future rules
are forward-compatible and never crash a generator. Numeric bounds keep their exact literal token (no
float reformatting). Pure and deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dataclass_field

from ..application_ir import Entity, Field, FieldType

_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")
_NUMERIC_TYPES = frozenset({FieldType.INT, FieldType.FLOAT})
_STRING_TYPES = frozenset({FieldType.STRING, FieldType.TEXT})


def filter_fields(entity: Entity) -> list[tuple[Field, str]]:
    """Fields eligible for server-side equality filtering (R-282): boolean fields and enum fields.

    Returns ``(field, kind)`` pairs where ``kind`` is ``"bool"`` or ``"enum"``, excluding the ``id``
    primary key. This is the single source of truth the backend generators (data-access, routers/handlers,
    OpenAPI) share, and it mirrors the frontend's boolean/enum filter selection so the two agree on the
    same field set. Deterministic, order-preserving.
    """

    out: list[tuple[Field, str]] = []
    for field in entity.fields:
        if field.name == "id":
            continue
        if field.type is FieldType.BOOL:
            out.append((field, "bool"))
        elif parse_field_rules(field).enum:
            out.append((field, "enum"))
    return out

# Generated-project dependency pin (only added when the Go backend enforces validation — R-252).
VALIDATOR_REQUIRE = "github.com/go-playground/validator/v10 v10.22.1"


@dataclass(frozen=True, slots=True)
class FieldRules:
    max_length: int | None = None
    enum: tuple[str, ...] = dataclass_field(default_factory=tuple)
    minimum: str | None = None  # raw numeric literal, emitted verbatim
    maximum: str | None = None


def parse_field_rules(field: Field) -> FieldRules:
    max_length: int | None = None
    enum: tuple[str, ...] = ()
    minimum: str | None = None
    maximum: str | None = None
    for rule in field.validation:
        if rule.startswith("max_length:"):
            value = rule.split(":", 1)[1].strip()
            if value.isdigit():
                max_length = int(value)
        elif rule.startswith("enum:"):
            body = rule.split(":", 1)[1]
            enum = tuple(part.strip() for part in body.split("|") if part.strip())
        elif rule.startswith("min:"):
            value = rule.split(":", 1)[1].strip()
            if _NUMBER.match(value):
                minimum = value
        elif rule.startswith("max:"):
            value = rule.split(":", 1)[1].strip()
            if _NUMBER.match(value):
                maximum = value
    return FieldRules(max_length=max_length, enum=enum, minimum=minimum, maximum=maximum)


def go_validate_tag(field: Field, rules: FieldRules) -> str:
    """The go-playground/validator tag body for a field's rules ("" when there are none)."""

    parts: list[str] = []
    if rules.max_length is not None and field.type in _STRING_TYPES:
        parts.append(f"max={rules.max_length}")
    if rules.enum:
        parts.append("oneof=" + " ".join(rules.enum))
    if field.type in _NUMERIC_TYPES:
        if rules.minimum is not None:
            parts.append(f"gte={rules.minimum}")
        if rules.maximum is not None:
            parts.append(f"lte={rules.maximum}")
    return ",".join(parts)


def go_validate_file() -> str:
    """The `internal/handlers/validate.go` source that enforces the `validate` struct tags (R-252/R-254).

    A single shared validator instance evaluates the go-playground tags the models carry
    (``max=`` / ``oneof=`` / ``gte=`` / ``lte=``). ``validateStruct`` returns a structured JSON
    error body — ``{"errors":[{"field":"...","rule":"...","message":"..."}]}`` — with one entry per
    violated field/rule pair, so clients can highlight exactly which field failed. Returns
    ``(http.StatusOK, nil)`` when the payload is valid. The validator dependency lives only in the
    generated project's go.mod; nothing here runs a validation at generation time.
    """

    return (
        "package handlers\n\n"
        "import (\n"
        '\t"fmt"\n'
        '\t"net/http"\n\n'
        '\t"github.com/go-playground/validator/v10"\n'
        ")\n\n"
        "// validate is the shared request validator, driven by the `validate` struct tags the models\n"
        "// carry (max=, oneof=, gte=, lte=), so payloads are checked before they reach the store.\n"
        "var validate = validator.New()\n\n"
        "// validationError is one field-level violation returned in the 400 body.\n"
        "type validationError struct {\n"
        '\tField   string `json:"field"`\n'
        '\tRule    string `json:"rule"`\n'
        '\tMessage string `json:"message"`\n'
        "}\n\n"
        "// validateStruct validates v against its `validate` struct tags. On success it returns\n"
        "// (http.StatusOK, nil). On failure it writes a 400 JSON body\n"
        '// {"errors":[{"field":"...","rule":"...","message":"..."}]} and returns\n'
        "// (http.StatusBadRequest, non-nil) so the caller can return immediately.\n"
        "func validateStruct(w http.ResponseWriter, v any) bool {\n"
        "\terr := validate.Struct(v)\n"
        "\tif err == nil {\n"
        "\t\treturn true\n"
        "\t}\n"
        "\tvar errs []validationError\n"
        "\tfor _, fe := range err.(validator.ValidationErrors) {\n"
        '\t\terrs = append(errs, validationError{\n'
        '\t\t\tField:   fe.Field(),\n'
        '\t\t\tRule:    fe.Tag(),\n'
        '\t\t\tMessage: fmt.Sprintf("%s failed %s validation", fe.Field(), fe.Tag()),\n'
        '\t\t})\n'
        "\t}\n"
        '\twriteJSON(w, http.StatusBadRequest, map[string]any{"errors": errs})\n'
        "\treturn false\n"
        "}\n"
    )
