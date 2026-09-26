# OmniStackAI Pack Registry — Complete Horizontal & Vertical Pack Catalog

> **Single source of truth** for every pack in the platform. Each pack is a versioned, composable unit that contributes IR deltas, page templates, state machines, API endpoints, and generators.

---

## Pack Manifest v2 Schema (Reference)

```json
{
  "name": "pack-name",
  "version": "1.0.0",
  "type": "horizontal|vertical",
## 1. Core Platform Packs (7)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `database-pg` | PostgreSQL + Drizzle/Prisma + migrations + seeds + RLS | `PostgresClient`, `migrationRunner`, `seedRunner`, `rlsHelper` |
| `api-core` | Hono/Express + Zod + OpenAPI + error handling + rate limiting | `HonoApp`, `zodValidator`, `openapiGenerator`, `rateLimiter` |
| `auth-rbac` | JWT + roles + permissions + sessions + MFA + OAuth providers | `User`, `Role`, `Permission`, `Session`, `user.lifecycle` SM, `/auth/*` endpoints |
| `config-env` | Type-safe env (Zod), feature flags, secrets injection, multi-env | `EnvSchema`, `featureFlags`, `secretRefs` |
| `observability` | OpenTelemetry, structured logs, metrics, traces, Sentry, Datadog | `logger`, `tracer`, `meter`, `errorReporter` |
| `ci-cd` | GitHub Actions + Docker + Helm + preview envs + smoke tests | `ci.yml`, `dockerfile`, `helm-chart`, `preview.yml` |
| `git-ops` | Conventional commits, changelog, version bump, release notes | `commitlint`, `release-plz`, `changesets` |
  "category": "auth|payments|realtime|healthcare|mobility|...",
  "description": "Human-readable purpose",
  "dependencies": ["auth-rbac", "database-pg"],
  "conflicts": [],
  "provides": {
    "entities": ["User", "Role", "Permission"],
    "stateMachines": ["user.lifecycle"],
    "apiEndpoints": [{"path": "/auth/login", "method": "POST"}],
    "pages": ["login", "register", "forgot-password"],
    "components": ["AuthForm", "RoleBadge"],
    "hooks": ["useAuth", "usePermissions"],
    "rlsPolicies": ["user.isolation"],
    "migrations": ["0001_auth.sql"],
## 2. Security & Compliance Packs (6)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `security-headers` | CSP, HSTS, COOP, COEP, permissions-policy, nonce generation | `cspMiddleware`, `nonceGenerator` |
| `audit-log` | Immutable append-only log, tamper-evident, query API, retention | `AuditEntry`, `auditMiddleware`, `auditQueryAPI` |
| `encryption` | Field-level AES-GCM, key rotation, envelope encryption, KMS | `encryptField`, `decryptField`, `keyRotationJob` |
| `compliance-gdpr` | Data export, right to deletion, consent tracking, DPA templates | `gdprExport`, `gdprDelete`, `consentLedger` |
| `compliance-hipaa` | BAA-ready, access controls, audit trails, breach notification | `hipaaAudit`, `phiMasking`, `breachNotifier` |
| `compliance-soc2` | Control mapping, evidence collection, access reviews, policy docs | `soc2Controls`, `evidenceCollector` |

## 3. Data & Storage Packs (5)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `files-storage` | S3/Tigris/R2 + presigned URLs + multipart + CDN + image transform | `File`, `uploadService`, `cdnUrl`, `imageTransform` |
| `search-engine` | Meilisearch/Typesense + faceted search + synonyms + typo tolerance | `SearchIndex`, `searchClient`, `facetedQuery` |
| `cache-layer` | Redis/Valkey + invalidation strategies + distributed locks + sessions | `cacheClient`, `invalidateTags`, `distributedLock` |
| `queue-jobs` | Inngest/Trigger.dev/BullMQ + retries + scheduling + dead-letter | `JobQueue`, `scheduleJob`, `retryPolicy` |
| `analytics-events` | Segment/PostHog/Amplitude + auto-track + funnels + cohorts | `trackEvent`, `identifyUser`, `funnelQuery` |
    "seeds": ["roles.sql", "permissions.sql"],
    "envVars": ["JWT_SECRET", "BCRYPT_ROUNDS"]
  },
  "generators": {
    "backend": ["auth-middleware", "jwt-service", "password-hasher"],
    "frontend": ["auth-pages", "protected-route", "role-guard"],
## 4. Real-time & Communication Packs (5)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `realtime-core` | Supabase Realtime/Ably/Pusher + presence + broadcast + postgres changes | `RealtimeClient`, `presence`, `broadcast`, `postgresChanges` |
| `notifications` | Email (Resend/SendGrid) + SMS (Twilio) + Push (FCM/APNs) + in-app center | `Notification`, `emailProvider`, `smsProvider`, `pushProvider`, `inAppCenter` |
| `communications` | 1:1 chat, group chat, threads, mentions, reactions, attachments | `Message`, `Thread`, `Conversation`, `chatAPI`, `realtimeSync` |
| `video-calling` | WebRTC (LiveKit/Daily) + recording + screen share + transcripts | `Call`, `Recording`, `callAPI`, `webRTCClient` |
| `webhooks` | Outbound webhook delivery + retries + signatures + replay + testing UI | `Webhook`, `deliveryEngine`, `signatureVerifier`, `replayUI` |

## 5. Business Logic & Workflow Packs (7)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `workflows-core` | Generic state machine engine + guards + actions + compensation + versioning | `StateMachine`, `transition`, `guard`, `action`, `compensation` |
| `approvals` | Multi-step approval chains + escalation + delegation + SLA tracking | `ApprovalRequest`, `approvalChain`, `escalationJob` |
| `scheduling` | Calendar + recurring rules (RRULE) + conflicts + timezones + buffers | `TimeSlot`, `RecurrenceRule`, `conflictDetector`, `timezoneHelper` |
| `billing-metering` | Usage metering + aggregation + rating + invoicing + dunning | `UsageEvent`, `meterAggregator`, `ratingEngine`, `invoiceGenerator` |
| `feature-flags` | Boolean/multivariate + targeting + rollouts + experimentation + analytics | `Flag`, `evaluateFlag`, `rolloutStrategy`, `experimentTracker` |
| `audit-trail` | Entity history + diffs + point-in-time queries + compliance export | `EntityHistory`, `diffEngine`, `pitQuery`, `complianceExport` |
| `data-archival` | Tiered storage + retention policies + legal hold + retrieval API | `ArchivePolicy`, `tieringJob`, `legalHold`, `retrieveArchive` |
    "mobile": ["auth-context", "biometric-storage"],
    "shared": ["auth-types", "api-client"]
  },
  "ui": {
    "allowlist": ["framer-motion", "lucide-react"],
    "composedComponents": ["AuthCard", "PasswordStrength"]
  },
  "documentation": "https://docs.omnistack.ai/packs/auth-rbac"
}
```
---

## 1. Healthcare & Life Sciences (12 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Compliance |
|------|----------|--------------|---------------------|----------------|------------|
| `patients` | Core | auth-rbac, database-pg, audit-log | Patient, MedicalRecord, Insurance, Consent | `patient.onboarding` | HIPAA, GDPR |
| `providers` | Core | auth-rbac, database-pg, scheduling | Provider, Specialty, License, Schedule, Credential | `provider.credentialing` | HIPAA |
| `appointments` | Core | patients, providers, scheduling, realtime-core, notifications | Appointment, Slot, Reminder, Waitlist | `appointment.lifecycle` | HIPAA |
| `emr` | Clinical | patients, providers, files-storage, rich-text, audit-trail | Encounter, Note, Diagnosis, Procedure, VitalSigns | `encounter.workflow` | HIPAA |
| `prescriptions` | Clinical | patients, providers, pharmacy-integration, audit-trail | Prescription, Medication, Pharmacy, Fill, PriorAuth | `prescription.lifecycle` | HIPAA, DEA |
| `lab-orders` | Clinical | patients, providers, lab-integration, files-storage | LabOrder, Specimen, Result, Panel, ReferenceRange | `lab.order.lifecycle` | HIPAA, CLIA |
| `telehealth` | Clinical | appointments, video-calling, communications, emr | TelehealthSession, Recording, Consent, TechnicalCheck | `session.connection` | HIPAA |
| `billing-codes` | Revenue | patients, providers, invoicing, tax-compliance | Claim, Code, Payer, Adjudication, Remittance | `claim.lifecycle` | HIPAA, CMS |
| `hipaa-compliance` | Compliance | audit-log, encryption, compliance-hipaa, data-archival | AccessLog, BreachReport, RiskAssessment, BAA | `breach.response` | HIPAA |
| `clinical-trials` | Research | patients, emr, consent-management, audit-trail | Trial, Protocol, Site, Enrollment, AdverseEvent | `trial.phase`, `enrollment.status` | FDA 21 CFR Part 11 |
| `pharmacy-integration` | Integration | prescriptions, communications, webhooks, inventory | Pharmacy, Formulary, Dispense, InteractionCheck | `dispense.workflow` | DEA |
| `lab-integration` | Integration | lab-orders, communications, webhooks, files-storage | LabInterface, Device, Interface, Mapping, QC | `interface.monitoring` | CLIA, HL7 |
## 6. Commerce & Payments Packs (6)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `payments-core` | Stripe/Razorpay/Paddle + PaymentIntent + SetupIntent + refunds + disputes | `Payment`, `paymentIntent`, `refundService`, `disputeHandler` |
| `subscriptions` | Plans + trials + upgrades/downgrades + proration + pausing + cancellation | `Subscription`, `Plan`, `prorationEngine`, `lifecycleManager` |
| `marketplace-payments` | Stripe Connect + escrow + splits + payouts + onboarding + tax | `ConnectedAccount`, `escrowHold`, `splitCalculator`, `payoutScheduler` |
| `invoicing` | Invoice templates + PDF generation + recurring + reminders + payments | `Invoice`, `pdfGenerator`, `recurringScheduler`, `reminderJob` |
| `tax-compliance` | VAT/GST/sales tax + nexus detection + validation + filing (TaxJar/Avalara) | `TaxCalculation`, `nexusDetector`, `validationService`, `filingIntegration` |
| `wallet-ledger` | Double-entry ledger + accounts + transfers + idempotency + reconciliation | `Account`, `LedgerEntry`, `transferService`, `reconciliationJob` |

## 7. User Experience & UI Packs (5)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `design-system` | shadcn/ui + Tailwind v4 + OKLCH tokens + Framer Motion + Radix primitives | `Button`, `Card`, `Dialog`, `tokens.css`, `motionVariants` |
| `forms-engine` | React Hook Form + Zod + multi-step wizards + conditional fields + drafts | `Form`, `Wizard`, `conditionalFields`, `draftPersistence` |
## 2. Mobility & On-Demand (10 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `rides` | Core | auth-rbac, database-pg, realtime-core, scheduling, payments-core | Ride, Route, Fare, Match, Rating, Receipt | `ride.lifecycle` | Surge, pooling, multi-stop |
| `drivers` | Core | auth-rbac, database-pg, scheduling, wallet-ledger, documents | Driver, Vehicle, License, BackgroundCheck, Earnings | `driver.onboarding` | KYC, document expiry |
| `dispatch` | Operations | rides, drivers, realtime-core, mapping, queue-jobs | DispatchZone, AssignmentRule, SurgeZone, Heatmap | `dispatch.assignment` | Auto-dispatch, manual |
| `mapping` | Infra | realtime-core, cache-layer, search-engine | MapTile, Geofence, POI, Route, TrafficLayer | — | MapLibre, OSM |
| `fleet` | Operations | drivers, vehicles, maintenance, analytics-events | Fleet, Vehicle, MaintenanceSchedule, Inspection | `vehicle.lifecycle` | Predictive maintenance |
| `deliveries` | Core | rides, drivers, scheduling, notifications, proof-of-delivery | Delivery, Package, Pickup, Dropoff, ProofOfDelivery | `delivery.lifecycle` | Contactless, age verify |
| `last-mile` | Optimization | deliveries, mapping, queue-jobs, analytics-events | RoutePlan, StopSequence, LoadOptimization, TimeWindow | `route.optimization` | VRP solver, reopt |
| `surge-pricing` | Revenue | rides, drivers, analytics-events, feature-flags | SurgeMultiplier, DemandSignal, SupplySignal, Zone | `surge.adjustment` | ML-based, rule-based |
| `background-checks` | Compliance | drivers, documents, webhooks, audit-log | BackgroundCheck, Provider, Status, AdverseAction | `check.lifecycle` | Fair Chance, continuous |
| `insurance-commercial` | Compliance | drivers, vehicles, wallet-ledger, documents | Policy, Coverage, Claim, Premium, Certificate | `claim.auto` | Commercial auto |

## 3. Marketplace & Commerce (12 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `listings` | Core | auth-rbac, database-pg, files-storage, search-engine, rich-text | Listing, Category, Attribute, Variant, Media, SEO | `listing.lifecycle` | Variants, bundles |
| `cart-checkout` | Core | listings, payments-core, subscriptions, inventory, tax-compliance | Cart, CartItem, Coupon, GiftCard, CheckoutSession | `checkout.flow` | Guest, split payment |
| `inventory` | Operations | listings, warehouse, purchase-orders, analytics-events | InventoryItem, StockLevel, Reservation, ReorderPoint | `stock.adjustment` | Multi-warehouse |
| `fulfillment` | Operations | inventory, shipping, warehouse, notifications | FulfillmentOrder, Shipment, Package, Label, Tracking | `fulfillment.lifecycle` | Multi-carrier, dropship |
| `vendors` | Core | auth-rbac, marketplace-payments, onboarding, compliance-kyc | Vendor, Storefront, Commission, Payout, Verification | `vendor.onboarding` | KYC, tiered commissions |
| `commissions` | Revenue | vendors, marketplace-payments, wallet-ledger, invoicing | CommissionRule, Split, PayoutSchedule, Hold | `payout.cycle` | Flexible rules, disputes |
| `reviews` | Trust | listings, orders, communications, moderation | Review, Rating, Response, Helpful, Report, Aggregate | `review.moderation` | Verified purchase |
| `returns` | Operations | orders, inventory, payments-core, shipping, wallet-ledger | ReturnRequest, Reason, Inspection, Refund, Exchange | `return.lifecycle` | Self-service, instant |
| `subscriptions-commerce` | Revenue | listings, subscriptions, payments-core, notifications | SubscriptionPlan, Subscriber, Cycle, Pause, Upgrade | `subscription.lifecycle` | Physical + digital |
| `affiliates` | Growth | vendors, tracking, payments-core, analytics-events | Affiliate, Link, Conversion, Commission, Tier, Payout | `affiliate.lifecycle` | Multi-level, cookie |
| `marketplace-seo` | Growth | listings, analytics-events, search-engine, ci-cd | Sitemap, StructuredData, Canonical, CoreWebVitals | — | Programmatic SEO |
| `multi-currency` | International | payments-core, tax-compliance, wallet-ledger, feature-flags | Currency, ExchangeRate, PriceList, Rounding, Display | `rate.refresh` | 150+ currencies |
| `data-tables` | TanStack Table + virtualization + grouping + column visibility + export | `DataTable`, `virtualizer`, `grouping`, `columnPicker`, `exporter` |
| `charts-dashboards` | Recharts + dashboard layouts + real-time updates + export + embedding | `Chart`, `Dashboard`, `realtimeSeries`, `exporter` |
| `rich-text` | Tiptap + collaborative editing + mentions + slash commands + export | `Editor`, `collaboration`, `mentions`, `slashCommands` |

## 8. Integration & Extensibility Packs (4)

| Pack | Purpose | Key Provides |
|------|---------|--------------|
| `api-gateway` | Kong/Traefik/Envoy + rate limiting + auth + transformation + analytics | `GatewayConfig`, `rateLimitPolicy`, `transformPlugin` |
| `integration-hub` | n8n/Temporal + connectors (Slack, Salesforce, HubSpot) + workflow builder | `Connector`, `workflowBuilder`, `executionEngine` |
| `plugin-system` | WASM plugins + sandbox + marketplace + versioning + permissions | `Plugin`, `wasmRuntime`, `pluginRegistry` |
| `mcp-gateway` | Model Context Protocol server + tool registry + auth + rate limits | `MCPServer`, `toolRegistry`, `authMiddleware` |

---

**Total Horizontal Packs: 45**

---

## 4. FinTech & Banking (14 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Compliance |
|------|----------|--------------|---------------------|----------------|------------|
| `accounts` | Core | auth-rbac, database-pg, wallet-ledger, encryption | Account, AccountHolder, Beneficiary, Signature, Limit | `account.lifecycle` | KYC, BSA |
| `ledger-core` | Core | wallet-ledger, audit-trail, data-archival, encryption | JournalEntry, Account, Period, Reconciliation | `period.close` | GAAP, SOX |
| `transfers` | Core | accounts, payments-core, compliance-aml, webhooks | Transfer, Wire, ACH, RTP, SEPA, FX, Counterparty | `transfer.lifecycle` | NACHA, FedNow |
| `cards` | Issuing | accounts, compliance-aml, webhooks, notifications | Card, Cardholder, Transaction, Authorization, Dispute | `card.lifecycle` | PCI-DSS, EMV |
| `lending` | Credit | accounts, ledger-core, credit-scoring, compliance-kyc | Loan, Application, Underwriting, Amortization | `loan.origination` | TILA, Reg Z |
| `credit-scoring` | Risk | accounts, analytics-events, ml-inference, data-archival | ScoreModel, Feature, Applicant, Decision, Monitor | `model.training` | FCRA, ECOA |
| `compliance-aml` | Compliance | transactions, audit-log, case-management, webhooks | Alert, Case, SAR, CTR, Watchlist, CustomerRisk | `alert.investigation` | BSA, OFAC |
| `compliance-kyc` | Compliance | accounts, documents, verification, webhooks | KYCProfile, Document, Verification, RiskRating | `kyc.review` | CIP, CDD |
| `treasury` | Operations | accounts, ledger-core, forecasting, analytics-events | CashPosition, Forecast, Investment, Sweep, Facility | `facility.compliance` | Basel III |
| `trade-finance` | Trade | accounts, documents, compliance-aml, letters-of-credit | LC, Guarantee, Collection, DocumentaryCredit | `lc.lifecycle` | UCP600 |
| `digital-assets` | Crypto | accounts, wallet-ledger, compliance-aml, custody | Wallet, Asset, Transaction, Staking, Yield, Custody | `asset.transfer` | Travel Rule |
| `open-banking` | Integration | accounts, api-gateway, consent-management, webhooks | Consent, DataAccess, PaymentInitiation, Aggregation | `consent.lifecycle` | PSD2, FDX |
| `regulatory-reporting` | Compliance | ledger-core, data-archival, audit-trail, ci-cd | Report, Schedule, Filing, Validation, Regulator | `report.generation` | Call Reports |
| `wealth-management` | Advisory | accounts, portfolio, compliance-kyc, reporting | Portfolio, Model, Rebalance, TaxLossHarvest, Goal | `rebalance.trigger` | Reg BI |
# VERTICAL PACKS — Domain-Specific (~85 Packs)

*Each vertical pack assumes relevant horizontal packs. They encode domain expertise: state machines, business rules, compliance, specialized UI.*

---

## HORIZONTAL PACKS — Universal Infrastructure (~45 Packs)

*Every application needs these. They compose cleanly with zero domain assumptions.*
## 5. Food Delivery & Hospitality (9 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `restaurants` | Core | auth-rbac, database-pg, files-storage, search-engine, menus | Restaurant, Cuisine, Hours, Location, Rating, Verification | `restaurant.onboarding` | Multi-location |
| `menus` | Core | restaurants, listings, inventory, rich-text, multi-currency | Menu, Category, Item, Modifier, Allergen, Nutrition | `menu.versioning` | Dayparts, seasonal |
| `orders` | Core | cart-checkout, restaurants, drivers, realtime-core, notifications | Order, LineItem, SpecialInstruction, Status, Timeline | `order.lifecycle` | Kitchen ticket, KDS |
| `kitchen` | Operations | orders, inventory, scheduling, analytics-events | KitchenDisplay, Station, Ticket, PrepTime, QualityCheck | `ticket.flow` | Bump screen, routing |
| `couriers` | Core | drivers, deliveries, mapping, wallet-ledger, gamification | Courier, Zone, Shift, Earnings, Rating, Incentive | `courier.shift` | Batch, priority |
| `delivery-tracking` | Customer | orders, couriers, realtime-core, mapping, notifications | LiveLocation, ETA, Route, Milestone, ProofOfDelivery | `tracking.updates` | Share link, SMS |
| `loyalty` | Growth | orders, wallet-ledger, notifications, feature-flags | LoyaltyProgram, Points, Tier, Reward, Referral | `points.earning` | Gamified, coalition |
| `catering` | B2B | restaurants, orders, scheduling, invoicing, crm | CateringOrder, Proposal, Contract, Deposit, Staffing | `catering.lifecycle` | Corporate, events |
| `ghost-kitchens` | Operations | restaurants, kitchen, inventory, analytics-events, multi-location | GhostKitchen, Brand, Capacity, Utilization, Economics | `brand.launch` | Virtual brands |

## 6. Real Estate & PropTech (8 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `properties` | Core | auth-rbac, database-pg, files-storage, search-engine, mapping | Property, Unit, Building, Amenity, Media, Valuation | `property.lifecycle` | MLS sync, IDX |
| `listings-re` | Core | properties, listings, rich-text, seo, virtual-tours | Listing, PriceHistory, Tour, Offer, Disclosure, HOA | `listing.re.lifecycle` | 3D tour, floorplan |
| `tours` | Operations | listings-re, scheduling, communications, calendar, notifications | Tour, Agent, TimeSlot, Feedback, CheckIn, VirtualLink | `tour.scheduling` | Self-guided, VR |
| `offers` | Transaction | listings-re, contracts, e-sign, escrow, compliance-kyc | Offer, Counter, Contingency, EarnestMoney, Deadline | `offer.negotiation` | Multi-offer |
| `contracts` | Legal | offers, e-sign, documents, audit-trail, compliance-re | Contract, Clause, Addendum, Signature, Recording | `contract.execution` | State-specific |
| `escrow` | Financial | contracts, payments-core, wallet-ledger, compliance-aml | EscrowAccount, Deposit, Disbursement, Instruction, Close | `escrow.hold` | RESPA, state law |
| `property-mgmt` | Operations | properties, maintenance, accounting, communications, portals | Lease, Tenant, MaintenanceRequest, Payment, Inspection | `lease.lifecycle` | Portal, auto-pay |
| `investment-analysis` | Analytics | properties, ledger-core, forecasting, reporting, tax-compliance | ProForma, CashFlow, IRR, CapRate, Sensitivity, Waterfall | `analysis.version` | Partnership |
## 7. Education & EdTech (9 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `courses` | Core | auth-rbac, database-pg, files-storage, rich-text, video-streaming | Course, Module, Lesson, Asset, Prerequisite, Certificate | `course.publishing` | Drip, cohort, self-paced |
| `enrollments` | Core | courses, users, payments-core, subscriptions, analytics-events | Enrollment, Progress, Grade, Completion, Certificate | `enrollment.status` | Waitlist, group |
| `assignments` | Academic | courses, submissions, grading, plagiarism, notifications | Assignment, Submission, Rubric, Feedback, PeerReview | `assignment.workflow` | Code, essay, quiz |
| `grading` | Academic | assignments, analytics-events, gradebook, notifications | Gradebook, Scheme, Curve, Export, History, Audit | `grade.calculation` | Standards-based |
| `certificates` | Credentials | enrollments, pdf-generation, blockchain, verification, sharing | Certificate, Credential, Verification, Revocation, Wallet | `credential.issuance` | W3C VC, PDF |
| `lms-admin` | Admin | courses, users, enrollments, analytics-events, rbac-extended | School, Department, Instructor, TA, Permission, Audit | — | Multi-tenant |
| `video-streaming` | Infra | courses, cdn, analytics-events, drm, accessibility | Stream, Transcoding, Caption, DRM, Analytics, Chat | `stream.quality` | Live, VOD, simulcast |
| `cohorts` | Social | enrollments, communications, scheduling, notifications, gamification | Cohort, Schedule, PeerGroup, Mentor, Milestone, Leaderboard | `cohort.timeline` | Peer learning |
| `compliance-education` | Compliance | enrollments, audit-trail, data-archival, reporting, privacy | FERPA, COPPA, StateAuth, Accreditation, Audit, Consent | `audit.education` | FERPA, COPPA |

## 8. SaaS & B2B Platforms (10 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `organizations` | Core | auth-rbac, database-pg, audit-log, multi-tenancy, invitations | Organization, Membership, Domain, Branding, Settings | `org.lifecycle` | SSO, SCIM |
| `teams` | Core | organizations, rbac-extended, communications, activity-feed | Team, Member, Role, Channel, Permission, Invite | `team.membership` | Nested, external |
| `seats` | Billing | organizations, subscriptions, usage-metering, invoicing | Seat, Assignment, Utilization, TrueUp, Reassignment | `seat.assignment` | Floating, named |
| `entitlements` | Access | seats, feature-flags, api-gateway, audit-trail | Entitlement, Grant, Revocation, Expiration, Override | `entitlement.check` | Per-feature, per-seat |
| `sso-saml` | Auth | organizations, auth-rbac, compliance-soc2, audit-log | SAMLConfig, IdP, AttributeMapping, JITProvision, Metadata | `sso.connection` | SAML 2.0, OIDC |
| `sso-oidc` | Auth | organizations, auth-rbac, compliance-soc2, audit-log | OIDCConfig, Client, Scope, PKCE, TokenExchange | `oidc.flow` | OIDC, FAPI |
| `usage-metering` | Billing | entitlements, analytics-events, billing-metering, invoicing | Meter, Event, Aggregation, Rating, Quota, Alert | `meter.aggregation` | Real-time, batch |
| `api-management` | Platform | api-gateway, entitlements, analytics-events, developer-portal | APIProduct, Plan, Key, RateLimit, Analytics, Docs | `api.versioning` | Monetization |
| `marketplace-saas` | Growth | vendors, listings, subscriptions-commerce, provisioning | SaaSListing, Provisioning, SSO, Billing, Lifecycle | `saas.provisioning` | AppExchange style |
| `white-label` | Platform | organizations, design-system, ci-cd, multi-tenancy, dns | Brand, Domain, Certificate, Customization, Rollout | `whitelabel.deploy` | CNAME, certs |
## 9. Logistics & Supply Chain (10 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `shipments` | Core | auth-rbac, database-pg, tracking, documents, customs | Shipment, Leg, Container, BillOfLading, Manifest, Status | `shipment.lifecycle` | Multi-modal |
| `warehouses` | Core | inventory, slotting, labor, analytics-events, iot | Warehouse, Zone, Location, SlottingRule, LaborStandard | `warehouse.operations` | WMS, automation |
| `inventory-wms` | Operations | warehouses, inventory, rfid, barcode, voice-picking | InventoryLocation, CycleCount, Replenishment, PickPath | `inventory.movement` | Directed putaway |
| `transportation` | Core | shipments, fleet, mapping, rate-engine, compliance-dot | Load, Carrier, Rate, Tender, Appointment, POD | `load.tender` | TMS, brokerage |
| `customs` | Compliance | shipments, documents, trade-finance, regulatory-reporting, hs-codes | Entry, Classification, Duty, Bond, Exam, Release | `customs.clearance` | ACE, AES |
| `freight-forwarding` | Operations | shipments, transportation, customs, warehouse, documents | ForwardingOrder, Quote, Booking, Docs, Milestone, Invoice | `forwarding.job` | NVOCC, FMC |
| `last-mile-logistics` | Operations | deliveries, mapping, routing, proof-of-delivery, customer-portal | Route, Stop, POD, Exception, Returns, CustomerPref | `route.execution` | Dynamic, crowdsourced |
| `supply-chain-visibility` | Analytics | shipments, iot, analytics-events, alerting, blockchain | Event, Sensor, Location, Condition, ETA, RiskScore | `visibility.monitoring` | Control tower |
| `procurement` | Operations | vendors, purchase-orders, contracts, approvals, spend-analysis | Requisition, PO, Receipt, Invoice, ThreeWayMatch, Spend | `procurement.cycle` | P2P, catalog |
| `fleet-management` | Assets | vehicles, maintenance, telematics, compliance-dot, fuel-cards | Asset, Maintenance, Inspection, Fuel, Utilization, TCO | `asset.lifecycle` | EV, mixed fleet |

## 10. Professional Services & Agencies (8 Packs)

| Pack | Category | Dependencies | Key Domain Entities | State Machines | Key Features |
|------|----------|--------------|---------------------|----------------|--------------|
| `projects` | Core | auth-rbac, database-pg, tasks, time-tracking, budgeting | Project, Phase, Milestone, Deliverable, Budget, Scope | `project.lifecycle` | Waterfall, agile |
| `time-tracking` | Operations | projects, users, invoicing, approvals, analytics-events | TimeEntry, Timer, Approval, Rate, Utilization, Report | `time.approval` | Mobile, desktop |
| `invoicing-ps` | Revenue | projects, time-tracking, expenses, payments-core, retainer | Invoice, LineItem, Retainer, WIP, WriteOff, Collection | `invoice.ps` | Progress, milestone |
| `retainers` | Billing | clients, invoicing-ps, usage-metering, notifications, wallet-ledger | Retainer, Balance, Drawdown, Replenishment, Rollover, Alert | `retainer.balance` | Evergreen, scoped |
| `resource-planning` | Operations | projects, people, skills, scheduling, forecasting | Allocation, Demand, Capacity, Skill, Conflict, Bench | `allocation.optimization` | Gantt, heatmap |
| `client-portal` | Client | projects, communications, documents, approvals, billing | Portal, Access, Notification, Feedback, Report, Payment | `portal.engagement` | White-label |
| `proposals` | Sales | clients, projects, pricing, e-sign, crm-integration | Proposal, Template, Version, Approval, Acceptance, SOW | `proposal.workflow` | CPQ, redline |
| `compliance-ps` | Compliance | projects, audit-trail, data-archival, privacy, insurance | EngagementLetter, Independence, ConflictCheck, PeerReview, Insurance | `compliance.check` | AICPA, PCAOB |

---

**Total Vertical Packs: ~90**
# COMPOSITION RULES — How Packs Combine

## 1. Dependency Resolution
```python
def resolve_pack_graph(selected_packs: list[str]) -> list[str]:
    """Topological sort with conflict detection."""
    graph = build_dependency_graph(selected_packs)
    if has_cycles(graph):
        raise PackConflictError("Circular dependency detected")
    return topological_sort(graph)
```

## 2. Entity Merge Strategy
| Conflict Type | Resolution |
|---------------|------------|
| Same entity name, compatible fields | **Merge** — union of fields, union of indexes |
| Same entity name, conflicting fields | **Prefix** — `packA_Field`, `packB_Field` + unified view |
| Same entity, different state machines | **Compose** — combined SM with namespaced states |
| Duplicate API endpoint | **Error** — must be resolved by pack author |

## 3. Required Horizontal Packs per Vertical Category

| Vertical Category | Mandatory Horizontal Packs |
|-------------------|---------------------------|
| Healthcare | auth-rbac, database-pg, audit-log, encryption, compliance-hipaa, realtime-core |
| Mobility | auth-rbac, database-pg, realtime-core, scheduling, payments-core, mapping |
| Marketplace | auth-rbac, database-pg, payments-core, marketplace-payments, search-engine, files-storage |
| FinTech | auth-rbac, database-pg, wallet-ledger, encryption, compliance-aml, compliance-kyc, audit-trail |
| Food Delivery | auth-rbac, database-pg, realtime-core, scheduling, payments-core, mapping |
| Real Estate | auth-rbac, database-pg, files-storage, search-engine, mapping, e-sign |
| Education | auth-rbac, database-pg, files-storage, video-streaming, rich-text, compliance-education |
| SaaS/B2B | auth-rbac, database-pg, organizations, rbac-extended, subscriptions, feature-flags |
| Logistics | auth-rbac, database-pg, tracking, mapping, documents, compliance-dot |
| Professional Services | auth-rbac, database-pg, time-tracking, invoicing-ps, projects, rbac-extended |

## 4. Role-to-Pack Mapping (Auto-Generates Role-Specific Apps)

| Role | Auto-Included Vertical Packs | Generated Apps |
|------|------------------------------|----------------|
| `customer` | listings, cart-checkout, orders, reviews, loyalty | Customer Web, Customer Mobile |
| `driver/courier` | drivers/couriers, deliveries/rides, dispatch, wallet-ledger | Driver Mobile |
| `merchant/vendor` | vendors, listings, inventory, commissions, analytics | Merchant Web, Merchant Mobile |
| `admin/operator` | all domain packs + admin-crud, audit-trail, analytics | Admin Web |
| `provider/clinician` | providers, appointments, emr, prescriptions, telehealth | Provider Web, Provider Mobile |
| `agent/broker` | listings-re, tours, offers, contracts, escrow, crm | Agent Web, Agent Mobile |

---

# PACK VERSIONING & UPGRADES

```json
{
  "name": "appointments",
  "version": "2.1.0",
  "upgradePath": {
    "from": "1.x",
    "migrations": ["2.0.0:split_recurring_rules", "2.1.0:add_waitlist_priority"],
    "breakingChanges": ["Slot model renamed to TimeSlot"]
  }
}
```

- **SemVer** strictly enforced
- **Migration scripts** generated for breaking changes
- **Compatibility matrix** published per release
- **Deprecation window**: 2 minor versions

---

# REGISTRY OPERATIONS

| Operation | CLI Command | API |
|-----------|-------------|-----|
| List packs | `omnistack pack list --type=vertical --category=healthcare` | `GET /packs` |
| Inspect pack | `omnistack pack inspect appointments@2.1.0` | `GET /packs/appointments/2.1.0` |
| Install pack | `omnistack pack add appointments@latest` | `POST /projects/{id}/packs` |
| Upgrade pack | `omnistack pack upgrade appointments@2.1.0` | `PATCH /projects/{id}/packs/appointments` |
| Publish pack | `omnistack pack publish ./my-pack --registry=private` | `POST /registry/packs` |
| Validate composition | `omnistack pack validate --packs=appointments,patients,providers` | `POST /packs/validate` |

---

# SUMMARY: PACK COUNTS

| Layer | Count | Purpose |
|-------|-------|---------|
| **Horizontal** | **45** | Universal infrastructure every app needs |
| **Vertical** | **~90** | Domain-specific business logic across 10 industries |
| **Total** | **~135** | Composable building blocks for any platform |

Each vertical pack declares its horizontal dependencies. The composer resolves the full graph, merges IRs, and generates a coherent monorepo with zero conflicts.
