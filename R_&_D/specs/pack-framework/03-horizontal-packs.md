# Spec: Horizontal Packs Registry (30 Packs)

**Tracker ID:** R-601-R-630 (Horizontal)
**Phase:** 2-3 — Pack Framework
**Priority:** P0
**Estimated Effort:** 12 weeks
**Dependencies:** R-600 composer
**Status:** Draft

---

## Horizontal Packs (Universal — Every App Needs These)

| Pack ID | Category | Provides | State Machine |
|---------|----------|----------|---------------|
| auth-rbac | Identity | Login, register, roles, permissions, JWT, sessions, passkeys | User: invited→active→suspended→deleted |
| payments | Commerce | Stripe/Razorpay, checkout, webhooks, subscriptions, invoices, refunds | Payment: pending→succeeded/failed/refunded |
| notifications | Communication | Email/SMS/push, templates, preferences, in-app center, digest | Notification: queued→sent→delivered/failed |
| files-storage | Media | S3 presigned URLs, upload progress, preview, PDF generation, CDN | File: uploading→processing→ready/failed |
| search | Discovery | Meilisearch/Typesense, faceted search, saved searches, synonyms | — |
| real-time | Communication | Socket.io/Supabase Realtime, presence, live updates, typing indicators | Connection: connecting→connected→reconnecting→disconnected |
| workflows | Logic | Generic state machine engine, transitions, guards, actions, audit | Meta: any entity can have SM |
| admin-crud | Admin | Generated admin: tables, filters, bulk actions, audit log, exports | — |
| multi-app | Platform | Shared API, cross-app auth, preview proxy, deployment coordination | — |
| audit-compliance | Compliance | Immutable audit log, GDPR export, retention policies, data lineage | AuditEntry: created (append-only) |
| analytics | Analytics | Event tracking, GA4/Mixpanel/PostHog, dashboards, funnels, cohorts | — |
| scheduling | Time | Calendar, recurring rules, conflicts, timezones, bookings, reminders | Slot: available→held→booked→completed/cancelled |
| communications | Communication | Chat, comments, mentions, threads, attachments, reactions | Message: draft→sent→read |
| ratings-reviews | Social | Stars, written reviews, moderation, aggregates, helpful votes | — |
| referrals-affiliates | Growth | Codes, tracking, rewards, payouts, multi-level | Referral: pending→qualified→paid |
| subscriptions | Commerce | Plans, trials, upgrades/downgrades, proration, churn, dunning | Subscription: trialing→active→past_due→canceled |
| marketplace-core | Commerce | Two-sided matching, commissions, payouts, disputes, escrow | Order: created→matched→in_progress→completed |
| localization | Platform | i18n, RTL, currency, date/number formatting, translation management | — |
| feature-flags | Platform | Rollouts, targeting, experimentation, kill switches | — |
| api-docs | Platform | OpenAPI spec, Swagger UI, Postman collection, SDK generation | — |
| rbac-advanced | Identity | ABAC, resource-level permissions, org hierarchies, impersonation | — |
| webhooks | Integration | Outgoing webhook management, retry, signature verification, dead letter | — |
| cache | Performance | Redis/Valkey integration, cache invalidation, distributed caching | — |
| queue | Async | Background jobs, BullMQ/Inngest, dead letter, priority queues, scheduling | — |
| secrets | Security | Vault/Env management, rotation, audit, dynamic secrets | — |
| observability | Platform | OpenTelemetry, logs, metrics, traces, Sentry, alerting | — |
| testing | Quality | E2E (Playwright), contract testing, visual regression, mutation testing | — |
| storybook | Design | Component docs, visual testing, design system playground, a11y testing | — |
| pwa | Platform | Service Worker, IndexedDB, offline-first, push notifications, background sync | — |
| accessibility | Quality | WCAG 2.1 AA, axe-core, automated a11y testing, color contrast | — |
| performance | Quality | Bundle analysis, Core Web Vitals, Lighthouse CI, regression detection | — |

## Implementation Notes

Each horizontal pack follows the manifest v2 schema with:
- Minimal ir_delta (entities, APIs, screens for that capability)
- No vertical dependencies
- Horizontal dependencies only on lower-level packs (e.g., payments depends on auth-rbac, api-core)
- State machines where applicable
- Seed generators for demo data

## Acceptance Criteria

- [ ] All 30 packs defined with manifest v2
- [ ] Dependency graph has no cycles
- [ ] Each pack generates working code in isolation
- [ ] Packs compose without conflicts via composer
- [ ] Integration tests for top 10 pack combinations