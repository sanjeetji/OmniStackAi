# Spec: MVP Vertical Packs (First 10)

**Tracker ID:** R-601-R-610
**Phase:** 2-3 — Pack Framework
**Priority:** P0
**Estimated Effort:** 10 weeks
**Dependencies:** R-600 composer, horizontal packs
**Status:** Draft

---

## MVP Vertical Packs (Weeks 17-28)

| Pack ID | Domain | Depends On (Horizontal) | Key Features |
|---------|--------|------------------------|--------------|
| healthcare-core | Healthcare | auth, scheduling, realtime, communications, files, audit | Patients, providers, appointments, EMR, telehealth, HIPAA, prescriptions, labs |
| mobility-core | Mobility | auth, scheduling, realtime, payments, maps, communications | Rides, drivers, dispatch, routing, surge, vehicle telemetry, earnings |
| commerce-core | Commerce | auth, payments, search, files, notifications, ratings | Listings, cart, checkout, inventory, fulfillment, vendors, commissions |
| fintech-core | FinTech | auth, payments, workflows, audit, compliance, rbac-advanced | Accounts, ledger, transfers, KYC, cards, lending, trading, compliance |
| food-delivery-core | Food | auth, scheduling, realtime, payments, maps, communications | Restaurants, menus, orders, kitchen, couriers, dark stores, substitutions |
| real-estate-core | Real Estate | auth, search, files, communications, workflows, payments | Properties, listings, tours, offers, contracts, escrow, mortgages |
| edtech-core | Education | auth, realtime, files, notifications, analytics, communications | Courses, enrollments, assignments, grades, certificates, LMS, video lessons |
| saas-b2b-core | SaaS/B2B | auth, subscriptions, feature-flags, rbac-advanced, analytics | Orgs, teams, seats, entitlements, SSO, provisioning, usage metering |
| logistics-core | Logistics | auth, real-time, scheduling, maps, analytics, files | Shipments, warehouses, inventory, tracking, route optimization, customs |
| hr-core | HR | auth, workflows, files, notifications, analytics, communications | ATS, onboarding, payroll, performance, attendance, workforce analytics |

## Implementation Order

1. **healthcare-core** (from care-clinic template) — Week 17-18
2. **mobility-core** (from ride-now template) — Week 18-19
3. **commerce-core** (from bazaar template) — Week 19-20
4. **fintech-core** — Week 20-21
5. **food-delivery-core** — Week 21-22
6. **real-estate-core** — Week 22-23
7. **edtech-core** — Week 23-24
8. **saas-b2b-core** — Week 24-25
9. **logistics-core** — Week 25-26
10. **hr-core** — Week 26-27

## Acceptance Criteria Per Pack

- [ ] Manifest v2 complete with ir_delta, state_machines, page_templates
- [ ] Regenerates original template (golden file test)
- [ ] State machines generate backend transitions + frontend UI
- [ ] Role permissions enforced via RLS
- [ ] Seed data produces realistic demo
- [ ] Compose with horizontal packs + other verticals