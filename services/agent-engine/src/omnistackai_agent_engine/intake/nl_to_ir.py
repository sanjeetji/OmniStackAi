"""Prompt -> Application IR intake agent (R-416).

The first brick of the OmniStackAI "chat -> create an app" front door: turn a
plain-English application description into a validated, normalized Application IR
(the framework-neutral spec the code generators already consume).

Design (so `task verify` stays offline and deterministic):
  * build_intake_messages(prompt) -> the (system, user) Message tuple. The system
    message teaches the schema BY EXAMPLE, embedding a real ``example_ir(...).to_dict()``
    so it can never drift from the actual IR schema.
  * parse_ir_response(text) -> ApplicationIR. Pure text -> IR: tolerates ```json fences
    and surrounding prose, injects the schema version when omitted, builds the IR via
    ``ApplicationIR.from_dict`` and normalizes it.
  * generate_ir(prompt, provider, ...) -> IntakeResult. The only I/O step; it depends
    solely on the vendor-neutral ``ModelProvider`` protocol, so tests inject an in-memory
    stub (0 model calls, 0 network). The live local-Ollama path is the opt-in
    ``omnistackai_agent_engine.intake.live_run`` module, excluded from static verify.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from ..application_ir import (
    ApplicationIR,
    Issue,
    Severity,
    has_errors,
    normalize_ir,
    validate_ir,
)
from ..application_ir.errors import ApplicationIRError
from ..application_ir.examples import example_ir
from ..application_ir.ir import (
    IR_SCHEMA_VERSION,
    AdminStrategy,
    BackendStrategy,
    DatabaseStrategy,
    FieldType,
    MobileProfile,
    RepoStrategy,
    WebStrategy,
)
from ..model_gateway import (
    ChatRole,
    GenerateRequest,
    Message,
    ModelProvider,
    ModelRef,
)
from .context import assemble_context
from .errors import IntakeError, IntakeResponseError
from .ir_repair import repair_ir_dict

DEFAULT_TEMPLATE_EXAMPLE = "minimal-blog"
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 300.0
_REQUEST_ID = "r416-intake-nl-to-ir"


@dataclass(frozen=True)
class IntakeResult:
    """Outcome of compiling a natural-language prompt into an Application IR."""

    ir: ApplicationIR
    issues: tuple[Issue, ...]
    raw_text: str
    context_truncated: bool = False
    active_skills: tuple[str, ...] = ()
    truncated_skills: tuple[str, ...] = ()
    #: PC-093: what intake repaired in the model's plan instead of rejecting it, one note each.
    repairs: tuple[str, ...] = ()


def _system_instruction(example_name: str) -> str:
    # R-564: while no capability kind is implemented, the example does not show `capabilities` at
    # all. Showing an empty list invites the model to fill it, and a capability nothing can build
    # would be accepted and then quietly dropped — the failure R-559 removed for stacks. The key
    # reappears here by itself the moment a kind is registered as implemented.
    from ..application_ir.capability import CAPABILITY_KINDS

    _template_ir = example_ir(example_name).to_dict()
    if not CAPABILITY_KINDS.implemented():
        _template_ir.pop("capabilities", None)
    template = json.dumps(_template_ir, indent=2, sort_keys=True)

    # R-566: an empty `capabilities` list with no schema beside it is an invitation to invent one.
    # Built from the registry, so a kind that is not implemented is never described to the model.
    capability_rules = ""
    if "workflow" in CAPABILITY_KINDS.implemented():
        capability_rules = (
            "\nLifecycles (optional, use only when the product really has one):\n"
            "- A 'capabilities' entry of kind 'workflow' describes the states an entity moves "
            "through and who may move it. Use it for an order that is placed then accepted then "
            "delivered, a document that is drafted then approved, a ticket that is opened then "
            "closed. Do NOT use it for a plain boolean like 'published'.\n"
            '- Shape: {"kind": "workflow", "name": "order_lifecycle", "config": {"entity": '
            '"Order", "field": "status", "states": ["placed", "accepted", "delivered"], '
            '"initial": "placed", "transitions": [{"name": "accept", "from": ["placed"], '
            '"to": "accepted", "roles": ["merchant"]}]}}\n'
            "- The entity MUST have the named field, as a string field, in its 'fields'.\n"
            "- State and transition names are lower_snake_case. Every 'to' and 'from' must be one "
            "of the declared states, and every role must be one of the app's roles.\n"
            "- Leave 'capabilities' as [] when the product has no lifecycle.\n"
        )
    if "ownership" in CAPABILITY_KINDS.implemented():
        # R-570: whose records are whose.
        capability_rules += (
            "\nOwnership (optional, use when users must not see or change each other's records):\n"
            "- Every record a signed-in user creates remembers who created them. A 'capabilities' "
            "entry of kind 'ownership' narrows an entity to its creator: private notes, a "
            "customer's own orders, a user's own expenses.\n"
            '- Shape: {"kind": "ownership", "name": "note_ownership", "config": {"entity": "Note", '
            '"read": "own", "write": "own", "see_all": ["manager"]}}\n'
            "- read 'own': each user lists and opens only the records they created; read 'all': "
            "everyone can read them. write 'own': only the creator may edit or delete. see_all: "
            "roles that see and change every record (admin always does).\n"
            "- A public catalogue (products, posts) is read 'all', write 'own'.\n"
            "- Records assigned to someone who did not create them (a courier's deliveries, an "
            "agent's tickets): add an 'assignee' naming a uuid field that holds that user's id, e.g. "
            '{"entity": "Order", "read": "own", "write": "own", "see_all": ["dispatcher"], '
            '"assignee": "driver_id"} with a uuid field driver_id on Order. The assignee sees and '
            "works on what is assigned to them; see_all roles assign.\n"
            "- When people pay for something (an order, a booking, a ticket), add ONE 'money' "
            "capability: {\"kind\": \"money\", \"name\": \"app_money\", \"config\": {\"currency\": "
            "\"INR\", \"charges\": [{\"entity\": \"Order\", \"amount\": \"total_amount\", \"payee\": "
            "\"vendor_id\"}], \"commission_bps\": 1000, \"refund_roles\": [\"manager\"]}}. amount is the "
            "entity's float price field; payee (optional) a uuid field naming the user who earns the sale "
            "(a vendor, a driver) - then commission_bps is the platform's share (1000 = 10%). The app "
            "gets checkout, a ledger, refunds and payouts; do not model Payment or Transaction entities.\n"
            "- Do NOT declare a User or Account entity: every app with sign-in already has accounts "
            "(email, password, role) and records who created each record. A profile with real data "
            "(bio, avatar) may be an entity named Profile, never holding a password.\n"
        )
    if "jobs" in CAPABILITY_KINDS.implemented():
        # R-568: what the app does on its own, on a clock.
        capability_rules += (
            "\nScheduled jobs (optional, only when the prompt asks for something to happen on its own):\n"
            "- 'cancel unpaid orders after 30 minutes', 'mark invoices overdue once the due date "
            "passes', 'delete drafts older than 30 days': add ONE 'jobs' capability with a schedule "
            "per rule: {\"kind\": \"jobs\", \"name\": \"app_jobs\", \"config\": {\"schedules\": [{\"name\": "
            "\"cancel_unpaid_orders\", \"entity\": \"Order\", \"every\": \"5m\", \"where\": {\"paid\": [false]}, "
            "\"older_than\": {\"field\": \"created_at\", \"age\": \"30m\"}, \"do\": {\"transition\": \"cancel\"}}]}}\n"
            "- every: how often to look, 1m to 7d (\"5m\", \"1h\", \"1d\"). where: a field and the values "
            "it must hold. older_than: a datetime field and an age (\"0m\" means the time has passed - "
            "a due date). At least one of where/older_than.\n"
            "- do: {\"transition\": <a transition of the entity's workflow>}, {\"set\": {\"is_overdue\": "
            "true}} (never the workflow's own field) or {\"delete\": true}.\n"
            "- Reminders and emails are not scheduled jobs yet; do not invent them.\n"
        )
    field_types = ", ".join(t.value for t in FieldType)
    # R-559: what may be *offered* comes from the adapter registry, not from the enum. Naming
    # `flutter` here told the model to choose a profile the assembler then discarded, which is how
    # the silent drop began. The enum keeps every value so an explicit request can still be
    # recorded; the instruction below is what stops us recommending one.
    from ..codegen.capabilities import offerable_mobile_profiles

    mobile_profiles = ", ".join(offerable_mobile_profiles())
    web_strategies = ", ".join(w.value for w in WebStrategy)
    admin_strategies = ", ".join(a.value for a in AdminStrategy)
    backend_strategies = ", ".join(b.value for b in BackendStrategy)
    database_strategies = ", ".join(d.value for d in DatabaseStrategy)
    repo_strategies = ", ".join(r.value for r in RepoStrategy)
    return (
        "You are the intake compiler for OmniStackAI, an AI app-generation platform.\n"
        "Convert the user's application description into a single Application IR JSON object.\n"
        "\n"
        "Core Architecture Rules:\n"
        "- Output ONLY one JSON object. No prose, no explanation, no markdown code fences.\n"
        "- Keep JSON compact and avoid unnecessary verbosity or whitespace so it parses cleanly within token limits.\n"
        f'- It MUST match the structure of the template below exactly, including "schema_version": '
        f"{IR_SCHEMA_VERSION}.\n"
        "- Use PascalCase for entity names (e.g. Product, CartItem, CustomerReview, Appointment, TaskItem).\n"
        "- Use lower_snake_case identifiers for field names, roles, and screen ids.\n"
        f"- Every field 'type' MUST be EXACTLY one of: {field_types}. Do NOT invent other types.\n"
        "  For a status/category/enum-like field use \"string\". For money use \"float\". For an id use \"uuid\".\n"
        # PC-102: what a file field accepts follows the requirement, not one fixed type.
        "  For a file people upload (a resume, photos, an invoice, a report, a contract) use \"attachment\" and say\n"
        "  what it accepts in the field's 'validation' - the types the requirement needs, never one fixed type:\n"
        "  e.g. resume [\"accept:pdf|word\", \"max_size_mb:10\"], product photos [\"accept:images\", \"max_files:8\"],\n"
        "  invoice [\"accept:pdf|images|spreadsheets\"]. Groups: images, documents, pdf, word, spreadsheets,\n"
        "  presentations, audio, video, archives, medical; or extensions such as pdf|docx|xlsx|csv.\n"
        # PC-104: formatted content.
        "  For long formatted content people write (an article or blog post body, a product, job or course\n"
        "  description, notes with headings and lists) use \"rich_text\"; for short plain text use \"string\"/\"text\".\n"
        "- In an api 'path', use lower_snake_case for literal segments and camelCase for any {param} "
        "placeholder (e.g. {productId}, not {product_id}), matching the template below.\n"
        "\n"
        "Feature Completeness & 1:1 Full-Stack Triad:\n"
        "- For EVERY feature or capability requested by the user (e.g., product grid, shopping cart, discounts, reviews, wishlist, booking, messaging):\n"
        "  1. Database Entity: Model a dedicated Entity with realistic, complete fields and relations.\n"
        "  2. API Endpoints: Define the necessary REST endpoints (list, get, create, update, delete).\n"
        "  3. Screens: Define interactive, user-facing screens corresponding to each workflow.\n"
        "  Never drop, skip, or omit any user-specified feature.\n"
        "\n"
        "Universal Domain Archetype Expansion (For Short Prompts):\n"
        "- If the user gives a concise, generic, or high-level prompt (e.g., 'Create an e-commerce platform', 'Build a clinic management app', 'Create a project tracker', 'Make an invoicing system', 'Build a gym fitness platform', 'Create a real estate portal'):\n"
        "  You MUST intelligently expand the domain into a comprehensive, production-grade 4 to 7 entity architecture.\n"
        "  Examples:\n"
        "  * E-Commerce: Product, Category, CartItem, Order, CustomerReview, Discount\n"
        "  * Healthcare / Clinic: Patient, Provider, Appointment, MedicalRecord, Prescription\n"
        "  * SaaS / Project Management: Workspace, Project, Task, TaskComment, TeamMember\n"
        "  * FinTech / Invoicing: Client, Invoice, LineItem, PaymentRecord, Expense\n"
        "  * Real Estate: PropertyListing, Agent, TourBooking, ClientInquiry, Review\n"
        "  * Education / LMS: Course, Module, Lesson, StudentEnrollment, QuizSubmission\n"
        "  * Hospitality / Restaurant: MenuItem, MenuCategory, TableBooking, CustomerOrder, Review\n"
        "  * Logistics / Fleet: Vehicle, Driver, DeliveryRoute, DispatchOrder, MaintenanceLog\n"
        "  Do NOT emit a shallow 1-entity stub when the user asks for a complete platform.\n"
        "\n"
        "Project Strategy Rules:\n"
        "- In 'project_strategy', use only allowed canonical values:\n"
        f"  * 'mobile_profile': {mobile_profiles} (choose 'react_native' if the user requested a mobile\n"
        "    app; it is the only mobile framework this platform generates today. If the user\n"
        "    explicitly named a framework we do not generate, such as Flutter or native\n"
        "    Swift/Kotlin, record what they asked for anyway — the build substitutes React Native\n"
        "    and explains why, and keeping the request lets us rebuild it when that stack ships.)\n"
        f"  * 'web_strategy': {web_strategies}\n"
        f"  * 'admin_strategy': {admin_strategies} (choose 'nextjs' if the user requested an admin dashboard/panel)\n"
        f"  * 'backend_strategy': {backend_strategies} (choose 'go' if the user requested Go/golang; default to 'python')\n"
        f"  * 'database_strategy': {database_strategies}\n"
        f"  * 'repo_strategy': {repo_strategies}\n"
        f"{capability_rules}"
        "\n"
        "Template Schema Reference (copy this JSON shape; replace the content with the expanded domain):\n"
        f"{template}\n"
    )


def build_intake_messages(
    prompt: str,
    *,
    example_name: str = DEFAULT_TEMPLATE_EXAMPLE,
    context_text: str | None = None,
) -> tuple[Message, ...]:
    """Build the (system, user) messages instructing a model to emit an Application IR."""
    cleaned = prompt.strip()
    if not cleaned:
        raise IntakeError("prompt must be a non-empty application description")
    system_text = _system_instruction(example_name).strip()
    if context_text and context_text.strip():
        system_text = f"{context_text.strip()}\n\n{system_text}"
    user = (
        "Application description:\n"
        f"{cleaned}\n\n"
        "Return only the Application IR JSON object."
    )
    return (
        Message(ChatRole.SYSTEM, system_text),
        Message(ChatRole.USER, user.strip()),
    )


def _extract_json_object(text: str) -> str:
    """Pull the outermost JSON object out of raw model text (fences/prose tolerated)."""
    stripped = text.strip()
    if not stripped:
        raise IntakeResponseError("model returned an empty response")
    if "```" in stripped:
        fence = stripped.find("```")
        newline = stripped.find("\n", fence)
        if newline != -1:
            close = stripped.find("```", newline)
            if close != -1:
                stripped = stripped[newline + 1 : close].strip()
    open_idx = stripped.find("{")
    close_idx = stripped.rfind("}")
    if open_idx == -1:
        raise IntakeResponseError("model response did not contain a JSON object")
    if close_idx == -1 or close_idx < open_idx:
        return stripped[open_idx:]
    return stripped[open_idx : close_idx + 1]


def _close_truncated_json(text: str) -> str:
    """Balance unclosed quotes and brackets/braces if the model output was truncated."""
    in_str = False
    escape = False
    stack: list[str] = []
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack and ((ch == "}" and stack[-1] == "{") or (ch == "]" and stack[-1] == "[")):
                stack.pop()

    closing = ""
    if in_str:
        closing += '"'
    while stack:
        opener = stack.pop()
        closing += "}" if opener == "{" else "]"
    return text + closing


def _clean_json_syntax(text: str) -> str:
    """Strip comments, trailing commas, and insert missing commas across lines outside strings."""
    text = re.sub(r"//.*$", "", text, flags=re.MULTILINE)

    result: list[str] = []
    in_string = False
    escape = False
    lines = text.split("\n")
    for i, line in enumerate(lines):
        result.append(line)
        for ch in line:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = not in_string
        if not in_string and i + 1 < len(lines):
            stripped_curr = line.rstrip()
            next_line = lines[i + 1].lstrip()
            if stripped_curr and next_line:
                last_char = stripped_curr[-1]
                first_char = next_line[0]
                if last_char in ('"', "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "e", "l", "}", "]") and last_char != ",":
                    if first_char in ('"', "{", "[") and not stripped_curr.endswith(("{", "[", ":", ",")):
                        result[-1] = stripped_curr + ","

    cleaned = "\n".join(result)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _robust_json_decode(payload: str) -> dict:
    """Decode JSON with multi-pass repair for quotes, comments, missing commas, and truncation."""
    try:
        return json.loads(payload, strict=False)
    except Exception:
        pass

    cleaned = _clean_json_syntax(payload)
    try:
        return json.loads(cleaned, strict=False)
    except Exception:
        pass

    closed = _close_truncated_json(cleaned)
    try:
        return json.loads(closed, strict=False)
    except Exception:
        pass

    curr = closed
    for _ in range(30):
        try:
            return json.loads(curr, strict=False)
        except json.JSONDecodeError as err:
            pos = err.pos
            found = False
            if "delimiter" in err.msg:
                q_pos = curr.rfind('"', 0, pos)
                if q_pos != -1 and (q_pos == 0 or curr[q_pos - 1] != "\\"):
                    curr = curr[:q_pos] + '\\"' + curr[q_pos + 1:]
                    found = True
            if not found:
                for p in range(max(0, pos - 6), min(len(curr), pos + 6)):
                    if curr[p] == '"' and (p == 0 or curr[p - 1] != "\\"):
                        curr = curr[:p] + '\\"' + curr[p + 1:]
                        found = True
                        break
            if not found:
                break

    return json.loads(curr, strict=False)


_FIELD_TYPE_ALIASES: dict[str, str] = {
    "str": "string",
    "varchar": "string",
    "char": "string",
    "text": "text",
    "integer": "int",
    "bigint": "int",
    "smallint": "int",
    "number": "float",
    "decimal": "float",
    "double": "float",
    "real": "float",
    "numeric": "float",
    "currency": "float",
    "money": "float",
    "boolean": "bool",
    "timestamp": "datetime",
    "date": "datetime",
    "time": "datetime",
    "id": "uuid",
    "dict": "json",
    "object": "json",
    "array": "json",
    "list": "json",
}



def _labels(items: Any, keys: tuple[str, ...]) -> list[str]:
    """Plain strings from a model's list, unwrapping objects to their first named key.

    PC-006, seen live: Groq wrote navigation as ``{"target": "category_editor", "action": "create"}``.
    ``str()`` of that became a link to ``/{'target': ...}`` and a page that did not compile.
    """
    out: list[str] = []
    for item in items if isinstance(items, (list, tuple)) else ():
        if isinstance(item, dict):
            item = next((item[k] for k in keys if isinstance(item.get(k), str) and item[k].strip()), "")
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _to_snake(val: str, default: str = "item") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", str(val)).strip("_").lower()
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"item_{cleaned}" if cleaned else default
    return cleaned[:64]


def _sanitize_ir_dict(data: dict) -> dict:
    """Coerce common LLM syntax variances into strict Application IR schemas."""
    # If the payload is completely devoid of entities and project_strategy,
    # it is not an IR payload (e.g. invalid test input like '{"name": "x"}').
    if "project_strategy" not in data and "entities" not in data:
        return data

    data.setdefault("schema_version", IR_SCHEMA_VERSION)

    # Name & Description
    raw_name = data.get("name") or data.get("app_name") or data.get("title")
    if not raw_name or not str(raw_name).strip():
        if data.get("entities") and isinstance(data["entities"], list) and data["entities"]:
            first_entity = data["entities"][0].get("name", "Workspace") if isinstance(data["entities"][0], dict) else "Workspace"
            raw_name = f"{first_entity} Manager"
        else:
            raw_name = "Modern Application"
    data["name"] = str(raw_name).strip()

    raw_desc = data.get("description")
    if not raw_desc or not str(raw_desc).strip():
        data["description"] = f"Production workspace for {data['name']}"
    data["description"] = str(data["description"]).strip()

    # Platforms
    if "platforms" not in data or not data["platforms"]:
        data["platforms"] = ["web", "backend"]

    # Project strategy
    if "project_strategy" not in data or not isinstance(data["project_strategy"], dict):
        data["project_strategy"] = {
            "mobile_profile": "none",
            "web_strategy": "nextjs",
            "admin_strategy": "nextjs",
            "backend_strategy": "python",
            "database_strategy": "postgres",
            "repo_strategy": "customer_project_monorepo",
        }
    else:
        strat = data["project_strategy"]
        strat.setdefault("mobile_profile", "none")
        strat.setdefault("web_strategy", "nextjs")
        strat.setdefault("admin_strategy", "nextjs")
        strat.setdefault("backend_strategy", "python")
        strat.setdefault("database_strategy", "postgres")
        strat.setdefault("repo_strategy", "customer_project_monorepo")

        # R-541: this used to force web_strategy back to 'nextjs' whenever an admin panel was
        # asked for, because the assembler had no admin adapter and the console could only be
        # smuggled into apps/web. Both apps are assembled properly now, so an admin-only request
        # stays admin-only instead of gaining a public website nobody asked for.

    # Roles
    if "roles" not in data or not isinstance(data["roles"], list) or not data["roles"]:
        data["roles"] = [
            {"id": "admin", "description": "Administrator with full access"},
            {"id": "user", "description": "Standard user access"},
        ]
    else:
        valid_roles = []
        for r in data["roles"]:
            if not isinstance(r, dict):
                continue
            r["id"] = _to_snake(r.get("id", "user"))
            r["description"] = str(r.get("description", "Role")).strip() or "Role"
            valid_roles.append(r)
        if not valid_roles:
            valid_roles = [
                {"id": "admin", "description": "Administrator with full access"},
                {"id": "user", "description": "Standard user access"},
            ]
        data["roles"] = valid_roles

    # APIs
    if "apis" in data and isinstance(data["apis"], list):
        valid_apis = []
        for api in data["apis"]:
            if not isinstance(api, dict):
                continue
            method = str(api.get("method", "GET")).strip().upper()
            if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                method = "GET"
            api["method"] = method

            path = str(api.get("path", "/")).strip()
            if not path.startswith("/"):
                path = f"/{path}"
            api["path"] = path

            raw_auth = api.get("auth", True)
            if isinstance(raw_auth, str):
                api["auth"] = raw_auth.strip().lower() not in ("false", "0", "no", "none", "public")
            elif not isinstance(raw_auth, bool):
                api["auth"] = bool(raw_auth)

            roles = api.get("required_roles", ())
            if isinstance(roles, (list, tuple)):
                cleaned_roles = [_to_snake(r) for r in roles if str(r).strip()]
                if cleaned_roles and not api["auth"]:
                    api["auth"] = True
                api["required_roles"] = cleaned_roles
            else:
                api["required_roles"] = []
            valid_apis.append(api)
        data["apis"] = valid_apis

    # Screens
    if ("screens" not in data or not isinstance(data["screens"], list) or not data["screens"]) and data.get("entities"):
        screens = []
        for ent in data["entities"]:
            if not isinstance(ent, dict):
                continue
            e_name = ent.get("name", "Item")
            e_slug = _to_snake(e_name)
            screens.append({
                "id": f"{e_slug}_list",
                "role": "user",
                "components": ["list"],
                "actions": ["view", "delete"],
                "navigation": [f"{e_slug}_editor"],
            })
            screens.append({
                "id": f"{e_slug}_editor",
                "role": "user",
                "components": ["form"],
                "actions": ["create", "edit"],
                "navigation": [f"{e_slug}_list"],
            })
        data["screens"] = screens
    elif "screens" in data and isinstance(data["screens"], list):
        valid_screens = []
        role_ids = {r["id"] for r in data.get("roles", []) if isinstance(r, dict)}
        for s in data["screens"]:
            if not isinstance(s, dict):
                continue
            s["id"] = _to_snake(s.get("id", "screen"))
            s_role = _to_snake(s.get("role", "user"))
            if s_role not in role_ids and role_ids:
                data.setdefault("roles", []).append({"id": s_role, "description": f"{s_role.capitalize()} role"})
                role_ids.add(s_role)
            s["role"] = s_role
            s["components"] = _labels(s.get("components", ()), ("name", "type", "id", "component"))
            s["actions"] = _labels(s.get("actions", ()), ("name", "action", "id", "label"))
            s["navigation"] = [
                _to_snake(n) for n in _labels(s.get("navigation", ()), ("target", "screen", "to", "id"))
            ]
            valid_screens.append(s)
        # PC-006: a link to a screen that does not exist is a 404 the user finds by clicking it.
        screen_ids = {s["id"] for s in valid_screens}
        for s in valid_screens:
            s["navigation"] = list(dict.fromkeys(n for n in s["navigation"] if n in screen_ids))
        data["screens"] = valid_screens

    # Entities
    valid_field_types = {t.value for t in FieldType}
    if "entities" in data and isinstance(data["entities"], list):
        valid_entities = []
        for e in data["entities"]:
            if not isinstance(e, dict):
                continue
            raw_name = str(e.get("name", "Item")).strip()
            e["name"] = re.sub(r"[^a-zA-Z0-9]+", "", raw_name) or "Item"
            if "fields" in e and isinstance(e["fields"], list):
                valid_fields = []
                for f in e["fields"]:
                    if not isinstance(f, dict):
                        continue
                    f["name"] = _to_snake(f.get("name", "field"))
                    raw_type = str(f.get("type", "string")).strip().lower()
                    if raw_type in valid_field_types:
                        f["type"] = raw_type
                    elif raw_type in _FIELD_TYPE_ALIASES:
                        f["type"] = _FIELD_TYPE_ALIASES[raw_type]
                    else:
                        f["type"] = "string"
                    f["primary_key"] = bool(f.get("primary_key", False))
                    f["nullable"] = bool(f.get("nullable", False))
                    f["unique"] = bool(f.get("unique", False))
                    f["indexed"] = bool(f.get("indexed", False))
                    valid_fields.append(f)
                e["fields"] = valid_fields
            valid_entities.append(e)
        data["entities"] = valid_entities

    # Roles
    if "roles" in data and isinstance(data["roles"], list):
        valid_roles = []
        for r in data["roles"]:
            if not isinstance(r, dict):
                continue
            r["id"] = _to_snake(r.get("id", "user"))
            r["description"] = str(r.get("description", "Role")).strip() or "Role"
            valid_roles.append(r)
        data["roles"] = valid_roles

    return data


def parse_ir_response(text: str) -> ApplicationIR:
    """Parse raw model text into a validated, normalized ApplicationIR.

    Raises IntakeResponseError when the text is not JSON or does not describe a
    structurally valid IR.
    """
    return parse_ir_response_with_repairs(text)[0]


def parse_ir_response_with_repairs(text: str) -> tuple[ApplicationIR, tuple[str, ...]]:
    """`parse_ir_response`, plus a note for each repair made instead of rejecting (PC-093)."""
    payload = _extract_json_object(text)
    try:
        data = _robust_json_decode(payload)
    except json.JSONDecodeError as error:
        raise IntakeResponseError(f"model response was not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise IntakeResponseError("model response JSON was not an object")
    # PC-094: a malformed part (a string where an object belongs, a list where a name belongs)
    # crashed intake with an AttributeError, which no caller expects. It is a bad answer like any
    # other: a clean IntakeResponseError the fallback chain and the user can act on.
    try:
        data = _sanitize_ir_dict(data)
        data, repairs = repair_ir_dict(data)
        ir = ApplicationIR.from_dict(data)
    except (ApplicationIRError, ValueError, TypeError, KeyError, AttributeError, IndexError) as error:
        raise IntakeResponseError(
            f"model response was not a valid Application IR: {type(error).__name__}: {error}"
        ) from error
    return normalize_ir(ir), repairs


def _with_prompt_ownership(ir: ApplicationIR, prompt: str) -> tuple[ApplicationIR, tuple[str, ...]]:
    """R-570: rules for what the prompt itself calls private, when the plan left them out; R-567:
    the same for money the prompt says is paid; R-568: for what it says happens on its own."""
    from .jobs_intent import jobs_from_prompt
    from .money_intent import money_from_prompt
    from .ownership_intent import ownership_from_prompt

    data = ir.to_dict()
    notes = ownership_from_prompt(prompt, data) + money_from_prompt(prompt, data) + jobs_from_prompt(prompt, data)
    if not notes:
        return ir, ()
    return ApplicationIR.from_dict(data), tuple(notes)


async def generate_ir(
    prompt: str,
    provider: ModelProvider,
    *,
    model_id: str,
    example_name: str = DEFAULT_TEMPLATE_EXAMPLE,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    context: dict[str, Any] | str | None = None,
) -> IntakeResult:
    """Compile a natural-language prompt into a validated Application IR via ``provider``.

    Raises IntakeResponseError if the model output cannot be parsed into a structurally
    valid IR, or if the resulting IR fails semantic validation.
    """
    context_text = ""
    is_truncated = False
    active_skills: list[str] = []
    truncated_skills: list[str] = []
    if isinstance(context, dict):
        context_text, is_truncated, active_skills, truncated_skills = assemble_context(context)
    elif isinstance(context, str):
        context_text = context

    messages = build_intake_messages(prompt, example_name=example_name, context_text=context_text)
    request = GenerateRequest(
        _REQUEST_ID,
        ModelRef(provider.provider_id, model_id),
        messages,
        max_output_tokens,
        timeout_seconds,
    )
    response = await provider.generate(request)
    ir, repairs = parse_ir_response_with_repairs(response.text)
    ir, owned = _with_prompt_ownership(ir, prompt)
    repairs = repairs + owned
    issues = validate_ir(ir)
    if has_errors(issues):
        detail = "; ".join(
            f"{issue.location}: {issue.message}"
            for issue in issues
            if issue.severity is Severity.ERROR
        )
        raise IntakeResponseError(f"generated IR failed validation: {detail}")
    return IntakeResult(
        ir=ir,
        issues=issues,
        raw_text=response.text,
        context_truncated=is_truncated,
        active_skills=tuple(active_skills),
        truncated_skills=tuple(truncated_skills),
        repairs=repairs,
    )


async def generate_ir_stream(
    prompt: str,
    provider: ModelProvider,
    *,
    model_id: str,
    example_name: str = DEFAULT_TEMPLATE_EXAMPLE,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    context: dict[str, Any] | str | None = None,
) -> AsyncIterator[str | IntakeResult]:
    """Streaming twin of `generate_ir` (R-484): yields raw text deltas as they arrive from the
    model via `provider.stream()`, then yields the final `IntakeResult` once the complete response
    has been parsed and validated exactly like `generate_ir` does.
    """
    context_text = ""
    is_truncated = False
    active_skills: list[str] = []
    truncated_skills: list[str] = []
    if isinstance(context, dict):
        context_text, is_truncated, active_skills, truncated_skills = assemble_context(context)
    elif isinstance(context, str):
        context_text = context

    messages = build_intake_messages(prompt, example_name=example_name, context_text=context_text)
    request = GenerateRequest(
        _REQUEST_ID,
        ModelRef(provider.provider_id, model_id),
        messages,
        max_output_tokens,
        timeout_seconds,
    )
    chunks: list[str] = []
    active = provider
    while True:
        chunks = []
        try:
            async for event in active.stream(request):
                if event.delta:
                    chunks.append(event.delta)
                    yield event.delta
            break
        except Exception as error:  # noqa: BLE001 - re-raised unless another provider can answer
            # PC-106, seen live: a free provider timed out (or was rate-limited) after its answer
            # had started, and the build failed with providers left untried. The plan is parsed as
            # one document, so the partial answer is dropped and the request starts again.
            after = getattr(active, "after", None)
            failed = getattr(active, "last_provider_id", None)
            rest = after(failed, error) if callable(after) else None
            if rest is None:
                raise
            yield (f"\n\n[{failed} stopped part-way ({type(error).__name__}); starting the plan again "
                   f"with {rest.provider_id}]\n\n")
            active = rest
    if active is not provider and hasattr(provider, "last_provider_id"):
        # The build record names the provider that wrote the plan, not the one that stopped.
        provider.last_provider_id = active.last_provider_id
    text = "".join(chunks)
    ir, repairs = parse_ir_response_with_repairs(text)
    ir, owned = _with_prompt_ownership(ir, prompt)
    repairs = repairs + owned
    issues = validate_ir(ir)
    if has_errors(issues):
        detail = "; ".join(
            f"{issue.location}: {issue.message}"
            for issue in issues
            if issue.severity is Severity.ERROR
        )
        raise IntakeResponseError(f"generated IR failed validation: {detail}")
    yield IntakeResult(
        ir=ir,
        issues=issues,
        raw_text=text,
        context_truncated=is_truncated,
        active_skills=tuple(active_skills),
        truncated_skills=tuple(truncated_skills),
        repairs=repairs,
    )
