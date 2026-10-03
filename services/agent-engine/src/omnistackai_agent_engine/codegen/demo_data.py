"""PC-077: realistic demo data for the preview - a product that looks used, not empty.

An empty list is the most common thing a person sees first in a new app, and the design review's
most common complaint. So every build gets demo rows for every table:

* **realistic** - the model writes the values (one request, for this product's own records:
  "Lemon Drizzle Cake", not "Product 1"), checked against each field's type and rules (enums,
  minimum and maximum, length); without a model, or for any value that fails, a deterministic
  generator writes plausible values from the field's name and type;
* **linked** - rows refer to rows of the tables they belong to, in dependency order;
* **deterministic** - the same plan gives the same rows (ids derived from the plan), so a preview
  looks the same every time;
* **preview only** - the rows are in ``services/api/demo/demo_data.sql``, which the preview loads
  after the migrations and publishing never reads: a real product never ships sample records.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import uuid
from typing import Any

from ..application_ir import ApplicationIR, Entity, FieldType
from .seed_sql import _sql_literal

ROWS = 6
PATH = "services/api/demo/demo_data.sql"

_FIRST = ("Asha", "Rahul", "Maya", "Daniel", "Priya", "Sofia", "Arjun", "Emma", "Kenji", "Lena", "Omar", "Zara")
_LAST = ("Rao", "Sharma", "Patel", "Garcia", "Chen", "Kim", "Okafor", "Silva", "Müller", "Nair", "Haddad", "Brown")
_CITIES = ("Bengaluru", "Mumbai", "Pune", "Delhi", "Hyderabad", "Chennai")
_WORDS = ("Classic", "Fresh", "Premium", "Everyday", "Signature", "Deluxe", "Essential", "Golden", "Urban", "Garden")


def _rng(*parts: Any) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def row_id(entity: str, index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"omnistackai:demo:{entity}:{index}"))


def _rules(field) -> Any:
    from .field_validation import parse_field_rules

    try:
        return parse_field_rules(field)
    except Exception:  # noqa: BLE001
        return None


def generated_value(entity: Entity, field, index: int) -> Any:
    """A plausible value from the field's name, type and rules - deterministic."""
    name = field.name.lower()
    r = _rng(entity.name, field.name, index)
    rules = _rules(field)
    if rules is not None and getattr(rules, "enum", None):
        return rules.enum[index % len(rules.enum)]
    if field.type is FieldType.BOOL:
        return index % 3 != 0
    if field.type in (FieldType.INT, FieldType.FLOAT):
        low = _number(getattr(rules, "minimum", None)) if rules else None
        high = _number(getattr(rules, "maximum", None)) if rules else None
        if any(w in name for w in ("rating", "stars", "score")):
            low, high = low if low is not None else 1, high if high is not None else 5
            value = max(low, min(high, 3 + r % 3))
        elif any(w in name for w in ("price", "amount", "total", "cost", "fee", "salary", "balance")):
            value = round(9 + (r % 9000) / 100, 2) if field.type is FieldType.FLOAT else 9 + r % 90
        elif any(w in name for w in ("quantity", "qty", "count", "stock", "seats", "capacity")):
            value = 1 + r % 20
        elif "year" in name:
            value = 2020 + r % 6
        else:
            value = 1 + r % 100
        if low is not None:
            value = max(value, low)
        if high is not None:
            value = min(value, high)
        return float(value) if field.type is FieldType.FLOAT else int(value)
    if field.type is FieldType.DATETIME:
        day = _dt.datetime(2026, 10, 1, 9, 0, tzinfo=_dt.timezone.utc) + _dt.timedelta(days=(r % 40) - 10, hours=r % 9)
        return day.isoformat()
    if field.type in (FieldType.UUID, FieldType.JSON, FieldType.ATTACHMENT):
        return None
    # One person per row: the name and the email on a row belong together.
    person = _rng(entity.name, index)
    first, last = _FIRST[person % len(_FIRST)], _LAST[(person // 7) % len(_LAST)]
    if "email" in name:
        return f"{first.lower()}.{last.lower().replace('ü', 'u')}{index + 1}@example.com"
    if "phone" in name or "mobile" in name:
        return f"+91 98{r % 100000000:08d}"
    if name in ("first_name", "firstname", "given_name"):
        return first
    if name in ("last_name", "lastname", "surname", "family_name"):
        return last
    if name in ("name", "full_name", "customer_name", "author", "author_name") and _is_person(entity):
        return f"{first} {last}"
    if "city" in name:
        return _CITIES[r % len(_CITIES)]
    if "address" in name:
        return f"{10 + r % 190} MG Road, {_CITIES[r % len(_CITIES)]}"
    if "url" in name or "website" in name or "link" in name:
        return f"https://example.com/{entity.name.lower()}/{index + 1}"
    if any(w in name for w in ("status", "state", "stage")):
        return ("active", "pending", "completed")[index % 3]
    if field.type in (FieldType.TEXT, FieldType.RICH_TEXT) or any(w in name for w in ("description", "body", "notes", "bio", "content")):
        return f"A {_WORDS[r % len(_WORDS)].lower()} {entity.name.lower()} added to show how this looks with real content."
    if any(w in name for w in ("name", "title", "label", "subject", "headline")):
        return f"{_WORDS[(index + r) % len(_WORDS)]} {_human(entity.name)} {index + 1}"
    if any(w in name for w in ("code", "sku", "reference", "number")):
        return f"{entity.name[:3].upper()}-{1000 + index}"
    return f"{_human(field.name).capitalize()} {index + 1}"


def _number(raw: Any) -> float | None:
    try:
        return None if raw is None else float(raw)
    except (TypeError, ValueError):
        return None


def _is_person(entity: Entity) -> bool:
    return bool(re.search(r"(?i)customer|user|member|patient|student|employee|person|client|author|driver|owner|staff|teacher|doctor|guest|tenant|contact", entity.name))


def _human(text: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])|_", " ", text).strip().lower()


def _fk_columns(entity: Entity) -> dict[str, str]:
    """Column -> the entity it points at, for the relations that are a column on this table."""
    from .schema_sql import _FK_KINDS

    columns = {}
    for relation in entity.relations:
        if relation.kind in _FK_KINDS:
            column = relation.name if relation.name.endswith("_id") else f"{relation.name}_id"
            columns[column] = relation.target_entity
    return columns


_TAG = re.compile(r"</?[A-Za-z][^<>]*>")


def _valid(entity: Entity, field, value: Any) -> bool:
    """Whether a model-written value fits the column."""
    if value is None:
        return not field.required
    rules = _rules(field)
    if field.type is FieldType.BOOL:
        return isinstance(value, bool)
    if field.type in (FieldType.INT, FieldType.FLOAT):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (field.type is FieldType.INT and not float(value).is_integer()):
            return False
        low, high = (_number(rules.minimum), _number(rules.maximum)) if rules is not None else (None, None)
        if (low is not None and value < low) or (high is not None and value > high):
            return False
        return True
    if field.type is FieldType.DATETIME:
        try:
            _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return True
        except ValueError:
            return False
    if field.type in (FieldType.STRING, FieldType.TEXT, FieldType.RICH_TEXT):
        if not isinstance(value, str) or not value.strip():
            return False
        if rules is not None and getattr(rules, "enum", None) and value not in rules.enum:
            return False
        if rules is not None and getattr(rules, "max_length", None) and len(value) > rules.max_length:
            return False
        return len(value) <= 2000
    return False


def plan_rows(ir: ApplicationIR, written: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Every table's demo rows: the model's values where they fit, generated ones otherwise."""
    from .schema_sql import ordered_entities

    try:
        order = ordered_entities(ir)
    except Exception:  # noqa: BLE001 - found live: tables that refer to each other in a cycle
        order = tuple(ir.entities)  # links are then filled only where a row already exists
    written = written or {}
    rows: dict[str, list[dict[str, Any]]] = {}
    # A lifecycle's own states, so every demo record is in a state the app knows.
    states = {(c.config.get("entity"), c.config.get("field") or "status"): list(c.config.get("states") or [])
              for c in ir.capabilities if c.kind == "workflow" and isinstance(c.config, dict)}
    for entity in order:
        id_field = next((f for f in entity.fields if f.name == "id"), None)
        if id_field is not None and id_field.type is not FieldType.UUID:
            continue  # rows that cannot be referred to are not worth inventing
        fks = _fk_columns(entity)
        model_rows = [r for r in written.get(entity.name) or [] if isinstance(r, dict)]
        table = []
        for index in range(ROWS):
            source = model_rows[index] if index < len(model_rows) else {}
            row: dict[str, Any] = {"id": row_id(entity.name, index)}
            for field in entity.fields:
                if field.name in ("id", "created_at", "updated_at", "created_by"):
                    continue
                if field.name in fks:
                    continue
                lifecycle = states.get((entity.name, field.name))
                if lifecycle:
                    row[field.name] = lifecycle[index % len(lifecycle)]
                    continue
                value = source.get(field.name)
                if isinstance(value, str) and field.type is not FieldType.RICH_TEXT:
                    # Seen live: the model marked up a plain description ("A <strong>24-hour</strong>
                    # ..."), which the app shows as text, tags and all.
                    value = _TAG.sub("", value)
                row[field.name] = value if value is not None and _valid(entity, field, value) else generated_value(entity, field, index)
            for column, target in fks.items():
                parents = rows.get(target)
                if parents:
                    row[column] = parents[(index * 5 + _rng(entity.name, column) % len(parents)) % len(parents)]["id"]
            table.append({k: v for k, v in row.items() if v is not None})
        rows[entity.name] = table
    return rows


def demo_sql(ir: ApplicationIR, written: dict[str, list[dict[str, Any]]] | None = None) -> str | None:
    """The demo file, or None when it cannot be made - demo data never fails a build."""
    try:
        return render_sql(ir, plan_rows(ir, written))
    except Exception:  # noqa: BLE001
        return None


def render_sql(ir: ApplicationIR, rows: dict[str, list[dict[str, Any]]]) -> str:
    from .schema_sql import sql_identifier, table_name

    lines = [f"-- Demo data for the preview of {ir.name} (PC-077). Never applied by publishing.",
             "BEGIN;"]
    for entity_name, table in rows.items():
        for row in table:
            columns = ", ".join(sql_identifier(c) for c in row)
            values = ", ".join(_sql_literal(v) for v in row.values())
            lines.append(f"INSERT INTO {sql_identifier(table_name(entity_name))} ({columns}) VALUES ({values}) ON CONFLICT DO NOTHING;")
    lines.append("COMMIT;")
    return "\n".join(lines) + "\n"


def values_request(ir: ApplicationIR, prompt: str) -> str:
    tables = {e.name: {f.name: f.type.value for f in e.fields if f.name not in ("id", "created_at", "updated_at", "created_by")}
              for e in ir.entities}
    return (
        f"Write realistic demo data for this product so its screens look used: {prompt[:600]}\n\n"
        f"For each table give {ROWS} rows. Use believable, specific, varied values for this exact product "
        "(real-sounding names, titles, prices, dates in 2026, statuses). Respect the types. Leave out ids and "
        "links between tables. Return JSON only: {\"<Table>\": [{\"<field>\": <value>, ...}, ...], ...}\n\n"
        f"Tables and fields: {json.dumps(tables)}"
    )


async def write_values(ir: ApplicationIR, prompt: str, provider: Any, model_id: str | None,
                       timeout: float = 120.0) -> tuple[dict[str, list[dict[str, Any]]], str]:
    if provider is None:
        return {}, "generated"
    import uuid as _uuid

    from ..codegen.llm_ui import _resolve_target
    from ..model_gateway.contracts import ChatRole, GenerateRequest, Message

    try:
        target, max_output = _resolve_target(provider, model_id)
        response = await provider.generate(GenerateRequest(
            f"demo-data-{_uuid.uuid4().hex[:12]}", target,
            (Message(ChatRole.SYSTEM, "You write realistic sample data. Respond with one JSON object only."),
             Message(ChatRole.USER, values_request(ir, prompt))), min(8192, max(2048, max_output)), timeout))
        match = re.search(r"\{.*\}", getattr(response, "text", "") or "", re.S)
        data = json.loads(match.group(0)) if match else None
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, list)}, "model"
        return {}, "generated (the model's answer was not JSON)"
    except Exception as error:  # noqa: BLE001 - generated values are used instead
        return {}, f"generated (the model could not answer: {type(error).__name__})"
