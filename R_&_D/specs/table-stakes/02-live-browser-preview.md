# Spec: Live In-Browser Preview (Bolt/WebContainer Parity)

**Tracker ID:** R-701
**Phase:** 1 — Vibe Mode Pro Foundation
**Priority:** P0 (Table Stakes)
**Estimated Effort:** 2 weeks
**Dependencies:** R-700 (allowlist for preview components)
**Status:** Draft

---

## 1. Problem Statement

Bolt.new uses WebContainer to run full Next.js + Node.js in browser. Users expect instant preview without local Docker. We need Tier 1 (Browser WASM) execution for Vibe Mode Pro.

---

## 2. Requirements

### 2.1 WebContainer Runtime

| Component | Specification |
|-----------|---------------|
| **Engine** | WebContainer API (StackBlitz) — Node.js in browser via WASM |
| **Supported Runtimes** | Node.js 20+ (LTS), pnpm 9+ |
| **Package Manager** | pnpm (lockfile cached by content hash) |
| **File System** | In-memory FS, persisted to IndexedDB for session resume |
| **Network** | HTTP server on random port, proxied via iframe |
| **Process Management** | `pnpm dev` for Next.js, `node dist/api.js` for Hono API |
| **Hot Reload** | Full HMR support for Next.js (WebSocket via proxy) |
### 2.2 Preview Architecture

```
Browser Tab
├── Studio (Parent)
│   ├── Chat, Files, Preview controls
│   └── WebContainer Controller (start/stop, logs, file sync)
└── WebContainer iframe
    ├── Next.js :3000
    ├── Hono API :3001
    └── Supabase (External)
        ├── PostgreSQL
        ├── Auth
        ├── Realtime
        └── Storage
```

### 2.3 Supabase Provisioning (Parallel, 45s)

```python
# services/agent-engine/src/omnistackai_agent_engine/runtime/supabase.py

class SupabaseProvisioner:
    async def provision(self, project_name: str) -> SupabaseProject:
        project = await self.management_api.create_project(
            name=project_name, region="us-east-1", plan="free",
            org_id=settings.SUPABASE_ORG_ID,
        )
        await self.wait_for_ready(project.ref)
        keys = await self.management_api.get_api_keys(project.ref)
        db_password = await self.management_api.get_db_password(project.ref)
        await self.run_migrations(project.ref, migrations)
        await self.seed_data(project.ref, seeds)
        await self.deploy_functions(project.ref, api_routes)
### 2.4 Generated Project Structure for Preview

```
.vibe/
├── ir.json
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   └── seed.sql
├── apps/
│   ├── web/              # Next.js 15
│   ├── admin/            # Next.js Admin
│   └── api/              # Hono/Express API
└── packages/
    └── shared/           # Types, hooks, API client
```

### 2.5 Preview Lifecycle

| Event | Action |
|-------|--------|
| Session Start | Restore IndexedDB FS, start WebContainer, `pnpm install` (cached) |
| First Preview | Provision Supabase (45s parallel), write `.env.local`, `pnpm dev` |
| Code Edit | Sync file changes → WebContainer FS → HMR triggers |
| Package Add | `pnpm add <pkg>` in WebContainer, update lockfile |
| Session End | Snapshot FS to IndexedDB, stop WebContainer (scale to zero) |
| Resume | Restore FS, restart WebContainer, `pnpm dev` (no reinstall) |

---

## 3. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | WebContainer starts Next.js + Hono in < 30s (warm) | Timing test |
| AC-02 | Supabase project provisioned in < 45s | Timing test |
| AC-03 | Real API calls work in preview (auth, CRUD, realtime) | E2E test |
| AC-04 | Hot reload works for Next.js and API changes | Manual + Playwright |
| AC-05 | Session resume restores state in < 10s | Timing test |
| AC-06 | Multiple concurrent previews isolated | Load test: 10 parallel |
| AC-07 | Preview iframe communicates with Studio (logs, errors) | Integration test |

---

## 4. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-701.1 | Integrate WebContainer API in `runtime/webcontainer.py` | Platform | 5 days |
| R-701.2 | Implement Supabase provisioning via Management API | Backend | 5 days |
| R-701.3 | Build preview proxy (iframe + WebSocket for logs) | Frontend | 3 days |
| R-701.4 | Generate project structure with Supabase config | AI Engineer | 3 days |
| R-701.5 | Implement session persistence (IndexedDB) | Platform | 2 days |
| R-701.6 | Add preview to Studio UI (iframe + controls) | Frontend | 2 days |

---

## 5. Files to Create/Modify

### New Files
- `services/agent-engine/src/omnistackai_agent_engine/runtime/webcontainer.py`
- `services/agent-engine/src/omnistackai_agent_engine/runtime/supabase.py`
- `services/agent-engine/src/omnistackai_agent_engine/studio/preview_proxy.py`
- `apps/console-web/app/studio/preview-iframe.tsx`

### Modified Files
- `services/agent-engine/src/omnistackai_agent_engine/intake/vibe_build.py`
- `services/agent-engine/src/omnistackai_agent_engine/studio/server.py`
- `apps/console-web/app/studio/page.tsx`

---

## 6. Definition of Done

- [ ] WebContainer runs Next.js + Hono + real Supabase in browser
- [ ] Cold start < 90s, warm start < 30s
- [ ] Real auth, DB, realtime, storage work in preview
- [ ] Hot reload functional for all file types
- [ ] Session persistence across browser refresh
- [ ] Resource cleanup on session end (scale to zero)
        return SupabaseProject(
            ref=project.ref,
            url=f"https://{project.ref}.supabase.co",
            anon_key=keys.anon,
            service_role_key=keys.service_role,
            db_url=f"postgresql://postgres:{db_password}@db.{project.ref}.supabase.co:5432/postgres",
        )
```