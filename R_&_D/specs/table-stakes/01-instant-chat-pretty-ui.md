# Spec: Instant Chat → Pretty UI (v0/Lovable Parity)

**Tracker ID:** R-700
**Phase:** 1 — Vibe Mode Pro Foundation
**Priority:** P0 (Table Stakes)
**Estimated Effort:** 2 weeks
**Dependencies:** None
**Status:** Draft

---

## 1. Problem Statement

Users expect "type a prompt → see beautiful UI in seconds" like v0 and Lovable. Current OmniStackAI generates correct but utilitarian UI. We need parity on visual polish, animations, and "wow factor" while maintaining our engineering guarantees.

---

## 2. Requirements

### 2.1 Visual Polish (Must Match v0/Lovable)

| Feature | Current | Target | Implementation |
|---------|---------|--------|----------------|
| Design System | shadcn/ui + Tailwind v3 | shadcn/ui + Tailwind v4 + OKLCH tokens | Upgrade Tailwind, add OKLCH color palette |
| Animations | CSS transitions only | Framer Motion entrance, scroll reveal, stagger | Add `framer-motion` to allowlist, create animation primitives |
| Charts | KPI cards only | Recharts: line, bar, area, pie, radar, sparklines | Add `recharts` to allowlist, create `ChartContainer` composed component |
| Rich Text | Plain textarea | Tiptap: toolbar, images, tables, links, code blocks | Add `@tiptap/*` to allowlist, create `RichTextEditor` composed component |
| Command Palette | None | cmdk: search, actions, keyboard shortcuts | Add `cmdk`, create `CommandPalette` composed component |
| Data Tables | Simple pagination | TanStack Table: sort, filter, paginate, virtualize, inline edit | Add `@tanstack/react-table`, create `DataTable` composed component |
| Forms | Basic inputs | React Hook Form + Zod: validation, wizard, draft autosave | Add `react-hook-form`, `@hookform/resolvers`, create `Wizard` composed component |
| File Upload | `<input type="file">` | Drag-drop, progress, preview, S3 direct upload | Add `@dnd-kit/*`, create `FileUploader` composed component |
| Drawers/Sheets | Basic dialog | Vaul: mobile-optimized bottom sheets | Add `vaul`, integrate with shadcn `Sheet` |
| Toasts | Basic alert | Sonner: promise-based, actionable, stacked | Add `sonner`, replace `sonner.tsx` wrapper |
| Date/Time | None | react-day-picker: booking, ranges, recurrence | Add `react-day-picker`, create `Calendar` composed component |
| Maps | None | MapLibre/Leaflet: markers, clusters, geofence | Add `maplibre-gl` or `leaflet`, create `MapView` composed component |
### 2.2 LLM Allowlist Expansion

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/llm_ui.py

VIBE_ALLOWLIST = [
    # Core (existing)
    'lucide-react', 'clsx', 'tailwind-merge', 'class-variance-authority',
    '@radix-ui/react-slot', '@radix-ui/react-icons',
    # Animation & Motion (NEW)
    'framer-motion', 'motion/react', '@motionone/react',
    # Charts & Visualization (NEW)
    'recharts', 'chart.js', 'react-chartjs-2', 'victory',
    # Rich Text & Content (NEW)
    '@tiptap/react', '@tiptap/starter-kit', '@tiptap/extension-image',
    '@tiptap/extension-link', '@tiptap/extension-table',
    '@tiptap/extension-code-block', '@tiptap/extension-highlight',
    # Command Palette & Search (NEW)
    'cmdk',
    # Date & Time (NEW)
    'date-fns', 'react-day-picker',
    # Forms & Validation (NEW)
    'react-hook-form', '@hookform/resolvers', 'zod',
    # Drag & Drop (NEW)
    '@dnd-kit/core', '@dnd-kit/sortable', '@dnd-kit/utilities',
    # Tables - Advanced (NEW)
    '@tanstack/react-table',
    # Drawers & Sheets (NEW)
    'vaul',
    # Toasts (UPGRADE)
    'sonner',
    # Icons - Extended (NEW)
    '@radix-ui/react-icons',
]

# Validator must reject any import not in allowlist
# Repair loop: max 2 attempts with real TypeScript errors
```
### 2.3 Composed Component Library

Create pre-built, design-token-compliant components that LLM can compose:

```
packages/ui/src/composed/
├── AnimatedHero.tsx           # Framer Motion: entrance, scroll-reveal, parallax
├── MetricCard.tsx             # Recharts sparkline + counter animation + trend indicator
├── DataTable.tsx              # TanStack Table: sort, filter, paginate, virtualize, column resize, export
├── ChartContainer.tsx         # Recharts wrapper: line/bar/area/pie/radar + responsive + loading skeleton
├── RichTextEditor.tsx         # Tiptap: toolbar, images, tables, links, code, mentions, slash commands
├── Wizard.tsx                 # Multi-step: validation per step, draft autosave (localStorage), branch/skip logic
├── FileUploader.tsx           # Drag-drop zone, progress, preview grid, S3 presigned URL, virus scan hook
├── MapView.tsx                # MapLibre: markers, clusters, heatmap, geofence, directions, offline tiles
├── Calendar.tsx               # react-day-picker: single/range/multi, booking slots, recurrence, timezone
├── NotificationBell.tsx       # Sonner + realtime: unread count, mark read, actions, preferences link
├── CommandPalette.tsx         # cmdk: fuzzy search, keyboard nav, sections, recent, actions with shortcuts
├── OnboardingFlow.tsx         # Wizard + Framer Motion + analytics events + skip/complete tracking
├── TestimonialCarousel.tsx    # Framer Motion: auto-play, pause hover, swipe, dots, keyboard
├── PricingTable.tsx           # Animated toggle (monthly/annual), feature comparison, CTA, popular badge
├── FeatureGrid.tsx            # Staggered entrance, hover lift, icon + title + description, responsive
├── StatsDashboard.tsx         # Recharts real-time: WebSocket updates, time range picker, export CSV
├── DataGrid.tsx               # TanStack Table + inline edit + row selection + bulk actions + virtualization
├── AnimatedSidebar.tsx        # Framer Motion: collapse/expand, nested routes, badge indicators
├── AvatarStack.tsx            # Overlapping avatars, tooltip on hover, "+N more", online indicators
├── ProgressRing.tsx           # Animated SVG ring, gradient, label, size variants, accessibility
### 2.4 Archetype-Aware Page Templates (Enhanced)

Extend existing archetype system with modern UI patterns:

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/archetype.py

ARCHETYPE_TEMPLATES = {
    'storefront': {
        'pages': ['home', 'products', 'product-detail', 'cart', 'checkout', 'account', 'orders'],
        'components': ['AnimatedHero', 'FeatureGrid', 'ProductGrid', 'TestimonialCarousel', 'PricingTable'],
        'animations': ['staggered-entrance', 'hover-lift', 'cart-drawer-slide', 'toast-pop'],
        'charts': ['sales-sparkline', 'category-distribution'],
    },
    'saas': {
        'pages': ['landing', 'dashboard', 'settings', 'team', 'billing', 'onboarding'],
        'components': ['AnimatedHero', 'MetricCard', 'DataTable', 'StatsDashboard', 'CommandPalette', 'OnboardingFlow'],
        'animations': ['page-transition', 'sidebar-collapse', 'metric-counter', 'chart-draw'],
        'charts': ['usage-line', 'revenue-bar', 'churn-funnel', 'feature-adoption-radar'],
    },
    'booking': {
        'pages': ['home', 'services', 'calendar', 'checkout', 'confirmation', 'manage'],
        'components': ['Calendar', 'Wizard', 'AnimatedHero', 'FeatureGrid', 'TestimonialCarousel'],
        'animations': ['slot-selection', 'step-transition', 'confirmation-confetti'],
        'charts': ['availability-heatmap', 'booking-trends'],
    },
    'directory': {
        'pages': ['home', 'search', 'listing-detail', 'categories', 'map', 'submit'],
        'components': ['DataTable', 'MapView', 'CommandPalette', 'FilterSidebar', 'AnimatedHero'],
        'animations': ['filter-slide', 'map-marker-drop', 'card-stagger'],
        'charts': ['category-distribution', 'rating-breakdown'],
    },
    'marketplace': {
        'pages': ['home', 'browse', 'listing-detail', 'seller-dashboard', 'checkout', 'orders', 'messages'],
        'components': ['ProductGrid', 'DataTable', 'RichTextEditor', 'FileUploader', 'NotificationBell', 'ChatInterface'],
        'animations': ['listing-hover', 'image-zoom', 'message-slide'],
        'charts': ['sales-line', 'conversion-funnel', 'rating-trend'],
    },
    'marketing': {
        'pages': ['landing', 'features', 'pricing', 'testimonials', 'faq', 'contact', 'blog'],
        'components': ['AnimatedHero', 'FeatureGrid', 'PricingTable', 'TestimonialCarousel', 'AnimatedSidebar'],
        'animations': ['scroll-reveal', 'parallax', 'counter', 'carousel-auto'],
        'charts': None,
    },
    'admin': {
        'pages': ['dashboard', 'users', 'analytics', 'settings', 'audit', 'billing'],
        'components': ['StatsDashboard', 'DataTable', 'DataGrid', 'ChartContainer', 'CommandPalette', 'NotificationBell'],
        'animations': ['metric-counter', 'chart-draw', 'table-row-slide'],
        'charts': ['users-line', 'revenue-bar', 'retention-cohort', 'funnel'],
    },
}
```

---

## 3. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | `framer-motion` animations render in generated preview | Visual regression test + snapshot |
| AC-02 | `recharts` charts render with real data from API | Integration test with mocked API |
| AC-03 | `tiptap` rich text editor saves/loads content | E2E test: type → save → reload → verify |
| AC-04 | `cmdk` command palette opens with `⌘K` | Playwright test: keyboard shortcut |
| AC-05 | `tanstack/react-table` sorts, filters, paginates | Unit test + visual regression |
| AC-06 | `react-hook-form` + Zod validates wizard steps | E2E test: invalid → error → fix → next |
| AC-07 | File upload shows progress, preview, completes | E2E test with mock S3 |
| AC-08 | All composed components use design tokens (no hardcoded values) | Static analysis: grep for hardcoded colors/spacing |
| AC-09 | LLM-generated code passes typecheck with new imports | `task verify` on 50 generated projects |
| AC-10 | Repair loop fixes import errors in ≤2 attempts | Integration test with injected errors |

---

## 4. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-700.1 | Upgrade to Tailwind v4 + OKLCH tokens in design system | Frontend | 3 days |
| R-700.2 | Expand LLM allowlist in `llm_ui.py` with validator updates | AI Engineer | 2 days |
| R-700.3 | Create 20 composed components in `packages/ui/src/composed/` | Frontend | 8 days |
| R-700.4 | Enhance archetype templates with new components/animations | AI Engineer | 3 days |
| R-700.5 | Add visual regression tests for all composed components | QA | 3 days |
| R-700.6 | Update `task verify` to include new allowlist validation | Platform | 1 day |

---

## 5. Files to Modify/Create

### New Files
- `packages/ui/src/composed/*.tsx` (20 files)
- `services/agent-engine/src/omnistackai_agent_engine/codegen/composed_components.py` (component registry)
- `apps/console-web/components/composed/*.tsx` (Studio preview components)

### Modified Files
- `services/agent-engine/src/omnistackai_agent_engine/codegen/llm_ui.py` (allowlist)
- `services/agent-engine/src/omnistackai_agent_engine/codegen/archetype.py` (templates)
- `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py` (component imports)
- `packages/ui/tailwind.config.ts` (v4 + OKLCH)
- `packages/ui/package.json` (new dependencies)

---

## 6. Definition of Done

- [ ] All 20 composed components built, tested, documented
- [ ] Allowlist expanded, validator updated, repair loop tested
- [ ] Archetype templates generate modern UI with animations/charts/rich text
- [ ] 50 generated projects pass `task verify` with new features
- [ ] Visual regression baseline established for all components
- [ ] Documentation: component props, usage examples, LLM prompting guide
├── SkeletonLoader.tsx         # Shimmer animation, variant per component (card, table, chart, list)
└── EmptyState.tsx             # Illustration + title + description + primary/secondary actions + variant
```