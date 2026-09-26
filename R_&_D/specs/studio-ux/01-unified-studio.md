# Spec: Unified Studio UX — Mode-Aware Interface

**Tracker ID:** R-706
**Phase:** 1 — Vibe Mode Pro Foundation
**Priority:** P0
**Estimated Effort:** 2 weeks
**Dependencies:** R-700, R-701, R-705
**Status:** Draft

---

## Design Principle
> Show only what matters for the current mode. Graduate seamlessly.

## Mode Switcher (Always Visible)
```tsx
// apps/console-web/app/studio/mode-switcher.tsx
export function ModeSwitcher() {
  const [mode, setMode] = useState<'vibe' | 'engineering'>('vibe');
  
  return (
    <SegmentedControl value={mode} onValueChange={setMode}>
      <SegmentedControlItem value="vibe">
        <Sparkles className="mr-2 h-4 w-4" />
        Vibe Mode
        <Badge variant="secondary" className="ml-2">Pro</Badge>
      </SegmentedControlItem>
      <SegmentedControlItem value="engineering">
        <Cpu className="mr-2 h-4 w-4" />
        Engineering Mode
      </SegmentedControlItem>
    </SegmentedControl>
  );
}
```

## Vibe Mode — Visible Options
| Category | Options Shown | Hidden in Vibe |
|----------|---------------|----------------|
| Project | Name, description, archetype, domain | Stack selection, repo strategy, execution mode |
| Features | Toggle packs (payments, realtime, auth, files, search, scheduling, notifications, analytics) | Individual pack versioning, IR editing, custom packs |
| UI | Theme (light/dark/auto), color preset, animation level, component density | Design tokens editor, custom component registry |
| Apps | Web (customer), Admin toggle | Mobile (RN/Native), additional operator apps |
| Backend | None (auto: Hono + Supabase) | Language (Go/Python/Node), BaaS options, custom DB |
| Database | None (auto: Supabase PG) | Provider (Neon/Turso/PlanetScale/Self-hosted), migrations UI |
| Deploy | One-click: Vercel, Netlify, Cloudflare | Kubernetes, AWS/GCP/Azure, BYOC, IaC export |
| Team | Invite members (basic) | RBAC, workspaces, review workflows, audit logs |
| Advanced | None | Feature flags, A/B testing, PWA, i18n, custom domains |

## Engineering Mode — Visible Options
| Category | Options Shown |
|----------|---------------|
| Project | Full IR editor (YAML/JSON), stack matrix, repo strategy, execution mode |
| Packs | Pack selector with dependency graph, version pinning, custom pack upload |
| Apps | Multi-app architect: add/remove apps per role, configure surfaces |
| Backend | Language per service (Go/Python/Node), BaaS, custom DB, microservices vs monolith |
| Database | Provider selection, migration management, seed data generator, RLS policy editor |
| Mobile | Profile per app: RN/Expo, Native Kotlin, Native Swift, Flutter, Web/PWA |
| Deploy | Target per app: Vercel, CF, AWS, GCP, Azure, K8s, BYOC, Docker |
| Team | Workspaces, RBAC, approval gates, audit logs, review workflows, cost allocation |
| Advanced | Feature flags, A/B testing, PWA, i18n, custom domains, edge config, observability |

## Graduation Banner (Vibe Mode Only)
```tsx
export function GraduationBanner() {
  const { needsGraduation, reasons } = useGraduationDetection();
  if (!needsGraduation) return null;
  return (
    <Alert className="border-primary/20 bg-primary/5">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Ready for Engineering Mode</AlertTitle>
      <AlertDescription>
        Your project needs: {reasons.join(', ')}.
        <Button variant="link" onClick={graduateToEngineering} className="ml-2">
          Graduate →
        </Button>
      </AlertDescription>
    </Alert>
  );
}
```

## Graduation Detection Logic
```typescript
function useGraduationDetection() {
  const project = useProject();
  
  const reasons = [];
  if (project.apps.length > 2) reasons.push("multi-app");
  if (project.mobile) reasons.push("native mobile");
  if (project.backend !== "hono") reasons.push("custom backend");
  if (project.team.size > 1) reasons.push("team collaboration");
  if (project.compliance.length > 0) reasons.push("compliance");
  
  return { needsGraduation: reasons.length > 0, reasons };
}
```

## Acceptance Criteria
- [ ] Mode switcher persists preference
- [ ] Vibe Mode shows only 4 tabs: Project, Features, UI, Deploy
- [ ] Engineering Mode shows all 9 tabs
- [ ] Graduation banner appears when detection triggers
- [ ] One-click graduation preserves all work
- [ ] No feature parity gaps (Engineering can do everything Vibe can)

## Files to Create/Modify
- apps/console-web/app/studio/mode-switcher.tsx
- apps/console-web/app/studio/vibe-chat.tsx
- apps/console-web/app/studio/engineering-workspace.tsx
- apps/console-web/app/studio/graduation-banner.tsx
- apps/console-web/app/studio/page.tsx (unified)
