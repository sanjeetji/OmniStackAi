"""Interpret the IR Field.validation rule strings for the generators (R-250).

A field's `validation` tuple may carry small deterministic rules that the schema and model generators
honour:

- ``max_length:<int>``   — a string length cap (schema VARCHAR(n); Pydantic Field(max_length=n))
- ``enum:<a>|<b>|<c>``   — an allowed-value set (schema CHECK (...); Pydantic Literal[...])

`parse_field_rules` extracts the recognised rules and ignores anything else, so unknown/future rules
are forward-compatible and never crash a generator. Pure and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field

from ..application_ir import Field


@dataclass(frozen=True, slots=True)
class FieldRules:
    max_length: int | None = None
    enum: tuple[str, ...] = dataclass_field(default_factory=tuple)


def parse_field_rules(field: Field) -> FieldRules:
    max_length: int | None = None
    enum: tuple[str, ...] = ()
    for rule in field.validation:
        if rule.startswith("max_length:"):
            value = rule.split(":", 1)[1].strip()
            if value.isdigit():
                max_length = int(value)
        elif rule.startswith("enum:"):
            body = rule.split(":", 1)[1]
            enum = tuple(part.strip() for part in body.split("|") if part.strip())
    return FieldRules(max_length=max_length, enum=enum)
