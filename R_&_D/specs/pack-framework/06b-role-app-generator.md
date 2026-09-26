# Spec: Role-Based App Generator (R-605)

**Tracker ID:** R-605
**Phase:** 2 — Pack Framework
**Priority:** P0
**Estimated Effort:** 1 week
**Dependencies:** R-600 composer, R-604 state machines
**Status:** Draft

---

## Input

```python
role_permissions = [
    {"role": "patient", "entity": "Appointment", "actions": ["read_own", "create", "cancel"]},
    {"role": "provider", "entity": "Appointment", "actions": ["read_assigned", "transition"]},
    {"role": "admin", "entity": "Appointment", "actions": ["read_all", "write", "manage_schedule"]},
]
screens = [
    {"id": "patient-booking", "role": "patient", "template": "booking-flow"},
    {"id": "provider-schedule", "role": "provider", "template": "calendar-ui"},
    {"id": "admin-queue", "role": "admin", "template": "walkin-queue"},
]
```

## Output Per Role

### Patient App (apps/patient/)
```
apps/patient/
├── src/
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx                    # Dashboard with upcoming appointments
│   │   │   ├── book/page.tsx               # Booking wizard
│   │   │   ├── appointments/page.tsx       # List with filters
│   │   │   ├── prescriptions/page.tsx
│   │   │   └── profile/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── Navigation.tsx                  # Patient nav: Dashboard, Book, Appointments, Profile
│   │   └── AppointmentCard.tsx
│   ├── lib/
│   │   ├── api.ts                          # Scoped: only patient endpoints
│   │   ├── hooks.ts                        # useMyAppointments, useBookAppointment
│   │   └── permissions.ts                  # canReadOwn, canCreate, canCancel
│   └── styles/
```

### Provider App (apps/provider/)
```
apps/provider/
├── src/
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx                    # Today's schedule
│   │   │   ├── schedule/page.tsx           # Weekly calendar
│   │   │   ├── patients/page.tsx           # Patient list
│   │   │   ├── queue/page.tsx              # Live queue
│   │   │   └── availability/page.tsx       # Manage slots
│   │   └── layout.tsx
│   ├── components/
│   │   ├── Navigation.tsx                  # Provider nav: Schedule, Patients, Queue, Availability
│   │   └── ScheduleView.tsx
│   ├── lib/
│   │   ├── api.ts                          # Scoped: provider endpoints
│   │   ├── hooks.ts                        # useMySchedule, useTransitionAppointment
│   │   └── permissions.ts                  # canReadAssigned, canTransition
│   └── styles/
```

### Admin App (apps/admin/) — Enhanced from admin-crud pack
```
apps/admin/
├── src/
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx                    # Analytics dashboard
│   │   │   ├── appointments/page.tsx       # Full CRUD + bulk actions
│   │   │   ├── providers/page.tsx          # Provider management
│   │   │   ├── schedule/page.tsx           # Clinic-wide calendar
│   │   │   ├── rooms/page.tsx              # Room allocation
│   │   │   ├── billing/page.tsx            # Invoices, payments
│   │   │   ├── audit/page.tsx              # HIPAA audit logs
│   │   │   └── settings/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── Navigation.tsx                  # Admin nav with all sections
│   │   └── AuditLogViewer.tsx
│   ├── lib/
│   │   ├── api.ts                          # Full admin API access
│   │   ├── hooks.ts                        # useAllAppointments, useAnalytics
│   │   └── permissions.ts                  # canReadAll, canWrite, canManageSchedule
│   └── styles/
```

## API Scoping Logic

```python
def generate_scoped_api_client(role: str, permissions: list[RolePermission]) -> str:
    endpoints = []
    for perm in permissions:
        if perm.role == role:
            # Generate typed hook per action
            for action in perm.actions:
                if action == "read_own":
                    endpoints.append(f"useList{perm.entity}s(filters={{mine: true}})")
                elif action == "read_assigned":
                    endpoints.append(f"useList{perm.entity}s(filters={{assignedToMe: true}})")
                elif action == "read_all":
                    endpoints.append(f"useList{perm.entity}s()")
                elif action == "create":
                    endpoints.append(f"useCreate{perm.entity}()")
                elif action.startswith("transition"):
                    endpoints.append(f"useTransition{perm.entity}()")
    return "\n".join(endpoints)
```

## Navigation Generation

```python
def generate_navigation(role: str, screens: list[ScreenSpec]) -> NavigationConfig:
    role_screens = [s for s in screens if s.role == role]
    groups = group_by_category(role_screens)
    
    return NavigationConfig(
        items=[
            NavItem(label=cat.title(), href=f"/{cat}", icon=cat_icon(cat), children=[
                NavItem(label=s.title, href=s.route, icon=s.icon)
                for s in screens
            ])
            for cat, screens in groups.items()
        ]
    )
```

## Acceptance Criteria

- [ ] Each role gets separate app with correct navigation
- [ ] API client scoped to role permissions
- [ ] Pages generated from screens with matching role
- [ ] Permissions enforced at API level (RLS + middleware)
- [ ] No cross-role data leakage possible

## Files to Create

- `services/agent-engine/src/omnistackai_agent_engine/codegen/role_app.py`