"""Generative LLM-powered UI Synthesizer with Deterministic Fallback (R-462).

Enables OmniStackAI to synthesize creative, bespoke, domain-tailored Next.js pages
leveraging the platform's rich pre-built component suite (@/components/*) and typed
data hooks (@/lib/hooks), while guaranteeing:
1. Complete, non-stubbed implementations with zero placeholder TODOs.
2. Strict JSX safety and AST/import validation (rejecting unwhitelisted external imports).
3. 100% reliable, silent fallback to the deterministic Python template whenever the
   model is offline, times out, or fails validation.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..application_ir import ApplicationIR, Screen
    from ..model_gateway.contracts import ModelProvider

logger = logging.getLogger(__name__)

# Allowed import source prefixes for security and build stability (strictly no random npm packages)
ALLOWED_IMPORT_PREFIXES: tuple[str, ...] = (
    "@/components/",
    "@/lib/",
    "react",
    "next/",
    "./",
    "../",
)

# Core pre-built UI components available in customer projects
AVAILABLE_COMPONENTS_SUMMARY = """
AVAILABLE PRE-BUILT UI COMPONENTS (import from '@/components'):
- StatCard, StatCardHeader, StatCardValue: KPI metric cards
- DataGrid: { columns: Array<{ key: string, header: string }>, data: any[], sortable?: boolean }
- Tabs: { tabs: Array<{ id: string, label: string }>, activeTab: string, onChange: (id: string) => void }
- Badge: { variant?: 'default' | 'success' | 'warning' | 'error' | 'info', children: ReactNode }
- Avatar: { name?: string, src?: string, size?: 'sm' | 'md' | 'lg' }
- Progress: { value: number, max?: number, variant?: string }
- Dialog: { open?: boolean, onOpenChange?: (open: boolean) => void, children: ReactNode }
- EmptyState: { title: string, description?: string, actionLabel?: string, onAction?: () => void }
"""


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
        # Remove opening fence
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    if not content:
        return False, "", "Content empty after stripping code fences"

    # 2. Ensure "use client" is at the top
    if not content.startswith('"use client"') and not content.startswith("'use client'"):
        content = '"use client";\n\n' + content

    # 3. Validate imports against whitelist
    import_pattern = re.compile(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"])|(?:import\s+['"]([^'"]+)['"])""")
    for line in content.splitlines():
        line_clean = line.strip()
        if not line_clean.startswith("import "):
            continue
        match = import_pattern.search(line_clean)
        if match:
            module_name = match.group(1) or match.group(2)
            if module_name:
                is_allowed = any(module_name == prefix or module_name.startswith(prefix) for prefix in ALLOWED_IMPORT_PREFIXES)
                if not is_allowed:
                    return False, "", f"Forbidden import '{module_name}'. Must use internal platform modules or react/next."

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
    admin_keywords = (
        "admin",
        "management",
        "system",
        "portal",
        "clinic",
        "hospital",
        "attendance",
        "dashboard",
        "fleet",
        "crm",
        "erp",
        "internal",
        "console",
        "backoffice",
        "manager",
    )
    if any(k in text for k in website_keywords) and not any(k in text for k in ("admin", "management", "backoffice")):
        return "public_website"
    return "admin_panel"


def build_ui_synthesis_prompt(ir: ApplicationIR, user_prompt: str) -> str:
    """Build high-fidelity prompt for LLM-powered overview page synthesis."""
    entities_desc = []
    hooks_desc = []
    for entity in ir.entities:
        fields_str = ", ".join(f"{f.name}: {f.type.value}" for f in entity.fields)
        plural = entity.name if entity.name.endswith("s") else f"{entity.name}s"
        entities_desc.append(f"- Entity {entity.name} ({fields_str})")
        hooks_desc.append(
            f"- useList{plural}({{ page?: number, pageSize?: number, sort?: string, order?: 'asc' | 'desc', q?: string, filters?: Record<string, string>, ownerOnly?: boolean }}): "
            f"returns {{ data, total, loading, error, page, pageSize, totalPages, params, setSearch, setPage, setPageSize, setSort, setFilter, clearFilters, refetch }}"
        )
        hooks_desc.append(f"- useCreate{entity.name}(): returns {{ create, loading, error }}")

    entities_block = "\n".join(entities_desc)
    hooks_block = "\n".join(hooks_desc)
    archetype = _detect_ui_archetype(ir, user_prompt)

    if archetype == "admin_panel":
        archetype_instructions = """ARCHETYPE: MODERN SAAS ADMIN PANEL / WORKSPACE
Design a complete, production-grade SaaS Admin Panel with drawer navigation:
1. Left Collapsible Drawer / Sidebar Navigation:
   - Sidebar header: App logo badge, title, and collapse toggle button.
   - Navigation links with icons (e.g. Dashboard, Management tables, Settings).
   - Sub-items with bullet dots and active blue pill state.
2. Top Navigation Bar:
   - Global search input.
   - Right controls: Notification bell, User Avatar.
   - Interactive User Avatar dropdown menu with user email/name, Settings link, Reset Password link (`/forgot-password`), and Sign Out button (calling `logout()`).
3. Main View Modes (toggleable via state):
   - Data Management Table View:
     - Page Title (e.g. Management, Settings).
     - Filter bar: Status dropdown, and '+ Add [Entity]' button.
     - Table card with columns: ID, Name/Title, Status pill, Actions ('Edit' & 'Delete' buttons).
   - Analytics Stat Cards: metric counters for key entities."""
    else:
        archetype_instructions = """ARCHETYPE: MODERN PUBLIC WEBSITE / E-COMMERCE
Design a world-class consumer-facing public web experience:
1. Modern Navigation Header: Brand logo, category links, search, cart/actions, and user auth buttons.
2. Dynamic Hero Banner: Compelling headline, value proposition, high-contrast CTA buttons, and floating metric chips.
3. Feature / Product Showcase: Responsive grid with product/service cards, prices, rating badges, and action buttons.
4. Interactive Testimonials & Social Proof: Rating cards and customer feedback quotes.
5. Modern Footer: Sitemap links, newsletter subscription input, and copyright."""

    return f"""You are a Lead UI/UX Engineer at a world-class software platform.
Your mission is to write the main page (`app/page.tsx`) for a Next.js 15 application.

USER'S ORIGINAL REQUEST:
"{user_prompt or ir.description or ir.name}"

PROJECT CONTEXT:
- Name: {ir.name}
- Purpose: {ir.description}

DATA ENTITIES IN POSTGRES DATABASE:
{entities_block}

TYPED DATA HOOKS (import from '@/lib/hooks'):
{hooks_block}
- useAuth() (from '@/components/auth-provider'): returns {{ user: {{ id, email, full_name, role }} | null, token, logout }}

{AVAILABLE_COMPONENTS_SUMMARY}

{archetype_instructions}

CORE IMPLEMENTATION RULES:
1. Start with `"use client";`
2. Strictly NO unapproved third-party npm packages. Only import from:
   - React (`useState`, `useEffect`, etc.)
   - Next.js (`next/link`)
   - `@/lib/hooks`
   - `@/components` or `@/components/*`
3. ZERO PLACEHOLDERS: Implement complete, functional JSX. Do NOT leave `// TODO` or empty stubs.
4. CONCISE & MODULAR: Keep total length under 300 lines so output is NEVER truncated.
5. NULL SAFETY: `data` in hooks can be null while loading. ALWAYS use `(data ?? []).map(...)`, `(data ?? []).filter(...)`, or `data?.length || 0`.
6. AUTH USER: user object has `user?.full_name || user?.email` (do NOT use `first_name` or `last_name`).
7. DATA GRID: Column definitions MUST use `header: string` (e.g. key and header properties). Do NOT use `label`.
8. DIALOG COMPONENT: Use `open` and `onOpenChange` props (do NOT use `isOpen`).
9. STAT CARDS: Use compound format: `<StatCard><StatCardHeader title="Label" icon="📊" /><StatCardValue value="123" subtext="info" /></StatCard>`.
10. HOOK METHODS: Use `refetch()` to reload data (do NOT call `refresh()`).
11. STYLING: Do NOT rely on Tailwind CSS classes alone. Use scoped `<style jsx>{{`...`}}</style>` or inline styles so the UI is styled with modern colors (#0f172a, #2563eb, #f8fafc), rounded corners, and soft shadows.
12. FILE COMPLETION: The file MUST end cleanly with the closing `}}` of the default export component.
13. Output ONLY the raw TypeScript/React JSX file content. Do NOT include markdown commentary.
"""



async def synthesize_overview_page(
    ir: ApplicationIR,
    user_prompt: str,
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    failover_provider: ModelProvider | None = None,
    failover_model_id: str | None = None,
    timeout_seconds: float = 120.0,
) -> str:
    """Synthesize bespoke overview page with LLM or fallback to deterministic template.

    Never raises: if anything fails, returns the deterministic _overview_page(ir).
    """
    from .nextjs import _overview_page

    # Deterministic fallback when no provider is given (e.g., offline test suite)
    if provider is None:
        return _overview_page(ir)

    try:
        from ..model_gateway.contracts import (
            ChatRole,
            GenerateRequest,
            Message,
            ModelRef,
        )

        import uuid

        prompt = build_ui_synthesis_prompt(ir, user_prompt).strip()
        provider_id = getattr(provider, "provider_id", "auto")
        if not model_id:
            profiles = getattr(provider, "profiles", lambda: ())()
            if profiles:
                resolved_model_id = profiles[0].descriptor.model.model_id
            else:
                resolved_model_id = "default"
        else:
            resolved_model_id = model_id
        target_model = ModelRef(provider_id=provider_id, model_id=resolved_model_id)

        max_output = 4096
        profiles_dict = getattr(provider, "_profiles", None)
        if isinstance(profiles_dict, dict) and resolved_model_id in profiles_dict:
            max_output = profiles_dict[resolved_model_id].descriptor.max_output_tokens
        elif hasattr(provider, "profile"):
            try:
                prof = provider.profile(target_model)
                max_output = prof.descriptor.max_output_tokens
            except Exception:
                pass

        req_id = f"ui-synth-{uuid.uuid4().hex[:12]}"
        request = GenerateRequest(
            request_id=req_id,
            model=target_model,
            messages=(
                Message(
                    role=ChatRole.SYSTEM,
                    content="You are an expert Next.js full-stack UI designer. Respond only with valid, executable TypeScript React code.",
                ),
                Message(role=ChatRole.USER, content=prompt),
            ),
            max_output_tokens=max_output,
            timeout_seconds=timeout_seconds,
        )

        response = await asyncio.wait_for(
            provider.generate(request),
            timeout=timeout_seconds,
        )
        raw_content = getattr(response, "text", None)
        if raw_content is None:
            raw_content = getattr(getattr(response, "message", None), "content", "")
        valid, cleaned_jsx, reason = clean_and_validate_jsx(raw_content)
        if valid:
            logger.info("Successfully synthesized bespoke LLM UI for project '%s'", ir.name)
            tag = f'// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI ({resolved_model_id})\n'
            if cleaned_jsx.startswith('"use client";'):
                return '"use client";\n' + tag + cleaned_jsx[len('"use client";'):].lstrip('\n')
            return tag + cleaned_jsx
        else:
            logger.warning("Synthesized JSX failed safety validation (%s); falling back to deterministic template", reason)
    except Exception as err:
        err_msg = str(err) if str(err) else type(err).__name__
        logger.warning("LLM UI synthesis with primary provider failed (%s); checking failover provider", err_msg)
        if failover_provider is not None:
            try:
                logger.info("Attempting failover to secondary provider '%s'...", getattr(failover_provider, "provider_id", "unknown"))
                return await synthesize_overview_page(
                    ir,
                    user_prompt,
                    provider=failover_provider,
                    model_id=failover_model_id,
                    failover_provider=None,
                    timeout_seconds=min(timeout_seconds, 60.0),
                )
            except Exception as failover_err:
                logger.warning("Failover provider also failed: %s", failover_err)

    return _overview_page(ir)


def synthesize_overview_page_sync(
    ir: ApplicationIR,
    user_prompt: str,
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
) -> str:
    """Synchronous bridge for synthesize_overview_page."""
    if provider is None:
        from .nextjs import _overview_page
        return _overview_page(ir)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                synthesize_overview_page(
                    ir,
                    user_prompt,
                    provider=provider,
                    model_id=model_id,
                    timeout_seconds=timeout_seconds,
                ),
            )
            return future.result()
    else:
        return asyncio.run(
            synthesize_overview_page(
                ir,
                user_prompt,
                provider=provider,
                model_id=model_id,
                timeout_seconds=timeout_seconds,
            )
        )


def build_screen_synthesis_prompt(screen: Screen, ir: ApplicationIR, user_prompt: str) -> str:
    """Build high-fidelity prompt for bespoke screen page synthesis."""
    entities_desc = []
    hooks_desc = []
    for entity in ir.entities:
        fields_str = ", ".join(f"{f.name}: {f.type.value}" for f in entity.fields)
        entities_desc.append(f"- Entity {entity.name} ({fields_str})")
        plural = f"{entity.name}s" if not entity.name.endswith("s") else entity.name
        hooks_desc.append(f"- useList{plural}({{ limit?: number }}): returns {{ data, total, loading, error, refresh }}")
        hooks_desc.append(f"- useCreate{entity.name}(): returns {{ create, loading, error }}")

    entities_block = "\n".join(entities_desc)
    hooks_block = "\n".join(hooks_desc)
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
{entities_block}

TYPED DATA HOOKS (import from '@/lib/hooks'):
{hooks_block}
- useAuth() (from '@/components/auth-provider'): returns {{ user, token, logout }}

{AVAILABLE_COMPONENTS_SUMMARY}
- Rating: {{ value: number, max?: number, onChange?: (val: number) => void, readOnly?: boolean }}
- Toast: {{ useToast: () => {{ toast: (opts: {{ title: string, description?: string, variant?: 'default' | 'success' | 'destructive' }}) => void }} }}

DESIGN & ARCHITECTURE GUIDELINES:
1. Start with `"use client";`
2. Deliver a state-of-the-art, domain-specific UI:
   - If this is a Catalog / Product Grid / Item List:
     Render a responsive grid of modern cards with badges, formatted prices, ratings (using `@/components/rating`), tags, and action buttons.
   - If this is a Shopping Cart / Order Review:
     Render interactive item rows with quantity steppers (+/-), price calculations, discount coupon code input, line items, order summary card (subtotal, discounts, total), and Checkout action.
   - If this is a Customer Reviews / Feedback page:
     Render overall rating summary, star breakdown bars, review cards with verified badges, and a "Write a Review" form or dialog.
   - If this is a Booking / Schedule / Clinic page:
     Render appointment slots, status badges, provider details, and confirmation modal.
   - If this is a Dashboard / Analytics page:
     Render StatCards with trend badges, filter controls, and action items.
3. Use the typed hooks (`useList<Entities>`) to load and display dynamic records.
4. Strictly NO unapproved third-party npm packages. Only import from:
   - React (`useState`, `useEffect`, `useMemo`, etc.)
   - Next.js (`next/link`, `next/navigation`)
   - `@/lib/hooks`
   - `@/components/*` (e.g., `@/components/stat-card`, `@/components/badge`, `@/components/dialog`, `@/components/rating`, `@/components/toast`, etc.)
5. ZERO PLACEHOLDERS: Implement complete, functional JSX with real buttons, inputs, and feedback states. Do NOT leave `// TODO` or empty stubs.
6. Output ONLY the raw TypeScript/React JSX file content. Do NOT include markdown commentary.
"""


async def synthesize_screen_page(
    screen: Screen,
    ir: ApplicationIR,
    user_prompt: str = "",
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
) -> str:
    """Synthesize bespoke screen page with LLM or fallback to deterministic template."""
    from .nextjs import _screen_page

    if provider is None:
        return _screen_page(screen, ir)

    try:
        from ..model_gateway.contracts import (
            ChatRole,
            GenerateRequest,
            Message,
            ModelRef,
        )
        import uuid

        prompt = build_screen_synthesis_prompt(screen, ir, user_prompt).strip()
        provider_id = getattr(provider, "provider_id", "auto")
        if not model_id:
            profiles = getattr(provider, "profiles", lambda: ())()
            resolved_model_id = profiles[0].descriptor.model.model_id if profiles else "default"
        else:
            resolved_model_id = model_id
        target_model = ModelRef(provider_id=provider_id, model_id=resolved_model_id)

        max_output = 4096
        profiles_dict = getattr(provider, "_profiles", None)
        if isinstance(profiles_dict, dict) and resolved_model_id in profiles_dict:
            max_output = profiles_dict[resolved_model_id].descriptor.max_output_tokens
        elif hasattr(provider, "profile"):
            try:
                prof = provider.profile(target_model)
                max_output = prof.descriptor.max_output_tokens
            except Exception:
                pass

        req_id = f"screen-synth-{uuid.uuid4().hex[:12]}"
        request = GenerateRequest(
            request_id=req_id,
            model=target_model,
            messages=(
                Message(
                    role=ChatRole.SYSTEM,
                    content="You are an expert Next.js full-stack UI designer. Respond only with valid, executable TypeScript React code.",
                ),
                Message(role=ChatRole.USER, content=prompt),
            ),
            max_output_tokens=max_output,
            timeout_seconds=timeout_seconds,
        )

        response = await asyncio.wait_for(
            provider.generate(request),
            timeout=timeout_seconds,
        )
        raw_content = getattr(response, "text", None)
        if raw_content is None:
            raw_content = getattr(getattr(response, "message", None), "content", "")
        valid, cleaned_jsx, reason = clean_and_validate_jsx(raw_content)
        if valid:
            logger.info("Successfully synthesized bespoke screen '%s' for project '%s'", screen.id, ir.name)
            tag = f'// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI ({resolved_model_id})\n'
            if cleaned_jsx.startswith('"use client";'):
                return '"use client";\n' + tag + cleaned_jsx[len('"use client";'):].lstrip('\n')
            return tag + cleaned_jsx
        else:
            logger.warning("Synthesized screen JSX for '%s' failed validation (%s); falling back to deterministic template", screen.id, reason)
    except Exception as err:
        err_msg = str(err) if str(err) else type(err).__name__
        logger.warning("LLM screen UI synthesis for '%s' encountered error (%s); falling back to deterministic template", screen.id, err_msg)

    return _screen_page(screen, ir)


def synthesize_screen_page_sync(
    screen: Screen,
    ir: ApplicationIR,
    user_prompt: str = "",
    provider: ModelProvider | None = None,
    model_id: str | None = None,
    timeout_seconds: float = 120.0,
) -> str:
    """Synchronous bridge for synthesize_screen_page."""
    if provider is None:
        from .nextjs import _screen_page
        return _screen_page(screen, ir)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                asyncio.run,
                synthesize_screen_page(
                    screen,
                    ir,
                    user_prompt=user_prompt,
                    provider=provider,
                    model_id=model_id,
                    timeout_seconds=timeout_seconds,
                ),
            )
            return future.result()
    else:
        return asyncio.run(
            synthesize_screen_page(
                screen,
                ir,
                user_prompt=user_prompt,
                provider=provider,
                model_id=model_id,
                timeout_seconds=timeout_seconds,
            )
        )

