# Spec: Shared Package Generator (R-607)

**Tracker ID:** R-607
**Phase:** 2-3 -- Pack Framework
**Priority:** P0
**Estimated Effort:** 1 week
**Dependencies:** R-600 composer, blueprints
**Status:** Draft

---

## Output Structure
```
packages/shared/
├── package.json
├── tsconfig.json
├── src/
│   ├── types/
│   │   ├── entities.ts           # All entity interfaces
│   │   ├── api.ts                # Request/response types
│   │   ├── state-machines.ts     # State machine types
│   │   └── index.ts
│   ├── api/
│   │   ├── client.ts             # Typed fetch wrapper
│   │   ├── endpoints.ts          # Endpoint definitions
│   │   └── hooks.ts              # useList, useCreate, useUpdate, useDelete, useTransition
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useRealtime.ts
│   │   ├── usePermissions.ts
│   │   └── useFeatureFlags.ts
│   ├── formatters/
│   │   ├── currency.ts
│   │   ├── dates.ts
│   │   ├── phone.ts
│   │   └── domain-specific/      # e.g., healthcare/medical-codes.ts
│   └── validators/
│       ├── entities.ts           # Zod schemas
│       └── transitions.ts        # State machine transition validators
```

## Generation Logic
```python
def generate_shared_package(ir: ApplicationIR, blueprints: list[Blueprint]) -> SharedPackage:
    return SharedPackage(
        types=generate_types(ir.entities, ir.state_machines),
        api=generate_api_client(ir.apis, ir.state_machines),
        hooks=generate_hooks(ir.apis, ir.state_machines, ir.screens),
        formatters=generate_formatters(blueprints),
        validators=generate_validators(ir.entities, ir.state_machines),
    )
```

## Acceptance Criteria
- [ ] Shared package compiles without errors
- [ ] All entity types exported
- [ ] API client typed for all endpoints
- [ ] Hooks generated for all CRUD + transitions
- [ ] Domain formatters included
- [ ] Zod validators for all entities + transitions
- [ ] Works across all apps in monorepo

## Files to Create
- services/agent-engine/src/omnistackai_agent_engine/codegen/shared_package.py
