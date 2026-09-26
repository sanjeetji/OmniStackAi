# Spec: Cloud Deploy Adapters (Engineering Mode)

**Tracker ID:** R-627
**Phase:** 4 — Engineering Mode Hardening
**Priority:** P1
**Estimated Effort:** 6 weeks
**Dependencies:** R-600 pack framework
**Status:** Draft

---

## Supported Targets
| Platform | Adapter | Features |
|----------|---------|----------|
| Vercel | vercel.ts | Edge functions, ISR, custom domains, analytics, preview deployments |
| Cloudflare Pages | cloudflare.ts | Workers, KV, D1, R2, custom domains, zero cold start |
| AWS | aws.ts | Amplify, ECS/Fargate, Lambda, RDS, CloudFront, Route53 |
| GCP | gcp.ts | Cloud Run, Cloud SQL, Firebase, Cloud CDN, Cloud DNS |
| Azure | azure.ts | Static Web Apps, Container Apps, PostgreSQL, Front Door |
| Kubernetes | k8s.ts | Helm charts, Kustomize, ArgoCD, cert-manager, ingress-nginx |
| Docker Compose | docker.ts | Local, VPS, any Docker host, Traefik, Let's Encrypt |
| BYOC | byoc.ts | Customer cloud credentials, Terraform/Pulumi, policy-as-code |

## Adapter Interface
```typescript
interface DeployAdapter {
  name: string;
  
  // Pre-deploy validation
  validate(project: EngineeringProject): Promise<ValidationResult>;
  
  // Generate IaC
  generateIaC(project: EngineeringProject): Promise<IaCOutput>;
  
  // Deploy
  deploy(project: EngineeringProject, iac: IaCOutput): Promise<DeployResult>;
  
  // Post-deploy
  configureDomains(result: DeployResult, domains: string[]): Promise<void>;
  
  // Rollback
  rollback(deploymentId: string): Promise<void>;
  
  // Logs
  streamLogs(deploymentId: string): AsyncIterable<LogEntry>;
}
```

## Engineering Mode Deploy Flow
```python
class EngineeringDeployer:
    async def deploy(self, project: EngineeringProject, target: DeployTarget) -> DeployResult:
        adapter = self.get_adapter(target)
        
        # 1. Validate
        validation = await adapter.validate(project)
        if not validation.valid:
            raise ValidationError(validation.errors)
        
        # 2. Generate IaC
        iac = await adapter.generateIaC(project)
        
        # 3. Deploy
        result = await adapter.deploy(project, iac)
        
        # 4. Configure domains
        if project.custom_domains:
            await adapter.configureDomains(result, project.custom_domains)
        
        # 5. Smoke test
        await self.smoke_test(result.url)
        
        return result
```

## IaC Output Examples

### Vercel (vercel.json)
```json
{
  "buildCommand": "pnpm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1"],
  "env": {
    "NEXT_PUBLIC_SUPABASE_URL": "@supabase-url",
    "STRIPE_SECRET_KEY": "@stripe-secret"
  },
  "headers": [
    {"source": "/(.*)", "headers": [{"key": "X-Content-Type-Options", "value": "nosniff"}]}
  ],
  "rewrites": [
    {"source": "/api/(.*)", "destination": "/api/$1"}
  ]
}
```

### Kubernetes (Helm values.yaml)
```yaml
# Generated per app
apps:
  web:
    image: "registry.example.com/project/web:sha-abc123"
    replicas: 3
    resources:
      limits: { cpu: "500m", memory: "512Mi" }
    autoscaling:
      enabled: true
      minReplicas: 2
      maxReplicas: 10
    ingress:
      enabled: true
      hostname: "app.example.com"
      tls: true
  api:
    image: "registry.example.com/project/api:sha-abc123"
    replicas: 2
    env:
      - name: DATABASE_URL
        valueFrom:
          secretKeyRef: { name: project-secrets, key: database-url }
```

## Acceptance Criteria
- [ ] Each adapter validates project before deploy
- [ ] IaC generates valid configuration for target
- [ ] Deploy completes with health checks
- [ ] Custom domains configured with SSL
- [ ] Rollback works in < 30s
- [ ] Logs stream to Studio in real-time
- [ ] BYOC uses customer credentials only

## Files to Create
- services/agent-engine/src/omnistackai_agent_engine/deploy/vercel.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/cloudflare.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/aws.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/gcp.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/azure.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/k8s.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/docker.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/byoc.ts
- services/agent-engine/src/omnistackai_agent_engine/deploy/registry.ts
