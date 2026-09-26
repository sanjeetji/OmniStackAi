# Spec: Pack Manifest v2 Schema

**Tracker ID:** R-600
**Phase:** 2 — Pack Framework
**Priority:** P0
**Estimated Effort:** 1 week
**Dependencies:** R-433, R-435, R-437
**Status:** Draft

---

## Pack Manifest v2 Schema (JSON)

```json
{
  "schema_version": "2.0",
  "pack_id": "healthcare-appointments",
  "version": "1.0.0",
  "display_name": "Healthcare Appointments",
  "category": "vertical",
  "domain": "healthcare",
  "description": "Appointment scheduling, state machine, reminders, telehealth",
  "dependencies": {
    "horizontal": ["auth-rbac", "database-pg", "api-core", "notifications", "scheduling", "real-time"],
    "vertical": ["healthcare-patients", "healthcare-providers"],
    "conflicts": []
  },
  "ir_delta": {
    "entities": [
      { "name": "Appointment", "fields": [...], "state_machine": "appointment_lifecycle" },
      { "name": "AvailabilitySlot", "fields": [...], "indexes": ["provider_id, start_time"] }
    ],
    "state_machines": {
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
    },
    "apis": [
      { "method": "POST", "path": "/appointments", "auth": "patient", "request": "CreateAppointmentDTO" },
      { "method": "PATCH", "path": "/appointments/{id}/transition", "auth": "provider", "request": "TransitionDTO" }
    ],
    "screens": [
      { "id": "patient-booking", "role": "patient", "template": "booking-flow", "data": ["providers", "availability"] },
      { "id": "provider-schedule", "role": "provider", "template": "calendar-ui", "data": ["appointments", "availability"] }
    ],
    "business_rules": [
      { "entity": "Appointment", "condition": "status == 'confirmed' AND provider.is_available == false", "action": "auto_cancel_with_notification" }
    ],
    "role_permissions": [
      { "role": "patient", "entity": "Appointment", "actions": ["read_own", "create", "transition(requested->cancelled)"] },
      { "role": "provider", "entity": "Appointment", "actions": ["read_assigned", "transition(confirmed->in_progress->completed)"] }
    ]
  },
  "page_templates": {
    "patient-booking": "healthcare/patient/appointment_booking.tsx.j2",
    "provider-schedule": "healthcare/provider/schedule_manager.tsx.j2"
  },
  "seed_generators": {
    "patients": "faker.healthcare.patients(count=150)",
    "providers": "faker.healthcare.providers(count=20)",
    "appointments": "faker.healthcare.appointments(count=770)"
  },
  "migrations": ["0001_appointments.sql.j2", "0002_availability.sql.j2"],
  "config": {
    "env_vars": ["TELEHEALTH_PROVIDER", "SMS_PROVIDER"],
    "feature_flags": ["telehealth_enabled", "walkin_enabled"]
  }
}
```

## Key Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| schema_version | string | Yes | "2.0" |
| pack_id | string | Yes | lowercase-hyphenated unique ID |
| version | string | Yes | semver |
| category | enum | Yes | "horizontal" or "vertical" |
| domain | string | Vertical only | e.g., "healthcare", "mobility" |
| dependencies.horizontal | array | Yes | Horizontal pack IDs required |
| dependencies.vertical | array | No | Vertical pack IDs required |
| dependencies.conflicts | array | No | Pack IDs that conflict |
| ir_delta | object | Yes | ApplicationIR delta (entities, state_machines, apis, screens, business_rules, role_permissions) |
| page_templates | object | No | Screen ID → template path mapping |
| seed_generators | object | No | Entity → faker generator expression |
| migrations | array | No | SQL template files (Jinja2) |
| config.env_vars | array | No | Required environment variables |
| config.feature_flags | array | No | Feature flags this pack introduces |

## Acceptance Criteria

- [ ] JSON schema validates all example manifests
- [ ] ir_delta structure matches ApplicationIR types
- [ ] State machine schema supports guards/actions
- [ ] Role permissions map to RLS policies
- [ ] Template paths resolvable in blueprint directory