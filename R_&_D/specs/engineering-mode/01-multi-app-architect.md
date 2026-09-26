# Spec: Multi-App Architect (Engineering Mode Core)

**Tracker ID:** R-800
**Phase:** 2 — Engineering Mode Depth
**Priority:** P0
**Estimated Effort:** 4 weeks
**Dependencies:** R-600 (Pack Manifest v2), R-602 (Pack Composer), R-706 (Unified Studio)
**Status:** Draft

---

## 1. Problem Statement

Engineering Mode must enable users to design, configure, and generate **coordinated multi-app ecosystems** (customer web, driver mobile, admin web, marketing web, backend API) from a single unified IR. This is our core differentiator vs. v0, Lovable, Bolt, Emergent, Dyad — none generate true multi-app platforms with shared contracts, types, and deployment topology.

---

## 2. Competitive Analysis

| Feature | v0 | Lovable | Bolt | Emergent | Dyad | **OmniStackAI Target** |
|---------|----|---------|------|----------|------|------------------------|
| Multi-app generation | ❌ | ❌ | ❌ | Partial (web + mobile) | ❌ | ✅ **5+ coordinated apps** |
| Shared types/contracts | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **packages/shared** |
| Per-app framework choice | ❌ | ❌ | ❌ | Locked (Expo+FastAPI) | Locked (Capacitor) | ✅ **Next.js/RN/Native/Flutter** |
| Cross-app API contracts | ❌ | ❌ | ❌ | Basic | ❌ | ✅ **OpenAPI + Zod + hooks** |
| Unified deployment topology | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **K8s + Helm + per-app targets** |
| Role-based app generation | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **Per-role nav/pages/API scope** |

---

## 3. Requirements

### 3.1 Multi-App Architect UI (Engineering Mode)

```tsx
// apps/console-web/app/studio/engineering/multi-app-architect.tsx

interface AppSurface {
  id: string;
  name: string;
  role: 'customer' | 'driver' | 'admin' | 'operator' | 'marketing' | 'merchant' | 'partner' | 'api';
  framework: 'nextjs' | 'react-native' | 'native-kotlin' | 'native-swift' | 'flutter' | 'hono' | 'fastapi' | 'express';
  surfaces: ('web' | 'mobile' | 'desktop' | 'cli')[];
  features: string[]; // pack IDs
  deployment: DeploymentTarget;
  domain?: string;
}

interface MultiAppProject {
### 3.2 IR Schema for Multi-App

```python
# application_ir/multi_app.py

class AppSurfaceIR:
    id: str
    name: str
    role: AppRole
    framework: Framework
    surfaces: list[Surface]
    pages: list[PageSpec]
    components: list[ComponentSpec]
    api_endpoints: list[ApiEndpoint]
    permissions: RolePermissionMatrix
    state_machines: list[StateMachine]
    business_rules: list[BusinessRule]
    deployment: DeploymentConfig

class MultiAppIR:
    project_id: str
    name: str
    version: str
    shared: SharedIR
    apps: list[AppSurfaceIR]
    topology: TopologyIR
    contracts: ContractIR
    packs_applied: list[PackRef]

class SharedIR:
    entities: list[Entity]
    enums: list[Enum]
    types: list[TypeDef]
    api_contracts: list[ApiContract]
    events: list[EventSchema]
    state_machines: list[StateMachine]
    validators: list[ValidatorSpec]
    formatters: list[FormatterSpec]
    hooks: list[HookSpec]
    components: list[ComponentSpec]
```
  projectId: string;
  name: string;
  sharedPackages: SharedPackageConfig[];
  apps: AppSurface[];
  topology: DeploymentTopology;
  contracts: ContractConfig;
}
```

### 3.3 Role-Based App Generation

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/role_app.py

class RoleAppGenerator:
    ROLE_TEMPLATES = {
        'customer': {
            'nav': ['Home', 'Browse', 'Orders', 'Profile', 'Support'],
            'pages': ['landing', 'catalog', 'product-detail', 'cart', 'checkout', 'order-history', 'order-detail', 'profile', 'settings', 'support'],
            'api_scope': ['read:products', 'write:orders', 'read:own-orders', 'write:own-profile'],
            'state_machines': ['order', 'cart', 'subscription'],
        },
        'driver': {
            'nav': ['Dashboard', 'Jobs', 'Earnings', 'Schedule', 'Profile'],
            'pages': ['job-board', 'job-detail', 'navigation', 'earnings-dashboard', 'schedule-manager', 'profile'],
            'api_scope': ['read:assigned-jobs', 'write:job-status', 'read:own-earnings', 'write:location'],
            'state_machines': ['job', 'shift', 'payout'],
        },
        'admin': {
            'nav': ['Overview', 'Users', 'Orders', 'Drivers', 'Analytics', 'Settings', 'Audit'],
            'pages': ['dashboard', 'user-management', 'order-management', 'driver-management', 'analytics', 'settings', 'audit-log'],
            'api_scope': ['admin:*'],
            'state_machines': [],
        },
        'operator': {
            'nav': ['Dispatch', 'Queue', 'Live Map', 'Incidents', 'Reports'],
            'pages': ['dispatch-board', 'walk-in-queue', 'live-tracking', 'incident-management', 'reports'],
            'api_scope': ['write:dispatch', 'read:live-locations', 'write:incidents'],
            'state_machines': ['dispatch', 'incident'],
        },
        'merchant': {
            'nav': ['Dashboard', 'Products', 'Orders', 'Inventory', 'Analytics', 'Payouts'],
            'pages': ['merchant-dashboard', 'product-catalog', 'order-fulfillment', 'inventory', 'analytics', 'payouts'],
            'api_scope': ['read:own-products', 'write:own-products', 'read:own-orders', 'write:fulfillment', 'read:own-analytics'],
            'state_machines': ['product', 'fulfillment'],
        },
        'partner': {
            'nav': ['Dashboard', 'Referrals', 'Commissions', 'Resources'],
            'pages': ['partner-dashboard', 'referral-tracking', 'commission-reports', 'marketing-resources'],
            'api_scope': ['read:own-referrals', 'read:own-commissions'],
            'state_machines': ['referral'],
        },
    }
```

### 3.4 Deployment Topology Generator

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/deployment_topology.py

class DeploymentTopologyGenerator:
    TARGETS = {
        'vercel': VercelConfig,
        'netlify': NetlifyConfig,
        'cloudflare': CloudflareConfig,
        'kubernetes': K8sConfig,
        'aws': AWSConfig,
        'gcp': GCPConfig,
        'azure': AzureConfig,
        'railway': RailwayConfig,
        'render': RenderConfig,
        'docker': DockerConfig,
    }
    
    def generate(self, ir: MultiAppIR) -> TopologyOutput:
        app_configs = {}
        for app in ir.apps:
            target = self.TARGETS[app.deployment.target]
            app_configs[app.id] = target.generate(app, ir.shared)
        
        shared_infra = SharedInfraConfig(
            database=self.generate_database(ir.shared),
            cache=self.generate_cache(ir.shared),
            message_queue=self.generate_mq(ir.shared),
            secrets=self.generate_secrets(ir.shared),
            monitoring=self.generate_monitoring(ir.shared),
        )
        
        if any(a.deployment.target == 'kubernetes' for a in ir.apps):
---

## 4. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-01 | Create 5-app ecosystem in < 3 min | Timing test |
| AC-02 | Shared types/hooks/api-client in `packages/shared` | File existence + import test |
| AC-03 | Per-app framework selection works | Matrix test |
| AC-04 | Role-based nav/pages/API scope enforced | E2E test per role |
| AC-05 | Cross-app API contracts valid | Contract test |
| AC-06 | Deployment topology generates valid Helm | `helm lint` + dry-run |
| AC-07 | Environment promotion configured | Integration test |
| AC-08 | Graduation from Vibe Mode expands to multi-app | Graduation test |

---

## 5. Implementation Tasks

| Task ID | Description | Owner | Estimate |
|---------|-------------|-------|----------|
| R-800.1 | MultiAppIR schema + validation | AI Engineer | 5 days |
| R-800.2 | RoleAppGenerator with 6 role templates | AI Engineer | 10 days |
| R-800.3 | DeploymentTopologyGenerator (9 targets + Helm) | Platform | 10 days |
| R-800.4 | Multi-App Architect UI | Frontend | 10 days |
| R-800.5 | Shared package generator | AI Engineer | 5 days |
| R-800.6 | Cross-app contract validation | Platform | 5 days |
| R-800.7 | Integration with Pack Composer | AI Engineer | 3 days |

---

## 6. Files to Create/Modify

### New Files
- `application_ir/multi_app.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/role_app.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/deployment_topology.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/shared_package.py`
- `apps/console-web/app/studio/engineering/multi-app-architect.tsx`
- `apps/console-web/app/studio/engineering/app-canvas.tsx`
- `apps/console-web/app/studio/engineering/framework-matrix.tsx`
- `apps/console-web/app/studio/engineering/contract-visualizer.tsx`
- `apps/console-web/app/studio/engineering/deployment-topology.tsx`

### Modified Files
- `services/agent-engine/src/omnistackai_agent_engine/assembler.py`
- `services/agent-engine/src/omnistackai_agent_engine/intake/build_ecosystem.py`
- `services/agent-engine/src/omnistackai_agent_engine/validation/validate_ir.py`

---

## 7. Definition of Done

- [ ] MultiAppIR schema complete with validation
- [ ] 6 role templates generate correct nav/pages/API scope
- [ ] 9 deployment targets + Helm chart generation works
- [ ] Multi-App Architect UI functional in Engineering Mode
- [ ] Shared package generated and consumable by all apps
- [ ] 5-app ecosystem generates, builds, passes tests
- [ ] Graduation from Vibe Mode → Engineering Mode expands to multi-app
- [ ] Documentation: role templates, framework compatibility, deployment targets
            helm_chart = self.generate_helm_chart(ir, app_configs, shared_infra)
        
        environments = self.generate_environments(ir)
        
        return TopologyOutput(
            apps=app_configs,
            shared=shared_infra,
            helm=helm_chart,
            environments=environments,
        )
```
**UI Components:**
- **App Canvas**: Drag-drop app surfaces, connect via shared packages
- **Role Selector**: Predefined roles + custom
- **Framework Matrix**: Per-app framework dropdown with compatibility validation
- **Contract Visualizer**: Graph of shared types, API endpoints, events
- **Deployment Topology**: Per-app target with environment promotion