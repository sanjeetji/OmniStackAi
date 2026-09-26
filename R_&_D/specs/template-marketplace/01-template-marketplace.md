# Spec: Template Marketplace — Blueprint Catalog & Pack Publishing

**Tracker ID:** R-830
**Phase:** 4 — Polish & Scale
**Priority:** P2
**Estimated Effort:** 4 weeks
**Dependencies:** R-600 (Pack Manifest), R-605 (Blueprint Conversion), R-706 (Unified Studio)
**Status:** Draft

---

## 1. Problem Statement

Users need **discoverable, versioned, reviewable blueprints/packs** — not just 3 hand-built templates. Marketplace enables: community contributions, organization-private packs, pack composition, one-click project start from blueprint.

---

## 2. Competitive Analysis

| Feature | v0 | Lovable | Bolt | Emergent | **OmniStackAI Target** |
|---------|----|---------|------|----------|------------------------|
| Template gallery | ✅ | ✅ | ✅ | ❌ | ✅ **Blueprint catalog** |
| Domain-specific templates | Limited | Limited | Limited | Partial | ✅ **80+ vertical packs** |
| Pack versioning | ❌ | ❌ | ❌ | ❌ | ✅ **SemVer + changelog** |
| Private org packs | ❌ | ❌ | ❌ | ❌ | ✅ **Enterprise** |
| Pack composition UI | ❌ | ❌ | ❌ | ❌ | ✅ **Visual composer** |
| One-click from template | ✅ | ✅ | ✅ | ❌ | ✅ **Instant project** |
| Community ratings/reviews | ❌ | ❌ | ❌ | ❌ | ✅ **Social layer** |
| Pack publishing workflow | ❌ | ❌ | ❌ | ❌ | ✅ **CLI + Studio** |

---

## 3. Requirements

### 3.1 Blueprint/Pack Manifest v2 (Extended)

```yaml
# pack-manifest.yaml
name: healthcare-appointments
version: 2.1.0
description: "Complete appointment scheduling + telehealth for clinics"
category: healthcare
subcategory: scheduling
tags: [appointments, telehealth, hipaa, multi-role]
license: Apache-2.0
author: OmniStackAI Team
repository: https://github.com/omnistackai/pack-healthcare-appointments

depends_on:
  - auth-rbac: ">=1.0.0"
  - database-pg: ">=1.0.0"
  - api-core: ">=1.0.0"
  - workflows: ">=1.0.0"
  - real-time: ">=1.0.0"
  - communications: ">=1.0.0"
  - hipaa-compliance: ">=1.0.0"

provides:
  entities: [Appointment, Provider, Patient, Schedule, TelehealthSession, Prescription]
  state_machines:
    - appointment: [requested, confirmed, in_progress, completed, cancelled, no_show]
    - telehealth_session: [waiting, connected, ended]
  business_rules:
    - "provider.cannot_double_book"
    - "patient.max_appointments_per_day: 3"
  api_endpoints:
    - GET /appointments
    - POST /appointments
    - PATCH /appointments/{id}/status
    - POST /telehealth/start
  pages:
    - patient: booking-flow, appointment-list, telehealth-room
    - provider: schedule-manager, patient-detail, soap-note
    - admin: audit-log, provider-dashboard
  components: [AppointmentCard, ScheduleGrid, TelehealthRoom, ProviderSelector]
  hooks: [useAppointments, useTelehealth]
  validators: [appointment-create, telehealth-join]
  formatters: [format-appointment-status, format-duration]

apps:
  - role: patient
    framework: nextjs
    surfaces: [web, mobile-pwa]
  - role: provider
    framework: nextjs
    surfaces: [web]
  - role: admin
    framework: nextjs
    surfaces: [web]

compatible_with:
  frameworks: [nextjs, react-native, native-kotlin, native-swift, flutter]
  databases: [postgresql]
  deployment: [vercel, kubernetes, aws, gcp, azure]

marketplace:
  featured: true
  rating: 4.8
  downloads: 1247
### 3.2 Marketplace Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TEMPLATE MARKETPLACE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Public    │    │  Private    │    │  Community  │     │
│  │  Registry   │    │   Registry  │    │  Submissions│     │
│  │  (npm-like) │    │  (per org)  │    │  (PR-based) │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            ▼                                 │
│              ┌─────────────────────────┐                     │
│              │    Pack Resolution      │                     │
│              │  (SemVer + deps graph)  │                     │
│              └───────────┬─────────────┘                     │
│                          │                                    │
│         ┌───────────────┼───────────────┐                    │
│         ▼               ▼               ▼                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │   Studio    │ │   CLI       │ │   CI/CD     │            │
│  │  Browser    │ │  Publisher  │ │  Validator  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Pack Publishing Workflow

```bash
# CLI: omnistack pack publish
omnistack pack publish ./my-healthcare-pack \
  --registry public \
  --tag v2.1.0 \
  --changelog "Added telehealth recording support"

# Studio: Visual pack composer → "Publish to Marketplace"
# 1. Select packs to compose
# 2. Test composition in sandbox
# 3. Fill metadata (description, tags, screenshots)
# 4. Submit for review (community) or publish (org-private)
# 5. Automated validation: IR valid, builds pass, tests pass
# 6. Published to registry with SemVer
```

### 3.4 Studio Marketplace Browser

```tsx
// apps/console-web/app/studio/marketplace/page.tsx

interface PackCardProps {
  pack: PackManifest;
  installed: boolean;
  onInstall: () => void;
  onViewDetails: () => void;
}

export function MarketplaceBrowser() {
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<'featured' | 'rating' | 'downloads' | 'updated'>('featured');
  
  return (
    <div className="grid gap-6">
      <div className="flex gap-4 flex-wrap">
        <CategoryFilter value={category} onChange={setCategory} />
        <SearchInput value={search} onChange={setSearch} />
        <SortSelect value={sort} onChange={setSort} />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredPacks.map(pack => (
          <PackCard
            key={pack.name}
            pack={pack}
            installed={installedPacks.has(pack.name)}
            onInstall={() => installPack(pack)}
            onViewDetails={() => openPackDetails(pack)}
          />
        ))}
      </div>
    </div>
  );
}

function PackCard({ pack, installed, onInstall, onViewDetails }: PackCardProps) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <Badge variant="secondary" className="mb-2">{pack.category}</Badge>
            <CardTitle className="text-lg">{pack.name}</CardTitle>
            <CardDescription>{pack.description}</CardDescription>
          </div>
          <Rating stars={pack.marketplace.rating} />
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col">
        <div className="flex flex-wrap gap-1 mb-4">
          {pack.tags.slice(0, 4).map(tag => (
            <Badge key={tag} variant="outline">{tag}</Badge>
          ))}
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground mt-auto">
          <span>{pack.marketplace.downloads.toLocaleString()} downloads</span>
          <span>v{pack.version}</span>
          {pack.marketplace.enterprise_ready && (
            <Badge variant="secondary">Enterprise</Badge>
          )}
        </div>
      </CardContent>
      <CardFooter className="flex gap-2">
        <Button variant={installed ? "outline" : "default"} onClick={onInstall} className="flex-1">
          {installed ? 'Installed' : 'Add to Project'}
        </Button>
        <Button variant="ghost" onClick={onViewDetails}>
---

## 4. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | Pack manifest v2 validates + resolves dependencies | Schema test |
| AC-02 | Public registry serves packs with SemVer | Registry test |
| AC-03 | Private org registry with access control | Auth test |
| AC-04 | Pack composer UI resolves conflicts visually | UI test |
| AC-05 | One-click project start from pack → Vibe/Engineering | E2E test |
| AC-06 | CLI publish validates IR + builds + tests | CI test |
| AC-07 | Community submission → review → publish workflow | Workflow test |
| AC-08 | Pack rating/review system functional | Feature test |

---

## 5. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-830.1 | Pack Manifest v2 schema + validator | AI Engineer | 5 days |
| R-830.2 | Public registry (npm-compatible API) | Platform | 10 days |
| R-830.3 | Private org registry with RBAC | Platform | 5 days |
| R-830.4 | Pack composer UI (visual, conflict resolution) | Frontend | 10 days |
| R-830.5 | Marketplace browser in Studio | Frontend | 5 days |
| R-830.6 | CLI pack publish / install / update | Platform | 5 days |
| R-830.7 | Community submission + review workflow | Platform | 5 days |
| R-830.8 | Rating/review/social features | Frontend | 5 days |

---

## 6. Files to Create

- `specs/pack-framework/pack-manifest-v2.yaml` (schema)
- `services/agent-engine/src/omnistackai_agent_engine/registry/` (public + private)
- `services/agent-engine/src/omnistackai_agent_engine/registry/validator.py`
- `apps/console-web/app/studio/marketplace/` (browser, pack-card, pack-details)
- `apps/console-web/app/studio/pack-composer.tsx`
- `packages/cli/src/commands/pack/` (publish, install, update, compose)
- `github/workflows/pack-validation.yml`

---

## 7. Definition of Done

- [ ] Pack Manifest v2 schema complete with dependency resolution
- [ ] Public registry serves 50+ packs
- [ ] Private org registry with RBAC
- [ ] Pack composer UI resolves conflicts visually
- [ ] One-click project start from any pack
- [ ] CLI publish validates + publishes
- [ ] Community workflow: submit → review → publish
- [ ] Ratings/reviews functional
- [ ] Documentation: pack authoring guide, publishing workflow
          <Info className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
```
  verified: true
  enterprise_ready: true
```