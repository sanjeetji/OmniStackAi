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

from ..application_ir import Field, FieldType

_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")
_NUMERIC_TYPES = frozenset({FieldType.INT, FieldType.FLOAT})
_STRING_TYPES = frozenset({FieldType.STRING, FieldType.TEXT})

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
    """The `internal/handlers/validate.go` source that enforces the `validate` struct tags (R-252).

    A single shared validator instance evaluates the go-playground tags the models carry
    (``max=`` / ``oneof=`` / ``gte=`` / ``lte=``). ``validateStruct`` returns the HTTP status and
    message to send back — ``msg == ""`` means the payload is valid. The validator dependency lives only
    in the generated project's go.mod; nothing here runs a validation at generation time.
    """

    return (
        "package handlers\n\n"
        "import (\n"
        '\t"net/http"\n\n'
        '\t"github.com/go-playground/validator/v10"\n'
        ")\n\n"
        "// validate is the shared request validator, driven by the `validate` struct tags the models\n"
        "// carry (max=, oneof=, gte=, lte=), so payloads are checked before they reach the store.\n"
        "var validate = validator.New()\n\n"
        "// validateStruct validates v against its `validate` struct tags. It returns the HTTP status and\n"
        '// message to send back (msg == "" means the payload is valid).\n'
        "func validateStruct(v any) (int, string) {\n"
        "\tif err := validate.Struct(v); err != nil {\n"
        '\t\treturn http.StatusBadRequest, "validation_failed"\n'
        "\t}\n"
        '\treturn http.StatusOK, ""\n'
        "}\n"
    )
