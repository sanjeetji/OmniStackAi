# OmniStackAI Master Architecture Plan
## Unified Vibe Mode Pro + Engineering Mode Platform

---

## 1. Executive Summary

This document defines the complete architecture for a **unified platform** that captures both:
- **Vibe Mode Pro**: "AI builds it for you" — instant chat → real backend + DB + modern UI → deploy
- **Engineering Mode**: "AI engineers it with you" — IR → packs → multi-app platform → owned, evolvable code

**Single codebase. Single team. Zero ceiling. Seamless graduation.**

---

## 2. Core Philosophy

```
Emergent:          LLM ──────────→ Code
                         ↑
                    (sandbox run)

OmniStackAI:  Prompt → IR → Architecture Rules → Change-Impact → Codegen Adapters
                         ↓              ↓              ↓            ↓
                    Contracts      Policies       Tests      Git/Deploy
                         ↘              ↘              ↘            ↘
                          └────────────── LLM (bounded contributor) ────────┘
```

**Key Principle**: LLM handles *presentation & composition*; deterministic engine handles *correctness, contracts, verification, evolution*.

---

## 3. Unified Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OMNISTACKAI PLATFORM                                 │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SHARED FOUNDATION                                │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │Application│ │  Pack   │ │  Code   │ │  Git    │ │ Verifica│       │   │
│  │  │    IR    │ │ Registry│ │generators│ │ Service │ │  tion   │       │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │   │
│  │       │           │           │           │           │            │   │
│  │       └───────────┼───────────┼───────────┼───────────┘            │   │
│  │                   ▼           ▼           ▼                        │   │
│  │         ┌─────────────────────────────────────────┐               │   │
│  │         │        COMPOSITION ENGINE               │               │   │
│  │         │  (merges packs → single valid IR)       │               │   │
│  │         └────────────────────┬────────────────────┘               │   │
│  └─────────────────────────────┼────────────────────────────────────┘   │
│                                │                                        │
│        ┌───────────────────────┼───────────────────────┐               │
│        ▼                       ▼                       ▼               │
│ ┌─────────────┐        ┌─────────────┐        ┌─────────────┐        │
│ │  VIBE MODE  │        │  GRADUATION │        │ENGINEERING  │        │
│ │    PRO      │◄──────►│   BRIDGE    │◄──────►│    MODE     │        │
│ │             │        │             │        │             │        │
│ │ • Chat UI   │        │ • One-click │        │ • Full IR   │        │
│ │ • Real PG   │        │   "Open in  │        │ • Pack      │        │
│ │ • Real API  │        │   Studio"   │        │   Selector  │        │
│ │ • LLM UI    │        │ • Preserves │        │ • Multi-app │        │
│ │ • Deploy    │        │   Git hist  │        │ • Verified  │        │
│ │ • Graduate  │        │ • Adds IR   │        │   builds    │        │
│ └─────────────┘        │   metadata  │        │ • Team WS   │        │
│                        │ • Enables   │        │ • Customer  │        │
│                        │   packs     │        │   deploy    │        │
│                        └─────────────┘        └─────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
---

## 4. Vibe Mode Pro — "Real Platform from Chat"

### 4.1 Generation Pipeline (90 seconds)

```
1. CLASSIFY (2s)     → LLM: prompt → {archetype, domain, features, suggested_packs}
2. SELECT PACKS (1s) → Deterministic: Core + Domain + Archetype packs
3. COMPOSE IR (3s)   → Merge pack IRs → single valid ApplicationIR
4. GENERATE (15s)    → Assembler → monorepo files (web, api, admin, shared, supabase)
5. PROVISION (45s)   → Supabase project + migrations + seeds + Edge Functions
6. PREVIEW (10s)     → WebContainer (web+admin) + API server → live preview
```

### 4.2 Pack Selection (Deterministic, No Hallucination)

**Core Packs (Always):**
- `auth-rbac` — Login, roles, JWT, RLS policies
- `database-pg` — PostgreSQL, migrations, seeds
- `api-core` — Hono/Express, Zod, OpenAPI, error handling
- `design-system-pro` — shadcn/ui + Tailwind v4 + **Framer Motion + Recharts + Tiptap + CmdK + Vaul + Sonner**
- `admin-crud` — Generated admin from IR

**Domain Packs (Auto-selected):**
| Domain | Packs |
|--------|-------|
| saas | subscriptions, billing-portal, usage-metering, feature-flags |
| marketplace | marketplace-core, payments, listings, reviews, communications |
| on-demand | scheduling, real-time, dispatch, payments, ratings |
| healthcare | hipaa-compliance, appointments, emr, communications |
| fintech | ledger, kyc-aml, transfers, cards, compliance |
| content | publications, media, subscriptions, analytics, seo |

**Archetype UI Packs:**
- storefront: shop-ui, cart-checkout, product-catalog, recommendations
- booking: booking-flow, calendar-ui, availability, reminders
- directory: search-ui, filters, maps, listings-grid
- saas: dashboard, onboarding-wizard, settings, team-management
- marketing: animated-hero, testimonials, pricing-table, faq

### 4.3 Real Infrastructure (No Mocks)

| Layer | Technology | Why |
|-------|------------|-----|
| Database | **Supabase** (PostgreSQL + pgvector + RLS + Realtime) | Real PG, instant provisioning, auth built-in |
| API | **Hono on Node.js** (Edge-compatible) | Fast, typed, OpenAPI, works in WebContainer |
| Auth | **Supabase Auth** (email, OAuth, magic links, MFA) | Battle-tested, RLS integration |
| Real-time | **Supabase Realtime** / Ably | WebSocket subscriptions, presence |
| Storage | **Supabase Storage** / S3-compatible | Presigned URLs, CDN, transformations |
| Payments | **Stripe** (Connect for marketplaces) | Test keys in preview, webhooks via ngrok |
| Email | **Resend** | Developer-friendly, test mode |
| Search | **Meilisearch Cloud** / Typesense | Faceted search, typo tolerance |

### 4.4 LLM UI Generation (Bounded but Expressive)

```python
# Expanded Allowlist for Vibe Mode Pro
VIBE_ALLOWED_IMPORTS = {
    # UI Primitives
    "lucide-react", "clsx", "cva", "tailwind-merge",
    "@radix-ui/react-*",
    "@/components/ui/*",
    
    # Animation & Interaction (NEW)
    "framer-motion",
    "motion",  # Framer Motion v11+
    
    # Charts & Visualization (NEW)
    "recharts",
    "@visx/*",
    
    # Rich Text (NEW)
    "@tiptap/react", "@tiptap/starter-kit", "@tiptap/extensions-*",
    
    # Forms & Wizards (NEW)
    "react-hook-form", "@hookform/resolvers", "zod",
    "vaul",  # drawer for mobile forms
    
    # Command Palette (NEW)
    "cmdk",
    
    # Notifications (NEW)
    "sonner",
    
    # Date/Time (NEW)
    "date-fns", "react-day-picker",
    
    # Tables (NEW)
    "@tanstack/react-table",
---

## 5. Engineering Mode — "Production-Grade Multi-App Platform"

### 5.1 Horizontal + Vertical Pack Composition

```
~30 Horizontal Packs (Universal) + ~80 Vertical Packs (Domain) = ~110 Total
```

**Horizontal Packs (Extended from 20):**
1. auth-rbac
2. database-pg
3. api-core
4. design-system-pro
5. admin-crud
6. payments
7. notifications
8. files-storage
9. search
10. real-time
11. workflows (generic state machine engine)
12. audit-compliance
13. multi-app
14. analytics
15. scheduling
16. communications
17. ratings-reviews
18. referrals-affiliates
19. subscriptions
20. marketplace-core
21. localization
22. feature-flags
23. api-docs
24. **webhooks** — Ingest/egress, retries, signatures
25. **background-jobs** — Inngest/Trigger.dev integration
26. **api-gateway** — Rate limiting, auth, routing
27. **cache** — Redis, invalidation strategies
28. **observability** — OpenTelemetry, Sentry, logs
29. **secrets** — Vault/1Password/Infisical integration
30. **testing** — Playwright, Vitest, contract tests

**Vertical Packs (~80, built incrementally):**
- Healthcare: patients, providers, appointments, emr, telehealth, prescriptions, labs, billing-codes, hipaa, insurance
- Mobility: rides, drivers, dispatch, routing, surge, fleet, matching, earnings
- Commerce: listings, cart, checkout, inventory, fulfillment, returns, vendors, commissions, pos
- FinTech: accounts, ledger, transfers, kyc, aml, cards, loans, compliance, reporting
- Food Delivery: restaurants, menus, orders, kitchen, couriers, delivery-tracking, reviews
- Real Estate: properties, listings, tours, offers, contracts, escrow, mortgages
- Education: courses, enrollments, assignments, grades, certificates, lms, video
- SaaS/B2B: organizations, teams, seats, usage-metering, entitlements, sso, quotas
- Logistics: shipments, warehouses, inventory, tracking, customs, fleet, routing
- Professional Services: projects, time-tracking, invoicing, contracts, retainers, resources

### 5.2 Domain-Specific IR Extensions

```python
# application_ir/domain.py

class StateMachine:
    name: str
    entity: str
    initial_state: str
    states: list[State]
    transitions: list[Transition]
    guards: dict[str, GuardExpression]  # CEL expressions
    actions: dict[str, ActionSpec]      # sync/async, compensation

class BusinessRule:
    name: str
    entity: str
    trigger: TriggerType  # CREATE, UPDATE, DELETE, TRANSITION
    condition: GuardExpression
    actions: list[ActionSpec]
    priority: int

class RolePermission:
    role: str
    entity: str
    actions: list[str]  # CRUD + custom transitions
    field_mask: list[str]  # field-level allow/deny
    row_filter: GuardExpression  # RLS policy

class PageTemplate:
    name: str
    archetype: str
---

## 6. Graduation Bridge — Zero Loss Transition

### 6.1 Vibe → Engineering Metadata

```json
// .vibe/graduation-manifest.json
{
  "ir": { /* full ApplicationIR inferred from generated code */ },
  "packs_used": ["auth-rbac", "database-pg", "api-core", "design-system-pro", "subscriptions", "payments"],
  "custom_ui": {
    "pages": ["app/dashboard/page.tsx", "app/pricing/page.tsx"],
    "components": ["components/AnimatedHero.tsx", "components/MetricCard.tsx"]
  },
  "supabase": {
    "project_id": "vibe-x7k9m2",
    "region": "us-east-1",
    "handoff_instructions": "..."
  },
  "design_tokens": { /* OKLCH values, radii, shadows */ },
  "user_modifications": [ /* git diff from initial generation */ ]
}
```

### 6.2 Graduation Flow

```
User clicks "Open in Engineering Mode"
         │
         ▼
1. Read .vibe/graduation-manifest.json
2. Hydrate full ApplicationIR
3. Open Engineering Studio with:
   - IR Editor (pre-filled)
   - Pack Selector (pre-checked)
   - Multi-app Architect (shows current single-app)
   - Custom UI preserved in /custom/
4. User can now:
   - Add mobile app (RN/Native)
   - Switch backend to Go/Python
   - Add Kubernetes deploy
   - Invite team members
   - Configure CI/CD
```

---

## 7. Studio UX — Mode-Aware Interface

### 7.1 Vibe Mode Pro Options (Only Relevant)

| Category | Options Shown |
|----------|---------------|
| **Project** | Name, description, archetype, domain |
| **Features** | Auth, Database, API, Payments, Realtime, Files, Search, Notifications |
| **UI Polish** | Animations (Framer Motion), Charts (Recharts), Rich Text (Tiptap), Maps |
| **Deploy** | Vercel, Netlify, Supabase (one-click) |
| **Graduation** | "Open in Engineering Mode" (always visible) |

**Hidden in Vibe:** Pack selector, IR editor, multi-app architect, Kubernetes config, team RBAC, CI/CD pipeline editor, backend language choice.

### 7.2 Engineering Mode Options (Full Control)

| Category | Options Shown |
|----------|---------------|
| **Architecture** | IR Editor, Pack Selector, Multi-app Architect, Dependency Graph |
| **Apps** | Add/remove apps, choose framework per app (Next.js, RN, Native, Flutter) |
| **Backend** | Language (Go/Python/Node), Database (PG/MySQL/SQLite), ORM |
| **Packs** | Horizontal + Vertical pack browser, version selector, custom packs |
| **Infrastructure** | Kubernetes, Terraform, Environments, Secrets, Domains |
| **Team** | Workspaces, RBAC, Invitations, Code Review, Audit Log |
| **CI/CD** | Pipeline editor, Preview deployments, Promotion gates |
| **Graduation** | "Import Vibe Project" (reverse bridge) |

**Hidden in Engineering:** One-click deploy to Vercel, simplified feature toggles, chat-first UI.

### 7.3 Shared Options (Both Modes)

- Design token editor (OKLCH colors, spacing, radii, motion)
---

## 9. Competitive Coverage Matrix (Post-Implementation)

| Feature | v0 | Lovable | Bolt | Emergent | Dyad | **OmniStackAI Unified** |
|---------|----|---------|------|----------|------|------------------------|
| **Instant pretty UI** | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ **Vibe Pro + Framer Motion** |
| **Live browser preview** | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ **WebContainer** |
| **One-click deploy** | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ **Vercel/Netlify/Supabase** |
| **Animations (Framer)** | ✅ | ✅ | ⚠️ | ❌ | ❌ | ✅ **Allowlist + components** |
| **Charts (Recharts)** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ **Allowlist + components** |
| **Rich text (Tiptap)** | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ **Allowlist + components** |
| **Real backend + DB** | ❌ | Supabase | In-browser | FastAPI+Mongo | Node | ✅ **Real PG + Hono + RLS** |
| **Real API + validation** | ❌ | ❌ | ❌ | Basic | Basic | ✅ **Zod + OpenAPI + types** |
| **Payments (Stripe)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Connect + webhooks** |
| **Real-time** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Supabase Realtime/Ably** |
| **File uploads** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **S3 + Uppy + presigned** |
| **Multi-app ecosystem** | ❌ | ❌ | ❌ | Partial | ❌ | ✅ **Native (Eng Mode)** |
| **Mobile (RN + Native)** | ❌ | ❌ | Expo | Expo | Capacitor | ✅ **RN *or* Kotlin/Swift** |
| **State machines** | ❌ | ❌ | ❌ | Basic | ❌ | ✅ **Pack: workflows** |
| **Domain packs (70+)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Horizontal + Vertical** |
| **Customer owns Git** | ❌ | ❌ | ❌ | ❌ | ✅ Local | ✅ **Both modes** |
| **Team workspaces** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Eng Mode (R-515)** |
| **Deploy to customer cloud** | ❌ | Vercel only | ❌ | ❌ | ❌ | ✅ **Eng Mode** |
| **Graduate vibe → eng** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Unique bridge** |
| **Import existing project** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Analyze → enhance** |
| **Offline / local-first** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ **Both modes** |

---

## 10. Implementation Roadmap (Phased)

### Phase 0: Foundation (Weeks 1-4) — **Do First**
- [ ] Pack Manifest v2 schema + Registry + Loader
- [ ] Composition Engine (merge IRs, resolve conflicts)
### Phase 1: Vibe Mode Pro (Weeks 5-10)
- [ ] Supabase provisioning via Management API
- [ ] Hono API generator (from IR + packs)
- [ ] WebContainer runtime + Supabase proxy
- [ ] Vibe Build Pipeline (classify → packs → generate → provision → preview)
- [ ] Graduation Bridge (.vibe/manifest.json → Engineering Studio)
- [ ] Unified Studio with Mode Switcher

### Phase 2: Engineering Mode Depth (Weeks 11-20)
- [ ] State Machine Codegen + Role App Generator
- [ ] Page Template Engine (Jinja2 + IR slots)
- [ ] Shared Package Generator
- [ ] Rich Seed Data Generator (domain-aware Faker)
- [ ] 5 Vertical Packs: Healthcare, Mobility, Commerce, FinTech, SaaS
- [ ] Real-time Adapter (Supabase/Ably)
- [ ] Form/Wizard Engine
- [ ] Search/Filter Engine (Meilisearch)

### Phase 3: Advanced Platform (Weeks 21-30)
- [ ] Remaining Vertical Packs (Food, Real Estate, Edu, Logistics, Prof Services)
- [ ] WebSocket/Real-time Adapter complete
- [ ] Payment Flow Generator (Stripe Connect, webhooks, subscriptions)
- [ ] Notification System Generator (multi-channel, templates, preferences)
- [ ] File Upload Pipeline (S3 direct, processing, PDF gen)
- [ ] True Native Mobile (Kotlin/Compose + Swift/SwiftUI adapters)
- [ ] Kubernetes Deploy Generator (Helm + Kustomize)
- [ ] Project Import Pipeline (GitHub → IR → packs)
- [ ] 10 Core Horizontal Packs (auth, db, api, design-pro, admin, payments, notifications, files, realtime, workflows)
- [ ] Design System Pro components (Framer Motion, Recharts, Tiptap, TanStack Table, CmdK, Vaul, Sonner, Uppy)
- Component library browser (shadcn/ui + composed)
### Phase 4: Polish & Scale (Weeks 31-40)
- [ ] Template Marketplace UX
- [ ] A/B Testing + Feature Flags runtime
- [ ] PWA/Offline support
- [ ] i18n framework
- [ ] Advanced Observability (distributed tracing, custom dashboards)
- [ ] Enterprise: SSO (SAML/OIDC), SCIM, Audit Export, Data Residency
- [ ] Performance optimization (bundle analysis, lazy loading, edge caching)

---

## 11. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Vibe Mode quality variance** | Strict validator + 2 repair rounds + deterministic fallback templates |
| **Pack conflict resolution** | Composition engine with deterministic precedence rules + validation |
| **Supabase dependency** | Abstract provider interface; support Neon/Turso/PlanetScale/self-hosted PG |
| **WebContainer limitations** | Fallback to local Docker preview; WebContainer only for instant preview |
| **LLM hallucination in IR** | LLM only proposes; deterministic engine validates & applies |
| **Scope creep** | Strict phase gates; each pack = separate Tracker ID with acceptance criteria |
| **Team bandwidth** | Horizontal packs first (high leverage); vertical packs parallelizable |

---

## 12. Success Metrics

| Metric | Target |
|--------|--------|
| Vibe Mode Pro: Prompt → Live Preview | < 90 seconds |
| Vibe Mode Pro: Prompt → Deployed URL | < 3 minutes |
| Engineering Mode: Prompt → Multi-app Monorepo | < 3 minutes |
| Graduation: Vibe → Engineering | < 30 seconds, zero data loss |
| Pack Composition: 10 packs merged | < 5 seconds, valid IR |
| Generated Code: TypeScript strict | 0 errors |
| Generated Code: Build (Next.js + API) | Passes 100% |
| Test Coverage (generated) | > 80% |
| User Retention (Vibe → Engineering) | > 40% |
| Project Import Success Rate | > 90% |

---

## 13. Conclusion

**This architecture achieves everything requested:**

1. ✅ **Vibe Mode Pro** = "AI builds it for you" with real backend, DB, payments, realtime, modern UI
2. ✅ **Engineering Mode** = "AI engineers it with you" with IR, packs, multi-app, native mobile, customer deploy
3. ✅ **Unified Foundation** = Single IR, single pack system, single codegen, single Git output
4. ✅ **Zero Ceiling** = Vibe users graduate seamlessly; Engineering users import existing projects
5. ✅ **Competitive Coverage** = Beats all competitors on at least one dimension; matches on "vibe" features
6. ✅ **No Hallucination** = LLM bounded by validators, allowlists, deterministic fallbacks
7. ✅ **Template Quality** = Packs encode domain logic; page templates encode UI patterns
8. ✅ **Mode-Aware UX** = Each mode shows only relevant options
9. ✅ **Future-Proof** = Pack system extensible; new domains = new vertical packs

**Next Step**: Begin Phase 0 implementation with `R-600 Blueprint Schema v1` and Pack Framework.
- Preview pane (WebContainer / local proxy)
- Git integration (commits, branches, history)
- Chat assistant (context-aware: IR-aware in Eng, UI-aware in Vibe)

---

## 8. Existing Project Import — "Read & Enhance"

### 8.1 Supported Sources

| Source | Detection | Import Process |
|--------|-----------|----------------|
| **GitHub/GitLab/Bitbucket** | Remote URL + token | Clone → analyze → generate IR |
| **Local folder** | Drag-drop / file picker | Analyze in-place |
| **Vercel/Netlify project** | API token | Fetch source + config |
| **Supabase project** | Project ref + token | Introspect schema + Edge Functions |

### 8.2 Analysis Pipeline

```
1. DETECT STACK
   - package.json, pyproject.toml, go.mod, Cargo.toml
   - Framework: Next.js, React, Vue, Express, FastAPI, etc.
   - Database: Prisma, Drizzle, SQLAlchemy, raw SQL
   - Auth: NextAuth, Clerk, Supabase, custom JWT

2. EXTRACT IR
   - Entities from Prisma/Drizzle/SQLAlchemy models
   - API routes from route handlers
   - UI components from component folders
   - Auth config from middleware/providers
   - Env vars from .env.example

3. MAP TO PACKS
   - Match entities → vertical packs
   - Match features → horizontal packs
   - Confidence scoring per pack

4. GENERATE MANIFEST
   - ApplicationIR (partial → complete via LLM)
   - Pack recommendations
   - Migration path (what's missing)
   - Risk assessment
```

### 8.3 Enhancement Modes

| Mode | What Happens |
|------|--------------|
| **Analyze Only** | Report: IR, packs, gaps, security issues, tech debt |
| **Add Feature** | "Add payments" → selects packs → generates code → PR |
| **Modernize UI** | "Rewrite with shadcn + Framer Motion" → component-by-component |
| **Add Mobile** | "Generate React Native app" → role-app generator → new app in monorepo |
| **Full Migration** | "Convert to OmniStackAI" → complete IR → regenerate with packs |
    role: str
    components: list[ComponentSpec]
    data_requirements: list[HookSpec]
    permissions: list[str]
    responsive: bool

class ComponentSpec:
    name: str
    type: ComponentType  # PRIMITIVE, COMPOSED, PAGE_SECTION
    props_schema: ZodSchema
    slots: list[SlotSpec]
    animations: AnimationSpec
    accessibility: A11ySpec
```

### 5.3 Advanced Code Generators

| Generator | Output |
|-----------|--------|
| `state_machine.py` | Backend transition API + frontend badge/buttons + validation middleware + audit logs |
| `role_app.py` | Complete per-role app: nav, pages, API scope, permissions |
| `page_template_engine.py` | Jinja2 + IR slots → complex domain pages (SOAP notes, dispatch board, etc.) |
| `shared_package.py` | `packages/shared/{types,api,hooks,formatters,validators,state-machines}` |
| `seed_data.py` | Domain-aware Faker: realistic patients, drivers, listings, transactions |
| `form_wizard_engine.py` | Multi-step, conditional, draft autosave, validation |
| `realtime_adapter.py` | Supabase/Ably/Socket.io unified hooks + presence + optimistic UI |
    
    # Maps (NEW)
    "react-map-gl", "maplibre-gl",
    
    # File Upload (NEW)
    "uppy", "@uppy/react", "@uppy/aws-s3",
    
    # Utilities
    "zustand", "jotai",  # lightweight state
    "swr", "@tanstack/react-query",  # data fetching
}

# Validator enforces:
# 1. ONLY these imports allowed
# 2. Must use design tokens (OKLCH CSS vars)
# 3. Must use shadcn/ui primitives as base
# 4. TypeScript strict mode passes
# 5. 2 repair rounds with real TS errors
```
