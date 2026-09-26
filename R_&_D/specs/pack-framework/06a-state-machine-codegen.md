# Spec: State Machine Codegen (R-604)

**Tracker ID:** R-604
**Phase:** 2 — Pack Framework
**Priority:** P0
**Estimated Effort:** 1 week
**Dependencies:** R-600 composer
**Status:** Draft

---

## Input (from pack manifest ir_delta.state_machines)

```json
{
  "appointment_lifecycle": {
    "states": ["requested", "confirmed", "in_progress", "completed", "cancelled", "no_show"],
    "transitions": {
      "requested": ["confirmed", "cancelled"],
      "confirmed": ["in_progress", "cancelled", "no_show"],
      "in_progress": ["completed", "cancelled"],
      "completed": [],
      "cancelled": ["requested"],
      "no_show": ["requested"]
    },
    "guards": {
      "confirm": "provider.available_at(slot) AND patient.eligible",
      "start": "provider.checked_in AND patient.checked_in",
      "complete": "provider.authorized"
    },
    "actions": {
      "on_confirm": ["send_confirmation", "create_calendar_event", "notify_provider"],
      "on_complete": ["generate_soap_note", "create_prescription_draft", "schedule_followup"]
    }
  }
}
```

## Output — Three Artifacts

### 1. Backend Transition API (Hono/Express)
```typescript
// apps/api/src/routes/{entity}.transitions.ts
app.patch("/{entity-plural}/:id/transition", zValidator("json", transitionSchema), async (c) => {
  const { transition } = c.req.valid("json");
  const entity = await db.query.{entity}.findFirst({ where: eq({entity}.id, id) });
  
  // Guard evaluation
  const guard = STATE_MACHINES.{machine_name}.guards[transition];
  if (guard && !evalGuard(guard, { entity, user: c.get("user") })) {
    return c.json({ error: `Guard failed: ${transition}` }, 400);
  }
  
  // Valid transition check
  const valid = STATE_MACHINES.{machine_name}.transitions[entity.status]?.includes(transition);
  if (!valid) return c.json({ error: `Invalid transition: ${entity.status} -> ${transition}` }, 400);
  
  // Execute actions
  for (const action of STATE_MACHINES.{machine_name}.actions[`on_${transition}`] || []) {
    await executeAction(action, { entity, user: c.get("user") });
  }
  
  // Update state
  const updated = await db.update({entity}).set({ status: transition }).where(eq({entity}.id, id)).returning();
  
  // Emit realtime event
  await c.get("realtime").publish("{entity-plural}.changes", { 
    type: "TRANSITION", 
    from: entity.status, 
    to: transition, 
    record: updated[0] 
  });
  
  return c.json(updated[0]);
});
```

### 2. Frontend State Transition UI
```tsx
// packages/ui/src/composed/StateTransitionBadge.tsx
export function StateTransitionBadge({ 
  entity, 
  stateMachine, 
  currentState, 
  onTransition 
}) {
  const validTransitions = useMemo(
    () => STATE_MACHINES[stateMachine].transitions[currentState] || [], 
    [stateMachine, currentState]
  );
  
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Badge variant={stateVariant(currentState)}>{currentState}</Badge>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        {validTransitions.map((next) => (
          <DropdownMenuItem key={next} onClick={() => onTransition(next)}>
            {transitionIcon(next)} {next}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

### 3. Audit Log Migration
```sql
-- Migration: 0003_{machine_name}_audit.sql
CREATE TABLE {entity}_state_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  {entity}_id UUID REFERENCES {entity}(id),
  from_state VARCHAR(50) NOT NULL,
  to_state VARCHAR(50) NOT NULL,
  triggered_by UUID REFERENCES users(id),
  guard_evaluations JSONB,
  actions_executed JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_{entity}_transitions_{entity}_id ON {entity}_state_transitions({entity}_id);
CREATE INDEX idx_{entity}_transitions_created_at ON {entity}_state_transitions(created_at);
```

## Guard/Action Runtime

```python
# services/agent-engine/src/omnistackai_agent_engine/codegen/state_machine.py

def eval_guard(guard_expr: str, context: dict) -> bool:
    """Safely evaluate guard expression in sandboxed context."""
    allowed_names = {"provider", "patient", "slot", "user", "entity", "now"}
    # Use restricted eval or compile to AST and validate
    ...

def execute_action(action_name: str, context: dict) -> None:
    """Execute registered action by name."""
    action_registry = {
        "send_confirmation": send_confirmation_email,
        "create_calendar_event": create_google_calendar_event,
        "notify_provider": send_push_notification,
        "generate_soap_note": create_soap_note_draft,
        ...
    }
    action_registry[action_name](context)
```

## Acceptance Criteria

- [ ] State machine definition generates all 3 artifacts
- [ ] Backend API validates guards, transitions, executes actions
- [ ] Frontend badge shows only valid transitions
- [ ] Audit log captures from/to state, user, guards, actions
- [ ] Realtime event emitted on transition
- [ ] TypeScript types generated for states/transitions

## Files to Create

- `services/agent-engine/src/omnistackai_agent_engine/codegen/state_machine.py`
- `services/agent-engine/src/omnistackai_agent_engine/codegen/state_machine_runtime.ts`