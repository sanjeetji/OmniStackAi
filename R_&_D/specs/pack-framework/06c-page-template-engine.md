# Spec: Page Template Engine (R-606)

**Tracker ID:** R-606
**Phase:** 2 -- Pack Framework
**Priority:** P0
**Estimated Effort:** 1 week
**Dependencies:** R-600 composer, blueprints
**Status:** Draft

---

## Template Structure
```
blueprint/page_templates/
  healthcare/
    patient/
      appointment_booking.tsx.j2
      telehealth_consult.tsx.j2
      prescription_list.tsx.j2
      lab_results.tsx.j2
    provider/
      patient_detail.tsx.j2
      soap_note_editor.tsx.j2
      schedule_manager.tsx.j2
    admin/
      audit_log_viewer.tsx.j2
      walkin_queue.tsx.j2
```

## Template Example
```jinja2
{# healthcare/patient/appointment_booking.tsx.j2 #}
{% extends "layouts/patient-layout.tsx.j2" %}

{% block content %}
<AnimatedHero 
  title="{{ archetype_data.hero_title | default('Book Your Appointment') }}"
  subtitle="{{ archetype_data.hero_subtitle | default('Find the right provider and book instantly') }}"
  animation="fade-up"
/>

<CommandPalette 
  placeholder="Search providers, specialties, symptoms..."
  data-sources="{{ providers | tojson }}"
/>

<FilterSidebar 
  filters="{{ filter_config | tojson }}"
  on-filter="handleFilterChange"
/>

<DataGrid
  columns="{{ provider_columns | tojson }}"
  data="{{ providers }}"
  row-click="selectProvider"
  virtualized
/>

<Wizard
  steps="{{ booking_steps | tojson }}"
  initial-data="{{ booking_draft | tojson }}"
  on-complete="submitBooking"
/>
{% endblock %}
```

## IR Slot Injection
```python
def render_page_template(template_path: str, ir: ApplicationIR, screen: ScreenSpec) -> str:
    context = {
        "screen": screen,
        "archetype_data": ir.archetype_config,
        "entities": ir.entities,
        "filter_config": build_filter_config(screen, ir),
        "provider_columns": build_columns(screen.entity, ir),
        "booking_steps": build_wizard_steps(screen, ir),
        "booking_draft": get_draft(screen.id),
    }
    return jinja_env.get_template(template_path).render(**context)
```

## Acceptance Criteria
- [ ] Jinja2 templates render with IR data, produce valid TSX
- [ ] Template inheritance works (layouts + content blocks)
- [ ] All IR slots populated (entities, archetype, filters, columns, steps)
- [ ] Generated pages pass TypeScript compilation
- [ ] Visual regression tests pass for each template

## Files to Create
- services/agent-engine/src/omnistackai_agent_engine/codegen/page_template_engine.py
