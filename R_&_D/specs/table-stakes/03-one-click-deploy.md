# Spec: One-Click Deploy (Vercel/Netlify/Cloudflare Parity)

**Tracker ID:** R-702
**Phase:** 1 — Vibe Mode Pro Foundation
**Priority:** P0 (Table Stakes)
**Estimated Effort:** 2 weeks
**Dependencies:** R-701 (preview working)
**Status:** Draft

---

## 1. Problem Statement

Users expect "generate → preview → deploy to production in one click" like Lovable, Bolt, v0. We need zero-config deployment to major platforms with custom domain support.

---

## 2. Requirements

### 2.1 Supported Deployment Targets (Vibe Mode Pro)

| Platform | Method | Features |
|----------|--------|----------|
| **Vercel** | Vercel CLI / API | Edge functions, ISR, custom domains, analytics |
| **Netlify** | Netlify CLI / API | Edge functions, forms, identity, custom domains |
| **Cloudflare Pages** | Wrangler / API | Workers, KV, D1, custom domains, zero cold start |
| **Railway** | Railway CLI | PostgreSQL, Redis, custom domains, simple pricing |
| **Render** | Render API | PostgreSQL, Redis, cron jobs, custom domains |

### 2.2 Deployment Flow

```python
# services/agent-engine/src/omnistackai_agent_engine/deploy/vibe_deploy.py

class VibeDeployer:
    async def deploy(self, project: VibeProject, target: DeployTarget) -> DeployResult:
        # 1. Build production bundles
        build_result = await self.build_production(project)
        
        # 2. Generate platform-specific config
        config = self.generate_config(project, target)
        
        # 3. Deploy via platform API/CLI
        if target == DeployTarget.VERCEL:
            return await self.deploy_vercel(project, config)
        elif target == DeployTarget.NETLIFY:
            return await self.deploy_netlify(project, config)
        elif target == DeployTarget.CLOUDFLARE:
            return await self.deploy_cloudflare(project, config)
        
        # 4. Configure custom domain (if provided)
        if project.custom_domain:
            await self.configure_domain(target, project.custom_domain)
        
        # 5. Run smoke tests
        await self.smoke_test(result.url)
        
        return DeployResult(url=result.url, status="success")

    def generate_config(self, project: VibeProject, target: DeployTarget) -> DeployConfig:
        return DeployConfig(
            build_command="pnpm run build",
            output_directory=".next" if target != DeployTarget.CLOUDFLARE else "dist",
            env_vars=self.collect_env_vars(project),
            headers=self.generate_headers(project),
            rewrites=self.generate_rewrites(project),
        )
```

### 2.3 Environment Variable Management

```yaml
# Generated .env.production (never committed)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
RESEND_API_KEY=re_...
UPSTASH_REDIS_URL=redis://...
MEILISEARCH_URL=https://...
MEILISEARCH_API_KEY=...
```

### 2.4 Custom Domain Flow

1. User enters domain in Studio → "Deploy" dialog
2. Platform verifies ownership (DNS TXT record)
3. Platform provisions SSL (Let's Encrypt / managed)
4. Platform configures DNS (CNAME/ALIAS)
5. Health check passes → domain active

---

## 3. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | Deploy to Vercel completes in < 3min | Timing test |
| AC-02 | Deployed app serves real traffic (auth, DB, API) | E2E test |
| AC-03 | Custom domain configured with SSL in < 5min | Integration test |
| AC-04 | Environment variables synced correctly | Smoke test |
| AC-05 | Rollback to previous deployment works | Manual test |
| AC-06 | Deploy logs streamed to Studio in real-time | UI test |
| AC-07 | Failed deploy shows actionable errors | Error injection test |

---

## 4. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-702.1 | Implement Vercel deployment via API | Platform | 3 days |
| R-702.2 | Implement Netlify deployment via API | Platform | 3 days |
| R-702.3 | Implement Cloudflare Pages deployment | Platform | 3 days |
| R-702.4 | Build deploy UI in Studio (target selector, domain input) | Frontend | 2 days |
| R-702.5 | Environment variable collection and validation | Backend | 2 days |
| R-702.6 | Custom domain verification + SSL provisioning | Platform | 3 days |
| R-702.7 | Deploy status polling + log streaming | Platform | 2 days |

---

## 5. Files to Create/Modify

### New Files
- `services/agent-engine/src/omnistackai_agent_engine/deploy/vibe_deploy.py`
- `services/agent-engine/src/omnistackai_agent_engine/deploy/vercel.py`
- `services/agent-engine/src/omnistackai_agent_engine/deploy/netlify.py`
- `services/agent-engine/src/omnistackai_agent_engine/deploy/cloudflare.py`
- `apps/console-web/app/studio/deploy-dialog.tsx`

### Modified Files
- `services/agent-engine/src/omnistackai_agent_engine/intake/vibe_build.py` (add deploy step)
- `apps/console-web/app/studio/page.tsx` (deploy button integration)

---

## 6. Definition of Done

- [ ] One-click deploy to Vercel, Netlify, Cloudflare works
- [ ] Custom domain + SSL automated
- [ ] Environment variables managed securely
- [ ] Deploy logs visible in Studio
- [ ] Rollback capability
- [ ] Production app fully functional (not just static)