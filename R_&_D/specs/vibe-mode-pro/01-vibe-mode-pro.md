# Spec: Vibe Mode Pro — "AI Builds It For You" with Real Backend

**Tracker ID:** R-840
**Phase:** 1 — Vibe Mode Pro Foundation
**Priority:** P0 (Table Stakes)
**Estimated Effort:** 6 weeks
**Dependencies:** R-700 (UI Polish), R-701 (WebContainer), R-702 (Deploy), R-706 (Unified Studio)
**Status:** Draft

---

## 1. Problem Statement

Vibe Mode Pro must deliver **"prompt → real platform in 90 seconds"** — not a toy. Real PostgreSQL (Supabase), real API (Hono), real auth, real payments, real realtime, real file storage — all working in browser preview. Then one-click deploy to Vercel/Netlify/Cloudflare. Then seamless graduation to Engineering Mode.

---

## 2. Competitive Analysis

| Feature | v0 | Lovable | Bolt | Emergent | Dyad | **Vibe Mode Pro Target** |
|---------|----|---------|------|----------|------|--------------------------|
| Instant pretty UI | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ **Framer Motion + shadcn Pro** |
| Live browser preview | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ **WebContainer + Supabase** |
| One-click deploy | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ **Vercel/Netlify/CF/Railway** |
| Real PostgreSQL | ❌ | Supabase | ❌ | ❌ | ❌ | ✅ **Supabase (instant provision)** |
| Real API (typed, validated) | ❌ | ❌ | In-browser | FastAPI | Node | ✅ **Hono + Zod + OpenAPI** |
| Real auth (JWT, OAuth, MFA) | ❌ | Supabase | ❌ | Basic | Basic | ✅ **Supabase Auth + RLS** |
| Real payments (Stripe) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Connect + webhooks** |
| Real-time (WebSocket) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Supabase Realtime/Ably** |
| File uploads (S3 direct) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Supabase Storage/Uppy** |
| Rich text (Tiptap) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ **Allowlist + composed** |
| Charts (Recharts) | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ **Allowlist + composed** |
| Animations (Framer Motion) | ✅ | ✅ | ⚠️ | ❌ | ❌ | ✅ **Allowlist + composed** |
| Multi-app (later) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Graduate → Engineering** |
| Native mobile (later) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Graduate → Native** |
| Own your data/infra | ❌ | Vercel only | ❌ | ❌ | ❌ | ✅ **Supabase project = yours** |
| Team collaboration | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Graduate → Workspaces** |
---

## 3. Requirements

### 3.1 Vibe Build Pipeline (90 Seconds)

```python
# services/agent-engine/src/omnistackai_agent_engine/intake/vibe_build.py

async def vibe_build_pro(prompt: str, provider: ModelProvider) -> VibeBuildResult:
    classification = await classify_prompt(prompt, provider)
    packs = select_vibe_packs(classification)
    ir = compose_ir(packs)
    project = await generate_monorepo(ir)
    supabase = await provision_supabase(project)
    preview = await start_preview(project, supabase)
    
    return VibeBuildResult(
        project=project,
        supabase=supabase,
        preview=preview,
        graduation_manifest=build_graduation_manifest(project, packs, supabase),
    )
```

### 3.2 Deterministic Pack Selection (No LLM Guessing)

```python
# services/agent-engine/src/omnistackai_agent_engine/intake/vibe_packs.py

VIBE_CORE_PACKS = [
    "auth-rbac", "database-pg", "api-core", "design-system-pro", "admin-crud",
]

DOMAIN_PACK_MAP = {
    "saas": ["subscriptions", "billing-portal", "usage-metering", "feature-flags"],
    "marketplace": ["marketplace-core", "payments", "listings", "reviews", "communications"],
    "on-demand": ["scheduling", "real-time", "dispatch", "payments", "ratings"],
    "healthcare": ["hipaa-compliance", "appointments", "emr", "communications"],
    "fintech": ["ledger", "kyc-aml", "transfers", "cards", "compliance"],
    "content": ["publications", "media", "subscriptions", "analytics", "seo"],
    "social": ["feed", "follows", "notifications", "messaging", "moderation"],
    "education": ["courses", "enrollments", "assignments", "grades", "certificates"],
    "real-estate": ["properties", "tours", "offers", "contracts", "escrow"],
    "logistics": ["shipments", "warehouses", "tracking", "fleet", "routing"],
}

ARCHETYPE_UI_PACKS = {
    "storefront": ["shop-ui", "cart-checkout", "product-catalog", "recommendations"],
    "booking": ["booking-flow", "calendar-ui", "availability", "reminders"],
    "directory": ["search-ui", "filters", "maps", "listings-grid"],
    "saas": ["dashboard", "onboarding-wizard", "settings", "team-management"],
    "marketing": ["animated-hero", "testimonials", "pricing-table", "faq"],
    "admin": ["data-table", "chart-dashboard", "audit-log", "user-management"],
}
```

### 3.3 Real Infrastructure Provisioning

```python
# services/agent-engine/src/omnistackai_agent_engine/runtime/supabase.py

class SupabaseProvisioner:
    async def provision(self, project_name: str, ir: ApplicationIR) -> SupabaseProject:
        project = await self.management_api.create_project(
            name=project_name, region="us-east-1", plan="free",
            org_id=settings.SUPABASE_ORG_ID,
        )
        await self.wait_for_ready(project.ref)
        keys = await self.management_api.get_api_keys(project.ref)
        db_password = await self.management_api.get_db_password(project.ref)
        await self.run_migrations(project.ref, ir.migrations)
        await self.seed_data(project.ref, ir.seeds)
        await self.deploy_functions(project.ref, ir.api_routes)
        await self.configure_rls(project.ref, ir.rls_policies)
        await self.enable_realtime(project.ref, ir.realtime_tables)
        await self.configure_storage(project.ref, ir.storage_buckets)
        
        return SupabaseProject(
            ref=project.ref,
            url=f"https://{project.ref}.supabase.co",
            anon_key=keys.anon,
            service_role_key=keys.service_role,
            db_url=f"postgresql://postgres:{db_password}@db.{project.ref}.supabase.co:5432/postgres",
        )
```

### 3.4 LLM UI Generation with Expanded Allowlist

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/llm_ui.py

VIBE_ALLOWLIST = {
    'lucide-react', 'clsx', 'cva', 'tailwind-merge',
    '@radix-ui/react-*', '@/components/ui/*',
    'framer-motion', 'motion/react',
    'recharts', '@visx/*',
    '@tiptap/react', '@tiptap/starter-kit', '@tiptap/extension-*',
    'react-hook-form', '@hookform/resolvers', 'zod', 'vaul',
    'cmdk', 'sonner',
    'date-fns', 'react-day-picker',
    '@tanstack/react-table',
    'react-map-gl', 'maplibre-gl',
    'uppy', '@uppy/react', '@uppy/aws-s3',
    'zustand', 'jotai', 'swr', '@tanstack/react-query',
}

# Validator enforces:
# 1. ONLY these imports allowed
# 2. Must use design tokens (OKLCH CSS vars)
# 3. Must use shadcn/ui primitives as base
# 4. TypeScript strict mode passes
# 5. 2 repair rounds with real TS errors
```

### 3.5 Graduation Bridge (Zero Loss)

```json
// .vibe/graduation-manifest.json
{
  "ir": { /* full ApplicationIR */ },
  "packs_used": ["auth-rbac", "database-pg", "api-core", "design-system-pro", "subscriptions", "payments"],
  "custom_ui": {
    "pages": ["app/dashboard/page.tsx", "app/pricing/page.tsx"],
    "components": ["components/AnimatedHero.tsx", "components/MetricCard.tsx"]
  },
  "supabase": {
    "project_id": "vibe-x7k9m2",
    "region": "us-east-1",
    "handoff_instructions": "Transfer project to your Supabase org..."
  },
  "design_tokens": { /* OKLCH values */ },
  "user_modifications": [ /* git diff */ ]
}
```
---

## 4. Vibe Mode Pro Studio UX

### 4.1 Chat-First Interface

```tsx
// apps/console-web/app/studio/vibe-chat.tsx

export function VibeChatInterface() {
  return (
    <div className="flex h-full flex-col">
      <PreviewPane className="flex-1" />
      <div className="border-t p-4">
        <ChatInput
          placeholder="Describe what you want to build..."
          onSend={handleSend}
          suggestions={[
            "SaaS with subscriptions",
            "Marketplace with payments",
            "Uber for X with real-time tracking",
            "Healthcare appointments + telehealth",
          ]}
        />
      </div>
    </div>
  );
}
```

### 4.2 Feature Toggles (Only Relevant Options)

| Category | Options Shown in Vibe Mode |
|----------|---------------------------|
| **Project** | Name, description, archetype, domain |
| **Features** | Auth, Database, API, Payments, Realtime, Files, Search, Notifications, Scheduling, Analytics |
| **UI Polish** | Theme, color preset, animation level, component density |
| **Deploy** | Vercel, Netlify, Cloudflare, Railway, Render |
| **Graduation** | "Open in Engineering Mode" (always visible) |

**Hidden in Vibe:** Pack selector, IR editor, multi-app architect, Kubernetes config, team RBAC, CI/CD editor, backend language choice.

---

## 5. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | Prompt → Live preview in < 90s | Timing test |
| AC-02 | Prompt → Deployed URL in < 3 min | Timing test |
| AC-03 | Real Supabase PG + Auth + Realtime + Storage works in preview | E2E test |
| AC-04 | Real Hono API + Zod validation + OpenAPI works | Integration test |
| AC-05 | Stripe test payments complete in preview | E2E test |
| AC-06 | Framer Motion / Recharts / Tiptap render in generated UI | Visual regression |
| AC-07 | One-click deploy to Vercel/Netlify/CF works | Deploy test |
| AC-08 | Graduation preserves all work + opens Engineering Mode | Graduation test |
| AC-09 | 50 generated projects pass `task verify` | CI test |

---

## 6. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-840.1 | Vibe classification pipeline (LLM + deterministic) | AI Engineer | 5 days |
| R-840.2 | Deterministic pack selector (core + domain + archetype) | AI Engineer | 3 days |
| R-840.3 | Supabase provisioning via Management API | Backend | 10 days |
| R-840.4 | Hono API generator from IR + packs | AI Engineer | 10 days |
| R-840.5 | WebContainer runtime + Supabase proxy | Platform | 10 days |
| R-840.6 | Vibe build orchestrator (parallel provision + generate) | AI Engineer | 5 days |
| R-840.7 | Graduation bridge (.vibe/manifest.json → Engineering) | AI Engineer | 5 days |
| R-840.8 | Vibe Studio UI (chat, preview, feature toggles, deploy) | Frontend | 10 days |
| R-840.9 | Deploy integrations (Vercel, Netlify, CF, Railway, Render) | Platform | 10 days |

---

## 7. Files to Create

- `services/agent-engine/src/omnistackai_agent_engine/intake/vibe_build.py`
- `services/agent-engine/src/omnistackai_agent_engine/intake/vibe_packs.py`
- `services/agent-engine/src/omnistackai_agent_engine/runtime/supabase.py`
- `services/agent-engine/src/omnistackai_agent_engine/runtime/webcontainer.py`
- `services/agent-engine/src/omnistackai_agent_engine/deploy/vibe_deploy.py`
- `services/agent-engine/src/omnistackai_agent_engine/studio/graduation_bridge.py`
- `apps/console-web/app/studio/vibe-chat.tsx`
- `apps/console-web/app/studio/vibe-feature-toggles.tsx`
- `apps/console-web/app/studio/vibe-deploy-dialog.tsx`
- `apps/console-web/app/studio/graduation-banner.tsx`

---

## 8. Definition of Done

- [ ] Vibe build pipeline: prompt → live preview < 90s
- [ ] Real Supabase + Hono + Stripe + Realtime all work in preview
- [ ] Framer Motion, Recharts, Tiptap, TanStack Table render correctly
- [ ] One-click deploy to 5+ targets works
- [ ] Graduation bridge: zero data loss, opens Engineering Mode
- [ ] Vibe Studio UI shows only relevant options
- [ ] 50 generated projects pass full verification
- [ ] Documentation: Vibe Mode Pro user guide, pack selection logic