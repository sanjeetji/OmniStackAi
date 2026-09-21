"""Grounded hybrid LLM UI synthesizer with a bounded repair loop and deterministic fallback (R-462, R-465).

The hybrid engine: a model writes the modern Next.js UI, but it is GROUNDED in the deterministic typed
data layer the customer project actually ships — the real ``lib/types.ts`` / ``lib/hooks.ts`` / ``lib/api.ts``
surface (parsed from the same generators, so it cannot drift), the real ``components/*`` export names, and the
real ``styles/tokens.css`` design-token names. The model owns look and features; the deterministic core owns
correctness (DB, API, auth, data wiring).

Guarantees:
1. The model can only import what exists (strict whitelist, multi-line aware; no ``require``/dynamic import).
2. Validator rejection feeds the reason back to the model and retries (bounded, ``max_attempts``); provider
   exceptions never retry. Exhaustion falls back to the deterministic template with no marker.
3. A JSON-safe, secret-free ``UiSynthesisOutcome`` per file records mode / attempts / last reason.
4. Model calls are opt-in: with ``provider=None`` everything is the deterministic template (``task verify``
   uses in-memory stubs — 0 real calls).
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from ..application_ir import ApplicationIR, Screen
    from ..model_gateway.contracts import ModelProvider, ModelRef

logger = logging.getLogger(__name__)

# Bare packages the generated project actually installs. Anything else that merely *starts* with "react"
# (react-icons, react-query, ...) is NOT installed and is rejected.
ALLOWED_EXACT_IMPORTS: frozenset[str] = frozenset({
    "react",
    "react-dom",
    # UI stack shipped by the code generator (Tailwind / shadcn ecosystem).
    "lucide-react",
    "clsx",
    "class-variance-authority",
    "tailwind-merge",
})
# Allowed import prefixes: platform modules, relative paths, and Radix UI primitives used by shadcn.
ALLOWED_IMPORT_PREFIXES: tuple[str, ...] = (
    "@/components/",  # includes @/components/ui/* (shadcn primitives)
    "@/lib/",
    "next/",
    "./",
    "../",
    "@radix-ui/",  # lean Radix primitives (react-slot, etc.) bundled with shadcn components
)

MARKER_PREFIX = "// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI"
DEFAULT_MAX_ATTEMPTS = 3
# The prior output echoed back on a repair turn. Kept lean: a live Groq run showed a full echo (~4k tokens)
# can push the repair request past a small tokens-per-minute quota; the rejection reason is already precise.
_MAX_ECHO_CHARS = 8_000
_SYSTEM_MESSAGE = (
    "You are an expert Next.js full-stack UI designer. Respond only with valid, executable TypeScript React code."
)

# Curated prop hints for the most-used components. The FULL, real export list is injected by
# nextjs.summarize_components (derived from the shipped component files), so the model never guesses names.
COMPONENT_PROP_HINTS = """KEY COMPONENT PROPS:
SHADCN UI PRIMITIVES (from '@/components/ui/<file>' — prefer these for common elements):
- Button: import { Button } from '@/components/ui/button';  { variant?: 'default'|'destructive'|'outline'|'secondary'|'ghost'|'link', size?: 'default'|'sm'|'lg'|'icon', asChild?: boolean }
- Card/CardHeader/CardTitle/CardDescription/CardContent/CardFooter: import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
- Input: import { Input } from '@/components/ui/input';  standard <input> with Tailwind ring/border styling
- Badge: import { Badge } from '@/components/ui/badge';  { variant?: 'default'|'secondary'|'destructive'|'outline'|'success'|'warning' }
- Label: import { Label } from '@/components/ui/label'
- Separator: import { Separator } from '@/components/ui/separator';  { orientation?: 'horizontal'|'vertical' }
- Skeleton: import { Skeleton } from '@/components/ui/skeleton';  pass className for sizing e.g. className="h-4 w-32"
- Alert/AlertTitle/AlertDescription: import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';  { variant?: 'default'|'destructive' }
- cn() helper: import { cn } from '@/lib/utils';  merges Tailwind classes conditionally
- Icons: import { LayoutDashboard, Users, Settings, Bell, Search, ChevronDown, Loader2, Plus, Pencil, Trash2, Eye, EyeOff, X, Check, AlertCircle, Info, TrendingUp, TrendingDown } from 'lucide-react';
RICH CUSTOM COMPONENTS (from '@/components/<file>' — for advanced/data-heavy UI):
- StatCard compound: <StatCard><StatCardHeader title="Label" icon="📊" /><StatCardValue value="123" subtext="info" /></StatCard>
- DataGrid: { columns: Array<{ key: string, header: string }>, data: any[], sortable?: boolean }  (columns use `header`, never `label`)
- Tabs: { tabs: Array<{ id: string, label: string }>, activeTab: string, onChange: (id: string) => void }
- Avatar: { name?: string, src?: string, size?: 'sm' | 'md' | 'lg' }
- Progress: { value: number, max?: number, variant?: string }
- Dialog: { open?: boolean, onOpenChange?: (open: boolean) => void, children: ReactNode }  (use `open`, never `isOpen`)
- EmptyState: { title: string, description?: string, actionLabel?: string, onAction?: () => void }
- Rating: { value: number, max?: number, onChange?: (val: number) => void, readOnly?: boolean }
- Toast: useToast() => { toast: (opts: { title: string, description?: string, variant?: 'default' | 'success' | 'destructive' }) => void }
"""

_ADMIN_ARCHETYPE = """ARCHETYPE: MODERN SAAS ADMIN PANEL
Design a complete SaaS Admin Panel using shadcn ui/ components and Tailwind classes:
1. Left Collapsible Sidebar: Logo badge, title, collapse toggle, links with Lucide icons (Dashboard, Users, Settings), active pills.
2. Top Bar (sticky, border-b): Global search <Input>, Bell icon, User Avatar with dropdown (profile, settings, sign out).
3. Main Grid: Metric cards with shadcn <Card>, <DataGrid> table, filter bar with '+ Add [Entity]' <Button>, loading skeletons."""

_WEBSITE_ARCHETYPE = """ARCHETYPE: MODERN PUBLIC WEBSITE / E-COMMERCE
Design a consumer web experience using shadcn ui/ components and Tailwind:
1. Sticky Header: Brand logo, links, search <Input>, auth <Button>.
2. Hero Banner: Bold headline, value prop, CTA <Button>s, floating metric chips.
3. Feature Showcase: Responsive grid (grid-cols-1 md:grid-cols-3 gap-6) with shadcn <Card>s, badges, and action buttons.
4. Testimonials: shadcn <Card>s with <Avatar> and rating stars.
5. Footer: Sitemap links and copyright."""

_DYNAMIC_IMPORT_RE = re.compile(r"\b(?:require|import)\s*\(")
_QUOTED_SOURCE_RE = re.compile(r"""['"]([^'"]+)['"]""")
_FROM_SOURCE_RE = re.compile(r"""from\s+['"]([^'"]+)['"]""")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _iter_import_sources(content: str):
    """Yield the module source of every static import statement, joining multi-line statements.

    A statement starts on a line beginning with ``import`` and is accumulated until a quoted module source
    appears; it never spans into the next ``import`` line, so a side-effect import cannot hide behind a later,
    allowed one.
    """
    lines = content.splitlines()
    i = 0
    total = len(lines)
    while i < total:
        stripped = lines[i].strip()
        if stripped.startswith("import ") or stripped.startswith("import{") or stripped == "import":
            statement = stripped
            end = i
            while (
                not _QUOTED_SOURCE_RE.search(statement)
                and end + 1 < total
                and not lines[end + 1].strip().startswith("import")
            ):
                end += 1
                statement += " " + lines[end].strip()
            match = _FROM_SOURCE_RE.search(statement)
            if match:
                yield match.group(1)
            else:
                side_effect = _QUOTED_SOURCE_RE.search(statement)
                if side_effect:
                    yield side_effect.group(1)
            i = end + 1
            continue
        i += 1


def _import_allowed(module_name: str) -> bool:
    if module_name in ALLOWED_EXACT_IMPORTS:
        return True
    return any(module_name.startswith(prefix) for prefix in ALLOWED_IMPORT_PREFIXES)


def clean_and_validate_jsx(raw: str) -> tuple[bool, str, str]:
    """Strip markdown code blocks and validate import safety and basic syntax.

    Returns:
        (is_valid, cleaned_code, rejection_reason)
    """
    if not raw or not raw.strip():
        return False, "", "Response is empty"

    content = raw.strip()

    # 1. Strip markdown code fences if model enclosed in ```tsx ... ```
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    if not content:
        return False, "", "Content empty after stripping code fences"

    # 2. Ensure "use client" is at the top
    if not content.startswith('"use client"') and not content.startswith("'use client'"):
        content = '"use client";\n\n' + content

    # 3. Validate EVERY static import (multi-line aware) against the whitelist; forbid dynamic loading.
    for module_name in _iter_import_sources(content):
        if not _import_allowed(module_name):
            return (
                False,
                "",
                f"Forbidden import '{module_name}'. Only react, react-dom, next/*, @/lib/*, @/components/* "
                "and relative imports exist in this project.",
            )
    if _DYNAMIC_IMPORT_RE.search(content):
        return False, "", "Dynamic import() / require() is not allowed. Use static imports from the approved modules only."

    # 4. Check for strict bracket balance and closing brace to prevent truncated code
    open_curly = content.count("{")
    close_curly = content.count("}")
    if open_curly != close_curly:
        return False, "", f"Mismatched curly braces: {open_curly} open vs {close_curly} closed (file is truncated)"

    open_paren = content.count("(")
    close_paren = content.count(")")
    if open_paren != close_paren:
        return False, "", f"Mismatched parentheses: {open_paren} open vs {close_paren} closed (file is truncated)"

    trimmed = content.rstrip()
    if not trimmed.endswith("}") and not trimmed.endswith("};"):
        return False, "", "File is truncated: does not end with closing brace '}'"

    # 5. Must export default component
    if "export default function" not in content and "export default" not in content:
        return False, "", "Missing default export for page"

    return True, content, ""


# ---------------------------------------------------------------------------
# Prompt construction (grounded in the real generated project)
# ---------------------------------------------------------------------------


def _detect_ui_archetype(ir: ApplicationIR, user_prompt: str) -> str:
    """Detect whether the application is an 'admin_panel' or 'public_website'."""
    text = f"{user_prompt} {ir.name} {ir.description}".lower()
    website_keywords = (
        "landing page",
        "marketing website",
        "public website",
        "portfolio",
        "ecommerce",
        "online store",
        "fashion shop",
        "showcase",
    )
    if any(k in text for k in website_keywords) and not any(k in text for k in ("admin", "management", "backoffice")):
        return "public_website"
    return "admin_panel"


def _entities_block(ir: ApplicationIR) -> str:
    rows = [
        f"- Entity {entity.name} ({', '.join(f'{f.name}: {f.type.value}' for f in entity.fields)})"
        for entity in ir.entities
    ]
    return "\n".join(rows) or "- (no entities)"


def _grounding_blocks(
    ir: ApplicationIR,
    data_layer: str | None,
    components: str | None,
    design_tokens: str | None,
) -> str:
    """The three grounding blocks. Computed lazily from the real generators when not supplied.

    The lazy import is deliberate: nextjs.py imports this module lazily too, so only a module-level import
    would create a cycle.
    """
    from .nextjs import summarize_components, summarize_data_layer, summarize_design_tokens

    data_layer = data_layer if data_layer is not None else summarize_data_layer(ir)
    components = components if components is not None else summarize_components(ir)
    design_tokens = design_tokens if design_tokens is not None else summarize_design_tokens()
    return (
        "TYPED DATA LAYER — THE ONLY DATA ACCESS THAT EXISTS (generated code; use EXACTLY these names and signatures):\n"
        f"{data_layer}\n\n"
        f"{components}\n\n"
        f"{COMPONENT_PROP_HINTS}\n"
        f"{design_tokens}\n"
    )


def _core_rules(ir: ApplicationIR) -> str:
    from .auth_guard import needs_auth

    if needs_auth(ir):
        auth_rule = (
            "6. AUTH: `useAuth()` from '@/components/auth-provider' returns "
            "{ user: { id, email, full_name, role } | null, token, logout }; show `user?.full_name || user?.email`.\n"
        )
    else:
        auth_rule = (
            "6. AUTH: this app has NO auth provider — do NOT import '@/components/auth-provider' or call useAuth().\n"
        )
    return f"""CORE IMPLEMENTATION RULES:
1. Start with `"use client";`
2. IMPORTS: ONLY `react`, `react-dom`, `next/*` (e.g. next/link, next/navigation), `@/lib/hooks`, `@/lib/types`,
   `@/lib/api`, and the `@/components/<file>` modules listed above. No other package exists (no Tailwind, no icon
   libraries, no axios). Never use require() or dynamic import().
3. DATA ACCESS: use ONLY the hooks in the TYPED DATA LAYER with EXACTLY those signatures. List hooks expose
   `refetch()`, `setPage()`, `setPageSize()`, `setSearch()`, `setSort()` (and `setFilter()`/`clearFilters()` on
   collection lists); there is NO `refresh()`. List params are `{{ limit, offset, sort, order, q }}` — never
   page/pageSize as params. If the data layer says NO hooks exist, do not import '@/lib/hooks'.
4. NULL SAFETY: hook `data` can be null while loading — ALWAYS write `(data ?? []).map(...)`,
   `(data ?? []).filter(...)`, `data?.length ?? 0`.
5. STYLING: Use **Tailwind CSS utility classes** as the primary method. The design system CSS variables
   (`var(--color-*)', `var(--space-*)', `var(--radius-*)`) are bridged to Tailwind semantic names
   (bg-primary, text-foreground, border-border, etc.) so Tailwind classes automatically match the brand.
   Use `cn()` from '@/lib/utils' to merge classes conditionally. Use shadcn `@/components/ui/*`
   (Button, Card, Input, Badge, Label, Skeleton, Alert, Separator) for common UI elements. NEVER hardcode
   hex colors. Dark mode is automatic via CSS variables + Tailwind `dark:` variants.
{auth_rule}7. DATA GRID columns use `header` (never `label`); DIALOG uses `open`/`onOpenChange` (never `isOpen`);
   STAT CARDS use the compound form shown above.
8. ZERO PLACEHOLDERS: complete, functional JSX with real buttons, inputs, and loading / empty / error states.
   No `// TODO`.
9. CONCISE: keep the file under 300 lines so it is never truncated; it MUST end with the closing `}}` of the
   default export.
10. Output ONLY the raw TypeScript/React file content — no markdown fences, no commentary.
"""


def build_ui_synthesis_prompt(
    ir: ApplicationIR,
    user_prompt: str,
    *,
    data_layer: str | None = None,
    components: str | None = None,
    design_tokens: str | None = None,
) -> str:
    """Build the grounded prompt for LLM-powered overview page synthesis (``app/page.tsx``)."""
    archetype = _detect_ui_archetype(ir, user_prompt)
    archetype_instructions = _ADMIN_ARCHETYPE if archetype == "admin_panel" else _WEBSITE_ARCHETYPE
    return f"""You are a Lead UI/UX Engineer at a world-class software platform.
Your mission is to write the main page (`app/page.tsx`) for a Next.js 15 application.

USER'S ORIGINAL REQUEST:
"{user_prompt or ir.description or ir.name}"

PROJECT CONTEXT:
- Name: {ir.name}
- Purpose: {ir.description}

DATA ENTITIES IN POSTGRES DATABASE:
{_entities_block(ir)}

{_grounding_blocks(ir, data_layer, components, design_tokens)}
{archetype_instructions}

{_core_rules(ir)}"""


def build_screen_synthesis_prompt(
    screen: Screen,
    ir: ApplicationIR,
    user_prompt: str,
    *,
    data_layer: str | None = None,
    components: str | None = None,
    design_tokens: str | None = None,
) -> str:
    """Build the grounded prompt for bespoke screen page synthesis (``app/<screen>/page.tsx``)."""
    components_str = ", ".join(screen.components) if screen.components else "default layout"
    actions_str = ", ".join(screen.actions) if screen.actions else "default actions"
    return f"""You are a Lead UI/UX Engineer at a world-class software platform.
Your mission is to write the dedicated, interactive page (`app/{screen.id}/page.tsx`) for a Next.js 15 application.

USER'S ORIGINAL REQUEST:
"{user_prompt or ir.description or ir.name}"

SCREEN SPECIFICATION:
- Screen ID: {screen.id}
- Intended Role: {screen.role}
- Declared Components: {components_str}
- Primary Actions: {actions_str}

PROJECT CONTEXT:
- App Name: {ir.name}
- Purpose: {ir.description}

DATA ENTITIES IN POSTGRES DATABASE:
{_entities_block(ir)}

{_grounding_blocks(ir, data_layer, components, design_tokens)}
DESIGN & ARCHITECTURE GUIDELINES:
Deliver a state-of-the-art, domain-specific UI for this screen:
- Catalog / Product Grid / Item List: a responsive grid of modern cards with badges, formatted values, ratings
  (Rating), tags, and action buttons; search, sort and pagination wired to the list hook.
- Editor / Form: a complete create/edit form bound to the real create/update hooks with validation, field
  errors, submit/loading states and success feedback (useToast).
- Detail: the record's fields, related sub-collections via the real list-by hooks, and edit/delete actions.
- Shopping Cart / Order Review: interactive rows with quantity steppers, totals, a summary card and a checkout action.
- Booking / Schedule: slots, status badges, provider details and a confirmation Dialog.
- Dashboard / Analytics: StatCards with trend badges, filter controls and action items.

{_core_rules(ir)}"""


# ---------------------------------------------------------------------------
# Synthesis core: one file, bounded repair loop, deterministic fallback
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UiSynthesisOutcome:
    """JSON-safe, secret-free record of how one file was produced.

    ``last_reason`` is a validator rejection reason or an exception *type name* (plus the HTTP status code when
    the error carries one, e.g. ``ProviderHTTPError(413)``) — provider errors can embed response bodies, which
    must never leak into state or logs.
    """

    path: str
    mode: str  # "llm" | "deterministic"
    attempts: int  # model calls made (0 when the model was never called)
    model_id: str
    last_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "mode": self.mode,
            "attempts": self.attempts,
            "model_id": self.model_id,
            "last_reason": self.last_reason,
        }


def _resolve_target(provider: ModelProvider, model_id: str | None) -> tuple[ModelRef, int]:
    from ..model_gateway.contracts import ModelRef

    provider_id = getattr(provider, "provider_id", "auto")
    if not model_id:
        profiles = getattr(provider, "profiles", lambda: ())()
        resolved_model_id = profiles[0].descriptor.model.model_id if profiles else "default"
    else:
        resolved_model_id = model_id
    target = ModelRef(provider_id=provider_id, model_id=resolved_model_id)

    max_output = 4096
    profiles_dict = getattr(provider, "_profiles", None)
    if isinstance(profiles_dict, dict) and resolved_model_id in profiles_dict:
        max_output = profiles_dict[resolved_model_id].descriptor.max_output_tokens
    elif hasattr(provider, "profile"):
        try:
            max_output = provider.profile(target).descriptor.max_output_tokens
        except Exception:  # noqa: BLE001 - profile lookup is best-effort
            pass
    return target, max_output


def _safe_message_text(text: str, limit: int) -> str:
    """Bound and sanitize text for a Message: no control characters (newline kept), no surrounding whitespace."""
    clipped = text[:limit]
    cleaned = "".join(ch if ch == "\n" or (ch >= " " and ch != "\x7f") else " " for ch in clipped)
    cleaned = cleaned.replace("\t", "    ").strip()
    return cleaned or "(empty output)"


def _repair_message(path: str, reason: str) -> str:
    """The corrective turn. Kept generic so a compiler's output can be fed through the same channel."""
    return (
        f"Your previous `{path}` was REJECTED: {reason}\n"
        "Return ONLY the corrected, complete file content (under 300 lines, no markdown fences, no commentary). "
        "Keep every import within react, react-dom, next/*, @/lib/*, @/components/* and relative paths, and use "
        "only the hooks and components that were listed."
    )


def _reason_for(err: BaseException) -> str:
    """A secret-free reason for an exception: the type name, plus the HTTP status when the error has one.

    Provider errors can embed response bodies, so the message is never used — but the status code is not
    a secret and is exactly what an operator needs (R-466: `ProviderHTTPError(413)` vs a bare type name).
    """
    name = type(err).__name__
    status = getattr(err, "status_code", None)
    return f"{name}({status})" if isinstance(status, int) and not isinstance(status, bool) else name


_TOO_LARGE_HINT = re.compile(r"too large|too long|context[ _]length|maximum context|reduce (?:the |your )?(?:message|prompt)", re.I)


def _is_request_too_large(err: BaseException) -> bool:
    """True when a provider rejected the request for its SIZE (HTTP 413, or a 400 that says so).

    Groq answers 413 when one request exceeds the tokens-per-minute limit on its own; OpenAI-style APIs
    answer 400 "context length exceeded". Waiting cannot fix either — only a smaller request can.
    """
    status = getattr(err, "status_code", None)
    if status == 413:
        return True
    return status == 400 and bool(_TOO_LARGE_HINT.search(str(err)))


class _Transcript:
    """The bounded conversation for one file, able to shrink itself after a 'request too large' rejection.

    Shape: ``[SYSTEM, USER(prompt)]`` plus one ``[ASSISTANT(echo), USER(corrective)]`` pair per rejected
    attempt. ``shrink()`` applies the next smaller form — level 1 drops every echo (the latest corrective text
    is merged into the prompt turn), level 2 swaps the full grounded prompt for the compact one — so a
    too-large rejection costs at most two extra attempts (R-466).
    """

    def __init__(self, prompt: str, compact_prompt: str | None) -> None:
        self.base = prompt.strip()
        self.compact = compact_prompt.strip() if compact_prompt else None
        self.compacted = False
        self.merged_repair: str | None = None
        self.pairs: list[tuple[str, str]] = []

    def reject(self, echo: str, corrective: str) -> None:
        self.pairs.append((echo, corrective))

    def shrink(self) -> str | None:
        """Apply the next shrink level; return what changed, or None when nothing is left to drop."""
        if self.pairs:
            self.merged_repair = self.pairs[-1][1]
            self.pairs = []
            return "dropped the echoed output"
        if self.compact is not None and not self.compacted:
            self.base = self.compact
            self.compacted = True
            return "switched to the compact grounding"
        return None

    def messages(self) -> tuple:
        from ..model_gateway.contracts import ChatRole, Message

        first = self.base if self.merged_repair is None else f"{self.base}\n\n{self.merged_repair}"
        messages = [Message(ChatRole.SYSTEM, _SYSTEM_MESSAGE), Message(ChatRole.USER, first)]
        for echo, corrective in self.pairs:
            messages.append(Message(ChatRole.ASSISTANT, echo))
            messages.append(Message(ChatRole.USER, corrective))
        return tuple(messages)


def _finalize(cleaned_jsx: str, tag: str) -> str:
    if cleaned_jsx.startswith('"use client";'):
        return '"use client";\n' + tag + cleaned_jsx[len('"use client";') :].lstrip("\n")
    return tag + cleaned_jsx


async def _synthesize_file(
    *,
    path: str,
    prompt: str,
    fallback: Callable[[], str],
    provider: ModelProvider,
    model_id: str | None,
    timeout_seconds: float,
    max_attempts: int,
    outcomes: list[UiSynthesisOutcome] | None,
    log_label: str,
    compact_prompt: str | None = None,
) -> str:
    """Generate one file with a bounded validation→feedback→retry loop. Never raises.

    Retries happen for exactly two reasons: a validator rejection (the reason is fed back) and a provider
    rejecting the request as too large (the transcript shrinks — R-466). Every other exception falls back at once.
    """
    from ..model_gateway.contracts import GenerateRequest

    try:
        target, max_output = _resolve_target(provider, model_id)
    except Exception as err:  # noqa: BLE001 - never raise out of synthesis
        if outcomes is not None:
            outcomes.append(UiSynthesisOutcome(path, "deterministic", 0, "default", type(err).__name__))
        return fallback()

    attempts_allowed = max(1, int(max_attempts))
    transcript = _Transcript(prompt, compact_prompt)
    attempts = 0
    last_reason = ""
    for attempt in range(1, attempts_allowed + 1):
        attempts = attempt
        try:
            request = GenerateRequest(
                request_id=f"ui-synth-{uuid.uuid4().hex[:12]}",
                model=target,
                messages=transcript.messages(),
                max_output_tokens=max_output,
                timeout_seconds=timeout_seconds,
            )
            response = await asyncio.wait_for(provider.generate(request), timeout=timeout_seconds)
        except Exception as err:  # noqa: BLE001 - transport/provider errors never retry; fall back
            last_reason = _reason_for(err)
            shrunk = transcript.shrink() if _is_request_too_large(err) and attempt < attempts_allowed else None
            if shrunk is not None:
                logger.warning("LLM UI synthesis for %s: request too large (%s); %s and retrying", log_label, last_reason, shrunk)
                continue
            logger.warning(
                "LLM UI synthesis for %s failed (%s); falling back to the deterministic template", log_label, last_reason
            )
            break
        raw = getattr(response, "text", None)
        if raw is None:
            raw = getattr(getattr(response, "message", None), "content", "") or ""
        valid, cleaned, reason = clean_and_validate_jsx(raw)
        if valid:
            tag = f"{MARKER_PREFIX} ({target.model_id}; attempt {attempt}/{attempts_allowed})\n"
            if outcomes is not None:
                outcomes.append(UiSynthesisOutcome(path, "llm", attempts, target.model_id, ""))
            logger.info("Synthesized bespoke LLM UI for %s on attempt %d", log_label, attempt)
            return _finalize(cleaned, tag)
        last_reason = reason
        logger.warning(
            "Synthesized JSX for %s rejected on attempt %d/%d (%s)", log_label, attempt, attempts_allowed, reason
        )
        if attempt < attempts_allowed:
            transcript.reject(_safe_message_text(raw, _MAX_ECHO_CHARS), _repair_message(path, reason))

    if outcomes is not None:
        outcomes.append(UiSynthesisOutcome(path, "deterministic", attempts, target.model_id, last_reason))
    return fallback()


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def synthesize_overview_page(
    ir: ApplicationIR,
    user_prompt: str,
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    failover_provider: ModelProvider | None = None,
    failover_model_id: str | None = None,
    timeout_seconds: float = 120.0,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    outcomes: list[UiSynthesisOutcome] | None = None,
    data_layer: str | None = None,
    components: str | None = None,
    design_tokens: str | None = None,
    compact_grounding: dict | None = None,
) -> str:
    """Synthesize the bespoke overview page (``app/page.tsx``) or fall back to the deterministic template.

    Never raises: any failure returns ``_overview_page(ir)``. ``compact_grounding`` (R-466) supplies the
    smaller data-layer/components/tokens blocks the engine switches to when a provider rejects the full
    request as too large.
    """
    from .nextjs import _overview_page

    if provider is None:
        return _overview_page(ir)

    prompt = build_ui_synthesis_prompt(
        ir, user_prompt, data_layer=data_layer, components=components, design_tokens=design_tokens
    )
    compact_prompt = build_ui_synthesis_prompt(ir, user_prompt, **compact_grounding) if compact_grounding else None
    path = "app/page.tsx"
    primary: list[UiSynthesisOutcome] = []
    result = await _synthesize_file(
        path=path,
        prompt=prompt,
        fallback=lambda: _overview_page(ir),
        provider=provider,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        outcomes=primary,
        log_label=f"project '{ir.name}' {path}",
        compact_prompt=compact_prompt,
    )
    if primary and primary[-1].mode == "deterministic" and failover_provider is not None:
        # One extra pass with the failover provider (preserves the R-462 failover behavior).
        logger.info("Attempting failover provider '%s' for %s", getattr(failover_provider, "provider_id", "unknown"), path)
        failover: list[UiSynthesisOutcome] = []
        result = await _synthesize_file(
            path=path,
            prompt=prompt,
            fallback=lambda: _overview_page(ir),
            provider=failover_provider,
            model_id=failover_model_id,
            timeout_seconds=min(timeout_seconds, 60.0),
            max_attempts=max_attempts,
            outcomes=failover,
            log_label=f"project '{ir.name}' {path} (failover)",
            compact_prompt=compact_prompt,
        )
        primary = failover
    if outcomes is not None:
        outcomes.extend(primary)
    return result


def synthesize_overview_page_sync(
    ir: ApplicationIR,
    user_prompt: str,
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    outcomes: list[UiSynthesisOutcome] | None = None,
    data_layer: str | None = None,
    components: str | None = None,
    design_tokens: str | None = None,
    compact_grounding: dict | None = None,
) -> str:
    """Synchronous bridge for synthesize_overview_page (the repair loop lives inside the coroutine)."""
    if provider is None:
        from .nextjs import _overview_page

        return _overview_page(ir)

    coro_factory = lambda: synthesize_overview_page(  # noqa: E731 - a fresh coroutine per run
        ir,
        user_prompt,
        provider=provider,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        outcomes=outcomes,
        data_layer=data_layer,
        components=components,
        design_tokens=design_tokens,
        compact_grounding=compact_grounding,
    )
    return _run_sync(coro_factory)


async def synthesize_screen_page(
    screen: Screen,
    ir: ApplicationIR,
    user_prompt: str = "",
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    outcomes: list[UiSynthesisOutcome] | None = None,
    data_layer: str | None = None,
    components: str | None = None,
    design_tokens: str | None = None,
    compact_grounding: dict | None = None,
) -> str:
    """Synthesize a bespoke screen page (``app/<screen>/page.tsx``) or fall back to the deterministic template."""
    from .nextjs import _screen_page

    if provider is None:
        return _screen_page(screen, ir)

    prompt = build_screen_synthesis_prompt(
        screen, ir, user_prompt, data_layer=data_layer, components=components, design_tokens=design_tokens
    )
    compact_prompt = (
        build_screen_synthesis_prompt(screen, ir, user_prompt, **compact_grounding) if compact_grounding else None
    )
    path = f"app/{screen.id}/page.tsx"
    return await _synthesize_file(
        path=path,
        prompt=prompt,
        fallback=lambda: _screen_page(screen, ir),
        provider=provider,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        outcomes=outcomes,
        log_label=f"project '{ir.name}' {path}",
        compact_prompt=compact_prompt,
    )


def synthesize_screen_page_sync(
    screen: Screen,
    ir: ApplicationIR,
    user_prompt: str = "",
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    outcomes: list[UiSynthesisOutcome] | None = None,
    data_layer: str | None = None,
    components: str | None = None,
    design_tokens: str | None = None,
    compact_grounding: dict | None = None,
) -> str:
    """Synchronous bridge for synthesize_screen_page."""
    if provider is None:
        from .nextjs import _screen_page

        return _screen_page(screen, ir)

    coro_factory = lambda: synthesize_screen_page(  # noqa: E731 - a fresh coroutine per run
        screen,
        ir,
        user_prompt=user_prompt,
        provider=provider,
        model_id=model_id,
        timeout_seconds=timeout_seconds,
        max_attempts=max_attempts,
        outcomes=outcomes,
        data_layer=data_layer,
        components=components,
        design_tokens=design_tokens,
        compact_grounding=compact_grounding,
    )
    return _run_sync(coro_factory)


def _run_sync(coro_factory: Callable[[], object]) -> str:
    """Run a synthesis coroutine to completion from sync code, even if an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro_factory()).result()
    return asyncio.run(coro_factory())
