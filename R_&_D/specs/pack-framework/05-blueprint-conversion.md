# Spec: Blueprint Structure & Template-to-Blueprint Conversion

**Tracker ID:** R-601-R-603 (Blueprint Conversion)
**Phase:** 2 — Pack Framework
**Priority:** P0
**Estimated Effort:** 3 weeks
**Dependencies:** R-600 composer
**Status:** Draft

---

## Blueprint Directory Structure

```
solution_packs/{domain}-blueprint/
├── manifest.json                    # Pack manifest v2 (domain core)
├── blueprint/
│   ├── apps/
│   │   ├── customer/               # IR + page specs for customer app
│   │   ├── provider/               # IR + page specs for provider app
│   │   ├── admin/                  # IR + page specs for admin app
│   │   └── api/                    # IR + API specs
│   ├── shared/
│   │   ├── types/                  # TypeScript type generators
│   │   ├── hooks/                  # React hook generators
│   │   ├── formatters/             # Domain formatters
│   │   └── validators/             # Zod schema generators
│   ├── migrations/
│   │   └── *.sql.j2               # Parameterized migrations
│   ├── seeds/
│   │   └── *.py                   # Faker-based seed generators
│   ├── supabase/
│   │   ├── rls_policies.sql       # Row-level security policies
│   │   └── functions/             # Edge functions
│   └── page_templates/
│       └── **/*.tsx.j2            # Jinja2 templates per role/screen
```

## Conversion Process (Per Template)

For each template in `templates/catalog/`:

1. **Extract IR** from existing generated code (reverse engineer)
2. **Identify State Machines** from business logic
3. **Extract Page Templates** as Jinja2 with IR slots
4. **Parameterize Migrations** with variables
5. **Create Seed Generators** using Faker
6. **Define Dependencies** on horizontal packs
7. **Validate** by regenerating template from blueprint
8. **Test** generated output matches original behavior

## Three Seed Blueprints

| Template | Blueprint | Target Apps |
|----------|-----------|-------------|
| `templates/catalog/care-clinic/` | `solution_packs/healthcare-blueprint/` | patient, doctor, admin, api |
| `templates/catalog/ride-now/` | `solution_packs/mobility-blueprint/` | customer, driver, admin, api |
| `templates/catalog/bazaar/` | `solution_packs/commerce-blueprint/` | buyer, seller, admin, api |

## Template-to-Blueprint Mapping

| Template File | Blueprint Output |
|---------------|------------------|
| `template.json` | `manifest.json` (v2) |
| `repo/apps/patient/` | `blueprint/apps/customer/` |
| `repo/apps/doctor/` | `blueprint/apps/provider/` |
| `repo/apps/admin/` | `blueprint/apps/admin/` |
| `repo/services/api/` | `blueprint/apps/api/` |
| `repo/packages/shared/` | `blueprint/shared/` |
| `repo/database/migrations/` | `blueprint/migrations/` |
| `repo/database/seeds/` | `blueprint/seeds/` |
| `repo/supabase/` | `blueprint/supabase/` |

## Acceptance Criteria

- [ ] All 3 blueprints created with full structure
- [ ] Each blueprint regenerates its template exactly
- [ ] Jinja2 templates have correct IR slots
- [ ] Migrations parameterized with variables
- [ ] Seed generators use Faker with domain logic
- [ ] RLS policies cover all role permissions
- [ ] Cross-blueprint composition works

## Files to Create

- `solution_packs/healthcare-blueprint/`
- `solution_packs/mobility-blueprint/`
- `solution_packs/commerce-blueprint/`