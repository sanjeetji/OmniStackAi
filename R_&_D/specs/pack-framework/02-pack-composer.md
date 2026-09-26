# Spec: Pack Composer — Merge, Wire, Validate

**Tracker ID:** R-600 (continued)
**Phase:** 2 — Pack Framework
**Priority:** P0
**Estimated Effort:** 1 week
**Dependencies:** R-600 manifest schema
**Status:** Draft

---

## Composition Algorithm

```python
# services/agent-engine/src/omnistackai_agent_engine/intake/composer.py

class PackComposer:
    def compose(self, 
        primary_domain: str,
        secondary_domains: list[str],
        requirements: dict,
        selected_packs: list[str] = None
    ) -> ApplicationIR:
        """
        1. Start with BASE_IR (auth, users, organizations, design tokens)
        2. Apply CORE_HORIZONTAL (always): auth-rbac, database-pg, api-core, design-system, admin-crud
        3. Apply DOMAIN_HORIZONTAL (from requirements): payments, realtime, files, search, workflows
        4. Apply PRIMARY_VERTICAL (from primary_domain): healthcare-core, mobility-core, commerce-core
        5. Apply SECONDARY_VERTICAL (from secondary_domains): pets, subscriptions, marketplace
        6. Apply REQUIREMENT_PACKS (from requirements): hipaa, pci-dss, gdpr
        7. MERGE: resolve conflicts (entity fields, API paths, screen routes)
        8. WIRE: cross-pack API endpoints, shared hooks, unified admin, realtime channels
        9. VALIDATE: validate_ir() — no circular deps, all refs resolve, contracts match
        10. RETURN: coherent ApplicationIR
        """
```

## Conflict Resolution Rules

| Conflict Type | Resolution Strategy |
|---------------|---------------------|
| Entity field overlap | Merge fields, prefix with pack namespace if semantic conflict |
| API path collision | Namespace by pack: `/healthcare/appointments` vs `/mobility/rides` |
| Screen route collision | Prefix with role: `/patient/appointments` vs `/driver/rides` |
| State machine name clash | Prefix with domain: `healthcare_appointment_lifecycle` |
| Dependency version mismatch | Use highest compatible, warn if breaking |
| Design token override | Last pack wins, but log warning |

## Merge Logic

```python
def merge_ir_deltas(base: ApplicationIR, delta: IRDelta) -> ApplicationIR:
    # Entities: merge by name, combine fields, deduplicate indexes
    # State machines: prefix with pack domain, merge if same name
    # APIs: group by path prefix, combine into single router
    # Screens: group by role, merge navigation
    # Business rules: combine, sort by priority
    # Role permissions: union by (role, entity), combine actions
```

## Validation Rules

1. **No circular dependencies** in pack dependency graph
2. **All references resolve** — every entity/API/screen referenced exists
3. **Contracts match** — API request/response schemas align across packs
4. **State machine consistency** — all transitions reference valid states
5. **Permission completeness** — every entity has at least one role with read access
6. **Screen data requirements** — every screen's data hooks exist in IR

## Acceptance Criteria

- [ ] Composer merges 10+ packs without manual intervention
- [ ] All 6 conflict types resolved correctly
- [ ] Validation catches circular deps, broken refs, contract mismatches
- [ ] Output IR passes `validate_ir()` 
- [ ] Deterministic: same input → byte-identical IR

## Files to Create

- `services/agent-engine/src/omnistackai_agent_engine/intake/composer.py`
- `services/agent-engine/src/omnistackai_agent_engine/intake/merge.py`
- `services/agent-engine/src/omnistackai_agent_engine/intake/validate.py`