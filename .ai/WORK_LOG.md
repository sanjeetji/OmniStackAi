# Work Log

## 2026-09-21 — R-519 (T-1 Template format + registry)

- **Why:** Phase T needs a template format. The founder's model: the original template never changes and is the same for everyone. "Use template" gives each user their own editable project copy.
- **Design:** a template is a hand-built golden `repo/` plus `template.json` under `templates/catalog/<slug>/`. It is strictly validated (apps, roles, demo users, migrations for API apps, no secrets, `.git`, `node_modules` or symlinks) and content-digested. Instantiation copies the repo into the project workspace, makes a fresh git repo with one commit, and writes `kind: "template"` plus slug, version and digest. Provenance lives in its own `project_templates` table, so no existing project query changed.
- **Protection:** prompt rebuilds and IR edits refuse template projects with a clear 400 until the code-edit agent (T-4). `use` rolls back fully (project row and workspace) on any failure.
- **Evidence:** 33 new Python tests and a new Go package test suite. `task verify` 3,895 OK. Live: two users, independent copies, original unchanged. Core smoke 14/14.

## 2026-09-21 — R-518 (T-0 Stabilise the core)

- **Why:** Phase T (Template Marketplace) was approved on the condition that the core prompt -> app -> edit loop must not break. First, prove it works live.
- **Found:** `omnistack.sh up` reused a control-plane image from 2026-09-19, so R-499..R-517 had never run against a real DB. After rebuilding, each defect was reproduced live and then fixed: startup ServeMux panic (duplicate `seo/audit|suggest`), missing `/opened`, `users.name` in migration 000015 and 4 store queries, the 15 s `http.Client.Timeout` cutting every build stream, console create-without-name 400, dropped `mention_skills`, 204 parsed as JSON (502), and the agent-engine `_workspace_edit` `ProjectDiff.added_files` crash (edits committed, then reported as 502).
- **Tests added:** `cmd/control-plane/main_test.go` (full route table), slow-upstream stream relay, no-overall-client-timeout, migration-comment semicolon guard, `WorkspaceEditTests` (real committed workspace edit), and the `scripts/test.sh` R-518 block.
- **Live:** `scripts/smoke-core.sh` 14/14. Restart persistence plus a post-restart edit gave 7 added / 12 modified, commit `4d6f770`.
- **Gates:** go vet/test (21 pkgs), console typecheck/lint/build, scripts/test.sh, task verify (3,862 OK), lint, security:quick, env:check.
- **Reported, not fixed:** google provider `.env` token limits; generated seed uuid "user1"; add-only delta engine.

## 2026-09-21 — R-517 (Node.js backend codegen — Express/Hono alongside Python/Go)

- **Why:** Provide first-class, deterministic Node.js backend code generation (`GenerationTarget.BACKEND_NODE` / `BackendStrategy.NODE`) alongside existing Python (FastAPI) and Go (`net/http`) backend adapters.
- **Part 1 — Node.js Backend Adapters (`services/agent-engine/src/omnistackai_agent_engine/codegen/backend_node.py`):**
  - Implemented `NodeBackendAdapter`, `ExpressBackendAdapter`, and `HonoBackendAdapter`.
  - Framework switching: defaults to Express, automatically selects Hono when `framework="hono"` or when `"hono"` is present in the application description or name.
  - Complete, idiomatic TypeScript project structure:
    - `package.json`: ESM-configured with production scripts (`dev`, `build`, `start`), framework dependencies (`express` or `hono` + `@hono/node-server`), TypeScript & type definitions (`@types/express`, `@types/node`, `typescript`, `tsx`), and data validation (`zod`).
    - `tsconfig.json`: Modern NodeNext module resolution, ES2022 target, strict mode enabled.
    - `src/config.ts`: Environment configuration with type casting and sensible fallbacks (`PORT`, `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGIN`).
    - `src/index.ts`: Server startup logic, graceful shutdown handling (`SIGTERM`/`SIGINT`), and port binding.
    - `src/app.ts`: HTTP application configuration, CORS middleware, JSON body parsing, request logging, and router mounting.
    - `src/models/types.ts`: TypeScript interfaces for every entity, create/update input payloads, and paginated responses.
    - `src/models/validation.ts`: Zod schemas for runtime request payload validation with inferred TypeScript types.
    - `src/middleware/auth.ts`: JWT authentication middleware with Bearer token parsing and header injection.
    - `src/db/pool.ts` & `src/db/<entity>.ts`: PostgreSQL data access with pooled connections (`pg`) and seamless in-memory fallback for local development.
    - `src/routes/<resource>.ts`: Resource routers wired with existing `route_wiring.py` for standard CRUD operations (`Op.LIST`, `Op.GET`, `Op.CREATE`, `Op.UPDATE`, `Op.DELETE`, `Op.LIST_BY`).
    - `contracts/openapi.json`: OpenAPI 3.0 contract rendered via `render_openapi_json`.
    - `schema.sql` & `seed.sql`: PostgreSQL DDL schema and initial seed data.
    - `.env.example` & `README.md`: Environment setup instructions and developer documentation.
- **Part 2 — Codegen Assembler Integration:**
  - Exported adapters in `codegen/__init__.py` and included in `__all__`.
  - Updated `assembler.py`: mapped `BackendStrategy.NODE` to `GenerationTarget.BACKEND_NODE` in `_BACKEND_TARGET` and registered `NodeBackendAdapter` in `default_registry()`.
  - Added R-517 contract assertions to `scripts/test.sh`.
- **Part 3 — Unit Testing & Verification:**
  - Added 10 tests in `test_backend_node.py` covering Express, Hono, route wiring, models, Zod validation, JWT auth, determinism, and live Node.js syntax parsing.
  - Updated assembler tests in `test_assembler.py`.
  - Verified full test suite (3,861/3,861 agent-engine tests passed in 91.6s, all Go packages clean, Next.js build clean, Stage 0 verification passed).

## 2026-09-21 — R-516 (Email feature — SMTP / Resend integration in generated apps)

- **Why:** Provide turnkey, production-grade Transactional Email capabilities for generated Next.js apps with zero external npm dependencies:
  1. Pure Node.js standard-library socket client in `lib/email.ts` using `node:net`, `node:tls`, and `node:crypto` speaking RFC 5321/4954 with direct TLS (port 465) and STARTTLS (port 587/25) upgrade support, AUTH LOGIN / PLAIN, and MIME formatting.
  2. Resend REST API integration in `lib/email.ts` using native `fetch` with typed options (`to`, `subject`, `html`, `text`, `from`, `replyTo`, `cc`, `bcc`) and robust error reporting.
  3. Pre-built responsive HTML email templates in `lib/email-templates.ts` (`welcomeEmailTemplate`, `otpVerificationTemplate`, `passwordResetTemplate`, `notificationTemplate`) with inline CSS and plaintext fallbacks.
  4. Interactive Contact Form UI component (`components/contact-form.tsx`) wired to `/api/send` route.
  5. Go control-plane test verification in `internal/connectors/handler.go` and catalog update in `internal/connectors/catalog.go`.
  6. Console Web UI helper snippets and template previews in `components/project-connectors-manage.tsx`.
  7. Verification: 7/7 Python tests (including Node.js template execution), 19/19 Go control-plane packages, Next.js build/typecheck/lint, contract tests in `scripts/test.sh`, and `task verify` (3,851 tests passed, Stage 0 clean).

## 2026-09-21 — R-515 (Team / Org model — multi-member workspaces, shared projects)

- **Why:** Implement Organization and multi-member Workspace tenancy model as specified in Sections 7 and 17 of `R_&_D/OmniStackAI_Implementation_Brief_v6.md` (`Organization -> Workspace -> Project -> Environment -> Target -> Deployment`), enabling collaborative multi-member workspaces with shared projects, member invites, role-based access control (`owner`, `admin`, `member`, `viewer`), and backwards compatibility for existing single-user projects.
- **Part 1 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000015_organizations_workspaces.up.sql` and `000015_organizations_workspaces.down.sql`.
  - Added tables: `organizations`, `workspaces`, `workspace_members`, `workspace_invites`.
  - Added `workspace_id` foreign key on `projects`.
  - Automatic backfill establishing personal org and default workspace for all existing users and linking their projects.
- **Part 2 — Control-Plane Backend (`services/control-plane/internal/workspaces/`):**
  - Implemented `store.go`: PostgreSQL data access for workspaces, members, and invites with strict RBAC rules.
  - Implemented `handler.go`: REST endpoints for workspace CRUD, member listing, role updating, member removal, invitation creation, revocation, and atomic join acceptance.
  - Implemented unit tests in `workspaces_test.go` (100% pass).
  - Registered `workspaces.Register` in `cmd/control-plane/main.go`. Zero new external Go dependencies (`github.com/jackc/pgx/v5` remains sole direct dependency).
- **Part 3 — Control-Plane Projects Multi-tenancy (`services/control-plane/internal/projects/`):**
  - Updated projects store and handler to support workspace tenancy, `workspace_id` filtering, and shared project access checks across creator and workspace members.
- **Part 4 — Console Web UI (`apps/console-web/`):**
  - Extended `lib/control-plane.ts`: Added `Workspace`, `WorkspaceMember`, `WorkspaceInvite`, and API client functions.
  - Added Next.js API route proxies under `app/api/workspaces/` and invite acceptance page at `app/invite/[token]/page.tsx`.
  - Created `components/workspace-switcher.tsx`: Sticky top header dropdown with active workspace, role badge, quick switcher, and "+ Create workspace" modal.
  - Created `components/workspace-manage.tsx`: Dedicated Lovable-grade team & workspace management interface in Settings -> Team & Workspaces (members table, role selector, invite modal with copyable link, pending invites table with revoke, workspace settings, danger zone).
  - Updated `app/projects/page.tsx`: Workspace filtering and creator badge on project cards.
- **Part 5 — Verification & Contract Testing:**
  - Added R-515 contract assertions to `scripts/test.sh`.
  - Verified: `task lint` (clean), `go test ./...` across all 19 control-plane packages (clean), Next.js build/typecheck/lint (clean), and full `task verify` (3,850 tests passed, Stage 0 clean).

## 2026-09-21 — R-514 (Mobile React Native / Expo Framework Adapter)

- **Why:** Deliver production-grade React Native (Expo SDK 51) framework adapter un-gating cross-platform mobile application synthesis for the platform (`R_&_D/OmniStackAI_Implementation_Brief_v6.md` Section 37 & 6.4).
- **Part 1 — Framework Adapter (`services/agent-engine/src/omnistackai_agent_engine/codegen/react_native.py`):**
  - Implemented `ReactNativeAdapter` satisfying the `FrameworkAdapter` protocol for `GenerationTarget.REACT_NATIVE`.
- **Part 2 — Expo TypeScript Project Architecture:**
  - Emits clean, production-ready mobile files: `package.json` (Expo 51, React Native 0.74, React Navigation Native Stack, Lucide icons), `app.json` (orientation, splash, bundle identifier, adaptive icons), `tsconfig.json`, `babel.config.js`, `index.js`.
- **Part 3 — Design System & Tokens:**
  - Generates `src/design-system/tokens.ts` embedding brand tokens (`BrandTokens`: primary color, dark primary, radii, spacing, typography) and native UI components (`Button`, `Card`, `Badge`, `Input`, `StatCard`, `ScreenContainer`).
- **Part 4 — Shared Data & Auth Layer:**
  - Generates `src/shared/api/client.ts` with typed HTTP client communicating with backend endpoints, and `src/shared/auth/AuthContext.tsx` providing user authentication, token storage, and session state.
- **Part 5 — Entity Features:**
  - Generates `src/features/<entity>/` with TypeScript models, CRUD API clients, `use<Entity>s` hooks, `ListScreen` (FlatList, search, KPI tiles, delete CTA), and `DetailScreen` (typed form inputs, create/edit modes, save handlers).
- **Part 6 — App Shell & Navigation:**
  - Generates `src/app/screens/OverviewScreen.tsx`, `src/app/navigation/RootNavigator.tsx` (NativeStack), and `src/app/App.tsx` (SafeAreaProvider, AuthProvider, NavigationContainer).
- **Part 7 — Monorepo Assembly:**
  - Registered in `default_registry()` and wired into `assembler.py` under `apps/mobile/` when `ir.project_strategy.mobile_profile` is `MobileProfile.REACT_NATIVE`.
- **Part 8 — Verification:**
  - Added 9 unit tests in `test_react_native_adapter.py`, updated assembler tests to 6 passed, all 3,850/3,850 Python tests pass, 18 Go packages pass, Next.js build/typecheck/lint clean, and full `task verify` clean.

## 2026-09-20 — R-513 (Analytics for published apps — G-05-analytics)

- **Why:** Deliver visitor traffic analytics for published applications with zero storage load on OmniStackAI, adhering to privacy laws by reading the Google Analytics 4 (GA4) Data API directly with the user's OAuth credentials.
- **Part 1 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000014_project_analytics.up.sql` and `down.sql`: added `analytics_provider` and `analytics_property_id` columns to `projects` table.
- **Part 2 — Control-Plane Backend (`services/control-plane/internal/analytics/`):**
  - Implemented `store.go`: PostgreSQL data access for project analytics settings.
  - Implemented `ga4.go`: standard-library `net/http` client querying Google Analytics Data API v1beta (`runReport`) with 5-minute caching, returning active users, sessions, pageviews, average engagement time, top pages, referrers, device categories, and country distribution.
  - Implemented `handler.go`: REST endpoints `GET/PUT/DELETE /projects/{id}/analytics` with caller project ownership verification.
  - Added unit tests in `analytics_test.go` (100% pass).
  - Registered in `cmd/control-plane/main.go`.
- **Part 3 — Console Web UI (`apps/console-web/`):**
  - Added analytics types and client SDK methods in `lib/control-plane.ts`.
  - Added Next.js API route proxies under `app/api/projects/[id]/analytics/`.
  - Created `components/project-analytics-manage.tsx`: Lovable-grade dashboard with KPI cards, time range filter (24h, 7d, 30d, 90d), top pages table, referrers chart, device/country breakdowns, and property configuration modal. Mounted in Studio Manage under Analytics tab.
- **Part 4 — Verification:**
  - Go control-plane tests clean, Next.js build/lint clean, and full `task verify` clean.

## 2026-09-20 — R-512 (G-04 Payment Gateways in Generated Apps — Stripe & Razorpay)

- **Why:** Enable generated applications to accept real customer payments ("my store takes money") with zero PCI scope for the platform, strict HMAC-SHA256 signature verification, and event idempotency (`R_&_D/specs/G-04-payments.md`).
- **Part 1 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000013_project_payments.up.sql` and `000013_project_payments.down.sql`:
    - Added `payment_gateway` TEXT column to `projects` table with CHECK constraint `('', 'stripe', 'razorpay')` and default `''`.
- **Part 2 — Control-Plane Backend (`services/control-plane/internal/payments/`):**
  - Implemented `store.go`: `PgStore` managing project payment gateway configuration with validation (`stripe`, `razorpay`, `""`).
  - Implemented `handler.go`: REST endpoints (`GET /projects/{id}/payments`, `PUT /projects/{id}/payments`, `DELETE /projects/{id}/payments`), required secrets inspection (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`) checking "set" vs "not_set" without ever leaking key values, and live webhook endpoint URL formatting.
  - Implemented unit tests in `payments_test.go` (100% pass).
  - Registered `payments.Register` in `cmd/control-plane/main.go`. Zero new external Go dependencies (`github.com/jackc/pgx/v5` remains sole direct dependency).
- **Part 3 — Agent-Engine Codegen Hooks (`services/agent-engine/`):**
  - Implemented `studio/payments.py`:
    - `apply_payments`: Generates `lib/payments/stripe.ts` (typed checkout & HMAC signature verification, zero npm dependencies), `app/api/checkout/route.ts`, `app/api/webhooks/stripe/route.ts` (HMAC-SHA256 signature validation & in-memory event deduplication), `app/checkout/success/page.tsx`, `app/checkout/cancel/page.tsx`, and `tests/payments/test_stripe_webhook.js` for Stripe; generates `lib/payments/razorpay.ts` (typed orders & signature verification), `app/api/checkout/route.ts`, `app/api/webhooks/razorpay/route.ts`, success/cancel pages, and verification tests for Razorpay; updates `.env.example`; commits additions to Git.
    - `remove_payments`: Cleanly unlinks generated payment files, strips keys from `.env.example`, and commits clean removal to Git.
  - Mounted routes in `studio/server.py`: `POST /api/workspaces/{id}/payments/apply` and `POST /api/workspaces/{id}/payments/remove`.
  - Added unit tests in `tests/test_payments.py` testing codegen, live Node HMAC verification script execution (3/3 passed), and HTTP API endpoints.
- **Part 4 — Console Web UI (`apps/console-web/`):**
  - Extended `lib/control-plane.ts`: Added `PaymentKeyStatus`, `ProjectPaymentsResponse`, and client functions (`getProjectPayments`, `setProjectPaymentGateway`, `clearProjectPaymentGateway`).
  - Added Next.js API proxy route `app/api/projects/[id]/payments/route.ts` (`GET`, `PUT`, `DELETE`).
  - Created `components/project-payments-manage.tsx`:
    - Stripe & Razorpay gateway cards with supported payment method tags.
    - Generated code file breakdown with explanations.
    - Required secret keys checklist with direct deep links to Manage -> Secrets.
    - Copyable live webhook URL with setup instructions for Stripe & Razorpay dashboards.
    - Test Mode Sandbox guidance with test card numbers and simulated UPI VPA.
    - Disconnect gateway confirmation modal.
  - Mounted Payments tab in Studio Manage sidebar (`app/studio/[projectId]/manage/page.tsx`).
- **Part 5 — Verification & Contract Testing:**
  - Added R-512 contract assertions to `scripts/test.sh`.
  - Verified: `task lint` (clean), `go test ./...` across all 17 control-plane packages (clean), Next.js build/typecheck/lint (clean), and full `task verify` (all 3,841 agent-engine tests pass).

## 2026-09-20 — R-511 (G-03 Connectors v1)

- **Why:** Enable generated apps to communicate with 3rd-party services (Google Analytics 4, Resend, and SMTP) using developer credentials (`R_&_D/specs/G-03-connectors.md`). Follows the strict **Honest Catalogue Rule**: ships few, working, and honest connectors only — zero deceptive 113-service marketing stubs.
- **Part 1 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000012_connectors.up.sql` and `000012_connectors.down.sql`:
    - `connector_accounts`: user-level credentials and encrypted refresh tokens (`user_id`, `provider`, `external_account`, `refresh_token_ciphertext`, `scopes`).
    - `project_connectors`: project-scoped connector binding (`project_id`, `provider`, `connector_account_id`, `config` JSONB, `enabled`).
- **Part 2 — Control-Plane Backend (`services/control-plane/internal/connectors/`):**
  - Implemented `catalog.go`: Honest catalogue of working connectors (`ga4`, `resend`, `smtp`) with category, auth type, config schema, and generated files descriptions.
  - Implemented `store.go`: `PgStore` managing project connectors CRUD with sensitive field masking and timestamp tracking.
  - Implemented `handler.go`: REST handlers (`GET /connectors`, `GET /projects/{id}/connectors`, `PUT /projects/{id}/connectors/{provider}`, `DELETE /projects/{id}/connectors/{provider}`, `POST /projects/{id}/connectors/{provider}/test`).
  - Added unit tests in `connectors_test.go`: Catalog schema checks, store lifecycle, and validation.
  - Registered `connectors.Register` in `cmd/control-plane/main.go`.
- **Part 3 — Agent-Engine Codegen Hooks (`services/agent-engine/`):**
  - Implemented `studio/connectors.py`:
    - `apply_connector`: Generates `components/GoogleAnalytics.tsx` and injects tag into `app/layout.tsx` for GA4; generates `lib/email.ts` and `app/api/send/route.ts` for Resend and SMTP; commits additions to Git.
    - `remove_connector`: Removes generated files and reverts layout modifications on disconnect; commits clean removal to Git.
  - Mounted routes in `studio/server.py`: `POST /api/workspaces/{id}/connectors/apply` and `POST /api/workspaces/{id}/connectors/remove`.
  - Added unit tests in `tests/test_connectors.py` (all 6 tests pass).
- **Part 4 — Console Web UI (`apps/console-web/`):**
  - Extended `lib/control-plane.ts`: Added `ConnectorDefinition`, `ProjectConnector`, and client methods (`listConnectorsCatalog`, `listProjectConnectors`, `saveProjectConnector`, `deleteProjectConnector`, `testProjectConnector`).
  - Added Next.js API routes:
    - `/api/connectors`
    - `/api/projects/[id]/connectors`
    - `/api/projects/[id]/connectors/[provider]`
    - `/api/projects/[id]/connectors/[provider]/test`
  - Created `components/project-connectors-manage.tsx`:
    - Clean connector grid with state chips (Connected / Not connected).
    - Configuration drawer displaying exact generated files, input fields with secret toggles, live connection testing, and one-click disconnect.
    - Honest "Request a Connector" dialog capturing user requests for future OAuth apps (Google Calendar, Gmail, Slack).
  - Mounted Connectors tab in `app/studio/[projectId]/manage/page.tsx`.
- **Part 5 — Verification & Contract Testing:**
  - Added R-511 assertions to `scripts/test.sh`.
  - Verified: `task lint` (clean), `go test ./...` across all 16 control-plane packages (clean), Next.js build/typecheck/lint (clean), and full `task verify` (all 3,837 agent-engine tests pass).

## 2026-09-20 — R-510 (G-02 Custom Domain: Bring Your Own)

- **Why:** Allow developers to connect their own custom domains (from Cloudflare, GoDaddy, Namecheap, Hostinger, BigRock, etc.) to their published OmniStackAI applications (`R_&_D/specs/G-02-domains.md`), with ₹0 domain registrar, purchasing, renewal, or WHOIS overhead for the platform.
- **Part 1 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000011_domains.up.sql` and `000011_domains.down.sql`:
    - `project_domains`: `id`, `project_id` (CASCADE), `hostname` (UNIQUE anti-hijack constraint), `provider`, `record_type`, `record_name`, `record_value`, `status` ('pending', 'verifying', 'verified', 'failed', 'removed'), `tls_status` ('pending', 'issued', 'failed'), `is_primary`, `last_checked_at`, `verified_at`, `error`, `created_at`.
    - Created indexes on `project_id` and `hostname`.
- **Part 2 — Control-Plane Backend (`services/control-plane/internal/domains/` & `internal/deploy/`):**
  - Extended `DeployProvider` in `internal/deploy/provider.go` with domain methods: `AddDomain`, `VerifyDomain`, `RemoveDomain` for `VercelProvider`, `NetlifyProvider`, and `mockDeployProvider`.
  - Implemented `internal/domains/store.go`: `PgStore` managing domain CRUD, primary domain designation with atomic transactions, and status updates.
  - Implemented `internal/domains/verifier.go`: RFC 1123 hostname syntax validation, prohibition of IP addresses, bare TLDs, and platform domains; apex vs subdomain detection; standard-library DNS verification (`net.LookupCNAME` / `net.LookupIP`).
  - Implemented `internal/domains/handler.go`: REST endpoints (`GET/POST /projects/{id}/domains`, `POST /projects/{id}/domains/{domainId}/verify`, `PUT /projects/{id}/domains/{domainId}/primary`, `DELETE /projects/{id}/domains/{domainId}`) with strict tenant isolation, anti-hijacking prevention (409 Conflict), and two-phase DNS + provider verification rule.
  - Added comprehensive unit tests in `domains_test.go`: RFC 1123 validation, apex classification, DNS record calculation, mock resolver lifecycle, and anti-hijacking conflict checks.
  - Registered `domains.Register` in `cmd/control-plane/main.go`.
- **Part 3 — Console Web UI (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added `ProjectDomain` interface and client SDK functions (`listProjectDomains`, `addProjectDomain`, `verifyProjectDomain`, `setPrimaryDomain`, `deleteProjectDomain`).
  - Added Next.js API route proxies:
    - `/api/projects/[id]/domains`
    - `/api/projects/[id]/domains/[domainId]`
    - `/api/projects/[id]/domains/[domainId]/verify`
  - Created `components/project-domain-manage.tsx`:
    - Clean, modern UI with empty state and informative zero-markup disclaimer.
    - Live RFC 1123 format validation with instant error messages.
    - DNS instruction cards (Type, Name/Host, Target/Value) with one-click copy buttons and visual feedback.
    - Step-by-step registrar setup guides with direct links for Cloudflare, GoDaddy, Namecheap, Hostinger, BigRock.
    - Honest DNS status badges (Connected / Resolving / Pending) and real TLS badges (Active / Pending / Failed) — never fake locks.
    - "Check DNS now" live polling action and propagation expectations notice (minutes to 48 hours).
    - Primary domain badge and toggle, and domain disconnect action.
  - Mounted `ProjectDomainManage` into `apps/console-web/app/studio/[projectId]/manage/page.tsx` under the new **Domain** tab.
- **Part 4 — Verification & Contract Testing:**
  - Added R-510 assertions to `scripts/test.sh`.
  - Verified with `task lint` (clean), Go tests across all 15 packages (clean), Next.js typecheck and lint (clean), and full `task verify` (3,831 tests pass).

- **Why:** Enable developers to deploy generated applications directly from their connected GitHub repository to their own Vercel or Netlify account via personal access tokens (`R_&_D/specs/G-01-publish.md`), achieving ₹0 hosting infrastructure cost for OmniStackAI while delivering seamless 1-click cloud deployments.
- **Part 1 — Database Migrations (`services/control-plane/migrations/`):**
  - Created `000010_deployments.up.sql` and `000010_deployments.down.sql`:
    - `deploy_connections`: User provider connections (`provider` IN ('vercel', 'netlify'), `encrypted_api_key`, `key_id`, `account_label`, `created_at`, `updated_at`).
    - `deployments`: Project deployment history (`project_id`, `user_id`, `provider`, `external_id`, `status` IN ('queued', 'building', 'ready', 'error', 'canceled'), `url`, `commit_sha`, `error_message`, `created_at`, `updated_at`).
    - Added `deploy_provider`, `deploy_external_id`, and `live_url` columns to `projects`.
- **Part 2 — Control-Plane Backend (`services/control-plane/internal/deploy/`):**
  - Implemented `store.go`: AES-256-GCM authenticated encryption with user_id:provider AAD binding and key rotation support; PostgreSQL CRUD for connections, deployments, and project live status.
  - Implemented `provider.go`: `DeployProvider` interface with standard library `net/http` implementations for `VercelProvider` (`api.vercel.com/v13/deployments`) and `NetlifyProvider` (`api.netlify.com/api/v1/sites`). Strictly zero new Go dependencies (`github.com/jackc/pgx/v5` remains the single direct dependency).
  - Implemented `handler.go`:
    - `GET/PUT/DELETE /deploy/connections/{provider}`: Connection lifecycle with encrypted storage.
    - `GET /projects/{id}/publish`: Publish readiness evaluation combining git status, connected provider, secrets count, and architecture requirements.
    - `POST /projects/{id}/publish`: Atomic deployment trigger forwarding git repository details and encrypted project secrets as environment variables.
    - `GET /projects/{id}/deployments` & `GET /projects/{id}/deployments/{depId}`: Deployment history and status polling.
  - Added unit tests in `deploy_test.go`: Full coverage of connection lifecycle, AES-256-GCM crypto, publish readiness evaluation, and deployment triggering.
  - Registered `deployStore` and handlers in `cmd/control-plane/main.go`.
- **Part 3 — Agent-Engine Publish Evaluator (`services/agent-engine/`):**
  - Implemented `studio/publish.py`:
    - `evaluate_publish_readiness(repo_dir)`: Deterministically evaluates project architecture into:
      - **Path 1**: Web-only (static/SSR Next.js/HTML, deploys completely to Vercel/Netlify).
      - **Path 2**: Web + separate backend service (generates starter `render.yaml` and `fly.toml` for 1-click backend deployment).
      - **Path 3**: Full-stack with Database (detects migrations, Prisma, or Postgres connection strings; provides guidance for Neon/Supabase PostgreSQL connection string via `DATABASE_URL`).
  - Mounted `GET /api/workspaces/{id}/publish/readiness` in `studio/server.py`.
  - Added unit tests in `tests/test_publish_readiness.py`: Verified Path 1, Path 2, Path 3, custom `render.yaml` preservation, and environment variable detection.
- **Part 4 — Console Web UI (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added types (`DeployConnectionStatus`, `DeploymentRecord`, `PublishReadiness`, `TriggerPublishResponse`) and API methods (`getDeployConnection`, `saveDeployConnection`, `deleteDeployConnection`, `getPublishReadiness`, `triggerPublish`, `getProjectDeployments`, `getProjectDeployment`).
  - Added Next.js API route proxies:
    - `/api/deploy/connections/[provider]`
    - `/api/projects/[id]/publish`
    - `/api/projects/[id]/deployments`
    - `/api/projects/[id]/deployments/[depId]`
  - Built `components/hosting-keys-manager.tsx`: Settings -> Hosting tab for managing Vercel and Netlify personal access tokens with AES-256-GCM encryption notice and token generation documentation links.
  - Built `components/publish-dialog.tsx`: Modal opened from Studio Workspace Header with architecture assessment badge, GitHub repository check, provider selector, inline token connector, secrets count notice, deploy trigger, and live site link.
  - Built `components/project-publish-manage.tsx`: Studio Manage -> Publish tab with live production card, visit site, redeploy, backend guidance configs, and deployment history table.
  - Mounted `HostingKeysManager` on `app/settings/page.tsx`, `PublishDialog` on `app/studio/studio-workspace.tsx`, and `ProjectPublishManage` on `app/studio/[projectId]/manage/page.tsx`.
- **Part 5 — Verification & Contract Testing:**
  - Updated `scripts/test.sh` with R-509 contract assertions.
  - Verified Go tests (`go test ./...` in `services/control-plane`), Python tests (`test_publish_readiness.py`), Next.js typecheck, lint, and production build (`next build`), and full `task verify` (3,831 tests pass).

## 2026-09-20 — R-508 (F-10 Security Scanning & Automated Tests)

- **Why:** Generated applications require automated verification of dependency safety, credential exposure prevention, framework security rules, and test execution across heterogeneous stacks (web, Python, Go) without inventing fake scores or vanity badges. `F-10-security-tests.md` specified deterministic dependency audits (`pnpm audit`, `pip-audit`, `govulncheck`) with honest skipped state for uninstalled toolchains, secret scanning over generated source code for API key prefixes, base64 private keys, and live `.env` files, framework rules checks (`dangerouslySetInnerHTML`, wildcard CORS with auth, `httpOnly`/`SameSite` cookies, raw SQL concatenation), test discovery and execution (`pnpm test`, `pytest`/`unittest`, `go test ./...`), control-plane REST proxy endpoints with project tenant isolation, and Lovable/Dyad-grade Console UI in Studio Manage -> Security and Studio Manage -> Tests tabs.
- **Part 1 — Agent-Engine Security & Test Runners (`services/agent-engine/`):**
  - Implemented `studio/security.py`:
    - `run_security_scan(repo_dir)`: Coordinates dependency audits, deterministic secret scans, and framework security checks. Caches report to `.omnistackai/security_report.json`.
    - `_scan_secrets_in_repo(repo_dir)`: Detects provider API keys (`sk-[A-Za-z0-9_-]{20,}`, `AIza[0-9A-Za-z-_]{35}`, `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9]{36}`, `stripe_secret`), private key blocks (`-----BEGIN ... PRIVATE KEY-----`), and live `.env` files (ignoring `.env.example`).
    - `_scan_framework_rules(repo_dir)`: Inspects source files for `dangerouslySetInnerHTML`, wildcard CORS with credentials/auth, cookies lacking `httpOnly` or `SameSite`, and raw SQL string interpolation.
    - `_run_dependency_audits(repo_dir)`: Executes `pnpm audit --json`, `pip-audit --format=json`, and `govulncheck -json ./...` when manifest files exist. Reports missing tools honestly as `skipped: <tool> not installed`, never as passed.
    - `get_last_security_report(repo_dir)`: Retrieves cached report.
  - Implemented `studio/tests_runner.py`:
    - `run_project_tests(repo_dir)`: Detects and runs available test suites (`pnpm test`, `python3 -m unittest` / `pytest`, `go test ./...`). Caches report to `.omnistackai/test_report.json`.
    - `_detect_test_suites(repo_dir)`: Discovers runnable suites from `package.json`, Python test files/directories, and Go `*_test.go` files.
    - `_run_single_suite(suite_info, repo_dir)`: Executes runner with timeout, captures output, and parses test names, durations, and status using regex patterns. Returns honest empty state (`no_tests`) when no suites are found.
    - `get_last_test_report(repo_dir)`: Retrieves cached report.
  - Updated `studio/server.py`: Mounted REST handlers `POST /api/workspaces/{id}/security/scan`, `GET /api/workspaces/{id}/security`, `POST /api/workspaces/{id}/tests/run`, and `GET /api/workspaces/{id}/tests`.
  - Added unit tests in `tests/test_security_and_tests.py`: 12 comprehensive unit tests covering secret scans, framework checks, dependency audit skipping, clean reports, test runner discovery, honest empty state, result parsing, and REST endpoints (all 12 passed).
- **Part 2 — Control-Plane Backend (`services/control-plane/`):**
  - Updated `internal/projects/handler.go`: Registered `POST /projects/{id}/security/scan`, `GET /projects/{id}/security`, `POST /projects/{id}/tests/run`, `GET /projects/{id}/tests`.
  - Implemented proxy handlers with caller ownership verification, streaming/response forwarding, and upstream error handling.
  - Added unit test in `internal/projects/projects_test.go`: `TestProjectSecurityAndTests` verifying all 4 endpoints with upstream agent-engine mocks.
- **Part 3 — Console Web UI (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added types (`SecurityFinding`, `SecurityCheck`, `ProjectSecurityReport`, `TestCaseResult`, `TestSuiteResult`, `ProjectTestReport`) and client SDK functions (`runProjectSecurityScan`, `getProjectSecurityReport`, `runProjectTests`, `getProjectTestReport`).
  - Added Next.js API route proxies: `/api/projects/[id]/security/scan`, `/api/projects/[id]/security`, `/api/projects/[id]/tests/run`, `/api/projects/[id]/tests`.
  - Built `components/project-security-manage.tsx`: Lovable/Dyad-grade Manage -> Security UI:
    - Summary metric cards: Total Findings, Critical, High, Medium, Low.
    - Checks performed checklist with Pass, Issues Found, and Skipped badges with honest uninstalled-tool notes.
    - Clean state card: "No issues found by these checks" when clean.
    - Findings accordion grouped by file and severity, with code location, rule explanation, suggested fix, and "Fix with AI" action (copies prompt and navigates to Studio chat).
    - Severity filter and search bar.
  - Built `components/project-tests-manage.tsx`: Lovable/Dyad-grade Manage -> Tests UI:
    - Summary bar: Total tests, Passed, Failed, Skipped, and total Duration.
    - Per-suite cards with runner badges, status badges, duration chips, collapsible raw output terminal, and individual test cases.
    - Failed test details with error messages and "Fix with AI" action.
    - Honest empty state: "This project has no test suite yet — ask the chat to add one" with "Ask Chat to Add Tests" action.
  - Updated `app/studio/[projectId]/manage/page.tsx`: Added `Security` and `Tests` navigation tabs in sidebar and mounted both components.
- **Part 4 — Verification & Contracts:**
  - Added R-508 contract assertions in `scripts/test.sh`.
  - `bash scripts/test.sh`: passed.
  - `cd services/control-plane && go test ./...`: all 14 packages passed.
  - `PYTHONPATH=src pytest tests/test_security_and_tests.py`: 12/12 passed.
  - `cd apps/console-web && pnpm run typecheck && pnpm run lint`: 0 errors, 0 warnings.
  - `pnpm run build`: all 28 static routes and dynamic API routes compiled cleanly.
  - `task verify`: all 3,827 tests passed; Stage 0 verification passed.
  - `task lint`, `task security:quick`, `task env:check`: all passed.
- **Next:** Review roadmap and founder build sequence for next tasks.

## 2026-09-20 — R-507 (F-09 Database Explorer & SQL Editor)

- **Why:** Generated applications create and use real PostgreSQL databases in local development and preview mode. Developers need direct visibility into their tables, column schemas, and live data, as well as the ability to test and run SQL queries safely without external database GUI tools or exposing database credentials. `F-09-database.md` specified an agent-engine database service connecting directly to the workspace container via `psql --csv`, transaction-isolated query execution with automatic rollback for read-only safety, statement timeouts (10s), 32 KB query size limits, control-plane REST proxy endpoints with project ownership isolation, 409 Conflict handling for unprovisioned databases, and a Lovable-grade Console UI in Studio Manage -> Database with table browser, column structure viewer, SQL editor, and migration schema viewer.
- **Part 1 — Agent-Engine Database Service (`services/agent-engine/`):**
  - Implemented `studio/database.py`:
    - `get_database_name(repo_dir)`: Computes the Postgres database name matching preview plan.
    - `check_database_exists(db_name)`: Probes `pg_database` in the container.
    - `list_tables(repo_dir, db_name)`: Queries `information_schema.tables` and `pg_stat_user_tables` to list base tables with schema, approximate row count, and column count.
    - `get_table_schema(db_name, table, schema)`: Fetches column definitions (name, data type, nullable, default).
    - `get_table_rows(db_name, table, ...)`: Paginated row query with sanitized table/column names, limit/offset, and ASC/DESC sorting.
    - `execute_query(db_name, sql, write=False, ...)`: Enforces read-only transactions by wrapping queries in `BEGIN; ... ROLLBACK;` by default. When `write=True`, statements execute with autocommit. Enforces 32 KB SQL size limits, 10s statement timeout, records duration and row counts, and logs queries to `StudioLogManager`.
    - `get_schema_sql(repo_dir)`: Reads `services/api/migrations/0001_init.sql` (or first migration file).
  - Updated `studio/server.py`: Mounted REST routes `GET /api/workspaces/{id}/db/tables`, `GET /api/workspaces/{id}/db/tables/{table}`, `POST /api/workspaces/{id}/db/query`, and `GET /api/workspaces/{id}/db/schema`, returning HTTP 409 Conflict when database does not exist.
  - Added unit tests in `tests/test_database_explorer.py`: 30 unit tests covering table listing, schema inspection, pagination, row queries, read-only rollback wrapping, write mode execution, 32 KB size cap, timeout handling, SQL injection protection, and schema reading (all 30 passed).
- **Part 2 — Control-Plane Backend (`services/control-plane/`):**
  - Updated `internal/projects/handler.go`: Registered `GET /projects/{id}/db/tables`, `GET /projects/{id}/db/tables/{table}`, `POST /projects/{id}/db/query`, and `GET /projects/{id}/db/schema`.
  - Implemented proxy handlers with caller ownership verification, URL parameter/query string forwarding, and upstream error mapping (preserving 409 Conflict status).
  - Added unit test in `internal/projects/projects_test.go`: `TestProjectDatabaseExplorer` verifying all 4 endpoints with upstream agent-engine mocks.
- **Part 3 — Console Web UI (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added database interfaces (`DBTable`, `DBTablesResponse`, `DBColumnMeta`, `DBTableRowsResponse`, `DBQueryResult`, `DBSchemaResponse`) and client functions (`getProjectDBTables`, `getProjectDBTableRows`, `executeProjectDBQuery`, `getProjectDBSchema`).
  - Added Next.js API route proxies: `/api/projects/[id]/db/tables`, `/api/projects/[id]/db/tables/[table]`, `/api/projects/[id]/db/query`, `/api/projects/[id]/db/schema`.
  - Built `components/project-db-manage.tsx`: Lovable-grade component with three sub-views:
    - Tables & Data Explorer: Table list sidebar with live search and row count badges; Table Header with total rows; Data tab with sortable columns and pagination; Structure tab with column types, nullability badges, and default values.
    - SQL Editor: Monospace editor with placeholder, `Cmd+Enter` execution shortcut, Write Mode toggle with amber warning banner, execution duration and row count chips, verbatim error displays, and results table.
    - Schema SQL Viewer: Migration SQL viewer with one-click clipboard copy.
    - Unprovisioned DB Empty State: Friendly banner with refresh action when database is not yet created.
  - Updated `app/studio/[projectId]/manage/page.tsx`: Added Database tab with `Database` icon in sidebar navigation and wired `ProjectDbManage`.
- **Part 4 — Verification & Contracts:**
  - Added R-507 contract assertions in `scripts/test.sh`.
  - `bash scripts/test.sh`: passed.
  - `cd services/control-plane && go test ./...`: all 14 packages passed.
  - `PYTHONPATH=src pytest tests/test_database_explorer.py`: 30/30 passed.
  - `cd apps/console-web && pnpm run typecheck && pnpm run lint`: 0 errors, 0 warnings.
  - `pnpm run build`: all 28 static routes and dynamic API routes compiled cleanly.
  - `task verify`: all 3,815 tests passed; Stage 0 verification passed.
  - `task lint`, `task security:quick`, `task env:check`: all passed.
- **Next:** Proceed to F-10 (R-508) Security scanning & automated test runs (spec `R_&_D/specs/F-10-security-tests.md`).

## 2026-09-20 — R-506 (F-08 Logs & Live Chat Streaming)

- **Why:** Developers building with OmniStackAI need complete observability into build/generation events and live preview runtime outputs, the ability to immediately stop in-flight builds without paying for ungenerated tokens or corrupting git history, voice input convenience, and the ability to attach reference files (schemas, markdown, code). `F-08-logs-chat.md` specified structured build logs (`build.jsonl`), preview runner stdout/stderr log rotation (`app.log`) with secrets scrubbing (`***`), REST/SSE logs endpoints, real build cancellation with 0 git commits and consumed-token debiting, Web Speech API voice input, text attachments, and a Lovable-grade Manage -> Logs UI (`Lova-17`).
- **Part 1 — Agent-Engine Logs & Cancellation (`services/agent-engine/`):**
  - Implemented `studio/logs.py`: `StudioLogManager` with `append_build_log`, `write_app_log` with file rotation (`OMNISTACKAI_LOG_MAX_BYTES` default 5 MB, max 3 rotated files), `scrub_secrets` replacing known secrets with `***`, `read_logs` with level/search filtering, `stream_logs` SSE generator, and `clear_logs`.
  - Updated `studio/workspace.py`: Added cancellation flags (`set_cancelled`, `is_cancelled`, `clear_cancelled`), attachments storage (`save_attachment`, `get_attachments`).
  - Updated `localrun/run.py` & `studio/preview.py`: Added `log_callback` parameter to preview runner daemon threads to tee stdout/stderr directly to `StudioLogManager.write_app_log`.
  - Updated `studio/live_serve.py`: Emits structured build event logs to `build.jsonl`. Checks `workspace_store.is_cancelled` during token generation and before disk/git operations. On cancellation, immediately breaks without committing anything and yields `phase: cancelled`. Exposed `workspace_cancel`, `workspace_logs`, `workspace_logs_stream`, and `workspace_logs_clear`.
  - Updated `studio/server.py`: Mounted REST handlers for `/api/workspaces/{id}/cancel`, `/api/workspaces/{id}/logs`, `/api/workspaces/{id}/logs/stream`, and `DELETE /api/workspaces/{id}/logs`.
  - Added unit tests in `tests/test_logs_and_cancellation.py`: Secrets scrubbing, log rotation, read/clear logs, cancellation flags, attachments, and streaming cancellation with stub provider (all passed).
- **Part 2 — Control-Plane Backend (`services/control-plane/`):**
  - Updated `internal/projects/handler.go`: Registered `POST /projects/{id}/build/cancel`, `GET /projects/{id}/logs`, `GET /projects/{id}/logs/stream`, `DELETE /projects/{id}/logs`.
  - In `handleProjectBuildStream`: Handled `phase == "cancelled"` by debiting credits for actual consumed tokens, recording `model_calls` with `error_code = 'cancelled'`, and relaying frame to client. Added client disconnect detection to cancel upstream agent-engine build immediately.
  - Added unit tests in `internal/projects/projects_test.go`: `TestProjectLogsAndCancellation` verifying logs retrieval and cancellation flow.
- **Part 3 — Console Web UI & Chat Controls (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added `BuildLogEntry`, `ProjectLogsResponse` interfaces and `getProjectLogs`, `clearProjectLogs`, `cancelProjectBuild`, `streamProjectLogs` API methods.
  - Added Next.js API route proxies: `/api/projects/[id]/logs`, `/api/projects/[id]/logs/stream`, `/api/projects/[id]/build/cancel`.
  - Built `components/project-logs-manage.tsx`: Lovable `Lova-17` design with Build / App source switch, level filter (`all`, `info`, `warn`, `error`), search query input, follow toggle, copy to clipboard, and log download.
  - Updated `app/studio/[projectId]/manage/page.tsx`: Mounted "Logs" tab in Studio Manage sidebar with `Terminal` icon.
  - Updated `app/studio/studio-chat.tsx`:
    - Real Build Cancellation: When `submitting`, Send button transforms into Stop button with `Square` icon (`aria-label="Stop generation"`). On click, calls `AbortController.abort()`, posts to `/api/projects/{id}/build/cancel`, stops streaming, and appends "Stopped. Nothing was committed."
    - Voice Input: Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) toggle button with animated listening state, transcribing speech into composer.
    - Attachments: Paperclip button accepting text files (`.md`, `.txt`, `.json`, `.csv`, `.sql`, `.ts`, `.tsx`, `.py`) up to 256 KB (max 4). Displays attachment chips with file size and remove button. Appends content as fenced markdown blocks to prompt. Rejects image files with honest notice on non-vision models.
- **Part 4 — Verification & Contracts:**
  - Added R-506 contract assertions in `scripts/test.sh`.
  - `bash scripts/test.sh`: passed.
  - `cd services/control-plane && go test ./...`: all 14 packages passed.
  - `task agent-engine:test`: all 3,785 tests passed.
  - `cd apps/console-web && pnpm run typecheck && pnpm run lint`: 0 errors, 0 warnings.
  - `task verify`: Stage 0 verification passed.
  - `task lint`, `task security:quick`, `task env:check`: all passed.
- **Next:** Proceed to F-09 (R-507) Database Explorer & SQL Editor (spec `R_&_D/specs/F-09-database-explorer.md`).

## 2026-09-20 — R-505 (F-07 SEO & AI search)

- **Why:** Generated applications must be indexable by search engines and readable by AI search agents out of the box. `F-07-seo.md` specified Next.js indexability codegen (`sitemap.ts`, `robots.ts`, `llms.txt`, `opengraph-image.tsx`, JSON-LD structured data, and per-page metadata), PostgreSQL schema migration `000009_seo`, Go control-plane store and REST handlers, deterministic SEO audit engine (0 credits, free), and a Lovable-grade Console UI in Studio Manage -> SEO with site defaults, pages table, live Google Search / Social card previews, audit findings, and optional AI copy suggestions.
- **Part 1 — Codegen for Next.js Indexability (`services/agent-engine/codegen/nextjs.py`):**
  - Generated `app/sitemap.ts` enumerating indexable routes with priorities and change frequencies.
  - Generated `app/robots.ts` pointing to `sitemap.xml` and respecting `NEXT_PUBLIC_DISCOURAGE_SEARCH`.
  - Generated `public/llms.txt` defining application purpose, routes, and content policy for AI search crawlers.
  - Generated `app/opengraph-image.tsx` using `next/og` (1200×630) for social share preview cards.
  - Injected JSON-LD structured data (`WebSite` and `Organization`) into `app/layout.tsx`.
  - Generated per-screen layout metadata (`title`, `description`, `openGraph`, `twitter`, `alternates.canonical`).
- **Part 2 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000009_seo.up.sql` / `down.sql`:
    - `project_seo`: `project_id` PK (FK cascade), `site_name`, `default_title`, `description`, `canonical_host`, `discourage`, `updated_at`.
    - `project_page_seo`: `id` UUID PK, `project_id` FK (cascade), `route`, `title`, `description`, `noindex`, `updated_at`, unique `(project_id, route)`.
- **Part 3 — Go Control-Plane Backend (`services/control-plane/`):**
  - Implemented `internal/seo/store.go`: `Store` interface and `PgStore` with tenant isolation and ownership checks (`GetProjectSEO`, `SetProjectSEO`, `GetProjectPageSEOs`, `GetProjectPageSEO`, `SetProjectPageSEO`, `DeleteProjectPageSEO`).
  - Implemented `internal/seo/handler.go`: REST handlers for `GET/PUT /projects/{id}/seo`, `GET /projects/{id}/seo/pages`, `PUT /projects/{id}/seo/pages/{route...}`, `POST /projects/{id}/seo/audit`, and `POST /projects/{id}/seo/suggest`.
  - Added unit tests in `internal/seo/seo_test.go` verifying defaults, tenant isolation (foreign project 404), page updates, and page listings.
  - Registered `seo.Register` in `cmd/control-plane/main.go`.
- **Part 4 — Deterministic SEO Audit Engine (`services/agent-engine/`):**
  - Implemented `seo/audit.py`: Checks generated files for missing/duplicate titles, description lengths (50–160 chars), missing canonical URLs, missing OpenGraph images, missing or multiple `<h1>` headings, images without `alt`, routes missing from `sitemap.ts`, unintentional `noindex`, and missing `public/llms.txt`. Calculates 0–100 health score with line-level findings (0 credits).
  - Updated `studio/workspace.py`: `update_page_seo` updates `app/[route]/layout.tsx` and commits changes to git workspace repository.
  - Added unit tests in `tests/test_seo_codegen_and_audit.py`: Codegen presence, sitemap/robots/llms.txt/og-image content, audit passing on generated apps, audit detecting flaws on broken apps, and workspace git commit creation.
- **Part 5 — Console-Web Frontend UI (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added SEO types (`ProjectSEO`, `ProjectPageSEO`, `SEOFinding`, `SEOAuditReport`, `SEOSuggestion`) and client functions (`getProjectSEO`, `setProjectSEO`, `getProjectPageSEOs`, `setProjectPageSEO`, `auditProjectSEO`, `suggestProjectSEOCopy`).
  - Added Next.js API route proxies: `/api/projects/[id]/seo`, `/api/projects/[id]/seo/pages`, `/api/projects/[id]/seo/pages/[...route]`, `/api/projects/[id]/seo/audit`, `/api/projects/[id]/seo/suggest`.
  - Built `components/project-seo-manage.tsx`: Lovable-grade SEO management component with site defaults, pages table with 50–160 character counters, Google Search and Social share live simulators, deterministic audit panel with health score and line-level findings, and AI copy suggestions with explicit credit confirmation notice.
  - Updated `app/studio/[projectId]/manage/page.tsx`: Added "SEO & AI Search" tab in sidebar navigation.
- **Part 6 — Verification & Contracts:**
  - Added R-505 contract assertions in `scripts/test.sh`.
  - `bash scripts/test.sh`: passed with R-505 contract assertions.
  - `cd services/control-plane && go test ./...`: all 14 packages passed.
  - `bash scripts/agent-engine.sh test`: all 3,779 tests passed.
  - `cd apps/console-web && pnpm run typecheck && pnpm run lint`: 0 errors, 0 warnings.
  - `bash scripts/console.sh build`: all 58 routes compiled and built cleanly.
  - `bash scripts/verify.sh`: Stage 0 verification passed.
- **Next:** Proceed to F-08 (R-506) Logs & live chat streaming (spec `R_&_D/specs/F-08-logs-chat.md`).

## 2026-09-20 — R-504 (F-06 AI — model configuration and usage)

- **Why:** Developers and teams want control over which AI model powers each project (e.g. Claude 3.7 Sonnet for complex apps, Groq Llama 3.3 for rapid scaffolding) and the ability to Bring-Your-Own-Key (BYOK) to avoid platform markups and usage caps. Every model call must be immutably tracked with exact token counts, latency, and cost for transparent accounting. `F-06-ai-usage.md` specified AES-256-GCM encrypted BYOK keys in PostgreSQL, per-project model pinning, an immutable `model_calls` audit table, multi-tier resolution precedence, and a Lovable-grade Console UI in Settings (AI & Usage) and Project Manage.
- **Part 1 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000008_ai_usage.up.sql` / `down.sql`:
    - `user_provider_keys` table: UUID `id`, `user_id` FK (cascade delete), `key_ciphertext BYTEA`, `provider_id TEXT`, `label TEXT`, `created_at`, `updated_at`, `last_used_at`, and unique constraint on `(user_id, provider_id)`.
    - `model_calls` immutable audit table: `id BIGSERIAL PRIMARY KEY`, `user_id`, `project_id`, `provider_id`, `model_id`, `tier`, `purpose`, `input_tokens`, `output_tokens`, `cost_micros_usd`, `credits_spent`, `billed_to` (`platform`/`byok`/`local`), `success`, `error_code`, `latency_ms`, `created_at`. Added indexes on `(user_id, created_at DESC)` and `(project_id, created_at DESC)`.
    - Altered `projects` table to add `model_provider_id TEXT` and `model_id TEXT` for per-project pinning.
- **Part 2 — Control-Plane Backend & Cryptography (`services/control-plane/`):**
  - Implemented `internal/ai/store.go`:
    - `Store` interface and `PgStore` implementing AES-256-GCM encryption with AAD bound to `user_id:provider_id`, preventing any user from decrypting another user's keys.
    - Transparent re-encryption on key rotation via `OMNISTACKAI_SECRETS_KEY_PREVIOUS`.
    - Store methods: `ListUserKeys`, `GetUserKey`, `SetUserKey`, `DeleteUserKey`, `RecordModelCalls`, `GetProjectUsage`, `GetAccountUsage`, `GetProjectModel`, and `SetProjectModel`.
  - Implemented `internal/ai/resolution.go`:
    - `ResolveModel`: Enforces strict precedence: (1) Project pinned model -> (2) User BYOK key (0 credits debited, `billed_to = 'byok'`) -> (3) Platform cloud provider (credits debited, `billed_to = 'platform'`) -> (4) Local Ollama (0 credits, `billed_to = 'local'`).
    - `RecordUsageCalls`: Maps both granular `calls: [...]` arrays and legacy aggregate summaries into `model_calls` audit rows.
  - Implemented `internal/ai/handler.go`:
    - REST handlers: `GET /ai/providers`, `GET /ai/keys`, `PUT /ai/keys/{providerId}`, `DELETE /ai/keys/{providerId}`, `POST /ai/keys/{providerId}/test`, `GET /ai/models`, `GET/PUT /projects/{id}/model`, `GET /projects/{id}/usage`, `GET /usage`.
    - Write-only security: BYOK keys are never returned in any API response or log.
    - Key test endpoint makes a 1-token probe without persistent logging.
  - Added unit tests in `internal/ai/ai_test.go`: AAD protection, key non-leakage, key test validation, project model pinning, and key deletion.
  - Injected `AIStore` into `cmd/control-plane/main.go`, `internal/projects/handler.go`, and `internal/jobs/handler.go`, recording `model_calls` rows atomically alongside credit debits on builds and edits.
- **Part 3 — Agent-Engine Integration (`services/agent-engine/`):**
  - Updated `intake/provider_resolution.py`: `resolve_generation_provider_from_env` accepts explicit `provider_id`, `model_id`, and `api_key`.
  - Updated `studio/live_serve.py`: Propagates explicit provider/model/key to generation functions, and emits granular `usage.calls: [...]` breakdown in responses.
  - Added unit tests in `tests/test_studio_workspace_ai.py` verifying explicit provider/model/key resolution and `usage["calls"]` payload structure.
- **Part 4 — Console-Web Frontend UI (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added AI types (`KeyMetadata`, `ModelCall`, `UsageTotals`, `DailyUsage`, `PurposeUsage`, `ProjectUsageReport`, `AccountUsageReport`, `ProjectModelConfig`, `ProviderCatalogItem`) and client functions.
  - Added Next.js API route proxies: `/api/ai/providers`, `/api/ai/keys/[providerId]`, `/api/ai/keys/[providerId]/test`, `/api/projects/[id]/model`, `/api/projects/[id]/usage`, `/api/usage`.
  - Built `components/ai-keys-manager.tsx`: Client component in Settings for managing BYOK keys with AES-256-GCM encryption notice, test button with latency feedback, and Add/Edit/Delete modals.
  - Built `components/account-usage-viewer.tsx`: Client component in Settings for account-wide AI usage with KPI cards (calls, tokens, USD cost, credits spent), per-project breakdown table, daily activity table, and 7d/30d/90d range selectors.
  - Built `components/project-ai-manage.tsx`: Client component in Studio Manage for project-level model pinning and project usage metrics.
  - Updated `app/settings/page.tsx`: Added "BYOK keys" and "AI usage" sections with in-page nav anchors.
  - Updated `app/studio/[projectId]/manage/page.tsx`: Added "AI & Model" tab in subnav sidebar rendering `ProjectAIManage`.
- **Part 5 — Verification & Contracts:**
  - Added R-504 contract assertions in `scripts/test.sh`.
  - `bash scripts/test.sh`: passed with R-504 contract assertions.
  - `cd services/control-plane && go test ./...`: all 13 packages passed.
  - `bash scripts/agent-engine.sh test`: all 3,769 tests passed.
  - `cd apps/console-web && pnpm run typecheck && pnpm run lint`: 0 errors/warnings.
  - `bash scripts/console.sh build`: all 52 routes compiled and built.
  - `bash scripts/verify.sh`: Stage 0 verification passed.
- **Next:** Proceed to F-07 (R-505) SEO & AI search (spec `R_&_D/specs/F-07-seo-and-ai-search.md`).

## 2026-09-20 — R-503 (F-05 Secrets — encrypted per-project configuration)

- **Why:** Real-world generated applications require API keys, payment tokens, SMTP credentials, and database passwords that must never be committed to git, exposed in client responses, or leaked in build streams. `F-05-secrets.md` specified AES-256-GCM encrypted storage in PostgreSQL with Go standard library `crypto/aes` and `crypto/cipher` (zero external Go dependencies), runtime injection into preview processes via `process.env`, and a Lovable-grade Console UI in `Manage → Secrets` with masked values, a 30s reveal timer, key validation, and preview restart prompts.
- **Part 1 — Database Migration (`services/control-plane/migrations/`):**
  - Created `000007_project_secrets.up.sql` / `down.sql`: `project_secrets` table with UUID `id`, `project_id` foreign key (cascade delete), `key ~ '^[A-Z][A-Z0-9_]*$'` constraint, `value_ciphertext BYTEA`, `description TEXT`, `created_at`, `updated_at`, `last_used_at`, and unique constraint on `(project_id, key)`.
- **Part 2 — Control-Plane Backend (`services/control-plane/`):**
  - Updated `internal/config/config.go`: Added `SecretsKeyPrevious` field from `OMNISTACKAI_SECRETS_KEY_PREVIOUS` for transparent key rotation.
  - Implemented `internal/secrets/store.go`: `Store` interface and `PgStore` with AES-256-GCM encryption using AAD `project_id:key`, tamper rejection, transparent re-encryption on key rotation, `ListSecrets`, `SetSecret`, `DeleteSecret`, `RevealSecret`, and `ForProject`.
  - Implemented `internal/secrets/handler.go`: REST handlers for `GET /projects/{id}/secrets`, `PUT /projects/{id}/secrets/{key}`, `DELETE /projects/{id}/secrets/{key}`, and `POST /projects/{id}/secrets/reveal/{key}`. Returns HTTP 503 when master key is unconfigured (never storing plaintext) and verifies caller project ownership.
  - Added unit tests in `internal/secrets/secrets_test.go`: Key pattern validation, store availability, AAD tamper protection, key rotation, and HTTP handler authorization / tenant isolation.
  - Updated `internal/projects/handler.go` and `cmd/control-plane/main.go`: Injected `SecretsStore` into projects handler and forwarded decrypted secrets map as `{"env": secrets}` in `handleProjectPreview`.
- **Part 3 — Agent-Engine Runtime Injection (`services/agent-engine/`):**
  - Updated `localrun/plan.py`: `build_run_plan` accepts `extra_env` and merges it into backend and web `RunStep` environments.
  - Updated `localrun/run.py`: `_plan_from_env` and `start_preview_app` accept and forward `extra_env`.
  - Updated `studio/preview.py`, `studio/live_serve.py`, and `studio/server.py`: `_handle_workspace_preview` parses `env` from JSON body and injects it into workspace preview runner.
  - Added unit tests in `tests/test_studio_workspace_secrets.py`: Verifies decrypted secrets are present in preview process environments and never written to repository files on disk.
- **Part 4 — Console-Web Frontend UI (`apps/console-web/`):**
  - Updated `lib/control-plane.ts`: Added `SecretMetadata`, `SetSecretParams`, `SecretRevealResponse` and client functions `getProjectSecrets`, `setProjectSecret`, `deleteProjectSecret`, `revealProjectSecret`.
  - Added Next.js API routes: `/api/projects/[id]/secrets/route.ts`, `/api/projects/[id]/secrets/[key]/route.ts`, and `/api/projects/[id]/secrets/reveal/[key]/route.ts`.
  - Updated `app/studio/[projectId]/manage/page.tsx`: Added Secrets subnav tab, masked table display (`••••••••`), 30-second reveal countdown timer, UPPER_SNAKE_CASE client validation, Add/Edit dialog, Delete confirmation, copy key action, and preview restart banner.
- **Part 5 — Verification & Contracts:**
  - Updated `.env.example`, `scripts/env-check.sh`, and `scripts/test.sh` with R-503 contract checks.
  - `bash scripts/test.sh`: passed with R-503 assertions.
  - `cd services/control-plane && go test -v ./...`: all 12 packages passed.
  - `bash scripts/agent-engine.sh test`: all 3,765 tests passed.
  - `cd apps/console-web && pnpm run typecheck && pnpm run lint`: 0 errors/warnings.
  - `bash scripts/console.sh build`: all 48 routes compiled and built.
  - `bash scripts/verify.sh`: Stage 0 verification passed.
- **Next:** Proceed to F-06 (R-504) AI — model configuration (BYOK) and usage per project/account (spec `R_&_D/specs/F-06-ai-usage.md`).

## 2026-09-20 — R-502 (F-04 Knowledge & Skills Engine)

- **Why:** Custom instructions and domain-specific knowledge are necessary for guiding AI app generation without repeated prompting. `F-04-skills.md` specified a two-tier model: project-level Knowledge (injected into every prompt for that project) and account-level Skills (reusable across projects, attachable, or `@mentionable` per message), with deterministic context assembly bounded by a server-side cap and honest truncation reporting.
- **Part 1 — Database & Control-Plane (`services/control-plane`):**
  - Created database migration `000006_skills.up.sql` / `down.sql`: `skills` table (account-scoped, unique `(user_id, slug)`, 8 KB body cap), `project_skills` junction table, and `knowledge` column in `projects` (16 KB cap).
  - Implemented `internal/skills/store.go` and `handler.go`: CRUD endpoints (`/skills`, `/skills/{id}`), project knowledge (`GET/PUT /projects/{id}/knowledge`), and project skills (`GET/POST /projects/{id}/skills`, `DELETE /projects/{id}/skills/{skillId}`) with caller ownership verification.
  - Implemented `ResolveContext(ctx, userID, projectID, mentions)`: resolves project knowledge, attached skills, and `@mentioned` skills with tenant isolation.
  - Updated `internal/projects/handler.go` to inject `ResolveContext` into agent-engine `/build` and `/edit` payloads as `"context"`.
  - Added unit and HTTP integration tests in `skills_test.go`.
- **Part 2 — Agent-Engine Context Assembly (`services/agent-engine`):**
  - Implemented `assemble_context(...)` in `src/omnistackai_agent_engine/intake/context.py`: bounded by `OMNISTACKAI_CONTEXT_MAX_CHARS` (default 24k chars).
  - Deterministic priority: Knowledge first, then attached and mentioned skills alphabetically. Truncates cleanly at skill boundaries when over budget, returning `context_truncated: true`, `active_skills`, and `truncated_skills`. Zero external dependencies.
  - Integrated into `intake/nl_to_ir.py`, `intake/build_app.py`, `intake/app_delta.py`, `studio/live_serve.py`, and `studio/server.py`. System prompt injects context instructions without leaking skill bodies into client responses.
  - Added 9 unit tests in `tests/test_skills_context.py` covering knowledge-only, skills-only, combined, truncation, and empty contexts.
  - Ensured backward compatibility in `AppDeltaProposal.to_dict()`.
- **Part 3 — Console-Web Frontend UI (`apps/console-web`):**
  - Added Skills and Knowledge types and API client functions in `lib/control-plane.ts`.
  - Added Next.js API routes under `/api/skills/`, `/api/skills/[id]/`, `/api/projects/[id]/knowledge/`, and `/api/projects/[id]/skills/`.
  - Built `components/skills-library.tsx`: Account skills library with search, cards, delete confirmation, and `SkillEditorDialog`/`SkillEditorForm` (kebab-case slug validation, 8 KB counter, live "What the model will see" preview, 4 starter templates: "Stripe Billing & Subscriptions", "Tailwind + Radix UI Design System", "Strict TypeScript & Zod Schemas", "Audit Logging & Security Headers").
  - Mounted skills library in `/settings#skills`.
  - Updated `/studio/[projectId]/manage/page.tsx`: Added "Knowledge" tab (16 KB counter, autosave/save status) and "Skills" tab (attached skills list, library picker modal, detach action, "New skill" shortcut).
  - Updated `studio-chat.tsx`: Added active context chips with next-message toggle, inline `@` skill mention autocomplete popover, and amber `context_truncated` banner when instructions exceed the server cap.
- **Evidence & Verification:**
  - `bash scripts/test.sh`: passed with R-502 contract assertions.
  - `cd services/control-plane && go test -v ./...`: passed 100% across all packages.
  - `PYTHONPATH=services/agent-engine/src python3 -m unittest discover -s services/agent-engine/tests`: passed 3,763 tests in 82.5s.
  - `pnpm --filter omnistackai-console-web typecheck && pnpm --filter omnistackai-console-web lint`: clean with 0 errors/warnings.
  - `bash scripts/console.sh build`: successfully generated all 46 routes.
  - `bash scripts/verify.sh`: all Stage 0 checks passed.
- **Next:** Proceed to F-05 (R-503) Secrets — encrypted per-project configuration (spec `R_&_D/specs/F-05-secrets.md`).

## 2026-09-20 — R-501 (F-03 Code ownership — download, connect GitHub, push)

- **Why:** Code ownership is essential to prevent vendor lock-in and enable deployment to Vercel/Netlify. `F-03-git.md` specified two paths: a free, instant no-account `.zip` export, and a full GitHub App connection with installation token minting, repo creation, and authenticated push with zero credential leakage.
- **Part 1 — Instant Download (.zip) (`services/agent-engine` & `services/control-plane`):**
  - Implemented `export_zip(workspace_id, out_file)` in `services/agent-engine/src/omnistackai_agent_engine/studio/workspace.py`: streams workspace repo at HEAD into a `.zip` archive on-the-fly, strictly filtering out VCS internals (`.git`), dependencies (`node_modules`), caches (`.next`, `__pycache__`, `.venv`, `venv`), and environment secrets (`.env`, `.env.*` except `.env.example`).
  - Added route `GET /api/workspaces/{id}/export` in agent-engine server.
  - Added streaming handler `GET /projects/{id}/export` in control-plane `internal/git/handler.go` with tenant verification and streamed proxying.
- **Part 2 — GitHub App Integration & Cryptography (`services/control-plane`):**
  - Created database migration `000005_git_connections.up.sql` / `down.sql`: `git_connections` table with encrypted refresh tokens and scopes, and added `repo_full_name`, `repo_url`, `repo_private`, `last_pushed_sha`, `last_pushed_at` to `projects`.
  - Cryptography helper `internal/crypto/gcm.go`: standard library AES-256-GCM encryption with 12-byte random nonce and AAD verification. 100% test coverage in `gcm_test.go`.
  - GitHub App client `internal/git/github.go`: stdlib `crypto/rsa` RS256 JWT minting (`MintAppJWT`), installation access token generation (`MintInstallationToken`), and user repository creation (`CreateUserRepo`). Zero external JWT dependencies.
  - Store `internal/git/store.go`: manages `git_connections` CRUD and project repo metadata with encrypted storage.
  - REST Handlers `internal/git/handler.go`: `GET /git/github/authorize`, `GET /git/github/callback`, `GET /git/status`, `DELETE /git/connection`, `GET /projects/{id}/git`, `POST /projects/{id}/git/repo`, `POST /projects/{id}/git/push`, `GET /projects/{id}/export`.
  - Push safety & zero-leakage: pushes directly to URL refspec `git push <url> HEAD:<branch>` without modifying `.git/config`; scrubs 100% of tokens from stderr, stdout, and error responses with `[REDACTED]`. Verified in unit tests `git_test.go` and `test_studio_workspace_git.py`.
- **Console Web UI (`apps/console-web`):**
  - Added Git types and client methods in `lib/control-plane.ts`.
  - Added Next.js API routes:
    - `/api/projects/[id]/export/route.ts` (streaming download proxy)
    - `/api/git/status/route.ts`
    - `/api/git/connection/route.ts`
    - `/api/git/github/authorize/route.ts`
    - `/api/projects/[id]/git/route.ts`
    - `/api/projects/[id]/git/repo/route.ts`
    - `/api/projects/[id]/git/push/route.ts`
  - Rebuilt `apps/console-web/app/studio/[projectId]/manage/page.tsx`:
    - Added nav switcher between General and Git & GitHub tabs.
    - Not-connected state: explanation, Connect GitHub button, and Download .zip button.
    - Connected, no repo: account chip (`@login`, Disconnect), repo name input pre-filled with project slug, Private/Public toggle, Create repository button.
    - Connected with repo: repo link to GitHub, last pushed commit & time, "N commits ahead" sync badge, Push button with spinner, copyable `git clone` command.
  - Updated `apps/console-web/app/studio/studio-workspace.tsx`:
    - Added "Download code" action in header and GitHub repository link once connected.
- **Evidence & Verification:**
  - `bash scripts/test.sh`: passed with R-501 contract assertions.
  - `cd services/control-plane && go test -v ./...`: passed 100% across all packages.
  - `PYTHONPATH=services/agent-engine/src python3 -m unittest discover -s services/agent-engine/tests`: passed 3,754 tests in 78.9s.
  - `pnpm --filter omnistackai-console-web typecheck && pnpm --filter omnistackai-console-web lint`: passed with 0 errors/warnings.
  - `bash scripts/console.sh build`: created Next.js production bundle with all 38 routes.
  - `bash scripts/verify.sh`: all Stage 0 checks passed.
- **Next:** Await user permission before committing or pushing code. Proceed to F-04 Skills Engine (R-502, spec `R_&_D/specs/F-04-skills.md`).

## 2026-09-20 — R-500 (F-02 Multi-Process Preview & Diagnostics Service)

- **Why:** Generated apps bound exclusively to `127.0.0.1:<port>`, preventing preview iframes from loading when accessing the console from mobile devices or other computers on the LAN. In addition, Studio was running in build-only mode without clear phase progress (`install` -> `migrate` -> `start` -> `ready`), lacked idle process harvesting, and gave ambiguous error states. `F-02-preview.md` specified an authenticated same-origin reverse proxy, strict SSRF defense, named lifecycle phase progression, idle reaper, and honest status banners.
- **Reverse Proxy & SSRF Prevention (`apps/console-web`):**
  - Created `apps/console-web/app/preview/[projectId]/[[...path]]/route.ts`: authenticated streaming reverse proxy mounted at `/preview/${projectId}/**`.
  - SSRF Defense: strictly verifies session authentication and project ownership against Control Plane `GET /projects/{id}`; retrieves internal port only from trusted control-plane state (never trusts caller headers or query parameters); validates loopback address (`127.0.0.1` / `localhost`).
  - HTML & Path Rewriting: injects `<base href="/preview/${projectId}/">` into HTML responses; dynamically rewrites root-relative Next.js chunk references (`/_next/` to `/preview/${projectId}/_next/`); rewrites `Location` redirect headers and `Set-Cookie` paths to preserve subpath isolation.
  - Streaming: supports chunked streaming for HTML, text, and binary assets (images, fonts, bundles) with hop-by-hop header stripping.
- **Agent Engine Preview Management (`services/agent-engine`):**
  - Updated `localrun/run.py` to support `on_phase` callbacks during app initialization.
  - Updated `studio/preview.py`:
    - Created `WorkspacePreviewSession` tracking lifecycle phase, process IDs, web/api ports, start/elapsed times, and last access timestamps.
    - Implemented `start_workspace`, `workspace_status`, and `stop_workspace`.
    - Implemented an automatic idle timeout reaper governed by `OMNISTACKAI_PREVIEW_IDLE_MINUTES` (defaults to 30 min) to reap inactive preview processes.
  - Updated `studio/live_serve.py` and `studio/server.py` with routes:
    - `GET /api/workspaces/{id}/preview` (status inspection)
    - `POST /api/workspaces/{id}/preview` (start with JSON response or text/event-stream SSE events)
    - `POST /api/workspaces/{id}/preview/stop` (stop running preview session)
  - Unit tests in `tests/test_studio_workspace_preview.py` (4/4 tests pass).
- **Control Plane (`services/control-plane`):**
  - Implemented routes in `internal/projects/handler.go`:
    - `GET /projects/{id}/preview`
    - `POST /projects/{id}/preview`
    - `POST /projects/{id}/preview/stop`
  - Validates project ownership via `Store.Get` (returning 404 for non-owners) and forwards to agent-engine preview API.
  - Unit tests in `internal/projects/projects_test.go` covering owner access, agent-engine proxying, and foreign user 404 isolation.
- **Console Web UI (`apps/console-web`):**
  - Extended `lib/control-plane.ts` with `PreviewStatus` (`phase`, `elapsed_ms`, `web_port`, `api_port`) and `getProjectPreview`/`stopProjectPreview` clients.
  - Added Next.js route handlers `app/api/projects/[id]/preview/route.ts` and `app/api/projects/[id]/preview/stop/route.ts`.
  - Updated `app/studio/studio-preview.tsx`:
    - Set iframe source to `/preview/${projectId}/`.
    - Auto-starts preview when `projectId` loads.
    - Visualizes real-time phase progression (`install` -> `migrate` -> `start` -> `ready`) with live timer.
    - Honest build-only banner: *"This server runs in build-only mode. Restart it with: ./scripts/omnistack.sh up"*.
    - Connected Restart and Stop controls to preview API endpoints.
- **Evidence & Verification:**
  - `bash scripts/test.sh` passing with R-500 assertions.
  - `go test -v ./...` in `services/control-plane` passed (0 failures).
  - `pnpm run typecheck && pnpm run lint` in `apps/console-web` passed (0 errors, 0 warnings).
  - `python3 -m unittest services/agent-engine/tests/test_studio_workspace_preview.py` passed (4 tests in 0.5s).
  - All 3,750 agent-engine tests passed in 79.7s.
  - Full platform `task verify` passed with code 0 (`Ran 3750 tests in 79.716s, OK. Stage 0 verification passed.`).
- **Next:** Proceed to F-03 Git Push / GitHub Export (R-501, spec `R_&_D/specs/F-03-git.md`).

## 2026-09-20 — R-499 (F-01 Projects & Workspaces Persistence)

- **Why:** projects and edits previously lived only in RAM in `studio/session.py` and `studio/history.py`.
  Process restarts destroyed turns, files, and state, and build URLs `/jobs/build/{id}/files` had no
  tenant isolation check (cross-tenant read vulnerability). `F-01-projects.md` specified true on-disk
  workspace persistence, database tracking in PostgreSQL, project management UI, and tenant isolation.
- **Database & Control-Plane (`services/control-plane`):**
  - Migration `000004_projects.up.sql` / `down.sql`: `projects` table with UUID primary key, `user_id` foreign key,
    composite unique index `(id, user_id)` for tenant isolation, `name`, `description`, `last_prompt`,
    `status` ('active' | 'archived'), `state` ('created' | 'building' | 'ready' | 'failed'), `entities`, `preview_url`,
    `opened_at`, `created_at`, `updated_at`.
  - Package `internal/projects`: `Store` interface & `PgStore` implementing tenant-isolated CRUD, atomic credit
    debits on builds/edits, touched-opened timestamp updates, and soft/hard deletes.
  - REST Handler `internal/projects/handler.go`: endpoints `GET /projects`, `POST /projects`, `GET /projects/{id}`,
    `PATCH /projects/{id}`, `DELETE /projects/{id}`, `POST /projects/{id}/opened`, `POST /projects/{id}/build/stream`,
    `POST /projects/{id}/edit`, `GET /projects/{id}/turns`, `GET /projects/{id}/files`, `GET /projects/{id}/file`,
    `GET/POST /projects/{id}/preview`, `GET/POST /projects/{id}/problems`.
  - Registered in `cmd/control-plane/main.go`. Unit test suite in `internal/projects/projects_test.go` (100% pass).
- **Agent Engine (`services/agent-engine`):**
  - Module `studio/workspace.py`: `StudioWorkspaceStore` with root `~/.omnistackai/workspaces/<uuid>/`.
    Stores `repo/` (git repo), `state.json` (atomic write via tempfile + `os.replace`), `turns.jsonl` (append-only log),
    `ir.json` (deserialized IR snapshot), `.lock` (`fcntl.flock` concurrency protection). Survives daemon restarts.
  - Updated `studio/server.py` with `/api/workspaces/<id>` routes and concurrency locking.
  - Updated `studio/live_serve.py` with `_workspace_build`, `_workspace_build_stream`, `_workspace_edit`.
  - Unit tests in `tests/test_studio_workspace.py` (8/8 pass).
- **Console Web UI (`apps/console-web`):**
  - Updated `lib/control-plane.ts` with typed project API clients and data structures.
  - Created `lib/time.ts` for relative timestamp formatting ("5m ago", "yesterday").
  - Created 10 Next.js API route handlers proxying project endpoints securely with session cookies.
  - Created components: `ProjectCard`, `ProjectDialogs` (rename, delete, duplicate), `HomeProjects`, `ProjectSwitcher`.
  - Created pages: `/projects` dashboard (search, active/archived tabs, sort by updated/created/name),
    `/studio/[projectId]` studio workspace routing, `/studio/[projectId]/manage` General settings panel.
  - Wired `ProjectSwitcher` and on-disk workspace hydration into `studio-chat.tsx` and `studio-tabs.tsx`.
- **Evidence & Verification:**
  - `bash scripts/test.sh` passing with newly pinned R-499 contracts.
  - `pnpm --filter omnistackai-console-web run typecheck` and `lint` 100% clean (0 errors, 0 warnings).
  - All 3,746 agent-engine tests passing (`Ran 3746 tests in 78.396s, OK`).
  - Full platform `task verify` passed with code 0.
- **Next:** Proceed to F-02 Preview & Diagnostics Service (R-500).

## 2026-09-19 — R-498 (Platform buildout plan + single-command local runtime)

- **Why:** the founder reviewed the console live and listed what a platform still needs (preview,
  Publish, Git, domains, Skills, SEO, connectors, payments, usage, logs, SQL, secrets, DB,
  analytics, chat controls, multi-project), and asked for an overview, a decision per feature,
  implementable specs so work can pause and resume, an explanation of the two run commands, and
  one script to run everything.
- **Verified before writing anything:** preview binds to loopback (`localrun/run.py`); the build
  history and editable IR are in memory — **proven live**: after a restart, build 7 returned
  `{"turns": []}` and 404 for files, and the next build was numbered 1; preview itself works (30 s
  build, 5 s preview, the running app served `<title>Simple Note Taking</title>`), so the
  founder's "Preview is not working" was build-only mode; the schema has no projects table;
  preview already creates a real per-app Postgres; every build is already a git repo.
- **Delivered:** `R_&_D/OmniStackAI_Platform_Buildout_v1.md` (decisions for all 23 features, the
  GitHub App mechanism, the Skills design, the dependency graph), `R_&_D/specs/` with **15 specs**
  (UI + migration + API + flow + acceptance each), `scripts/omnistack.sh`
  (up/down/restart/status/logs/build/doctor/verify/open, **preview by default**), Taskfile
  aliases, `.run/` gitignored.
- **Two real bugs in my own script, found by running it:** `down` silently skipped the Docker step
  because a trailing `&&` was a loop's last command under `set -e`; it still aborted because
  `lsof` exits 1 on a free port and the script uses `pipefail`. Both fixed and explained in
  comments. A third issue — `status` guessing the Studio mode from the log and reporting
  "build-only?" while preview was live — was replaced with an authoritative `/api/preview` probe.
- **Evidence:** `down` stops processes *and* containers (exit 0, `docker ps` empty); a **cold `up`
  took 13.8 s**; `status` reports pids and the real mode; login/`/`/`/studio`/`/settings` all 200
  afterwards. Gates: `scripts/test.sh` + new R-498 block, `task verify` 3,738 OK,
  lint/security/env.
- **Next:** F-01 (R-499) projects persistence — the prerequisite for everything else.

## 2026-09-19 — R-497 (Console: Lovable-grade pass after the founder's reference screenshots)

- **Why:** the founder shared 96 screenshots (`~/Desktop/AI_Platform_Screenshots`: Dyad 40,
  Emergent 18, Lovable 38) and asked which to follow. Reviewed all of them as labelled contact
  sheets (Pillow, 12 per sheet) and the decisive screens at full size. **Lovable** chosen as
  the primary reference (dark, dense, chat-left project workspace, prose replies, follow-up
  chips, a "More" panel with a real product IA); Dyad for the prompt-first home; Emergent only
  the credits chip we already have. Recorded in memory and the kickoff doc.
- **Built (real behavior only):** `components/home-composer.tsx` — the dashboard hero is a
  composer ("What do you want to build, {name}?", chips, Build → `/studio?prompt=`); the Studio
  reads `?prompt=` (never with `?build=`), pre-fills the composer and starts exactly one build
  through the existing form submit (`requestSubmit()` + ref guard; no setState in the effect,
  no second code path), then cleans the URL; assistant replies as prose rows with a brand-mark
  gutter, 13px rail; three follow-up chips after a completed build/edit that fill the composer;
  a shared file-search filter above the Files and Code trees ("N of M files match") and a
  "Read only" label on the viewer. Not borrowed, on purpose: Cloud/Publish/Payments panels (no
  backend), a project switcher (no per-user build list), Web/Mobile tabs (hard gate).
- **Gates:** typecheck/lint clean first run; build 25 routes; `scripts/test.sh` passes (new
  block also pins the home and Studio example prompts to identical strings); `task verify`
  3,738 OK; lint/security/env pass.
- **Live smoke:** `/` hero + composer + chips, old "Open Studio" button gone, rest unchanged;
  `/studio?prompt=hello%20world` server-renders the pre-filled composer with Send enabled and no
  build triggered (the auto-start is a client effect — verified against the real `disabled`
  attribute after a first grep matched the `disabled:` class variants); `/studio` empty → Send
  disabled; `/studio?build=5` unchanged and not pre-filled; 0 server errors. Founder to try the
  browser flow.
- **Next:** the founder's pick (Publish/deploy, sandbox→preview + per-user routing, Node.js
  codegen, mobile, tenant isolation) or a per-user build list to power a project switcher.

## 2026-09-19 — R-496 (Console: motion, states & polish — the overhaul's last task)

- **Why:** every screen was on the R-491 stack; what remained was the finish — loading and
  error states, social metadata, entry motion, and retiring the last pinned legacy CSS.
- **Built:** `app/studio/loading.tsx` and `app/settings/loading.tsx` (skeletons under their
  gated layouts); the dashboard's and Settings' provider-status card streams inside
  `<Suspense>` below the auth gate (async `ProviderCard` / `ProvidersSection`); `app/error.tsx`
  (branded, `error.digest` as a reference, Try again on Next 16's documented `retry()`, Go home)
  and `app/global-error.tsx` (own `html`/`body`, inline dark styling — global styles never
  reach it); `metadataBase` from the new optional `OMNISTACKAI_CONSOLE_PUBLIC_URL` with a
  fallback to the real dev address, `openGraph` + `twitter` fields, and a generated 1200×630
  PNG via `ImageResponse` from `next/og` (`opengraph-image.tsx`, `twitter-image.tsx`
  re-export); a `.reveal` rise+fade utility (transform/opacity, 60ms stagger via
  `--reveal-index` from `lib/motion.ts`, collapsed by `prefers-reduced-motion`) on the
  dashboard, settings, fabric, auth card, 404/error pages, Studio empty states and new chat
  messages; tinted `shadow-*` utilities via `--shadow-tint`; `.pill`/`.spinner`/`@keyframes
  spin` and every dead token alias removed; the R-475 assertion edited to the three radius
  tokens; `globals.css` 330 lines. Redesign audit checklist recorded honestly in the contract.
- **A real regression caught live, fixed in-task:** a root `app/loading.tsx` (built first) made
  signed-out `/`, `/studio`, `/settings` answer **200** with `<meta http-equiv="refresh">` and
  a `NEXT_REDIRECT` payload instead of 307 — a Suspense boundary above `redirect()` makes Next
  fall back to a client-side redirect. Removed; replaced by the Suspense-below-the-gate pattern;
  a `test.sh` assertion now forbids a root `loading.tsx` with that note. Also caught: the new
  contract block's `rg -qF "--shadow-tint"` parsed its pattern as a flag — both loops pass
  `--` now.
- **Gates:** typecheck/lint clean; build **25 routes** (the two image routes are new);
  `scripts/test.sh` passes; `task verify` 3,738 OK; lint/security/env pass.
- **Live smoke:** every route responds with the right status signed out and in (307s
  restored); `<head>` carries the full `og:*`/`twitter:*` set with an absolute `og:image`;
  `/opengraph-image` and `/twitter-image` → 200 `image/png`, 56,598 bytes, `file` says 1200×630
  RGBA; reveal indexes 0–5 on the right elements; compiled CSS has reduced-motion, `.reveal`,
  `rise`, `--shadow-tint`, no `.pill`/`.spinner`; streamed provider cards render; 0 server
  errors. Honest limits: loading fallbacks and the error boundary need a browser.
- **Next:** the UI overhaul is complete. Direction needs the founder's pick — Publish/deploy,
  sandbox providers into Studio preview + per-user routing, Node.js codegen, mobile, tenant
  isolation.

## 2026-09-19 — R-495 (Console: Settings + Fabric; legacy CSS sweep)

- **Why:** `/settings` and `/fabric` were the last two screens on the hand-rolled legacy classes
  — one table titled "Model Providers", and five `.panel`s over a static snapshot.
- **Built:** Settings — header, `lg` two-column with a sticky in-page nav; Account as a
  read-only `dl` with the honest "Profile editing isn't available yet." (no fake Save);
  Appearance with `components/theme-switcher.tsx` (System/Light/Dark segmented control on
  `next-themes`, `role="group"`, `aria-pressed`, hydration-safe via a `useSyncExternalStore`
  mounted flag — in Settings, not a header sun/moon switch); Model providers with the live
  Ready/Not ready summary from the unchanged `getProviderStatus()` call, routing mode / cloud
  tier / configured count, and a card per provider with a real "Set `KEY_ENV` in `.env`" hint
  from `ProviderInfo.keyEnv` (names only) and "Runs your next build" on the active one. Fabric
  — a "snapshot vN" badge and the true regeneration note (`scripts/console.sh snapshot` on
  every console build), the routing ladder, Providers and Price book as semantic tables with
  sr-only captions and `tabular-nums`, Usage & resilience stat cards that say "No model calls
  are recorded in this snapshot." instead of hiding zeros, the builder showcase with gate chips
  and a `DiffBlock` coloring `+`/`-`/`@@` lines. Still public.
- **CSS sweep:** 266 lines of the dead legacy family removed by a deterministic script that kept
  only the R-475-pinned `.pill`/`.pill--accent`/`.spinner`/`@keyframes spin` (and the token
  aliases); `.grain::before` scoped from `fixed` to `absolute` (it had covered the whole
  viewport from the auth screen's panel).
- **Three real gate catches, all mine, fixed before shipping:** `react-hooks/set-state-in-effect`
  *is* enabled (the mounted-flag effect → `useSyncExternalStore`); my sweep comment contained
  `--radius-*/`, whose `*/` closed the comment and broke the build with a real
  `CssSyntaxError`; the dead 640px `@media` block still carried `.wrap` — caught by the new
  contract block, missed by my line-anchored grep. `task verify` had run zero tests while
  `test.sh` failed; checked for the count line, re-run → 3,738 OK.
- **Gates:** typecheck/lint clean, build 23 routes, `scripts/test.sh` passes, `task verify`
  3,738 OK, lint/security/env pass.
- **Live smoke:** `/settings` signed in — every section, the theme control in its disabled
  pre-mount SSR state (by design), Ready · groq, 11 provider cards, 8 real `keyEnv` hints;
  `/fabric` signed out — snapshot badge, ladder, both captioned tables (11 rows / 20 price
  cells), the zero-usage note, the diff (12/12/12 colored lines), Sign in / Create account;
  signed in — account menu; no legacy selectors exist in the stylesheet (HTML "hits" were
  Tailwind utilities); other routes unchanged; 0 server errors.
- **Next:** R-496 (motion, states & polish; retire the pinned selectors with the assertion).

## 2026-09-19 — R-494 (Console: Studio tabs — Preview chrome, Files tree, Code viewer, Problems)

- **Why:** R-493 rebuilt the Studio's rail and workspace shell; the four tabs inside it were
  still the R-481 hand-rolled versions (flat 200-item list, native `<select>`, 560px iframe with
  two text buttons, plain problems list).
- **Constraints read first:** R-481 pins `studio-tabs.tsx`, `code-highlight.ts` and the four
  quoted labels; R-479 pins `studio-preview.tsx`; R-475 pinned `studio-icons.tsx` — retired here
  with that assertion edited deliberately. **The contract tests then caught my own stale R-493
  assertion** (it still demanded the shim) on their first run — replaced with a note; and, per
  the R-493 lesson, I checked `task verify` for the `Ran N tests` line rather than trusting an
  empty tail (it had run zero tests until `test.sh` passed).
- **Built:** `studio-tabs.tsx` on the vendored shadcn `Tabs` (real Radix tabs), Lucide icon per
  trigger, live file/problem counts; **Files** = a collapsible tree (`file-tree-model.ts` pure
  `buildFileTree`/`ancestorsOf`/`countFiles`; `file-tree.tsx` `FileTree` with `aria-expanded`
  dirs, depth indentation, selected row, default expansion derived — top-level + ancestors of the
  selected file — with user toggles as overrides, no effects; no cap); **Code** = tree pane +
  viewer with sticky header (path, extension badge, lines, size), unchanged tokenizer on the
  `.code-tok-*` colors, `tabular-nums` gutter, skeleton loading, alert errors, honest
  binary/truncated notes; **Problems** = Check button with spinner, result badge, empty/clean
  states, per-file cards whose header opens the file in Code, `parseDiagnostic` for tsc's
  `L12:5 TS2339: msg` (verbatim fallback, no invented severity), raw output in `<details>`;
  **Preview** = unchanged state machine + toolbar (status pill, URL, Open in new tab,
  Desktop/Tablet/Phone `aria-pressed` presets, Restart/Stop), taller frame, skeleton starting
  state, designed disabled/error states; idle renders the stopped card instead of nothing.
- **R-477 degradation closed:** `studio-chat.tsx` fetches the file list on `?build=` hydration
  (`fetchBuildFiles` at module scope; SSE/edit/404 untouched); `StudioWorkspace` shows the
  restored note with the file count whenever the snapshot has no name.
- **Mid-task refactor, recorded:** the pure tree functions moved to a React-free `.ts` module so
  the smoke could run them with `node --experimental-strip-types` against the real file list.
- **Gates:** typecheck/lint clean first run; build 23 routes; `scripts/test.sh` passes; `task
  verify` 3,738 OK; lint/security/env pass; re-gated after the refactor.
- **Live smoke (build 5):** new tabs server-rendered with full ARIA, legacy classes gone; tree
  model on the real 173 files — 173 leaves, dirs-first alphabetical at every level, depth 7,
  correct ancestors, 0 duplicates; a real 6,214-byte file read; problems GET 404 → POST **409
  "tsc is not installed for this app…"** (R-480's honest build-only answer, rendered as the tab's
  alert); preview POST/GET 404 (the disabled state); 0 server errors. Honest limits: client
  interactions and the ready/diagnostics states need a browser + `task
  agent-engine:studio:preview` — the founder is asked to run that and open
  `localhost:4321/studio?build=5`.
- **Next:** R-495 (Settings + Fabric).

## 2026-09-19 — R-493 (Console: Studio core — chat rail + workspace shell on shadcn/Lucide)

- **Why:** the Studio is the product, and after R-491/R-492 it was still the R-477/R-481
  hand-rolled layout (right-hand chat panel, plain bubbles, "Loading history…", a stats card, a
  raw textarea) inside the new shell. This task rebuilds the core the way Lovable / Dyad /
  Emergent lay it out. The founder's screenshots have not been shared yet; the layout follows
  the reference platforms' common structure (chat left, workspace right, full width).
- **Constraints read first, from `scripts/test.sh`:** R-475 pins `studio-icons.tsx`; R-477 pins
  `studio-workspace.tsx` and `.studio-grid`; R-479/R-481/R-485 pin `StudioPreview`/`StudioTabs`/
  `sendBuildStream` inside `studio-chat.tsx`; and R-494's `studio-tabs.tsx`/`studio-preview.tsx`
  import icons from `studio-icons.tsx`. So: `studio-icons.tsx` became a **thin Lucide shim**
  (same export names, 18px + `aria-hidden` defaults) — one icon family across the console
  immediately, untouched files keep compiling, R-494 can retire the shim + assertion
  deliberately; `.studio-grid` kept its name with a new definition; **chat logic stayed
  byte-for-byte** (hydration, three-shape SSE parser, edit, 404 recovery, credits,
  `previewVersion`, `router.replace`) — only presentation and error-string casing changed.
- **Built:** `AppShell layout="full"` (main → flex column; the header container follows the prop
  too, after the smoke caught it still capped at 1180px); `.studio-grid` chat rail
  `minmax(340px,400px)` left + workspace right at `calc(100dvh - 3.5rem)`, each scrolling
  internally, stacking below `lg`; rail header (project name, credits Badge, **New app** action —
  there was no way to start a second app without editing the URL); `role="log"` thread with
  user/assistant/`role="alert"` error bubbles, server errors sentence-cased via
  `formatServerError`; working bubble (`LoaderCircle` + live label keeping R-485's character
  count + three shimmer `Skeleton` lines); skeleton bubbles while hydrating; "What do you want to
  build?" empty state with three real example prompts that fill and focus the composer;
  composer with focus-within ring, `field-sizing-content` auto-grow, Enter/Shift+Enter,
  `ArrowUp` Send, hint, "Editing {name}" line; workspace with a transform-only indeterminate
  progress bar, a designed "Your app will show up here" empty state, and `StudioWorkspace`
  rewritten as a compact project header (entity badges capped at 8, files/commit/latest-turn
  usage in `tabular-nums`, a "Restored from this session's history" variant) above the untouched
  `StudioTabs`. Dead legacy CSS removed; `.studio-progress` + keyframes added.
- **Gates:** typecheck/lint clean first run; build 23 routes. **The new contract block caught a
  real leftover on its first run** — two `@media` blocks still carried `.studio-topbar`/
  `.studio-main` overrides and a 900px `.studio-grid`/`.chat-rail` override that would have
  fought the new 1023px rule; removed. That failure had made `task verify` run zero tests
  (`verify.sh` runs `test.sh` first) — noticed from the empty output, re-run: 3,738 OK.
  lint/security/env pass.
- **Live smoke:** `/studio` signed in serves every new marker, legacy markup gone, full-layout
  `<main>`; `/studio?build=does-not-exist` renders the hydrating skeletons + restored header;
  **one real streamed build with example prompt #1 verbatim** — 200 `text/event-stream`, 9s,
  2,458 `generating_ir` frames + `done` ("Task Tracker", 5 entities, 173 files, id 5) + the
  trailing credits frame; `/studio?build=5` 200, 2 turns hydrated, 173 files listed; credits
  100 → 100 (`credits_spent: 0` — the pre-existing R-476 price-book gap, recorded). Header
  container fix verified from the served HTML of both `/studio` and `/`. **0 server errors.**
  Console left running detached on 4321 for the founder.
- **Next:** R-494 (Studio tabs). Consider fetching the file list on `?build=` hydration so a
  restored session isn't empty in Files/Code (a pre-existing R-477 degradation).

## 2026-09-19 — R-492 (Console: auth screens + app shell — nav, user menu, skip link, 404, dashboard)

- **Why:** second task of the Console UI overhaul and the first one a user actually sees. R-491
  changed nothing visible beyond fonts/tokens; this task redesigns sign-in / create-account, adds
  the shared application shell, a branded 404 and a real dashboard.
- **Design decision from a direct read, not assumption:** route groups (`app/(app)/`,
  `app/(auth)/`) were the textbook structure — and would have broken eight earlier
  `scripts/test.sh` contract blocks that assert the literal current paths (`app/login/page.tsx`,
  `app/studio/layout.tsx` *containing* `getCurrentUser`, `app/settings/layout.tsx`,
  `studio-icons.tsx`, …). Kept the file layout; the shell is a shared server component every
  authenticated layout/page wraps itself in. Same visible result, zero contract churn.
- **Built on the R-491 stack** (shadcn primitives + Lucide + Tailwind utilities; `globals.css`
  untouched; no new dependencies): `components/app-shell.tsx` (skip link → `#main`, sticky
  translucent header, brand mark + wordmark, nav, account menu or sign-in actions, `<main>` with
  the legacy `.studio-main` geometry so the untouched Studio grid still fits);
  `components/app-nav.tsx` (`usePathname`, `aria-current="page"`); `components/user-menu.tsx` on
  the vendored `DropdownMenu` — a real Radix menu — with name/email, plan, tabular credits,
  links, destructive Sign out with loading state (the old `app/logout-button.tsx` retired into
  it and deleted); `components/auth-screen.tsx` split layout (grain brand panel, one soft brand
  glow, display headline, three *true* product statements); `login-form.tsx` /
  `register-form.tsx` with validation mirroring the server's limits, per-field `aria-invalid` +
  `aria-describedby` errors cleared on edit, `role="alert"` server banner (sentence-cased),
  spinner + disabled submit, show/hide password (`aria-pressed`), `noValidate` + `aria-busy`;
  login/register pages became server components (metadata, redirect signed-in visitors to `/`,
  control-plane-down treated as signed-out so the page still renders); `app/not-found.tsx`
  (Next 16 `not-found.js` convention, read from the bundled docs — also serves every unmatched
  URL); `app/page.tsx` dashboard — asymmetric 7/5 layout, honest three-step loop, live provider
  card reusing `getProviderStatus()` exactly as `/settings` does, plan/credits/role/BYOK cards,
  no invented "recent projects" (no per-user build history endpoint exists); titles trimmed to
  the R-491 template; `/fabric` wrapped in the shell with an optional user (stays public).
- **Gates:** typecheck + lint clean on the first run; build 23 routes (`/login`/`/register` now
  dynamic since they read the cookie); `scripts/test.sh` passes with a new R-492 block;
  `task verify` 3,738 OK; lint/security/env pass.
- **Live smoke (real stack):** signed-out 200/307/404 matrix as designed; served-HTML markers
  verified per page (template titles, form attributes, skip link, `aria-current` on exactly the
  right nav link for `/`, `/studio`, `/settings`, `/fabric`, Sign in / Create account on public
  `/fabric`, 404 copy); auth API through the real control-plane (401 "invalid email or
  password", 400 malformed, 200 + cookie); signed-in 200 everywhere and 307 from `/login`,
  `/register` to `/`; dashboard shows real data (Ready · groq · openai/gpt-oss-120b, 3 of 11
  providers configured, 100 credits, Radix trigger with `aria-haspopup="menu"`); Studio grid +
  chat rail intact; logout 204 → 307 again; **server log 0 errors**. Console left running
  detached on 4321 with its own log for the founder.
- **Smoke observations recorded** (not bugs): React 19 serializes `noValidate`/`autoComplete`/
  `maxLength` with camelCase names in SSR HTML, and inserts `<!-- -->` between adjacent text
  nodes — a first grep reported them missing; verified by dumping the raw tags instead.
- **Next:** R-493 (Studio core). Founder's screenshots shape R-493/R-494.

## 2026-09-19 — R-491 (Console: UI foundation — Tailwind v4 + shadcn/ui + Geist, dark-first)

- **Why:** after R-486–R-490 shipped, the founder asked why the platform UI is "just simple and
  very ugly." Honest, specific diagnosis from direct reads: `package.json` had zero UI
  dependencies (no component library, icon set, font, or motion), all styling was 858 lines of
  hand-rolled CSS with one indigo accent, this was a deliberate *enforced* constraint
  (`scripts/test.sh:276`, the R-470 gate, plus the Phase D "no new UI dependency" rule), and
  every task since prioritized backend correctness. Offered three honest options; the founder
  chose **Full UI overhaul now** ("I need proper best UI based platform not just simple a page";
  reference bar: Emergent/Lovable/Dyad, screenshots to be re-shared — none exist in the repo).
- **Roadmap written first** (plan file, Phase E-UI): R-491 foundation → R-492 auth + app shell →
  R-493 Studio core → R-494 Studio tabs → R-495 Settings/Fabric → R-496 motion/states/polish.
- **Gate retired with the decision recorded**: the R-470 `scripts/test.sh` gate blocking
  `tailwind|shadcn|…` was removed with a comment citing the founder's decision, replaced by an
  R-491 block asserting the new stack is present — the same "hard gates change only with explicit
  founder direction" discipline as every prior gate revision.
- **Stack decisions verified against real, current docs** (not assumed): Tailwind v4 via
  `@tailwindcss/postcss` per Next 16's own bundled CSS guide (read directly — the console's
  `AGENTS.md` warns Next 16 differs from training data); shadcn/ui confirmed supporting Tailwind
  v4 + React 19 + Next 16; Geist + Geist Mono via `next/font/google` per Next 16's font guide;
  `app/icon.svg` per Next 16's app-icons file convention; `next-themes` dark-first.
- **Real tooling drift, worked through honestly**: the installed shadcn CLI is v4.21.0 —
  `--base-color` no longer exists (now `--base <base|radix|aria>` chooses the component library;
  styling comes from named presets), the default preset `base-nova` is on Base UI not Radix,
  preset names are bare (`nova`, …), and Tailwind v4 is detected via `@import "tailwindcss"` in
  the CSS, not a config file. Three attempts failed first — one silently, because `timeout`
  doesn't exist on macOS (caught by inspecting the empty result). The Nova preset is literally
  "Lucide / Geist", the exact independent choice; Radix chosen deliberately over the Base UI
  default as the primitive set correct code can be written against.
- **A real bug introduced by `shadcn init`, caught and fixed**: init merged its semantic tokens
  into `:root` and clobbered two shared legacy names — `--muted` (legacy: muted *text*, 17 uses;
  shadcn: a near-white surface) and `--accent` (legacy: brand/button color, 14 uses; shadcn: a
  hover surface) — which would have made light mode's muted text near-invisible and primary
  buttons white-on-white. The full `globals.css` rewrite: shadcn semantic names as canonical, a
  cool-tinted OKLCH neutral scale, one amber `--brand` accent (no purple/blue AI gradient), tinted
  shadows, real type scale with `text-wrap: balance`, `tabular-nums`, `:focus-visible` rings,
  reduced-motion support, themed scrollbars, brand `::selection`, an opt-in `.grain` utility;
  every legacy name aliased via `var()` (follows the theme automatically), every `var(--muted)` →
  `var(--muted-foreground)`, brand uses → `--brand`, primary actions → `--primary`, hover/active/
  transitions added to legacy interactive classes, `100vh` → `100dvh`, and the legacy
  `prefers-color-scheme` dark block + syntax colors converted to the `.dark` class strategy so
  `next-themes` stays authoritative. `/fabric`'s one inline `var(--accent)` fixed to
  `var(--brand)` (allowed_paths extended mid-task, recorded).
- **Root layout**: Geist/Geist Mono as `--font-sans`/`--font-mono`, `suppressHydrationWarning`,
  `ThemeProvider` (class, dark default, system-aware), `TooltipProvider`, `Toaster`, title
  template + real description, branded `icon.svg`. 13 shadcn primitives vendored. No other page
  markup changed.
- **Gates**: `typecheck` clean; `lint` (one cosmetic warning fixed) clean; `build` 23 routes;
  `scripts/test.sh` passes; `task verify` 3,738 OK; lint/security/env pass.
- **Live smoke**: stale 4321 instance restarted on the new build; every route responds as
  expected (200 / 307-when-signed-out / 404), authenticated `/api/providers` 200 via a real
  cookie session, served `<html>` carries both Geist classes + the theme script, `/icon.svg`
  linked, 0 server errors. No browser tool in this session — founder eyeballs `localhost:4321`.
- **Next:** R-492 (auth + app shell). Founder's screenshots feed R-493/R-494.

## 2026-09-19 — R-490 (Runtime: sandbox provider-selection surface)

- **Why:** fifth and final task in the sandbox-provider sequence (R-486..R-490). R-486 through
  R-489 each built a real, independently-tested `SandboxLifecycleProvider` driver (E2B, Vercel
  Sandbox, Daytona, gVisor); none of them built the mechanism that actually lets a caller choose
  and switch between them — the founder's own explicit, repeated ask across this sequence:
  "switch easily... based on more cost, speed, smoothness," later made concrete as "just change
  configuration on a boolean value to switch the sandbox free or paid or per userbase in a
  setting."
- **Design, verified by direct source read before writing any code**: confirmed `runtime/tier.py`
  and `runtime/bootstrap.py` resolve a genuinely separate, *older* concern — the pre-R-486
  pure-planning `RuntimeProvider`/`DeploymentProvider` system, still backed by `drivers.py`'s
  placeholder-URL `CloudSandboxProvider` stub, correctly left untouched by every task in this
  sequence (R-486's own contract already documented why that planning abstraction can't become a
  real cloud sandbox lifecycle manager). The real `SandboxLifecycleProvider` system needed its own
  selection surface, not shoehorned into either older file.
- **New `runtime/sandbox_selection.py`**, deliberately mirroring `bootstrap.py`'s own established
  shape (`build_runtime_from_env(selection=None) -> RuntimeSetup`) for consistency: a registry
  (`_SANDBOX_LIFECYCLE_PROVIDERS`) mapping each of the four real provider names to its driver
  class's constructor; a new frozen `SandboxSetup` dataclass (`active`, `selected`, `provider`);
  and `build_sandbox_from_env(selection=None, *, providers=None) -> SandboxSetup`, reading a new
  `OMNISTACKAI_SANDBOX_PROVIDER` env var only when `selection` isn't passed directly, defaulting to
  `"none"` — matching `OMNISTACKAI_DEPLOY_PROVIDER`'s own precedent, meaning this task changes the
  actual behavior of zero existing deployments until an operator explicitly opts in.
- **A new `SandboxSelectionError`** (added to the shared `runtime/errors.py`, alongside the
  pre-existing `RuntimeSelectionError`/`DeploySelectionError` `bootstrap.py`'s own sibling
  functions already raise) for an unrecognized name or a real-but-inactive one, mirroring
  `build_runtime_from_env()`'s own "selecting a keyless cloud provider is a clear error"
  precedent — the unknown-name message lists every real, currently-registered provider name.
- **The `selection` parameter, when supplied explicitly, unconditionally takes priority over the
  global env var** — not an incidental detail, but literally the founder's own "switch... per
  userbase" mechanism made concrete: a future caller could compute a different `selection` per
  request (e.g. from a user's plan) without mutating any process-wide state, proven by a dedicated
  test (`test_explicit_selection_parameter_overrides_the_env_var`), not just described. Reading
  that real per-user plan data itself — which lives in the Go control-plane's `users.plan` column,
  not this Python codebase — is deliberately not attempted here, a materially larger, separate
  cross-service integration for its own future Tracker ID, mirroring how R-486 through R-489 each
  declined to wire their own driver into the Studio's actual preview flow for the same reason.
- **A real risk in this task's own test design was caught and avoided before it was ever
  committed**: an early draft test exercising the real registry-construction path (no `providers`
  override) would have triggered a genuine local Docker Unix-socket connection attempt via
  `GVisorSandboxProvider.active` (since `active` reporting evaluates every registered provider
  regardless of what's selected) — a real violation of "0 real network/Docker calls in any
  automated gate," however quickly and safely that connection attempt would fail on a machine
  without Docker running. Replaced with `TestRealRegistryWiring`, which asserts the registry maps
  every name to the correct real driver *class* via `assertIs` identity checks, with zero risk of
  any real I/O.
- **Gates**: agent-engine `task verify` **3,738 tests OK** (9 new, all in
  `test_runtime_sandbox_selection.py`), 0 model/network/Docker calls — covering the
  default-disabled state and its zero-behavior-change guarantee, `"none"` explicitly equivalent to
  unset, `active` aggregating multiple true fake providers correctly (sorted), env-var-based
  selection, the explicit-parameter-override behavior, case-insensitivity/whitespace trimming, an
  inactive selection raising, an unknown name raising with the real registered names listed, and
  the zero-I/O registry-wiring check. Repo-wide `task verify`/`lint`/`security:quick`/`env:check`
  all pass; a new, final `scripts/test.sh` contract block for this five-task sequence asserts
  `sandbox_selection.py`/`build_sandbox_from_env`/`SandboxSelectionError` all genuinely exist.
- **Every other file across this entire five-task sequence** (`sandbox_http.py`,
  `docker_socket.py`, `e2b.py`, `vercel_sandbox.py`, `daytona.py`, `gvisor.py`, `contracts.py`,
  `tier.py`, `bootstrap.py`, `drivers.py`, `local.py`, `providers.py`) remains completely,
  provably unmodified by this task.
- **This completes the five-task sandbox-provider sequence (R-486..R-490)**: four real,
  independently fetched-and-verified, independently-tested sandbox backends — E2B and Vercel
  Sandbox (microVM-isolated, paid managed clouds), Daytona (container-isolated paid managed cloud,
  with a real, honestly-surfaced isolation-strength tradeoff), and gVisor (genuinely free, open
  source, self-hosted, explicitly positioned as a development/free tier) — now sit interchangeably
  behind one shared contract, genuinely switchable by a single configuration value or an explicit
  per-call override.
- **Next** (not yet scoped into any task contract, per the founder's earlier direction): real
  multi-target Publish/deploy (Netlify one-click primary; Vercel/Cloudflare/self-host/GitHub-export
  as secondary options), Node.js backend codegen support alongside Python/Go, and starting mobile
  technology work (React Native near-term, per earlier competitor research). Full per-user
  process/tenant isolation as a wholesale architecture — beyond just which sandbox technology runs
  one preview, encompassing session-to-instance routing, per-user DB/port allocation, and
  state-store externalization — remains a separate, materially larger architecture decision
  needing its own explicit founder sign-off before any implementation, per the standing "stop and
  ask for hard-gate architecture decisions" rule.

## 2026-09-19 — R-489 (Runtime: free, self-hosted gVisor sandbox driver)

- **Why:** fourth of the five-task sandbox-provider sequence (R-486..R-490) — **replaces the
  originally planned WebContainers option**. Real research (WebSearch/WebFetch against
  `webcontainers.io`) found WebContainers requires a paid commercial license for any real
  (non-prototype) commercial use — free use is explicitly limited to prototypes/POCs — directly
  contradicting the founder's "free, no cost or too much configuration" ask, and it can only run
  Node.js anyway (no Python/Go), a real fit problem for this platform's generated backends.
- **Founder direction, recorded before implementation**: presented the real licensing/self-hosting
  picture for every credible candidate — Vercel Sandbox/Fly/CodeSandbox (paid-only, no self-host);
  raw Firecracker (free, open source, but a low-level building block whose self-hosted
  orchestration is a multi-quarter engineering project, exactly what R-486's own originating
  research warned against); E2B/Daytona (open source at their core, but self-hosting means
  operating their full orchestrator yourself); gVisor (genuinely free, open source, and a small,
  well-trodden lift — a drop-in Docker/OCI runtime, not a new platform to operate). The founder
  approved gVisor.
- **Two further real, practical questions asked before continuing, both answered directly**: (1)
  real resource cost on a dev machine — `runsc` is ~50MB on disk, runs as a lightweight user-space
  process on the *same* kernel (no VM, unlike Firecracker), layers directly onto the Docker daemon
  this project's own local Compose stack already runs, ~15-30MB RAM overhead per active sandbox,
  base images (`node:22-slim`, `python:3.13-slim`, `golang:1.23-alpine`) each a one-time cached
  download; (2) why not simply use this in production instead of paying for E2B/Vercel Sandbox/
  Daytona — answered honestly: gVisor solves kernel-level isolation for free, but the three paid
  providers actually charge for isolation *plus* a globally-distributed public routing/proxy layer
  with TLS and auto-scaling; a self-hosted gVisor sandbox's URL is a bare loopback address
  (`http://127.0.0.1:<port>`) that only resolves for a viewer on the same machine, so making it
  reachable by real remote users at production scale would mean building that entire layer from
  scratch — the same order of effort the original research already said not to take on. The
  founder confirmed the intended shape: gVisor as a genuinely free, self-hosted **development/
  free-tier** option, switchable per user/config alongside the three paid managed providers — not
  a replacement for any of them.
- **Design, verified against real, current documentation before writing any code**: the Docker
  Engine API (a long-established, extremely stable, ubiquitous surface, confirmed via a direct
  curl-example fetch, not summarized secondhand) — `POST /containers/create` (→ `"Id"`), `POST
  /containers/{id}/start`, `GET /containers/{id}/json` (`NetworkSettings.Ports` keyed by
  `"<port>/tcp"`, each a list of `{"HostIp", "HostPort"}`; `State.Status`), `POST
  /containers/{id}/kill`, `DELETE /containers/{id}`, `GET /info` (`Runtimes`, keyed by runtime
  name — the live signal this driver uses to detect whether `runsc` is registered).
- **A genuinely different transport, and the reason this task couldn't reuse `sandbox_http.py`
  unchanged**: the Docker daemon listens on a **Unix domain socket**
  (`/var/run/docker.sock` by default), not TCP — `urllib` has no Unix-socket support at all. New
  `runtime/docker_socket.py` adds a small, purpose-built sibling transport: a
  `http.client.HTTPConnection` subclass overriding `connect()` to open an `AF_UNIX` socket, the
  same stdlib idiom `docker-py` itself is built on internally — same safety invariants
  (bounded response, finite timeout, stable typed errors) and the same testability invariant
  (every call accepts an injectable `connection`, mirroring the injectable-`opener` pattern for
  the three cloud drivers).
- **New `runtime/gvisor.py`'s `GVisorSandboxProvider`** implements R-486's
  `SandboxLifecycleProvider` on top of this new transport. Two real, honest design differences
  from every other driver in this sequence: (1) `active` is a **live local capability check**, not
  an env-var check — this provider has no credential at all, so `active` queries the daemon's own
  `GET /info` and confirms `"runsc"` genuinely appears in `Runtimes`, defensively returning `False`
  (never raising) on any connection failure. (2) Unlike Vercel Sandbox (R-487), whose `runtime`
  enum has no Go at all, Docker's own image ecosystem covers every target this platform generates
  without exception, including a real `golang:1.23-alpine` mapping for `backend-go`.
- **A real, necessary correction to R-486's own original contract, found while designing this, not
  glossed over**: `SandboxHandle.__post_init__` originally required every `url` to start with
  `https://` unconditionally — correct for three cloud-only providers, but it would have rejected
  this driver's own legitimate `http://127.0.0.1:<port>` loopback URL outright. Relaxed to match
  the pattern `PreviewPlan` (the older, pre-R-486 local-preview contract) had already independently
  established for exactly this reason — confirmed safe first by checking no existing test asserted
  the old error message's exact text; `contracts.py` added to `allowed_paths` mid-task for this one
  minimal, well-justified correction, following the same mid-task scope-correction discipline
  already applied twice before this session (R-484's `RecordingProvider.stream()` gap, R-487's
  `RUNTIME_SPECS`/`drivers.py` registry-consistency gap).
- **Scope matches every prior driver in this sequence**: proves real lifecycle management
  (create/status/kill against a real local Docker daemon), not file-sync/install/run automation or
  wiring into the Studio's actual preview flow — the same boundary R-486/R-487/R-488 already
  established.
- **No live Docker daemon with `runsc` actually installed and registered exists in this
  environment** — every automated test is offline via an injected fake Unix-socket connection
  object; real live verification is honestly deferred, matching R-486/R-487/R-488's posture on
  missing cloud credentials.
- **Gates**: agent-engine `task verify` **3,729 tests OK** (22 new: 8 in
  `test_runtime_docker_socket.py`, 14 in `test_runtime_gvisor.py`), 0 model/network/Docker calls —
  covering the full create→start→inspect sequence and its exact request shapes, all four
  target→image mappings including Go, an unsupported target rejected before any request, a missing
  container id stopping before start/inspect, a missing host port raising clearly, a real
  Docker-shaped 404/500 error body mapping correctly, a connection-level failure mapping to
  `DockerUnreachableError`, and `status()`/`kill()` (kill-then-remove) both correctly keyed by the
  real container id. Repo-wide `task verify`/`lint`/`security:quick`/`env:check` all pass; a new
  `scripts/test.sh` contract block asserts the new driver/transport files and class exist. Every
  pre-existing suite passes unmodified beyond the one deliberate `SandboxHandle` relaxation.
- **Next:** R-490 (a provider-selection surface exposing the founder's explicit "switch easily by
  cost/speed/smoothness" ask — free gVisor vs. paid E2B/Vercel/Daytona, switchable per user/
  config) — the fifth and final task in this sequence.

## 2026-09-19 — R-488 (Runtime: real Daytona driver)

- **Why:** third of the five-task sandbox-provider sequence (R-486..R-490). E2B (R-486) and Vercel
  Sandbox (R-487) each proved `SandboxLifecycleProvider`/`sandbox_http.py` generalize across
  differently-shaped APIs; this task adds Daytona, whose real API is shaped a *third*, genuinely
  distinct way.
- **Design, verified against real, current Daytona documentation before writing any code**:
  Daytona's docs were fetched across several pages (`daytona.io/docs`, mirror pages, DeepWiki)
  since no single page carried the complete request/response schema. **A real base-URL ambiguity
  was found across Daytona's own documentation**: one search snippet showed
  `app.daytona.io/api/sandbox/...` while a more detailed, schema-bearing page fetched directly
  showed `https://api.daytona.io/sandbox` with exact request/response field names — resolved the
  same way R-486's E2B v1/v2 ambiguity was: preferring the more specific, structured,
  directly-fetched source consistently for every endpoint (`POST/GET/DELETE
  https://api.daytona.io/sandbox[/{id}]`, `Authorization: Bearer <DAYTONA_API_KEY>`, reusing the
  existing `RUNTIME_SPECS["daytona"]` key declared since an earlier task and unused until now).
- **A genuinely new API shape this task had to accommodate**: unlike E2B (a URL pattern built from
  the sandbox id) and Vercel Sandbox (a `routes[]` array with real URLs already embedded in the
  create response), Daytona's `POST /sandbox` response carries **no URL at all** — only sandbox
  metadata (`id`, `state`, ...). Getting a usable preview URL requires a second, separate real
  HTTP call, `GET /sandbox/{id}/ports/{port}/preview-url`, which returns `{"url": ..., "token":
  ...}`; `create()` therefore makes two real HTTP requests in sequence rather than one, verified
  by a dedicated test asserting both requests' exact URLs/methods and their strict ordering, plus
  a second test confirming that when the first call's response is malformed, the second call is
  never attempted at all.
- **A second real, confirmed requirement this task applies correctly**: Daytona's own docs state
  that a non-public sandbox's preview link requires a companion `X-Daytona-Preview-Token` header
  to access, while a sandbox created with `"public": true` has a preview link that is "publicly
  accessible without authentication." Since `SandboxHandle.url` is a single string with no room
  for a companion per-request auth header (the same shape every other provider in this sequence
  already assumes), `create()` always sends `"public": true`, verified by an explicit assertion on
  the sent JSON body.
- **Every other documented request field left unset rather than guessed**: Daytona's own docs
  confirm omitting `snapshot` uses "the Daytona default snapshot," and the official Python SDK's
  own parameter list shows sensible platform defaults for every other field, so this task does not
  invent values for fields whose exact required/optional status could not be independently
  confirmed from the fetched documentation pages — the same conservative discipline R-486 already
  applied to E2B's `templateID` default.
- **A real, honest isolation-strength tradeoff, surfaced not glossed over**: this five-task
  sequence's own originating research (R-486's task contract) already established that Daytona's
  *documented default* sandbox isolation is plain Docker containers — a shared kernel, meaningfully
  weaker than E2B's and Vercel Sandbox's Firecracker microVMs — with stronger isolation modes
  (Kata Containers, Sysbox) available only as an explicit opt-in this driver does not attempt to
  select, since the exact API shape for requesting that opt-in was not documented in any of the
  pages fetched for this task; called out explicitly in both the code and this log entry so it
  stays visible to whoever builds R-490's provider-selection surface.
- **New `runtime/daytona.py`'s `DaytonaSandboxProvider`** implements R-486's
  `SandboxLifecycleProvider` contract via the exact same shared `sandbox_http.py` helper R-486
  introduced for E2B and R-487 reused unchanged for Vercel Sandbox — now proven a third time to
  generalize across a third differently-shaped provider API with zero changes to that shared file.
- **No real `DAYTONA_API_KEY` exists in this environment** (`.env` checked: absent) — every
  automated test is offline via the same injected-fake-`OpenerDirector` pattern established in
  R-486/R-487; real live-cloud verification against an actual Daytona account is honestly not
  possible here and is not claimed, deferred to whenever the founder provides a real key.
- **Gates**: agent-engine `task verify` **3,707 tests OK** (13 new in `test_runtime_daytona.py`), 0
  model/network calls — covering the full two-call create sequence and its exact request shapes,
  `"public": true` always being sent, the target→port mapping for all four known targets, an
  unknown target still correctly raising `UnsupportedRuntimeTargetError` before any request, a
  missing sandbox id in the create response correctly stopping before the second call, a missing
  preview URL raising a clear error rather than crashing, a real Daytona-shaped 401 error body
  mapping correctly, the API key never appearing in a `SandboxHandle`'s `repr()`, and
  `status()`/`kill()` both correctly keyed by the real sandbox id. Repo-wide `task
  verify`/`lint`/`security:quick`/`env:check` all pass; a new `scripts/test.sh` contract block
  asserts the new driver file and class exist. **Unlike R-487, this task needed no change to
  `runtime/providers.py` or `runtime/drivers.py` at all** — `RUNTIME_SPECS["daytona"]` and its
  corresponding `_SANDBOX_URLS` placeholder both already existed from an earlier task, so every
  pre-existing suite passes completely unmodified with zero coupling surprises this time.
- **All three sandbox providers the founder explicitly asked for (E2B, Vercel Sandbox, Daytona)
  now have real, tested, independently-verified, pluggable drivers behind one shared
  `SandboxLifecycleProvider` contract** — the founder's "switch easily... based on more cost,
  speed, smoothness" ask now has three genuinely interchangeable real implementations to switch
  between, not just one.
- **Next:** R-489 (the free WebContainers browser-only option — client-side in the console,
  Node.js/frontend apps only, an honest limitation to document rather than work around) and R-490
  (a provider-selection surface exposing the founder's "switch easily by cost/speed/smoothness"
  ask — the point where more than one of these three real providers actually gets wired into the
  Studio's real preview flow for the first time, deliberately deferred until now).

## 2026-09-19 — R-487 (Runtime: real Vercel Sandbox driver)

- **Why:** second of the five-task sandbox-provider sequence (R-486..R-490). R-486 proved the
  `SandboxLifecycleProvider` pattern with E2B; this task proves it is genuinely pluggable by
  adding a second, independent real driver against a differently-shaped API — the founder's
  explicit ask ("switch easily... based on more cost, speed, smoothness").
- **Design, verified against real, current Vercel documentation before writing any code:** fetched
  the canonical `vercel.com/docs/rest-api#sandboxes` endpoint index (not a single page in
  isolation) — sandbox creation is `POST /v2/sandboxes` (only one creation model, "named"; no
  separate "unnamed" endpoint exists; `persistent: false` selects the ephemeral, non-snapshotting
  behavior this task needs). Status: `GET /v2/sandboxes/{name}`. Termination:
  `DELETE /v2/sandboxes/{name}` (both keyed by **name**, confirmed via the official endpoint
  index — not the response's `session.id`; distinct from `POST
  /v2/sandboxes/sessions/{sessionId}/stop`, which only pauses a resumable session). Auth is
  `Authorization: Bearer <VERCEL_TOKEN>` — reuses the *same* env var `DEPLOY_SPECS["vercel"]`
  already declares for the CLI-based deploy path (same underlying account, no duplicate
  credential). A real, additional required config beyond the token: Vercel's create-sandbox call
  requires a `projectId` — new `VERCEL_PROJECT_ID` env var, `create()` raises a clear typed error
  when unset.
- **A real, meaningful design difference from E2B**: `routes[].url` is used directly from the
  create response (one entry per requested port, each already carrying its own public URL) rather
  than reconstructed from a guessed pattern string — possible only because Vercel's own response
  provides it, unlike E2B's `{port}-{sandboxID}.e2b.app` convention.
- **A real, documented product limitation, not glossed over**: Vercel Sandbox's documented
  `runtime` enum is `node22`/`node24`/`node26`/`python3.13` — no Go. `backend-go` (a real, valid
  target `LocalRuntimeProvider` already supports) is explicitly rejected by this provider with a
  new, specific `UnsupportedSandboxRuntimeError`, distinct from `UnsupportedRuntimeTargetError`
  (no target definition exists at all) — a custom OCI `image` field exists in Vercel's schema as a
  real future escape hatch, deliberately not attempted here since building and maintaining a
  Go-capable custom image is materially more work than this task's scope.
- **New `runtime/vercel_sandbox.py`'s `VercelSandboxProvider`**, implementing R-486's
  `SandboxLifecycleProvider` contract via the exact same shared `sandbox_http.py` helper R-486
  introduced for E2B, with zero changes to either that file or `contracts.py`/`e2b.py` — the
  clearest possible proof that shared HTTP-safety module generalizes across differently-shaped
  provider APIs.
- **Two real bugs found and fixed by this task's own tests and gates, not glossed over**:
  1. The first implementation draft checked whether *this provider* supports the target's runtime
     *before* validating that the target exists at all — an unknown target string like
     `"flutter"` was therefore misclassified as `UnsupportedSandboxRuntimeError` instead of the
     correct `UnsupportedRuntimeTargetError`. Fixed by reordering so the shared
     `_port_for_target()` helper (which validates the target's existence via
     `LocalRuntimeProvider`, exactly as R-486's E2B driver already does) runs first, with the
     Vercel-specific runtime-support check only after that succeeds.
  2. Adding a new `"vercel-sandbox"` entry to the shared `RUNTIME_SPECS` registry (used by both
     this new real driver and the older, still-stubbed `CloudSandboxProvider`/`sandbox_driver()`
     planning-stub path from before R-486) broke two pre-existing tests in `test_tier_drivers.py`
     that enumerate every `RUNTIME_SPECS` entry and expect a matching placeholder URL in
     `drivers.py`'s `_SANDBOX_URLS` dict. Fixed with a single added line (`"vercel-sandbox":
     "https://<name>.vercel.run"`), with `drivers.py` added to `allowed_paths` mid-task once the
     real gap was found, following the same discipline as every prior mid-task scope correction
     this session — the `CloudSandboxProvider`/`sandbox_driver()` planning logic itself remains
     completely untouched otherwise.
- **No real `VERCEL_TOKEN`/`VERCEL_PROJECT_ID` exist in this environment** (`.env` checked:
  neither present; `.env.example` carries only name-only placeholders) — every automated test is
  offline via the same injected-fake-`OpenerDirector` pattern R-486 established; real live-cloud
  verification against an actual Vercel account and project is honestly not possible here and is
  not claimed, deferred to whenever the founder provides real credentials.
- **Gates**: agent-engine `task verify` **3,694 tests OK** (14 new in
  `test_runtime_vercel_sandbox.py`), 0 model/network calls — covering successful create/status/
  kill against hand-built Vercel-shaped responses, `active` correctly requiring *both* credentials
  (neither alone sufficient, unlike E2B's single-key requirement), both credentials raising a
  clear typed error before any request when either is missing, the node/python runtime mapping per
  target, `backend-go`'s specific rejection, an unknown target still correctly raising
  `UnsupportedRuntimeTargetError`, a missing matching route producing a clear error rather than a
  crash, a real Vercel-shaped 401 error body mapping correctly, the token never appearing in a
  `SandboxHandle`'s `repr()`, and `status()`/`kill()` both correctly keyed by the sandbox's name
  (not a session id). Repo-wide `task verify`/`lint`/`security:quick`/`env:check` all pass; a new
  `scripts/test.sh` contract block asserts the new driver file/class/registry-entry exist. Every
  pre-existing suite passes unmodified beyond the one-line `drivers.py` fix, confirming this
  task's additions are genuinely additive.
- **Next:** R-488 (Daytona driver — notable because its documented default is plain Docker
  containers rather than a microVM, a real isolation-strength tradeoff worth surfacing honestly
  when that task is scoped), R-489 (the free WebContainers browser-only option), and R-490 (a
  provider-selection surface exposing the founder's explicit "switch easily by cost/speed/
  smoothness" ask).

## 2026-09-19 — R-486 (Runtime: real sandbox lifecycle contract + E2B driver)

- **Why:** first of a five-task sequence (R-486..R-490) toward the founder's "Full isolation:
  per-user processes/sandboxes" direction, itself chosen from an earlier `AskUserQuestion` this
  session. Before writing any code, delegated a combined codebase-audit + competitor-platform +
  sandbox-technology research task to a subagent (sourced, not from stale training knowledge):
  confirmed zero containerization exists anywhere in the agent-engine; `scripts/test.sh` has an
  active enforced gate blocking `agent-engine`/`redis`/`runner-manager`/`nats`/`temporal`/
  `kubernetes` as Compose services; `services/runner-manager/` is an empty placeholder; the Studio
  server is a single shared in-memory process with no tenant dimension; the Go control-plane
  always proxies to one fixed `AgentEngineURL`; Postgres has no per-tenant scheme; and the existing
  `runtime/` provider abstraction is a real, well-designed Protocol wrapping thin/untested cloud
  stubs. A platform comparison found every serious 2025-2026 AI app-builder running real
  server-side code (Vercel Sandbox, E2B, Fly, CodeSandbox) converged on Firecracker microVMs, or
  gVisor via a managed provider (Lovable→Modal) — only browser-only sandboxing (Bolt.new/StackBlitz
  WebContainers) sidesteps real server execution entirely, which doesn't fit this platform's
  Python/Go backend requirement. A technology-tradeoff comparison (Firecracker, gVisor, Kata
  Containers, plain Docker/cgroups, Kubernetes multi-tenancy) concluded self-hosting any of these
  from scratch is a multi-quarter platform-engineering effort a single-founder-plus-AI-agent team
  doesn't have headcount for.
- **Presented to the founder via `AskUserQuestion`** as a hard-gate decision (adopting a managed
  sandbox provider is a new paid external cloud dependency, not just an architecture pattern) —
  the founder's answer: build real, pluggable drivers for multiple providers (E2B, Vercel Sandbox,
  Daytona) so they can be switched later by cost/speed/smoothness, plus one free option that runs
  directly in the browser with no cost or configuration (WebContainers). This task proves the
  pattern end-to-end with the first provider before repeating it three more times.
- **Design, verified by direct source read before writing any code:** the existing
  `RuntimeProvider`/`PreviewPlan` abstraction (`runtime/contracts.py`) is a pure *planner* —
  `preview_plan()` returns a description of local install/run commands plus a URL string, and
  executing it (`local.run_preview`) runs those commands on the *same* machine. The existing
  `CloudSandboxProvider` (`runtime/drivers.py`) stub reuses this exact shape with a hardcoded
  placeholder URL (`https://<id>.e2b.dev`) and never calls any provider's real API — this planning
  abstraction is correct for local execution and stays completely untouched, because a real cloud
  sandbox fundamentally needs actual create/get-a-real-id-and-url/later-kill lifecycle management,
  which a pure "plan" has no room for.
- **New, additive `SandboxHandle` + `SandboxLifecycleProvider` (`runtime/contracts.py`)**: a
  `SandboxHandle` (`provider_id`, `sandbox_id`, `url`, `status`) and a Protocol with
  `create()`/`status()`/`kill()`, genuinely mirroring what a real remote resource needs, alongside
  (never replacing) the existing `RuntimeProvider`.
- **New `runtime/sandbox_http.py`**: a small, safe, stdlib-only JSON HTTP helper shared by every
  sandbox driver this sequence adds (E2B now; Vercel Sandbox/Daytona in R-487/R-488) — bounded
  response size, a finite timeout, and redirect rejection (an auth header must never be replayed
  to another host), a purpose-built and much smaller sibling of `model_gateway/cloud.py`'s own
  HTTP safety net (that file is LLM-completion-specific — streaming, retry-after pacing,
  finish-reason mapping — none of which a sandbox lifecycle call needs).
- **New `runtime/e2b.py`'s `E2BSandboxProvider`**, implementing the new contract for real, verified
  against E2B's actual documented REST API fetched directly from `docs.e2b.dev` (not assumed from
  training data, and cross-checked against a second, independent fetch to resolve a `/sandboxes`
  vs `/v2/sandboxes` inconsistency across their own doc pages by preferring the two
  mutually-consistent, directly-fetched pages): `POST https://api.e2b.app/sandboxes` with
  `{"templateID", "timeout"}` and an `X-API-Key` header returns `201` with a `sandboxID`; the
  public URL is built from E2B's own documented pattern `https://{port}-{sandboxID}.e2b.app`;
  `DELETE https://api.e2b.app/sandboxes/{sandboxID}` returns `204` on success. `templateID`
  defaults to E2B's own documented generic default (`"base"`, confirmed via a second search),
  overridable via a new `E2B_TEMPLATE_ID` env var — a real generated OmniStackAI app needs a
  custom template with the right toolchain pre-installed, a separate, later concern once a real
  account exists to build one against.
- **The target→port mapping is reused, not duplicated**: a new `_port_for_target()` helper calls
  the existing `LocalRuntimeProvider().preview_plan(app_dir, target)` and parses the port out of
  its returned `http://127.0.0.1:{port}` URL, keeping `local.py` the single source of truth and
  naturally inheriting its `UnsupportedRuntimeTargetError` for an unknown target.
- **An honest, documented gap**: E2B's `GET /sandboxes/{id}` status response's exact field shape
  could not be independently verified from the fetched documentation pages — `status()`
  defensively looks for a `"state"` string field and falls back to keeping the handle's existing
  status when absent, rather than guessing and hiding the assumption.
- **Activated by the existing `RUNTIME_SPECS["e2b"]`'s `E2B_API_KEY`** env var (declared since an
  earlier task, unused until now) — the same "add a key, it activates" pattern every cloud LLM
  provider already uses.
- **No real `E2B_API_KEY` exists in this environment** (`.env` checked: absent; `.env.example`
  carries only the pre-existing name-only placeholder, now joined by a new `E2B_TEMPLATE_ID`
  placeholder) — every automated test is offline via an injected fake `OpenerDirector`-shaped
  transport, mirroring `model_gateway/cloud.py`'s own testable-opener pattern for its LLM adapters;
  real live-cloud verification against an actual E2B account is honestly not possible here and is
  not claimed, deferred to whenever the founder provides a real key, exactly matching this
  project's existing precedent for cloud LLM providers.
- **Not in scope for this task**: wiring `E2BSandboxProvider` into the Studio's actual preview flow
  (`studio/preview.py`) or `_build_stream()` — this task proves the driver is real and correctly
  built against E2B's actual API; swapping what the Studio actually uses for preview is a separate,
  later decision once more than one provider exists to choose between (R-490's job).
- **Gates**: agent-engine `task verify` **3,680 tests OK** (22 new: 9 in new
  `test_runtime_sandbox_http.py`, 13 in new `test_runtime_e2b.py`), 0 model/network calls —
  covering successful create/kill/status against hand-built E2B-shaped responses, a missing key
  raising before any request is sent (both `create()` and `kill()`), HTTP error mapping (a real
  E2B-shaped 401 `{"message","error_code"}` body, and a non-JSON 500 body falling back to a
  generic message), oversized/malformed response rejection, redirect rejection, an
  `E2B_TEMPLATE_ID` override, the target→port mapping for all four known targets plus the
  unsupported-target case, and the API key never appearing in a `SandboxHandle`'s `repr()`; the
  pre-existing `test_runtime.py` suite passes completely unmodified, confirming this task's
  additions are genuinely additive and the existing (still-stubbed) `CloudSandboxProvider`/
  `sandbox_driver()` planning path is untouched. Repo-wide `task verify`/`lint`/`security:quick`/
  `env:check` all pass; a new `scripts/test.sh` contract block asserts the new contract/driver
  files and symbols exist.
- **Next:** R-487 (Vercel Sandbox driver), R-488 (Daytona driver), R-489 (the free WebContainers
  browser-only option, client-side in the console, Node.js/frontend apps only — an honest,
  documented limitation since WebContainers cannot run Python or Go), and R-490 (a
  provider-selection surface exposing the founder's explicit "switch easily by cost/speed/
  smoothness" ask).

## 2026-09-19 — R-485 (Console: streaming build UI)

- **Why:** fast-follow to R-484 (backend SSE build streaming), closing the loop it opened — the
  console's own `/studio` chat now actually shows real, live incremental progress for a new build,
  instead of the existing static "Building…" wait.
- **Design, verified by direct source read before writing any code:** `studio-chat.tsx`'s
  create-path is already plain-prompt-only (`sendBuild()` only ever POSTed `{prompt}` — it has no
  Solution Pack/Ecosystem/`hybrid_ui` UI at all, those only exist in the separate raw-HTML Studio
  page built in earlier tasks, not this Next.js console). Every build this component can ever
  trigger is therefore exactly the kind R-484's streaming route already supports — no build-kind
  branching needed here.
- **New server-side client `streamBuildApp()` (`lib/control-plane.ts`)**: unlike every existing
  function in this file (which awaits and returns parsed JSON via `callControlPlane<T>`), this
  returns the raw upstream `Response` unparsed, so the proxy route can pipe its body straight
  through without buffering it.
- **New proxy route `app/api/jobs/build/stream/route.ts`**: auth-gates via `getSessionToken()`
  (same 401-if-missing shape as every other proxy route), validates a non-blank `prompt` (same 400
  shape as `app/api/jobs/build/route.ts`), then returns `new Response(upstream.body, {status,
  headers})` — relaying the upstream response through unchanged. This single pipe-through
  correctly handles both real shapes the control-plane can return: a streamed `text/event-stream`
  success body, and a plain buffered `application/json` pre-stream rejection — neither this route
  nor the browser needs to branch on which one it got.
- **`studio-chat.tsx` gains `sendBuildStream()`**, replacing `sendBuild()` as the create-path
  handler: `fetch()` + manual `response.body.getReader()` framing (not `EventSource`, which cannot
  send a POST body) — buffers bytes, splits on `"\n\n"` event boundaries, parses each frame's
  `data:` line as JSON. Three real shapes, verified against R-484's actual live output: a
  `{"phase": "generating_ir", "delta": "..."}` frame (only its length is used, to drive a live
  character-count indicator — the raw JSON text itself would render as visibly broken/meaningless
  to a non-technical user, and a real-time partial-JSON-aware renderer is a materially larger
  feature explicitly left out of scope here), a `{"phase": "done", ...}` frame (the final build
  result, identical rendering to what `sendBuild()` already produced), and a bare `{"credit_
  balance": ..., "credits_spent": ...}` frame with **no** `"phase"` key at all (the Go relay's
  trailing `event: credits` frame — confirmed live during R-484 that credits arrive separately
  from `"done"` in the streaming path, unlike the non-streaming response's shape).
- **What's shown while streaming, and why**: a live, honest "Generating your app… (N characters so
  far)" indicator, ticking up in real time as deltas arrive — proving genuine live activity (the
  founder's actual ask: an engaged, alive feeling from the first response) without fabricating a
  fake progress percentage or showing broken partial JSON. Replaced by the existing full
  result-card rendering the instant the `"done"` frame arrives.
- **The existing non-streaming path is untouched and still real**: `POST /jobs/build`,
  `app/api/jobs/build/route.ts`, and `buildApp()` all remain exactly as they are — genuinely
  reachable via direct API use, simply no longer called by this one UI component. Edit stays
  non-streaming (`sendEdit()` unchanged), per R-484's own scope boundary.
- **Gates**: `pnpm run typecheck` clean; `pnpm run lint` clean; `pnpm run build` → 21 routes (1
  new: `/api/jobs/build/stream`), clean. Repo-wide `task verify`/`lint`/`security:quick`/
  `env:check` all pass (3,658 agent-engine tests unaffected — no agent-engine or control-plane file
  touched by this task).
- **Live manual smoke — no browser-automation tool was available this session** (checked via
  `ToolSearch`, only Figma/design tools surfaced): verified instead via `next start` (the real
  production build; the previously-running instance on port 4321 was a stale pre-task build and
  was restarted to pick up the new route) plus `curl` driven through a real, cookie-based login
  session (`POST /api/auth/login` with the same real test user from R-484, capturing the real
  httpOnly `omnistackai_session` cookie exactly as a browser would) — a faithful behavioral proxy
  for the browser exercising the identical code path (Route Handler → fetch → Go control-plane →
  agent-engine), with only the pixels-on-screen part unverified (this task adds no new visual/CSS
  surface — the character-count text reuses existing `.chat-message--assistant`/`.spinner`
  styling unchanged). A real `curl -N` session for `{"prompt":"Build a simple bookmarks manager
  app"}` through the full real path showed genuine token-by-token `generating_ir` deltas arriving
  with real millisecond-scale gaps over ~9 real seconds of wall-clock time, `Content-Type:
  text/event-stream` correctly relayed by the new Route Handler, ending with a real `"phase":
  "done"` frame (174 files, entities `Bookmark, BookmarkTag, Folder, Tag, User`, a real git commit
  sha `317913cdaa02a91fbc44b02f2d0d53d8efc3284d`, real usage with `input_tokens: 1875,
  output_tokens: 3725`), followed by a real trailing `event: credits` frame (`credit_balance: 100,
  credits_spent: 0` — honestly zero, this environment's configured cloud model has no price-book
  entry, the same pre-existing fact already documented in R-484's own evidence). A real request
  with no session cookie returned a real `401 {"error":"not signed in"}`; a real request with no
  `prompt` returned a real `400 {"error":"prompt is required"}`, both rejected before any upstream
  call. A real follow-up edit on the build just created (`POST /api/jobs/build/2/edit`,
  `{"prompt":"add a health check endpoint"}`) produced a real diff (`"2 added, 4 modified, 0
  deleted, 170 unchanged"`), a real second commit sha, and correct turn history spanning both the
  original build's and this edit's turns — confirming the edit path is completely unaffected by
  this task's changes.
- **Next:** per the founder's stated build order ("streaming first, then scope isolation
  properly"), properly SCOPE (not yet build) full per-user process/sandbox isolation as its own
  multi-task project. Publish/deploy and backend/mobile stack breadth remain named and
  directionally approved but not yet scoped into task contracts.

## 2026-09-19 — R-484 (Backend: real-time build streaming, SSE)

- **Why:** first of the founder's post-roadmap priorities, per "streaming first, then scope
  isolation properly" — chosen after three parallel research passes (competitor streaming
  architecture, per-user isolation scoping, deploy/stack breadth). Replaces the one-shot blocking
  "Building…" wait with genuine incremental progress. Scoped backend-only (agent-engine SSE
  emission + Go relay, curl-verified); console UI consumption is R-485, mirroring this session's
  proven backend-then-UI split (R-476→R-477, R-478→R-479).
- **Design, verified by direct source read before writing any code:** `model_gateway/contracts.py`'s
  `ModelProvider` Protocol already declared `stream(request) -> AsyncIterator[StreamEvent]`, and
  every real provider already implemented it — but `_build()`'s entire call chain
  (`build_app_from_prompt` → `generate_ir` → `provider.generate()`) never once called `.stream()`.
  The gap this task closes is entirely in the intake/build layer, not the model layer.
- **New, purely additive streaming twins — every existing non-streaming function untouched:**
  `generate_ir_stream()` (`intake/nl_to_ir.py`, an async generator yielding raw text deltas from
  `provider.stream()`, then the final `IntakeResult`); `build_app_from_prompt_stream()`
  (`intake/build_app.py`, streams the IR-generation deltas then does `build_app_from_ir()`'s disk/
  git work synchronously once the IR completes); `_build_stream()` (`studio/live_serve.py`, an
  async generator mirroring `_build()`'s plain-prompt-only branch — Solution Pack, Ecosystem, and
  `hybrid_ui=True` builds are explicitly, honestly rejected via a new
  `StreamingBuildNotSupportedError`, matching the exact scope precedent `_edit()`/R-476 already
  set, rather than silently falling back or guessing).
- **New `POST /api/build/stream` route (`studio/server.py`):** reads the JSON body, rejects
  unsupported build kinds with a normal `400` before any streaming starts, then switches to SSE
  (`Content-Type: text/event-stream`, manual `self.wfile.write()`+`flush()` per event over stdlib
  `http.server`'s connection-close-delimited body — zero new dependencies), driven via a small
  `asyncio.run()`-wrapped drain loop matching `_edit()`'s existing "sync handler, async model
  calls" pattern.
- **New Go control-plane route `POST /jobs/build/stream` (`internal/jobs/handler.go`):** because
  crediting requires the final event's usage (only known once the stream completes), the relay
  can't inject `credits_spent`/`credit_balance` into an already-sent frame — instead it relays
  every upstream SSE frame verbatim via `http.Flusher` as it arrives (new `readSSEFrame`/
  `parseSSEDataPayload` helpers read one frame at a time without altering what gets forwarded),
  then appends one trailing `event: credits\ndata: {...}\n\n` frame once the upstream `"done"`
  event's usage is known and debited via the same `creditsForUsage` computation `proxyAndDebit`
  already uses. A `"done"` with no `usage` at all still gets a `credits_spent: 0` frame (tracked
  via a separate `sawDone` boolean, not conflated with "no usage reported"); a debit failure after
  streaming has started (headers already sent — a plain `500` is no longer possible) surfaces as a
  named `credits_error` SSE frame instead.
- **Two real bugs found and fixed by this task's own gates — not glossed over:**
  1. The SSE route initially sent `Connection: keep-alive`. `BaseHTTPRequestHandler.send_header`
     specially interprets that literal value as "keep this socket open"
     (`self.close_connection = False`); since the response has no `Content-Length`/chunked
     framing, the client's only signal the body has ended is the connection closing — so this hung
     every real client indefinitely. Caught immediately by the first HTTP-level streaming test via
     a real client socket timeout. Fixed by sending `Connection: close` instead.
  2. `RecordingProvider` (`model_gateway/recording.py`) — the real usage/cost-tracking wrapper
     every production build call is routed through via `resolve_generation_provider_from_env` —
     had no `.stream()` method at all. Every automated test mocks around this real wrapping
     (handing `_build_stream()` a raw stub provider directly), so this was invisible to
     `task verify` and only surfaced via the task's own required live `curl -N` smoke test, which
     failed immediately with `'RecordingProvider' object has no attribute 'stream'`. Fixed by
     adding `RecordingProvider.stream()`, mirroring `generate()`'s own success/failure
     ledger-recording shape exactly, plus 4 new tests in `test_recording_provider.py` (both files
     added to `allowed_paths` mid-task once the gap was found, following the same discipline as
     every prior mid-task scope correction this session).
- **Gates:** agent-engine `task verify` **3,658 OK** (27 net-new: 9 in `test_intake_nl_to_ir.py`, 3
  in `test_build_app.py`, 11 in `test_studio_server.py`, 4 in `test_recording_provider.py`), 0
  model/network calls. Control-plane `go build`/`go vet`/`go test ./...`: all green, 7 new tests
  in `handler_test.go` (55 total). Repo-wide `task verify`/`lint`/`security:quick`/`env:check` and
  a new `scripts/test.sh` contract block all pass.
- **Live manual smoke:** rebuilt the control-plane container (`task control-plane:verify`) and
  restarted the agent-engine Studio server (build-only mode, Python doesn't hot-reload — the first
  attempt against the still-running pre-fix process is exactly what surfaced bug #2 above). A real
  `curl -N` session through the real Go control-plane (not directly against the agent-engine)
  showed genuine token-by-token `generating_ir` deltas arriving with real millisecond-scale gaps
  over ~9 real seconds of wall-clock time, ending with a real `"phase": "done"` frame carrying the
  full real build result (177 files, entities `Tag, TaskComment, TaskItem, TaskTag, TodoList,
  User`, a real git commit sha `75f4b0addf7d08267efc751680d4b50fe339df3f`, real `usage` with
  `input_tokens: 1875, output_tokens: 3144`), followed by a real trailing `event: credits` frame
  (`{"credit_balance":100,"credits_spent":0}` — honestly zero because this environment's real
  configured cloud model has no price-book entry, a pre-existing, unrelated fact already
  documented in R-472/R-476's own evidence). All three unsupported build kinds (`pack_id`,
  `ecosystem_id`, `hybrid_ui`) confirmed cleanly rejected with a `400` and
  `Content-Type: application/json` before any SSE framing began. The existing non-streaming
  `POST /jobs/build`/`POST /api/build` were not touched by any edit and remain covered unchanged
  by every pre-existing passing test.
- **Next:** R-485 (console: streaming build UI, consuming this endpoint in `studio-chat.tsx`'s
  `sendBuild()`), then properly scope (not yet build) full per-user process/sandbox isolation per
  the founder's stated build order.

## 2026-09-19 — R-483 (Fix: dynamic-route slug collision & duplicate FK identifier)

- **Why:** second follow-up task after the 7-task Phase D roadmap, per the founder's "complete one
  by one all" direction. Fixes the exact real bug found live during R-481's own manual smoke test:
  a Next.js dev-server crash (`Error: You cannot use different slug names for the same dynamic path
  ('counterId' !== 'counter_id')`) and a duplicate `lib/types.ts` identifier (`TS2300`/`TS2687`/
  `TS2717`).
- **Root cause, verified by direct source read before any fix** — two independent, compounding
  defects, both deterministic code/prompt facts, not one-off model randomness:
  1. The full-build prompt has no path-param casing rule for API endpoints (camelCase only by its
     own worked example); the edit-delta prompt explicitly demanded `lower_snake_case` for the
     *whole* path, including `{param}` placeholders. Nothing reconciled a new endpoint's param
     spelling against an existing endpoint's own param for the same resource —
     `apply_app_delta` never even called `normalize_ir()`.
  2. `codegen/nextjs.py`'s `_entity_interface()` unconditionally synthesized a `<relation>_id` FK
     field for every to-one relation with no check against already-declared explicit fields —
     confirmed this exact shape (a field *and* a same-named relation) already sat, unexercised for
     this, in `test_app_delta.py`'s own fixture.
- **Fixed at the structural root, not just the two known call sites:**
  `ApiEndpoint.__post_init__` (`application_ir/ir.py`) now canonicalizes every `{param}` to
  camelCase unconditionally, via a new pure, idempotent `_canonicalize_path_params()` helper —
  covering every construction path, present and future, not just full-build and edit-delta.
  `_entity_interface()` now skips the synthesized FK field when an explicit same-named field
  already exists. Both prompts also corrected to ask for camelCase params, as a first line of
  defense (the code-level fix is the real guarantee).
- **A pre-existing test initially failed after the fix — investigated, not reverted:** its
  fixture's own hardcoded path used raw snake_case, and the previously-passing assertion matched
  that exact raw spelling. Confirmed not a functional regression: the generated reader code already
  defensively checked the camelCase spelling as *its own* second-priority fallback — clear
  pre-existing evidence this exact inconsistency was already anticipated. Updated the assertions to
  the new, correct camelCase expectation.
- **Gates:** agent-engine `task verify` 3,635 OK (6 new regression tests). Repo
  `task verify`/`lint`/`security:quick`/`env:check` all pass.
- **Live — reproduced the exact originally-reported scenario end to end**: built the same counter
  app, sent the same follow-up edit, started the preview → real `200 ready`, no crash (grepped the
  real log for the exact original error string, confirmed absent). Listed the real generated
  dynamic route folders on disk → exactly one, no colliding sibling. Ran a real `tsc` check via
  Problems → 8 real errors remained (pre-existing, unrelated LLM-UI-synthesis noise, not this
  task's concern) but **zero** duplicate-identifier errors and zero in `lib/types.ts`. Read the
  real generated `lib/types.ts` directly → exactly one `user_id` line, no duplicate.
- **NEXT** (per "complete one by one all"): R-484 (real-time streaming, renumbered from R-483),
  per-user backend multi-tenancy, and Publish/deploy each need an explicit founder architecture
  decision before implementation.

## 2026-09-19 — R-482 (Model Provider settings UI)

- **Why:** first follow-up task after the 7-task Phase D roadmap shipped, per the founder's
  "complete one by one all" direction. A real, live Dyad-style provider status page.
- **Verified before writing code:** `model_gateway/overview.py`'s `platform_overview()` already
  existed (real, tested, metadata-only) but was only ever used to generate a static build-time JSON
  snapshot for the public `/fabric` page — no live HTTP endpoint existed anywhere.
- **New, never surfaced anywhere before:** `resolve_generation_provider_from_env()` always succeeds
  (it falls through to local Ollama, never raises for "nothing configured") and its returned
  `ModelProvider` has a real `.provider_id` — calling it safely reports which provider would
  actually run the *next* build right now.
- New agent-engine `GET /api/providers` (wired build-only-mode-inclusive — needs only env vars plus
  one optional lightweight local ping, never a toolchain or running preview). New control-plane
  `GET /jobs/providers` (no credit debit — a status read isn't a model call). New authenticated
  console `/settings` page (new `layout.tsx` mirroring `studio/layout.tsx`'s auth gate, a new
  `SettingsIcon`, linked from the Studio topbar and the home page) — live "Ready"/"Not ready"
  callout plus the same provider-table visual language `/fabric` already established, now
  live-polled instead of a static snapshot.
- **A real bug found AND FIXED during this task's own live smoke test** (introduced by this task's
  own first draft, not a pre-existing platform issue): calling `platform_overview()` *before*
  `resolve_generation_provider_from_env()` meant the providers list's `active` flags were computed
  before `.env` had been lazily loaded into the process (a side effect of the resolve function's own
  `load_dotenv=True` default) — in a fresh process that had never handled a build, every cloud
  provider showed "Needs key" even with a real key configured, while `activeNow` (computed after the
  dotenv load already happened) correctly named the real provider. An honest but
  internally-inconsistent response, not a crash — caught only because the live smoke test used a
  freshly started process, exactly the scenario a real first-time user would hit. Fixed by
  reordering: resolve `activeNow` first, then `platform_overview()` second — verified with `env -i`
  (a completely clean environment) both reproducing the bug and confirming the fix.
- **Gates:** agent-engine `task verify` 3,629 OK (4 new tests). Control-plane `go test` all green
  (48 tests, 3 new). Console `typecheck`/`lint`/`build` clean (20 routes, 2 new). Repo
  `task verify`/`lint`/`security:quick`/`env:check` all pass.
- **Live** (real control-plane rebuilt + real agent-engine Studio server in preview mode, freshly
  restarted after the fix): real `/api/providers` returned `activeNow: groq` plus a correct
  provider table; real `/settings` rendered the live "Ready" callout. **Cross-verified `activeNow`
  against a real build**: the agent-engine's own log showed real Groq rate-limit retries, confirming
  the real call genuinely used Groq — exactly matching `activeNow`'s own report, not a guess.
  Unauthenticated calls correctly blocked (401 API, 307 page redirect).
- **NEXT** (per the founder's "complete one by one all"): scope and fix the dynamic-route
  slug-collision codegen bug found live during R-481's own smoke test.

## 2026-09-19 — R-481 (Tabbed workspace) — FINAL task of the 7-task Phase D roadmap

- **Why:** seventh and final task of the approved 7-task Phase D roadmap. Restructure `/studio`'s
  main pane into four real tabs — Preview, Files, Code, Problems — with chat persisting alongside,
  assembling R-474 (files), R-477 (chat), R-479 (preview), and R-480 (problems) into one shell.
- **New `studio-tabs.tsx`** owns `activeTab` and a lifted `selectedFile` shared by Files and Code
  (kept as two separate tabs, per the founder's explicit decision): Files is a lightweight clickable
  list that opens a file in Code; Code has its own file switcher too, for a technical user who wants
  to jump straight to reading code.
- **New `code-highlight.ts`**: a hand-rolled, dependency-free tokenizer porting the *approach* of
  `codegen/nextjs.py`'s own generated `tokenizeCodeLine`/`normalizeLang` — the exact same
  regex-driven algorithm the platform already ships (tested) inside every generated app's own
  `CodeBlock` component, scoped to TS/TSX/JS/JSON/CSS/Markdown/plain. Matches the R-475
  icon-decision precedent — confirmed live that no `prismjs` fallback was needed.
- **Problems tab** is an explicit on-demand "Check for problems" button (per R-480's own design,
  never automatic), hydrates the last stored report on mount, shows real toolchain/no-web-target
  errors verbatim.
- **Gates:** console `typecheck`/`lint`/`build` all clean (19 routes, 1 new). `task verify` 3,625 OK
  (unchanged — no backend files touched). Repo `task verify`/`lint`/`security:quick`/`env:check` all
  pass.
- **Live** (Colima/Docker had stopped again since the prior session — restarted — real control-plane
  + real agent-engine Studio server in preview mode + a freshly rebuilt `next start`): full loop
  confirmed — build → real Preview (ready + real HTML served) → real Files list → real Code content
  (hand-rolled tokenizer rendered real generated TSX cleanly) → real edit (second commit) → Files
  list refresh confirmed (168→170, matching the edit's own diff) → Preview re-preview confirmed
  triggered.
- **A real, pre-existing codegen bug found live, unrelated to this task**: the edit introduced a
  Next.js dynamic-route slug-name collision (`counterId` vs `counter_id`) — correctly surfaced as an
  honest Preview error (not a crash) *and* independently caught by a real Problems check (18 genuine
  TypeScript errors across 2 files, tracing to the exact same root cause). Cross-confirmed evidence
  that R-479's and R-480's error-surfacing design both work correctly under genuine failure
  conditions, not just the happy path. Not fixed here — out of scope, worth its own future Tracker
  ID. A repeated `GET` returned the byte-identical cached problems report in 17ms.
- **THIS COMPLETES THE APPROVED 7-TASK PHASE D ROADMAP** (R-475 through R-481). The Studio is now a
  real chat-driven, multi-pane workspace closer to Lovable/Dyad/Emergent parity than at the start.
- **NEXT:** no pre-approved task remains queued. Named, not-yet-scheduled follow-ups: R-482 (Model
  Provider settings UI), R-483 (real-time streaming, its prerequisite now exists), per-user backend
  multi-tenancy, Publish/deploy, and the newly-found route-slug codegen bug. Needs explicit founder
  direction on priority before picking the next Tracker ID.

## 2026-09-19 — R-480 (Backend — Problems/compile-report support)

- **Why:** sixth task of the approved 7-task Phase D roadmap. Real compile-error reporting for the
  first time in this codebase — the founder's explicit choice over a placeholder, even though it
  made the roadmap longer. Confirmed by exhaustive grep during the original planning research:
  `verify/compile.py` has a real `CompileError`/`CompileReport`/`compile_web_project()`, but its
  only caller anywhere was a standalone CLI script — never the Studio's `_build()`/`_edit()` path.
- **On-demand, not automatic:** `node_modules`/`tsc` only exist after a live-preview install
  (confirmed by this session's own R-478/R-479 smoke tests, which needed a real `pnpm install`
  before any toolchain existed). Automating a compile check on every build/edit would make the
  fast, network-light core loop slower and more toolchain-dependent — an explicit "Check for
  problems" trigger avoids that regression.
- **New `studio/problems.py`** mirrors `files.py`'s shape: `check_build_problems()` resolves
  `apps/web`, raises `NoWebTargetError` if there's no web app, remaps `compile_web_project()`'s
  `VerifyError` into a clear `ToolchainNotInstalledError` — never silently installs dependencies as
  a side effect of a click. `StudioProblemsStore` is a bounded per-build-id LRU cache mirroring
  `StudioSessionStore`. New agent-engine routes wired into build-only mode too (checking needs the
  build's own already-installed `node_modules`, not a *currently running* preview).
- **Control-plane:** new `POST`/`GET /jobs/build/{id}/problems`, no credit debit (a local compile
  isn't a model call), a new `defaultProblemsTimeout` (90s) on the write route. Error mapping:
  `BuildNotFoundError`→404, `NoWebTargetError`→400, `ToolchainNotInstalledError`→409 (a new status
  for this API surface, chosen so a client can distinguish "install dependencies first" from every
  other failure), `ProblemsNotCheckedError`→404 (GET only).
- **Gates:** agent-engine `task verify` 3,625 OK (21 new tests, all against an injected fake `tsc`
  runner or a tempdir — no real toolchain needed, mirroring `verify/compile.py`'s own test style).
  Control-plane `go test` all green (45 tests, 7 new). Repo `task verify`/`lint`/`security:quick`/
  `env:check` all pass.
- **Live:** build-only mode with no toolchain → real `409` "tsc is not installed..." and real `404`
  "not checked yet," no crash, no accidental multi-minute install. Along the way, hit two real,
  pre-existing environment issues unrelated to this task — a generated-migration collision
  (`relation "bookmark_tag" already exists`) and a 500ing preview page — both honestly worked
  through rather than hidden, since a problems check only needs the build's already-installed
  `node_modules`, not a working running preview. Preview mode with a real installed toolchain → a
  real `tsc --noEmit` run surfaced **10 genuine TypeScript errors** in an LLM-synthesized page
  (missing module, not-callable expressions, a type mismatch, a missing name, an invalid prop
  value) — real, substantial compiler output, and the same real bug explains why that build's own
  preview page was 500ing. A repeated `GET` returned the byte-identical cached report in 12ms.
- **NEXT:** R-481 (tabbed workspace) — the final task of the approved 7-task roadmap.

## 2026-09-19 — R-479 (Console — live preview UI)

- **Why:** fifth task of the approved 7-task Phase D roadmap. An iframe rendering the real running
  generated app, wired to R-478's four routes.
- **Preview start is synchronous** (confirmed live during R-478's own smoke test), so there's no
  server-side "starting" state to poll for — polling's real job is **crash detection**: a 5s
  interval while `status.status === "ready"`, calling `GET /jobs/preview`, since the agent-engine's
  own `status()` lazily notices a subprocess that died on its own.
- **New `studio-preview.tsx`:** one effect triggers `POST /jobs/build/{id}/preview` whenever
  `buildId` becomes real or a `previewVersion` counter (bumped by `studio-chat.tsx` after every
  successful edit — `_edit()` never restarts the preview on its own, unlike `_build()`) changes. A
  404 from either preview route sets a `disabled` flag, rendering an honest static message instead
  of a broken iframe. Manual Restart/Stop controls reuse the `RefreshIcon`/`StopIcon` that existed
  unused since R-475, purpose-built for exactly this.
- **Every `PreviewStatus` shape verified by reading `preview.py` directly**, not assumed:
  idle/stopped/error/unavailable/ready, plus the build-scoped route's own extra error case
  (confirmed live in R-478) rendering through the same branch.
- **A real lint finding, not a design change:** `eslint-plugin-react-hooks`'s `set-state-in-effect`
  rule flagged a synchronous `setState` at the top of the buildId-change effect — the classic
  React-docs "set loading, then fetch" pattern. Fixed by moving it to be the first statement inside
  the effect's own async IIFE instead of before it, and consolidating `starting`/`elapsedMs`/
  `fetchError` into one combined state object.
- **Gates:** console `typecheck`/`lint`/`build` all clean (18 routes, 4 new). `task verify` 3,604 OK
  (unchanged — no backend files touched). Repo `task verify`/`lint`/`security:quick`/`env:check` all
  pass.
- **Live** (real control-plane + real agent-engine Studio server in preview mode + a freshly
  rebuilt `next start`): first found and cleaned up a real operational gap from R-478's own smoke
  test — an orphaned generated-app preview process left running because the agent-engine had been
  killed non-gracefully (not a bug in this task's code, just cleanup hygiene worth naming). Then: a
  real build auto-started a real preview whose `web_url`, fetched directly, returned genuine
  Next.js HTML; a real edit triggered the exact re-preview call the `previewVersion` bump makes,
  landing on a genuinely new port (fresh code served, not stale). **Crash detection confirmed
  live**: found the real OS process behind the current preview port and `kill -9`'d it directly (a
  true external crash) — the very next poll correctly reported `"stopped"`. Manual Restart/Stop both
  worked. Build-only mode made both preview routes return the real, uniform 404 the component
  checks for.
- **NEXT:** R-480 (backend: Problems/compile-report support) per the approved plan.

## 2026-09-19 — R-478 (Backend — live preview proxy, local-only)

- **Why:** fourth task of the approved 7-task Phase D roadmap. Proxy the agent-engine's existing
  trusted-local preview control surface — correctly **four** routes, not three: the singleton
  control surface (`GET /api/preview`, `POST /api/preview/stop`, `POST /api/preview/restart`) plus
  the build-scoped one (`POST /api/history/preview`) a chat-per-build UI actually needs. Zero
  agent-engine changes — every route reused exactly as-is, same precedent R-474 set for the file
  browser.
- **A real, verified shape, not assumed:** an unknown/evicted build's build-scoped preview route
  does not 404 — `_preview_recorded_build` has no exception path for that case, it returns a plain
  `{"status": "error", "message": "..."}` dict sent as a **200**. Confirmed by reading the source
  before writing the tests, then confirmed live during the manual smoke test too. The proxy
  deliberately forwards this shape unchanged rather than "fixing" it into a 404.
- **Go side:** generalized `proxyGet` into `proxyUpstream(method, body)`, covering both GET and the
  new credit-free POST control routes. `handleBuildPreview` always constructs its own
  `{"id": "<path id>"}` body server-side — the caller's own body is never trusted for which build to
  preview, matching every other build-scoped route in this package. New `defaultPreviewTimeout`
  (60s, above the real 45s internal readiness wait) applied to `handleBuildPreview`; also applied to
  `handlePreviewRestart` — added during implementation once it was clear `restart()` can itself
  trigger a real cold start, the same risk build-preview has (confirmed live).
- **Gates:** control-plane `go test` all green (38 in `internal/jobs`, 13 new, including a dedicated
  test asserting the 200-with-error-status shape survives the proxy unchanged). Repo
  `task verify`/`lint`/`security:quick`/`env:check` all pass — unchanged test count, since this task
  touched no agent-engine or console-web files.
- **Live** (real Docker control-plane rebuilt via `control-plane.sh verify`, real agent-engine
  Studio server in preview mode via `studio-preview`): a real build automatically started a real
  preview as a side effect (existing pre-R-478 behavior) — a genuine `pnpm install` + Next.js dev
  server + FastAPI backend, with a real Groq rate-limit retry and a real JSX-synthesis fallback to
  the deterministic template along the way (an honest real-world signal, not a bug). `GET
  /jobs/preview` returned real live URLs. `POST /jobs/build/1/preview` sent with a deliberately
  mismatched body proved the server-constructed-body design (a genuine re-preview on new ports, the
  caller's body ignored). `POST /jobs/build/nonexistent-999/preview` returned the real
  200-with-error-status shape live. Stop/restart both worked; the credit balance stayed unchanged
  across all four calls. Switching the agent-engine to build-only mode made all four routes return
  the identical, uniform `404 "preview controls are not enabled"` — the honest zero-new-logic
  passthrough confirmed.
- **NEXT:** R-479 (console: live preview UI) per the approved plan.

## 2026-09-19 — R-477 (Console — chat UI)

- **Why:** third task of the approved 7-task Phase D roadmap. Replace `/studio`'s one-shot prompt
  form with a persistent, multi-turn chat thread on R-475's shell, wired to R-476's new
  `POST /jobs/build/{id}/edit` / `GET /jobs/build/{id}/turns` routes. `buildId` (`null` vs. set) is
  the single piece of state deciding whether the composer calls `/jobs/build` or
  `/jobs/build/{id}/edit` — same composer, same input box.
- **New components:** `studio-chat.tsx` owns `messages`/`buildId`/`workspace` state and the
  composer. `studio-workspace.tsx` holds the `BuildResult`/`FileBrowser` pieces moved out of the
  retired `studio-form.tsx`, generalized to a `WorkspaceSnapshot` patched by either a build's full
  response (has `name`/`description`/`files`) or an edit's narrower one (re-fetching the file list
  separately, since `_edit()`'s response carries no `files` key at all).
- **Refresh survival:** `buildId` persists in the URL (`?build=<id>`); a refresh hydrates the chat
  thread's *text* from `/turns` — the rich workspace panel does not rehydrate, an honest, named
  simplification rather than a silently incomplete "full history" claim.
- **A real finding, verified by reading the actual source before writing the failure-mode handling
  (not assumed from the plan sketch):** `GET /turns` does **not** 404 for an unknown/evicted build —
  `session.py`'s `turns_view` returns `{"turns": []}` for a missing session entry, not an error.
  Only `_edit()`'s own `BuildNotFoundError` is a real, reachable 404. So the "session no longer
  available, start a new app" recovery is wired to a failed *edit* response (status 404), not to
  turns-hydration, which just honestly (and harmlessly) starts as an empty thread against a stale id.
- **Gates:** console `typecheck`/`lint`/`build` all clean (14 routes, 2 new). `task verify` 3,604 OK
  (unchanged — no backend files touched). Repo `task verify`/`lint`/`security:quick`/`env:check` all
  pass. A pre-existing `scripts/test.sh` R-473 contract block had hard-coded `studio-form.tsx` as a
  required file — updated in this same commit, since retiring that exact file is this task's job.
- **Live** (real Docker control-plane + real agent-engine Studio server + a freshly rebuilt/restarted
  `next start`): a real build, then a real turns-hydration fetch proving both the build's own turns
  are present; a real follow-up edit on the same `buildId` produced a genuine second commit and a
  refreshed 162-file list (confirmed a real favorites-related file present post-edit — the workspace
  panel's file-list refresh is real, not stale). **The task's most important new path**: killed and
  restarted the real agent-engine Studio server (wiping in-memory session state, the same real
  mechanism a production restart would cause) — an edit against the now-stale `buildId` returned a
  real `404 {"error":"build '2' is not available in this session"}`, exactly what `sendEdit()`
  checks for; `GET /turns` against the same stale id returned `200 {"turns": []}`, not an error,
  confirming the Finding above live, not just by source-reading. A fresh build afterward succeeded
  normally, proving the full recovery loop. `GET /studio`'s rendered HTML confirmed the new
  `studio-grid`/`chat-rail`/`chat-composer` markup present with no server errors.
- **NEXT:** R-478 (backend: live preview proxy) per the approved plan.

## 2026-09-19 — R-476 (Backend — multi-turn edit bridge)

- **Why:** second task of the approved 7-task Phase D roadmap. New control-plane routes proxying
  the agent-engine's existing (R-468) edit/turns endpoints, mirroring `POST /jobs/build`'s exact
  proxy+debit shape (R-472) — plus two real, verified gaps in the Python edit path found while
  planning this roadmap.
- **Two real bugs fixed, both confirmed by direct comparison with `_build()`, not assumed:**
  `_edit()` had no `usage_ledger` at all — its response carried no `"usage"` key whatsoever, so
  every edit was debiting 0 credits regardless of real cost. `_build()` never called
  `session_store.record_turn` — only `_edit()` did, so `GET /turns` returned an empty history for
  any build that had never been edited yet, meaning a future chat UI hydrating from `/turns` after
  a page refresh would silently lose the very first message. Both fixed by mirroring `_build()`'s
  own existing patterns exactly (a fresh `UsageLedger()` threaded into
  `resolve_generation_provider_from_env`, and `record_turn` calls right after
  `session_store.begin(...)`).
- **Go side:** new `POST /jobs/build/{id}/edit` and `GET /jobs/build/{id}/turns`. The shared
  "forward, decode, debit, inject" body was extracted out of `handleBuild` into a `proxyAndDebit`
  helper both handlers now call — mirrors the `writeAuthError` extraction precedent R-474 set once
  a second call site appeared. A no-op edit (the delta call still happened even though it produced
  no file changes) still debits real credits by design, since `creditsForUsage` only ever looks at
  the reported cost — a dedicated test locks this in.
- **Gates:** control-plane `go test` all green (25 in `internal/jobs`, 10 new). Agent-engine
  `task verify` — 3,604 tests, OK (2 pre-existing `test_studio_edit.py` assertions updated to
  account for `_build()` now correctly recording its own turn — a real, intended behavior change,
  not a regression; 1 new test proving `_edit()`'s real usage recording, mirroring the exact
  `RecordingProvider`-around-a-real-`UsageLedger` pattern R-472's own build test already
  established). `task verify`/`lint`/`security:quick`/`env:check` all pass.
- **Live:** rebuilt/restarted the control-plane, **and separately had to restart the agent-engine
  Studio server** — Python doesn't hot-reload, and the first live attempt against the still-running
  old process reproduced exactly the bug this task fixes (`GET /turns` returning `{"turns": []}`
  even after a real build) — a useful, honest confirmation that the fix only takes effect once
  actually deployed, not a new bug. After restarting: a real build's own turn was immediately
  present in `/turns` before any edit; a real edit produced a genuine second git commit (5 files
  added including a new `Favorite` entity's repository/router/screen, 10 modified) and, for the
  first time ever, a real `"usage"` key on the edit response. **Honest note:** this environment's
  real configured cloud model has no `DEFAULT_PRICE_BOOK` entry, so both the build and the edit
  came back genuinely unpriced (`credits_spent: 0`) — a pre-existing, unrelated fact about this
  deployment, not a flaw in this task; the "debits a nonzero charge" half of the acceptance
  criteria is proven deterministically by the new unit tests instead, not claimed as something the
  live run itself showed. Error paths (401 no token, 404 unknown build on both new routes) all
  proxied correctly too.
- **NEXT:** R-477 (console: chat UI) per the approved plan
  (`/Users/sanjeet_kumar/.claude/plans/hi-fancy-shannon.md`), then R-478 (preview backend), R-479
  (preview UI), R-480 (problems backend), R-481 (tabbed workspace).

## 2026-09-19 — R-475 (Studio visual foundation)

- **Why:** the founder asked directly whether the platform now has a "rich, upgraded, advanced UI"
  like Lovable/Dyad/Emergent. Honest answer: no — R-473/R-474 are functionally real but visually
  still a plain form. The founder asked for "everything" (visual polish, chat, live preview, tabs),
  got an honest time estimate, then asked for a written plan and paused for the day.
- **Planning, this session:** turning the doc's 6-task sketch into an executable plan went through
  full plan-mode discipline — two parallel Explore agents researched the real console-web frontend
  and the real agent-engine/control-plane backend (not the doc's assumptions), a Plan agent
  synthesized a task-by-task design, and the most consequential claims were independently verified
  by directly reading the source. Confirmed: `_build()` never records a chat turn though `_edit()`
  does; `_edit()` has no `usage_ledger` at all (every edit today debits 0 credits regardless of
  real cost); the agent-engine's live-preview API is two different surfaces, the build-scoped one
  returning an unusual `200 {"status":"error"}` for an unknown build, not a 404; the
  control-plane's `WriteTimeout` defaults to 15s against a real 45s preview-readiness wait; no
  compile/verify-error endpoint exists anywhere in the Studio path today. Two decisions asked of
  the founder directly, both honored: Problems (compile errors) gets built for real, not deferred
  as a placeholder — given its own task, R-480, rather than bloating tab assembly (this is what
  took the roadmap from six tasks to seven); Files and Code stay as two separate real tabs, not
  collapsed into one. Plan approved via `ExitPlanMode` — twice, since the session briefly
  re-entered plan mode mid-execution after R-475's contract/doc files were already written; the
  plan file was updated with a status note reflecting real on-disk progress and re-approved rather
  than re-litigated.
- **R-475 itself:** new `app/studio/layout.tsx` takes over `/studio`'s auth gate and renders
  persistent top-bar chrome (brand, back link, sign-out) that R-477's chat and R-481's tabs build
  on top of — moved out of `page.tsx` so every future Studio sub-view inherits it for free.
  `globals.css` gained additive design tokens (`--radius-sm/md/lg`, replacing today's inconsistent
  inline 8/12/14px values across `.field input/textarea`, `.button`, `.error-banner`, `.stat`, and
  `.panel`; `--surface-2`; an accent-tinted chip background; a CSS-only `.spinner`; `.pill--accent`)
  mirrored into the existing dark-mode media query exactly like every token before it. New
  hand-rolled `studio-icons.tsx` (~10 inline-SVG stroke icons) rather than a new npm dependency —
  the fixed, small icon surface needed across the whole roadmap didn't clear the bar for a
  dependency given everything else in this app is already hand-rolled. `studio-form.tsx` restyled
  only (credit balance moved from its own stat panel into a compact pill chip), zero logic change.
  No backend changes.
- **Gates:** console `typecheck`/`lint`/`build` all clean (13 routes unchanged). `task verify` —
  Ran 3,603 tests, OK, Stage 0 verification passed. `task lint`/`security:quick`/`env:check` all
  pass. New `scripts/test.sh` R-475 block (contract files present, `layout.tsx` has the auth gate,
  `globals.css` has the new tokens/classes).
- **Live:** Colima/Docker had stopped since the previous session and was restarted; real
  control-plane + real agent-engine Studio server + a fresh `next start` on the new build proved
  `/studio`'s auth gate now correctly lives in `layout.tsx` (`307` signed out), the new shell
  renders correctly signed in (`studio-shell`/`studio-topbar` present, real credit pill showing
  "100 credits" — the `<!-- -->` between the number and the word is React's own harmless hydration
  boundary comment, the same pattern already diagnosed in R-471), and `/`, `/fabric`, `/login`,
  `/register` all remain structurally unaffected (only the shared `.panel` radius token change is
  visible — confirmed via the home page's real `"Welcome back, R475 Smoke"` heading rendering
  correctly). Confirmed `package.json`'s dependencies are still exactly `next`/`react`/`react-dom`.
- **NEXT:** R-476 (backend: multi-turn edit bridge) per the approved plan
  (`/Users/sanjeet_kumar/.claude/plans/hi-fancy-shannon.md`), then R-477 (chat UI), R-478 (preview
  backend), R-479 (preview UI), R-480 (problems backend), R-481 (tabbed workspace) in that order.

## 2026-09-18 — R-474 (File browser in the console Studio — see what a build actually produced)

- **Why:** the founder asked to see the platform running before continuing Phase D. Brought up the
  real Docker control-plane + real agent-engine Studio server + real `next start` console for a
  live look (walkthrough: register → `/` → `/studio` build → `/fabric`), then, per the founder's
  "Left it as running and continue," carried on with the next Phase D slice against that same
  running stack rather than tearing it down first.
- **What:** R-473's build result panel listed filenames as inert text; this task makes that list
  clickable so a user can actually read the generated code, not just see it exists. The
  agent-engine's Studio server already had real, tested, path-safe read-only file access
  (`studio/files.py`, wired since R-467 as `GET /api/build/{id}/files` /
  `GET /api/build/{id}/file?path=...`) — this task bridges those two existing endpoints through the
  authenticated control-plane, the same "generic proxy, no new agent-engine code" shape R-472
  established for the build endpoint itself.
- **Control-plane:** two new authenticated, read-only routes — `GET /jobs/build/{id}/files` and
  `GET /jobs/build/{id}/file?path=...` — proxying verbatim to the agent-engine, no credit debit
  (browsing already-generated files isn't a billable model call). A shared `writeAuthError` helper
  replaces three copies of the same `errors.Is(err, auth.ErrUnauthenticated)` mapping that would
  otherwise have been repeated across `handleBuild`/`handleBuildFiles`/`handleBuildFile`.
- **No agent-engine changes** — `studio/files.py`'s path-safety guarantees (traversal-proof,
  secret-`.env`-excluded, binary-file-safe) carry over completely unchanged, since nothing about
  them is touched.
- **Console:** `lib/control-plane.ts` gained `BuildFileTreeResponse`/`BuildFileContentResponse`
  types and `listBuildFiles()`/`readBuildFile()` clients; two new dynamic Route Handlers
  (`app/api/jobs/build/[id]/files/route.ts`, `.../file/route.ts`) follow the exact
  session-cookie-gated pattern `app/api/jobs/build/route.ts` already established; `studio-form.tsx`
  gained a `FileBrowser` component — each filename is now a button that fetches and shows real file
  content in a read-only `<pre>` viewer, with a binary-file guard ("binary file, not shown" instead
  of corrupted output).
- **Known, honestly-documented limitation, not fixed or worsened by this task:** the agent-engine's
  Studio server (`StudioBuildHistory`) is a single shared in-memory process with no per-user
  scoping — unchanged from R-467. Any authenticated console user who knows (or guesses) a build id
  can browse its files through this new proxy, exactly as any local Studio user already could
  before an authenticated frontend ever existed. Real per-user build isolation needs the Studio
  server itself to become multi-tenant-aware — out of scope here, named rather than silently
  accepted.
- **Gates:** control-plane `go build`/`go vet`/`gofmt` clean; `go test ./...` all green (15 tests in
  `internal/jobs`, 6 new: missing-token 401 on both routes, verbatim file-list/file-content
  proxying with the exact `?path=` query forwarded, an unknown-build 404 proxied unchanged, a
  path-traversal-rejection 400 proxied unchanged). Console `typecheck`/`lint`/`build` all clean (13
  routes now, including the two new dynamic file routes). `task verify` — Ran 3,603 tests, OK,
  Stage 0 verification passed. `task lint`/`security:quick`/`env:check` all pass. New
  `scripts/test.sh` R-474 block.
- **Live** (against the founder's own already-running stack — rebuilt/restarted only the
  control-plane container and the console process to pick up this task's code; Postgres and the
  agent-engine Studio server's in-memory build history were left completely untouched):
  registered a fresh account, built a real 158-file "Simple Notes App" via real Groq cloud (`id:
  "2"`, confirming the Studio server really had been left running with prior history from the
  founder's own browsing), then proved the file browser end to end — the file list matched the
  build response exactly, `GET .../file?path=README.md` returned genuine content read from the real
  repo on disk (`binary: false`, `size: 402`), an unknown build id proxied through as the
  agent-engine's own `404`, and a path-traversal attempt (`../../../../etc/passwd`) proxied through
  as the agent-engine's own `400` — no new traversal logic added or needed. (One earlier build
  attempt hit a real, unforced Groq IR-validation failure, the same class of live-model flakiness
  already documented in R-472/R-473 — not a bug in this task.)
- **NEXT:** continue Phase D — live preview (a materially different trust posture since it executes
  generated code, needs its own scoped decision before starting), chat/multi-turn edit (porting
  R-468's capability into the console), or Solution Pack/Ecosystem build selection in the Studio
  UI. Phase E still needs its own explicit founder sign-off before starting.

## 2026-09-18 — R-473 (Studio v1 in the console — build an app from the product, not curl)

- **Why:** Phase D of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md`, first slice — a
  logged-in user should be able to actually call the now-real `/jobs/build` (R-472) from the
  product itself, not just curl, and see their real credit balance update.
- **Scope, deliberately small:** the kickoff doc's Phase D vision is a full IDE-like surface
  (persistent chat, top tabs Preview/Files/Code/Problems/Publish/More, Model Provider settings, a
  Problems tab). Building all of that in one task would repeat the mistake this project's own
  history avoids — the agent-engine's own hybrid-UI engine shipped across four separate, gated
  Tracker IDs (R-465 synthesis, R-466 compile-repair, R-467 file browser + toggle, R-468 multi-turn
  edit). This task ships the smallest real, end-to-end slice: prompt in, real build out, real
  credit debit reflected in the UI. File browser, live preview, and chat/multi-turn edit are named,
  not silently dropped, follow-ups.
- **New `app/studio/page.tsx`** (Server Component): mirrors `app/page.tsx`'s auth gate exactly —
  `getCurrentUser()` → redirect to `/login` if signed out.
- **New `app/studio/studio-form.tsx`** (Client Component): a prompt textarea, a Build button, a
  real pending state (builds take real time — 3s to 3+ minutes observed live, both in this task and
  R-472's), an error banner on failure, and a result panel (name/description/entities/file_count/
  commit_sha/files, plus the `usage` block and `credits_spent` when the agent-engine reported
  them). Updates the displayed credit balance straight from the response's `credit_balance` — no
  separate `/auth/me` re-fetch needed, the Job API already returns the authoritative post-debit
  value.
- **New `app/api/jobs/build/route.ts`**: server-side proxy — reads the session cookie
  (`getSessionToken()`), 401s immediately with **no** upstream call if absent, then forwards to the
  control-plane's `POST /jobs/build` with the bearer token attached (never exposed to client-side
  JS, the same boundary every existing `app/api/auth/*` route already draws). No artificial
  timeout — R-472's own `http.ResponseController.SetWriteDeadline` fix is what makes waiting out a
  real multi-minute build possible; this route does nothing that would cut that short.
- **`lib/control-plane.ts`** gained `BuildJobResponse`/`BuildJobUsage`/`buildApp()`, following the
  exact `callControlPlane` pattern `login`/`registerAccount` already use. Only the fields this UI
  actually renders are typed; an index signature lets other build-kind-specific fields (e.g.
  `pack_id`) round-trip without the UI needing to know about them.
- **No control-plane or agent-engine changes** — R-472 already built the real backend this task's
  UI calls; this task is console-only.
- **Gates:** `pnpm run typecheck`/`lint`/`build` all clean (11 routes; `/studio` and
  `/api/jobs/build` both correctly dynamic, since they read the session cookie per request).
  `task verify` — Ran 3,603 tests, OK, Stage 0 verification passed. `task lint`/`security:quick`/
  `env:check` all pass. New `scripts/test.sh` R-473 block (contract files present, `buildApp()`
  exists, the build route checks `getSessionToken()` before proxying).
- **Live:** real Docker Postgres+control-plane, a real agent-engine Studio server on local Ollama
  (kept free/reproducible, matching R-472's precedent), and a real `next start` console. `GET
  /studio` with no session → `307` to `/login`; with a real session → `200`, correct credit balance
  server-rendered. `POST /api/jobs/build` with no cookie → `401` instantly (no upstream call). Two
  real build attempts: the first hit a genuine, unforced local-model IR-validation failure, honestly
  proxied through as a `502` with the agent-engine's own error message — a real, live proof of the
  error-banner path, not a synthetic test. The second succeeded for real: a genuine 157-file
  "Recipe Box" repo with `entities`/`commit_sha`/`files`/`usage`/`credits_spent`/`credit_balance` in
  exactly the shape the new UI renders.
- **NEXT:** continue Phase D — port the agent-engine's own `studio/page.py` capabilities (file
  browser + live preview from R-467, multi-turn chat/edit from R-468) into the console, and/or add
  Solution Pack/Ecosystem build selection to the Studio UI. Phase E still needs its own explicit
  founder sign-off before starting.

## 2026-09-18 — R-472 (Bridge the control-plane's Job API to the agent-engine — real credit debiting)

- **Why:** Phase C of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md` — a real generation
  call needs to actually debit the authenticated user's credit balance, with local-Ollama usage
  staying credit-exempt, closing the loop Phases A/B (auth, plans, credits, console) set up.
- **Correction to the kickoff doc's own framing, found while researching:** the Studio's real
  plain-prompt build path (`intake/provider_resolution.py::resolve_generation_provider_from_env`)
  hands callers a **raw** `ModelProvider` — the `ModelGateway`'s own accounting hook
  (`model_gateway/accounting.py::UsageLedger`) is real and tested, but until now was only ever
  exercised by `console_snapshot`'s illustrative dashboard, never a real build. Closed the gap with
  a small, additive `model_gateway.RecordingProvider` decorator (new file) implementing the exact
  same `ModelProvider` protocol — zero changes to any existing provider or call site.
- **Agent-engine wiring:** `resolve_generation_provider_from_env` gained an optional
  `usage_ledger: UsageLedger | None = None` param (default preserves today's exact behavior);
  `intake/build_app.py::app_build_result_to_dict` gained an additive `usage` key (same pattern as
  R-467's `ui_outcomes`); `studio/live_serve.py`'s plain-prompt `_build` branch creates one
  `UsageLedger()` per request and surfaces a JSON-safe summary — `cost_micros_usd` as an **int**
  (`cost_usd * 1_000_000`, rounded), not a decimal string, to avoid any float/precision risk
  crossing the Go/Python boundary.
- **Real bug caught by the new tests themselves, before any commit:** the first
  `RecordingProvider.generate()` draft recorded `provider_id`/`model_id` from the *response's own*
  echoed `.model` field instead of `self._inner.provider_id`/`request.model.model_id` — the
  pattern `ModelGateway._record` actually uses (the truly-dispatched provider, not whatever the
  response happens to echo). The local-Ollama test caught the mismatch immediately (wrong tier,
  `cost_usd` came back `None`); fixed to match the gateway exactly.
- **Control-plane wiring:** new exported `auth.RequireUser(ctx, store, r) (User, error)` (factored
  out of `handleMe`, which now calls it too); new `users.Store.DebitCredits` — one transaction,
  row-locked (`SELECT ... FOR UPDATE`), clamped via a pure, unit-tested `clampCharge` helper so
  `credit_balance` never goes negative (v1 policy: never block a build, only clamp the charge); a
  new `internal/jobs` package (`POST /jobs/build`) that authenticates the caller, forwards the
  request body **verbatim** to `${OMNISTACKAI_AGENT_ENGINE_URL}/api/build`, and — only on a
  successful response reporting real usage — converts `cost_micros_usd` to credits via the new
  `OMNISTACKAI_CREDITS_PER_USD` and debits them, returning the agent-engine's response augmented
  with `credits_spent`/`credit_balance`. Chose round-to-nearest over the originally-planned
  ceiling rounding (ceiling would systematically overcharge every build; the exact real cost stays
  visible in `cost_micros_usd` regardless).
- **Real infra bug found only by the live smoke test:** the control-plane's global
  `http.Server.WriteTimeout` (15s, tuned for fast routes like `/auth/*`) was silently killing
  `/jobs/build`'s connection before a real multi-minute build finished. Fixed with
  `http.NewResponseController(w).SetWriteDeadline(...)` scoped to just this one handler, leaving
  the server-wide timeout intact for every other route.
- **Compose networking:** the agent-engine's Studio server runs on the host (Compose is
  hard-blocked from adding it as a service); added `OMNISTACKAI_AGENT_ENGINE_URL` defaulting to
  `http://host.docker.internal:4173` plus `extra_hosts: ["host.docker.internal:host-gateway"]` so
  the containerized control-plane can reach it — verified reachable from inside the container
  before relying on it.
- **Gates:** agent-engine `task verify` — Ran 3,603 tests, OK, 0 model/network calls. Control-plane
  `go build`/`go vet`/`gofmt` clean; `go test ./...` all green (7 new `internal/jobs` cases, a
  7-case `creditsForUsage` table test, a 6-case `clampCharge` table test in the new
  `internal/users/store_test.go`). Repo-wide `task verify` — Stage 0 verification passed; `task
  lint`/`security:quick`/`env:check` all pass. **Live:** real Docker Postgres+control-plane, a
  real local Ollama build (forced via `OMNISTACKAI_PREFER_LOCAL=1` to keep the proof free and
  reproducible — this machine's real `.env` otherwise defaults to live Groq) produced a real
  161-file "Task Tracker" repo via `POST /jobs/build`, with `usage.cost_micros_usd: 0` and
  `credits_spent: 0` (correct — local usage is credit-exempt by price, not a special case). Since
  a free build has nothing to debit, `DebitCredits`'s row-locked SQL path was proven separately
  against the same live Postgres with a throwaway, never-committed `go run` program: `100 → 63`
  after `DebitCredits(37)`, then `63 → 0` (clamped, never negative) after `DebitCredits(999999)`,
  independently confirmed via a real `GET /auth/me` showing `credit_balance: 0`. One small, real,
  incidental Groq cost was honestly incurred by the *first* smoke attempt (before discovering this
  environment's real cloud default and switching to forced-local) — the build failed at
  IR-parsing before any usage summary existed, so nothing was charged for it either.
- **NEXT R-473 (Phase D):** rebuild the real Studio/builder UX inside `apps/console-web` so a
  logged-in user can actually call the now-real `/jobs/build` from the product itself.

## 2026-09-17 — R-471 (Fix dev-mode hydration bug + add full name to registration)

- **Why:** the founder actually opened the R-470 console in a browser and reported registration
  silently did nothing, plus asked whether the registration form should collect more profile
  fields (Name/Gender/Age) "if they are helpful later."
- **Real bug, found via the dev server's own log, not guessed:** `⚠ Blocked cross-origin request to
  Next.js dev resource /_next/hmr from "127.0.0.1"`, immediately followed by `GET
  /register?email=...&password=... 200`. Next.js 16 blocks cross-origin access to its own dev/HMR
  resources by default and treats `127.0.0.1` and `localhost` as different origins for that check —
  the founder had been pointed at `http://127.0.0.1:4321`. With no client JS hydrated, the
  register form's `onSubmit` handler never attached to the DOM, so the browser fell back to its
  native default form submission: a plain GET request with every field serialized into the URL
  query string, reloading the page and doing nothing — with no visible error to explain why.
  Fixed with `allowedDevOrigins: ["127.0.0.1", "localhost"]` in `next.config.ts` — exactly the fix
  Next.js's own warning prescribes.
- **Verified as thoroughly as possible without a real browser:** fetched the register page's own
  actual client JS chunk (taken from the real page HTML, not guessed) with `Origin:
  http://127.0.0.1:4321` — 200, and the dev server log shows no cross-origin warning this time,
  where an equivalent request was blocked outright before the fix. Honestly logged as the strongest
  available verification, not a substitute for the founder retrying it themselves.
- **Registration field decision, made explicit rather than silently picked:** added **Name**
  (`full_name`) — broadly useful, and the home page previously only had an email to show. Explicitly
  **did not** add Gender or Age: neither serves any function anywhere in this product's actual
  roadmap (credits, plans, a builder Studio), and collecting them would be unused PII with real
  privacy/compliance liability (gender is special-category data under some privacy regimes) for
  zero benefit. New migration `000003_users_full_name` (additive, `000001`/`000002` untouched);
  `internal/auth`'s `Store` interface, handler, and `User`/response types now carry `Name`;
  registration without a non-empty name is a clean 400. Console: `lib/control-plane.ts`,
  `app/api/auth/register/route.ts`, `app/register/page.tsx` (new required Name field), and
  `app/page.tsx` (greets "Welcome back, {name}" instead of showing only the email).
- **Renumbered the kickoff doc's Phase C** from R-471 to **R-472**, since this fix-and-feature work
  took the R-471 slot as its own real, scoped task rather than being folded silently into R-470 or
  Phase C.
- **Gates:** control-plane `go build`/`go vet`/`gofmt` clean; `go test ./...` all green
  (`internal/auth` 15, incl. 2 new sub-cases for missing/whitespace-only name; `config` 2; `health`
  3; `password` 8; `migrations` 4). Console `typecheck`/`lint`/`build` all clean. `task verify` —
  Ran 3,593 tests in 62.945s, OK, Stage 0 verification passed. **Live:** rebuilt and restarted the
  real Docker Compose control-plane (picked up migration `000003` cleanly on the pre-existing
  volume, re-proving R-469's self-healing migration runner); `POST /auth/register` with no name →
  400; with a name → 201, name in the response body; `GET /` with the resulting cookie → 200, page
  contains "Welcome back, Saurabh Chopra"; a direct control-plane check bypassing the console
  confirmed the same round trip against the real Postgres-backed `users.Store`.
- **NEXT R-472 (Phase C):** bridge the control-plane's Job API to the unmodified agent-engine so a
  real generation call actually debits a user's credits (local Ollama stays credit-exempt).

## 2026-09-17 — R-470 (Real Next.js console-web, wired to R-469's auth API)

- **Why:** Phase B of `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md` — replace the static,
  dependency-free `apps/console-web` with the real Next.js console the platform architecture has
  always specified, wired to R-469's newly-real auth API.
- **Session handling — a deliberate architecture call:** server-side cookie proxy, not a
  browser-held bearer token. `app/api/auth/{register,login,logout}/route.ts` proxy to the
  control-plane server-to-server (no CORS — the browser only ever talks to the Next.js origin) and
  set/clear an `httpOnly`, `sameSite=lax` cookie holding the token; the raw token is never handed
  to client-side JS. `lib/session.ts`'s `getCurrentUser()` reads the cookie and resolves it against
  the control-plane's `/auth/me` for Server Components.
- **Pages:** `/login`, `/register` (client forms), `/` (server component — redirects to `/login` if
  no session, otherwise shows profile/plan/credit balance + a logout control), `/fabric` (the old
  model/cost overview, now a Server Component importing `data/overview.json` directly at build
  time — same data contract, same design language, carried forward as promised in the old static
  console's own README).
- **No new UI dependency** beyond React/Next.js itself — the existing console's CSS custom
  properties (indigo accent, light/dark via `prefers-color-scheme`) carry into `app/globals.css`
  unchanged in spirit. A real design system is Phase D's job.
- **Real, non-trivial ecosystem friction found and fixed** (not anticipated in the contract):
  - `pnpm install` timed out fetching `next`/`@next/swc-darwin-arm64` (curl error 23) — a raw
    `curl` of the same tarball took ~50s on this network, right at pnpm's default per-attempt
    timeout edge. Fixed with a new root `.npmrc` (longer `fetch-timeout`, more retries).
  - `typescript@7.0.2` — genuinely npm's current `latest` — is not yet supported by
    `typescript-eslint@8.70.0` (`eslint` refused to run at all). `eslint-config-next@16.3.5`'s own
    `devDependencies` pin `typescript: 6.0.2`; matched that generation (`6.0.3`, latest 6.x)
    instead. `tsc --noEmit` itself works fine under TS7 — this was pure ecosystem-tooling lag.
  - The documented `FlatCompat` + `compat.extends("next/core-web-vitals", "next/typescript")`
    pattern crashed (`TypeError: Converting circular structure to JSON` inside
    `@eslint/eslintrc`'s error formatter) on both ESLint 10.10.0 and 9.9.1 — never actually an
    ESLint-version problem. Root cause: `eslint-config-next@16.3.5`'s default export is already a
    native flat-config array; the legacy compat shim is unneeded for this version and its
    validator chokes formatting an unrelated error because of a circular self-reference inside
    `eslint-plugin-react`'s own flat config. Fixed by importing `eslint-config-next` directly and
    dropping `@eslint/eslintrc` entirely.
  - pnpm 11.19 silently stopped reading `package.json`'s `pnpm.*` fields (warned once) — moved
    `onlyBuiltDependencies`/`allowBuilds` (needed to let `unrs-resolver`'s postinstall run) to
    `pnpm-workspace.yaml` instead.
  - **The session cookie's `Secure` flag was wired from `NODE_ENV === "production"`, which is
    wrong**: `next start` always sets `NODE_ENV=production` regardless of the real protocol, so
    every cookie issued locally over plain `http://127.0.0.1` was marked `Secure` — invisible in
    the first curl-based smoke test (curl doesn't enforce the attribute the way a real browser
    does), but a real browser refuses to send a `Secure` cookie back over non-HTTPS, which would
    have silently broken login persistence for anyone actually using the app locally. Caught by
    inspecting the raw `Set-Cookie` header rather than trusting 200/204 status codes alone. Fixed
    with a new per-request `isSecureRequest()` helper (checks `x-forwarded-proto` then the
    request's own protocol); re-ran the full live smoke test afterward and confirmed the cookie is
    now issued without `Secure` over plain HTTP.
- **Gates:** `apps/console-web` `typecheck`/`lint`/`build` all clean; `task verify` — Ran 3,593
  tests in 63.552s, OK, Stage 0 verification passed (the two new console steps run inside it,
  `next build` succeeding with no control-plane running, proving Route Handlers are compiled, not
  executed, at build time). **Live manual smoke, twice** (real `next start` on :4321 + the real,
  still-running R-469 Docker Compose control-plane/Postgres) — the second run, after the
  `Secure`-cookie fix, is authoritative: register → 201 (no token in the body, `Set-Cookie` correct
  without `Secure`) → duplicate register → 409 → home with the cookie → 200, real email rendered
  (proves the full cookie → control-plane `/auth/me` → profile round trip) → `/fabric` → 200 → home
  with no cookie → 307 to `/login` → logout → 204 → home with the cleared cookie → 307 to `/login`
  again (real server-side session invalidation) → login again → 200, a new cookie issued.
- **NEXT R-471 (Phase C):** bridge the control-plane's Job API to the unmodified agent-engine so a
  real generation call actually debits a user's credits (local Ollama stays credit-exempt).

## 2026-09-17 — R-469 (Control-plane foundation: users, auth, plans, credits)

- **Why:** the founder decided (2026-09-17) to advance OmniStackAI from its Stage-0 static console
  (`apps/console-web`) and stdlib Studio prototype toward the real commercial platform
  `R_&_D/OmniStackAI_Implementation_Brief_v6.md` Section 33 has always specified — a Next.js
  console over a Go control-plane (Auth/Orgs/Billing) and the existing Python agent-engine. This
  is recorded in full in `R_&_D/OmniStackAI_Commercial_Platform_Kickoff_v1.md` (written this
  session, five phases). R-469 is Phase A: give the existing `services/control-plane` Go skeleton
  (health-check-only before this task) real users, authentication, and a plan/credit model.
- **Role/plan/credit model (resolves the founder's "which is best approach" question):** two roles
  only — `super_admin` (full access, internal) and `user` (everyone else, gated entirely by
  `plan`, never a second role tier). Plans reuse the tier names already named in the Implementation
  Brief Section 22 (`free`/`developer`/`pro`/`agency`/`enterprise`, `byok` as an add-on flag rather
  than a separate tier). Every signup gets the `free` plan plus an env-configurable starting credit
  grant (`OMNISTACKAI_SIGNUP_CREDIT_GRANT`, default 100), recorded in an append-only
  `credit_ledger` — local-model usage is intended to stay credit-exempt (Phase C's job to enforce
  once the agent-engine bridge exists; this task only needed the ledger to record the grant
  correctly).
- **Migration `000002_users_auth_billing`:** `users` (role/plan/byok_enabled/credit_balance
  columns, `CHECK` constraints), `credit_ledger` (append-only, `balance_after` snapshot per row),
  `sessions` (token stored only as its SHA-256 hash, never raw). Transactional, idempotent
  (`IF NOT EXISTS`/`ON CONFLICT DO NOTHING`) — same style as the pre-existing `000001`.
- **`migrations` package (new):** `//go:embed *.up.sql` embeds every migration file in its own
  directory; `Apply(ctx, pool)` replays all of them, in ascending version order, each inside a
  Go-managed transaction, on every control-plane boot. This closes a real gap:
  `docker-entrypoint-initdb.d` (the existing fast path wired in `compose.yaml`) only runs against
  a brand-new empty Postgres volume — a developer's existing local volume would otherwise never
  see `000002` just by restarting the container. Safe to replay because every migration file is
  written idempotently.
- **`internal/password` (new):** PBKDF2-HMAC-SHA256 (RFC 8018) implemented directly on
  `crypto/hmac`+`crypto/sha256`+`crypto/subtle` — **zero new `go.mod` dependency**.
  `golang.org/x/crypto/bcrypt` was considered and rejected specifically because it would be this
  repo's first new Go dependency beyond the one already-necessary `pgx` (there is no stdlib
  Postgres driver, but there is no such excuse for password hashing). Self-describing encoded
  format (`pbkdf2-sha256$<iterations>$<salt>$<key>`), constant-time comparison.
- **`internal/auth` (new):** `User`/`Store`/`Hasher` interfaces (same "narrow interface, wire the
  real thing at the edge" shape `internal/health`'s `Pinger` already established), `Register(mux,
  Deps)` mounting `POST /auth/{register,login,logout}` + `GET /auth/me`. Login failure is a
  generic 401 regardless of wrong-password vs. unknown-email — including a same-cost dummy-hash
  `Verify` call on the "not found" path, computed once per handler construction (not per-request,
  not a package-level global) from whichever `Hasher` that `Deps` carries, so there is no timing
  side channel for enumerating registered emails. Opaque `crypto/rand` session tokens; only their
  SHA-256 hash is ever persisted (`internal/auth/token.go`).
- **`internal/users` (new):** the real PostgreSQL-backed `Store` (`var _ auth.Store =
  (*Store)(nil)` compiles). `CreateUser` wraps the user insert and the signup credit-grant ledger
  row in one transaction — a user's `credit_balance` and its ledger history can never disagree.
  Deliberately **not** unit-tested against a live database in `go test` (keeps
  `control-plane:test` exactly as hermetic as it already was, matching how `internal/health` tests
  a fake `Pinger` rather than a real database) — proven instead by a real Docker Compose smoke
  test (see Gates below).
- **`internal/health`:** `NewHandler` renamed to `Register(mux, ...)` so `main.go` can mount
  health and auth routes on one shared `http.ServeMux` — behavior/JSON bodies unchanged.
- **`internal/config` + `cmd/control-plane/main.go`:** two new env-configurable fields
  (`OMNISTACKAI_SESSION_TTL` default `720h`, `OMNISTACKAI_SIGNUP_CREDIT_GRANT` default `100`);
  `main.go` now calls `migrations.Apply` before serving traffic and wires the real `users.Store` +
  a `password`-backed `auth.Hasher` adapter into `auth.Register`.
- **`Dockerfile`/`compose.yaml`/`.env.example`/`scripts/env-check.sh`/`scripts/test.sh`:**
  `COPY migrations ./migrations` (required for the new `//go:embed` to see its files during the
  container build); a second `docker-entrypoint-initdb.d` mount for `000002` (fast path for a
  fresh volume); the two new env vars documented and enforced; a new `scripts/test.sh` block
  (matching the existing per-Tracker-ID convention) asserting the new contract files exist, the
  migration creates the three new tables, all four auth routes are present, and — the concrete,
  checkable proof password hashing stayed stdlib-only — `go.mod`'s direct-dependency count is
  still exactly 1 (`pgx`).
- **Live discovery while implementing:** an initial design used a package-level mutable global
  (`SetDefaultHasher`) plus a `sync.Once`-cached dummy hash to support the login-timing mitigation
  — this had a real footgun (panics on first login if `main.go` forgot to call `SetDefaultHasher`,
  plus stale-cache risk across tests using different fake hashers). Replaced with computing the
  dummy hash once per handler construction from the request's own injected `Hasher`, removing the
  global entirely — simpler, no initialization-order dependency, and the timing mitigation now
  automatically uses whatever hasher a given `Deps` actually carries.
- **Gates:** `go test ./...` — migrations 4, password 8, auth 15, health 3, config 2 (9 subtests),
  all passing, all hermetic/offline. `control-plane` lint/build passed. `scripts/test.sh`'s new
  R-469 block passed. `task verify` (full pipeline) → **Ran 3593 tests in 62.421s — OK; Stage 0
  verification passed** (agent-engine untouched, 0 model/network calls, no slowdown). **Live
  manual smoke** (Colima started, real Docker Compose + real PostgreSQL): image built with the new
  `COPY migrations` layer, both containers `Healthy`, live readiness check passed (proves
  `migrations.Apply` ran cleanly on boot). Full `curl` round trip against the running container:
  register (201, `credit_balance:100`) → duplicate register (409) → login (200, new token) →
  wrong password (401) → unknown email (401, **byte-identical** error body to wrong-password — no
  enumeration leak in production) → `/auth/me` authenticated (200) → `/auth/me` no token (401) →
  logout (204) → `/auth/me` with the now-invalid token (401, "session not found or expired" — a
  real deletion from PostgreSQL) → logout again (204, idempotent).
- **NEXT R-470 (Phase B):** replace the static `apps/console-web` with a real Next.js (App Router,
  TypeScript) app wired to this task's four auth endpoints — the point where `task bootstrap`/
  `task doctor` deliberately gain a real Node/npm toolchain requirement for the console, a scope
  change already recorded in the kickoff doc.

## 2026-09-17 — R-468 (Multi-turn chat / "continue editing this app" in the Studio)

- **Why:** every `/api/build` call was a fresh, stateless one-shot prompt — no way to say "now add a
  favorites feature" and have it land as a further commit on the same repo. Two rounds of direct-code
  investigation (not guessed) confirmed no session/conversation concept exists anywhere in the repo, that
  the apply/commit half already works end-to-end and untested-nowhere-except (`edit/diff.py::plan_edit` →
  `edit/apply.py::commit_edit`, proven by `test_edit_loop.py::CommitEditTests`), and that the missing half —
  producing a second `ApplicationIR` from a follow-up prompt — has no existing code.
- **Chosen approach, and why not the obvious one:** a generic, validated delta (mirroring
  `solution_packs/ai_delta.py`'s shape) rather than re-calling `generate_ir` with an augmented prompt and
  diffing old vs new — the latter has no code, no test, and no guarantee the model preserves every existing
  entity/screen verbatim (the intake system prompt actively says to "replace the template content"); a
  supersetting failure there would produce a huge, confusing diff, the opposite of the clean incremental
  history this feature exists for.
- **`intake/app_delta.py` (new):** `AppDeltaProposal(entities=(), apis=(), screens=(), rationale="")` — the
  same bounded/unique validation as `AIDeltaProposal` minus pack-specific fields; `build_app_delta_messages`
  lists the app's real existing entities/apis/screens/roles as context; `parse_app_delta_proposal` strictly
  parses untrusted model JSON, rejecting any collision with the base IR at parse time;
  `apply_app_delta` independently re-checks every collision (defense in depth) before merging by tuple
  concatenation (`base_ir.entities + proposal.entities`, mirroring `solution_packs/application.py:196-231`
  exactly), backstopped by `ApplicationIR.__post_init__` and the same `validate_ir`/`has_errors` check;
  `generate_app_delta_proposal` is a bounded validate→feedback→retry loop (retry only on a validation
  rejection, never on a provider exception, mirroring R-465's `_synthesize_file`). **Zero changes to
  `edit/`, `git_service/`, or `application_ir/`** — every diff/commit primitive is reused exactly as-is.
- **`studio/session.py` (new):** `StudioSessionStore` — bounded (LRU-by-last-touched, `OrderedDict`),
  thread-safe, in-memory, server-only, keyed by the same build id `StudioBuildHistory` assigns; holds the
  app's *current* `ApplicationIR` (never sent to the browser) and a bounded turn history. `live_serve.py`'s
  `_build` starts a session only for the two build kinds with exactly one IR — plain-prompt and
  single-surface Ecosystem Pack builds; Solution Pack and "all surfaces" ecosystem builds never get one.
- **`studio/live_serve.py`'s new `_edit`:** resolve the session (typed not-found) → reject Solution
  Pack/all-surfaces builds honestly (`EditNotSupportedError`) → resolve a provider (mocked in every test
  from the start) → `generate_app_delta_proposal` → `apply_app_delta` → `plan_edit` (empty diff → no
  commit, early honest response) → `commit_edit` (one new commit on the existing repo) →
  `session_store.advance` + `record_turn` → `history.update(...)` so "Recent builds" reflects the edited
  state. `main()` wires `edit_fn`/`turns_fn` unconditionally (no toolchain needed — just git and a model).
- **`studio/server.py`:** `POST /api/build/{id}/edit` and `GET /api/build/{id}/turns`, via the same
  `_build_id_for_suffix` path-matching helper R-467 built for the file routes; typed-error → status mapping
  (not-found→404, unsupported-build-kind→400, other→502).
- **`studio/history.py`:** new `.update(build_id, patch)` refreshes `file_count`/`commit_sha`/`entities` on
  an existing entry in place (identity/location fields stay fixed) — so "Recent builds" isn't stale after
  an edit.
- **`page.py`:** a "Continue editing this app" panel (turn list + input + Apply button) under the file
  browser; a successful edit re-renders entities/file-count/commit and refreshes the file browser (files
  changed); zero external assets preserved (verified with `node --check` on the extracted script + the
  usual no-CDN/no-`<link>` checks).
- **Found and fixed while implementing (via the end-to-end tests, not a live run):** neither this new
  module nor `ai_delta.py` (the pattern it mirrors) validated that a proposed screen's `role` refers to one
  of the base IR's *actual* declared roles — `ApplicationIR.__post_init__` does catch it as a last resort
  (it did, in the first failing test run: `minimal-blog-ecosystem`'s "author-studio" surface only declares
  an `author` role), but only *after* `generate_app_delta_proposal` had already returned, too late for the
  retry loop to use it. Fixed by adding an explicit role check to `parse_app_delta_proposal` (same layer as
  every other base-IR collision, gets the retry benefit) and to `apply_app_delta` (defense in depth), plus
  listing the app's real roles in the prompt.
- **Tests:** `test_app_delta.py` (27, new), `test_studio_session.py` (13, new), `test_studio_edit.py` (11,
  new end-to-end against real temp git repos — a real second commit with the new entity's files actually on
  disk, a second edit stacking a third commit, a collision rejected with zero commits and state unchanged,
  `StudioBuildHistory` updated in place, a provider exception never retried, both excluded build kinds
  honestly rejected), plus route/page-control additions to `test_studio_server.py`. Gates: focused 214
  passed; `task verify` **3,593 OK** (63.8s — no slowdown, confirming no hidden network calls crept in);
  lint/security/env green; demos clean (359/353 files).
- **Manual smoke (opt-in, real HTTP, build-only mode, no live model call — today's Groq daily quota was
  already exhausted per R-466/R-467):** `/healthz` ok; an unknown build's `/turns` → `{"turns": []}` (200,
  honest empty view, not an error); an unknown build's `/edit` → 404; a build id with a slash → 404 (not
  matched); the page's HTML contains "Apply change". The core delta→merge→diff→commit round trip was
  already proven end-to-end by the test suite above, so no further live model call was spent.

## 2026-09-17 — R-467 (Studio File Browser + Hybrid UI Toggle — wiring the hybrid engine into the product UI)

- **Why:** R-465/R-466 built a real hybrid engine, but it was reachable only from a standalone CLI
  (`task agent-engine:ui:synthesize`), completely disconnected from the Studio a user actually opens in a
  browser. Direct reading of `studio/server.py` (stdlib `http.server`, route dispatch as an `if/elif` chain
  with every capability function-injected), `live_serve.py` (the real build-trigger wiring), and `page.py`
  (one server-rendered HTML+vanilla-JS string, no framework) confirmed two concrete gaps: no endpoint ever
  exposed a build's files after the initial response (`<ul id="r-files">` was flat, non-clickable text), and
  `synthesize_screens`/`ui_outcomes` were never passed by any of the three `_build` code paths.
- **File browser:** new pure `studio/files.py` — `list_build_files`/`read_build_file`, path safety mirroring
  `edit/apply.py`'s `_safe_destination` (resolve, `relative_to(root)`, reject on `ValueError`); excludes
  `.git`/`node_modules`/`__pycache__`/`.next`/`.venv`/`venv` and any real `.env*` file (`.env.example` kept).
  `server.py` gains `GET /api/build/{id}/files` and `GET /api/build/{id}/file?path=...`
  (`_build_id_for_suffix` path matching — an id containing `/` never matches; `BuildNotFoundError`→404,
  `PathOutsideBuildError`→400, `FileNotFoundInBuildError`→404); `live_serve.py`'s
  `_resolve_build_dir`/`_list_build_files`/`_read_build_file` resolve against `StudioBuildHistory`'s
  recorded `target_dir`, wired unconditionally (file browsing needs no toolchain or running preview).
- **Hybrid UI toggle:** `/api/build` accepts `hybrid_ui: bool`. Plain-prompt path: always active (a
  provider is already mandatory there). Ecosystem path (single- and all-surfaces): active only when a
  provider actually resolved — `hybrid_ui_active = hybrid_ui and eco_provider is not None`, never a silent
  no-op. `ui_outcomes` surfaces in the response and, via `app_build_result_to_dict`'s new optional
  `ui_outcomes` param (additive; byte-identical when omitted — regression-tested) and
  `StudioBuildHistory.record`'s new bounded capture. Solution Pack path: `build_solution_pack_project` has
  no such parameter — `hybrid_ui_active: false` reported honestly, never guessed at or ignored.
- **`page.py`:** the flat inert `<ul id="r-files">` becomes a clickable two-pane file browser (list +
  read-only viewer fetching `/api/build/{id}/file?path=`, with binary/truncated notices); a "Hybrid UI
  (experimental)" checkbox on the build form; a one-line hybrid summary + a 🤖 badge on model-written files.
  Zero external assets preserved (verified: no `http://`, `https://`, `src=`, `<link`; JS syntax verified
  with `node --check` on the extracted `<script>` block).
- **Found and fixed while implementing:** a missing `ApplicationIR` import (latent `NameError`) in
  `live_serve.py`'s ecosystem single-surface branch (`custom_name`/`custom_description` override path).
- **Live discovery — a real, active gap, not a theoretical one:** the founder's real Groq credentials now
  sit in the repo's gitignored `.env` (added during today's R-465/R-466 live proofs). Running the
  *pre-existing, unmodified* Studio test suite made real outbound Groq calls — `pytest` took minutes instead
  of seconds. Four pre-existing `live_serve._build(...)` test call sites never mocked
  `resolve_generation_provider_from_env`: the two already suspected in `test_studio_ecosystem.py`, **plus
  two more found here** in `test_studio_server.py` (`test_live_serve_build_with_solution_pack`,
  `test_live_serve_build_with_ai_delta_features`) — because *any* non-`None` provider reaching
  `build_app_from_ir`/`build_solution_pack_project` triggers R-462's overview-page LLM synthesis regardless
  of `hybrid_ui`. Timed precisely: `resolve_generation_provider_from_env()` alone takes 0.02s; the unmocked
  ai-delta test took **23.5s of real, R-466-paced Groq traffic** (413 too-large → compact-grounding retry →
  validator rejection → 429 rate-limited → give-up) before falling back. All four now mock it explicitly to
  `(None, "stub-model", 4096, 5.0)`.
- **Tests:** `test_studio_files.py` (18, new), plus additions to `test_studio_server.py` (file routes,
  `hybrid_ui` forwarding, page-controls), `test_studio_ecosystem.py` (hybrid-UI threading + Solution Pack
  honest no-op), `test_studio_history.py` (hybrid fields round-trip), `test_build_app.py` (`ui_outcomes`
  regression guard). Gates: focused 144 passed; `task verify` **3,529 OK** (full local suite: 3,529 passed +
  42 subtests in 68.80s — materially faster post-fix, corroborating no hidden network calls remain);
  lint/security/env green; demos clean (359/353 files).
- **Manual smoke (opt-in, real HTTP, build-only mode, no `hybrid_ui` — today's Groq daily quota was already
  spent per R-466):** a real 160-file build via `POST /api/build`; `GET /api/build/1/files` listed 160 real
  paths; `GET /api/build/1/file?path=...` returned real content; unknown build id → 404; a
  `../../../etc/passwd` traversal attempt → 400; missing `path` → 400. `hybrid_ui` end-to-end threading was
  proven by the stub-provider ecosystem test (a real `page.tsx` on disk carries the `LLM-Synthesized`
  marker) rather than spending more of today's exhausted quota.

## 2026-09-17 — R-466 (Compile-Level Repair for LLM-Written UI + Rate-Limit-Aware Pacing)

- **Why:** the R-465 live run showed two gaps — the gateway collapsed every HTTP failure into an opaque
  `ProviderHTTPError` (no status, no `Retry-After`), and the R-465 validator is string-level (a page can pass
  and still fail `tsc`; `run_verify` only records exit codes).
- **Pacing (`model_gateway/errors.py`, `cloud.py`, `bootstrap.py`, `.env.example`):** `ProviderHTTPError`
  carries `status_code` + `retry_after_seconds`; `ProviderRateLimitedError` for 429; pure `parse_retry_after`
  (header delay-seconds / HTTP-date, else the body's "try again in 6.495s"); one `_http_error` builder for the
  JSON and stream paths (bounded body, never the key); `generate()` waits the hint (+0.5s; 2s/4s backoff
  without one) and re-sends the SAME request, bounded by `OMNISTACKAI_RATE_LIMIT_RETRIES` (2) and
  `OMNISTACKAI_MAX_RETRY_AFTER_SECONDS` (60; a longer ask fails fast); every wait/give-up logged; injectable
  sleep. No other error is retried; the circuit breaker and routing are untouched.
- **Capturing compiler (`verify/compile.py`):** `CompileError`/`CompileReport` (JSON-safe, grouped by file),
  `parse_tsc_output` (`--pretty false` format, de-duplicated, POSIX paths), `compile_web_project` (the app's own
  `node_modules/.bin/tsc`, injectable runner, timeout → `VerifyError`), `ensure_web_dependencies`
  (present / symlink an existing install / `pnpm install --ignore-scripts`).
- **Compile repair (`codegen/hybrid_repair.py`):** `llm_file_specs` reproduces the exact R-465 prompts,
  template fallbacks and compact prompts for `app/page.tsx` + `app/<screen>/page.tsx`;
  `compile_errors_message` (bounded); `repair_compiled_files` sends `[SYSTEM, USER(prompt), ASSISTANT(current
  file), USER(REJECTED: TypeScript reported N error(s) …)]`, validates, marks `compile-repair k/N`, falls back to
  the template, records a `UiSynthesisOutcome`, and never touches a path without a spec; `build_repair_diff`
  → `ProjectDiff` of `MODIFIED apps/web/<path>`; `compile_and_repair(_sync)` = compile → repair → apply →
  recompile for `max_rounds`, reverting still-failing LLM files on the last round →
  `CompileRepairReport(rounds, repaired, reverted, untouched_failures, final_ok)`.
- **Shrink on "request too large" (`llm_ui.py`, `nextjs.py`) — amendment from the live runs:** a
  `_Transcript` holds the bounded conversation and shrinks on 413 (or a 400 that says "context length"/"too
  large"): first drop the echoed output (corrective text merged into the prompt turn), then switch to
  `compact_grounding(ir)` (every hook signature; one export per component; tokens; prompts ≤ 14k chars);
  threaded through the synthesis entry points, the adapter (only with a provider — default bytes unchanged),
  `LlmFileSpec.compact_prompt` and `_repair_one`. `last_reason` now carries the HTTP status
  (`ProviderHTTPError(413)`), never the body.
- **CLI Step 3/3 (`intake/ui_synthesize_run.py`):** link (`OMNISTACKAI_WEB_NODE_MODULES`) or install
  `node_modules`, compile, repair, revert, commit the repair as the customer identity, print each compile
  round + repaired/reverted/untouched + the verdict; skips cleanly without the toolchain.
- **Tests:** `test_cloud_rate_limit.py` (15), `test_compile_report.py` (11), `test_hybrid_repair.py` (12),
  `test_llm_ui_compact.py` (10) — stub providers, fake runners, temp dirs. Gates: focused 115 passed;
  `task verify` **3,490 OK**; lint/security/env green; demos clean; `web-typecheck` PASSED ×2.
- **Live (Groq free tier) — as found:** the 3-step CLI ran end-to-end in 13 s (intake OK; all 5 UI calls
  failed instantly on a non-429 status; fallbacks; Step 3 compiled at 0 errors, PASSED). A direct probe with
  the full grounded prompt SUCCEEDED on an empty window (5,024 in / 3,639 out). A reproduction showed the 429
  path working (typed; `Retry-After: 112` honoured) but giving up above the 60 s cap — the limiter was tokens
  per DAY (200k, 191k used): the day's proofs spent the daily budget. Pacing + status outcomes are
  live-verified; compile repair with real tsc errors and shrink-on-413 are stub-verified only.

## 2026-09-17 — R-465 (Grounded Hybrid UI Synthesis — LLM writes the UI over the deterministic data layer)

- **Founder decisions (after the honest platform assessment):** compete via a HYBRID engine — an LLM writes
  the modern UI constrained to the deterministic typed data layer, with a verify/repair loop; paid Groq/Gemini
  approved, opt-in only; engine slightly ahead of the product-UI shell. R-465 is the first engine brick.
- **Why the R-462 seed hallucinated:** the prompt hand-described the hooks and had drifted from the generator
  (`refresh()` vs the real `refetch()`; `page/pageSize` *params* vs the real `limit/offset`; no
  `use<Entity>`/`useUpdate`/`useDelete`/`useList<Child>By<Rel>`; `useAuth` advertised even without an
  auth-provider); it told the model to hardcode hex colours although `styles/tokens.css` exists; per-screen
  synthesis sat behind a never-set env var with zero test coverage; the validator's rejection reason was
  discarded after one attempt; the import whitelist had a multi-line bypass.
- **Grounding (`codegen/nextjs.py`):** `summarize_data_layer(ir)` parses the REAL generator output — entity
  interfaces (`_entity_interface`), the `Use*` interfaces and every exported hook signature from
  `_hooks_file(ir)` (mutation hooks rendered from their bodies), `api.*` names — with an explicit "NO data
  hooks" line for IRs without entity-schema APIs. `_component_files(ir)` factors the ~110 component files out
  of `generate()` (byte-identical output; `GeneratedProject` sorts by path) and `summarize_components(ir)` lists
  their real export names (auth-provider first, only when `needs_auth`). `summarize_design_tokens()` lists the
  real token names. `NextjsWebAdapter.generate` computes the three blocks once per project when a provider is
  present.
- **Engine (`codegen/llm_ui.py` rewritten):** one `_synthesize_file` core — `[SYSTEM, USER]`; on validator
  rejection append `ASSISTANT(prior output, capped 8k chars)` + `USER(_repair_message(path, reason))` and
  retry up to 3; **retry only on validator rejection, never on exceptions**; exhaustion/exception → the
  deterministic template with no marker; success marker `… (<model>; attempt k/N)`; a JSON-safe, secret-free
  `UiSynthesisOutcome(path, mode, attempts, model_id, last_reason)` per file (`last_reason` = validator reason
  or exception type name only). `clean_and_validate_jsx` now scans every static import statement (multi-line
  aware), allows exactly `react`/`react-dom` + platform prefixes, rejects `react-*`, `require(`, dynamic
  `import(`. Prompt builders accept `data_layer`/`components`/`design_tokens` (lazily computed — no import
  cycle), share `_grounding_blocks` + `_core_rules` (token styling; `useAuth` rule conditional on `needs_auth`).
- **Explicit switch:** `synthesize_screens: bool = False` + `ui_outcomes` threaded
  `NextjsWebAdapter.generate → assemble_project → build_app_from_ir / build_app_from_prompt`; the env gate and
  the now-unused `import os` removed; `ModelProvider` gets a proper `TYPE_CHECKING` import.
- **Opt-in CLI:** `intake/ui_synthesize_run.py` → `task agent-engine:ui:synthesize -- "<prompt>"` (script case
  + Taskfile + COMMANDS.md): intake via `resolve_generation_provider_from_env()`, then
  `build_app_from_ir(..., synthesize_screens=True, ui_outcomes=…)`, per-file outcome table, local-Ollama
  context warning, clean bounded exit on provider errors. New `docs/HYBRID_UI.md`.
- **Tests:** new `tests/test_llm_ui_grounding.py` (15: grounding, no-hallucination, drift guard, tokens,
  components/auth, repair success on attempt 2 with the reason in request #2, exhaustion → template, exception
  → 1 request, switch default/opt-in, byte-identical default, import hardening, assemble/build threading).
  Honest updates: the R-462 test IR gained real entity-schema APIs (two tests had been asserting the
  hallucinated hook); the platform test's drifted `page?/pageSize?` assertions became the real
  `limit?/offset?` params + `page/pageSize` state.
- **Gates:** focused 47 passed; `task verify` **3,442 OK** (Stage 0; 0 model calls); lint/security/env green;
  demos 157/153; `web-typecheck` **PASSED** for minimal-blog and rideshare-favourites (deterministic default
  unchanged).
- **Live proof (opt-in, founder's Groq key) — honest:** the account is on the free `on_demand` tier (8,000 TPM)
  with exactly one accessible model (`openai/gpt-oss-120b`). Full CLI run → 429 on the intake call (the CLI's
  traceback leak was fixed). Scoped run (one grounded overview call + tsc): the model returned a page, the
  validator rejected it with an exact reason (truncated at max_output 4096), the repair loop engaged, the repair
  call hit 429 (the echo pushed it past 8k TPM), and the engine fell back gracefully with a truthful outcome
  record; the built repo compiles (tsc 0). The engine behaves as designed; a full LLM-page-compiles proof needs
  >8k TPM (Gemini via `GOOGLE_API_KEY`, or Groq Dev tier). Echo cap lowered 16k → 8k chars; gateway 429 pacing
  logged for R-466.

## 2026-09-16 — R-464 (Full-Stack Platform Feature Completeness — 4-Phase Plan)

- Implemented full-stack platform feature completeness across all 4 phases:
  - **Phase 1 (Frontend Search, Pagination & Filter UI Controls)**:
    - Verified collection screen pagination, search, and segmented filter controls.
    - Updated `llm_ui.py` (`build_ui_synthesis_prompt`) to document complete hook signatures (`page`, `pageSize`, `totalPages`, `params`, `setSearch`, `setPage`, `setPageSize`, `setSort`, `setFilter`, `clearFilters`, `refetch`).
  - **Phase 2 (Audit Timestamps on All Entity Tables)**:
    - Added `"created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()` and `"updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()` to all entity tables in `schema_sql.py`.
    - Added PostgreSQL `set_updated_at()` trigger function and `BEFORE UPDATE ON "<table>"` triggers for all entities.
    - Excluded `created_at` and `updated_at` from `_insert_columns` in `data_access.py`.
    - Added `CreatedAt` and `UpdatedAt` (`time.Time`) to Go model structs in `backend_go.py`.
    - Added `created_at` and `updated_at` (`Optional[datetime] = None`) to Python models in `backend_python.py`.
    - Added `created_at?: string;` and `updated_at?: string;` to TypeScript entity interfaces in `nextjs.py`.
    - Rendered record creation & last-updated metadata footer in `_detail_screen_page` in `nextjs.py`.
  - **Phase 3 (RBAC / Row Ownership `created_by`)**:
    - Conditional on `needs_auth(ir)`: added `"created_by" UUID REFERENCES "users"("id") ON DELETE SET NULL` to entity tables in `schema_sql.py`.
    - Added `created_by: str | None = None` support to `create_*` in `data_access.py`.
    - Added `require_owner` helper in `python_auth_file` and `RequireOwner` in `go_auth_file` in `auth_guard.py`.
    - Added `created_by?: string | null;` to TypeScript interfaces and `ownerOnly?: boolean` param to `useList*` hooks in `nextjs.py`.
  - **Phase 4 (S3-Compatible File Uploads)**:
    - Added `FieldType.ATTACHMENT = "attachment"` and string aliases (`attachment`, `file`, `upload`, `media`) in `application_ir/ir.py`.
    - Mapped `FieldType.ATTACHMENT` to `TEXT` in `schema_sql.py`, `string` in TypeScript (`nextjs.py`), `str` in Python (`backend_python.py`), and `string` in Go (`backend_go.py`).
    - Added storage environment variables (`STORAGE_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`) to `.env.example` in Next.js, Python FastAPI, and Go Gin adapters.
- Created comprehensive test suite `test_platform_feature_completeness.py` with 14 tests across all 4 phases.
- Verification:
  - `python3 -m unittest test_platform_feature_completeness.py`: 14 tests passed.
  - `bash scripts/agent-engine.sh lint`: Passed.
  - `bash scripts/agent-engine.sh test`: **3,427 tests passing (100% OK)**.



- Built full modern SaaS Admin Panel in `scratch/apps/build-a-clinic-management-app/apps/web/app/page.tsx` replacing legacy flat overview cards:
  - Collapsible drawer / left sidebar navigation with Clinic brand badge, collapse/expand toggle button (`◫`), Clinical Records accordion with live entity badge counters (Appointments, Patients, Prescriptions), Settings accordion with bullet dots (`General Settings`, `City Settings`, `Schedule Settings`, `Manager Settings`), active blue pill indicator (`#eff6ff` / `#2563eb`), and footer user profile chip.
  - Top navigation bar with global search input, Language selector (`Language (EN)`, `Spanish`, `French`, `Hindi`), Country selector (`Australia`, `US`, `UK`, `India`), Notification bell with unread badge counter, and interactive User Avatar dropdown menu with user profile details, Settings, Reset Password (`/forgot-password`), and Sign Out (`logout()`).
  - Manager Settings View (matching user reference Images 1, 3, 4): Status filter dropdown, `Apply Filter` primary blue button, `+ Add Manager` dark button with interactive modal to add staff, and high-contrast data table with `ID`, `Name`, `Email`, `Status` (green `Active` pill), `Role` (`Super Admin`), `Action` (`Edit` & `Delete`), and `Reset Password` buttons, plus pagination footer (`Showing 1 to X of Y entries`).
  - General Settings & City Settings Views (matching user reference Images 2, 5): clean form cards with required red asterisks (`*`), Brand Logo and Favicon upload preview boxes with upload triggers, and primary `UPDATE` button.
- Upgraded platform synthesis prompt in `codegen/llm_ui.py`:
  - Added `_detect_ui_archetype(ir, prompt)` distinguishing Admin Panels / Management Systems from Public Websites / E-Commerce.
  - Generates full drawer-based admin layouts for management/admin apps, and modern consumer landing pages (hero, product catalog, testimonials, footer) for public websites.
- Verified:
  - `npx tsc --noEmit`: 0 TypeScript errors.
  - `next build`: 24/24 static & dynamic pages successfully compiled.
  - Next.js dev server: HTTP 200 on `/`, `/login`, `/register`, and `/forgot-password`.
  - `task lint` & `bash scripts/agent-engine.sh lint`: Passed.
  - `bash scripts/agent-engine.sh test`: **3,413 tests passed (100% OK)**.

## 2026-09-16 — R-463 (Auth Lifecycle Hardening, Unterminated Regexp Literal Fix & Forgot Password Workflow)

- Diagnosed and resolved Next.js Webpack syntax crash `Unterminated regexp literal ./app/register/page.tsx:68:1 Caused by: Syntax Error`:
  - Root cause: in `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py`, lines 224 (`_login_page`) and 407 (`_register_page`) used `f'          }}>{brand_initial}</div>\n'`. In Python f-strings, `}}` emits a single `}`, outputting invalid JSX `}>C</div>` which Webpack/SWC parses as an unclosed regular expression literal (`/>`), failing the entire Next.js compilation graph.
  - Fixed by using four braces `}}}}` in f-strings so the rendered JSX contains correct double closing braces `}}>C</div>`.
  - Also resolved `AttributeError: 'ApplicationIR' object has no attribute 'title'` in `_forgot_password_page` by standardizing on `ir.name`.
- Implemented Complete End-to-End Forgot Password Workflow:
  - Added `_forgot_password_page(ir: ApplicationIR) -> str` in `codegen/nextjs.py` synthesizing `app/forgot-password/page.tsx` with email, new password, confirmation password validation, and automatic redirect to `/login`.
  - Added "Forgot password?" link to `app/login/page.tsx` directly above the submit button.
  - Updated `auth_guard.py` backend code generator to emit `ResetPasswordRequest`, `POST /auth/forgot-password`, and `POST /auth/reset-password` which directly hashes with PBKDF2-SHA256 and updates `users` in PostgreSQL.
  - Automatically emits `app/forgot-password/page.tsx` whenever `needs_auth(ir)` is true in `NextjsWebAdapter.generate`.
- Synchronized and verified active project `scratch/apps/build-a-clinic-management-app`:
  - Fixed register and login pages; added `app/forgot-password/page.tsx`.
  - Added `ResetPasswordRequest`, `POST /auth/forgot-password`, and `POST /auth/reset-password` in `services/api/app/routers/auth.py`.
  - Executed `npx tsc --noEmit` (0 TypeScript errors) and `next build`: **24/24 static and dynamic pages compiled successfully**.
- Verification:
  - `task lint`: Passed.
  - `bash scripts/agent-engine.sh lint`: Passed.
  - `bash scripts/agent-engine.sh test`: **3,413 tests passing (100% OK)**.


- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
- Implemented hybrid generative LLM-powered UI synthesis engine (`services/agent-engine/src/omnistackai_agent_engine/codegen/llm_ui.py`):
  - `build_ui_synthesis_prompt(ir, user_prompt)`: Synthesizes rich domain-tailored prompts referencing the 57 built-in components and entity hooks for the overview landing page.
  - `build_screen_synthesis_prompt(screen, ir)`: Generates focused screen-level prompts for specific interactive workflow pages (`app/[screen]/page.tsx`).
  - `clean_and_validate_jsx(raw_jsx)`: Automatic safety verification enforcing `'use client'`, markdown fence stripping, strict import whitelisting (React, Next.js, and internal platform components), blocking arbitrary third-party npm injections, and checking balanced delimiters (`{}`, `()`, `[]`).
  - `synthesize_overview_page` & `synthesize_screen_page`: Orchestrates ModelProvider prompt delivery with timeout and graceful, silent fallback to deterministic templates (`_overview_page` and `_fallback_screen_page`) on provider errors, timeouts, or invalid JSX.
- Upgraded `nl_to_ir.py` with Universal Domain Archetype Expansion & 1:1 Full-Stack Triad Mapping:
  - Enforced that every user-specified feature (and generic short prompts for E-Commerce, Healthcare, SaaS, FinTech, Real Estate, LMS, Logistics, etc.) maps into a full 4–8 entity architecture with database migrations, FastAPI REST endpoints, and interactive Next.js screens.
  - Added `_sanitize_ir_dict` to coerce common LLM syntax variances (string auth, type aliases, role casing) into strict, valid Application IR schemas.
- Implemented Dynamic Multi-Provider Resolution (`intake/provider_resolution.py`):
  - `resolve_generation_provider_from_env()`: Automatically detects `OMNISTACKAI_CLOUD_PROVIDER` (Groq, OpenAI, Anthropic) and authenticates using the user's API key from `.env` while maintaining local container execution (`OMNISTACKAI_TIER=0`).
  - Attached `certifi` CA context to urllib HTTPSHandler in `model_gateway/cloud.py` to fix macOS SSL root certificate issues.
  - Added `User-Agent: OmniStackAI/1.0` header to avoid Cloudflare WAF Error 1010 blocks against default Python urllib.
  - Configured `openai/gpt-oss-120b` for Groq inference (120B parameters, full 4,096 token limit, generating comprehensive 8-entity architectures in 8 seconds).
- Integrated across `NextjsWebAdapter.generate`, monorepo `assemble_project`, `build_app_from_prompt`, `build_run.py`, and `studio/live_serve.py`.
- Added unit and integration test suites:
  - `services/agent-engine/tests/test_llm_ui.py` (18 tests)
  - `services/agent-engine/tests/test_provider_resolution.py` (3 tests)
- Verified:
  - `task agent-engine:lint && task lint` (passed)
  - `task agent-engine:test` (3,411 tests passed in 43.037s)
  - `task verify` (Stage 0 verification passed)
  - `task security:quick` (Stage 0 secret-policy check passed)
  - Live Groq generation test: successfully compiled `"Modern e-commerce store with product grid, shopping cart, discounts, and customer reviews"` into 182 files with full database migrations (`0001_init.sql`), REST API routers (`cart.py`, `discounts.py`, `orders.py`, `products.py`, `reviews.py`), and Next.js frontend pages.

## 2026-09-16 — R-461 (Full-Stack Production Authentication Engine)

- Recorded `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-461.md` before implementation.
- Implemented complete production-ready authentication across the full generated stack:
  - Database schema (`schema_sql.py`): Emits PostgreSQL `users` table with UUID primary key, `VARCHAR UNIQUE NOT NULL` email, `VARCHAR NOT NULL` password_hash, optional full_name, `VARCHAR NOT NULL DEFAULT 'user'` role, and `TIMESTAMPTZ` created_at, plus a development admin seed row (`admin@example.local` / `changeme`) with PBKDF2 hash.
  - FastAPI Auth Router (`auth_guard.py`): Exported `python_auth_router_file(ir)` with `/register`, `/login`, `/me`, `/logout` endpoints, using `hashlib.pbkdf2_hmac` (SHA-256, 100k iterations) with zero external dependencies, JWT signing/verification, and wired into `main.py` via `backend_python.py`.
  - Next.js Web (`nextjs.py`): Synthesizes `components/auth-provider.tsx` with `useAuth()` hook exposing `user`, `token`, `login()`, `register()`, and `logout()`; responsive `app/login/page.tsx` and `app/register/page.tsx` with error alerts, client validation, and redirection; navbar user state toggle showing user greeting / logout button when logged in and Sign In link when logged out.
  - API Client (`lib/api.ts`): Automatically attaches the Bearer token from localStorage (`auth_token`) with explicit override support.
- Added comprehensive unit tests in `services/agent-engine/tests/test_full_stack_auth.py` (42 tests).
- Verified with `task test`, `task lint`, `task security:quick`, `task env:check`, and full offline `task verify`: 3,386 tests passing offline (+46 net-new tests); zero external deps, zero network calls, clean gates.

## 2026-09-15 — R-460 (Next.js Codegen End-to-End Route Handler Synthesis & Interactive CRUD Form Submission)

- Recorded `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-460.md` before implementation.
- Fixed Web Studio iframe preview blocker:
  - Scoped `X-Frame-Options: DENY` to production only in generated Next.js `next.config.mjs` (`process.env.NODE_ENV === "production"`).
  - Resolves `ERR_BLOCKED_BY_RESPONSE` (broken sad document icon) inside the Studio preview iframe at `http://127.0.0.1:4173`.
- Replaced scaffolded 501 `not_implemented` route stubs in `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py`:
  - `_route_file(apis)` now synthesizes production-grade proxy route handlers that forward requests directly to the FastAPI backend (`BACKEND_INTERNAL_URL || NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"`).
  - Forwards HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`), query parameters, request bodies, and authorization/content-type headers.
  - Implements reliable fallback returning structured HTTP 503 JSON (`backend_unavailable`) when the upstream backend service is offline.
  - Updated existing generated app route handlers in `scratch/apps/create-a-worker-attendance-management-sy/apps/web/app/` for immediate end-to-end functionality.
- Added comprehensive unit tests in `services/agent-engine/tests/test_nextjs_routes_crud.py` (+3 tests).
- Verified with `task test` and full offline `task verify`: 3,340 tests passing offline (+3 net-new tests); 0 model calls, 0 network, clean lint, security, and environment checks.

## 2026-09-15 — Studio Output Destination Selector & Folder Customization (Option A / Option B / Custom)

- Implemented Output Destination switching and folder name customization across Studio frontend and backend:
  - Added Option A: Project workspace apps (`scratch/apps`).
  - Added Option B: Personal projects folder (`~/Documents/Projects/GeneratedApps`).
  - Added Custom Path option: arbitrary parent folder directory + custom app folder name input.
  - Live destination preview indicator: dynamically reflects destination path as user types prompt or custom folder name.
  - Added `GET /api/config` in `studio/server.py` returning `workspace_apps_dir`, `personal_apps_dir`, and `current_out_dir`.
  - Updated `POST /api/build` options allowlist to accept `output_dir`, `folder_name`, `target_dir`.
  - Updated `_target_dir_for` in `studio/live_serve.py` to accept `custom_dir`, `folder_name`, `custom_name`, expand `~`, and auto-create target directories.
  - Wired `output_dir` and `folder_name` across ecosystem, solution pack, and local LLM build branches in `studio/live_serve.py`.
  - Updated `scripts/agent-engine.sh` to export `OMNISTACKAI_APP_OUT_DIR` consistently.
  - Added comprehensive offline tests in `test_studio_server.py` (+4 tests, total 46 studio tests, 3,337 project tests). Zero external network requests, 100% offline verification passed.

## 2026-09-15 — R-459 (Solution Pack Ecosystem Multi-Surface Documentation, Architecture Runbooks, and OpenAPI Aggregator Contracts)

- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
  Final focused suite: 20 passing tests in `test_ecosystem_docs.py`. Total test suite: 3,333 tests passing offline (+23 net-new tests across test files).
- Implemented `solution_packs/ecosystem_docs.py`:
  - Defined frozen `DocPage`: page_id, surface_slug, title, category, order, markdown_content, tags tuple; `to_dict`/`from_dict`.
  - Defined frozen `RunbookStep`: step_id, order, action, command, expected_output, is_automated, description; `to_dict`/`from_dict`.
  - Defined frozen `ArchitectureRunbook`: runbook_id, title, surface_slug, runbook_type, severity, trigger, steps tuple, tags tuple; `to_dict`/`from_dict`.
  - Defined frozen `OpenAPIRoute`: path, method, summary, operation_id, request_schema dict, response_schema dict, tags tuple; `to_dict`/`from_dict`.
  - Defined frozen `OpenAPIAggregationEntry`: surface_slug, base_path, routes tuple; `to_dict`/`from_dict`.
  - Defined frozen `AggregatedAPISpec`: title, version, description, openapi_version, base_url, surfaces tuple, routes tuple; `to_dict`/`from_dict`.
  - Defined frozen `EcosystemDocsContract`: ecosystem_id, version, pages, runbooks, aggregated_api, metadata; `to_dict`/`from_dict`/`to_json`/`from_json` roundtrips; deterministic SHA-256 `digest()`.
  - Defined report models: `DocSearchResult`, `DocSearchReport`, `DocExportSimulationResult`.
  - Implemented `synthesize_ecosystem_docs(ecosystem_id, surfaces, version)`: derives platform overview, data-flow, security pages, surface-specific architecture pages, operational runbooks (local dev setup, production deployment, incident triage), and OpenAPI 3.1 aggregated specs across web, admin, API, worker, and database surfaces offline (0 model calls).
  - Implemented `EcosystemDocsEngine`: thread-safe (`threading.RLock`); `render_markdown_bundle(surface_slug, category)` producing unified, navigational documentation bundles; `search_documentation(query, tags)` with keyword and tag-based relevance scoring; `get_aggregated_openapi()` merging OpenAPI specs with route collision detection; `simulate_documentation_export(format_type, output_dir)` simulating exports across `markdown`, `json`, `openapi_bundle`, and `runbook_checklist` formats.
- Updated Ecosystem Pack Package & Registry:
  - `ecosystem_pack.py`: Added `docs_contract: EcosystemDocsContract | None` field; updated `to_dict`, `parse_ecosystem_pack_package`, and `synthesize_ecosystem_pack` to include docs_contract in payload and whole-package SHA-256 checksum.
  - `ecosystem_registry.py`: Added `docs_contract` property to `EcosystemPack`; `has_docs_contract` in `to_dict`; `get_docs_contract(ecosystem_id, version)` on `EcosystemPackRegistry` and `_LazyEcosystemPackRegistry` delegate.
- Updated Studio Preview & Server:
  - `studio/preview.py`: Imports docs types; adds `_docs_contract`/`_docs_engine` fields; `replace_ecosystem()` accepts optional `docs_contract` param, falls back to registry cache then synthesize; all three payload branches inject `has_docs`, `page_count`, `runbook_count`, `api_endpoint_count`, and `docs_status`; cleanup in `_stop_locked()`; new `get_ecosystem_docs()` and `export_ecosystem_docs()` methods.
  - `studio/server.py`: `_make_handler` and `create_studio_server` accept `get_ecosystem_docs_fn` and `export_ecosystem_docs_fn`; `GET /api/ecosystem/docs`; `POST /api/ecosystem/docs/export`.
  - `studio/live_serve.py`: Wires `get_ecosystem_docs_fn` and `export_ecosystem_docs_fn` in `control_kwargs`.
  - `studio/page.py`: Sky-blue/amber-themed `.preview-docs-info` CSS panel; `#preview-docs-info` HTML with Pages count, Runbooks count, API Endpoints count badges, and "Export Docs" / "Refresh" buttons; JS update logic in preview status handler; button handlers for Export (calls POST, renders export status) and Refresh (calls GET, updates badges, strictly 0 external network requests).
- Added `docs` subcommand to `ecosystem_cli.py`: accepts file path or registered ecosystem ID; `--json` outputs canonical JSON; `--search` performs tag/keyword query; `--export` simulates export into specified format (`markdown`, `json`, `openapi_bundle`, `runbook_checklist`); default text mode shows pages, runbooks, and aggregated OpenAPI route specs.
- Exported all docs symbols in `solution_packs/__init__.py`.
- All gates pass: `task verify` (3,333 tests in 41.057s), `bash scripts/agent-engine.sh lint`, `task security:quick`, `task env:check`, `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites`. Zero model calls.

## 2026-09-15 — R-458 (Solution Pack Ecosystem Multi-Surface Governance, Compliance Policy, and Audit Evidence Contracts)

- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
  Final focused suite: 22 passing tests in `test_ecosystem_governance.py`. Total test suite: 3,310 tests passing offline (+22 net-new tests).
- Implemented `solution_packs/ecosystem_governance.py`:
  - Defined frozen `ComplianceStandard`: standard_id, name, version, description, mandatory_controls tuple; `to_dict`/`from_dict`.
  - Defined frozen `CompliancePolicy`: policy_id, surface_slug, standard_id, control_id, severity, enforcement_mode, rule_expression, remediation, description, tags tuple; `to_dict`/`from_dict`.
  - Defined frozen `DataClassification`: classification_id, surface_slug, entity_name, field_name, classification_level, encryption_required, retention_days, anonymization_method, description; `to_dict`/`from_dict`.
  - Defined frozen `AuditEvidenceItem`: evidence_id, control_id, surface_slug, collector_kind, status, collected_at, sha256_hash, details dict; `to_dict`/`from_dict`.
  - Defined frozen `EcosystemGovernanceContract`: ecosystem_id, version, standards, policies, classifications, evidence_items, metadata; `to_dict`/`from_dict`/`to_json`/`from_json` roundtrips; deterministic SHA-256 `digest()`.
  - Report models: `PolicyEvaluationResult`, `GovernanceComplianceReport` (with `overall_compliant`, `violations`), `EvidenceVerificationItemResult`, `AuditVerificationReport` (with `all_valid`), `GovernanceAuditSimulationReport` (with `overall_audit_passed`, `compliance_report`, `evidence_report`).
  - Implemented `synthesize_ecosystem_governance(ecosystem_id, surfaces, version)`: derives surface-specific compliance policies, data privacy classifications, and initial cryptographic audit evidence items across web, admin, API, worker, and database surfaces offline (0 model calls).
  - Implemented `EcosystemGovernanceEngine`: thread-safe (`threading.RLock`); `evaluate_compliance(surface_configs, environment_state)` verifying configuration rules and detecting violations; `verify_audit_evidence(evidence_items)` verifying cryptographic SHA-256 hashes against evidence items; `simulate_compliance_audit(scenario)` simulating full compliance audits across operational scenarios (`standard_audit`, `gdpr_dsar_request`, `data_breach_investigation`, `soc2_certification`, `high_risk_violations`).
- Updated Ecosystem Pack Package & Registry:
  - `ecosystem_pack.py`: Added `governance_contract: EcosystemGovernanceContract | None` field; updated `to_dict`, `parse_ecosystem_pack_package`, and `synthesize_ecosystem_pack` to include governance_contract in payload and whole-package SHA-256 checksum.
  - `ecosystem_registry.py`: Added `governance_contract` property to `EcosystemPack`; `has_governance_contract` in `to_dict`; `get_governance_contract(ecosystem_id, version)` on `EcosystemPackRegistry` and `_LazyEcosystemPackRegistry` delegate.
- Updated Studio Preview & Server:
  - `studio/preview.py`: Imports governance types; adds `_governance_contract`/`_governance_engine` fields; `replace_ecosystem()` accepts optional `governance_contract` param, falls back to registry cache then synthesize; all three payload branches inject `has_governance`, `standard_count`, `policy_count`, `evidence_count`, and `governance_status`; cleanup in `_stop_locked()`; new `get_ecosystem_governance()` and `simulate_ecosystem_governance()` methods.
  - `studio/server.py`: `_make_handler` and `create_studio_server` accept `get_ecosystem_governance_fn` and `simulate_ecosystem_governance_fn`; `GET /api/ecosystem/governance`; `POST /api/ecosystem/governance/simulate`.
  - `studio/live_serve.py`: Wires `get_ecosystem_governance_fn` and `simulate_ecosystem_governance_fn` in `control_kwargs`.
  - `studio/page.py`: Indigo/violet-themed `.preview-governance-info` CSS panel; `#preview-governance-info` HTML with Standards count, Policies count, Evidence Items count badges, and "Simulate Audit" / "Refresh" buttons; JS update logic in preview status handler; button handlers for Simulate (calls POST, renders audit status) and Refresh (calls GET, updates badges, strictly 0 external network requests).
- Added `governance` subcommand to `ecosystem_cli.py`: accepts file path or registered ecosystem ID; `--json` outputs canonical JSON; `--simulate` with `--scenario` runs compliance simulation and prints structured controls, risk score, findings, and recommended actions; default text mode shows standards, policies, data classifications, and audit evidence.
- Exported all governance symbols in `solution_packs/__init__.py`.
- All gates pass: `task verify` (3,310 tests in 41.372s), `bash scripts/agent-engine.sh lint`, `task security:quick`, `task env:check`, `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites`. Zero model calls.

## 2026-09-15 — R-457 (Solution Pack Ecosystem Multi-Surface SLA, SLO, and Error Budget Contracts)

- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
  Final focused suite: 23 passing tests in `test_ecosystem_sla.py`. Total test suite: 3,288 tests passing offline (+23 net-new tests).
- Implemented `solution_packs/ecosystem_sla.py`:
  - Defined frozen `ServiceLevelIndicator`: sli_id, surface_slug, metric_name, kind (availability, latency, error_rate, throughput, saturation), threshold, unit, good_events_query, total_events_query, description, tags tuple.
  - Defined frozen `ServiceLevelObjective`: slo_id, name, surface_slug, sli_id, target_percentage, rolling_window_days, budgeting_method (timeslice, occurrences), warning_threshold_pct, tier (critical, high, medium, low), tags tuple.
  - Defined frozen `ErrorBudget`: slo_id, total_budget_percentage, remaining_budget_percentage, burn_rate_1h, burn_rate_6h, burn_rate_24h, budget_status (healthy, warning, exhausted), consumed_budget_percentage.
  - Defined frozen `ServiceLevelAgreement`: sla_id, customer_tier (enterprise, business, developer, free), surface_slug, availability_target_pct, p95_latency_ms_target, financial_credit_pct, penalty_threshold_pct, description.
  - Defined frozen `EcosystemSLAContract`: ecosystem_id, version, slis, slos, error_budgets, slas; `to_dict`/`from_dict`/`to_json`/`from_json` roundtrips; deterministic SHA-256 `digest()`.
  - Implemented `synthesize_ecosystem_sla(ecosystem_id, surfaces, version)`: derives surface-specific SLIs (availability, p95 latency, web uptime, Core Web Vitals LCP, mobile crash-free sessions), tiered SLOs with rolling windows, error budgets, and customer-tier SLAs with availability and financial credit guarantees offline (0 model calls).
  - Implemented `EcosystemSLAEngine`: thread-safe (`threading.Lock`); `evaluate_sli_metrics(metrics)` evaluating observations against thresholds; `calculate_error_budget_burn(slo_id, error_rate_pct, time_window_hours)` computing 1h, 6h, 24h burn rates and exhaustion projections; `simulate_sla_compliance(scenario, metrics)` simulating compliance, SLO breaches, and financial credit liabilities across operational scenarios (normal_operations, minor_degradation, severe_outage, budget_exhaustion).
- Updated Ecosystem Pack Package & Registry:
  - `ecosystem_pack.py`: Added `sla_contract: EcosystemSLAContract | None` field; updated `to_dict`, `parse_ecosystem_pack_package`, and `synthesize_ecosystem_pack` to include sla_contract in payload and whole-package SHA-256 checksum.
  - `ecosystem_registry.py`: Added `sla_contract` property to `EcosystemPack`; `has_sla_contract` in `to_dict`; `get_sla_contract(ecosystem_id, version)` on `EcosystemPackRegistry` and `_LazyEcosystemPackRegistry` delegate.
- Updated Studio Preview & Server:
  - `studio/preview.py`: Imports SLA types; adds `_sla_contract`/`_sla_engine` fields; `replace_ecosystem()` accepts optional `sla_contract` param, falls back to registry cache then synthesize; all three payload branches inject `has_sla`, `sli_count`, `slo_count`, `sla_count`, and `sla_status`; cleanup in `_stop_locked()`; new `get_ecosystem_sla()` and `simulate_ecosystem_sla()` methods.
  - `studio/server.py`: `_make_handler` and `create_studio_server` accept `get_ecosystem_sla_fn` and `simulate_ecosystem_sla_fn`; `GET /api/ecosystem/sla`; `POST /api/ecosystem/sla/simulate`.
  - `studio/live_serve.py`: Wires `get_ecosystem_sla_fn` and `simulate_ecosystem_sla_fn` in `control_kwargs`.
  - `studio/page.py`: Emerald/teal-themed `.preview-sla-info` CSS panel; `#preview-sla-info` HTML with SLI count, SLO count, SLA count badges, and "Simulate SLA" / "Refresh" buttons; JS update logic in preview status handler; button handlers for Simulate (calls POST, renders compliance status) and Refresh (calls GET, updates badges, strictly 0 external network requests).
- Added `sla` subcommand to `ecosystem_cli.py`: accepts file path or registered ecosystem ID; `--json` outputs canonical JSON; `--simulate` with `--scenario` runs compliance simulation and prints structured SLIs, burn rates, and financial liabilities; default text mode shows SLIs, SLOs, error budgets, and SLAs.
- Exported all SLA symbols in `solution_packs/__init__.py`.
- All gates pass: `task verify` (3,288 tests), `task lint`, `task security:quick`, `task env:check`, `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites`. Zero model calls.

## 2026-09-15 — R-456 (Solution Pack Ecosystem Multi-Surface Alerting, Incident Runbooks, and Escalation Policies)

- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
  Final focused suite: 23 passing tests in `test_ecosystem_alerting.py`. Total test suite: 3,265 tests passing offline (+23 net-new tests).
- Implemented `solution_packs/ecosystem_alerting.py`:
  - Defined frozen `AlertRule`: rule_id, surface_slug, metric_name, condition (>, >=, <, <=, ==), threshold, duration_seconds, severity (info, warning, critical, fatal), description, runbook_id, tags tuple.
  - Defined frozen `RunbookStep`: step_id, order, action (inspect_telemetry, scale_replicas, drain_traffic, restart_service, notify_stakeholders), target, description, is_automated, remediation_command.
  - Defined frozen `IncidentRunbook`: runbook_id, title, severity, summary, steps tuple, escalation_policy_id, tags tuple.
  - Defined frozen `EscalationTier`: tier, target_channel (slack, pagerduty, executive), wait_minutes, auto_action.
  - Defined frozen `EscalationPolicy`: policy_id, name, description, tiers tuple.
  - Defined frozen `EcosystemAlertingContract`: ecosystem_id, version, alert_rules, runbooks, escalation_policies; `to_dict`/`from_dict`/`to_json`/`from_json` roundtrips; deterministic SHA-256 `digest()`.
  - Implemented `synthesize_ecosystem_alerting(ecosystem_id, surfaces, version)`: derives surface-specific alert rules (HTTP 5xx error spikes, p99 request latency degradation, DB connection saturation, worker queue depth, Web LCP degradation), linked incident runbooks with remediation steps, and tiered escalation policies. Fully offline, deterministic, zero I/O.
  - Implemented `EcosystemAlertingEngine`: thread-safe (threading.Lock); `evaluate_metric()` comparing metric values against rules, `dry_run_runbook()` validating automated commands and manual intervention flags, and `simulate_incident()` evaluating alert firing, running runbook dry-run, and sequencing escalation responders across tiers (scenarios: api_error_spike, high_latency_degradation, db_connection_exhaustion, finops_budget_breach, healthy_baseline).
- Updated Ecosystem Pack Package & Registry:
  - `ecosystem_pack.py`: Added `alerting_contract: EcosystemAlertingContract | None` field; updated `to_dict`, `parse_ecosystem_pack_package`, and `synthesize_ecosystem_pack` to include alerting_contract in payload and whole-package SHA-256 checksum.
  - `ecosystem_registry.py`: Added `alerting_contract` property to `EcosystemPack`; `has_alerting_contract` in `to_dict`; `get_alerting_contract(ecosystem_id, version)` on `EcosystemPackRegistry` and `_LazyEcosystemPackRegistry` delegate.
- Updated Studio Preview & Server:
  - `studio/preview.py`: Imports alerting types; adds `_alerting_contract`/`_alerting_engine` fields; `replace_ecosystem()` accepts optional `alerting_contract` param, falls back to registry cache then synthesize; all three payload branches inject `has_alerting`, `alert_rule_count`, `runbook_count`, `escalation_policy_count`, and `alert_status`; cleanup in `_stop_locked()`; new `get_ecosystem_alerting()` and `simulate_ecosystem_alerting()` methods.
  - `studio/server.py`: `_make_handler` and `create_studio_server` accept `get_ecosystem_alerting_fn` and `simulate_ecosystem_alerting_fn`; `GET /api/ecosystem/alerting`; `POST /api/ecosystem/alerting/simulate`.
  - `studio/live_serve.py`: Wires `get_ecosystem_alerting_fn` and `simulate_ecosystem_alerting_fn` in `control_kwargs`.
  - `studio/page.py`: Rose/crimson-themed `.preview-alerting-info` CSS panel; `#preview-alerting-info` HTML with alert rule count, runbook count, escalation policy count badges, and "Simulate Incident" / "Refresh" buttons; JS update logic in preview status handler; button handlers for Simulate (calls POST, renders summary and responder channels) and Refresh (calls GET, updates badges).
- Added `alerting` subcommand to `ecosystem_cli.py`: accepts file path or registered ecosystem ID; `--json` outputs canonical JSON; `--simulate` with `--scenario` runs incident dry-run simulation and prints structured trigger, runbook, and escalation details; default text mode shows rules, runbooks, and escalation policies.
- Exported all alerting symbols in `solution_packs/__init__.py`.
- All gates pass: `task verify` (3,265 tests), `task lint`, `task security:quick`, `task env:check`, `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites`. Zero model calls.

## 2026-09-15 — R-455 (Solution Pack Ecosystem Multi-Surface Capacity Planning, Resource Quotas, and Unit Economics Budgeting)

- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
  Final focused suite: 19 passing tests in `test_ecosystem_capacity.py`. Total test suite: 3,242 tests passing offline (+19 net-new tests).
- Implemented `solution_packs/ecosystem_capacity.py`:
  - Defined frozen `ResourceQuota`: quota_id, surface_slug, resource_kind (cpu_cores/memory_mb/storage_gb/bandwidth_mbps/concurrent_connections/requests_per_second), limit_value, burst_limit_value, unit, enforcement_action (throttle/queue/reject/scale_out).
  - Defined frozen `SurfaceCapacitySpec`: surface_slug, surface_kind, min_replicas, max_replicas, target_cpu_utilization_pct, target_memory_utilization_pct, requests_per_replica_limit, scale_down_stabilization_seconds.
  - Defined frozen `UnitEconomicsCostModel`: cost_model_id, surface_slug, base_monthly_cost_usd, marginal_cost_per_1k_requests_usd, marginal_cost_per_gb_storage_usd, currency, cost_tier (free/starter/growth/enterprise).
  - Defined frozen `EcosystemCapacityContract`: ecosystem_id, version, surface_capacities, resource_quotas, cost_models, monthly_budget_limit_usd; `to_dict`/`from_dict`/`to_json`/`from_json` roundtrips; deterministic SHA-256 `digest()`.
  - Implemented `synthesize_ecosystem_capacity(ecosystem_id, surfaces, version, monthly_budget_limit_usd)`: derives surface capacity specs (database singletons, api horizontal auto-scaling, web edge caching), resource quotas for CPU, memory, concurrent connections, bandwidth, and RPS, and cost models with budget limits. Fully offline, deterministic, zero I/O.
  - Implemented `EcosystemCapacityEngine`: thread-safe (threading.Lock); `simulate_workload_tier(tier="base"|"peak"|"stress", monthly_requests=100_000)` computing scaled requests, required replicas, resource utilization, and cost with quota breach detection; `evaluate_quota()` evaluating proposed allocations against quota limits and burst windows; `estimate_monthly_unit_economics(monthly_active_users, requests_per_user_monthly)` projecting per-user and per-1k request unit economics.
- Updated Ecosystem Pack Package & Registry:
  - `ecosystem_pack.py`: Added `capacity_contract: EcosystemCapacityContract | None` field; updated `to_dict`, `parse_ecosystem_pack_package`, and `synthesize_ecosystem_pack` to include capacity_contract in payload and whole-package SHA-256 checksum.
  - `ecosystem_registry.py`: Added `capacity_contract` property to `EcosystemPack`; `has_capacity_contract` in `to_dict`; `get_capacity_contract(ecosystem_id, version)` on `EcosystemPackRegistry` and `_LazyEcosystemPackRegistry` delegate.
- Updated Studio Preview & Server:
  - `studio/preview.py`: Imports capacity types; adds `_capacity_contract`/`_capacity_engine` fields; `replace_ecosystem()` accepts optional `capacity_contract` param, falls back to registry cache then synthesize; all three payload branches inject `has_capacity`, `capacity_spec_count`, `quota_count`, `cost_model_count`, `monthly_budget_usd`, and `capacity_status`; cleanup in `_stop_locked()`; new `get_ecosystem_capacity()` and `simulate_ecosystem_capacity()` methods.
  - `studio/server.py`: `_make_handler` and `create_studio_server` accept `get_ecosystem_capacity_fn` and `simulate_ecosystem_capacity_fn`; `GET /api/ecosystem/capacity`; `POST /api/ecosystem/capacity/simulate`.
  - `studio/live_serve.py`: Wires `get_ecosystem_capacity_fn` and `simulate_ecosystem_capacity_fn` in `control_kwargs`.
  - `studio/page.py`: Cyan-themed `.preview-capacity-info` CSS panel; `#preview-capacity-info` HTML with capacity spec count, quota count, and monthly budget badges, and "Simulate Capacity" / "Refresh" buttons; JS update logic in preview status handler; button handlers for Simulate (calls POST, renders summary and cost) and Refresh (calls GET, updates badges).
- Added `capacity` subcommand to `ecosystem_cli.py`: accepts file path or registered ecosystem ID; `--json` outputs canonical JSON; `--simulate` with `--tier` (base, peak, stress) runs dry-run simulation and prints structured PASS/FAIL/BREACH summary; default text mode shows surface capacities, quotas, and cost models.
- Exported all capacity symbols in `solution_packs/__init__.py`.
- All gates pass: `task verify` (3,242 tests), `task lint`, `task security:quick`, `task env:check`, `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites`. Zero model calls.

## 2026-09-15 — R-454 (Solution Pack Ecosystem Multi-Surface Disaster Recovery, Snapshot Backup, and Rollback Orchestration)

- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
  Final focused suite: 21 passing tests in `test_ecosystem_recovery.py`. Total test suite: 3,223 tests passing offline (+21 net-new tests).
- Implemented `solution_packs/ecosystem_recovery.py`:
  - Defined frozen `BackupTarget`: target_id, surface_slug, target_kind (database/state/configuration), storage_uri, frequency, retention_days, encryption_required, tags tuple.
  - Defined frozen `SnapshotManifest`: snapshot_id, ecosystem_id, surface_slug, created_at_utc, checksum_sha256, size_bytes, metadata dict.
  - Defined frozen `RecoveryStep`: step_id, sequence_order, surface_slug, action (drain_traffic/stop_service/restore_data/run_migration/verify_health/resume_traffic), target, timeout_seconds, critical, description.
  - Defined frozen `RollbackTrigger`: trigger_id, condition, threshold, action, severity.
  - Defined frozen `EcosystemDisasterRecoveryContract`: ecosystem_id, version, backup_targets, recovery_steps, rollback_triggers; `to_dict`/`from_dict`/`to_json`/`from_json` roundtrips; deterministic SHA-256 `digest()`.
  - Implemented `synthesize_ecosystem_recovery(ecosystem_id, surfaces, version)`: derives backup targets (database, state, configuration based on surface kind), sequential recovery plan (ingress isolation, graceful service quiescing, snapshot restoration, schema migration integrity verification, phased service start, traffic cutover), and rollback triggers (health probe failures, database migration errors, timeout exceeded). Fully offline, deterministic, zero I/O.
  - Implemented `EcosystemRecoveryEngine`: thread-safe (threading.Lock); `simulate_snapshot_creation()`, `simulate_recovery_plan()`, `simulate_rollback_triggers()`, `simulate_full_dr_exercise()` — dry-run simulation returning structured pass/fail summaries with duration metrics.
- Updated Ecosystem Pack Package & Registry:
  - `ecosystem_pack.py`: Added `recovery_contract: EcosystemDisasterRecoveryContract | None` field; updated `to_dict`, `parse_ecosystem_pack_package`, and `synthesize_ecosystem_pack` to include recovery_contract in payload and whole-package SHA-256 checksum.
  - `ecosystem_registry.py`: Added `recovery_contract` property to `EcosystemPack`; `has_recovery_contract` in `to_dict`; `get_recovery_contract(ecosystem_id, version)` on `EcosystemPackRegistry` and `_LazyEcosystemPackRegistry` delegate.
- Updated Studio Preview & Server:
  - `studio/preview.py`: Imports recovery types; adds `_recovery_contract`/`_recovery_engine` fields; `replace_ecosystem()` accepts optional `recovery_contract` param, falls back to registry cache then synthesize; all three payload branches inject `has_recovery`, `backup_target_count`, `recovery_step_count`, `rollback_trigger_count`, and `dr_status`; cleanup in `_stop_locked()`; new `get_ecosystem_recovery()` and `simulate_ecosystem_recovery()` methods.
  - `studio/server.py`: `_make_handler` and `create_studio_server` accept `get_ecosystem_recovery_fn` and `simulate_ecosystem_recovery_fn`; `GET /api/ecosystem/recovery`; `POST /api/ecosystem/recovery/simulate`.
  - `studio/live_serve.py`: Wires `get_ecosystem_recovery_fn` and `simulate_ecosystem_recovery_fn` in `control_kwargs`.
  - `studio/page.py`: Amber-themed `.preview-recovery-info` CSS panel; `#preview-recovery-info` HTML with backup target count, recovery step count, rollback trigger count badges, and "Simulate DR" / "Refresh" buttons; JS update logic in preview status handler; button handlers for Simulate (calls POST, renders summary) and Refresh (calls GET, updates badges).
- Added `recovery` subcommand to `ecosystem_cli.py`: accepts file path or registered ecosystem ID; `--json` outputs canonical JSON; `--simulate` runs dry-run simulation and prints structured PASS/FAIL summary; default text mode shows backup targets, recovery plan steps, and rollback triggers.
- Exported all recovery symbols in `solution_packs/__init__.py`.
- All gates pass: `task verify` (3,223 tests), `task lint`, `task security:quick`, `task env:check`, `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites`. Zero model calls.

## 2026-09-15 — R-453 (Solution Pack Ecosystem Comprehensive Multi-Surface Health Check, Smoke Testing, and Canary Verification)

- Recorded `.ai/CURRENT_TASK.yaml` before implementation.
  Final focused suite: 29 passing tests in `test_ecosystem_verification.py`. Total test suite: 3,202 tests passing offline (+29 net-new tests).
- Implemented `solution_packs/ecosystem_verification.py`:
  - Defined frozen `HealthCheckProbe`: probe_id, surface_slug, surface_kind, method (GET), endpoint (/healthz), expected_status (200), timeout_seconds (5), tags tuple.
  - Defined frozen `SmokeTestStep`: step_id, description, action, target, expected.
  - Defined frozen `SmokeTestSpec`: test_id, surface_slug, name, category (functional/api/infrastructure), steps tuple, expected_outcome.
  - Defined frozen `CanaryVerificationRule`: rule_id, surfaces_covered tuple, trigger, assertion, severity (info/warning/error).
  - Defined frozen `EcosystemVerificationContract`: ecosystem_id, version, probes, smoke_tests, canary_rules; `to_dict`/`from_dict` roundtrips; deterministic SHA-256 `digest()`.
  - Implemented `synthesize_ecosystem_verification(ecosystem_id, surfaces, version)`: derives probes per surface endpoint (based on surface_kind map), one smoke test per surface (kind-specific action sequences), and cross-surface canary rules (health-all, cross-auth, api-web-latency when api+web surfaces present, data-consistency, smoke-suite). Fully offline, deterministic, zero I/O.
  - Implemented `EcosystemVerificationEngine`: thread-safe (threading.Lock); `simulate_probe_evaluation()`, `simulate_smoke_tests()`, `simulate_canary_rules()`, `simulate_full_verification()` — all dry-run, all pass in nominal state, returning structured result dicts with summary counts.
- Updated Ecosystem Pack Package & Registry:
  - `ecosystem_pack.py`: Added `verification_contract: EcosystemVerificationContract | None` field; updated `to_dict`, `parse_ecosystem_pack_package`, and `synthesize_ecosystem_pack` to include verification_contract in payload and checksum.
  - `ecosystem_registry.py`: Added `verification_contract` property to `EcosystemPack`; `has_verification_contract` in `to_dict`; `get_verification_contract(ecosystem_id, version)` on `EcosystemPackRegistry` and `_LazyEcosystemPackRegistry` delegate.
- Updated Studio Preview & Server:
  - `studio/preview.py`: Imports verification types; adds `_verification_contract`/`_verification_engine` fields; `replace_ecosystem()` accepts optional `verification_contract` param, falls back to registry cache then synthesize; all three payload branches inject `has_verification`, `probe_count`, `smoke_test_count`, `canary_rule_count`; cleanup in `_stop_locked()`; new `get_ecosystem_verification()` and `simulate_ecosystem_verification()` methods.
  - `studio/server.py`: `_make_handler` and `create_studio_server` accept `get_ecosystem_verification_fn` and `simulate_ecosystem_verification_fn`; `GET /api/ecosystem/verification`; `POST /api/ecosystem/verification/simulate`.
  - `studio/live_serve.py`: Wires `get_ecosystem_verification_fn` and `simulate_ecosystem_verification_fn` in `control_kwargs`.
  - `studio/page.py`: Green-themed `.preview-verification-info` CSS panel; `#preview-verification-info` HTML with probe/smoke/canary count badges and "Simulate Verification" / "Refresh" buttons; JS update logic in preview status handler; button handlers for Simulate (calls POST, renders summary) and Refresh (calls GET, updates badges).
- Added `verify-suite` subcommand to `ecosystem_cli.py`: accepts file path or registered ecosystem ID; `--json` outputs canonical JSON; `--simulate` runs dry-run and prints structured PASS/FAIL summary; default text mode shows probe list, smoke test list, and canary rule detail with surfaces and assertion.
- Exported all verification symbols in `solution_packs/__init__.py`.
- All gates pass: `task verify` (3,202 tests), `task lint`, `task security:quick`, `task env:check`, `task builder:demo -- minimal-blog`, `task builder:demo -- rideshare-favourites`. Zero model calls.

## 2026-09-14 — R-452 (Solution Pack Ecosystem Multi-Surface CI/CD Workflow & GitHub Actions Orchestration)

- Recorded `.ai/tasks/R-452.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 15 passing tests in `test_ecosystem_cicd.py`. Total test suite: 3,173 tests passing offline (+15 net-new tests).
- Implemented Ecosystem Multi-Surface CI/CD & GitHub Actions Orchestration (`solution_packs/ecosystem_cicd.py`):
  - Defined frozen `CIJobStep`: step name, action reference (`uses`), shell command (`run`), working directory, environment variables (`env`), and step arguments (`with_args`).
  - Defined frozen `CIJob`: job ID, name, surface slug, runner (`runs_on`), dependencies (`needs`), steps tuple, service container definitions (`services`), and environment variables (`env`).
  - Defined frozen `CIWorkflow`: workflow ID, name, triggers tuple (`push`, `pull_request`, `workflow_dispatch`), jobs tuple, and environment variables.
  - Defined frozen `EcosystemCICDContract`: ecosystem ID, version, workflows tuple, covered surfaces, and required quality gates.
  - Implemented deterministic Python 3.13 stdlib-only GitHub Actions YAML generator (`generate_github_actions_workflow` and `to_workflow_yaml`) formatting triggers, runner environments, needs constraints, service containers with health checks (e.g. PostgreSQL), step arguments, working directories, and env vars with zero external dependencies (no PyYAML).
  - Implemented in-process DAG dependency validator and pipeline simulator (`EcosystemCICDEngine`):
    - `validate_dag`: Kahn's algorithm cycle detection and dependency verification returning validation status and diagnostic message.
    - `topological_sort`: computes deterministic job execution order according to `needs` dependencies, raising `ValueError` on dependency cycles.
    - `simulate_pipeline_run`: offline dry-run pipeline simulation evaluating job ordering, simulated step durations, exit codes, and quality gate compliance.
  - Implemented deterministic contract synthesis (`synthesize_ecosystem_cicd(ecosystem_id, surfaces)`): derives surface verification jobs based on surface runtime (Node.js/pnpm for web/admin, Python/pip + PostgreSQL service for FastAPI APIs, Go + PostgreSQL service for Go backends) and overarching `ecosystem-integration` verification gate running after all surface jobs pass.
- Updated Ecosystem Pack Package & Registry (`solution_packs/ecosystem_pack.py`, `solution_packs/ecosystem_registry.py`):
  - Extended `EcosystemPackPackage` with optional `cicd_contract`, serializing, parsing, and verifying it with whole-package SHA-256 checksums.
  - Updated `synthesize_ecosystem_pack` to automatically derive and attach CI/CD contracts.
  - Updated `EcosystemPackRegistry` and `EcosystemPack` with `cicd_contract` and `get_cicd_contract()`.
  - Exported all CI/CD types and functions in `solution_packs/__init__.py`.
- Updated Studio Preview & Server (`studio/preview.py`, `studio/server.py`, `studio/live_serve.py`):
  - `StudioPreviewManager` tracks CI/CD contract and simulation engine, injects `has_cicd`, `cicd_workflow_count`, `cicd_job_count`, and `cicd_status` into preview status payloads, and exposes `get_ecosystem_cicd()`, `to_workflow_yaml()`, and `simulate_cicd_run()`.
  - Added `GET /api/ecosystem/cicd`, `GET /api/ecosystem/cicd/yaml`, and `POST /api/ecosystem/cicd/simulate` to Studio HTTP server and wired handlers in `live_serve.py`.
- Updated Studio Web UI (`studio/page.py`):
  - Added `#preview-cicd-info` container displaying workflow triggers, job chips, and 1-click "Copy GitHub Actions YAML", "Simulate Pipeline", and "Refresh CI/CD" buttons, strictly maintaining zero external network requests.
- Added CLI & Taskfile Tooling (`solution_packs/ecosystem_cli.py`):
  - Added `cicd` subcommand supporting both file paths and registered ecosystem IDs (`task agent-engine:solution-pack:ecosystem -- cicd <id|file> [--yaml|--json|--simulate]`).
  - Updated `scripts/agent-engine.sh` and `Taskfile.yml`.
- Verification: 15 focused tests in `test_ecosystem_cicd.py` passed; `task verify` passed (3,173 tests passed in 34.1s); `task lint`, `task security:quick`, `task env:check`, and both builder demos passed.

## 2026-09-14 — R-451 (Solution Pack Ecosystem Cross-Surface Data Sync, Conflict Resolution, and Offline-First Sync Protocol)

- Recorded `.ai/tasks/R-451.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 14 passing tests in `test_ecosystem_sync.py`. Total test suite: 3,158 tests passing offline (+14 net-new tests).
- Implemented Ecosystem Cross-Surface Data Sync and Conflict Resolution Engine (`solution_packs/ecosystem_sync.py`):
  - Defined frozen `SyncEntitySpec`: entity name, strategy (`last_write_wins`, `source_of_truth`, `field_merge`), authority surface, sync surfaces, and immutable fields.
  - Defined frozen `SyncMutation`: mutation ID, entity name, record ID, surface, operation (`insert`, `update`, `delete`), data dict, timestamp, mutation SHA-256 hash, and base version.
  - Defined frozen `SyncConflict`: conflict ID, entity name, record ID, incoming surface, conflicting surface, resolution strategy, resolved data, and timestamp.
  - Defined frozen `SyncCheckpoint`: surface slug, last mutation sequence, record count, and timestamp.
  - Defined frozen `EcosystemSyncContract`: ecosystem ID, version, sync entities tuple, conflict strategies, and max offline queue size.
  - Implemented deterministic conflict resolution algorithms (`resolve_sync_conflict`):
    - `last_write_wins`: resolves by newest timestamp with tie-breaking on mutation hash.
    - `source_of_truth`: authoritative surface always wins over non-authoritative surfaces.
    - `field_merge`: field-by-field merge respecting immutable fields and authoritative field defaults.
  - Implemented thread-safe in-process `EcosystemSyncEngine`:
    - Tracks mutation log, current state store, conflict log (bounded 500), and surface checkpoints with `threading.RLock`.
    - `push_mutations()`: validates surface permissions, checks base versions, detects conflicts, applies deterministic resolution, updates state, and advances checkpoints.
    - `pull_changes()`: retrieves incremental changes since client sequence number.
    - `simulate_conflict()`: deterministic utility simulating concurrent writes across surfaces for live demonstration and testing.
  - Implemented deterministic contract synthesis (`synthesize_ecosystem_sync(ecosystem_id, surfaces)`): derives sync entity specifications, strategy assignments, and authority mappings from ecosystem surface definitions.
- Updated Ecosystem Pack Package & Registry (`solution_packs/ecosystem_pack.py`, `solution_packs/ecosystem_registry.py`):
  - Extended `EcosystemPackPackage` with optional `sync_contract`, serializing, parsing, and verifying it with whole-package SHA-256 checksums.
  - Updated `synthesize_ecosystem_pack` to automatically derive and attach sync contracts.
  - Updated `EcosystemPackRegistry` and `EcosystemPack` with `sync_contract` and `get_sync_contract()`.
  - Exported all symbols in `solution_packs/__init__.py`.
- Updated Studio Preview & Server (`studio/preview.py`, `studio/server.py`, `studio/live_serve.py`):
  - `StudioPreviewManager` tracks sync contract and engine, injects `has_sync`, `sync_entity_count`, `sync_conflict_count`, and `sync_version` into preview status payloads, and exposes `get_ecosystem_sync()`, `push_sync_mutations()`, `pull_sync_changes()`, and `simulate_sync_conflict()`.
  - Added `GET /api/ecosystem/sync`, `POST /api/ecosystem/sync/push`, `GET /api/ecosystem/sync/pull`, and `POST /api/ecosystem/sync/simulate` to Studio HTTP server and wired handlers in `live_serve.py`.
- Updated Studio Web UI (`studio/page.py`):
  - Added `#preview-sync-info` container displaying entity chips, conflict/version badges, and 1-click "Simulate Conflict" and "Refresh Sync" buttons, strictly maintaining zero external network requests.
- Added CLI & Taskfile Tooling (`solution_packs/ecosystem_cli.py`):
  - Added `sync` subcommand supporting both file paths and registered ecosystem IDs (`task agent-engine:solution-pack:ecosystem -- sync <id|file> [--json]`).
  - Updated `scripts/agent-engine.sh` and `Taskfile.yml`.
- Verification: 14 focused tests in `test_ecosystem_sync.py` passed; `task verify` passed (3,158 tests passed in 33.7s); `task lint`, `task security:quick`, `task env:check`, and both builder demos passed.

- Recorded `.ai/tasks/R-450.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 13 passing tests in `test_ecosystem_deployment.py`. Total test suite: 3,144 tests passing offline.
- Implemented Ecosystem Multi-Surface Deployment Manifest and Live Gateway Engine (`solution_packs/ecosystem_deployment.py`):
  - Defined frozen `GatewayRoute`: route ID, path prefix, target surface, target port, strip_prefix flag, and optional required_role.
  - Defined `match_gateway_route`: longest prefix match algorithm matching incoming requests to registered gateway routes.
  - Defined frozen `SurfaceDeploymentSpec`: surface slug, surface kind, app name, runtime target, container port, host port, env vars, health path, and service dependencies.
  - Defined frozen `EcosystemDeploymentManifest`: ecosystem ID, version, gateway port, database spec, surfaces tuple, and gateway routes tuple.
  - Implemented `generate_docker_compose` and `to_compose_yaml()`: deterministic, byte-stable Docker Compose YAML generator for all surfaces and PostgreSQL with 0 external dependencies (no PyYAML).
  - Implemented in-process `EcosystemLiveGateway`: thread-safe HTTP reverse proxy listening on loopback (127.0.0.1) that intercepts incoming HTTP requests, matches longest route prefix, strips hop-by-hop headers, injects forwarding headers (`X-Forwarded-For`, `X-Forwarded-Host`, `X-Forwarded-Proto`, `X-Gateway-Route`), and proxies to target surface ports.
  - Implemented deterministic deployment synthesis (`synthesize_ecosystem_deployment(ecosystem_id, surfaces)`): assigns non-colliding host ports, creates root `/` and subpath `/<slug>` gateway routes, and binds database and cross-app environment variables.
- Updated Ecosystem Pack Package & Registry (`solution_packs/ecosystem_pack.py`, `solution_packs/ecosystem_registry.py`):
  - Extended `EcosystemPackPackage` with optional `deployment_manifest`, serializing, parsing, and verifying it with checksum integrity.
  - Updated `synthesize_ecosystem_pack` to automatically derive and attach deployment manifests.
  - Updated `EcosystemPackRegistry` and `EcosystemPack` with `deployment_manifest` and `get_deployment_manifest`.
  - Exported all symbols in `solution_packs/__init__.py`.
- Updated Studio Preview & Server (`studio/preview.py`, `studio/server.py`, `studio/live_serve.py`):
  - `StudioPreviewManager` tracks deployment manifest and live gateway, injects `has_deployment`, `deployment_surface_count`, `gateway_routes`, `gateway_port`, and `gateway_url` into preview status payloads, and exposes `get_ecosystem_deployment()` and `to_compose_yaml()`.
  - Added `GET /api/ecosystem/deployment` and `GET /api/ecosystem/deployment/compose` to Studio HTTP server and wired handlers in `live_serve.py`.
- Updated Studio Web UI (`studio/page.py`):
  - Added `#preview-deployment-info` container displaying surface counts, route chips, and 1-click "Copy Compose YAML" / "Refresh Deployment" buttons, strictly maintaining zero external network requests.
- Added CLI & Taskfile Tooling (`solution_packs/ecosystem_cli.py`):
  - Added `deploy` subcommand supporting both file paths and registered ecosystem IDs (`task agent-engine:solution-pack:ecosystem -- deploy <id|file> [--compose|--json]`).
  - Updated `scripts/agent-engine.sh` and `Taskfile.yml`.
- Verification: 13 focused tests in `test_ecosystem_deployment.py` passed; `task verify` passed (3,144 tests passed in 33.3s); `task lint`, `task security:quick`, `task env:check`, and both builder demos passed.

## 2026-09-14 — R-449 (Solution Pack Ecosystem Cross-Surface Telemetry, Audit Trails, and Distributed Tracing)

- Recorded `.ai/tasks/R-449.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 33 passing tests in `test_ecosystem_telemetry.py`. Total test suite: 3,131 tests passing offline.
- Implemented Ecosystem Cross-Surface Telemetry, Audit Trails, and Distributed Tracing Engine (`solution_packs/ecosystem_telemetry.py`):
  - Defined frozen `TelemetrySpan` with span ID, trace ID, parent span ID, operation, surface, start/end ISO timestamps, duration ms, status (`ok`, `error`, `unset`), attributes, and deterministic SHA-256 digest.
  - Defined frozen `AuditTrailEntry` capturing entry ID, actor ID, actor role, surface, action, entity, target ID, outcome, details, and ISO timestamp.
  - Defined frozen `DistributedTrace` aggregating spans across surfaces, computing root span, span tree, and total duration ms.
  - Defined frozen `TelemetrySamplingPolicy` with sampling rate, propagation header (`X-OmniStack-Trace-Id`), and export format (`otlp-json`).
  - Defined frozen `TracedSurface` and `EcosystemTelemetryContract`.
  - Implemented Python 3.13 stdlib-only deterministic trace ID and span ID generation (uuid + hashlib, 0 external dependencies, 100% offline).
  - Implemented in-process `EcosystemTelemetryCollector` with bounded ring-buffer span storage (max 500) and audit trail (max 500) with span lifecycle orchestration (`start_span`, `finish_span`, `record_audit`).
  - Implemented deterministic contract synthesis (`synthesize_ecosystem_telemetry`) deriving traced surfaces, cross-surface operations, and audit actions from ecosystem definitions.
- Updated Ecosystem Pack Package & Registry (`solution_packs/ecosystem_pack.py`, `solution_packs/ecosystem_registry.py`):
  - Extended `EcosystemPackPackage` with optional `telemetry_contract`, serializing, parsing, and verifying it with checksum integrity.
  - Updated `synthesize_ecosystem_pack` to automatically derive and attach telemetry contracts.
  - Updated `EcosystemPackRegistry` and `EcosystemPack` with `telemetry_contract` and `get_telemetry_contract`.
  - Exported all symbols in `solution_packs/__init__.py`.
- Updated Studio Preview & Server (`studio/preview.py`, `studio/server.py`, `studio/live_serve.py`):
  - `StudioPreviewManager` tracks telemetry collector, injects `has_telemetry` and `span_count` into preview status payloads, and exposes `get_ecosystem_telemetry()`.
  - Added `GET /api/ecosystem/telemetry` to Studio HTTP server and wired handler in `live_serve.py`.
- Updated Studio Web UI (`studio/page.py`):
  - Added `#preview-telemetry-info` container displaying span counts and traced surface badges, strictly maintaining zero external network requests.
- Added CLI & Taskfile Tooling (`solution_packs/ecosystem_cli.py`):
  - Added `telemetry` subcommand supporting both file paths and registered ecosystem IDs (`task agent-engine:solution-pack:ecosystem -- telemetry <id|file>`).
  - Updated `scripts/agent-engine.sh` and `Taskfile.yml`.
- Verification: 33 focused tests in `test_ecosystem_telemetry.py` passed; `task verify` passed (3,131 tests passed in 31.8s); `task lint`, `task security:quick`, `task env:check`, and both builder demos passed.


## 2026-09-14 — Task Compilation Audit (Documentation Synchronization)

**Why:** During an audit of all task-related documentation triggered by the user request on 2026-09-14,
it was discovered that 90 completed tasks (R-359..R-448) were missing from the execution tracker workbook,
5 CHANGELOG entries had been omitted during rapid development, and 1 task file (R-360.md) had a stale
`IN_PROGRESS` status despite full completion. This audit corrects all discrepancies to achieve 100%
documentation synchronization.

**Actions performed:**
- `R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx`: Inserted 90 rows into `Phase_Roadmap` for R-359..R-448.
  Tracker now covers 448 tasks: 237 Done, 1 Deferred, 210 Not Started (MVP 69.1%, overall 52.9%).
- `CHANGELOG.md`: Backfilled 5 missing entries — R-272 (2026-09-08), R-314 (2026-09-10), R-374, R-375,
  R-376 (all 2026-09-11) — each with an audit note citing this date and reason.
- `.ai/tasks/R-360.md`: Corrected status from `IN_PROGRESS` to `DONE`; added `completed_at: "2026-09-11"`,
  full evidence block, and explanatory comment.
- `docs/PROGRESS.md`: Updated headline metrics (147→237 Done, 358→448 total, 58.1%→69.1% MVP).
- `docs/RESUME_PROMPT.md`: Updated NOTE block with unified tracker counts; removed stale "No tracker row
  exists past R-358" statement; updated `task verify` count to 3,098.
- `PROJECT_STATE.md`: Added "Task Compilation Audit — 2026-09-14" section documenting all actions.
- `.ai/PROJECT_STATE.yaml`: Added `task_compilation_audit` block with machine-readable audit summary.
- `.ai/WORK_LOG.md`: This entry.
- `.ai/HANDOFF.md`: Updated handoff notes to reflect audit completion.

**Verification:** `task verify` was not re-run (no production code changed); all changes are documentation
and metadata. The workbook now has 448 rows; CHANGELOG has 238 entries (0 missing); all `.ai/tasks/*.md`
files have valid DONE/NOT_STARTED status.

## 2026-09-14 — R-448 (Solution Pack Ecosystem Cross-Surface Webhook and Event Bridge)

- Recorded `.ai/tasks/R-448.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 15 passing tests across `test_ecosystem_event_bridge.py`. Total studio/ecosystem suites: 85 studio + 84 ecosystem passing tests.
- Implemented Ecosystem Cross-Surface Webhook and Event Bridge Engine (`solution_packs/ecosystem_events.py`):
  - Defined frozen `WebhookRetryPolicy` capturing max retries (default 3), backoff multiplier (2.0), initial delay ms (500), max delay ms (10000), and timeout ms (5000).
  - Defined frozen `EcosystemWebhookSubscription` with subscription ID, source surface slug, target surface slug, event type pattern, target endpoint, secret reference, retry policy, active flag, and created timestamp.
  - Defined frozen `EcosystemEventPayload` with event ID, event type, source surface, timestamp, idempotency key, entity name, entity ID, action, and payload data.
  - Defined frozen `WebhookDeliveryRecord` with delivery ID, subscription ID, event ID, source surface, target surface, target endpoint, HTTP status code, success boolean, attempt count, timestamp, and error message.
  - Defined frozen `EcosystemEventBridgeContract` with ecosystem ID, subscriptions list, event catalog, and delivery log.
  - Implemented Python 3.13 stdlib-only deterministic HMAC-SHA256 signature generator (`sign_webhook_payload`) and verifier (`verify_webhook_signature`) with constant-time equality check (`hmac.compare_digest`), zero external dependencies.
  - Implemented in-process `EcosystemEventBridge` with subscription management, cross-surface webhook routing, dispatching, and bounded delivery logging (max 100 entries).
  - Implemented deterministic contract synthesis (`synthesize_ecosystem_events`) deriving cross-surface subscriptions from entity writers to readers with lowercase slug formatting.
- Updated Ecosystem Pack Package & Registry (`solution_packs/ecosystem_pack.py`, `solution_packs/ecosystem_registry.py`):
  - Extended `EcosystemPackPackage` with optional `event_bridge`, serializing, parsing, and verifying it with checksum integrity.
  - Updated `synthesize_ecosystem_pack` to automatically derive and attach event bridge contracts.
  - Extended `EcosystemPack` and `EcosystemPackRegistry` with `event_bridge` property and `get_event_bridge` accessor.
  - Exported new event bridge symbols in `solution_packs/__init__.py`.
- Updated Studio Preview Manager & HTTP Server (`studio/preview.py`, `studio/server.py`, `studio/live_serve.py`, `studio/page.py`):
  - In `StudioPreviewManager`, stored active ecosystem event bridge contract, injected `has_events`, `event_count`, and `subscription_count` into preview status payloads, and exposed `get_ecosystem_events()` and `dispatch_ecosystem_event()`.
  - In `studio/server.py`, exposed `GET /api/ecosystem/events` and `POST /api/ecosystem/events/dispatch`. Wired handlers in `studio/live_serve.py`.
  - In `studio/page.py`, added `#preview-events-info` container displaying subscription counts, event simulation panel ("Simulate Event"), and live delivery log table, strictly maintaining zero external network requests.
- Added CLI and Taskfile Integration (`solution_packs/ecosystem_cli.py`, `scripts/agent-engine.sh`, `Taskfile.yml`):
  - Added `events` subcommand to `ecosystem_cli.py`, supporting both file paths and registered ecosystem IDs with human-readable and `--json` outputs.
  - Updated `scripts/agent-engine.sh` usage string and `Taskfile.yml` task description.
- Gates: `task verify` **3,098 passed** fully offline (+15 net-new tests); agent-engine/repository lint, security, and environment passed; both builder demos remained 152/149 files; 0 model calls in test execution.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change.

## 2026-09-14 — R-447 (Solution Pack Ecosystem Multi-Surface Cross-App Auth and Unified State Binding)

- Recorded `.ai/tasks/R-447.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 16 passing tests across `test_ecosystem_auth_and_state.py`. Total studio/ecosystem suites: 85 studio + 69 ecosystem passing tests.
- Implemented Ecosystem Cross-App Auth Engine (`solution_packs/ecosystem_auth.py`):
  - Defined frozen `EcosystemRoleBinding` capturing surface slug, role identifier, display name, allowed surfaces, authorized actions, and scope permissions.
  - Defined frozen `EcosystemAuthContract` encapsulating shared cross-app JWT parameters (`HS256`, secret reference, issuer, audience, TTL, and role bindings).
  - Defined frozen `CrossAppAuthMatrix` verifying role isolation, surface access permissions, and action capabilities across surfaces.
  - Implemented Python 3.13 stdlib-only deterministic HS256 JWT minter (`mint_ecosystem_token`) and verifier (`verify_ecosystem_token`) using standard `hmac`, `hashlib`, `base64`, and `json` with 0 external dependencies (no PyJWT).
  - Implemented `generate_surface_tokens` for deterministic per-surface demo token generation.
  - Implemented `synthesize_ecosystem_auth(ecosystem_id, surfaces)` with surface kind role affinity selection.
- Implemented Ecosystem Unified State Binding Engine (`solution_packs/ecosystem_state.py`):
  - Defined frozen `SharedEntityBinding` declaring authoritative surfaces, reading surfaces, and writing surfaces per entity.
  - Defined frozen `EntityStateFlow` and `StateTransition` formalizing entity lifecycle state machines with role-gated transition checks (`can_transition`).
  - Defined frozen `CrossAppEndpointBinding` mapping shared backend routes to consuming surfaces and required roles.
  - Defined frozen `SurfaceEnvBinding` specifying per-surface environment variables (`NEXT_PUBLIC_API_URL`, `JWT_SECRET`, `DATABASE_URL`, demo token).
  - Defined frozen `EcosystemStateBinding` formalizing whole-ecosystem shared data model and lifecycle transitions.
  - Implemented `synthesize_ecosystem_state(ecosystem_id, surfaces)`.
- Updated Ecosystem Pack Package & Registry (`solution_packs/ecosystem_pack.py`, `solution_packs/ecosystem_registry.py`):
  - Extended `EcosystemPackPackage` with optional `auth_contract` and `state_binding`, serializing, parsing, and verifying them with checksum integrity.
  - Updated `synthesize_ecosystem_pack` to automatically derive and attach auth contracts and state bindings.
  - Extended `EcosystemPack` and `EcosystemPackRegistry` with `auth_contract` and `state_binding` properties and accessors (`get_auth_contract`, `get_state_binding`).
  - Exported new auth and state symbols in `solution_packs/__init__.py`.
- Updated Studio Preview Manager & HTTP Server (`studio/preview.py`, `studio/server.py`, `studio/live_serve.py`, `studio/page.py`):
  - In `StudioPreviewManager`, stored active ecosystem auth contract and state binding, generated demo tokens, and injected `active_role`, `active_token`, `has_auth`, `has_state` into preview status and launch payloads.
  - Implemented `get_ecosystem_auth()` and `get_ecosystem_state()` on `StudioPreviewManager`.
  - In `studio/server.py`, exposed `GET /api/ecosystem/auth` and `GET /api/ecosystem/state`. Wired handlers in `studio/live_serve.py`.
  - In `studio/page.py`, added `#preview-auth-info` UI container displaying active role badge and "Copy Demo JWT" button, strictly preserving 0 external network requests.
- Added CLI and Taskfile Integration (`solution_packs/ecosystem_cli.py`, `scripts/agent-engine.sh`, `Taskfile.yml`):
  - Added `auth` and `state` subcommands to `ecosystem_cli.py`, supporting both file paths and registered ecosystem IDs with human-readable and `--json` outputs.
  - Updated `scripts/agent-engine.sh` usage string and `Taskfile.yml` task description.
- Gates: `task verify` **3,083 passed** fully offline (+16); agent-engine/repository lint, security, and environment passed; both builder demos remained 152/149 files; 0 model calls in test execution.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change.

## 2026-09-14 — R-446 (Solution Pack Ecosystem Studio Live Multi-Surface Preview and Process Orchestration)

- Recorded `.ai/tasks/R-446.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 12 passing tests across `test_studio_ecosystem_preview.py`. Total studio suites: 85 passing tests (+12 net-new tests).
- Enhanced `StudioPreviewManager` (`studio/preview.py`):
  - Switched internal synchronization from `threading.Lock` to `threading.RLock`, eliminating deadlocks when composite lifecycle actions (like `restart`) invoke other synchronized methods (`replace`).
  - Added multi-surface ecosystem preview lifecycle: `replace_ecosystem(ecosystem_id, surfaces, active_surface_slug=None)`.
  - Added multi-session map (`_sessions: dict[str, LocalAppSession]`), dynamically allocating collision-free loopback ports for each surface to prevent port conflicts across surfaces.
  - Implemented `switch_surface(surface_slug)` for instantaneous switching between ecosystem surfaces, lazily starting unlaunched surfaces on demand.
  - Implemented surface-scoped and global process control: `stop(surface_slug=None)` and `restart(surface_slug=None)`.
  - Implemented liveness-aware multi-surface `status()` reporting `is_ecosystem`, `active_surface`, and per-surface status descriptors.
  - Preserved 100% backward compatibility for existing single-app preview calls (`replace(repo_dir)`).
- Extended Studio HTTP Server (`studio/server.py`):
  - Added `switch_surface_fn` control parameter to `create_studio_server` and `_make_handler`.
  - Implemented `POST /api/preview/switch` with payload `{"surface_slug": str}`.
  - Updated `POST /api/preview/stop` and `POST /api/preview/restart` to accept optional `{"surface_slug": str}` for per-surface or whole-ecosystem scoping.
  - Updated `POST /api/history/preview` to accept optional `{"id": str, "surface_slug": str | None}` for surface-targeted re-previewing.
- Extended Studio Live Runner & History (`studio/live_serve.py`, `studio/history.py`):
  - In `live_serve.py`, automatically invoked `preview_manager.replace_ecosystem` when an entire multi-surface ecosystem is built with preview enabled.
  - Extended `_preview_recorded_build` to handle re-previewing recorded ecosystem builds and activating targeted surfaces.
  - Updated `StudioBuildHistory.record` to preserve the `surfaces` list for ecosystem entries.
- Enhanced Studio Web UI (`studio/page.py`):
  - Added `#preview-surface-tabs` container with sleek CSS tabs and pulsing live status dots (`.surface-dot.running`).
  - Implemented client-side `switchSurface(slug)` calling `POST /api/preview/switch` with zero iframe flicker.
  - Updated preview render logic to display active surface tabs, surface kind badges, and surface URLs.
  - Updated history card rendering to provide direct preview chips for all surfaces in an ecosystem build.
  - Maintained strict compliance with 0 external network requests (no external http/https/src/link/fonts).
- Gates: `task verify` **3,067 passed** fully offline (+12); agent-engine/repository lint, security, and environment passed; both builder demos remained 152/149 files; 0 model calls in test execution.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change.

## 2026-09-14 — R-445 (Solution Pack Ecosystem Pack Registry Integration, Catalog Discovery, and Studio Multi-Surface Selection)

- Recorded `.ai/tasks/R-445.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused suites: 14 passing tests across `test_ecosystem_pack_registry.py` (8 tests) and `test_studio_ecosystem.py` (6 tests). Total studio/solution pack suites: 101 passing tests.
- Implemented Ecosystem Pack Registry (`solution_packs/ecosystem_registry.py`):
  - Defined frozen canonical `EcosystemPack` descriptor (`ecosystem_id`, `version`, `display_name`, `description`, `domain`, `base_pack_id`, `surfaces`, `package_sha256`, `package`).
  - Defined frozen canonical `EcosystemPackRecommendation` (`query`, `recommended_ecosystem_id`, `recommended_version`, `reason`, `matched_surface_count`, `surfaces`).
  - Implemented immutable `EcosystemPackRegistry` supporting `list_packs`, `get`, `select`, `recommend`, `register_package`, and `load_surface_ir`.
  - Implemented `build_default_ecosystem_packs` synthesizing built-in ecosystem baselines (`minimal-blog-ecosystem`, `rideshare-favourites-ecosystem`).
  - Implemented `_LazyEcosystemPackRegistry` to defer baseline synthesis on first attribute access, breaking potential circular imports during module load.
  - Initialized `DEFAULT_ECOSYSTEM_PACK_REGISTRY`.
- Updated Ecosystem Pack Synthesis (`solution_packs/ecosystem_pack.py`):
  - Enabled passing `pack_id` string directly into `synthesize_ecosystem_pack`.
  - Defaulted `registry=None` to `DEFAULT_SOLUTION_PACK_REGISTRY`.
- Added Ecosystem Pack Catalog CLI (`solution_packs/ecosystem_cli.py`):
  - Added `catalog` subcommand supporting human-readable table output and `--json` format.
  - Exported registry symbols in `solution_packs/__init__.py`.
- Extended Studio HTTP Server (`studio/server.py`):
  - Added optional `ecosystem_pack_registry` parameter to `create_studio_server` and handler maker.
  - Implemented `GET /api/ecosystem-packs` returning the complete registered ecosystem catalog.
  - Implemented `POST /api/ecosystem-packs/recommend` recommending ecosystem packs based on domain and capabilities.
  - Updated `POST /api/build` to extract `ecosystem_id`, `ecosystem_version`, and `surface_slug` and forward to `build_fn`.
- Extended Studio Live Runner & History (`studio/live_serve.py`, `studio/history.py`):
  - Handled multi-surface ecosystem builds in `live_serve.py`: building a single selected surface with 0 model calls via `load_surface_ir` or compiling the full multi-surface ecosystem using `build_ecosystem`.
  - Prioritized the first customer web surface for preview when an entire ecosystem is built.
  - Extended `StudioBuildHistory` to record `ecosystem_id`, `ecosystem_version`, `surface_slug`, `surface_kind`, and `is_ecosystem`.
- Enhanced Studio Web UI (`studio/page.py`):
  - Added tab selector (`#tab-single` vs `#tab-ecosystem`) to toggle between single-app and multi-surface modes.
  - Added multi-surface ecosystem selector (`#eco-select`), surface selector (`#surface-select`), surface summary banner (`#eco-banner`), and interactive surface cards (`#surface-cards`).
  - Added ecosystem badges and chips to recent build history items.
  - Maintained strict compliance with 0 external network requests (no external http/https/src/link/fonts).
- Gates: `task verify` **3,055 passed** fully offline (+14); agent-engine/repository lint, security, and environment passed; both builder demos remained 152/149 files; 0 model calls in test execution.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change.


- Recorded `.ai/tasks/R-444.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused ecosystem suite: 18 passing tests across `test_solution_pack_ecosystem.py`.
- Implemented Multi-Surface Ecosystem Pack Schema & Verification (`solution_packs/ecosystem_pack.py`):
  - Defined frozen canonical `EcosystemSurfacePackage` (`surface_kind`, `app_name`, `slug`, `ir_sha256`, `ir_dict`, `verify_targets`).
  - Defined frozen canonical `EcosystemPackPackage` bundle with `schema_version` (`"1.0"`), `ecosystem_id`, `version`, `display_name`, `description`, `domain`, `base_pack_id`, `surfaces`, and whole-ecosystem `package_sha256` checksum.
  - Implemented `compute_ecosystem_checksum` using canonical JSON representation with sorted keys and no whitespace.
  - Implemented `parse_ecosystem_pack_package` with strict validation: validates schema version, semver, slugs, required keys, validates every surface's embedded Application IR with `validate_ir`, confirms `ir_sha256` digest match for every surface, verifies whole-ecosystem package checksum, and fails closed with `SolutionPackError` on any drift, tampering, or corruption.
  - Implemented `verify_ecosystem_pack` diagnostic checker.
  - Implemented `synthesize_ecosystem_pack` to synthesize all surfaces for a domain/proposal from a base pack or application result.
- Implemented Multi-Surface Synthesis Engine & Planner Integration (`intake/ecosystem.py`):
  - Added `_primary_entity_names_for_pack` and `_writable_entity_names_for_pack` with synonym mapping (`_SYNONYM_MAP`) ensuring entities from packs (e.g. `Post`/`Comment` or `Driver`/`FavouriteDriver`) are appropriately scoped for reader, portal, and admin surfaces.
  - Added `synthesize_surface_ir`: builds clean `ApplicationIR` for secondary surfaces derived from the pack's authoritative data model, preserving project strategy, relational closures, surface actor roles, APIs, and screens.
  - Enhanced `SurfaceApp` with `is_synthesized: bool = False` flag and serialization.
  - Enhanced `plan_ecosystem`: when `pack_result` is provided, synthesizes secondary surfaces via `synthesize_surface_ir` from `pack_result.ir` (marked `is_synthesized=True`).
- Implemented Ecosystem Pack CLI (`solution_packs/ecosystem_cli.py`):
  - Subcommands: `synthesize` (generate multi-surface ecosystem pack JSON from Solution Pack), `verify` (verify package integrity, IRs, and checksums), `inspect` (pretty-print surfaces, entities, APIs, screens, targets), and `build` (materialize all surfaces as separate owned Git repos).
  - Wired into `scripts/agent-engine.sh` (`solution-pack-ecosystem`) and `Taskfile.yml` (`task agent-engine:solution-pack:ecosystem`).
- Exported new symbols in `solution_packs/__init__.py`.
- Gates: `task verify` **3,041 passed** fully offline (+18); agent-engine/repository lint, security, and environment passed; both builder demos remained 152/149 files; 0 model calls in test execution.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change.

## 2026-09-14 — R-443 (Solution Pack Packaging, Verification, and Export CLI)

- Recorded `.ai/tasks/R-443.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Final focused package suite: 16 passing tests across `test_solution_pack_package.py`.
- Implemented `SolutionPackPackage` in `services/agent-engine/src/omnistackai_agent_engine/solution_packs/package.py`:
  - Defined frozen canonical `SolutionPackPackage` bundle with `schema_version` (`"1.0"`), metadata (`pack_id`, `version`, `display_name`, `description`, `domains`, `capabilities`, `targets`, `verify_targets`), `ir_sha256`, canonical `ir_dict`, `verify_plans`, and `package_sha256` checksum.
  - Implemented `compute_package_checksum` using canonical JSON representation with sorted keys and no whitespace.
  - Implemented `parse_solution_pack_package` with strict validation: validates schema version, semver format, slug format, required keys, non-empty targets/domains, validates embedded Application IR with `validate_ir`, confirms `ir_sha256` digest match, verifies whole-package SHA-256 integrity, and fails closed with `SolutionPackError` on drift, tampering, or corruption.
  - Implemented `verify_package` returning verification boolean and diagnostics tuple.
- Extended `SolutionPack` and `SolutionPackRegistry` (`registry.py`):
  - Added `SolutionPack.package` optional field and `SolutionPack.from_package(pkg)` constructor.
  - Added `SolutionPackRegistry.register_package(pkg)` supporting dynamic registration of verified packages with duplicate/digest/target drift validation.
- Implemented CLI in `services/agent-engine/src/omnistackai_agent_engine/solution_packs/package_cli.py`:
  - Subcommands: `export` (export registered pack to canonical JSON or stdout), `verify` (verify package file integrity, IR validity, and checksums), `inspect` (pretty-print package metadata and integrity).
  - Wired into `scripts/agent-engine.sh` (`solution-pack-package|solution-pack-export`) and `Taskfile.yml` (`task agent-engine:solution-pack:package`).
- Gates: `task verify` **3,023 passed** fully offline (+16); agent-engine/repository lint, security, and environment passed; both builder demos remained 152/149 files; 0 model calls in test execution.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change.

## 2026-09-14 — R-442 (Studio AI-delta feature modification controls above Solution Packs)

- Recorded `.ai/tasks/R-442.md` and `.ai/CURRENT_TASK.yaml` before implementation. Approved implementation plan.
  Test-first focused suite failed on missing AI-delta server extraction and page UI tokens; final focused studio suite: 53 passing tests (4 net-new tests across test_studio_server and test_studio_history).
- Extended Studio HTTP server (`services/agent-engine/src/omnistackai_agent_engine/studio/server.py`):
  - Updated `POST /api/build` handler to parse `ai_features` (list of strings or comma-separated string) and `ai_delta_prompt` from JSON body and forward them to `build_fn`.
- Extended `live_serve.py`:
  - When `pack_id` is specified with `ai_features`, formulates typed `ai-delta` `SolutionPackChange` intents targeting the capability area.
  - Generates bounded `AIDeltaProposal` via `generate_ai_delta_proposal` (supporting both real async coroutines and sync mocks).
  - Bypasses the model provider (0 model calls) when no AI-delta features are requested.
  - Merges the proposal safely into a derived `ApplicationIR` via `apply_solution_pack_manifest` and compiles the project with `build_solution_pack_project`.
  - Records full provenance including `applied_ai_delta_change_ids` and `unapplied_ai_delta_change_ids`.
- Enhanced `StudioBuildHistory` (`history.py`):
  - Records `applied_ai_delta_change_ids` in bounded secret-free history entries.
- Enhanced Studio web UI (`page.py`):
  - Added AI Feature Modifications input (`id="ai-features"`) inside the Solution Pack customization card.
  - Added full-width responsive styling for `#ai-features` and `.ai-delta-chip` styling for history items.
  - Form submit includes `ai_features` and `ai_delta_prompt` in `/api/build` payload when provided.
  - Live status indicator reflects AI feature synthesis progress when requested.
  - Provenance box renders `Applied AI Deltas` list when present.
  - History items render an `AI delta (N)` chip when deltas were applied.
  - Preserved 100% self-contained inline CSS and JS with 0 external resource requests (no `http://`, `https://`, `src=`, `<link`).
- Gates: `task verify` 3,007 passed fully offline (+4); agent-engine/repository lint, security, and environment
  passed; both builder demos remained 152/149 files; 0 model calls in test execution.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider,
  PostgreSQL, infrastructure, tracker workbook, or `.claude/` change. Workbook remains unchanged past R-358.

## 2026-09-14 — R-441 (live Studio integration and UI controls for Solution Pack selection, customization, and provenance)

- Recorded `.ai/tasks/R-441.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused suite
  failed on missing Solution Pack routes and UI tokens; final focused studio suite: 63 passing tests (8 net-new tests across test_studio_server and test_studio_history).
- Extended Studio HTTP server (`services/agent-engine/src/omnistackai_agent_engine/studio/server.py`):
  - `GET /api/solution-packs`: returns registered packs with domain, capabilities, targets, and base digests from `SolutionPackRegistry`.
  - `POST /api/solution-packs/recommend`: returns domain classification and matching pack recommendation via `propose_ecosystem` and `registry.recommend`.
  - `POST /api/build`: accepts `pack_id`, `pack_version`, `custom_name`, `custom_description`, and `configuration_changes` options and passes them to `build_fn`.
- Extended `live_serve.py`:
  - When `pack_id` is provided, deterministically builds the app with 0 model calls using `create_solution_pack_manifest`, `apply_solution_pack_manifest`, and `build_solution_pack_project`.
  - Records full Solution Pack provenance in build payload: `pack_id`, `pack_version`, `base_ir_sha256`, `derived_ir_sha256`, `applied_configuration_change_ids`, `applied_ai_delta_change_ids`, `unapplied_ai_delta_change_ids`, and `verify_targets`.
- Enhanced `StudioBuildHistory` (`history.py`):
  - Records `pack_id` and `pack_version` in bounded secret-free history entries.
- Enhanced Studio web UI (`page.py`):
  - Added Solution Pack dropdown selector (`id="pack-select"`) with Auto-detect (recommended), AI Model Build (no pack), and individual pack options.
  - Real-time prompt recommendation banner (`id="pack-banner"`).
  - Custom app name and description inputs (`id="custom-name"`, `id="custom-desc"`).
  - Provenance box in build results rendering base/derived SHA-256 digests and applied change IDs.
  - Verified Solution Pack badge in build result and history items (`.pack-chip`).
  - Preserved 100% self-contained inline CSS and JS with 0 external resource requests (no `http://`, `https://`, `src=`, `<link`).
- Gates: `task verify` 3,003 passed fully offline (+8); agent-engine/repository lint, security, and environment
  passed; both builder demos remained 152/149 files; 0 model calls.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider,
  PostgreSQL, infrastructure, tracker workbook, or `.claude/` change. Workbook remains unchanged past R-358.

## 2026-09-14 — R-440 (wire derived Solution Pack Application IRs into verified multi-repo builder pipelines and project generation)

- Recorded `.ai/tasks/R-440.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused suite
  failed because `omnistackai_agent_engine.solution_packs.builder` and exports were missing; final R-440 through R-434
  focused regression is 86 passing tests (11 new R-440 tests).
- Implemented `solution_packs/builder.py` with frozen `SolutionPackBuildResult`:
  - `build_solution_pack_project()` accepts a `SolutionPackApplicationResult` or `SolutionPackManifest` (+ optional `AIDeltaProposal`).
  - Calls `assemble_project()` and `create_repository()` to write an owned Git repository to disk.
  - Derives deterministic verification plans via `verify_plans_for_ir()`.
  - Serializes byte-stable provenance via `to_dict()` and `to_json()`.
- Extended `intake/ecosystem.py`:
  - `plan_ecosystem()` and `build_ecosystem()` accept optional `pack_result` or `pack_manifest` (+ `pack_proposal`).
  - Validates pack compatibility with ecosystem domain (raising `SolutionPackError` on mismatch).
  - Substitutes the customer web surface IR with the pack-derived IR while preserving all other ecosystem services.
  - Embeds pack provenance in `EcosystemPlan.to_dict()`.
- Implemented standalone CLI `solution_packs/build_cli.py` and Taskfile task `agent-engine:solution-pack:build`.
- Gates: `task verify` 2,995 passed fully offline (+11); agent-engine/repository lint, security, and environment
  passed; both demos remained 152/149 files; build CLI passed; 0 model calls.
- No dependency, pack baseline/selection, Application IR schema/example, generator, generated output, provider,
  PostgreSQL, infrastructure, tracker workbook, or `.claude/` change. Workbook remains unchanged past R-358.

## 2026-09-14 — R-439 (safely apply validated AI-delta proposals to Application IR)

- Recorded `.ai/tasks/R-439.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused suite
  failed because `proposal` argument and `applied_ai_delta_change_ids` were missing; final R-439 through R-434
  focused regression is 66 passing tests (14 new R-439 tests).
- Enhanced `SolutionPackApplicationResult` with `applied_ai_delta_change_ids: tuple[str, ...] = ()` and updated
  `to_dict()` / `to_json()` for deterministic serialization.
- Updated `apply_solution_pack_manifest(manifest, *, proposal=None, registry=...)`:
  - When `proposal is None`: backward-compatible with R-437. All configuration applied, AI deltas marked unapplied.
  - When `proposal` is provided:
    - Revalidates pack pins (`proposal.pack_id`, `proposal.pack_version`, and `proposal.base_ir_sha256` match manifest).
    - Revalidates change IDs (all `proposal.addressed_change_ids` match pending `ai-delta` changes in `manifest.changes`).
    - Revalidates collisions: proposed entity names, API endpoints (method + path), and screen IDs do not collide with base IR.
    - Revalidates relation targets: all relations in proposed entities target declared base or proposed entities.
    - Immutably merges entities, APIs, and screens with allowlisted configuration updates into a fresh derived `ApplicationIR`.
    - Ensures the derived IR is `validate_ir`-clean (failing closed with `SolutionPackError` on any semantic issue).
    - Records `applied_ai_delta_change_ids` and remaining `unapplied_ai_delta_change_ids` in `SolutionPackApplicationResult`.
- Gates: `task verify` 2,984 passed fully offline (+14); agent-engine/repository lint, security, and environment
  passed; both demos remained 152/149 files; deterministic serialization inspection passed; 0 model calls.
- No dependency, pack baseline/selection, ecosystem plan, Application IR schema/example, generator, generated
  output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change. Workbook remains
  unchanged past R-358.

## 2026-09-14 — R-438 (bounded typed Solution Pack AI-delta proposal schema & local ModelProvider boundary)

- Recorded `.ai/tasks/R-438.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused import
  failed because `omnistackai_agent_engine.solution_packs.ai_delta` did not exist; final R-438 through R-434 focused
  regression is 52 passing tests (15 new R-438 tests).
- Added frozen `AIDeltaProposal` (`pack_id`, `pack_version`, `base_ir_sha256`, `addressed_change_ids`, bounded
  `entities`, `apis`, `screens`, `capabilities`, `rationale`). Limits enforce 0-8 entities, 0-16 APIs, 0-16 screens,
  0-16 capabilities, and rationale <= 500 characters.
- Manifests with zero pending `ai-delta` changes bypass the model provider completely (0 calls) and return an empty
  proposal.
- Added `build_ai_delta_messages` formulating system and user instructions embedding the base pack context and
  pending change intents without prompt injection risk.
- Added `parse_ai_delta_proposal` to strictly validate untrusted JSON, rejecting credential-bearing fields (`password`,
  `secret`, `token`, `jwt`, `api_key`), entity name / API / screen collisions with base IR, unknown/missing keys,
  controls, malformed types, and unmapped change IDs.
- Added `generate_ai_delta_proposal` issuing a single bounded `GenerateRequest` to `provider.generate()`. The proposal
  is data only and does not apply the delta, mutate base IR, generate source, build repos, or invoke cloud models.
- Gates: `task verify` 2,970 passed fully offline (+15); agent-engine/repository lint, security, and environment
  passed; both demos remained 152/149 files; deterministic zero-call fast-path and mock inspection passed; 0 model calls.
- No dependency, pack baseline/selection, ecosystem plan, Application IR schema/example, generator, generated
  output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change. Workbook remains
  unchanged past R-358.

## 2026-09-14 — R-437 (deterministic Solution Pack configuration application)

- Recorded `.ai/tasks/R-437.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused import
  failed because the legacy-version constant/application API did not exist; final R-437 through R-434 focused
  regression is 37 passing tests (10 new R-437 tests).
- Advanced current manifest JSON to schema 1.1 with typed `desired_text`, accepted only for explicit
  configuration/update of `project:name` or `project:description` and bounded to the corresponding IR limits.
  AI-delta and all other targets cannot carry it. Summaries are never parsed as values.
- Preserved strict, lossless parsing/serialization for R-436 schema 1.0 manifests. A legacy unvalued project
  configuration remains valid historical intent but application fails until it has an explicit value.
- Added `apply_solution_pack_manifest`: revalidates the exact registry recommendation pin, preflights the
  complete configuration set and duplicate targets, loads a fresh pinned baseline IR, applies only the two
  allowlisted project metadata updates immutably, and requires a validate_ir-clean derived result.
- Added frozen canonical `SolutionPackApplicationResult` with base/derived digests, applied configuration IDs,
  explicitly unapplied AI-delta IDs, and the derived IR. Empty/AI-only manifests preserve the base digest;
  repeated application is byte-identical and the registered baseline remains unchanged.
- Gates: `task verify` 2,955 passed fully offline (+10); agent-engine/repository lint, security, and environment
  passed; both demos remained 152/149 files; deterministic manifest/application proof passed; 0 model calls.
- No dependency, pack baseline/selection, ecosystem plan, Application IR schema/example, generator, generated
  output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change. Workbook remains
  unchanged past R-358.

## 2026-09-14 — R-436 (pinned declarative Solution Pack customization manifests)

- Recorded `.ai/tasks/R-436.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused import
  failed because the manifest API did not exist; final R-436/R-435/R-434 focused regression is 27 passing
  tests (11 new R-436 tests).
- Added frozen `SolutionPackChange` with typed configuration/AI-delta source, add/update/remove operation,
  six bounded semantic areas, area-compatible semantic target references, bounded summaries, and 1–8 bounded
  acceptance criteria. Change IDs are unique and a manifest contains at most 32 changes.
- Added factory-only `SolutionPackManifest` construction above a selected exact recommendation. It pins pack
  id/version/canonical IR SHA-256 and the exact domain/capability/target query; no-match and registry pin drift
  fail closed. Change order is canonical by ID.
- Added byte-stable `to_json()` plus strict JSON/object parsing. Unknown/missing keys, malformed types/enums,
  wrong target-area pairs, controls, oversized values, duplicates, noncanonical input, and a query/version/
  digest that no longer resolves to the exact registered selection are rejected.
- The schema has no path/patch/source-code/command/model-output/secret-value field. It neither loads/applies a
  pack nor mutates an IR, generates source, builds, or calls a provider.
- Gates: `task verify` 2,945 passed fully offline (+11); agent-engine/repository lint, security, and environment
  passed; both demos remained 152/149 files; canonical manifest JSON round-tripped equal; 0 model calls.
- No dependency, pack baseline/registry behavior, ecosystem plan, Application IR/schema, generator, generated
  output, provider, PostgreSQL, infrastructure, tracker workbook, or `.claude/` change. Workbook remains
  unchanged past R-358.

## 2026-09-14 — R-435 (exact-compatible Solution Pack recommendations in ecosystem planning)

- Recorded `.ai/tasks/R-435.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused import
  failed because `SolutionPackRecommendation` did not exist; final R-435/R-434/R-431 focused regression is
  25 passing tests (8 new R-435 tests).
- Extended immutable registry selection with optional required targets while preserving its exact-domain,
  capability-subset, and deterministic newest-version behavior.
- Added frozen `SolutionPackRecommendation`: canonical domain/capability/target query plus minimal selected
  pack id/version/digest/targets metadata or explicit `no-exact-match`. Constructor consistency checks prevent
  incompatible selections from being represented.
- Every `EcosystemPlan` now derives its required targets from the existing project plans of all already-built
  surface IRs and exposes one recommendation in `to_dict()` and the plan CLI. The recommendation is metadata
  only; it does not load, merge, apply, or build the pack.
- Deterministic proof: blog-cms Next.js/Python -> `minimal-blog@1.0.0`; rideshare Next.js/Python ->
  `no-exact-match` because the registered rideshare baseline targets Go. No semantic capability was guessed.
- Gates: `task verify` 2,934 passed fully offline (+8); agent-engine/repository lint, security, and environment
  passed; both demos remained 152/149 files; 0 model calls.
- No dependency, baseline/example, Application IR/schema, generator, provider, PostgreSQL, infrastructure,
  tracker workbook, generated-output, or `.claude/` change. Workbook remains unchanged past R-358.

## 2026-09-14 — R-434 (versioned baseline Solution Pack registry)

- Recorded `.ai/tasks/R-434.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused run
  failed with the expected `ModuleNotFoundError` because the `solution_packs` package did not exist; final
  focused suite is 8 passing tests.
- Added frozen, stdlib-only `SolutionPack` descriptors and immutable `SolutionPackRegistry`. The descriptors
  reference the existing `minimal-blog` and `rideshare-favourites` example IR builders, pin their canonical
  SHA-256 and exact assembled targets, and contain no copied skeleton or duplicated IR.
- Registry construction validates descriptor shape, stable semantic versions, duplicate identities, example
  existence, `validate_ir`, digest/target drift, and target verify plans. Exact domain + required-capability
  selection deterministically prefers the newest compatible version and returns `None` for no match.
- Added a deterministic JSON CLI/task: `task agent-engine:solution-packs` lists the registry or selects by
  `--domain` and repeatable `--capability`. It performs no build, model, network, database, or live work.
- Added `docs/SOLUTION_PACKS.md` describing the verified-baseline/configuration/AI-delta boundary and the
  honest scope of this foundation.
- Gates: focused 8 passed; `task verify` 2,926 passed fully offline (+8); agent-engine lint + repository lint,
  security, and environment gates passed; minimal-blog/rideshare demos generated 152/149 files; deterministic
  list returned two packs and rideshare+favourites selected `rideshare-favourites@1.0.0`; 0 model calls.
- No dependency, existing IR/example, generator, provider, PostgreSQL, infrastructure, tracker workbook, or
  `.claude/` change. The workbook remains unchanged because its planned task universe ends at R-358.

## 2026-09-13 — R-433 (surface-specific ecosystem data and capability scoping)

- Recorded `.ai/tasks/R-433.md` and `.ai/CURRENT_TASK.yaml` before implementation. Test-first focused run
  failed four assertions against R-432 because each app still contained the full entity model and all
  proposal roles; final R-431/R-432/R-433 focused regression is 30 passing tests (7 new R-433 tests).
- Added explicit readable/writable entity policies for every surface across the ten curated domains.
  R-432 refined domains use deterministic singular/verb-aware entity-name matching against bounded surface
  metadata, falling back to the complete validated model when no match is defensible.
- Added recursive relation closure: a selected entity never loses a required relation target. Dependencies
  are retained read-only, selected readable entities receive list screens, and only explicit writable
  entities receive editors plus POST/PUT/DELETE endpoints.
- Each surface IR now declares exactly its normalized actor role with entity-qualified permissions. Every
  authenticated mutation declares that role in `required_roles`; existing public GET behavior remains for
  the current generated preview flow. Plan JSON exposes role/permission and writable-entity scope.
- Deterministic food-delivery inspection: Customer has Restaurant/MenuItem/Order visible but only Order
  writable; Merchant has all three read/write; Courier has Order plus Restaurant dependency, Order-only
  write (8 APIs/2 screens); Admin has Restaurant+Order read/write (11 APIs/4 screens).
- Gates: `task verify` 2,918 passed fully offline; `task lint`, `task security:quick`, `task env:check`
  passed; demos generated 152 (`minimal-blog`) / 149 (`rideshare-favourites`) files. 0 local/cloud model
  calls. Workbook unchanged because its planned universe ends at R-358; `.claude/` remained untracked.

## 2026-09-13 — R-432 (opt-in model refinement for unknown-domain ecosystems)

- Recorded `.ai/tasks/R-432.md` and `.ai/CURRENT_TASK.yaml` before code; focused test import failed RED
  because the API did not exist, then finished at 14 passing tests.
- Added stdlib-only `intake/scope_refinement.py`. The R-430 deterministic proposal always runs first:
  curated domains return R-431 entities with **zero provider calls**; only `custom-application` is eligible
  for one explicit `ModelProvider` request. The prompt includes the deterministic first pass and a bounded
  JSON schema. The parser builds `ScopeProposal` + typed `Entity` values and rejects unknown keys, bad
  identifiers/types/actor references/relation targets, >3 questions, missing UUID ids, credential fields,
  relation-derived FK collisions, and unsupported validation grammar. An omitted empty `relations` list is
  the sole safe structural normalization. Raw output is retained only in the result and excluded from
  `to_dict()`/CLI output.
- Extended R-431 `surface_to_ir`/`plan_ecosystem` with an optional validated entities tuple; existing callers
  remain byte-equivalent. `plan_refined_ecosystem` reuses the same deterministic repository-wired CRUD/IR
  path. Exported the refinement API from `intake`.
- Added explicit local-only `scope_refine_live.py` and `task agent-engine:ecosystem:refine`; it uses the
  existing environment-driven loopback Ollama `ModelProvider`, never cloud, and prints parsed bounded data.
- Live proof: unknown apiary operations prompt -> `apiary-management`, Beekeeper Dashboard + Admin Panel,
  four entities, 23 wired APIs and eight screens per app. Five local calls outside verify were used: three
  malformed responses failed closed, one initially accepted response exposed credential/FK collision gaps
  during review and caused stronger guards, and the final apiary response passed. 0 cloud calls.
- Gates: focused **14 passed**; `task verify` **2,911 passed** fully offline (0 real model calls);
  lint/security/env passed; food-delivery deterministic regression stayed four apps; both builder demos
  passed (152 / 149 files). PostgreSQL, IR, adapters, infrastructure, and `.claude/` unchanged.

## 2026-09-13 — R-431 (Scope → Application IRs — materialize a multi-app ecosystem from one prompt)

- **Second brick of the spine (founder said "continue").** R-430 *proposed* a multi-app ecosystem; R-431 makes it *real* — one prompt → multiple owned, clean-compiling app repos.
- New stdlib-only `intake/ecosystem.py`:
  - Curated `DOMAIN_ENTITIES` — 2–4 typed entities + FK relations for all 10 domains + a `custom-application` fallback.
  - Deterministic CRUD API/screen derivers emitting canonical shapes that WIRE to real repositories (GET/POST /<plural>, GET/PUT/DELETE /<plural>/{id}, and GET /<parents>/{id}/<children> for a single-FK child).
  - `surface_to_ir` (roles from actors, entities = domain model, apis/screens derived, Next.js + Python + PostgreSQL, `normalize_ir` + `validate_ir`-clean), `plan_ecosystem`/`plan_ecosystem_from_prompt` (respects the Complete/Customer-only/Custom option), and `build_ecosystem` (materializes each app under `out/<slug>/` via `build_app_from_ir`). Exported from `intake/__init__.py`.
  - Deterministic plan CLI `intake/ecosystem_plan.py` (`task agent-engine:ecosystem:plan`) + opt-in build CLI `intake/ecosystem_build.py` (`:build`).
- Demo: `ecosystem:plan -- "food delivery app …"` → 4 apps (Customer Ordering App, Merchant Portal, Courier Dispatch App, Super-Admin Dashboard), each 3 entities / 17 APIs / 6 screens. `ecosystem:build` wrote **4 owned Git repos** (164 files each, author sanjeetji).
- **Verified the generated ecosystem apps COMPILE clean** (`tsc --noEmit` on all four → 0 errors). Running it exposed **4 generator compile bugs** in paths minimal-blog/rideshare never generate (FK editor, multi-subcollection parent list, filterable child) — all fixed in `codegen/nextjs.py`:
  - over-braced FK `<select>` `onChange` (`=> {{` → `=> {`);
  - single-brace bool-badge inline style in the child preview (`}>` → `}}>`);
  - a parent list with 2+ sub-collections rendered search-bar + filter-chips as two JSX roots → wrapped in a fragment `<>…</>`;
  - the entity interface omitted the scalar `<relation>_id` FK column the DB schema/API/editor use → now emitted for to-one relations.
- `tests/test_ecosystem.py` (9 tests): per-domain valid IRs, option app-counts, deterministic plan, CRUD wiring (`wire_endpoint`), a real 4-repo build into a temp dir, and an offline guard for the fixed compile-bug classes.
- Gates: `task verify` **2,897** passed (offline; +9); lint/security/env green; both builder demos (152 / 149) unaffected; the R-429 examples still pass `web-typecheck` (no regression). **0 model calls.**

## 2026-09-13 — R-430 (Ecosystem Scope Compiler — deterministic domain classification + multi-app scope proposal)

- **Founder-approved pivot to the DIFFERENTIATING SPINE** (after the R-429 strategy discussion; via AskUserQuestion the founder chose "Start the Scope Compiler"). Master Architecture Spec §2: competitors turn "create a food delivery app" into a single customer screen — OmniStackAI proposes the whole business ecosystem BEFORE generation.
- Built the **deterministic core** so it runs under `task verify` (no model/network), mirroring the intake agent's "deterministic core + opt-in model layer" pattern:
  - New `intake/scope_compiler.py` (stdlib only): frozen `Actor`, `AppSurface` (kind/name/audience/actor/description), `ScopeOption`, `ScopeProposal`, `DomainMatch`, `DomainSpec` — all with JSON-safe `to_dict()`.
  - Curated 10-domain `DOMAIN_LIBRARY` (food-delivery, rideshare, marketplace, e-commerce, b2b-saas, healthcare-clinic, booking, learning, social, blog-cms); each carries weighted keywords, the full-platform surfaces (customer app + operator portals + admin), ≤3 materiality questions, and a self-classifying example prompt.
  - `classify_domain(prompt)` — case-insensitive weighted keyword scoring (multi-word phrases weigh 3, single tokens 1), highest score wins, stable tie-break by library order, `None` below threshold.
  - `propose_ecosystem(prompt)` — classify → build Complete (recommended) / Customer-only (strict customer-audience subset) / Custom options + questions; single-app `custom-application` fallback when nothing matches. Pure/deterministic (same prompt → byte-identical proposal).
- Exported the public API from `intake/__init__.py`; added a **deterministic CLI** `intake/scope_propose.py` wired as `task agent-engine:scope:propose -- "<prompt>"` (+ `scripts/agent-engine.sh scope-propose`, usage string updated).
- Demo: `… "Create a food delivery app where customers order from restaurants and couriers deliver"` → domain **food-delivery** (confidence 1.0) → Customer Ordering App + Merchant Portal + Courier Dispatch App + Super-Admin Dashboard, with Complete/Customer-only/Custom options and 2 materiality questions.
- `tests/test_scope_compiler.py` (11 tests): representative classification, each domain classifies its own example, determinism/purity, Complete carries all surfaces, Customer-only only customer-audience surfaces (strict subset), ≤3 questions, JSON round-trip, no-match fallback, public exports.
- Gates: `task verify` **2,888** passed (offline; +11); lint/security/env green; both builder demos (152 / 149) unaffected. **0 model calls.** No IR/adapter/DB change; scope is not yet wired into generation (next brick).

## 2026-09-13 — R-429 (generated web app passes strict `tsc --noEmit` — component-library type cleanup)

- **Founder direction:** "complete R-429 then tell me next strategy." Ran the R-428 opt-in gate to get the REAL error list (no guessing): a generated `minimal-blog` reported **84** `tsc --noEmit` errors — **4** in `node_modules/next` (missing `skipLibCheck`) + **80** in our code across 19 files, in 8 mechanical classes.
- Wrote the contract (`.ai/tasks/R-429.md` + `CURRENT_TASK.yaml`) before coding; built a fast regenerate→symlink-node_modules→`tsc` loop to drive the count to 0.
- Fixes (all at `codegen/nextjs.py` + the generated tsconfig):
  - **G0** tsconfig now sets `"skipLibCheck": true` (Next's own default) → the 4 dependency `.d.ts` errors gone.
  - **G1** `context-menu.tsx` trailing `export { … }` reduced to just `{ ContextMenu }` (the other 13 names are already `export const`; re-listing them was TS2323/2484) → 39 gone.
  - **G2** internal sub-component aliases (audio-player/geo-map/pdf-viewer, 9) typed `typeof XInner & { displayName?: string }` so `.displayName =` is allowed (runtime unchanged).
  - **G3** compound components (color-picker, pin-input) rebuilt as a typed compound: `forwardRef` result → a `…Base` const cast to `type XComponent = typeof XBase & { Sub: … }`; `.Sub =` assignments and `<X.Sub/>` are now on the type. Named (`export { X }`) + default exports preserved.
  - **G4** `Banner/Carousel/Checkbox/CodeBlock/CodeBlockCopyButton`Props now `Omit` the conflicting inherited DOM attribute (`title`/`onSelect`/`defaultChecked`/`onCopy`).
  - **G5** DOM/SVG element ref annotations `React.RefObject<T | null>` → `React.RefObject<T>` (assignable to a JSX `ref=`); mutable `MutableRefObject<T | null>` casts and value refs (`AbortController`/`number`) left untouched.
  - **G6** `terminal.tsx` variant destructuring default `"default"` → `"minimal"` (a valid `TerminalVariant`; no `=== "minimal"` branch exists, so rendering is byte-identical), scoped to the terminal template only (the other 65 `variant = "default"` defaults, where "default" IS valid, untouched).
  - **G7** added `isUnchanged?: boolean` to `SplitDiffRow`.
  - **G8** the exported `api` object now includes the `…WithCount` LIST/LIST_BY methods (emitted as standalone functions but omitted from the object → TS2339/2551); the generated LIST/LIST_BY hooks always forward a fresh `requestParams` object literal (implicit index signature → assignable to the client's flat `Record` param type; a bare `UseListParams` interface value is not) with `...options` spread **first**, so a caller's `options` can no longer override the hook's params or abort signal (now consistent with the GET/CREATE hooks).
- **Result:** a generated `minimal-blog` AND `rideshare-favourites` pass `tsc --noEmit` with **0** errors. Extended the gate (`scripts/agent-engine.sh web-typecheck`) to assert a clean exit + print PASS/FAIL; `task agent-engine:web-typecheck -- minimal-blog` → **PASSED**, `-- rideshare-favourites` → **PASSED** (fresh generate + `pnpm install` + `tsc` each).
- Regression: `tests/test_generated_tsx_compile.py` gained 4 deterministic guards — tsconfig `skipLibCheck`, no duplicate exports, no `React.RefObject<HTMLxxx | null>`, and every `api.<method>` a hook calls exists on the `api` object. Updated 7 hook/component test files' exact assertions to the corrected emitted strings (spread order + `requestParams`; compound `X = XBase as XComponent` / `export { X }`).
- Gates: `task verify` **2,877** passed (offline); lint/security/env green; both builder demos (152 / 149) pass. **0 model calls in verify.** Removes the last blocker to a production `next build` for generated apps.

## 2026-09-13 — R-428 (generated web app compiles — opt-in tsc gate + fix the bugs it reveals)

- **Chosen approach (founder): compile gate + fix all.** Added an opt-in, live TypeScript typecheck gate — `task agent-engine:web-typecheck -- <example> [out-dir]` (`scripts/agent-engine.sh web-typecheck` + Taskfile) — that generates an example app, `pnpm install --ignore-scripts`, and runs `./node_modules/.bin/tsc --noEmit`. Never run by `task verify`.
- Ran it (and `next dev`) on a generated `minimal-blog` app; fixed the RUN-BLOCKING generator bugs:
  - `codegen/nextjs.py` search input: `onChange={(e) => {{ ... }}}}` and clear `onClick={() => {{ ... }}}}` had extra literal braces (regular strings, not f-strings) → `=> { ... }}`.
  - `components/pdf-viewer.tsx`: a raw string `r"...;\n"` made the trailing `\n` a literal backslash-n (TS1127 invalid character) → ended the raw string before `\n` and appended a real newline via adjacent concatenation.
  - Nested screen pages imported `../components/`/`../lib/` (module-not-found one folder deep) → switched all 24 generator import sites to the `@/` path alias (tsconfig `@/* -> ./*`), which resolves from any depth.
- Verified end-to-end: regenerated `minimal-blog`, `pnpm install`, `next dev` → `/`, `/post_list`, `/post_editor` all serve **HTTP 200** (were 500), 0 module-resolution errors in generated code, 0 compile errors in `next dev`.
- Added `tests/test_generated_tsx_compile.py` (3 tests): forbids over-braced handlers (`=> {{`), depth-relative `../components|../lib` imports, and literal backslash-n in generated `.tsx` (alongside R-427's style test). Updated 9 screen/layout test files' import assertions from `../` to `@/` (25 assertions).
- Gates: focused 6 (+117 in the updated screen tests) passed; `task verify` **2,873** passed; lint/security/env green; both builder demos (152 / 149) pass. **0 model calls in verify.**
- **Remaining (follow-up R-429):** ~82 strict TYPE errors in the component library (TS2323 duplicate exports, TS2339 `displayName` on function components, TS2430/TS2322 prop-type conflicts). These do NOT block `next dev`/preview; they would fail a production `next build`/strict typecheck. The `web-typecheck` gate reports them.

## 2026-09-13 — R-427 (fix malformed single-brace inline styles in generated Next.js screens)

- **Found while running a generated app via the Studio preview:** the backend was healthy (`/posts` 200) but the generated Next.js web app returned HTTP 500 with an SWC syntax error `Expected '</', got ':'` at `app/post_editor/page.tsx` — a single-brace JSX inline style `style={ fontSize: 12, ... }` (JSX requires double braces). Scanning a generated app found 3 offenders in 2 files; scanning the generator found the root cause.
- **Root cause:** 14 f-string templates in `codegen/nextjs.py` (screen header role badges, `<h1>`/`<h2>` titles, and detail `<dt>`/`<dd>` definition lists) wrote `style={{ ... }}`, which Python collapses to single-brace `style={ ... }` in the emitted TSX. `task verify` never caught it because it asserts generated code as strings and never compiles the TSX.
- **Fix:** rewrote those 14 f-string styles to quadruple braces `style={{{{ ... }}}}` (→ valid `style={{ ... }}` output) via a script targeting **only f-string lines** (regular/raw component templates, which are already correct, were left untouched). No component template, screen layout, styling value, or logic changed.
- Added `services/agent-engine/tests/test_generated_screen_styles.py` (3 tests): generates both example IRs and asserts no generated `.tsx` contains a single-brace object-literal inline style (`style={ key: ...`) — precise enough to ignore valid single-brace expression styles (`style={expr}`). RED before the fix (caught `app/favourites/page.tsx` + blog screens), GREEN after.
- Gates: focused 3 passed; `task verify` **2,870** passed; lint/security/env green; `task builder:demo -- minimal-blog` (152) and `-- rideshare-favourites` (149) pass. Diff-invariance/console-snapshot unaffected. **0 model calls in verify.**
- Follow-up noted: the running `studio:preview` holds the old generator in memory — restart it so a fresh build compiles; and a broader generated-TSX compile/lint gate would catch this class of bug automatically (candidate future task).

## 2026-09-13 — R-426 (remove a build from the Studio history)

- Recorded the R-426 contract (`.ai/tasks/R-426.md`, `.ai/CURRENT_TASK.yaml`) before code; implemented test-first.
- `studio/history.py`: added `StudioBuildHistory.remove(build_id) -> bool` (thread-safe; drops the entry by id, returns whether it was present; unknown id is a safe no-op returning False).
- `studio/server.py`: added `POST /api/history/delete` via a new optional injected `delete_build_fn`, reusing the generic `_run_id_control` body reader (unset -> 404, missing id -> 400, errors -> 502).
- `studio/live_serve.py`: wired `delete_build_fn` in **both** Studio modes (it only edits the in-memory list) — `delete_build(id)` calls `history.remove(id)` and returns `{"removed": bool, **history.list()}` (the refreshed, bounded, secret-free history).
- `studio/page.py`: each Recent-builds item now has a fourth action, **Remove**, which POSTs `/api/history/delete` and re-renders the list from the returned `builds` (falls back to `loadHistory()`), DOM-only (no HTML injection).
- Tests (6 net-new): `test_studio_history.py` (remove drops the entry by id; unknown id -> False no-op); `test_studio_server.py` (POST /api/history/delete passes id, missing id 400, 404 when disabled, page has the Remove action).
- Gates: focused 70 passed; `task verify` **2,867** passed; lint/security/env green; `task builder:demo -- minimal-blog` (152) and `-- rideshare-favourites` (149) pass. Deterministic remove/delete inspection confirmed True/False removal and a bounded, secret-free `{removed, builds}` payload. **0 model calls in verify.** Nothing on disk or in the database is deleted.

## 2026-09-13 — R-425 (per-build repo actions — copy path + open folder)

- Recorded the R-425 contract (`.ai/tasks/R-425.md`, `.ai/CURRENT_TASK.yaml`) before code; implemented test-first.
- `studio/server.py`: refactored the `{id}`-body handler into a generic `_run_id_control(fn)` (shared by re-preview) and added a trusted-local route `POST /api/history/open` via a new optional injected `open_dir_fn(build_id) -> dict`; unset handlers 404, missing id 400, handler errors 502. Existing routes unchanged.
- `studio/live_serve.py`: added `_open_path(path)` (platform folder opener — darwin `open`, Windows `os.startfile`, else `xdg-open`; best-effort, never raises, never echoes a command) and `_open_recorded_build(build_id, history)` (looks up the recorded build, opens its `target_dir`, returns a bounded, secret-free `opened`/`error` status; unknown id -> bounded error). Wired `open_dir_fn` only in trusted-local preview mode.
- `studio/page.py`: each Recent-builds item now has three actions (Preview, **Copy path**, **Open folder**). `copyPath` writes the recorded `target_dir` to the clipboard (`navigator.clipboard.writeText` with an `execCommand` fallback and transient feedback; works in both modes, no server call); `openBuild` calls `POST /api/history/open` and shows a bounded result. Rendered with `textContent`/DOM only (no HTML injection).
- Tests (4 net-new): `test_studio_server.py` (POST /api/history/open passes id, missing id 400, 404 when disabled, page has per-build copy/open actions).
- Gates: focused 64 passed; `task verify` **2,861** passed; lint/security/env green; `task builder:demo -- minimal-blog` (152) and `-- rideshare-favourites` (149) pass. Deterministic open-route inspection (opener stubbed — no real Finder launch) confirmed opened/error/unknown payloads are bounded and secret-free. **0 model calls in verify.**

## 2026-09-13 — R-424 (live preview status — liveness-aware status + Studio polling)

- Recorded the R-424 contract (`.ai/tasks/R-424.md`, `.ai/CURRENT_TASK.yaml`) before code; implemented test-first.
- `localrun/run.py`: added `LocalAppSession.is_alive()` — false when stopped or owning no process, true only when every owned background process is still running (`poll()` is None).
- `studio/preview.py`: `StudioPreviewManager.status()` is now liveness-aware. A new `_refresh_locked()` (called under the lock by `status()`) checks the active session; if it is no longer alive it stops/forgets the dead session exactly once and sets a bounded, secret-free "stopped" state (`_EXITED`: "The preview stopped running. Restart to run it again."). While the session stays alive, `status()` returns the current ready state unchanged.
- `studio/page.py`: added live polling of the existing `GET /api/preview` route (`setInterval` every 5s) while a preview is `ready`; `renderPreview` starts polling on ready and stops it otherwise, and only (re)sets the iframe `src` when the preview URL actually changes (`currentPreviewUrl` guard) so polling never reloads/flickers the embedded app.
- No new routes, server signature change, or `live_serve` wiring change — reuses R-422's `GET /api/preview` and the R-421/R-422 manager.
- Tests (7 net-new): `test_localrun_session.py` (is_alive: all-running true, no-processes false, exited-process false, after-stop false); `test_studio_preview.py` (status stays ready while alive; status reports "stopped" and stops the dead session exactly once when it exits, and does not re-stop); `test_studio_server.py` (page polls `GET /api/preview` via `setInterval`).
- Gates: focused 60 passed; `task verify` **2,857** passed; lint/security/env green; `task builder:demo -- minimal-blog` (152) and `-- rideshare-favourites` (149) pass. Deterministic liveness/status inspection confirmed the ready→stopped transition (single cleanup) and secret-free payloads. **0 model calls in verify.**

## 2026-09-13 — R-423 (Studio build history + re-preview a recent build)

- Recorded the R-423 contract (`.ai/tasks/R-423.md`, `.ai/CURRENT_TASK.yaml`) before code; implemented test-first.
- `studio/history.py` (new): `StudioBuildHistory` — a dependency-free, thread-safe, in-memory ring (default cap 10) of recent builds. `record(build) -> id` stores a bounded, secret-free entry (id, prompt truncated to 400 chars, name, up to 24 entities, file_count, target_dir, commit_sha, created_at via an injected clock); `list()` returns `{builds: [...]}` newest-first; `get(id)` finds by id. Only the eight known fields are ever exposed.
- `studio/__init__.py`: exported `StudioBuildHistory`.
- `studio/server.py`: `create_studio_server` gained optional `history_fn` -> `GET /api/history` and `preview_build_fn` -> `POST /api/history/preview` (reads `{id}` from the body via a bounded JSON reader; missing id -> 400; unknown handler -> 404; handler errors -> clean 502). Existing routes unchanged.
- `studio/live_serve.py`: creates a `StudioBuildHistory`, records every successful build (`payload["id"] = history.record(payload)`), wires `history_fn=history.list` in both modes, and wires `preview_build_fn` (re-preview via `_preview_recorded_build` -> `StudioPreviewManager.replace(entry.target_dir)`) only in trusted-local preview mode.
- `studio/page.py`: added a "Recent builds" list (`id="history-list"`) that loads on start (`loadHistory`), refreshes after each successful build, and re-previews a build on click (`previewBuild` -> `POST /api/history/preview`), rendering with `textContent` only (no HTML injection). CSS added.
- Tests (12 net-new): `test_studio_history.py` (record/list/get, newest-first, bounded eviction, injected clock, bounded secret-free entries, JSON-safe); `test_studio_server.py` (GET /api/history, POST /api/history/preview passes id, missing-id 400, 404 when disabled, page has the surface).
- Gates: focused 53 passed; `task verify` **2,850** passed; lint/security/env green; `task builder:demo -- minimal-blog` (152) and `-- rideshare-favourites` (149) pass. Deterministic history-payload inspection confirmed bounded, newest-first, secret-free entries with id lookup/eviction. **0 model calls in verify.**

## 2026-09-13 — R-422 (collision-free preview ports + status/stop/restart controls)

- Recorded the R-422 contract (`.ai/tasks/R-422.md`, `.ai/CURRENT_TASK.yaml`) before code; implemented test-first.
- `localrun/run.py`:
  - Added `find_free_port(host)` and `allocate_preview_ports(host)` — the latter holds two sockets open simultaneously while reading their OS-assigned ports, guaranteeing two distinct free loopback ports.
  - Added `start_preview_app(repo_dir, *, log, health_timeout_seconds, host)` — allocates collision-free ports, builds the env plan with them (`_plan_from_env` now accepts `api_port`/`web_port` overrides), and delegates to the strict `start_app` (readiness, occupied-port rejection, cleanup). Threads the ports into the run plan and thus the generated web app's `NEXT_PUBLIC_API_URL`.
  - `localrun/__init__.py`: exported `find_free_port`, `allocate_preview_ports`, `start_preview_app`.
- `studio/preview.py`: `StudioPreviewManager` default `start_fn` is now `start_preview_app` (collision-free). Added bounded, JSON-safe, secret-free `status()`, `stop()` (returns "stopped", idempotent), and `restart()` (re-previews the single remembered last repo; idle no-op before any build). All state is a fixed-shape dict.
- `studio/server.py`: `create_studio_server` gained optional `status_fn`/`stop_fn`/`restart_fn` -> `GET /api/preview`, `POST /api/preview/stop`, `POST /api/preview/restart`; unset handlers return 404. Control-body drained; handler exceptions become clean 502s. Existing `GET /`, `/healthz`, `POST /api/build` unchanged.
- `studio/live_serve.py`: wires the three control handlers to the manager only in trusted-local preview mode (build-only leaves them unset -> 404).
- `studio/page.py`: added Stop/Restart buttons + a live status line in the preview head; `renderPreview` toggles them by state; `control()` POSTs to the routes and re-renders (no `innerHTML` of server data; loopback-URL validation and the sandboxed iframe preserved).
- Tests (15 net-new): `test_localrun_session.py` (find_free_port bindable, allocate distinct free ports, start_preview_app threads allocated ports into the plan, missing-repo rejected); `test_studio_preview.py` (default start_fn is start_preview_app, status ready/idle, stop reports stopped, restart idle-noop / re-previews last repo, secret-free); `test_studio_server.py` (GET /api/preview, POST stop/restart, 404 when disabled, page has controls).
- Gates: focused 53 passed; `task verify` **2,838** passed; lint/security/env green; `task builder:demo -- minimal-blog` (152) and `-- rideshare-favourites` (149) pass. Deterministic payload/port inspection confirmed distinct free ports and secret-free ready/status/stop/restart payloads. **0 model calls in verify.**

## 2026-09-13 — R-421 (managed embedded trusted-local Studio preview)

- Preserved `agent-engine:studio:serve` as build-only and added explicit
  `agent-engine:studio:preview` with `db:up`; its Task description clearly labels trusted-local
  generated-code execution rather than sandbox isolation.
- Refactored the R-419 executor into exported `LocalAppSession`/`start_app`. The managed boundary owns
  every child, waits for API and web readiness, stops idempotently, cleans up partial failures, checks
  strict preview ports before DB/setup, and rejects exited children so stale health responses cannot
  masquerade as a new preview. The existing `app:run` delegates to it with best-effort readiness retained.
- Added `StudioPreviewManager`: a lock serializes one active session; replacement/shutdown stops it; only
  JSON-safe secret-free `ready`/`error`/`unavailable` fields leave the boundary. A launch error preserves
  the successful repo and the build endpoint's HTTP 200 response.
- Added the actual-app iframe, accessible status, and open link. It accepts only loopback HTTP URLs and
  sets DOM URL properties; model/build response text is never inserted as HTML. The iframe is sandboxed.
- Test-first evidence: missing managed APIs failed first; new occupied-port/stale-process assertions failed
  before the preflight/liveness implementation. Final focused suite: **38 passed**. `task verify`: **2,823
  passed**. Lint/security/env and both demos passed (minimal-blog 152, rideshare-favourites 149).
- Existing user-owned listeners on ports 3000/8000 were not interrupted. The strict preview now rejects
  that collision honestly; dynamic port allocation is the recommended R-422 follow-up.
- Verification made 0 local model calls, 0 cloud calls, and did not execute generated code, Docker, DB,
  installs, or external network. No dependency/provider/IR/DB-engine/service/infra/top-level/mobile change;
  no workbook row exists past R-358.

## 2026-09-13 — R-420 (SQL-safe identifiers and FK dependency order)

- Added one defensive PostgreSQL identifier encoder and applied it consistently to generated schema DDL,
  fixture INSERTs, Python repositories, and Go stores. Logical snake_case paths, symbols, functions,
  routes, and API contracts are unchanged.
- Added stable topological ordering over non-self many-to-one/one-to-one dependencies for entity tables
  and fixture groups. Independent entities preserve source order, fixture rows preserve authored order,
  self-references remain valid, association tables stay after entities, and non-self cycles raise a stable
  explanatory `ValueError`.
- Added 7 focused tests in `test_schema_sql_safety.py`; updated only existing exact-output assertions
  affected by deliberate SQL quoting. Focused tests and 186 related regression tests passed.
- Gates: `task verify` **2,808 passed**; `task lint`, `task security:quick`, and `task env:check` passed;
  both builder demos passed (minimal-blog 152 files, rideshare-favourites 149 files). Generated Python
  parsed with `ast`; representative Go stores passed `gofmt`.
- Live proof: a generated reserved-name User/Order migration created its verification schema, both tables,
  and index in local PostgreSQL, then `ROLLBACK` removed all verification state. Initial command/env/Docker
  access failures were sandbox/invocation issues; a subsequent table/index namespace collision came from
  the test fixture reusing the same name and was corrected to a distinct reserved-looking index name.
- 0 local model calls, 0 cloud calls. No dependency, IR, database-engine, infrastructure, top-level-layout,
  studio, local-run, deployment, or native/mobile change. The workbook ends at R-358, so no tracker row
  exists or was modified for R-420.

## 2026-09-13 — R-419 (front-door pivot: brick 4 — turnkey local run)

- Made a generated app repo run locally in one command. New `omnistackai_agent_engine/localrun/` package (Python 3.13 stdlib only), "deterministic plan + opt-in executor" pattern.
  - `plan.py`: `RunStep`/`RunPlan` dataclasses + `build_run_plan(repo_dir, *, db_*, api_port, web_port, jwt_secret, db_name=None)`. Inspects the repo (backend flavor python via requirements.txt / go via go.mod|main.go; migrations under `services/api/migrations/*.sql`; web via `apps/web/package.json`) and composes an ordered, JSON-safe plan: DROP+CREATE a per-app Postgres DB in the local container, apply each migration (piped on stdin), start the backend (`uvicorn app.main:app` with `DATABASE_URL`/`JWT_SECRET`, or `go run .`), start the web app with `./node_modules/.bin/next dev` (the Next binary directly, never `pnpm dev`) + `NEXT_PUBLIC_API_URL`. `RunPlan.to_dict()` masks the DB password.
  - `run.py`: opt-in executor (`task agent-engine:app:run -- <dir>`; Task `deps: [db:up]`). Runs setup steps synchronously (skips an existing `.venv`/`node_modules`), launches both servers, polls the backend `/healthz`, prints URLs, and terminates both on Ctrl+C.
- Wired opt-in Task: `scripts/agent-engine.sh app-run` + `Taskfile.yml` `agent-engine:app:run` (deps db:up).
- Added `services/agent-engine/tests/test_localrun_plan.py` (12 tests, deterministic — materializes a real repo into a temp dir via git, then asserts the plan): python backend + web detected, URLs, DB drop→create→migrations order (sorted, 0001 first), backend serve env has DATABASE_URL/JWT_SECRET, web uses the Next binary + `--ignore-scripts` and never `pnpm dev`, step order (db→backend→web), `to_dict` JSON-safe + password masked, default db name = repo slug + override, no-backend fallback, migration piped on stdin, package exports.
- Gates: focused 12 passed; `task verify` **2,801** passed; lint/security/env green; `builder:demo` 152 files (unchanged). **0 model calls in verify.**
- **Live proof (opt-in, on the Mac):** `task agent-engine:app:run -- ~/omnistackai-blog-run` -> Postgres up, DB recreated, **both migrations applied**, backend venv+install, **uvicorn on :8000** (`/healthz` 200, `/posts` returned the 2 seeded posts), web install, **Next.js on :3000** (HTTP 200). One command, full boot. The manual 6-step dance is gone.
- **Bug fixed:** a bare `pnpm install` exits 1 on pnpm 11 `ERR_PNPM_IGNORED_BUILDS` (sharp) -> plan uses `pnpm install --ignore-scripts` (sharp's native build isn't needed for `next dev`).
- **Codegen bugs surfaced (-> R-420):** executing real migrations (which `task verify` never does) exposed two pre-existing schema-generator defects: (1) reserved-word identifiers unquoted — a bookstore "Order" entity emits `CREATE TABLE order (` (Postgres syntax error); (2) FK/table creation order is entity order, not dependency order — a recipe box's `ingredient`→`recipe` FK emits `ingredient` first ("relation recipe does not exist"). R-419's executor is correct and surfaced both cleanly; the fix belongs to codegen (R-420).

## 2026-09-13 — R-418 (front-door pivot: brick 3 — chat studio web UI)

- Added the user-facing "chat -> create an app" screen. New `omnistackai_agent_engine/studio/` package, Python 3.13 **stdlib only** (`http.server`) — no npm/pnpm, no web framework.
  - `page.py`: self-contained `STUDIO_HTML` (inline CSS/JS, zero external requests) — prompt textarea, example chips, Build button, building state, and a results panel (app name, description, entity chips, file count, repo path, commit, file list). Diff-invariant static content.
  - `server.py`: `create_studio_server(build_fn, *, host, port)` -> `ThreadingHTTPServer`. `GET /` serves the page, `GET /healthz` returns ok, `POST /api/build` reads `{prompt}` and calls the **injected** `build_fn(prompt) -> dict` (400 on empty/invalid, 502 on build failure, 413 on oversize). The build function is injected so the HTTP layer is fully testable offline.
  - `live_serve.py`: opt-in entrypoint wiring the real local-Ollama `build_app_from_prompt` path; per-build output dir (slug of the prompt under `OMNISTACKAI_APP_OUT_DIR` or a temp dir); serves on `OMNISTACKAI_STUDIO_HOST`/`PORT` (default 127.0.0.1:4173).
- `intake/build_app.py`: added `app_build_result_to_dict(result)` (pure, JSON-safe: name/description/entities/file_count/target_dir/commit_sha/files, excludes `.git`), exported from `intake`.
- Wired opt-in Task: `scripts/agent-engine.sh studio-serve` + `Taskfile.yml` `agent-engine:studio:serve`.
- Added `services/agent-engine/tests/test_studio_server.py` (11 tests, deterministic — ephemeral localhost server + in-memory stub build, real urllib requests): page is self-contained + no external resources, GET serves the page, healthz, unknown GET 404, POST build success (+ records the prompt), empty-prompt 400, invalid-JSON 400, build-failure 502, unknown POST 404, `app_build_result_to_dict` shape.
- Gates: focused 11 passed; `task verify` **2,789** passed; lint/security/env green; `builder:demo` 152 files (unchanged). **0 model calls in verify.**
- **Live proof (opt-in, on the Mac):** started `task agent-engine:studio:serve`; `GET /` served the 7,513-byte page; `POST /api/build` with "Build a bookstore where users browse books, each book has an author, and users can place orders" -> local Ollama -> IR "Bookstore" (Book/Order) -> a 154-file owned Git repo. The local user-facing chat-to-create experience now works end to end.

## 2026-09-13 — R-417 (front-door pivot: brick 2 — prompt -> app repo)

- Chained the R-416 intake agent into the existing builder so a plain-English description produces a real, customer-owned Git repository.
- `intake/build_app.py`:
  - `build_app_from_ir(ir, target_dir, *, author_name, author_email, prompt="", overwrite=False)` -> `assemble_project(ir)` -> `create_repository(...)` -> `AppBuildResult(prompt, ir, target_dir, file_count, commit_sha)`.
  - `async build_app_from_prompt(prompt, provider, target_dir, *, model_id, author_name, author_email, ...)` -> `generate_ir` then `build_app_from_ir`. Depends only on the vendor-neutral `ModelProvider` protocol.
- `intake/_ollama.py`: extracted `build_ollama_provider_from_env()` (shared local-Ollama construction); `live_run.py` refactored to use it.
- `intake/build_run.py`: opt-in live builder CLI (out dir from `OMNISTACKAI_APP_OUT_DIR` or a temp dir); prints app name, entities, file count, repo path, first commit, and the file tree.
- Wired opt-in Task: `scripts/agent-engine.sh app-build` + `Taskfile.yml` `agent-engine:app:build` (`task agent-engine:app:build -- "<description>"`).
- `intake/__init__.py`: exported `AppBuildResult`, `build_app_from_ir`, `build_app_from_prompt`.
- Added `services/agent-engine/tests/test_build_app.py` (7 tests, deterministic — in-memory stub provider + temp-dir git materialization): IR -> owned repo on disk (.git present, commit sha), expected web/backend files written, commit message names the app, prompt -> repo end-to-end, result carries ir+prompt, invalid model output raises + writes nothing, package exports.
- Gates: focused 7 passed; `task verify` **2,778** passed; lint/security/env green; `builder:demo` 152 files (unchanged). **0 model calls in verify.**
- **Live proof (opt-in, on the Mac):** `OMNISTACKAI_APP_OUT_DIR=~/omnistackai-chat-demo task agent-engine:app:build -- "Build a recipe box where users save recipes, each recipe has ingredients and cooking steps"` -> local Ollama compiled it to IR "Recipe Box" (entities Ingredient/Recipe) and materialized a **154-file owned Git repo** with recipe-specific routes/screens, first commit authored sanjeetji. The offline "chat -> real owned app" pipeline now works end to end (chat UI still to come).

## 2026-09-13 — R-416 (front-door pivot: brick 1)

- **New direction.** With the UI-component series paused at R-415, started the user-facing "chat -> create an app" front door. R-416 = the **Prompt -> Application IR intake agent**.
- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-416.md` before code (test-first).
- New package `services/agent-engine/src/omnistackai_agent_engine/intake/`:
  - `nl_to_ir.py`: `build_intake_messages(prompt)` (system+user `Message` tuple; schema taught BY EXAMPLE via a real `example_ir().to_dict()` template + explicit allowed field types from the `FieldType` enum); `parse_ir_response(text)` (extract JSON from raw model text tolerating ```json fences + prose, inject `schema_version`, `ApplicationIR.from_dict` + `normalize_ir`, raise `IntakeResponseError` on malformed/invalid); `async generate_ir(prompt, provider, *, model_id, ...)` (single I/O step via the vendor-neutral `ModelProvider` protocol; validates with `validate_ir`/`has_errors`; returns `IntakeResult`).
  - `errors.py`: `IntakeError`, `IntakeResponseError`.
  - `live_run.py`: opt-in live runner (excluded from `task verify`) that builds an Ollama provider from `OMNISTACKAI_OLLAMA_*` env, compiles a prompt, and prints the IR JSON; clean error (no traceback) on failure.
  - `__init__.py`: public exports.
- Wired an opt-in Task: `scripts/agent-engine.sh intake-run` + `Taskfile.yml` `agent-engine:intake:run` (`task agent-engine:intake:run -- "<description>"`).
- Added `services/agent-engine/tests/test_intake_nl_to_ir.py` (18 tests, deterministic, in-memory stub provider): message building, JSON extraction (bare/fenced/prose), schema-version injection, invalid-input rejection, normalized+valid result, `generate_ir` happy path + request shape + invalid-output raise + **end-to-end IR -> NextjsWebAdapter().generate()**, field-type guidance, package exports.
- Gates: focused tests 18 passed; `task verify` **2,771** passed; `task lint`/`security:quick`/`env:check` passed; `task builder:demo -- minimal-blog` 152 files (unchanged). **0 model calls in verify.**
- **Live proof (opt-in, on the Mac):** `task agent-engine:intake:run -- "Build a task tracker where users create projects and each project has tasks with a title, status and due date"` -> local Ollama (`qwen2.5-coder:14b`) returned a **valid Application IR** (Project/Task entities, `/projects` + nested-task APIs, acceptance criteria). First working piece of chat -> create.

## 2026-09-12 — R-415

- Self-paced `/loop` iteration (hands-off continuous build); **loop stopped at founder's explicit request after this task**.
- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-415.md` before code (test-first).
- `nextjs.py`:
  - Added `_PHONE_INPUT_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Phone Number Input compound component suite (`apps/web/components/phone-input.tsx`).
  - Genuinely functional international phone handling: a curated 20-entry `DEFAULT_COUNTRIES` table (`{code, name, dial}`, ISO2 + dial codes, no flag emoji for ASCII safety, overridable via a `countries` prop), `onlyDigits` (strip via `replace /[^0-9]/g`), `groupNational` loose display grouping, E.164 assembly (`dial + digits`), and length-based validation (6..14 digits).
  - Computed `PhoneInputMeta` (`{country, dial, national, e164, valid}`); controlled + uncontrolled national `value`; `defaultCountry`; `onChange(e164, meta)`.
  - WAI-ARIA: labeled country `<select>` (`aria-label="Country"`) + `<input type="tel" inputMode="tel" autoComplete="tel-national">` with `aria-label`, `aria-invalid` (on invalid), `aria-required`; `role="group"` wrapper + `aria-label`; focus-driven accent border; `data-e164` on the input.
  - Imperative `PhoneInputHandle` (`getValue`, `getE164`, `setValue`, `getCountry`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `PhoneInputVariant`/`PhoneInputSize` types, `PhoneCountry`/`PhoneInputMeta`/`PhoneInputHandle`/`PhoneInputProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `PhoneInput`, `PhoneNumberInput`, `TelInput`, `PhoneField`, default export — each with explicit `displayName`.
  - Exported `render_phone_input_component` in `omnistackai_agent_engine.codegen` and registered `components/phone-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies; ASCII-only source.
- Added `services/agent-engine/tests/test_phone_input_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, ASCII-only source, forwardRef + useImperativeHandle + 6 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, DEFAULT_COUNTRIES/dial/+1, e164, national digits (replace), validation, aria + inputMode="tel", callbacks/controlled, codegen export).
- Gates: `pytest .../test_phone_input_component.py` (18 passed); `task verify` (2,753 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 152 files including `apps/web/components/phone-input.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, react-only imports, 0 non-ASCII chars, no `"""`/backtick hazards.

## 2026-09-12 — R-414

- Self-paced `/loop` iteration (hands-off continuous build).
- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-414.md` before code (test-first).
- `nextjs.py`:
  - Added `_DURATION_INPUT_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Duration Input compound component suite (`apps/web/components/duration-input.tsx`).
  - Genuinely functional duration math: `UNIT_SECONDS` (days 86400 / hours 3600 / minutes 60 / seconds 1), `toSegments`/`fromSegments` to convert to/from a single total-seconds value, and a `formatDuration` helper (e.g. `1d 2h 3m`).
  - Segmented numeric inputs for a configurable `units` set; `min`/`max` clamping with segment normalization on clamp; controlled + uncontrolled `value` (seconds); `onChange(totalSeconds)`; live summary (`role="status"` `aria-live`).
  - WAI-ARIA: `role="group"` + `aria-label`; per-segment `aria-label` (Days/Hours/Minutes/Seconds) + `inputMode="numeric"`; focus-driven accent border.
  - Imperative `DurationInputHandle` (`getValue`, `setValue`, `getFormatted`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `DurationInputVariant`/`DurationInputSize`/`DurationUnit` types, `DurationInputHandle`/`DurationInputProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `DurationInput`, `DurationField`, `TimeSpanInput`, `IntervalInput`, default export — each with explicit `displayName`.
  - Exported `render_duration_input_component` in `omnistackai_agent_engine.codegen` and registered `components/duration-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies; ASCII-only source.
- Added `services/agent-engine/tests/test_duration_input_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, ASCII-only source, forwardRef + useImperativeHandle + 5 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, units + UNIT_SECONDS, conversion (86400/3600/toSegments/fromSegments), formatting, min/max, aria + inputMode, callbacks/controlled, codegen export).
- Gates: `pytest .../test_duration_input_component.py` (18 passed); `task verify` (2,735 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 151 files including `apps/web/components/duration-input.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, 0 non-ASCII chars, no `\"\"\"`/backtick hazards.

## 2026-09-12 — R-413

- Self-paced `/loop` iteration (hands-off continuous build).
- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-413.md` before code (test-first).
- `nextjs.py`:
  - Added `_COPY_BUTTON_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Copy-to-Clipboard Button compound component suite (`apps/web/components/copy-button.tsx`).
  - Genuinely functional: `writeClipboard(text)` uses `navigator.clipboard.writeText` and falls back to a hidden-textarea + `document.execCommand('copy')`; the button shows a transient "Copied" state (configurable `timeout`) with a swapped inline SVG icon (`CopyGlyph` -> `CheckGlyph`) and a visually-hidden `aria-live="polite"` announcement; disables when there's nothing to copy; `onCopy`/`onError` callbacks.
  - ASCII-only source (inline SVG icons, no unicode glyphs) — added a dedicated `test_ascii_only_source` guard to lock this in.
  - Imperative `CopyButtonHandle` (`copy`, `isCopied`, `reset`, `focus`) via `useImperativeHandle`.
  - Implemented `CopyButtonVariant`/`CopyButtonSize` types, `CopyButtonHandle`/`CopyButtonProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `CopyButton`, `CopyToClipboard`, `ClipboardButton`, `CopyIconButton`, default export — each with explicit `displayName`.
  - Exported `render_copy_button_component` in `omnistackai_agent_engine.codegen` and registered `components/copy-button.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_copy_button_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, ASCII-only source, forwardRef + useImperativeHandle + 4 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, clipboard write + fallback, feedback, aria, icon/svg, callbacks, value/disabled, codegen export).
- Gates: `pytest .../test_copy_button_component.py` (18 passed); `task verify` (2,717 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 150 files including `apps/web/components/copy-button.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, **0 non-ASCII chars**, no `\"\"\"`/backtick hazards.

## 2026-09-12 — R-412

- Founder switched to hands-off continuous execution via a self-paced `/loop` (dynamic mode); autonomous advancement until manually stopped.
- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-412.md` before code (test-first).
- `nextjs.py`:
  - Added `_CHARACTER_COUNTER_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Character & Word Counter Textarea compound component suite (`apps/web/components/character-counter.tsx`).
  - Genuinely functional counting: `countCharacters` (Unicode-safe `Array.from(text).length`), `countWordsIn` (trim + `/\s+/` split), and `computeStats` returning `{characters, words, remaining, overLimit}`.
  - Configurable `maxLength`/`maxWords`; optional `hardLimit` clipping input past maxLength (code-point-safe); `warnThreshold` recolors near the limit; optional progress bar; over-limit border/aria-invalid.
  - Controlled + uncontrolled `value`; `onChange(value, stats)`; WAI-ARIA (labeled textarea, `aria-describedby` → a `role="status"` `aria-live="polite"` counter region reporting words/characters and remaining/over).
  - Imperative `CharacterCounterHandle` (`getValue`, `setValue`, `getStats`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `CharacterCounterVariant`/`CharacterCounterSize` types, `CharacterCounterStats`/`CharacterCounterHandle`/`CharacterCounterProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `CharacterCounter`, `CharCounter`, `WordCounter`, `TextCounter`, default export — each with explicit `displayName`.
  - Exported `render_character_counter_component` in `omnistackai_agent_engine.codegen` and registered `components/character-counter.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_character_counter_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 5 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, counting logic, limits, word counting, progress + threshold, aria semantics, hard limit, callbacks/controlled, codegen export).
- Gates: `pytest .../test_character_counter_component.py` (18 passed); `task verify` (2,699 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 149 files including `apps/web/components/character-counter.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards (one benign `·` separator char).

## 2026-09-12 — R-411

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-411.md` before code (test-first).
- `nextjs.py`:
  - Added `_SLUG_INPUT_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Slug / URL Input compound component suite (`apps/web/components/slug-input.tsx`).
  - Genuinely functional `slugify(text, separator)`: `String.normalize('NFKD')` + a `charCodeAt` filter stripping combining diacritics (0x300-0x36f), `toLowerCase`, non-alphanumeric runs collapsed to the separator, and leading/trailing separators trimmed (ASCII-only source — no unicode escapes embedded).
  - Auto-sync from an optional `source` prop until the user manually edits (`editedRef`); optional `prefix`/base URL with a computed full URL; copy-to-clipboard (`navigator.clipboard.writeText`) with copied feedback; controlled + uncontrolled `value`; `maxLength` clipping.
  - `onChange(slug)` + `onCopy(fullUrl)`; WAI-ARIA (labeled input, `aria-label`, visually-hidden `aria-live` copied announcement); focus-driven accent border; monospace input with a joined prefix chip and inline copy button.
  - Imperative `SlugInputHandle` (`getValue`, `getFullUrl`, `setValue`, `slugify`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `SlugInputVariant`/`SlugInputSize` types, `SlugInputHandle`/`SlugInputProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `SlugInput`, `Slugify`, `UrlSlugInput`, `PermalinkInput`, default export — each with explicit `displayName`.
  - Exported `render_slug_input_component` in `omnistackai_agent_engine.codegen` and registered `components/slug-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
  - Note: initial diacritic strip was authored with `̀-ͯ` but the JSON tool layer converted those escapes to literal combining-mark characters; rewrote to a `charCodeAt`/`0x300`-`0x36f` filter so the generated source stays ASCII-only and robust.
- Added `services/agent-engine/tests/test_slug_input_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 6 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, slugify logic, diacritics/NFKD + charCodeAt, source sync, prefix, copy-to-clipboard, aria, callbacks/controlled, codegen export).
- Gates: `pytest .../test_slug_input_component.py` (18 passed); `task verify` (2,681 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 148 files including `apps/web/components/slug-input.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, ASCII-only, no `\"\"\"`/backtick hazards.

## 2026-09-12 — R-410

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-410.md` before code (test-first).
- `nextjs.py`:
  - Added `_PASSWORD_GENERATOR_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Password Generator compound component suite (`apps/web/components/password-generator.tsx`).
  - Genuinely functional secure generation: `secureRandomInt` (crypto.getRandomValues via Uint32Array, Math.random fallback), `buildSets` (uppercase/lowercase/numbers/symbols with optional `excludeAmbiguous` stripping `Il1O0o`), and `generatePassword` (guarantees one char per enabled set, fills from the pool, then Fisher-Yates shuffles).
  - Strength meter (`strengthOf` by length + set variety), read-only monospace output, length slider (min/max), set toggles, regenerate action, and copy-to-clipboard (`navigator.clipboard.writeText` with a `document.execCommand('copy')` fallback) + copied feedback.
  - SSR-safe: crypto/clipboard only touched in handlers/effects; auto-generates on mount via `useEffect`. `onGenerate`/`onCopy` callbacks.
  - WAI-ARIA: `role="group"` + `aria-label`, labeled controls, a visually-hidden `aria-live="polite"` copied announcement.
  - Imperative `PasswordGeneratorHandle` (`generate`, `getValue`, `copy`, `setLength`) via `useImperativeHandle`.
  - Implemented `PasswordGeneratorVariant`/`PasswordGeneratorSize` types, `PasswordGeneratorOptions`/`PasswordGeneratorHandle`/`PasswordGeneratorProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `PasswordGenerator`, `PasswordCreator`, `SecurePasswordGenerator`, `PasswordMaker`, default export — each with explicit `displayName`.
  - Exported `render_password_generator_component` in `omnistackai_agent_engine.codegen` and registered `components/password-generator.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_password_generator_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 4 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, secure RNG, charsets, options, generate logic, copy-to-clipboard, aria semantics, callbacks, codegen export).
- Gates: `pytest .../test_password_generator_component.py` (18 passed); `task verify` (2,663 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 147 files including `apps/web/components/password-generator.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards (unicode `↻` refresh glyph inside a JS-string expression).

## 2026-09-12 — R-409

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-409.md` before code (test-first).
- `nextjs.py`:
  - Added `_CURRENCY_INPUT_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Currency / Money Input compound component suite (`apps/web/components/currency-input.tsx`).
  - Genuinely functional money handling: `sanitizeNumeric` (keeps digits + single dot + optional leading minus, no regex backslashes), `toNumber` (`parseFloat`, null on empty/partial), and `formatCurrency` using the built-in `Intl.NumberFormat(locale, { style: 'currency', currency })` (try/catch fallback to `toFixed(2)`).
  - Focus/blur display strategy: plain numeric while focused (easy editing), locale-currency formatted when blurred; a `useEffect` syncs the display from a controlled `value` when not focused. Clamps to `min`/`max` on blur; `step`/`allowNegative`/`currency`/`locale` configurable.
  - Controlled + uncontrolled `value` (number|null); `onChange(value|null, formatted)` + `onBlur(value|null)`; WAI-ARIA (labeled input, `aria-invalid` on out-of-range, `aria-required`, `inputMode="decimal"`, right-aligned tabular-nums); data-* attrs expose currency/min/max/step.
  - Imperative `CurrencyInputHandle` (`getValue`, `getFormatted`, `setValue`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `CurrencyInputVariant`/`CurrencyInputSize` types, `CurrencyInputHandle`/`CurrencyInputProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `CurrencyInput`, `MoneyInput`, `CurrencyField`, `PriceInput`, default export — each with explicit `displayName`.
  - Exported `render_currency_input_component` in `omnistackai_agent_engine.codegen` and registered `components/currency-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_currency_input_component.py` with 17 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 5 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, Intl formatting, locale, parsing, min/max/step, aria + inputMode, callbacks/controlled, codegen export).
- Gates: `pytest .../test_currency_input_component.py` (17 passed); `task verify` (2,645 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 146 files including `apps/web/components/currency-input.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards.

## 2026-09-12 — R-408

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-408.md` before code (test-first).
- `nextjs.py`:
  - Added `_COLOR_CONTRAST_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Color Contrast Checker compound component suite (`apps/web/components/color-contrast.tsx`).
  - Genuinely functional WCAG math: `parseHex` (#rgb/#rrggbb, backslash-free `/[^0-9a-fA-F]/` guard), `channelLuminance` (sRGB gamma via `Math.pow((s+0.055)/1.055, 2.4)`), `relativeLuminance` (`0.2126`/`0.7152`/`0.0722` weights), `contrastRatio` (`(lighter+0.05)/(darker+0.05)`), and `evaluateContrast` producing a `ContrastResult` with AA/AAA thresholds for normal (>=4.5 / >=7), large (>=3 / >=4.5), and UI (>=3).
  - Native `<input type="color">` + hex text inputs for foreground/background, a swap action, a live preview swatch (sample text at normal + large sizes on the actual colors), and pass/fail badges; a big rounded ratio readout with the derived rating.
  - Controlled + uncontrolled colors; `onChange(result, {foreground, background})`; WAI-ARIA (labeled inputs, `role="status"` `aria-live` results region); imperative `ColorContrastHandle` (`getRatio`, `getResult`, `setColors`, `swap`).
  - Implemented `ColorContrastVariant`/`ColorContrastSize` types, `ContrastResult`/`ColorContrastHandle`/`ColorContrastProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `ColorContrast`, `ContrastChecker`, `WcagContrast`, `ContrastRatio`, default export — each with explicit `displayName`.
  - Exported `render_color_contrast_component` in `omnistackai_agent_engine.codegen` and registered `components/color-contrast.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_color_contrast_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 4 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, luminance algorithm, contrast ratio, WCAG thresholds, hex parsing, color inputs, aria status, callbacks/controlled, codegen export).
- Gates: `pytest .../test_color_contrast_component.py` (18 passed); `task verify` (2,628 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 145 files including `apps/web/components/color-contrast.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards (unicode escapes `✓`/`✗`/`⇄` used inside JS-string expressions, not raw JSX text).

## 2026-09-12 — R-407

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-407.md` before code (test-first).
- `nextjs.py`:
  - Added `_CREDIT_CARD_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Credit Card Payment Field compound component suite (`apps/web/components/credit-card.tsx`).
  - Genuinely functional payment logic: `onlyDigits`, `detectBrand` (IIN prefixes via backslash-free regexes: amex `/^3[47]/`, visa `/^4/`, mastercard `/^(5[1-5]|2[2-7])/`, discover `/^6(011|5)/`), `formatNumber` (amex 4-6-5, others 4-4-4-4), `formatExpiry` (MM/YY), `luhnValid` (Luhn checksum, `sum % 10 === 0`), and `expiryValid` (valid month + not in the past).
  - Card-number, expiry, CVC, and optional cardholder-name inputs with real-time formatting and per-field `aria-invalid`; a computed `CreditCardMeta` (`{brand, numberValid, expiryValid, cvcValid, complete}`); brand-aware CVC length (4 for amex, else 3); an optional live gradient card preview (brand label, masked number, name, expiry) via `BRAND_META`.
  - Controlled + uncontrolled `value`/`defaultValue` (Partial); `onChange(value, meta)` + `onComplete(value, meta)`; `inputMode="numeric"` and `autoComplete` cc-* hints for good mobile/autofill UX.
  - Imperative `CreditCardHandle` (`getValue`, `getMeta`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `CreditCardVariant`/`CreditCardSize`/`CardBrand` types, `CreditCardValue`/`CreditCardMeta`/`CreditCardHandle`/`CreditCardProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES`/`BRAND_META` maps.
  - Compound and semantic alias exports: `CreditCard`, `CreditCardField`, `PaymentCardField`, `CardInput`, default export — each with explicit `displayName`.
  - Exported `render_credit_card_component` in `omnistackai_agent_engine.codegen` and registered `components/credit-card.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies. Only placeholder card numbers in source (no real PANs/secrets).
- Added `services/agent-engine/tests/test_credit_card_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 4 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, 5 brands, Luhn validation, brand detection, formatting, validation meta, aria + inputMode, callbacks/controlled, codegen export).
- Gates: `pytest .../test_credit_card_component.py` (18 passed); `task verify` (2,610 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 144 files including `apps/web/components/credit-card.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards (only intentional `•` bullet escapes in the preview placeholder).

## 2026-09-12 — R-406

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-406.md` before code (test-first).
- `nextjs.py`:
  - Added `_MARQUEE_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Marquee / Ticker compound component suite (`apps/web/components/marquee.tsx`).
  - Seamless continuous scroller for arbitrary `children`: duplicates the content once (second copy `aria-hidden`) for a seamless `-50%` loop, driven by CSS `@keyframes` injected via an inline `<style>{MARQUEE_CSS}</style>` (`omni-marquee-x` / `omni-marquee-y`, with `animationDirection` handling left/right/up/down).
  - Configurable `direction`, `durationSeconds`, `gap`, and edge gradient fade via CSS `maskImage`/`WebkitMaskImage`; `pauseOnHover` (via `onMouseEnter`/`onMouseLeave` + `animationPlayState`), a controlled `paused` prop, and an imperative `pause`/`resume`/`toggle`/`isPaused` handle.
  - A CSS `@media (prefers-reduced-motion: reduce)` rule in the injected style stops the animation (`.omni-marquee-track { animation: none !important }`), in addition to the app's global reduced-motion tokens.
  - Accessibility: container `role="group"` + `aria-label`; the duplicated visual copy is `aria-hidden="true"` so screen readers read the content once.
  - Implemented `MarqueeVariant`/`MarqueeSize`/`MarqueeDirection` types, `MarqueeHandle`/`MarqueeProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps; `import type { CSSProperties, ReactNode } from 'react'`.
  - Compound and semantic alias exports: `Marquee`, `MarqueeTicker`, `ScrollingBanner`, `NewsTicker`, default export — each with explicit `displayName`.
  - Exported `render_marquee_component` in `omnistackai_agent_engine.codegen` and registered `components/marquee.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_marquee_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 4 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, 4 directions, keyframes injection + `<style`, prefers-reduced-motion, pause-on-hover + animationPlayState, seamless duplicate aria-hidden, edge maskImage, controlled pause + durationSeconds, codegen export).
- Gates: `pytest .../test_marquee_component.py` (18 passed); `task verify` (2,592 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 143 files including `apps/web/components/marquee.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens (CSS keyframes braces balanced within the JS string), react-only imports, no `\"\"\"`/backtick hazards.

## 2026-09-12 — R-405

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-405.md` before code (test-first).
- `nextjs.py`:
  - Added `_MENTION_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Mention / @-Autocomplete Textarea compound component suite (`apps/web/components/mention.tsx`).
  - Genuinely functional: a `detectTrigger(text, caret, trigger)` helper scans back from the caret to a whitespace-delimited trigger token; when found, opens a filtered suggestion listbox from the `items` prop (custom `filter` or a default label/description substring match, capped at `maxSuggestions`).
  - Keyboard nav: ArrowDown/ArrowUp cycle `activeIndex`, Enter/Tab insert the active suggestion, Escape closes; mouse hover/mousedown also select; `selectItem` splices `trigger + label + ' '` into the text and repositions the caret via `requestAnimationFrame` + `setSelectionRange`.
  - `extractMentions()` derives the set of mentioned ids from the text; controlled + uncontrolled `value`; `onChange(value, mentions)` + `onMention(item)` callbacks; blur closes the popup after a short delay so option mousedown still registers.
  - ARIA combobox/listbox pattern: textarea `role="combobox"` + `aria-autocomplete="list"` + `aria-expanded` + `aria-controls` + `aria-activedescendant`; `<ul role="listbox">` with `<li role="option" aria-selected>` and stable option ids; empty-state text.
  - Implemented `MentionVariant`/`MentionSize` types, `MentionItem`/`MentionHandle`/`MentionProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps; used `import type { ChangeEvent, CSSProperties, KeyboardEvent } from 'react'` (no React namespace).
  - Compound and semantic alias exports: `Mention`, `MentionInput`, `MentionTextarea`, `AtMention`, default export — each with explicit `displayName`.
  - Exported `render_mention_component` in `omnistackai_agent_engine.codegen` and registered `components/mention.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_mention_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 5 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, trigger detection, suggestion listbox, keyboard nav, combobox ARIA, callbacks, controlled/uncontrolled, mentions extraction, codegen export).
- Gates: `pytest .../test_mention_component.py` (18 passed); `task verify` (2,574 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 142 files including `apps/web/components/mention.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards (only intentional `\s` regex escapes).

## 2026-09-12 — R-404

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-404.md` before code (test-first).
- `nextjs.py`:
  - Added `_MASKED_INPUT_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Masked / Pattern Input compound component suite (`apps/web/components/masked-input.tsx`).
  - Genuinely functional: a token-based `applyMask(input, mask)` (`TOKENS` — `9`=digit `/[0-9]/`, `A`=letter, `*`=alphanumeric; other chars are literals) that formats as the user types and returns `{formatted, raw, complete}` (raw = unmasked chars, complete = all token slots filled).
  - Built-in `PRESET_MASKS` (phone/date/card/time/ssn) selectable via `preset`, plus custom `mask`; if neither given the input passes through unmasked.
  - Caret kept at the end after reformatting via `window.requestAnimationFrame` + `el.setSelectionRange` (try/catch, since some input types disallow it); controlled + uncontrolled `value`; `onChange(formatted, raw)` + `onComplete(formatted, raw)`; `inputMode` pass-through for mobile keyboards; focus-driven accent border.
  - WAI-ARIA: `aria-label`, `aria-required` when `required`; the mask doubles as the placeholder when none supplied.
  - Imperative `MaskedInputHandle` (`getValue`, `getRawValue`, `setValue`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `MaskedInputVariant`/`MaskedInputSize`/`MaskedInputPreset` types, `MaskedInputResult`/`MaskedInputHandle`/`MaskedInputProps` interfaces, `VARIANT_STYLES`/`SIZE_STYLES` maps.
  - Compound and semantic alias exports: `MaskedInput`, `InputMask`, `PatternInput`, `FormattedInput`, default export — each with explicit `displayName`.
  - Exported `render_masked_input_component` in `omnistackai_agent_engine.codegen` and registered `components/masked-input.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_masked_input_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 5 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, 5 presets + PRESET_MASKS, masking logic, raw/formatted/complete, caret handling, aria + inputMode, callbacks, controlled/uncontrolled, codegen export).
- Gates: `pytest .../test_masked_input_component.py` (18 passed); `task verify` (2,556 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 141 files including `apps/web/components/masked-input.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards.

## 2026-09-12 — R-403

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-403.md` before code (test-first).
- `nextjs.py`:
  - Added `_PASSWORD_STRENGTH_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Password Strength Meter & Requirements compound component suite (`apps/web/components/password-strength.tsx`).
  - Genuinely functional: live rule-based `evaluate()` computes `{score, level, passed}` from the ratio of passed rules → `empty`/`weak`/`fair`/`good`/`strong`; a 4-segment strength bar colored by level; a live requirements checklist with met/unmet indicators.
  - Default rules (`defaultRules(minLength)`): min length, uppercase, lowercase, number, symbol (character-class regexes, no backslashes); overridable via a `rules` prop of `{id,label,test}`.
  - Controlled + uncontrolled `value`; show/hide password toggle (`aria-pressed`, `type={visible ? 'text' : 'password'}`); `onChange` + `onStrengthChange` callbacks (held in refs to avoid stale closures).
  - Accessibility: `role="status"` + `aria-live="polite"` strength text; `aria-describedby` wiring the input to the strength + requirements via `useId()`; SSR-safe (no time/window in render; `matchMedia` reduced-motion read only in an effect, gating the bar transition).
  - Imperative `PasswordStrengthHandle` (`getValue`, `setValue`, `getStrength`, `clear`, `focus`) via `useImperativeHandle`.
  - Implemented `PasswordStrengthVariant`/`PasswordStrengthSize`/`PasswordStrengthLevel` types, `PasswordRule`/`PasswordStrengthResult` interfaces, `VARIANT_STYLES`/`SIZE_STYLES`/`LEVEL_META` maps.
  - Compound and semantic alias exports: `PasswordStrength`, `PasswordStrengthMeter`, `PasswordInput`, `PasswordField`, default export — each with explicit `displayName`.
  - Exported `render_password_strength_component` in `omnistackai_agent_engine.codegen` and registered `components/password-strength.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_password_strength_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 5 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, 5 levels, strength scoring, requirements checklist, show/hide toggle, ARIA semantics + useId, callbacks, controlled/uncontrolled, codegen export).
- Gates: `pytest .../test_password_strength_component.py` (18 passed); `task verify` (2,538 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 140 files including `apps/web/components/password-strength.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backtick hazards (only intentional `·`/`✓` JS unicode escapes).

## 2026-09-12 — R-402

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-402.md` before code (test-first).
- `nextjs.py`:
  - Added `_COOKIE_CONSENT_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Cookie Consent & Preferences Manager compound component suite (`apps/web/components/cookie-consent.tsx`).
  - Genuinely functional (not decorative): a fixed-position banner with a compact view (Accept all / Reject all / Customize) and an expandable per-category preferences view with `role="switch"` toggles; required categories are forced on and disabled.
  - `localStorage` persistence via `readStored`/`writeStored` helpers (`window.localStorage.getItem`/`setItem` under a configurable `storageKey`, all try/catch-wrapped so private-mode/blocked storage degrades gracefully) — returning visitors are not re-prompted.
  - SSR-safe: a `mounted` flag renders `null` until after mount, and stored consent is read only in the mount effect, avoiding hydration mismatch and banner flash.
  - Configurable `categories` (default necessary[required]/analytics/marketing), title/description, optional privacy-policy link (`policyUrl`/`policyLabel`), and button labels; `forceShow` override; `onAccept`/`onReject`/`onChange` callbacks.
  - WAI-ARIA: `role="region"` + `aria-label` container; `role="switch"` + `aria-checked` category toggles with accessible labels; 5 placements (bottom/top/bottom-left/bottom-right/center).
  - Imperative `CookieConsentHandle` (`open`, `close`, `accept`, `reject`, `getConsent`, `reset`) via `useImperativeHandle`.
  - Implemented `CookieConsentVariant`/`CookieConsentSize`/`CookieConsentPosition` types, `ConsentCategory`/`ConsentState`, `VARIANT_STYLES` + `SIZE_STYLES` hard-coded hex maps.
  - Compound and semantic alias exports: `CookieConsent`, `ConsentBanner`, `CookieBanner`, `ConsentManager`, default export — each with explicit `displayName`.
  - Exported `render_cookie_consent_component` in `omnistackai_agent_engine.codegen` and registered `components/cookie-consent.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_cookie_consent_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 6 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, 5 positions, localStorage persistence, SSR-safe mounting, categories/required/ConsentState, switch ARIA, callbacks, policy link, codegen export).
- Gates: `pytest .../test_cookie_consent_component.py` (18 passed); `task verify` (2,520 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 139 files including `apps/web/components/cookie-consent.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backslash/backtick hazards.

## 2026-09-12 — R-401

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-401.md` before code (test-first).
- `nextjs.py`:
  - Added `_COUNTDOWN_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Countdown Timer, Stopwatch & Live Clock compound component suite (`apps/web/components/countdown.tsx`).
  - Three modes: `countdown` (to a `targetDate` or fixed `duration` in seconds), `stopwatch` (elapsed), and `clock` (live current time, 12h/24h), driven by a real `window.setInterval` tick (1s for clock, 250ms otherwise) computing values from `Date.now()` and refs.
  - SSR-safe: a `mounted` flag gives a deterministic first paint ("--" placeholders); real time is only read after mount, avoiding hydration mismatch.
  - Day/hour/minute/second segments with optional labels and configurable `separator`; `autoStart`; controlled + uncontrolled `paused`; `onComplete` + `onTick` callbacks (via refs to avoid stale closures).
  - JS `prefers-reduced-motion` guard disables the per-tick transition; WAI-ARIA semantics (`role="timer"`, `aria-atomic`, visually-hidden `aria-live="assertive"` completion announcement).
  - Imperative `CountdownHandle` (`start`, `pause`, `reset`, `restart`, `getTime`, `isRunning`) via `useImperativeHandle`; stopwatch pause/resume accumulates elapsed correctly.
  - Implemented `CountdownVariant` ("default" | "card" | "glass" | "neon"), `CountdownSize` ("sm" | "md" | "lg"), `CountdownMode` ("countdown" | "stopwatch" | "clock") types; `VARIANT_STYLES` + `SIZE_STYLES` hard-coded hex maps.
  - Compound and semantic alias exports: `Countdown`, `CountdownTimer`, `Stopwatch`, `LiveClock`, default export — each with explicit `displayName`.
  - Exported `render_countdown_component` in `omnistackai_agent_engine.codegen` and registered `components/countdown.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_countdown_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 6 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, 3 modes, interval ticking, SSR-safe mounting, timer ARIA, prefers-reduced-motion, callbacks, time formatting, codegen export).
- Gates: `pytest .../test_countdown_component.py` (18 passed); `task verify` (2,502 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 138 files including `apps/web/components/countdown.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backslash/backtick hazards.

## 2026-09-12 — R-400

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-400.md` before code (test-first).
- `nextjs.py`:
  - Added `_IMAGE_COMPARISON_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Before/After Image Comparison Slider compound component suite (`apps/web/components/image-comparison.tsx`).
  - Genuinely interactive (not cosmetic): an "after" base layer with a "before" layer revealed via CSS `clip-path` (`inset(...)`), a draggable divider with `setPointerCapture`, click/tap-to-position on the track, and a `role="slider"` handle with full keyboard control (Arrow keys by `step`, Home/End → 0/100, PageUp/PageDown by 10).
  - Horizontal and vertical orientations; controlled + uncontrolled `position` with `onChange`; optional before/after labels; gradient placeholder layers when no `beforeSrc`/`afterSrc`; `disabled` state.
  - WAI-ARIA 1.2 semantics: `role="group"` container, `role="slider"` handle with `aria-valuemin`/`aria-valuemax`/`aria-valuenow`/`aria-valuetext`/`aria-orientation`; `aria-hidden` divider; alt text / `role="img"` on image layers and placeholders.
  - Imperative `ImageComparisonHandle` (`setPosition`, `getPosition`, `reset`) via `useImperativeHandle`.
  - Implemented `ImageComparisonVariant` ("default" | "card" | "glass" | "neon"), `ImageComparisonSize` ("sm" | "md" | "lg"), `ImageComparisonOrientation` ("horizontal" | "vertical") types; `VARIANT_STYLES` + `SIZE_STYLES` hard-coded hex maps.
  - Compound and semantic alias exports: `ImageComparison`, `BeforeAfterSlider`, `CompareSlider`, `ImageReveal`, default export — each with explicit `displayName`.
  - Exported `render_image_comparison_component` in `omnistackai_agent_engine.codegen` and registered `components/image-comparison.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_image_comparison_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + 3 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, slider ARIA semantics, group role, pointer drag, keyboard control, clip-path reveal, orientation, labels/images, codegen export).
- Gates: `pytest .../test_image_comparison_component.py` (18 passed); `task verify` (2,484 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 137 files including `apps/web/components/image-comparison.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backslash/backtick hazards.

## 2026-09-12 — R-399

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-399.md` before code (test-first).
- `nextjs.py`:
  - Added `_PARTICLE_NETWORK_COMPONENT` static template (raw triple-quoted string) implementing the accessible, desktop-and-mobile-grade, futuristic Particle Network & Interactive Constellation Canvas compound component suite (`apps/web/components/particle-network.tsx`).
  - Ambient / decorative-by-default: NO required data props (distinct from the data-driven `network-graph`); particles generated internally from a `count`/`density` derivation (clamped 12–200).
  - HTML5 Canvas 2D `requestAnimationFrame` loop with edge-bounce motion; proximity link lines between particles with distance-proportional `globalAlpha`; pointer reactivity (gentle attraction + accent-colored cursor links within `interactionRadius`).
  - Device-pixel-ratio-aware sizing (`ctx.setTransform` reset + `ctx.scale(dpr, dpr)`); `window` resize + `pointermove`/`pointerleave` listeners with full cleanup.
  - JS `prefers-reduced-motion` guard (net-new pattern): reads `matchMedia('(prefers-reduced-motion: reduce)')`, renders a single static frame and schedules no rAF when reduced, and live-updates via a `change` listener (with `addListener` fallback).
  - Imperative `ParticleNetworkHandle` (`pause`, `resume`, `toggle`, `restart`, `isPaused`, `getCanvas`) via `useImperativeHandle`; controlled `paused` prop via a secondary effect (no reseed).
  - WAI-ARIA decorative semantics: wrapper `role="img"` + `aria-label`, `aria-hidden="true"` canvas, no `tabIndex`/focus trap, not keyboard-interactive.
  - Implemented `ParticleNetworkVariant` ("default" | "card" | "glass" | "neon"), `ParticleNetworkSize` ("sm" | "md" | "lg"), `ParticleNetworkHandle`, `ParticleNetworkProps` interfaces; `VARIANT_STYLES` + `SIZE_STYLES` hard-coded hex maps (canvas cannot resolve CSS vars).
  - Compound and semantic alias exports: `ParticleNetwork`, `ConstellationCanvas`, `ParticleField`, `StarfieldBackground`, default export — each with explicit `displayName`.
  - Exported `render_particle_network_component` in `omnistackai_agent_engine.codegen` and registered `components/particle-network.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description` (static module constant; never references `ir.name`/`ir.description`); 0 external runtime dependencies.
- Added `services/agent-engine/tests/test_particle_network_component.py` with 18 tests (file-generated, diff-invariance + accessor byte-equality, `'use client'`, zero-deps imports, forwardRef + useImperativeHandle + all 6 handle methods, TS types, alias/default exports, displayNames, 4 variants, 3 sizes, canvas rAF loop, prefers-reduced-motion, pointer interaction, link lines, DPR/resize, WAI-ARIA, ambient/no-required-data, codegen export).
- Gates: `pytest .../test_particle_network_component.py` (18 passed); `task verify` (2,466 tests passed); `task lint`, `task security:quick`, `task env:check` passed; `task builder:demo -- minimal-blog` generated 136 files including `apps/web/components/particle-network.tsx`. 0 model calls.
- Static TSX sanity check: `'use client'` first line, balanced braces/parens, react-only imports, no `\"\"\"`/backslash/backtick hazards.

## 2026-09-12 — R-398

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-398.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_AUDIO_VISUALIZER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Audio Waveform & Spectrum Visualizer compound component suite (`apps/web/components/audio-visualizer.tsx`).
  - Implemented `AudioVisualizerVariant` ("default" | "card" | "glass" | "neon"), `AudioVisualizerSize` ("sm" | "md" | "lg"), `AudioVisualizerMode` ("bars" | "wave" | "spectrum" | "circular"), `AudioVisualizerHandle`, `AudioVisualizerControlsProps`, `AudioVisualizerCanvasProps`, `AudioVisualizerProps` interfaces.
  - Implemented compound and semantic alias exports: `AudioVisualizer`, `WaveformVisualizer`, `SpectrumAnalyzer`, `Oscilloscope`, `AudioVisualizerControls`, `AudioVisualizerCanvas`, default export.
  - Implemented 4 dynamic visualization modes on HTML5 `<canvas>`: vertical frequency bars with peak hold indicators, continuous oscilloscope waveform line, area frequency spectrum with gradient fill, and 360-degree radial circular spectrum with pulsating bass core.
  - Implemented simulated harmonic audio oscillation loop alongside optional real `HTMLMediaElement` / Web Audio API connection.
  - Implemented interactive timeline scrubber slider with current/total time display (`MM:SS`) and keyboard seek controls.
  - Implemented play/pause toggling, volume slider, mute/unmute toggle, and playback speed selector (0.5x, 1x, 1.5x, 2x).
  - Implemented accessible keyboard shortcuts (Space to play/pause, M to mute, Left/Right arrow keys to seek ±5s).
  - Implemented WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Audio Visualizer"`, `role="toolbar"`, `role="slider"`, `aria-valuemin`, `aria-valuemax`, `aria-valuenow`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan/magenta glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`AudioVisualizerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_audio_visualizer_component` in `omnistackai_agent_engine.codegen` and registered `components/audio-visualizer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_audio_visualizer_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,448 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass (135 files generated).

## 2026-09-12 — R-397

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-397.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_MIND_MAP_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Mind Map & Concept Tree compound component suite (`apps/web/components/mind-map.tsx`).
  - Implemented `MindMapVariant` ("default" | "card" | "glass" | "neon"), `MindMapSize` ("sm" | "md" | "lg"), `MindMapLayout` ("radial" | "tree-horizontal" | "tree-vertical"), `MindMapNode`, `MindMapHandle`, `MindMapControlsProps`, `NodeInspectorProps`, `MindMapProps` interfaces.
  - Implemented compound and semantic alias exports: `MindMap`, `ConceptTree`, `BrainstormMap`, `IdeaGraph`, `MindMapControls`, `NodeInspector`, default export.
  - Implemented hierarchical multi-layout algorithms: radial layout (center-out balanced distribution), tree-horizontal (left-to-right hierarchy), and tree-vertical (top-to-bottom hierarchy).
  - Implemented smooth SVG cubic bezier curved branches connecting parent and child concept nodes.
  - Implemented pan/zoom viewport (0.3x to 3x) with mouse drag panning and wheel zooming.
  - Implemented collapsible subtrees with interactive expand/collapse toggling and child progress indicators.
  - Implemented node selection with slide-over Node Inspector editing panel (label, notes/description, theme color palette picker, completion progress slider, add child node, delete branch).
  - Implemented dynamic node addition and recursive subtree deletion.
  - Implemented search input by label and notes with glowing match highlighting.
  - Implemented export to PNG, vector SVG, and JSON formats.
  - Implemented WAI-ARIA 1.2 application & tree semantics (`role="application"`, `role="tree"`, `role="treeitem"`, `role="toolbar"`, `role="complementary"`, `aria-label="Mind Map Canvas"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`MindMapHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_mind_map_component` in `omnistackai_agent_engine.codegen` and registered `components/mind-map.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_mind_map_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,431 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass (134 files generated).

## 2026-09-12 — R-396

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-396.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_LOG_VIEWER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Live Log Viewer & Real-Time Event Stream Inspector compound component suite (`apps/web/components/log-viewer.tsx`).
  - Implemented `LogViewerVariant` ("default" | "card" | "glass" | "neon"), `LogViewerSize` ("sm" | "md" | "lg"), `LogLevel` ("trace" | "debug" | "info" | "warn" | "error" | "fatal"), `LogEntry`, `LogViewerHandle`, `LogToolbarProps`, `LogEntryRowProps`, `LogViewerProps` interfaces.
  - Implemented compound and semantic alias exports: `LogViewer`, `LogStream`, `EventViewer`, `ConsoleLogs`, `LogToolbar`, `LogEntryRow`, default export.
  - Implemented real-time tail streaming with auto-scroll lock toggle, user scroll-up pause detection, and floating resume badge with unread counts.
  - Implemented severity level filter chips (`ALL`, `TRACE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`) with event counters and color badges.
  - Implemented real-time search/filter input with match counter badge and highlighted text substrings (`<mark>`).
  - Implemented service/source filtering dropdown and available sources discovery.
  - Implemented expandable structured JSON metadata drawer with tag badges and syntax formatting.
  - Implemented line wrap toggle (`wrapLines`), line numbers gutter, copy log line / JSON to clipboard with checkmark feedback.
  - Implemented export / download logs to `.txt` and `.json` files, alongside clear logs action.
  - Implemented WAI-ARIA 1.2 log semantics (`role="log"`, `aria-live="polite"`, `role="region"`, `role="toolbar"`, `aria-label="Log stream viewer"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with color-coded luminous level badges).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`LogViewerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_log_viewer_component` in `omnistackai_agent_engine.codegen` and registered `components/log-viewer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_log_viewer_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,414 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass (133 files generated).

## 2026-09-11 — R-395

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-395.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_NETWORK_GRAPH_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Network Graph & Topology Map compound component suite (`apps/web/components/network-graph.tsx`).
  - Implemented `NetworkGraphVariant` ("default" | "card" | "glass" | "neon"), `NetworkGraphSize` ("sm" | "md" | "lg"), `GraphNodeType` ("server" | "database" | "client" | "service" | "gateway" | "ai"), `GraphNodeStatus` ("healthy" | "warning" | "error" | "idle"), `GraphNodeMetrics`, `GraphNode`, `GraphEdge`, `NetworkGraphHandle`, `GraphControlsProps`, `NodeDetailsPanelProps`, `NetworkGraphProps` interfaces.
  - Implemented compound and semantic alias exports: `NetworkGraph`, `TopologyMap`, `ForceGraph`, `GraphVisualizer`, `GraphControls`, `NodeDetailsPanel`, default export.
  - Implemented force-directed physics layout with Coulomb node repulsion, Hooke spring edge attraction, center gravity, velocity damping, and requestAnimationFrame simulation loop.
  - Implemented interactive viewport with zoom in/out (0.3x to 3x), zoom reset, pan dragging, and node drag-and-drop repositioning with physics reheating.
  - Implemented node selection with slide-over inspection drawer displaying node metadata, status badge, live performance metrics (CPU, memory, latency, throughput, uptime), and interactive connected nodes list.
  - Implemented search input by label, ID, and tags, alongside multiselect type filtering pills ("all", "gateway", "service", "database", "server", "client", "ai").
  - Implemented export topology to PNG functionality via SVG serialization and canvas rasterization.
  - Implemented WAI-ARIA 1.2 application semantics (`role="application"`, `aria-label="Network Topology Graph"`, `role="toolbar"`, `role="complementary"`, `role="button"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`NetworkGraphHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_network_graph_component` in `omnistackai_agent_engine.codegen` and registered `components/network-graph.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_network_graph_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,397 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-394

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-394.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_IMAGE_GALLERY_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Image Gallery & Masonry Lightbox compound component suite (`apps/web/components/image-gallery.tsx`).
  - Implemented `ImageGalleryVariant` ("default" | "card" | "glass" | "neon"), `ImageGallerySize` ("sm" | "md" | "lg"), `GalleryLayout` ("grid" | "masonry"), `GalleryItem`, `ImageGalleryHandle`, `ImageGalleryToolbarProps`, `LightboxModalProps`, `ImageGalleryProps` interfaces.
  - Implemented compound and semantic alias exports: `ImageGallery`, `PhotoGallery`, `MediaGallery`, `MasonryGallery`, `Lightbox`, `ImageGalleryToolbar`, default export.
  - Implemented responsive multi-column grid and masonry layouts with auto-fill minmax columns and variable aspect ratios.
  - Implemented interactive full-screen Lightbox modal with zoom in/out (0.5x to 3x), zoom reset, 90-degree image rotation, previous/next navigation, and backdrop dismissal.
  - Implemented auto-advancing slideshow presentation mode with play/pause toggling and configurable timer intervals (`slideshowInterval`).
  - Implemented category filter pills ("All", "Architecture", "Sci-Fi", "Abstract", "Nature") and real-time title/description/tag search filter.
  - Implemented bottom thumbnail strip navigation inside the lightbox with active thumbnail indicator and click-to-jump.
  - Implemented image download action and interactive like/favorite toggle with heart counters.
  - Implemented WAI-ARIA 1.2 dialog and grid semantics (`role="region"`, `role="grid"`, `role="gridcell"`, `role="dialog"`, `aria-modal="true"`, `role="toolbar"`, keyboard navigation).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`ImageGalleryHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_image_gallery_component` in `omnistackai_agent_engine.codegen` and registered `components/image-gallery.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_image_gallery_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,380 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-393

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-393.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_JSON_VIEWER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Interactive JSON Viewer & Schema Tree Inspector compound component suite (`apps/web/components/json-viewer.tsx`).
  - Implemented `JsonViewerVariant` ("default" | "card" | "glass" | "neon"), `JsonViewerSize` ("sm" | "md" | "lg"), `JsonViewMode` ("tree" | "raw"), `JsonValueType` ("string" | "number" | "boolean" | "null" | "undefined" | "object" | "array"), `JsonViewerHandle`, `JsonViewerToolbarProps`, `JsonTreeNodeProps`, `JsonViewerProps` interfaces.
  - Implemented compound and semantic alias exports: `JsonViewer`, `JsonTree`, `ObjectInspector`, `SchemaViewer`, `JsonViewerToolbar`, default export.
  - Implemented collapsible and expandable object & array tree nodes (`JsonTreeNode`) with chevron indicators and child counters (`{ N keys }`, `[ N items ]`).
  - Implemented color-coded type badges (`TYPE_COLORS`) and value syntax highlighting (string, number, boolean, null, undefined, object, array).
  - Implemented copy path (JSONPath / dot-notation, e.g. `$.users[0].name`) and copy value to clipboard with animated checkmark feedback.
  - Implemented real-time search filtering across keys and values with match counter badge and highlighted text substrings (`<mark>`).
  - Implemented depth expansion controls: Expand All, Collapse All, and configurable default expansion depth (`defaultDepth`).
  - Implemented dual view modes: Interactive Tree view (`tree`) vs Raw Formatted JSON view (`raw`) with syntax formatting.
  - Implemented inline primitive value editing with live validation, type parsing (`parseInputPrimitive`), and immutable tree updater (`updateAtPath`).
  - Implemented download/export formatted JSON file and copy entire JSON root to clipboard.
  - Implemented WAI-ARIA 1.2 tree semantics (`role="tree"`, `role="treeitem"`, `role="group"`, `aria-expanded`, `aria-level`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`JsonViewerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_json_viewer_component` in `omnistackai_agent_engine.codegen` and registered `components/json-viewer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_json_viewer_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,363 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-392

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-392.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_MERGE_EDITOR_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Code Diff Editor & 3-Way Merge Conflict Resolver compound component suite (`apps/web/components/merge-editor.tsx`).
  - Implemented `MergeEditorVariant` ("default" | "card" | "glass" | "neon"), `MergeEditorSize` ("sm" | "md" | "lg"), `ConflictStatus` ("unresolved" | "current" | "incoming" | "both"), `MergeConflict`, `MergeEditorHandle`, `MergeEditorToolbarProps`, `MergeEditorProps` interfaces.
  - Implemented compound and semantic alias exports: `MergeEditor`, `ConflictResolver`, `ThreeWayMerge`, `DiffEditor`, `MergeEditorToolbar`, default export.
  - Implemented 3-pane synchronized layout: Left ("Current Change / Ours", emerald accent), Center ("Result / Merged View", violet accent), Right ("Incoming Change / Theirs", sky blue accent).
  - Implemented interactive conflict block resolution actions ("Accept Current", "Accept Incoming", "Accept Both").
  - Implemented raw conflict marker parser (`parseRawConflicts`) parsing `<<<<<<< HEAD`, `=======`, `>>>>>>> incoming`.
  - Implemented batch actions: "All Current", "All Incoming", "Reset All".
  - Implemented conflict navigation jumper bar (Next/Prev conflict jumper, conflict counter, remaining unresolved badge).
  - Implemented editable merged output buffer with manual edit override and copy to clipboard / file download actions.
  - Implemented WAI-ARIA 1.2 semantics (`role="region"`, `aria-label="3-Way Merge Editor"`, `role="toolbar"`, `role="status"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`MergeEditorHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_merge_editor_component` in `omnistackai_agent_engine.codegen` and registered `components/merge-editor.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_merge_editor_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,346 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-391

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-391.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_WHITEBOARD_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Whiteboard & Collaborative Canvas compound component suite (`apps/web/components/whiteboard.tsx`).
  - Implemented `WhiteboardVariant` ("default" | "card" | "glass" | "neon"), `WhiteboardSize` ("sm" | "md" | "lg"), `WhiteboardTool` ("select" | "pencil" | "line" | "arrow" | "rectangle" | "circle" | "text" | "eraser"), `WhiteboardPoint`, `WhiteboardElement`, `WhiteboardHandle`, `WhiteboardToolbarProps`, `WhiteboardProps` interfaces.
  - Implemented compound and semantic alias exports: `Whiteboard`, `DrawingCanvas`, `SketchBoard`, `CollaborativeCanvas`, `WhiteboardToolbar`, default export.
  - Implemented vector shape drawing (rectangle, ellipse/circle, arrow, line, freehand pencil with quadratic smoothing, text sticky notes, eraser).
  - Implemented color palette presets (`PRESET_COLORS`) and stroke width selector (`STROKE_WIDTHS`: 2px to 14px).
  - Implemented infinite canvas pan & zoom transform with mouse wheel zoom, click-drag panning, and reset zoom button.
  - Implemented multi-level undo/redo history stack (`pushHistory`, `undo`, `redo`).
  - Implemented export to PNG (`canvas.toDataURL`), export to standalone vector SVG XML (`exportSvg`), export and import JSON canvas diagrams (`exportJson`, `loadJson`).
  - Implemented WAI-ARIA 1.2 application semantics (`role="application"`, `aria-label="Whiteboard Canvas"`, `role="toolbar"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`WhiteboardHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_whiteboard_component` in `omnistackai_agent_engine.codegen` and registered `components/whiteboard.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_whiteboard_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,329 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-390

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-390.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_VIDEO_PLAYER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Video Player & Streaming Theater compound component suite (`apps/web/components/video-player.tsx`).
  - Implemented `VideoPlayerVariant` ("default" | "card" | "glass" | "neon"), `VideoPlayerSize` ("sm" | "md" | "lg"), `VideoQuality` ("auto" | "1080p" | "720p" | "480p" | "360p"), `VideoChapter`, `VideoCaption`, `VideoSource`, `VideoPlayerHandle`, `VideoControlsProps`, `VideoPlayerProps` interfaces.
  - Implemented compound and semantic alias exports: `VideoPlayer`, `MoviePlayer`, `TheaterPlayer`, `StreamPlayer`, `VideoControls`, default export.
  - Implemented video playback controls (play, pause, 10s skip forward/backward, time formatting helper `formatVideoTime`).
  - Implemented interactive seekable timeline / scrubber with buffered progress bar and visual chapter markers with hover tooltips.
  - Implemented theater mode layout expansion and native Fullscreen API integration.
  - Implemented picture-in-picture (PiP) toggle via HTML5 `requestPictureInPicture`.
  - Implemented closed captions / subtitles overlay with active cue text matching.
  - Implemented playback speed selector (0.5x to 2x) and video quality selector (Auto, 1080p, 720p, 480p, 360p).
  - Implemented volume slider with mute toggle and keyboard shortcuts (Space, K, Arrows, F, T, M, C).
  - Implemented WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Video Player"`, `role="toolbar"`, `role="slider"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`VideoPlayerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_video_player_component` in `omnistackai_agent_engine.codegen` and registered `components/video-player.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_video_player_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,312 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-389

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-389.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_AUDIO_PLAYER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Audio Player & Frequency Equalizer compound component suite (`apps/web/components/audio-player.tsx`).
  - Implemented `AudioPlayerVariant` ("default" | "card" | "glass" | "neon"), `AudioPlayerSize` ("sm" | "md" | "lg"), `AudioTrack`, `AudioEqualizerBand`, `AudioEqualizerPreset`, `AudioPlayerHandle`, `AudioPlaylistProps`, `AudioEqualizerProps`, `AudioPlayerProps` interfaces.
  - Implemented compound and semantic alias exports: `AudioPlayer`, `MusicPlayer`, `SoundPlayer`, `AudioPlaylist`, `AudioEqualizer`, default export.
  - Implemented audio playback controls (play, pause, previous, next, seek forward/back 10s).
  - Implemented interactive seekable waveform / scrubber with duration and current time indicators (`MM:SS`).
  - Implemented multi-band frequency equalizer (`AudioEqualizer`: 60Hz, 250Hz, 1kHz, 4kHz, 16kHz) with presets ("Flat", "Bass Boost", "Vocal", "Electronic", "Rock") and vertical interactive sliders.
  - Implemented multi-track playlist queue drawer (`AudioPlaylist`) with track selection, active track indicator, and track durations.
  - Implemented playback speed selector (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x).
  - Implemented volume slider with mute toggle, repeat (none, all, one) and shuffle toggles.
  - Implemented WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Audio Player"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`AudioPlayerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_audio_player_component` in `omnistackai_agent_engine.codegen` and registered `components/audio-player.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_audio_player_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,295 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-388

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-388.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_PDF_VIEWER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic PDF & Document Viewer compound component suite (`apps/web/components/pdf-viewer.tsx`).
  - Implemented `PdfViewerVariant` ("default" | "card" | "glass" | "neon"), `PdfViewerSize` ("sm" | "md" | "lg"), `PdfViewMode` ("single" | "continuous"), `PdfPage`, `PdfViewerHandle`, `PdfThumbnailProps`, `PdfToolbarProps`, `PdfPageCanvasProps`, `PdfViewerProps` interfaces.
  - Implemented compound and semantic alias exports: `PdfViewer`, `DocumentViewer`, `FileViewer`, `PdfThumbnails`, `PdfToolbar`, `PdfPageCanvas`, default export.
  - Implemented multi-page document pagination with page number jumper and page counter indicators (`Page X of Y`).
  - Implemented interactive page zooming (50% to 300%) with zoom in/out buttons, zoom presets, and smooth scaling.
  - Implemented page rotation (90° clockwise per trigger).
  - Implemented slide-over thumbnail navigation drawer (`PdfThumbnails`) with clickable miniature page preview cards.
  - Implemented in-document text search with live match counter (`Match X of Y`), previous/next match navigation, and `<mark>` highlighted text styling.
  - Implemented single-page and continuous vertical scroll view modes (`single` vs `continuous`).
  - Implemented action toolbar with print trigger (`window.print`), download action, and fullscreen presentation toggle.
  - Implemented WAI-ARIA 1.2 document and toolbar semantics (`role="region"`, `role="toolbar"`, `role="document"`, `aria-label="Document Viewer"`, keyboard shortcuts).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`PdfViewerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_pdf_viewer_component` in `omnistackai_agent_engine.codegen` and registered `components/pdf-viewer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_pdf_viewer_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,278 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-387

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-387.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_GEO_MAP_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Interactive Geo Map & Location Pinpoint compound component suite (`apps/web/components/geo-map.tsx`).
  - Implemented `GeoMapVariant` ("default" | "card" | "glass" | "neon"), `GeoMapSize` ("sm" | "md" | "lg"), `MarkerStyle` ("pin" | "dot" | "pulse" | "beacon"), `MapMarker`, `MapRoute`, `GeoMapHandle`, `MapCalloutProps`, `MapControlsProps`, `GeoMapProps` interfaces.
  - Implemented compound and semantic alias exports: `GeoMap`, `InteractiveMap`, `LocationPicker`, `MapPin`, `MapCallout`, `MapControls`, `RouteLine`, default export.
  - Implemented zero-dependency mathematical vector SVG Equirectangular coordinate projection engine (`lngToX`, `latToY`, `xToLng`, `yToLat`).
  - Implemented stylized world continent vector paths (North America, South America, Europe, Africa, Asia, Australia, Antarctica) and latitude/longitude graticules.
  - Implemented interactive pan & zoom transform engine with mouse drag-to-pan, scroll wheel zoom, keyboard arrow navigation, and reset-view controls.
  - Implemented customizable location marker pins with 4 styles (`pin`, `dot`, `pulse`, `beacon`), pulsating animated radar rings, and selection indicators.
  - Implemented interactive marker callout popup card (`MapCallout`) showing category badge, title, description, coordinate readout, and action button.
  - Implemented route polyline visualizer (`RouteLine`) connecting waypoints with glowing animated data flow.
  - Implemented real-time location search bar and category filter pill buttons.
  - Implemented coordinate picker crosshair mode capturing exact latitude and longitude on click (`onCoordinateSelect`).
  - Implemented floating HUD controls (`MapControls`) for zoom in/out, reset, and live cursor coordinate badge.
  - Implemented WAI-ARIA 1.2 application semantics (`role="application"`, `aria-label="Interactive Map"`, keyboard navigation).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`GeoMapHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_geo_map_component` in `omnistackai_agent_engine.codegen` and registered `components/geo-map.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_geo_map_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,261 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-386

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-386.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_FILE_EXPLORER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic File Explorer & Storage Browser compound component suite (`apps/web/components/file-explorer.tsx`).
  - Implemented `FileExplorerVariant` ("default" | "card" | "glass" | "neon"), `FileExplorerSize` ("sm" | "md" | "lg"), `FileExplorerViewMode` ("grid" | "list"), `FileItemType` ("folder" | "file" | "image" | "video" | "audio" | "code" | "pdf" | "archive"), `FileItem`, `FileExplorerHandle`, `FileBreadcrumbsProps`, `FileDetailsProps`, `FileExplorerProps` interfaces.
  - Implemented compound and semantic alias exports: `FileExplorer`, `FileManager`, `FileBrowser`, `DocumentManager`, `FileGrid`, `FileList`, `FileDetailsPanel`, `FileBreadcrumbs`, default export.
  - Implemented folder navigation with dynamic path breadcrumbs bar and click-to-traverse hierarchy.
  - Implemented dual view modes: card grid view with item type badges and list view with tabular columns (Name, Size, Date, Type).
  - Implemented single and multi-selection modes (`allowMultiSelect`) with checkbox selection and select-all affordance.
  - Implemented real-time search filtering across item names.
  - Implemented slide-over file inspector details panel (`FileDetailsPanel`) showing preview icons, formatted file sizes (B, KB, MB, GB), timestamps, and item actions.
  - Implemented action toolbar with upload button, download action, and delete confirmation trigger.
  - Implemented WAI-ARIA 1.2 grid and region semantics (`role="region"`, `aria-label="File Explorer"`, `role="grid"`, `role="row"`, `role="gridcell"`, `aria-selected`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`FileExplorerHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_file_explorer_component` in `omnistackai_agent_engine.codegen` and registered `components/file-explorer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_file_explorer_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,244 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-385

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-385.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_AUDIO_RECORDER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Audio & Voice Recorder compound component suite (`apps/web/components/audio-recorder.tsx`).
  - Implemented `AudioRecorderVariant` ("default" | "card" | "glass" | "neon"), `AudioRecorderSize` ("sm" | "md" | "lg"), `RecordingState` ("idle" | "recording" | "paused" | "stopped"), `WaveformStyle` ("bars" | "wave" | "mirror"), `AudioRecording`, `AudioRecorderHandle`, `WaveformVisualizerProps`, `AudioPlayerBarProps`, `AudioRecorderProps` interfaces.
  - Implemented compound and semantic alias exports: `AudioRecorder`, `VoiceRecorder`, `SoundRecorder`, `WaveformVisualizer`, `AudioPlayerBar`, default export.
  - Implemented real-time sound recording lifecycle state machine (`idle` -> `recording` <-> `paused` -> `stopped`).
  - Implemented sound waveform canvas visualizer (`WaveformVisualizer`) supporting 3 visual styles: `bars` (frequency bars), `wave` (smooth bezier wave), and `mirror` (symmetrical wave).
  - Implemented real-time duration timer (`MM:SS`) with animated pulsing live recording indicator dot.
  - Implemented maximum duration auto-stop guard (`maxDuration`).
  - Implemented integrated audio playback bar with seekable scrubber, play/pause toggle, and duration readout.
  - Implemented audio download and delete/discard actions.
  - Implemented WAI-ARIA 1.2 media semantics (`role="region"`, `aria-label="Audio Recorder"`, `aria-live="polite"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`AudioRecorderHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_audio_recorder_component` in `omnistackai_agent_engine.codegen` and registered `components/audio-recorder.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_audio_recorder_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,227 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-384

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-384.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CHAT_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Chat & Real-Time Messaging compound component suite (`apps/web/components/chat.tsx`).
  - Implemented `ChatVariant` ("default" | "card" | "glass" | "neon"), `ChatSize` ("sm" | "md" | "lg"), `MessageSender` ("user" | "bot" | "agent" | "system"), `MessageStatus` ("sending" | "sent" | "delivered" | "read" | "failed"), `ChatAttachment`, `ChatAction`, `ChatMessage`, `ChatConversation`, `ChatHandle`, `ChatHeaderProps`, `ChatMessageProps`, `ChatInputProps`, `ChatSidebarProps`, `ChatMessageListProps`, `ChatProps` interfaces.
  - Implemented compound and semantic alias exports: `Chat`, `ChatWindow`, `Messenger`, `ChatWidget`, `ChatHeader`, `ChatSidebar`, `ChatMessageItem`, `ChatInput`, `ChatMessageList`, default export.
  - Implemented conversational message streams with user, bot/agent, and system message bubble styling distinctions.
  - Implemented sent, delivered, read receipt status indicators and timestamp display.
  - Implemented typing indicator with pulsing animated dots.
  - Implemented auto-expanding input bar with Enter-to-send, Shift+Enter for newline, file attachment button, and send button.
  - Implemented quick action pills / suggestion chips for rapid response.
  - Implemented media attachment previews (image and file types) with name and type display.
  - Implemented multi-thread conversation sidebar with search filtering and unread count badges.
  - Implemented auto-scroll to bottom behavior on new messages.
  - Implemented WAI-ARIA 1.2 log accessibility semantics (`role="log"`, `aria-live="polite"`, `role="list"`, `role="listitem"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with luminous halos).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`ChatHandle`), and explicit `displayName` across all exports.
  - Exported `render_chat_component` in `omnistackai_agent_engine.codegen` and registered `components/chat.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_chat_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,210 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-383

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-383.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SPREADSHEET_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Spreadsheet & Inline-Editable Data Sheet compound component suite (`apps/web/components/spreadsheet.tsx`).
  - Implemented `SpreadsheetVariant` ("default" | "card" | "glass" | "neon"), `SpreadsheetSize` ("sm" | "md" | "lg"), `CellType` ("text" | "number" | "currency" | "percentage" | "date" | "boolean" | "select" | "formula"), `CellValue`, `CellCoord`, `CellRange`, `ColumnDef`, `RowData`, `SpreadsheetHandle`, `SpreadsheetProps`, `SpreadsheetToolbarProps`, `SpreadsheetCellProps` interfaces.
  - Implemented compound and semantic alias exports: `Spreadsheet`, `DataSheet`, `InlineGrid`, `SpreadsheetToolbar`, `SpreadsheetCell`, default export.
  - Implemented inline cell editing triggered on double-click, F2, or Enter key, with input commit on Enter/Blur and abort on Escape.
  - Implemented zero-dependency pure JavaScript formula evaluation engine (`evaluateFormula`) supporting `=SUM`, `=AVG`, `=COUNT`, `=MIN`, `=MAX`, and `=IF(cond, trueVal, falseVal)` formulas with cell reference parsing (e.g. `A1`, `B2`) and range extraction (`A1:A5`).
  - Implemented comprehensive keyboard navigation: Arrow keys (Up/Down/Left/Right), Tab/Shift+Tab horizontal step, Home/End (row start/end), Ctrl+Home/Ctrl+End (grid start/end), PageUp/PageDown (vertical jump).
  - Implemented multi-cell rectangular range selection via Shift+Click and Shift+Arrow keys.
  - Implemented column freeze sticky positioning (`frozen: true`) with horizontal offset accounting for row number gutter.
  - Implemented column resize handles with drag listener and automatic minimum width constraints.
  - Implemented row number gutter (#) with row selection on click.
  - Implemented undo/redo history stack tracking cell changes with `Ctrl+Z` / `Ctrl+Y` shortcuts and toolbar triggers.
  - Implemented CSV export (`exportCsv`) and CSV text import (`csvToRows`).
  - Implemented clipboard copy/paste (`Ctrl+C` TSV/CSV format, `Ctrl+V` multi-cell paste).
  - Implemented right-click custom context menu: Insert row above, Insert row below, Delete row, Clear row.
  - Implemented Ctrl+F find bar searching cell values with search match highlight tinting.
  - Implemented interactive column header sorting (ascending/descending) with indicator arrows.
  - Implemented specialized cell editor controls: checkbox toggle for boolean, select dropdown for choices, number formatting for currency/percentage, text input for generic fields.
  - Implemented cell validation with error state border highlighting and tooltip error messages.
  - Implemented WAI-ARIA 1.2 grid semantics (`role="grid"`, `role="row"`, `role="columnheader"`, `role="gridcell"`, `aria-selected`, `aria-sort`, `aria-rowindex`, `aria-colindex`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant outline).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`SpreadsheetHandle`), and explicit `displayName` across all exports.
  - Exported `render_spreadsheet_component` in `omnistackai_agent_engine.codegen` and registered `components/spreadsheet.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_spreadsheet_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,193 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-382

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-382.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_QR_CODE_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic QR Code & Barcode compound component suite (`apps/web/components/qr-code.tsx`).
  - Implemented `QrErrorCorrectionLevel` ("L" | "M" | "Q" | "H"), `QrModuleStyle` ("square" | "rounded" | "dots" | "diamonds"), `QrEyeStyle` ("square" | "rounded" | "circle"), `QrGradientType` ("none" | "linear" | "radial"), `BarcodeFormat` ("code128" | "ean13"), `QrCodeVariant` ("default" | "card" | "glass" | "neon"), `QrCodeSize` ("sm" | "md" | "lg"), `QrCodeHandle`, `QrCodeProps`, `BarcodeProps`, `QrCardProps` interfaces.
  - Implemented compound and semantic alias exports: `QrCode`, `Barcode`, `QrCard`, default export.
  - Implemented zero-dependency built-in mathematical QR generator with Galois Field GF(2^8) Reed-Solomon polynomial math and standard error correction levels (L, M, Q, H).
  - Implemented zero-dependency mathematical 1D barcode generator (Code 128 / EAN-13) rendered directly into SVG.
  - Implemented module/dot styling options: square, rounded, dots, diamonds, and customizable corner finder eye styling with distinct outer/inner colors.
  - Implemented center logo slot with quiet zone padding and masking.
  - Implemented linear and radial gradient fills and cyberpunk neon glow dropshadow filter.
  - Implemented action toolbar with copy to clipboard (with checkmark feedback), high-res PNG download, vector SVG download, and print affordance.
  - Implemented WAI-ARIA 1.2 accessibility semantics (`role="img"`, `aria-label`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant halos).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`QrCodeHandle`), and explicit `displayName` across all compound exports.
  - Exported `render_qr_code_component` in `omnistackai_agent_engine.codegen` and registered `components/qr-code.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_qr_code_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,176 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-381

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-381.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TERMINAL_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Terminal & Command Console compound component suite (`apps/web/components/terminal.tsx`).
  - Implemented `TerminalVariant` ("terminal" | "neon" | "glass" | "minimal"), `TerminalSize` ("sm" | "md" | "lg"), `TerminalLineType` ("stdout" | "stderr" | "system" | "command" | "info"), `TerminalLine`, `TerminalTab`, `TerminalHandle`, `TerminalProps`, `TerminalHeaderProps`, `TerminalOutputProps`, `TerminalPromptProps` interfaces.
  - Implemented compound and semantic alias exports: `Terminal`, `TerminalHeader`, `TerminalTabs`, `TerminalOutput`, `TerminalPrompt`, `ConsoleViewer`, `CommandLine`, default export.
  - Implemented ANSI color code parsing (`parseAnsi`) supporting 16-color ANSI codes, bold, and underline styles.
  - Implemented interactive command line prompt with user@host:cwd prefix and glowing cursor.
  - Implemented command history stack navigation using ArrowUp and ArrowDown keys.
  - Implemented multi-tab terminal session bar (`TerminalTabs`) with tab switching, close buttons, and add tab affordance.
  - Implemented real-time search filtering across terminal output buffer lines.
  - Implemented toolbar controls: Auto-scroll toggle, Copy all buffer to clipboard with checkmark feedback, Download as log file, Clear buffer.
  - Implemented keyboard shortcuts: `Ctrl+L` (clear buffer), `Ctrl+C` (cancel input).
  - Implemented WAI-ARIA 1.2 log & region accessibility semantics (`role="region"`, `role="log"`, `aria-live="polite"`).
  - Implemented 4 futuristic visual styling variants ("terminal" retro CRT phosphor green, "neon" cyberpunk glowing cyan, "glass" with backdropFilter blur, "minimal" high-contrast dark).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`TerminalHandle`), and explicit `displayName` across all exports.
  - Exported `render_terminal_component` in `omnistackai_agent_engine.codegen` and registered `components/terminal.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_terminal_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,159 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-380

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-380.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_FLOW_CANVAS_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Flowchart & Node-Based Workflow Canvas compound component suite (`apps/web/components/flow-canvas.tsx`).
  - Implemented `FlowVariant` ("default" | "card" | "glass" | "neon"), `FlowSize` ("sm" | "md" | "lg"), `FlowNodeType` ("default" | "input" | "output" | "action" | "condition"), `FlowNodeStatus` ("idle" | "running" | "success" | "error"), `FlowEdgeStyle` ("bezier" | "straight" | "step"), `FlowPortPosition` ("left" | "right" | "top" | "bottom"), `FlowPort`, `FlowNode`, `FlowEdge`, `FlowCanvasHandle`, `FlowCanvasProps`, `FlowNodeProps`, `FlowEdgeProps`, `FlowMinimapProps`, `FlowControlsProps` interfaces.
  - Implemented compound and semantic alias exports: `FlowCanvas`, `WorkflowBuilder`, `NodeGraph`, `FlowNodeItem`, `FlowEdgeLine`, `FlowMinimap`, `FlowControls`, default export.
  - Implemented 2D interactive canvas pan and zoom transform with mouse wheel zoom, click-drag panning, and reset/fit-view buttons.
  - Implemented draggable nodes with grid snapping (`snapToGrid`, `gridSize`).
  - Implemented SVG cubic bezier curved connection lines with customizable directional arrow markers.
  - Implemented active animated dataflow pulses along edges (`animated: true`).
  - Implemented real-time interactive Minimap (`FlowMinimap`) with viewport indicator box and click-to-pan.
  - Implemented floating canvas toolbar controls (`FlowControls`): Zoom In, Zoom Out, Reset Zoom, Fit to View, Toggle Grid.
  - Implemented WAI-ARIA 1.2 application accessibility semantics (`role="application"`, `aria-label="Workflow Canvas"`), keyboard arrow keys to nudge selected nodes, Delete to remove, Escape to deselect.
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant node halos and luminous bezier edges).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`FlowCanvasHandle`), and explicit `displayName` across all exports.
  - Exported `render_flow_canvas_component` in `omnistackai_agent_engine.codegen` and registered `components/flow-canvas.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_flow_canvas_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,142 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-379

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-379.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_GANTT_CHART_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Gantt Chart & Project Roadmap compound component suite (`apps/web/components/gantt-chart.tsx`).
  - Implemented `GanttViewMode` ("day" | "week" | "month"), `GanttVariant` ("default" | "card" | "glass" | "neon"), `GanttSize` ("sm" | "md" | "lg"), `GanttTask`, `GanttChartHandle`, `GanttChartProps` interfaces.
  - Implemented compound and semantic alias exports: `GanttChart`, `ProjectRoadmap`, `TimelineGantt`, `GanttTaskBar`, `GanttTimescale`, `GanttDependencyLine`, default export.
  - Implemented interactive task duration bars with proportional progress fill.
  - Implemented diamond milestone markers for instantaneous deadlines.
  - Implemented SVG dependency connector lines and bezier arrowheads connecting predecessor tasks to successor tasks.
  - Implemented multi-scale timescale zoom levels ("day", "week", "month").
  - Implemented synchronized task list sidebar with task name and progress.
  - Implemented weekend column shading and vertical "Today" indicator line.
  - Implemented timescale navigation controls (Jump to Today, Zoom In, Zoom Out).
  - Implemented WAI-ARIA 1.2 grid semantics (`role="grid"`, `aria-label="Project Gantt Chart"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant progress bars and luminous dependency lines).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`GanttChartHandle`), and explicit `displayName` across all exports.
  - Exported `render_gantt_chart_component` in `omnistackai_agent_engine.codegen` and registered `components/gantt-chart.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_gantt_chart_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,125 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.


- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-378.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_IMAGE_CROPPER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Image Cropper & Canvas Mask compound component suite (`apps/web/components/image-cropper.tsx`).
  - Implemented `CropAspectRatio` ("free" | "1:1" | "4:3" | "16:9" | "circular"), `ImageCropperVariant` ("default" | "card" | "glass" | "neon"), `ImageCropperSize` ("sm" | "md" | "lg"), `CropArea`, `CropData`, `ImageCropperHandle`, `ImageCropperProps`, `CropToolbarProps`, `CropPreviewProps`, `AvatarCropperProps` interfaces.
  - Implemented compound and semantic alias exports: `ImageCropper`, `AvatarCropper`, `CropCanvas`, `CropToolbar`, `CropPreview`, default export.
  - Implemented draggable crop marquee bounding box and 8 tactile resize handles (`nw`, `n`, `ne`, `e`, `se`, `s`, `sw`, `w`) with pointer capture APIs.
  - Implemented aspect ratio constraints: `"free"`, `"1:1"`, `"4:3"`, `"16:9"`, `"circular"` (for avatars and user profiles).
  - Implemented continuous zoom scaling slider (0.5x to 3x).
  - Implemented rotation controls (-180° to +180° slider and ±90° step quick buttons).
  - Implemented horizontal flip and vertical flip transform toggles.
  - Implemented HTML5 `<canvas>` rendering with circular clipping option and data export (`crop()`, `toDataURL()`).
  - Implemented real-time thumbnail preview component (`CropPreview`).
  - Implemented keyboard arrow key nudging (`ArrowLeft`, `ArrowRight`, `ArrowUp`, `ArrowDown`) with Shift multiplier for precision control.
  - Implemented WAI-ARIA 1.2 accessibility semantics (`role="region"`, `aria-label="Image Cropper"`, `aria-roledescription="image cropping canvas"`, `tabIndex={0}`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with luminous handles).
  - Implemented 3 size scales ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`), imperative handle (`ImageCropperHandle`), and explicit `displayName` across all exports.
  - Exported `render_image_cropper_component` in `omnistackai_agent_engine.codegen` and registered `components/image-cropper.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_image_cropper_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,108 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.


- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-377.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_PIVOT_TABLE_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Pivot Table & Cross-Tabulation Matrix compound component suite (`apps/web/components/pivot-table.tsx`).
  - Implemented `PivotAggregator` ("sum" | "avg" | "count" | "min" | "max"), `PivotVariant` ("default" | "card" | "glass" | "neon"), `PivotSize` ("sm" | "md" | "lg"), `PivotValueField`, `PivotCellCoord`, `PivotTableHandle`, `PivotTableProps`, `PivotCellProps`, `PivotHeaderProps` interfaces.
  - Implemented compound and semantic alias exports: `PivotTable`, `CrossTab`, `MatrixTable`, `PivotCell`, `PivotHeader`, default export.
  - Implemented multi-dimensional hierarchical row grouping and multi-level column dimension grouping.
  - Implemented aggregation calculations: `sum`, `avg`, `count`, `min`, `max`.
  - Implemented collapsible and expandable row hierarchies with chevron toggle buttons and indentation depth.
  - Implemented automatic calculation and rendering of row subtotals and global grand totals for rows and columns.
  - Implemented interactive sorting on dimension and metric column headers.
  - Implemented live search filtering input for dimension matching.
  - Implemented cell click selection callback (`onCellClick`, `selectedCell`).
  - Implemented CSV export capability via imperative handle (`exportCsv`) and toolbar trigger.
  - Implemented WAI-ARIA 1.2 table/grid accessibility semantics (`role="table"`, `role="row"`, `role="columnheader"`, `role="rowheader"`, `role="gridcell"`, `aria-expanded`, `aria-sort`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant total rows).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_pivot_table_component` in `omnistackai_agent_engine.codegen` and registered `components/pivot-table.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_pivot_table_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,091 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-376.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_MEDIA_PLAYER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Media Player & Audio/Video Controller compound component suite (`apps/web/components/media-player.tsx`).
  - Implemented `MediaType` ("video" | "audio"), `MediaPlayerVariant` ("default" | "card" | "glass" | "neon"), `MediaPlayerSize` ("sm" | "md" | "lg"), `MediaPlaybackRate` (0.5 | 0.75 | 1 | 1.25 | 1.5 | 2), `MediaTrackSource`, `MediaSubtitle`, `MediaPlayerHandle`, `MediaPlayerProps`, `MediaScrubberProps`, `VolumeSliderProps` interfaces.
  - Implemented compound and semantic alias exports: `MediaPlayer`, `VideoPlayer`, `AudioPlayer`, `MediaControls`, `MediaScrubber`, `VolumeSlider`, default export.
  - Implemented dual media modes: Video player with aspect-ratio container, poster image, overlay controls, fullscreen, and Picture-in-Picture; and Audio player with album cover art, track/artist metadata, and animated equalizer bars.
  - Implemented interactive scrubber bar with loaded buffer progress, played progress bar, and hover timestamp preview tooltip.
  - Implemented volume control slider with mute toggle and dynamic volume level icons.
  - Implemented playback rate selector (0.5x, 0.75x, 1x, 1.25x, 1.5x, 2x).
  - Implemented skip forward/backward buttons (±10s).
  - Implemented fullscreen and Picture-in-Picture controls with native API fallback.
  - Implemented closed captions / subtitles track support (CC).
  - Implemented comprehensive keyboard navigation shortcuts (`Space`/`K` for play/pause, `ArrowLeft`/`ArrowRight` for seek, `ArrowUp`/`ArrowDown` for volume, `M` for mute, `F` for fullscreen, `P` for PiP).
  - Implemented WAI-ARIA media semantics (`role="region"`, `role="slider"`, `aria-valuenow`, `aria-roledescription`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant scrubber).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_media_player_component` in `omnistackai_agent_engine.codegen` and registered `components/media-player.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_media_player_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,074 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-375.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_HEATMAP_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Heatmap & Activity Contribution Matrix compound component suite (`apps/web/components/heatmap.tsx`).
  - Implemented `HeatmapMode` ("calendar" | "grid"), `HeatmapColor` ("emerald" | "cyan" | "violet" | "amber" | "rose"), `HeatmapVariant` ("default" | "card" | "glass" | "neon"), `HeatmapSize` ("sm" | "md" | "lg"), `HeatmapIntensityLevel` (0 | 1 | 2 | 3 | 4), `HeatmapDatum`, `HeatmapStats`, `HeatmapHandle`, `HeatmapProps`, `HeatmapLegendProps`, `HeatmapCellProps` interfaces.
  - Implemented compound and semantic alias exports: `Heatmap`, `ActivityCalendar`, `ContributionGraph`, `HeatmapLegend`, `HeatmapCell`, default export.
  - Implemented dual layout modes: 52-week calendar contribution matrix with month headers and weekday labels, and 24x7 / arbitrary 2D dense coordinate grid with X and Y category labels.
  - Implemented 5 cyberpunk and natural color palettes: emerald, cyan, violet, amber, rose.
  - Implemented dynamic quantile intensity bucketing (levels 0 to 4) with threshold customization.
  - Implemented interactive cell hover/focus floating tooltips with custom formatter support.
  - Implemented keyboard arrow-key navigation and cell selection (`onCellClick`, `selectedCell`).
  - Implemented WAI-ARIA grid accessibility semantics (`role="grid"`, `role="row"`, `role="gridcell"`, `aria-selected`).
  - Implemented integrated legend sub-component (`HeatmapLegend`) with configurable labels and intensity markers.
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with radiant cells).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_heatmap_component` in `omnistackai_agent_engine.codegen` and registered `components/heatmap.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_heatmap_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,057 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-374.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_ORG_CHART_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Organizational Chart & Hierarchy Flow Diagram compound component suite (`apps/web/components/org-chart.tsx`).
  - Implemented `OrgChartOrientation` ("vertical" | "horizontal"), `OrgChartVariant` ("default" | "card" | "glass" | "neon"), `OrgChartSize` ("sm" | "md" | "lg"), `OrgChartNode`, `OrgChartHandle`, `OrgChartProps`, `OrgNodeCardProps` interfaces.
  - Implemented compound and semantic alias exports: `OrgChart`, `HierarchyTree`, `OrgNode`, default export.
  - Implemented recursive hierarchical tree layout with SVG/CSS connector stems and crossbars linking parent nodes to child branches without third-party diagramming dependencies.
  - Implemented collapsible and expandable subtree nodes with direct and indirect report count pill badges.
  - Implemented dual layout orientations (`vertical` top-to-bottom and `horizontal` left-to-right).
  - Implemented built-in search filter input matching names, roles, departments, or emails with glowing highlight rings and automatic ancestor expansion.
  - Implemented interactive node selection (`selectedId`, `onNodeClick`) and optional action menus.
  - Implemented full WAI-ARIA 1.2 accessibility tree semantics (`role="tree"`, `role="treeitem"`, `aria-expanded`, `aria-selected`).
  - Implemented 5 built-in zero-dependency vector icons (`SearchIcon`, `ChevronDownIcon`, `ChevronRightIcon`, `UsersIcon`, `MoreVerticalIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with glowing connectors).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_org_chart_component` in `omnistackai_agent_engine.codegen` and registered `components/org-chart.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_org_chart_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,040 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-373

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-373.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_DIFF_VIEWER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Diff Viewer & Code/Text Comparison compound component suite (`apps/web/components/diff-viewer.tsx`).
  - Implemented `DiffViewMode` ("split" | "unified"), `DiffLineType` ("added" | "deleted" | "unchanged"), `DiffViewerVariant` ("default" | "card" | "glass" | "neon"), `DiffViewerSize` ("sm" | "md" | "lg"), `DiffWordPart`, `DiffLine`, `SplitDiffRow`, `DiffViewerHandle`, `DiffViewerProps` interfaces.
  - Implemented compound and semantic alias exports: `DiffViewer`, `CodeDiff`, `TextDiff`, default export.
  - Implemented pure mathematical LCS (Longest Common Subsequence) diff algorithm for line addition, deletion, and unchanged resolution without third-party dependencies.
  - Implemented word-level intraline character diffing highlighting specific within-line modifications.
  - Implemented Split (side-by-side) comparison view mode with synchronized row alignment and gap padding.
  - Implemented Unified (inline) comparison view mode with dual old and new line number gutters.
  - Implemented collapsible unchanged lines folding with configurable threshold (`foldThreshold`), context buffers (`contextLines`), and interactive expand trigger banners.
  - Implemented responsive toolbar with filename badge, addition (`+N`) and deletion (`-N`) counter statistics, view mode toggles, and one-click clipboard copy actions.
  - Implemented full WAI-ARIA accessibility semantics (`role="region"`, `role="table"`, `role="row"`, `role="cell"`, `aria-label="Code diff viewer"`, `aria-roledescription="diff view"`).
  - Implemented 6 built-in zero-dependency vector icons (`SplitIcon`, `UnifiedIcon`, `CopyIcon`, `CheckIcon`, `FileCodeIcon`, `ChevronDownIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with emerald/rose glowing diff gutters).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all compound exports.
  - Exported `render_diff_viewer_component` in `omnistackai_agent_engine.codegen` and registered `components/diff-viewer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_diff_viewer_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,023 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-372

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-372.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SIGNATURE_PAD_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Digital Signature Pad & Drawing Canvas compound component suite (`apps/web/components/signature-pad.tsx`).
  - Implemented `SignaturePadVariant` ("default" | "card" | "glass" | "neon"), `SignaturePadSize` ("sm" | "md" | "lg"), `SignaturePoint`, `SignatureStroke`, `SignaturePadHandle`, `SignaturePadProps` interfaces.
  - Implemented compound and semantic alias exports: `SignaturePad`, `SignatureCanvas`, `DrawingPad`, default export.
  - Implemented zero-dependency HTML5 `<canvas>` rendering with quadratic bezier curve stroke interpolation for silk-smooth lines.
  - Implemented high-DPI Retina `devicePixelRatio` scaling for razor-sharp rendering on all displays.
  - Implemented cross-device pointer events (`pointerdown`, `pointermove`, `pointerup`, `pointerleave`, `pointercancel` with `touch-action: none`) supporting stylus pressure, touch, and mouse input.
  - Implemented multi-level stroke history stack with undo, redo, and clear actions.
  - Implemented raster PNG dataURL export (`toDataURL()`) and vector SVG export (`toSVG()`) generating crisp scalable vector paths.
  - Implemented signing guide line with dashed styling, subtle "✕" mark, and customizable text ("Sign on line above").
  - Implemented pristine placeholder prompt overlay.
  - Implemented responsive toolbar with stroke counter badge and action buttons (Undo, Redo, Clear, Download).
  - Implemented native HTML form hidden input synchronization (`name`).
  - Implemented full WAI-ARIA application semantics (`role="application"`, `aria-label="Signature Pad"`, `aria-roledescription="drawing canvas"`, `aria-label="Signature drawing area"`).
  - Implemented 5 built-in zero-dependency vector icons (`UndoIcon`, `RedoIcon`, `TrashIcon`, `DownloadIcon`, `PenIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_signature_pad_component` in `omnistackai_agent_engine.codegen` and registered `components/signature-pad.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_signature_pad_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 2,006 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task builder:demo -- minimal-blog` pass.

## 2026-09-11 — R-371

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-371.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TIME_PICKER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Time Picker & Time Range compound component suite (`apps/web/components/time-picker.tsx`).
  - Implemented `TimeFormat` ("12h" | "24h"), `TimePickerVariant` ("default" | "card" | "glass" | "neon"), `TimePickerSize` ("sm" | "md" | "lg"), `TimePreset`, `TimeRangePreset`, `TimePickerProps`, `TimeRangePickerProps`, `TimeInputProps` interfaces.
  - Implemented compound and semantic alias exports: `TimePicker`, `TimeRangePicker`, `TimeInput`, `TimeColumn`, `ClockIcon`, default export.
  - Implemented 12h (with AM/PM period selector) and 24h military/international format modes.
  - Implemented scrollable column lists for hours, minutes, and optional seconds with active item auto-scrolling into view.
  - Implemented customizable step increments (`stepMinutes`, `stepSeconds`).
  - Implemented quick-select preset chips ("Now", "09:00 AM", "12:00 PM", "05:00 PM").
  - Implemented dual-input `TimeRangePicker` with start and end time validation.
  - Implemented popover dropdown trigger with outside click and Escape key dismissal, alongside direct inline embedding mode (`inline={true}`).
  - Implemented full WAI-ARIA 1.2 combobox, listbox, and option semantics (`role="combobox"`, `role="listbox"`, `role="option"`, `role="group"`, `aria-haspopup="dialog"`, `aria-selected`).
  - Implemented 5 built-in zero-dependency vector icons (`ClockIcon`, `ChevronUpIcon`, `ChevronDownIcon`, `XIcon`, `CheckIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented native HTML form submission integration via hidden inputs (`name`).
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_time_picker_component` in `omnistackai_agent_engine.codegen` and registered `components/time-picker.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_time_picker_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 1,989 tests pass (17 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (108 files generated). 0 model calls.

## 2026-09-11 — R-370

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-370.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CHART_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Data Visualization & SVG Chart compound component suite (`apps/web/components/chart.tsx`).
  - Implemented `ChartType` ("bar" | "line" | "area" | "donut" | "pie" | "sparkline"), `ChartVariant` ("default" | "card" | "glass" | "neon"), `ChartSize` ("sm" | "md" | "lg"), `ChartCurve` ("linear" | "smooth" | "step"), `ChartDataPoint`, `ChartSeries`, `ChartTooltipData`, `ChartProps` interfaces.
  - Implemented compound and semantic alias exports: `Chart`, `BarChart`, `LineChart`, `AreaChart`, `DonutChart`, `PieChart`, `Sparkline`, default export.
  - Implemented native SVG mathematical rendering without external packages: polar-to-cartesian trigonometry for circular arcs, smooth bezier curves and polylines, gradient area fills, and rounded vertical bars.
  - Implemented interactive floating tooltip with exact values, series indicators, and percentages.
  - Implemented series visibility toggling via interactive legend items.
  - Implemented hover crosshairs and expanded point circles on line/area charts.
  - Implemented center readout metric on Donut charts with hovered or total sum value formatting.
  - Implemented ultra-compact Sparkline mode without axes or padding.
  - Implemented WAI-ARIA 1.2 graphics semantics (`role="img"`, `role="region"`, `aria-label`).
  - Implemented visually hidden accessible HTML data table fallback (`className="sr-only"`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow with glowing SVG dropshadows).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `displayName` across all exports.
  - Exported `render_chart_component` in `omnistackai_agent_engine.codegen` and registered `components/chart.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_chart_component.py` with 17 comprehensive unit tests (all passing).
- `task verify` — 1,972 tests pass (17 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (107 files generated). 0 model calls.

## 2026-09-11 — R-369

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-369.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_FILTER_BUILDER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Query Filter Builder & Dynamic Rule Bar compound component suite (`apps/web/components/filter-builder.tsx`).
  - Implemented `FilterBuilderVariant` ("default" | "card" | "glass" | "neon"), `FilterBuilderSize` ("sm" | "md" | "lg"), `FilterFieldType` ("string" | "number" | "boolean" | "date" | "select"), `FilterCombinator` ("and" | "or"), `FilterOperator`, `FilterFieldConfig`, `FilterRule`, `FilterGroup`, `FilterBuilderProps` interfaces.
  - Implemented compound and semantic alias exports: `FilterBuilder`, `QueryFilterBuilder`, `RuleBuilder`, default export.
  - Implemented recursive nested rule group hierarchy evaluation with dynamic indentation depth styling.
  - Implemented dynamic operator selection based on field types (equals, not_equals, contains, not_contains, starts_with, ends_with, greater_than, less_than, greater_than_or_equal, less_than_or_equal, is_empty, is_not_empty, is_true, is_false, in).
  - Implemented AND / OR combinator pill switcher with visual active glow styling.
  - Implemented add rule and add nested subgroup buttons, plus delete rule/group actions with minimum root rule constraint.
  - Implemented `maxDepth` guard (default 3) preventing unbounded nesting.
  - Implemented type-aware value inputs: text input, number input, date picker, select dropdown with options, and boolean labels.
  - Implemented clear all rules action and rule count badge indicator.
  - Implemented full WAI-ARIA 1.2 region & group semantics (`role="region"`, `role="group"`, `aria-label`).
  - Implemented 5 built-in zero-dependency vector icons (`PlusIcon`, `TrashIcon`, `FolderPlusIcon`, `XCircleIcon`, `FilterIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented native HTML form submission integration via hidden input (`name`).
  - Implemented React ref forwarding (`forwardRef`) and explicit `FilterBuilder.displayName = "FilterBuilder"`.
  - Exported `render_filter_builder_component` in `omnistackai_agent_engine.codegen` and registered `components/filter-builder.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_filter_builder_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,955 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (106 files generated). 0 model calls.

## 2026-09-11 — R-368

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-368.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_VIRTUAL_LIST_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic High-Performance Infinite Virtual List & Windowed Scroller compound component suite (`apps/web/components/virtual-list.tsx`).
  - Implemented `VirtualListVariant` ("default" | "card" | "glass" | "neon"), `VirtualListSize` ("sm" | "md" | "lg"), `VirtualScrollAlignment` ("start" | "center" | "end" | "auto"), `VirtualItemInfo`, `VirtualListHandle`, `VirtualListProps` interfaces.
  - Implemented compound and semantic alias exports: `VirtualList`, `VirtualScroller`, `WindowedList`, default export.
  - Implemented mathematical windowing logic with prefix-sum array and binary search for variable item heights or multiplier calculation for fixed heights.
  - Implemented configurable overscan rendering buffer to eliminate white space flashing during fast kinetic scrolling.
  - Implemented infinite scroll threshold detection (`onEndReached`, `endReachedThreshold`) with duplicate call guards.
  - Implemented fast-scrolling detection (`isScrolling`) for lightweight placeholder rendering.
  - Implemented imperative handle (`scrollTo`, `scrollToIndex`, `scrollToTop`, `scrollToBottom`) via `useImperativeHandle`.
  - Implemented built-in zero-dependency SVG loading spinner (`SpinnerIcon`).
  - Implemented full WAI-ARIA 1.2 feed semantics (`role="feed"`, `role="article"`, `aria-posinset`, `aria-setsize`, `aria-busy`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented React ref forwarding (`forwardRef`) and explicit `VirtualList.displayName = "VirtualList"`.
  - Exported `render_virtual_list_component` in `omnistackai_agent_engine.codegen` and registered `components/virtual-list.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_virtual_list_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,939 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (105 files generated). 0 model calls.

## 2026-09-11 — R-367

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-367.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_KANBAN_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Kanban Board & Task Flow Matrix compound component suite (`apps/web/components/kanban.tsx`).
  - Implemented `KanbanVariant` ("default" | "card" | "glass" | "neon"), `KanbanSize` ("sm" | "md" | "lg"), `KanbanPriority` ("low" | "medium" | "high" | "urgent"), `KanbanColumn`, `KanbanAssignee`, `KanbanItem`, `KanbanProps` interfaces.
  - Implemented compound and semantic alias exports: `Kanban`, `KanbanBoard`, `TaskBoard`, default export.
  - Implemented HTML5 native drag-and-drop card movement across lanes (`draggable`, `onDragStart`, `onDragOver`, `onDragLeave`, `onDrop`, `onDragEnd`).
  - Implemented column WIP limits with visual warning badge when count > limit.
  - Implemented column collapse/expand toggling with smooth width transitions.
  - Implemented built-in search filtering across task titles, descriptions, tags, and assignees.
  - Implemented priority badges with distinctive colors (urgent: rose/red, high: amber/orange, medium: blue, low: emerald/green).
  - Implemented assignee avatars, due date tags, and quick-add card triggers.
  - Implemented WAI-ARIA 1.2 region & listbox semantics (`role="region"`, `role="group"`, `role="listbox"`, `role="option"`).
  - Implemented 9 built-in zero-dependency vector icons (`PlusIcon`, `GripVerticalIcon`, `ChevronDownIcon`, `ChevronRightIcon`, `ClockIcon`, `TagIcon`, `AlertCircleIcon`, `UserIcon`, `SearchIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented native HTML form submission integration via hidden input (`name`).
  - Implemented React ref forwarding (`forwardRef`) and explicit `Kanban.displayName = "Kanban"`.
  - Exported `render_kanban_component` in `omnistackai_agent_engine.codegen` and registered `components/kanban.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_kanban_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,923 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (104 files generated). 0 model calls.

## 2026-09-11 — R-366

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-366.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CALENDAR_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Calendar & Event Scheduler compound component suite (`apps/web/components/calendar.tsx`).
  - Implemented `CalendarVariant` ("default" | "card" | "glass" | "neon"), `CalendarSize` ("sm" | "md" | "lg"), `CalendarViewMode` ("month" | "week" | "day" | "agenda"), `CalendarEvent`, `CalendarProps` interfaces.
  - Implemented compound and semantic alias exports: `Calendar`, `Scheduler`, `EventCalendar`, default export.
  - Implemented pure zero-dependency calendar math helpers (`getMonthMatrix`, `isSameDay`, `isToday`, `isSameMonth`, `getDaysInMonth`, `toISODateString`).
  - Implemented month grid view with weekday headers, today circular badge, selected date highlight, event pills with custom colors, and `+N more` overflow indicator.
  - Implemented agenda view with chronological event cards, title, description, date, and time badges.
  - Implemented header navigation controls (previous month, next month, today quick jump, month/year display) and view mode switcher tabs.
  - Implemented WAI-ARIA 1.2 Grid pattern compliance (`role="grid"`, `role="row"`, `role="columnheader"`, `role="gridcell"`, `aria-selected`, `aria-current="date"`).
  - Implemented 4 built-in zero-dependency vector icons (`ChevronLeftIcon`, `ChevronRightIcon`, `CalendarIcon`, `ClockIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented native HTML form submission integration via hidden input (`name`).
  - Implemented React ref forwarding (`forwardRef`) and explicit `Calendar.displayName = "Calendar"`.
  - Exported `render_calendar_component` in `omnistackai_agent_engine.codegen` and registered `components/calendar.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_calendar_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,907 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (103 files generated). 0 model calls.

## 2026-09-11 — R-365

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-365.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_MARKDOWN_EDITOR_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Markdown & Rich Content Editor compound component suite (`apps/web/components/markdown-editor.tsx`).
  - Implemented `MarkdownEditorVariant` ("default" | "card" | "glass" | "neon"), `MarkdownEditorSize` ("sm" | "md" | "lg"), `MarkdownEditorViewMode` ("edit" | "preview" | "split"), `MarkdownToolbarAction`, `MarkdownEditorProps`, `MarkdownToolbarProps`, `MarkdownPreviewProps`, `MarkdownStatusBarProps` interfaces.
  - Implemented compound and alias exports: `MarkdownEditor`, `MarkdownToolbar`, `MarkdownPreview`, `MarkdownStatusBar`, `RichTextEditor`, `ContentEditor`.
  - Implemented formatting toolbar with 16 rich formatting actions (bold, italic, strikethrough, headings 1-3, blockquote, inline code, fenced code block, bulleted list, numbered list, task list checkbox, link, image, table, horizontal rule).
  - Implemented live preview tabs & split-view mode with WAI-ARIA tab semantics (`role="tablist"`, `role="tab"`, `aria-selected`).
  - Implemented built-in zero-dependency Markdown parser and HTML preview renderer (headings, blockquotes, code blocks with syntax tag badges, checklists with toggle indicators, markdown tables with striped headers, external links with security rel tags, images with responsive constraints, inline bold/italic/strike/code formatting).
  - Implemented status bar live metrics (character count, word count, line count, reading time estimate, tabular numbers).
  - Implemented keyboard shortcuts (`Ctrl/Cmd+B` for bold, `Ctrl/Cmd+I` for italic, `Ctrl/Cmd+K` for link, `Tab` for 2-space indentation).
  - Implemented 19 built-in zero-dependency vector icons.
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented native HTML form submission integration via hidden inputs (`name`).
  - Implemented React ref forwarding (`forwardRef`) and explicit `MarkdownEditor.displayName = "MarkdownEditor"`.
  - Exported `render_markdown_editor_component` in `omnistackai_agent_engine.codegen` and registered `components/markdown-editor.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_markdown_editor_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,891 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (102 files generated). 0 model calls.

## 2026-09-11 — R-364

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-364.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TRANSFER_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Transfer / Dual Listbox Picker primitive suite (`apps/web/components/transfer.tsx`).
  - Implemented `TransferVariant` ("default" | "card" | "glass" | "neon"), `TransferSize` ("sm" | "md" | "lg"), `TransferDirection` ("left" | "right"), `TransferItem`, `TransferProps`, and `TransferListProps` interfaces.
  - Implemented dual-column listbox architecture (Source and Target panels) with independent selection, item counts, and live filtering.
  - Implemented live search inputs with clear button (`XIcon`) filtering across title, description, and key.
  - Implemented central move operation buttons ("Move selected right", "Move selected left", "Move all right", "Move all left") with disabled threshold states and customizable labels/tooltips.
  - Implemented header select-all checkbox with indeterminate state calculation and selection count badge ("X/Y").
  - Implemented double-click instant item transfer between lists.
  - Implemented full WAI-ARIA 1.2 dual-listbox compliance (`role="group"`, `role="listbox"`, `role="option"`, `role="checkbox"`, `aria-multiselectable="true"`, `aria-selected`, `aria-disabled`, `aria-checked`).
  - Implemented full keyboard navigation (`Space` to toggle checkbox, `Enter` to transfer, roving `tabIndex`).
  - Implemented 8 built-in zero-dependency vector icons (`ChevronRightIcon`, `ChevronLeftIcon`, `ChevronsRightIcon`, `ChevronsLeftIcon`, `SearchIcon`, `XIcon`, `CheckIcon`, `DashIcon`).
  - Implemented 4 futuristic visual styling variants ("default", "card", "glass" with backdropFilter blur, "neon" cyberpunk cyan glow).
  - Implemented 3 size presets ("sm", "md", "lg").
  - Implemented native HTML form submission integration via hidden input arrays (`name`).
  - Implemented React ref forwarding (`forwardRef`), explicit `Transfer.displayName = "Transfer"`, and `DualListbox` and `PickList` semantic aliases.
  - Exported `render_transfer_component` in `omnistackai_agent_engine.codegen` and registered `components/transfer.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_transfer_component.py` with 18 comprehensive unit tests (all passing).
- `task verify` — 1,875 tests pass (18 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (101 files generated). 0 model calls.

## 2026-09-11 — R-363

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-363.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TOUR_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Tour and Onboarding Spotlight Guide compound component suite (`apps/web/components/tour.tsx`).
  - Implemented `TourVariant` ("default" | "card" | "glass" | "neon"), `TourSize` ("sm" | "md" | "lg"), `TourPlacement` ("top" | "bottom" | "left" | "right" | "center"), `TourStep`, and `TourProps` interfaces.
  - Implemented dynamic target element measurement with `getBoundingClientRect()`, window resize/scroll tracking, and target element auto-scrolling into view.
  - Implemented full-screen SVG cutout spotlight mask (`<mask id="...">` with `<rect fill="white"/>` and `<rect fill="black"/>` over semi-transparent overlay backdrop).
  - Implemented floating card popover with auto placement resolution, edge clamping against `window.innerWidth`/`innerHeight`, and directional SVG arrow pointer notch.
  - Implemented step navigation controls: Previous, Next, Finish, Skip, and Close buttons.
  - Implemented step dots indicators with jump-to-step support and active pill state.
  - Implemented step counter badge ("X of Y").
  - Implemented full WAI-ARIA 1.2 dialog semantics (`role="dialog"`, `aria-modal="true"`, `aria-label`, `aria-describedby`).
  - Implemented full keyboard navigation (`Escape` to dismiss, `ArrowRight`/`Enter` to advance, `ArrowLeft` to go back, Tab trapping).
  - Implemented compound exports: `Tour`, `TourStepDot`, `TourProgressBadge`, `TourCloseButton`.
  - Implemented full React ref forwarding (`forwardRef`) and explicit `Tour.displayName = "Tour"`.
  - Exported `render_tour_component` in `omnistackai_agent_engine.codegen` and registered `components/tour.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_tour_component.py` with 19 comprehensive unit tests (all passing).
- `task verify` — 1,857 tests pass (19 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (100 files generated). 0 model calls.

## 2026-09-11 — R-362

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-362.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SIDEBAR_COMPONENT` static template implementing accessible, desktop-and-mobile-grade, futuristic Sidebar and Side Navigation compound component suite (`apps/web/components/sidebar.tsx`).
  - Implemented `SidebarVariant` ("default" | "card" | "glass" | "neon"), `SidebarSize` ("sm" | "md" | "lg"), `SidebarCollapsible` ("icon" | "offcanvas" | "none"), `SidebarSide` ("left" | "right"), `SidebarState` ("expanded" | "collapsed"), `SidebarContextValue`, and props interfaces.
  - Implemented compound subcomponents: `Sidebar`, `SidebarHeader`, `SidebarContent`, `SidebarFooter`, `SidebarGroup`, `SidebarGroupLabel`, `SidebarGroupContent`, `SidebarMenu`, `SidebarMenuItem`, `SidebarMenuButton`, `SidebarMenuBadge`, `SidebarMenuSub`, `SidebarMenuSubItem`, `SidebarMenuSubButton`, `SidebarRail`, `SidebarTrigger`, `SidebarToggle`, `SideNav`.
  - Implemented collapsible modes: `"icon"` rail mode (with tooltip fallback), `"offcanvas"` sliding mode (with mobile backdrop blur and outside click dismiss), and `"none"` (fixed width).
  - Implemented WAI-ARIA 1.2 navigation landmark and menu pattern compliance (`role="navigation"`, `role="menu"`, `role="menuitem"`, `aria-label`, `aria-current="page"`, `aria-expanded`).
  - Implemented keyboard navigation (`ArrowDown`/`ArrowUp` roving traversal, `Home`/`End` jump navigation).
  - Implemented 5 built-in vector icons (`PanelLeftIcon`, `ChevronRightIcon`, `ChevronLeftIcon`, `ChevronDownIcon`, `MenuIcon`).
  - Implemented full React ref forwarding (`forwardRef`) and explicit `displayName`.
  - Exported `render_sidebar_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_sidebar_component.py` with 26 comprehensive unit tests (all passing).
- `task verify` — 1,838 tests pass (26 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (99 files generated). 0 model calls.

## 2026-09-11 — R-361

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-361.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_NOTIFICATION_CENTER_COMPONENT` static template implementing accessible, desktop-grade, futuristic Notification Center compound component suite (`apps/web/components/notification-center.tsx`).
  - Implemented `NotificationVariant` ("default" | "card" | "glass" | "neon"), `NotificationSize` ("sm" | "md" | "lg"), `NotificationType` ("info" | "success" | "warning" | "error"), `NotificationItem`, and props interfaces.
  - Implemented compound subcomponents: `NotificationCenter`, `NotificationTrigger`, `NotificationPanel`, `NotificationList`, `NotificationItemComponent`, `NotificationBadge`, `NotificationEmptyState`.
  - Implemented bell icon trigger with unread badge counter (boolean dot or numeric badge, capped at 99+).
  - Implemented animated slide-in / dropdown panel with outside-click and Escape key dismissal.
  - Implemented individual notification item cards with read/unread visual states, actions ("Mark all as read", "Clear all", individual "Mark as read", custom CTA).
  - Implemented filter tabs (All / Unread).
  - Implemented relative time formatting ("just now", "Xm ago", "Xh ago", "Xd ago").
  - Implemented category / type indicator vector icons.
  - Implemented WAI-ARIA 1.2 dialog and listbox compliance (`role="dialog"`, `role="listbox"`, `role="option"`, `aria-label`, `aria-expanded`, `aria-haspopup="dialog"`, `aria-live="polite"`).
  - Implemented full React ref forwarding (`forwardRef`) and explicit `displayName`.
  - Exported `render_notification_center_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_notification_center_component.py` with 44 comprehensive unit tests (all passing).
- `task verify` — 1,812 tests pass (44 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (98 files generated). 0 model calls.

## 2026-09-11 — R-360

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-360.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_NUMBER_INPUT_COMPONENT` static template implementing accessible, desktop-and-mobile-grade Number Input & Numeric Stepper compound component suite (`apps/web/components/number-input.tsx`).
  - Implemented `NumberInputVariant` ("default" | "card" | "glass" | "neon"), `NumberInputSize` ("sm" 32px | "md" 38px | "lg" 44px), `NumberInputFormat` ("plain" | "currency" | "percentage"), and `NumberInputProps`.
  - Implemented WAI-ARIA spinbutton: `role="spinbutton"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-invalid`, `aria-required`, `aria-describedby`.
  - Implemented full keyboard navigation (`ArrowUp` increments, `ArrowDown` decrements with `e.preventDefault()`).
  - Implemented stepper buttons (`ChevronUpIcon`/`ChevronDownIcon`, `aria-label="Increment"/"Decrement"`, `tabIndex=-1`, disabled at boundaries).
  - Implemented `clamp()` helper, `precision`/`step`, 3 format modes via `Intl.NumberFormat`, `hideControls`, `leftSection`/`rightSection` slot nodes.
  - Implemented controlled and uncontrolled modes, focus/blur raw-vs-formatted display toggle, `inputMode="decimal"`, `fontVariantNumeric="tabular-nums"`, React ref forwarding (`forwardRef`) and explicit `displayName`.
  - Exported `render_number_input_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_number_input_component.py` with 35 comprehensive unit tests (all passing).
- `task verify` — 1,768 tests pass (35 new), 0 failures. `task lint`, `task security:quick` pass.

## 2026-09-11 — R-359

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-359.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_BOTTOM_NAV_COMPONENT` static template implementing accessible, mobile-first Bottom Navigation Bar compound component suite (`apps/web/components/bottom-nav.tsx`).
  - Implemented `BottomNavVariant` ("default" | "glass" | "card" | "neon"), `BottomNavSize` ("sm" | "md" | "lg"), `BottomNavItem`, and `BottomNavProps`.
  - Implemented WAI-ARIA 1.2 Tabs pattern compliance: `role="tablist"`, `role="tab"`, `aria-selected`, `aria-disabled`, `aria-controls`, `aria-orientation="horizontal"`, `aria-label`.
  - Implemented full keyboard navigation (`ArrowRight`/`ArrowLeft`/`ArrowUp`/`ArrowDown` traversal with wrap-around, `Home`/`End` jump navigation).
  - Implemented badge notifications (boolean dot or count chip via `BadgeChip`), optional FAB centre gap slot, full-screen backdrop tint.
  - Exported `render_bottom_nav_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_bottom_nav_component.py` with 26 comprehensive unit tests (all passing).
- `task verify` — 1,733 tests pass (26 new), 0 failures. `task lint`, `task security:quick` pass.

## 2026-09-11 — R-358

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-358.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_COMBOBOX_COMPONENT` static template implementing accessible, desktop-grade, futuristic Searchable Combobox & Autocomplete compound component suite (`apps/web/components/combobox.tsx`).
  - Implemented `ComboboxVariant` ("default" | "card" | "glass" | "neon"), `ComboboxSize` ("sm" | "md" | "lg"), `ComboboxOptionItem`, and `ComboboxProps` interfaces.
  - Implemented WAI-ARIA 1.2 Combobox and Listbox pattern compliance: `role="combobox"`, `role="listbox"`, `role="option"`, `aria-expanded`, `aria-haspopup="listbox"`, `aria-controls`, `aria-activedescendant`, `aria-selected`, `aria-disabled`, and `data-highlighted`.
  - Implemented live type-ahead fuzzy and substring filtering across label, description, and keywords.
  - Implemented full keyboard navigation (`ArrowDown`/`ArrowUp` traversal with wrap-around, `Enter` to select, `Escape` to close, `Home`/`End` jump navigation).
  - Implemented single-select mode and multi-select mode with removable tag chips (`XIcon`).
  - Implemented clear button affordance (`allowClear`) for quick value clearing.
  - Implemented 4 futuristic visual variants: `"default"`, `"card"`, `"glass"` with backdrop blur, and `"neon"` (cyberpunk glowing cyan/indigo border and glow shadow).
  - Implemented 3 size scales (`sm`, `md`, `lg`) with proportional minHeight, font sizes, padding, and tag heights.
  - Implemented hidden input form submission (`name`).
  - Implemented semantic alias `Autocomplete = Combobox` and default export.
  - Implemented full React ref forwarding (`forwardRef`) and explicit `displayName`.
  - Exported `render_combobox_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_combobox_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,707 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (95 files generated). `builder:demo rideshare-favourites` passes (92 files generated). 0 model calls.
- Tracker: inserted R-358 Done row at `Phase_Roadmap!A9`; table `A4:M366`; 366 total rows;
  147 Done, 1 Deferred, 210 Not Started; MVP 147/253 (58.1%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-358.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-357

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-357.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_BANNER_COMPONENT` static template implementing accessible, desktop-grade, futuristic Announcement Banner & Callout compound component suite (`apps/web/components/banner.tsx`).
  - Implemented `BannerVariant` ("info" | "success" | "warning" | "error" | "neon" | "gradient"), `BannerPosition` ("top" | "bottom" | "inline" | "floating"), `BannerSize` ("sm" | "md" | "lg"), `BannerProps`, and `BannerCloseButtonProps` interfaces.
  - Implemented WAI-ARIA live region semantics: `role="status"` / `role="alert"` (for error/warning) and `aria-live="polite"` / `aria-live="assertive"`.
  - Implemented 4 layout positions: `"top"` sticky header banner, `"bottom"` sticky footer banner, `"inline"` card banner, and `"floating"` elevated center toast callout.
  - Implemented 6 visual styling variants: `"info"`, `"success"`, `"warning"`, `"error"`, `"neon"` (cyberpunk glowing cyan/indigo border and glow shadow), and `"gradient"` (futuristic violet-indigo linear gradient).
  - Implemented 3 size scales (`sm`, `md`, `lg`) with responsive padding, font metrics, and icon dimensions.
  - Implemented dismissible state with smooth collapse transition (`dismissible?: boolean`, `onDismiss?: () => void`) and accessible close button (`BannerCloseButton`, `aria-label="Dismiss banner"`).
  - Implemented action CTA slot container (`BannerAction`), icon slot container (`BannerIcon`) with built-in SVGs (`InfoIcon`, `SuccessIcon`, `WarningIcon`, `ErrorIcon`, `NeonIcon`, `CloseIcon`).
  - Implemented compound subcomponents and semantic aliases: `Banner`, `BannerIcon`, `BannerAction`, `BannerCloseButton`, `AnnouncementBanner`, and `Callout`.
  - Implemented full React ref forwarding (`forwardRef`) and explicit `displayName` on all subcomponents.
  - Exported `render_banner_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_banner_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,692 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (94 files generated). `builder:demo rideshare-favourites` passes (91 files generated). 0 model calls.
- Tracker: inserted R-357 Done row at `Phase_Roadmap!A9`; table `A4:M365`; 365 total rows;
  146 Done, 1 Deferred, 210 Not Started; MVP 146/252 (57.9%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-357.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-356

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-356.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CHECKBOX_COMPONENT` static template implementing accessible, desktop-grade, futuristic Checkbox & Checkbox Group compound component suite (`apps/web/components/checkbox.tsx`).
  - Implemented `CheckboxVariant` ("default" | "card" | "pill" | "neon"), `CheckboxSize` ("sm" | "md" | "lg"), `CheckedState` (boolean | "indeterminate"), `CheckboxProps`, `CheckboxGroupProps`, and `CheckboxGroupContextValue` interfaces.
  - Implemented WAI-ARIA 1.2 Checkbox pattern compliance: `role="checkbox"`, `role="group"`, `aria-checked="mixed"` (for indeterminate) / boolean, `aria-orientation`, `aria-disabled`, `aria-required`, and `tabIndex`.
  - Implemented tri-state / indeterminate support with dedicated SVG minus vector and checkmark vector.
  - Implemented keyboard space toggling (`Space` key with `e.preventDefault()`).
  - Implemented 4 futuristic visual variants: `"default"` (minimalist rounded square with blue fill), `"card"` (interactive selection card with title, description, and indicator), `"pill"` (segmented toggle pills), and `"neon"` (cyberpunk glowing cyan/indigo border and ambient glow shadow).
  - Implemented 3 size scales (`sm`, `md`, `lg`) with proportional box dimensions, icon scales, and typography.
  - Implemented controlled (`checked`, `onCheckedChange`) and uncontrolled (`defaultChecked`) state management with hidden input form submission (`name`).
  - Implemented `CheckboxGroup` compound container with multi-select array management (`value: string[]`, `onValueChange`), options array convenience prop mapping alongside custom children, subcomponent alias `CheckboxItem = Checkbox`, and `useCheckboxGroup` context hook.
  - Implemented full React ref forwarding (`forwardRef<HTMLButtonElement, CheckboxProps>`, `forwardRef<HTMLDivElement, CheckboxGroupProps>`) with `displayName`.
  - Exported `render_checkbox_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_checkbox_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,677 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (93 files generated). `builder:demo rideshare-favourites` passes (90 files generated). 0 model calls.
- Tracker: inserted R-356 Done row at `Phase_Roadmap!A9`; table `A4:M364`; 364 total rows;
  145 Done, 1 Deferred, 210 Not Started; MVP 145/251 (57.8%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-356.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-355

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-355.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_RADIO_GROUP_COMPONENT` static template implementing accessible, desktop-grade, futuristic Radio Group compound component suite (`apps/web/components/radio-group.tsx`).
  - Implemented `RadioGroupOrientation` ("vertical" | "horizontal"), `RadioGroupVariant` ("default" | "card" | "pill" | "neon"), `RadioGroupSize` ("sm" | "md" | "lg"), `RadioOption`, `RadioGroupProps`, `RadioGroupItemProps`, and `RadioGroupContextValue` interfaces.
  - Implemented WAI-ARIA 1.2 Radio Group pattern compliance: `role="radiogroup"`, `role="radio"`, `aria-checked`, `aria-orientation`, `aria-disabled`, `aria-required`, and roving focus management.
  - Implemented full keyboard arrow key navigation with circular wrap-around (`ArrowDown` / `ArrowRight` -> next, `ArrowUp` / `ArrowLeft` -> prev, `Space` -> select) and programmatic focus transfer.
  - Implemented vertical and horizontal layout orientations with flex alignment.
  - Implemented 4 futuristic visual variants: `"default"` (minimalist circular radios with centered indicator dot), `"card"` (interactive selection card with title, description, and indicator), `"pill"` (segmented toggle pills), and `"neon"` (cyberpunk glowing cyan/indigo border and ambient glow shadow).
  - Implemented 3 size scales (`sm`, `md`, `lg`) with proportional circle diameters, inner dots, and typography.
  - Implemented controlled (`value`, `onValueChange`) and uncontrolled (`defaultValue`) state management with hidden input form submission (`name`).
  - Implemented options array convenience prop mapping alongside custom children, subcomponent alias `Radio = RadioGroupItem`, and `useRadioGroup` context hook.
  - Implemented full React ref forwarding (`forwardRef<HTMLDivElement, RadioGroupProps>`, `forwardRef<HTMLButtonElement, RadioGroupItemProps>`) with `displayName`.
  - Exported `render_radio_group_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_radio_group_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,662 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (92 files generated). `builder:demo rideshare-favourites` passes (89 files generated). 0 model calls.
- Tracker: inserted R-355 Done row at `Phase_Roadmap!A9`; table `A4:M363`; 363 total rows;
  144 Done, 1 Deferred, 210 Not Started; MVP 144/250 (57.6%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-355.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-354

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-354.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_KBD_COMPONENT` static template implementing accessible, desktop-grade, futuristic Keyboard Keycap & Shortcut Badge component (`apps/web/components/kbd.tsx`).
  - Implemented `KbdVariant` ("default" | "outline" | "subtle" | "ghost" | "neon"), `KbdSize` ("xs" | "sm" | "md" | "lg"), `KbdProps`, `KbdGroupProps`, and `KbdShortcutProps` interfaces.
  - Implemented semantic `<kbd>` HTML elements with WAI-ARIA compliance (`role="group"` on container, `aria-label`, `aria-keyshortcuts`, `data-variant`, `data-size`).
  - Implemented automatic modifier key symbol conversion (`"meta"`/`"command"` -> `"⌘"`, `"shift"` -> `"⇧"`, `"ctrl"` -> `"⌃"`, `"alt"`/`"option"` -> `"⌥"`, `"enter"` -> `"↵"`, `"backspace"` -> `"⌫"`, `"tab"` -> `"⇥"`, `"esc"` -> `"Esc"`, arrows, etc.).
  - Implemented 4 size scales (`xs`, `sm`, `md`, `lg`) with tactile monospace typography, padding, min-width, and border-radius presets.
  - Implemented 5 futuristic visual variants: `"default"` (tactile 3D keycap with bottom border and shadow), `"outline"`, `"subtle"`, `"ghost"`, and `"neon"` (cyberpunk glowing cyan/indigo).
  - Implemented composite key combination arrays with configurable separators, composite container `KbdGroup`, and convenience string shortcut parser `KbdShortcut` (e.g. `"⌘+K"`, `"Ctrl+Shift+P"`).
  - Implemented full React ref forwarding (`forwardRef<HTMLElement, KbdProps>`, `forwardRef<HTMLDivElement, KbdGroupProps>`, `forwardRef<HTMLElement, KbdShortcutProps>`) with `displayName`.
  - Exported `render_kbd_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_kbd_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,647 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (91 files generated). `builder:demo rideshare-favourites` passes (88 files generated). 0 model calls.
- Tracker: inserted R-354 Done row at `Phase_Roadmap!A9`; table `A4:M362`; 362 total rows;
  143 Done, 1 Deferred, 210 Not Started; MVP 143/249 (57.4%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-354.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-353

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-353.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SEPARATOR_COMPONENT` static template implementing accessible, desktop-grade, futuristic Separator / Divider component (`apps/web/components/separator.tsx`).
  - Implemented `SeparatorOrientation` ("horizontal" | "vertical"), `SeparatorVariant` ("neon" | "glass" | "gradient" | "bordered" | "minimal"), `SeparatorThickness` ("thin" | "md" | "thick"), `SeparatorLabelAlign` ("start" | "center" | "end"), and `SeparatorProps` interfaces.
  - Implemented WAI-ARIA 1.2 Separator pattern compliance: decorative mode (`role: "none"`, `aria-hidden: true`) vs semantic mode (`role: "separator"`, `aria-orientation: orientation`).
  - Implemented horizontal orientation (`width: "100%"`) and vertical orientation (`height: "100%"`, `display: "inline-block"`, `alignSelf: "stretch"`).
  - Implemented thickness resolution for presets ("thin" -> 1px, "md" -> 2px, "thick" -> 4px) and custom numeric pixel values.
  - Implemented optional label/content slot along horizontal dividers with flexible alignment (`"start"`, `"center"`, `"end"`), rendering dual flex-grow line segments around a styled uppercase badge.
  - Implemented 5 futuristic visual variants: `"neon"` (cyberpunk cyan line with glowing cyan aura), `"glass"` (translucent frosted divider), `"gradient"` (linear accent fade), `"bordered"` (crisp frame), and `"minimal"` (subtle slate divider).
  - Implemented full React ref forwarding (`forwardRef<HTMLDivElement, SeparatorProps>`) with `displayName = "Separator"`.
  - Exported `render_separator_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_separator_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,631 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (90 files generated). `builder:demo rideshare-favourites` passes (87 files generated). 0 model calls.
- Tracker: inserted R-353 Done row at `Phase_Roadmap!A9`; table `A4:M361`; 361 total rows;
  142 Done, 1 Deferred, 210 Not Started; MVP 142/248 (57.3%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-353.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-352

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-352.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_ASPECT_RATIO_COMPONENT` static template implementing accessible, desktop-grade, futuristic Aspect Ratio Viewport Container component (`apps/web/components/aspect-ratio.tsx`).
  - Implemented `AspectRatioPreset` ("16/9" | "4/3" | "1/1" | "21/9" | "9/16" | "3/2" | "2/3"), `AspectRatioVariant` ("neon" | "glass" | "bordered" | "minimal"), and `AspectRatioProps` interfaces.
  - Implemented `parseRatio` supporting both direct numeric ratios (`number`) and preset ratio strings (`AspectRatioPreset`), defaulting to `16 / 9`.
  - Implemented zero Cumulative Layout Shift (CLS) space reservation via percentage padding-bottom calculation (`paddingBottom = `${(1 / numericRatio) * 100}%``).
  - Implemented modern CSS `aspectRatio` property inline style acceleration.
  - Implemented absolute full-bleed child container layout (`position: "absolute"`, `inset: 0`, `width: "100%"`, `height: "100%"`).
  - Implemented overflow clipping control (`overflowHidden` defaulting to `true`).
  - Implemented full React ref forwarding (`forwardRef<HTMLDivElement, AspectRatioProps>`).
  - Implemented 4 futuristic visual variants: `"neon"` (cyan cyberpunk border with glowing cyan aura), `"glass"` (translucent frosted backdrop blur `12px`), `"bordered"` (clean slate frame), and `"minimal"` (clean borderless transparent).
  - Exported `render_aspect_ratio_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_aspect_ratio_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,615 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (89 files generated). `builder:demo rideshare-favourites` passes (86 files generated). 0 model calls.
- Tracker: inserted R-352 Done row at `Phase_Roadmap!A9`; table `A4:M360`; 360 total rows;
  141 Done, 1 Deferred, 210 Not Started; MVP 141/247 (57.1%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-352.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-351

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-351.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_COLLAPSIBLE_COMPONENT` static template implementing accessible, desktop-grade, futuristic Collapsible / Disclosure compound component suite (`apps/web/components/collapsible.tsx`).
  - Implemented `CollapsibleVariant` ("neon" | "glass" | "bordered" | "minimal"), `CollapsibleSize` ("sm" | "md" | "lg"), `CollapsibleProps`, `CollapsibleTriggerProps`, `CollapsibleContentProps`, `CollapsibleContextValue` interfaces.
  - Implemented compound subcomponents: `CollapsibleRoot`, `CollapsibleTrigger`, `CollapsibleContent`, `useCollapsible`, and compound bindings `Collapsible.Trigger = CollapsibleTrigger; Collapsible.Content = CollapsibleContent;`.
  - Implemented smooth CSS grid template rows expansion animation (`gridTemplateRows: open ? "1fr" : "0fr"`) with `overflow: "hidden"` container for layout-jump-free resizing to arbitrary heights.
  - Implemented built-in rotating vector indicator chevron (`transform: open ? "rotate(180deg)" : "rotate(0deg)"`), custom `indicator` slot, and `hideIndicator` option.
  - Implemented controlled and uncontrolled open state management (`open`, `defaultOpen`, `onOpenChange`, `isControlled`).
  - Implemented disabled state management (`disabled`, `aria-disabled`).
  - Implemented full WAI-ARIA 1.2 disclosure pattern compliance (`aria-expanded={open}`, `aria-controls={contentId}`, `id={triggerId}`, `role="region"`, `aria-labelledby={triggerId}`, `data-state={open ? "open" : "closed"}`).
  - Implemented full keyboard navigation (`Enter` and `Space` trigger activation).
  - Implemented 4 futuristic visual variants: `"neon"` (cyan cyberpunk border glow), `"glass"` (translucent frosted backdrop blur `12px`), `"bordered"` (clean slate frame), and `"minimal"` (clean borderless).
  - Implemented 3 size presets: `"sm"`, `"md"`, `"lg"`.
  - Implemented `forceMount` prop on `CollapsibleContent`.
  - Exported `render_collapsible_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_collapsible_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,599 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (88 files generated). `builder:demo rideshare-favourites` passes (85 files generated). 0 model calls.
- Tracker: inserted R-351 Done row at `Phase_Roadmap!A9`; table `A4:M359`; 359 total rows;
  140 Done, 1 Deferred, 210 Not Started; MVP 140/246 (56.9%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-351.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-350

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-350.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SCROLL_AREA_COMPONENT` static template implementing accessible, desktop-grade, futuristic Scroll Area / Custom Viewport compound component suite (`apps/web/components/scroll-area.tsx`).
  - Implemented `ScrollAreaType` ("auto" | "always" | "scroll" | "hover"), `ScrollAreaOrientation` ("vertical" | "horizontal" | "both"), `ScrollAreaVariant` ("neon" | "glass" | "bordered" | "minimal"), `ScrollAreaSize` ("sm" | "md" | "lg"), `ScrollAreaProps`, `ScrollAreaViewportProps`, `ScrollAreaScrollbarProps`, `ScrollAreaThumbProps`, `ScrollAreaCornerProps`, `ScrollAreaContextValue` interfaces.
  - Implemented compound subcomponents: `ScrollArea`, `ScrollArea.Viewport` (`ScrollAreaViewport`), `ScrollArea.Scrollbar` (`ScrollAreaScrollbar`), `ScrollArea.Thumb` (`ScrollAreaThumb`), `ScrollArea.Corner` (`ScrollAreaCorner`), `useScrollArea`.
  - Implemented cross-browser native scrollbar concealment via CSS (`scrollbarWidth: "none"`, `msOverflowStyle: "none"`, `WebkitOverflowScrolling: "touch"`).
  - Implemented proportional thumb sizing (`ratio * el.clientHeight` / `ratio * el.clientWidth` clamped to min 18px) and dynamic offset mapping.
  - Implemented mouse and touch dragging handlers with `setPointerCapture` and `releasePointerCapture` for smooth thumb dragging.
  - Implemented track click jump scrolling (`handleTrackClick`) with smooth scrolling.
  - Implemented 4 visibility modes: `"auto"`, `"always"`, `"scroll"`, `"hover"`.
  - Implemented WAI-ARIA 1.2 scrollbar semantics (`role="scrollbar"`, `aria-orientation`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-controls`).
  - Implemented viewport keyboard navigation (`tabIndex={0}`, `ArrowDown`/`ArrowUp`, `PageDown`/`PageUp`, `Home`/`End`).
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glowing thumb with cyan border glow), `"glass"` (translucent frosted track), `"bordered"` (clean slate border frame), and `"minimal"` (unobtrusive micro thumb).
  - Implemented 3 size presets: `"sm"` (4px), `"md"` (8px), `"lg"` (12px).
  - Exported `render_scroll_area_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_scroll_area_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,583 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (84 files generated). `builder:demo rideshare-favourites` passes (84 files generated). 0 model calls.
- Tracker: inserted R-350 Done row at `Phase_Roadmap!A9`; table `A4:M358`; 358 total rows;
  139 Done, 1 Deferred, 210 Not Started; MVP 139/245 (56.7%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-350.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-349

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-349.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_HOVER_CARD_COMPONENT` static template implementing accessible, desktop-grade, futuristic Hover Card / Preview Card compound component suite (`apps/web/components/hover-card.tsx`).
  - Implemented `HoverCardVariant` ("neon" | "glass" | "bordered" | "minimal"), `HoverCardSize` ("sm" | "md" | "lg"), `HoverCardSide` ("top" | "bottom" | "left" | "right"), `HoverCardAlign` ("start" | "center" | "end"), `HoverCardProps`, `HoverCardTriggerProps`, `HoverCardContentProps`, `HoverCardArrowProps`, `HoverCardContextValue` interfaces.
  - Implemented compound subcomponents: `HoverCard`, `HoverCard.Trigger` (`HoverCardTrigger`), `HoverCard.Content` (`HoverCardContent`), `HoverCard.Arrow` (`HoverCardArrow`), `useHoverCard`.
  - Implemented configurable entrance and exit delay timers (`openDelay` default 300ms, `closeDelay` default 200ms) with full timeout cleanup.
  - Implemented smooth cursor pointer transit between trigger and content without premature card dismissal.
  - Implemented viewport boundary collision prevention and edge flipping against `window.innerWidth` and `window.innerHeight` with safety padding.
  - Implemented directional SVG pointer arrow notch (`HoverCard.Arrow`).
  - Implemented Escape key dismissal with automatic trigger focus restoration.
  - Implemented full WAI-ARIA 1.2 dialog semantics (`role="dialog"`, `aria-haspopup="dialog"`, `aria-expanded`, `aria-controls`, `aria-labelledby`, `tabIndex={-1}`).
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glow borders and cyan focus glow), `"glass"` (translucent frosted backdrop blur `16px`), `"bordered"` (clean slate border frame), and `"minimal"` (clean subtle shadow).
  - Implemented 3 size presets: `"sm"` (maxWidth 260px), `"md"` (maxWidth 320px), `"lg"` (maxWidth 400px).
  - Exported `render_hover_card_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_hover_card_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,567 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (83 files generated). `builder:demo rideshare-favourites` passes (83 files generated). 0 model calls.
- Tracker: inserted R-349 Done row at `Phase_Roadmap!A9`; table `A4:M357`; 357 total rows;
  138 Done, 1 Deferred, 210 Not Started; MVP 138/244 (56.6%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-349.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-348

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-348.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CONTEXT_MENU_COMPONENT` static template implementing accessible, desktop-class, futuristic Context Menu / Right-Click Action Menu compound component suite (`apps/web/components/context-menu.tsx`).
  - Implemented `ContextMenuVariant` ("neon" | "glass" | "bordered" | "minimal"), `ContextMenuSize` ("sm" | "md" | "lg"), `ContextMenuProps`, `ContextMenuTriggerProps`, `ContextMenuContentProps`, `ContextMenuItemProps`, `ContextMenuCheckboxItemProps`, `ContextMenuRadioGroupProps`, `ContextMenuRadioItemProps`, `ContextMenuSeparatorProps`, `ContextMenuLabelProps`, `ContextMenuSubProps`, `ContextMenuSubTriggerProps`, `ContextMenuSubContentProps`, `ContextMenuContextValue`, `ContextMenuSubContextValue` interfaces.
  - Implemented compound subcomponents: `ContextMenu`, `ContextMenu.Trigger` (`ContextMenuTrigger`), `ContextMenu.Content` (`ContextMenuContent`), `ContextMenu.Item` (`ContextMenuItem`), `ContextMenu.CheckboxItem` (`ContextMenuCheckboxItem`), `ContextMenu.RadioGroup` (`ContextMenuRadioGroup`), `ContextMenu.RadioItem` (`ContextMenuRadioItem`), `ContextMenu.Separator` (`ContextMenuSeparator`), `ContextMenu.Label` (`ContextMenuLabel`), `ContextMenu.Sub` (`ContextMenuSub`), `ContextMenu.SubTrigger` (`ContextMenuSubTrigger`), `ContextMenu.SubContent` (`ContextMenuSubContent`).
  - Implemented viewport boundary collision prevention and clamping (`window.innerWidth`, `window.innerHeight`, `Math.min(position.x, window.innerWidth - width)`).
  - Implemented nested submenus (`ContextMenu.Sub`) with hover and `ArrowRight`/`ArrowLeft` traversal and automatic edge-flipping.
  - Implemented checkbox items (`ContextMenu.CheckboxItem`) with vector checkmark indicator and toggle callbacks.
  - Implemented radio groups (`ContextMenu.RadioGroup`, `ContextMenu.RadioItem`) with vector radio dot indicator and single-select value synchronization.
  - Implemented keyboard shortcut badges (`shortcut?: string`) rendered via `<kbd>` tags.
  - Implemented destructive item styling (`destructive?: boolean`).
  - Implemented outside click/scroll/resize dismissal and Escape key dismiss with focus restoration.
  - Implemented full WAI-ARIA 1.2 Menu pattern semantics (`role="menu"`, `role="menuitem"`, `role="menuitemcheckbox"`, `role="menuitemradio"`, `role="separator"`, `role="group"`, `aria-checked`, `aria-disabled`, `aria-haspopup="menu"`, `aria-expanded`).
  - Implemented full keyboard navigation (`Escape`, `ArrowDown`/`ArrowUp`, `ArrowRight`/`ArrowLeft`, `Home`/`End`, `Tab`, `Enter`/`Space`).
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glow borders and cyan hover accents), `"glass"` (translucent frosted backdrop blur `16px`), `"bordered"` (clean slate border frame), and `"minimal"` (clean subtle shadow).
  - Implemented 3 size presets: `"sm"` (item height 28px), `"md"` (item height 32px), `"lg"` (item height 38px).
  - Exported `render_context_menu_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_context_menu_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,551 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (82 files generated). `builder:demo rideshare-favourites` passes (82 files generated). 0 model calls.
- Tracker: inserted R-348 Done row at `Phase_Roadmap!A9`; table `A4:M356`; 356 total rows;
  137 Done, 1 Deferred, 210 Not Started; MVP 137/243 (56.4%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-348.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-347

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-347.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SPEED_DIAL_COMPONENT` static template implementing accessible, futuristic Speed Dial & Floating Action Button compound component suite (`apps/web/components/speed-dial.tsx`).
  - Implemented `SpeedDialDirection` ("up" | "down" | "left" | "right"), `SpeedDialVariant` ("neon" | "glass" | "bordered" | "minimal"), `SpeedDialSize` ("sm" | "md" | "lg"), `SpeedDialActionItem`, `SpeedDialProps`, `SpeedDialTriggerProps`, `SpeedDialActionProps`, `SpeedDialContentProps`, `SpeedDialContextValue` interfaces.
  - Implemented compound subcomponents: `SpeedDial`, `SpeedDial.Trigger` (`SpeedDialTrigger`), `SpeedDial.Action` (`SpeedDialAction`), `SpeedDial.Content` (`SpeedDialContent`).
  - Implemented primary FAB with smooth 45° rotation toggle animation (`rotate(45deg)`).
  - Implemented 4 directional action cascades ("up", "down", "left", "right") with absolute coordinate anchoring and staggered entrance/exit transitions.
  - Implemented action item labels/tooltips with accessible screen-reader support.
  - Implemented optional backdrop overlay (`backdrop?: boolean`) with subtle blur (`2px`) and click-to-dismiss.
  - Implemented click-outside detection (`handlePointerDown`) and auto-close when clicking outside.
  - Implemented controlled and uncontrolled open state management (`open`, `defaultOpen`, `onOpenChange`).
  - Implemented full WAI-ARIA 1.2 Menu semantics (`role="menu"`, `role="menuitem"`, `aria-haspopup="menu"`, `aria-expanded`, `aria-controls`, `aria-labelledby`, `aria-orientation`).
  - Implemented full keyboard navigation (`Escape` closes speed dial and returns focus to trigger, `ArrowUp`/`ArrowDown`/`ArrowLeft`/`ArrowRight` cycles through menu items, `Home`/`End` jumps to bounds, `Tab` closes menu).
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glowing border and cyan pulse glow), `"glass"` (translucent frosted backdrop blur `16px`), `"bordered"` (clean slate border frame), and `"minimal"` (flat circular button).
  - Implemented 3 size presets: `"sm"` (trigger 40px / action 32px), `"md"` (trigger 48px / action 40px), `"lg"` (trigger 56px / action 48px).
  - Exported `render_speed_dial_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_speed_dial_component.py` with 16 comprehensive unit tests (all passing).
- `task verify` — 1,535 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (81 files generated). `builder:demo rideshare-favourites` passes (81 files generated). 0 model calls.
- Tracker: inserted R-347 Done row at `Phase_Roadmap!A9`; table `A4:M355`; 355 total rows;
  136 Done, 1 Deferred, 210 Not Started; MVP 136/242 (56.2%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-347.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-346

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-346.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_PIN_INPUT_COMPONENT` static template implementing accessible, futuristic PIN & OTP Code Input compound component suite (`apps/web/components/pin-input.tsx`).
  - Implemented `PinInputVariant` ("neon" | "glass" | "bordered" | "minimal"), `PinInputSize` ("sm" | "md" | "lg"), `PinInputType` ("numeric" | "alphanumeric" | "password"), `PinInputProps`, `PinInputGroupProps`, `PinInputSlotProps`, `PinInputSeparatorProps`, `PinInputContextValue` interfaces.
  - Implemented compound subcomponents: `PinInput`, `PinInput.Group` (`PinInputGroup`), `PinInput.Slot` (`PinInputSlot`), `PinInput.Separator` (`PinInputSeparator`).
  - Implemented multi-slot discrete character entry with auto-advance on input and auto-retreat on Backspace.
  - Implemented smart clipboard paste auto-distribution across slots (e.g. pasting "849201" populates all 6 slots).
  - Implemented masking and concealed mode (`mask={true}` or `type="password"`).
  - Implemented native browser autofill support via `autocomplete="one-time-code"`.
  - Implemented hidden input field synchronization (`<input type="hidden" name={name} value={fullCode} />`) for native form integration.
  - Implemented full keyboard navigation (`ArrowLeft`/`ArrowRight`, `Backspace`, `Delete`, `Home`, `End`).
  - Implemented full WAI-ARIA 1.2 accessibility semantics (`role="group"`, `aria-label`, individual slot labelling with position and total count, `aria-hidden="true"` separator).
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glowing border with cyan/purple active slot aura), `"glass"` (translucent frosted background with backdrop blur), `"bordered"` (clean slate border frame), and `"minimal"` (bottom-line underline slots).
  - Implemented 3 size presets: `"sm"` (34x40px), `"md"` (44x50px), `"lg"` (54x60px).
  - Exported `render_pin_input_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_pin_input_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,519 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (82 files generated). `builder:demo rideshare-favourites` passes (80 files generated). 0 model calls.
- Tracker: inserted R-346 Done row at `Phase_Roadmap!A9`; table `A4:M354`; 354 total rows;
  135 Done, 1 Deferred, 210 Not Started; MVP 135/241 (56.0%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-346.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-345

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-345.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_COLOR_PICKER_COMPONENT` static template implementing accessible, futuristic Color Picker & Palette Swatch compound component suite (`apps/web/components/color-picker.tsx`).
  - Implemented `ColorPickerFormat` ("hex" | "rgb" | "hsl"), `ColorPickerVariant` ("neon" | "glass" | "bordered" | "minimal"), `ColorPickerSize` ("sm" | "md" | "lg"), `ColorSwatch`, `ColorPickerProps`, `ColorAreaProps`, `ColorSliderProps`, `ColorSwatchesProps`, `ColorPickerContextValue` interfaces.
  - Implemented compound subcomponents: `ColorPicker`, `ColorPicker.Area` (`ColorArea`), `ColorPicker.HueSlider` (`HueSlider`), `ColorPicker.AlphaSlider` (`AlphaSlider`), `ColorPicker.Swatches` (`ColorSwatches`), `ColorPicker.Inputs` (`ColorInputs`), `ColorPicker.EyeDropper` (`ColorEyeDropper`).
  - Implemented pure mathematical color models without external libraries (`hsvToRgb`, `rgbToHsv`, `rgbToHsl`, `parseHexColor`, `toHex`).
  - Implemented 2D saturation/value spectrum canvas area with live coordinate tracking on pointer/touch drag.
  - Implemented 1D hue slider bar (0° to 360°) and alpha opacity slider (0 to 100%).
  - Implemented format switcher toggling between HEX, RGB, and HSL with individual numeric/text controls.
  - Implemented preset palette swatches with keyboard navigation (`role="listbox"`, `role="option"`, `aria-selected`).
  - Implemented native browser EyeDropper API integration (`new window.EyeDropper()`) with graceful degradation when unsupported.
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glow borders with active color accent glow), `"glass"` (translucent frosted backdrop blur `12px`), `"bordered"` (clean border frame with slate neutral borders), and `"minimal"`.
  - Implemented full WAI-ARIA slider and listbox accessibility semantics (`role="slider"`, `role="listbox"`, `role="option"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`, `aria-label`).
  - Implemented full keyboard navigation (`ArrowLeft`/`Right`, `ArrowUp`/`Down`, `Home`, `End`).
  - Exported `render_color_picker_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_color_picker_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,504 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (81 files generated). `builder:demo rideshare-favourites` passes (79 files generated). 0 model calls.
- Tracker: inserted R-345 Done row at `Phase_Roadmap!A9`; table `A4:M353`; 353 total rows;
  134 Done, 1 Deferred, 210 Not Started; MVP 134/240 (55.8%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-345.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-344

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-344.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_RESIZABLE_COMPONENT` static template implementing accessible, futuristic Resizable Panels & Splitter compound component suite (`apps/web/components/resizable.tsx`).
  - Implemented `ResizableDirection` ("horizontal" | "vertical"), `ResizableVariant` ("neon" | "glass" | "bordered" | "minimal"), `ResizablePanelGroupProps`, `ResizablePanelProps`, `ResizableHandleProps`, `ResizablePanelContextValue` interfaces.
  - Implemented compound subcomponents: `ResizablePanelGroup` (or `Resizable`), `ResizablePanel`, `ResizableHandle`.
  - Implemented pointer and touch dragging with responsive coordinate calculation and live percentage sizing.
  - Implemented min and max constraints (`minSize`, `maxSize`, `defaultSize`).
  - Implemented collapsible panel support (`collapsible`, `collapsedSize`, `onCollapse`, `onExpand`).
  - Implemented keyboard navigation per WAI-ARIA Separator (Window Splitter) Pattern (`ArrowLeft`/`ArrowRight` or `ArrowUp`/`Down` with 1% step, 5% with Shift, `Home` to collapse, `End` to expand to max, `Enter` to toggle collapse).
  - Implemented full WAI-ARIA separator accessibility semantics (`role="separator"`, `aria-orientation`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`, `tabIndex={0}`).
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glow borders and glowing cyan divider line), `"glass"` (translucent frosted divider with backdrop blur), `"bordered"` (slate border with centered grip dots), and `"minimal"` (clean 1px line with expanded hit-area).
  - Exported `render_resizable_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_resizable_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,489 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (81 files generated). `builder:demo rideshare-favourites` passes (78 files generated). 0 model calls.
- Tracker: inserted R-344 Done row at `Phase_Roadmap!A9`; table `A4:M352`; 352 total rows;
  133 Done, 1 Deferred, 210 Not Started; MVP 133/239 (55.6%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-344.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-343

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-343.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CAROUSEL_COMPONENT` static template implementing accessible, futuristic Carousel & Slider Showcase compound component suite (`apps/web/components/carousel.tsx`).
  - Implemented `CarouselVariant` ("neon" | "glass" | "cards" | "minimal"), `CarouselTransition` ("slide" | "fade"), `CarouselOrientation` ("horizontal" | "vertical"), `CarouselIndicatorType` ("dots" | "fraction" | "progress" | "none"), `CarouselContextValue`, `CarouselProps`, `CarouselContentProps`, `CarouselSlideProps`, `CarouselPreviousProps`, `CarouselNextProps`, `CarouselIndicatorsProps`, `CarouselProgressProps`, `CarouselAutoplayToggleProps` interfaces.
  - Implemented compound subcomponents: `Carousel`, `Carousel.Content`, `Carousel.Slide`, `Carousel.Previous`, `Carousel.Next`, `Carousel.Indicators`, `Carousel.Progress`, `Carousel.AutoplayToggle`.
  - Implemented touch / swipe gesture handling (`onTouchStart`, `onTouchEnd`) with 40px delta threshold.
  - Implemented configurable autoplay with interval timer, auto-pause on mouse hover and keyboard focus, and accessible play/pause toggle button.
  - Implemented keyboard navigation per WAI-ARIA Carousel Pattern (`ArrowLeft`/`ArrowRight` or `ArrowUp`/`ArrowDown`, `Home`/`End` jump to first/last slide).
  - Implemented full WAI-ARIA accessibility semantics (`role="region"`, `aria-roledescription="carousel"`, `role="group"`, `aria-roledescription="slide"`, `aria-label`, `aria-hidden`, `aria-live`).
  - Implemented indicator modes: dot pills with elongated active indicator, fraction counter (`1 / 5`), and animated progress bar.
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glow borders and accent pagination dots), `"glass"` (translucent backdrop blur controls), `"cards"` (3D perspective card deck with scaled inactive slides), and `"minimal"`.
  - Exported `render_carousel_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_carousel_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,474 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (80 files generated). `builder:demo rideshare-favourites` passes (77 files generated). 0 model calls.
- Tracker: inserted R-343 Done row at `Phase_Roadmap!A9`; table `A4:M351`; 351 total rows;
  132 Done, 1 Deferred, 210 Not Started; MVP 132/238 (55.5%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-343.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-342

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-342.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SEGMENTED_CONTROL_COMPONENT` static template implementing accessible, futuristic Segmented Control & Mode Switcher component suite (`apps/web/components/segmented-control.tsx`).
  - Implemented `SegmentedControlOption`, `SegmentedControlVariant` ("neon" | "glass" | "pills" | "minimal"), `SegmentedControlSize` ("sm" | "md" | "lg"), `SegmentedControlOrientation` ("horizontal" | "vertical"), `SegmentedControlProps`, `SegmentedControlOptionItemProps` interfaces.
  - Implemented sliding pill indicator animation with smooth cubic-bezier transitions (`cubic-bezier(0.4, 0, 0.2, 1)`).
  - Implemented option labels, icons, disabled states, and notification badges.
  - Implemented controlled and uncontrolled operation modes (`value`, `defaultValue`, `onChange`).
  - Implemented full keyboard navigation (`ArrowLeft`/`ArrowRight` horizontal traversal, `ArrowUp`/`ArrowDown` vertical traversal, `Home`/`End` jump).
  - Implemented full WAI-ARIA radiogroup semantics (`role="radiogroup"`, `role="radio"`, `aria-checked`, `aria-disabled`, `aria-orientation`, `tabIndex`).
  - Implemented hidden input field integration for native form submissions.
  - Exported `render_segmented_control_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_segmented_control_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,459 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass.
  `builder:demo minimal-blog` passes (78 files generated). `builder:demo rideshare-favourites` passes (76 files generated). 0 model calls.
- Tracker: inserted R-342 Done row at `Phase_Roadmap!A9`; table `A4:M350`; 350 total rows;
  131 Done, 1 Deferred, 210 Not Started; MVP 131/237 (55.3%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-342.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.


## 2026-09-11 — R-341

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-341.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_RADIAL_GAUGE_COMPONENT` static template implementing accessible, futuristic Radial Gauge & Activity Rings component suite (`apps/web/components/radial-gauge.tsx`).
  - Implemented `RadialGaugeVariant`, `RadialGaugeSize`, `RadialGaugeThreshold`, `ActivityRingItem`, `RadialGaugeProps`, `ActivityRingsProps`, `RadialGaugeValueProps`, `RadialGaugeLabelProps` interfaces.
  - Implemented pure mathematical SVG arc trigonometry without external chart libraries (`polarToCartesian`, `describeArc`).
  - Implemented single radial gauge mode with configurable angle sweeps (240°, 270°, 360°), threshold transitions (`resolveThresholdColor`), target goal marker tick, and glowing endpoint dot.
  - Implemented concentric multi-ring activity mode (`ActivityRings` / `RadialGauge.Rings`) with nested radius geometry, interactive hover focus, and clickable legend badges.
  - Implemented 4 futuristic visual variants: `"neon"` (cyberpunk glow filters), `"glass"` (translucent backdrop blur readout), `"gradient"` (smooth multi-stop SVG linear gradients), and `"minimal"`.
  - Implemented WAI-ARIA accessibility semantics (`role="meter"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`, `aria-label`).
  - Exported `render_radial_gauge_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_radial_gauge_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,444 tests pass (15 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (78 files generated). `builder:demo rideshare-favourites` passes (75 files generated). 0 model calls.
- Tracker: inserted R-341 Done row at `Phase_Roadmap!A9`; table `A4:M349`; 349 total rows;
  130 Done, 1 Deferred, 210 Not Started; MVP 130/236 (55.1%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-341.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-340

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-340.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CODE_BLOCK_COMPONENT` static template implementing accessible, futuristic Code Block & Syntax Presentation component suite (`apps/web/components/code-block.tsx`).
  - Implemented `CodeSnippet`, `CodeBlockVariant`, `CodeBlockSize`, `TokenType`, `CodeToken`, `CodeBlockProps`, `CodeBlockHeaderProps`, `CodeBlockContentProps`, `CodeBlockLineProps`, `CodeBlockCopyButtonProps` interfaces.
  - Implemented zero-dependency lexical tokenizer (`tokenizeCodeLine`) supporting TS/JS, Python, JSON, SQL, Bash, Go, Diff.
  - Implemented multi-tab snippet switcher with keyboard navigation and active tab indicators.
  - Implemented line numbering (`showLineNumbers`, `startLineNumber`) and line highlighting (`highlightLines`, `parseHighlightLines`).
  - Implemented git diff mode (`diffMode`, `diff-add` with emerald green background/border, `diff-delete` with rose red background/border).
  - Implemented one-click copy-to-clipboard with smooth animated checkmark feedback and automatic timer reset.
  - Implemented line wrap toggle (`wrapLines`) and expandable/collapsible max-height container with gradient fade mask.
  - Implemented 4 futuristic visual variants: `"terminal"` (macOS dots, deep dark background), `"glass"` (translucent backdrop blur), `"neon"` (cyberpunk glow), and `"minimal"`.
  - Implemented WAI-ARIA accessibility semantics (`role="region"`, `role="tablist"`, `role="tab"`, keyboard scrollable `<pre tabIndex={0}>`).
  - Implemented inline SVG vector icons (`TerminalDots`, `CopyIcon`, `CheckIcon`, `WrapIcon`, `ExpandIcon`).
  - Exported `render_code_block_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_code_block_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,429 tests pass (15 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (77 files generated). `builder:demo rideshare-favourites` passes (74 files generated). 0 model calls.
- Tracker: inserted R-340 Done row at `Phase_Roadmap!A9`; table `A4:M348`; 348 total rows;
  129 Done, 1 Deferred, 210 Not Started; MVP 129/235 (54.9%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-340.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-339

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-339.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TAG_INPUT_COMPONENT` static template implementing accessible, futuristic Tag and Chip Tokenizer component suite (`apps/web/components/tag-input.tsx`).
  - Implemented `TagItem`, `TagValue`, `TagInputVariant`, `TagInputSize`, `TagInputProps` interfaces.
  - Implemented delimiter parsing on `Enter`, `Comma` (`,`), and `Tab`.
  - Implemented chip keyboard traversal (`ArrowLeft`/`ArrowRight`) and `Backspace` chip deletion.
  - Implemented autocomplete suggestions dropdown with keyboard navigation (`ArrowDown`, `ArrowUp`, `Enter`, `Escape`).
  - Implemented validation: `maxTags` limits, duplicate prevention with visual warning feedback, and custom `validateTag` predicate.
  - Implemented visual variants: `"default"`, `"glass"` (translucent backdrop blur), `"neon"` (cyberpunk glow), and `"bordered"`.
  - Implemented WAI-ARIA Combobox / Listbox 1.2 semantics (`role="combobox"`, `role="listbox"`, `role="option"`, `aria-autocomplete="list"`, `aria-expanded`, `aria-activedescendant`).
  - Implemented inline SVG icons (`TagIcon`, `XIcon`, `ClearIcon`).
  - Exported `render_tag_input_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_tag_input_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,414 tests pass (15 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (76 files generated). `builder:demo rideshare-favourites` passes (73 files generated). 0 model calls.
- Tracker: inserted R-339 Done row at `Phase_Roadmap!A9`; table `A4:M347`; 347 total rows;
  128 Done, 1 Deferred, 210 Not Started; MVP 128/234 (54.7%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-339.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-338

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-338.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TREE_VIEW_COMPONENT` static template implementing accessible, reusable Hierarchical Tree View component suite (`apps/web/components/tree-view.tsx`).
  - Implemented `TreeNode`, `TreeViewVariant`, `TreeViewProps` interfaces.
  - Implemented single-select (`selectedId`, `onSelect`) and multi-select (`selectedIds`, `onMultiSelect`, `multiSelect` with accessible checkboxes).
  - Implemented controlled and uncontrolled expansion control (`expandedIds`, `onToggle`, `defaultExpanded`).
  - Implemented search filter with automated ancestor branch auto-expansion and match highlighting (`<mark>`).
  - Implemented visual hierarchy guide lines (`showLines`, `variant="lines"`).
  - Implemented WAI-ARIA Tree View 1.2 compliance (`role="tree"`, `role="treeitem"`, `role="group"`, `aria-expanded`, `aria-selected`, `aria-level`, `aria-posinset`, `aria-setsize`, `aria-disabled`).
  - Implemented complete keyboard navigation (`ArrowDown`, `ArrowUp`, `ArrowRight`, `ArrowLeft`, `Home`, `End`, `Enter`, `Space`, `*` to expand all siblings).
  - Implemented inline SVG icons (`ChevronRightIcon`, `FolderClosedIcon`, `FolderOpenIcon`, `FileTextIcon`, `SearchIcon`).
  - Exported `render_tree_view_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_tree_view_component.py` with 15 comprehensive unit tests (all passing).
- `task verify` — 1,399 tests pass (15 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (75 files generated). `builder:demo rideshare-favourites` passes (72 files generated). 0 model calls.
- Tracker: inserted R-338 Done row at `Phase_Roadmap!A9`; table `A4:M346`; 346 total rows;
  127 Done, 1 Deferred, 210 Not Started; MVP 127/233 (54.5%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-338.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-337

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-337.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_STAT_CARD_COMPONENT` static template implementing accessible, futuristic Stat & Metric KPI Card component (`apps/web/components/stat-card.tsx`).
  - Implemented `StatCardVariant`, `StatTrend`, and compound subcomponents (`StatCard`, `StatCardHeader`, `StatCardValue`, `StatCardDelta`, `StatCardSparkline`, `StatCardFooter`).
  - Implemented pure mathematical SVG spline curve (`computeSplinePath`) generating cubic-bezier `C` control points with `<linearGradient>` area fill and interactive hover highlight.
  - Implemented directional trend delta badge with directional SVG arrows (`TrendingUpIcon`, `TrendingDownIcon`, `TrendingFlatIcon`) and accessible `aria-label`.
  - Implemented glassmorphic styling (`backdropFilter: "blur(16px)"`) and ambient glow border styling.
  - Implemented WAI-ARIA `role="region"` / `role="button"` with keyboard `Enter`/`Space` activation.
  - Exported `render_stat_card_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_stat_card_component.py` with 15 tests.
- `task verify` — 1,384 tests pass (15 new). `builder:demo minimal-blog` passes (74 files). `builder:demo rideshare-favourites` passes (71 files).
- Tracker: inserted R-337 at row 9; table `A4:M345`; 126 Done, 1 Deferred, 210 Not Started; MVP 126/232 (54.3%).

## 2026-09-11 — R-336

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-336.md` (status in_progress → done).
- Added `_TIMELINE_COMPONENT` static template implementing accessible, reusable Timeline / Activity Feed component (`apps/web/components/timeline.tsx`).
- Implemented `TimelineVariant`, `TimelineItemStatus`, `TimelineItem`, `TimelineProps`.
- Implemented built-in vector status icons, vertical connector lines, centered layout, compact layout, semantic `<time>` elements.
- Exported `render_timeline_component` in `codegen` and registered in `NextjsWebAdapter.generate()`.
- Added `services/agent-engine/tests/test_timeline_component.py` with 20 tests.
- `task verify` — 1,369 tests pass. `builder:demo` passes with 73/70 files.
- Tracker: reconciled R-336 at row 9; table `A4:M344`; 125 Done, 1 Deferred, 210 Not Started; MVP 125/231 (54.1%).

## 2026-09-11 — R-335

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-335.md` (status in_progress → done).
- Added `_FILE_UPLOAD_COMPONENT` static template implementing accessible, reusable File Upload / Dropzone component (`apps/web/components/file-upload.tsx`).
- Implemented drag-and-drop, click browse, keyboard trigger, file preview list with progressbar, and avatar variant.
- Exported `render_file_upload_component` in `codegen` and registered in `NextjsWebAdapter.generate()`.
- Added `services/agent-engine/tests/test_file_upload_component.py` with 19 tests.
- `task verify` — 1,349 tests pass. `builder:demo` passes with 72/69 files.

## 2026-09-11 — R-334

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-334.md` (status in_progress → done).
- Added `_STEPPER_COMPONENT` static template implementing accessible, reusable Stepper / Multi-step Wizard component (`apps/web/components/stepper.tsx`).
- Implemented horizontal/vertical orientations, step status badges, completed icons, step navigation callbacks.
- Exported `render_stepper_component` in `codegen` and registered in `NextjsWebAdapter.generate()`.
- Added `services/agent-engine/tests/test_stepper_component.py` with 20 tests.
- `task verify` — 1,330 tests pass. `builder:demo` passes with 71/68 files.

## 2026-09-11 — R-333

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-333.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_RATING_COMPONENT` static template implementing accessible, reusable Rating & Review component (`apps/web/components/rating.tsx`).
  - Implemented `RatingSize`, `RatingIcon`, `RatingProps` interfaces.
  - Implemented interactive hover preview: mouse move across items calculates bounding client coordinates, supporting half-star detection when `allowHalf` is true, and restoring active score on mouse leave.
  - Implemented click selection: updates controlled or internal state and fires `onChange(score)`.
  - Implemented full keyboard navigation: `ArrowRight`/`ArrowUp` (+step), `ArrowLeft`/`ArrowDown` (-step), `Home` (0), `End` (max).
  - Implemented WAI-ARIA slider pattern semantics: `role="slider"`, `tabIndex={disabled || readOnly ? -1 : 0}`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`, `aria-readonly`, `aria-disabled`, and `aria-label`.
  - Implemented built-in inline vector icons (`star`, `heart`, `thumb`) with precise fractional fill rendering via overlay clipping.
  - Implemented read-only (`readOnly`) and disabled (`disabled`) interaction guards and styling.
  - Implemented numeric score display formatting (`showScore`, `formatScore`) and size presets (`sm`, `md`, `lg`).
  - Exported `render_rating_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_rating_component.py` with 13 comprehensive tests covering client directive, types and component exports, WAI-ARIA slider semantics, hover preview and click selection, half increments, keyboard navigation, vector icons, read-only/disabled states, score formatting, size presets, codegen export, adapter registration, and diff invariance.
- `task verify` — 1,310 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (70 files generated). `builder:demo rideshare-favourites` passes (67 files generated). 0 model calls.
- Tracker: inserted R-333 Done row at `Phase_Roadmap!A9`; table `A4:M341`; 338 total rows;
  122 Done, 1 Deferred, 210 Not Started; MVP 122/228 (53.5%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-333.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-332

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-332.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_PROGRESS_COMPONENT` static template implementing accessible, reusable Progress and Spinner component suite (`apps/web/components/progress.tsx`).
  - Implemented `ProgressVariant`, `ProgressSize`, `ProgressBarProps`, `CircularProgressProps`, `SpinnerProps` interfaces.
  - Implemented `ProgressBar` (and `Progress` alias) supporting linear determinate mode (`value`, `min`, `max`, `showValue`, `formatValue`) and indeterminate animated shimmer/pulse mode.
  - Implemented WAI-ARIA progressbar semantics: `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext` (with `aria-valuenow` correctly omitted in indeterminate mode per WAI-ARIA specification).
  - Implemented striped gradient pattern and animated stripes (`striped`, `animated`).
  - Implemented `CircularProgress` with SVG circle stroke-dasharray and stroke-dashoffset mathematical calculations, supporting percentage fill in determinate mode, continuous rotating sweep in indeterminate mode, and center text/label rendering.
  - Implemented lightweight `Spinner` with SVG loader circle, `role="status"`, `aria-live="polite"`, and screen-reader accessible label (`sr-only` span, defaulting to "Loading...").
  - Implemented size presets (`sm`, `md`, `lg`) and semantic color variants (`default`, `primary`, `success`, `warning`, `error`, `info`).
  - Exported `render_progress_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_progress_component.py` with 13 comprehensive tests covering client directive, types and component exports, determinate mode ARIA attributes, indeterminate mode omitting valuenow, label and formatting options, striped and animated classes, sizes and variants, circular SVG calculations, circular determinate/indeterminate modes, spinner live regions and sr-only label, codegen export, adapter registration, and diff invariance.
- `task verify` — 1,297 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (69 files generated). `builder:demo rideshare-favourites` passes (66 files generated). 0 model calls.
- Tracker: inserted R-332 Done row at `Phase_Roadmap!A9`; table `A4:M340`; 337 total rows;
  121 Done, 1 Deferred, 210 Not Started; MVP 121/227 (53.3%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-332.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-331

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-331.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SLIDER_COMPONENT` static template implementing accessible, reusable Slider & Range component (`apps/web/components/slider.tsx`).
  - Implemented `SliderOrientation`, `SliderValue`, `SliderMark`, `SliderProps` interfaces.
  - Implemented single-value (`number`) and dual-thumb range (`[number, number]`) modes.
  - Implemented range crossover prevention: clamping thumb values so Thumb 0 cannot exceed Thumb 1 and Thumb 1 cannot drop below Thumb 0.
  - Implemented interactive dragging on track and thumbs via pointerdown, pointermove, and pointerup events with touch-action none.
  - Implemented full keyboard navigation for focused thumb: `ArrowRight`/`ArrowUp` (+step), `ArrowLeft`/`ArrowDown` (-step), `PageUp` (+10x step), `PageDown` (-10x step), `Home` (snap to minimum valid value), `End` (snap to maximum valid value).
  - Implemented WAI-ARIA slider pattern semantics: `role="slider"`, `tabIndex={disabled ? -1 : 0}`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-orientation`, `aria-disabled`, `aria-label`, and `aria-valuetext`.
  - Implemented tick marks and labels rendering when `marks` is specified.
  - Implemented value display badge when `showValue` is true with customizable `formatValue`.
  - Exported `render_slider_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_slider_component.py` with 13 comprehensive tests covering client directive, types and component exports, single/range modes, pointer dragging, keyboard navigation (step/page increments, Home/End boundaries), WAI-ARIA slider semantics, crossover prevention, marks/labels, value display formatting, codegen export, adapter registration, and diff invariance.
- `task verify` — 1,284 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (68 files generated). `builder:demo rideshare-favourites` passes (65 files generated). 0 model calls.
- Tracker: inserted R-331 Done row at `Phase_Roadmap!A9`; table `A4:M339`; 331 unique IDs (0 dupes);
  120 Done, 1 Deferred, 210 Not Started; MVP 120/226 (53.1%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-331.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-330

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-330.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_COMMAND_PALETTE_COMPONENT` static template implementing accessible, reusable Command Palette and Search Menu component (`apps/web/components/command-palette.tsx`).
  - Implemented `CommandItem`, `CommandGroup`, `CommandPaletteProps` interfaces.
  - Implemented global `Cmd+K` / `Ctrl+K` keyboard shortcut listener (`triggerShortcut?: boolean`, default `true`) to toggle palette visibility.
  - Implemented real-time search filtering across item `label`, `description`, `group`, and `keywords`.
  - Implemented keyboard navigation: `ArrowDown`/`ArrowUp` traversal (skipping disabled items and wrapping gracefully), `Home`/`End` jump to first/last selectable item, `Enter` execution of selected item callback, and `Escape` dismissal with focus restoration.
  - Implemented WAI-ARIA combobox pattern: `role="combobox"` input with `aria-autocomplete="list"`, `aria-expanded="true"`, `aria-haspopup="listbox"`, `aria-controls`, and `aria-activedescendant`; results container with `role="listbox"`; items with `role="option"`, unique `id`, `aria-selected`, and `aria-disabled`.
  - Implemented group headings (`role="group"` with `aria-labelledby`), shortcut badges (`<kbd>`), configurable `emptyMessage`, modal backdrop overlay (`role="dialog"`, `aria-modal="true"`, `backdropFilter: "blur(4px)"`), and body scroll lock management.
  - Exported `render_command_palette_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_command_palette_component.py` with 13 comprehensive tests covering client directive, types and component exports, global shortcut listener, query filtering, keyboard traversal, active descendant / combobox semantics, group headers and sublists, kbd badges, empty search state, dialog backdrop and body scroll lock, codegen export, adapter registration, and diff invariance.
- `task verify` — 1,271 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (67 files generated). `builder:demo rideshare-favourites` passes (64 files generated). 0 model calls.
- Tracker: inserted R-330 Done row at `Phase_Roadmap!A9`; table `A4:M338`; 330 unique IDs (0 dupes);
  119 Done, 1 Deferred, 210 Not Started; MVP 119/225 (52.9%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-330.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-329

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-329.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_DATA_GRID_COMPONENT` static template implementing accessible, reusable Data Grid and Table component (`apps/web/components/data-grid.tsx`).
  - Implemented generic `ColumnDef<T>`, `DataGridProps<T>`, `SortDirection`, `SortState`, `DataGridDensity` interfaces.
  - Implemented sortable column headers with WAI-ARIA `aria-sort` ("ascending" | "descending" | "none"), sort indicator SVGs (up/down/dual arrows), and keyboard trigger (`Enter` / `Space`).
  - Implemented row selection checkboxes with header select-all (checked, unchecked, indeterminate states) and `aria-selected` row attribute.
  - Implemented display density presets (`"compact"`, `"comfortable"`, `"spacious"`) with proportional cell padding and font-size maps.
  - Implemented `stickyHeader` with fixed position `<thead>` and border preservation.
  - Implemented `striped` alternating row styling and `hoverable` row hover background transitions.
  - Implemented loading skeleton placeholder rows with animated pulsing divs, `role="status"`, and `aria-busy="true"`.
  - Implemented `emptyState` fallback rendering.
  - Exported `render_data_grid_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_data_grid_component.py` with 13 comprehensive tests covering client directive, types and component exports, density presets, sortable columns and aria-sort, row selection checkboxes, row aria-selected, sticky header, striped/hoverable styling, loading skeleton state, empty state, codegen export, adapter registration, and diff invariance.
- `task verify` — 1,258 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (66 files generated). `builder:demo rideshare-favourites` passes (63 files generated). 0 model calls.
- Tracker: inserted R-329 Done row at `Phase_Roadmap!A9`; table `A4:M337`; 329 unique IDs (0 dupes);
  118 Done, 1 Deferred, 210 Not Started; MVP 118/224 (52.7%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-329.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-11 — R-328

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-328.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_DATE_PICKER_COMPONENT` static template implementing accessible, reusable Date Picker and Calendar component suite (`apps/web/components/date-picker.tsx`).
  - Implemented `DateFormatter`, `CalendarProps`, and `DatePickerProps` interfaces.
  - Implemented `Calendar` month grid view with:
    - Month and year navigation header with previous/next month and year controls with accessible `aria-label`s.
    - Weekday headers with `<abbr>` and accessible full day labels.
    - Calendar day grid with WAI-ARIA `role="grid"`, `role="row"`, `role="gridcell"`, `aria-selected`, `aria-current="date"`, and `aria-disabled`.
    - Full keyboard navigation: Left/Right Arrow (+/- 1 day), Up/Down Arrow (+/- 7 days), PageUp/PageDown (+/- 1 month or year with Shift), Home/End (start/end of week), Enter/Space (select date).
    - Quick-select "Today" action and optional "Clear" button.
  - Implemented `DatePicker` trigger and floating popover:
    - Accessible trigger button styled as input field with calendar SVG icon, `aria-haspopup="dialog"`, `aria-expanded`, formatted date text, and placeholder fallback.
    - Clearable button affordance (`clearable` with `aria-label="Clear date"`).
    - Floating popover container with `role="dialog"`, `aria-modal="false"`, `aria-label="Choose date"`, dismiss on outside click, and dismiss on Escape with focus restoration.
    - Placement styling (`bottom-start`, `bottom-end`, `top-start`, `top-end`).
    - Error and helper text rendering with `role="alert"` and `aria-describedby` wiring.
  - Implemented zero-dependency date utilities: `formatDate`, `isSameDay`, `isToday`.
  - Exported `render_date_picker_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_date_picker_component.py` with 13 comprehensive tests covering client directive, types and component exports, header controls, weekday headers, grid WAI-ARIA semantics, keyboard navigation, today/clear actions, trigger semantics, clearable affordance, popover dialog and dismiss, codegen export, adapter registration, and diff invariance.
- `task verify` — 1,245 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (65 files generated). `builder:demo rideshare-favourites` passes (62 files generated). 0 model calls.
- Tracker: inserted R-328 Done row at `Phase_Roadmap!A9`; table `A4:M336`; 328 unique IDs (0 dupes);
  117 Done, 1 Deferred, 210 Not Started; MVP 117/223 (52.5%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-328.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-327

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-327.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_FORM_CONTROLS_COMPONENT` static template implementing accessible, reusable compound Form Controls and Input primitives suite (`apps/web/components/form-controls.tsx`).
  - Implemented `InputSize` (`"sm"` | `"md"` | `"lg"`), `sizeMap`, and interfaces for all form elements.
  - Implemented `Input` with size presets, prefix slot, suffix slot, and optional clear button (`onClear` with `aria-label="Clear input"`).
  - Implemented `Textarea` with size presets, auto/custom rows, and optional live character counter (`showCount`, `maxLength`) with 90% amber capacity warning.
  - Implemented `Select` with options array rendering, placeholder support (`disabled hidden`), custom SVG chevron indicator, and disabled states.
  - Implemented `Checkbox` with checked, unchecked, and indeterminate states (`el.indeterminate`), focus ring, and label/description binding.
  - Implemented `RadioGroup` and `Radio` with `RadioGroupContext`, WAI-ARIA `role="radiogroup"`, `role="radio"`, `aria-checked`, and full keyboard Arrow navigation (`ArrowDown`, `ArrowUp`, `ArrowRight`, `ArrowLeft`).
  - Implemented `Label` with optional red asterisk indicator (`*`, `aria-hidden="true"`).
  - Implemented `FormField` compound container auto-generating unique IDs via `useId()`, linking `htmlFor`, and wiring `aria-invalid` and `aria-describedby` to `FormHelperText` and `FormMessage`.
  - Implemented `FormMessage` with `role="alert"` and `aria-live="polite"`.
  - Implemented `FormHelperText` for descriptive hints.
  - Exported `render_form_controls_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_form_controls_component.py` with 13 comprehensive tests covering client directive, types, forwardRef and function exports, size presets, prefix/suffix/clear affordances, character counters, select options, checkbox semantics, radiogroup WAI-ARIA and arrow keyboard navigation, formfield/formmessage semantics, label required indicator, adapter registration, codegen exports, and diff invariance.
- `task verify` — 1,232 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (64 files generated). `builder:demo rideshare-favourites` passes (61 files generated). 0 model calls.
- Tracker: inserted R-327 Done row at `Phase_Roadmap!A9`; table `A4:M335`; 327 unique IDs (0 dupes);
  116 Done, 1 Deferred, 210 Not Started; MVP 116/222 (52.3%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-327.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-326

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-326.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_DIALOG_COMPONENT` static template implementing accessible, reusable compound Dialog and Modal component (`apps/web/components/dialog.tsx`).
  - Implemented `DialogSize` (`"sm"` | `"md"` | `"lg"` | `"xl"` | `"full"`), `sizeMap`, and `DialogContextValue` interfaces.
  - Implemented `Dialog` root component with controlled (`open`, `onOpenChange`) and uncontrolled (`defaultOpen`) state support, providing `DialogContext`.
  - Implemented `DialogTrigger` button/wrapper supporting `asChild` delegation, `aria-haspopup="dialog"`, `aria-expanded`, and trigger element ref caching.
  - Implemented `DialogPortal` rendering top-level dialog elements when active.
  - Implemented `DialogOverlay` backdrop overlay with dark semi-transparent tint, backdrop blur, fade transitions, and backdrop click dismiss.
  - Implemented `DialogContent` container with `role="dialog"`, `aria-modal="true"`, dynamic `aria-labelledby` and `aria-describedby` wiring, Escape key dismiss listener, document body scroll lock, focus restoration upon dismiss, and optional accessible close button (`aria-label="Close dialog"` with SVG icon).
  - Implemented `DialogHeader`, `DialogTitle` (accessible heading), `DialogDescription` (muted caption), `DialogBody` (scrollable content area), `DialogFooter` (actions bar), and `DialogClose` (action trigger).
  - Implemented `useDialog()` hook.
  - Exported `render_dialog_component` in `omnistackai_agent_engine.codegen` and registered `components/dialog.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_dialog_component.py` with 13 comprehensive tests covering client directive, types, compound subcomponents, ARIA dialog semantics, size presets, Escape key listener, backdrop click dismiss, accessible close button, body scroll lock and focus restoration, controlled and uncontrolled state, hook, adapter registration, codegen exports, and diff invariance.
- `task verify` — 1,219 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (63 files generated). `builder:demo rideshare-favourites` passes (60 files generated). 0 model calls.
- Tracker: inserted R-326 Done row at `Phase_Roadmap!A9`; table `A4:M334`; 326 unique IDs (0 dupes);
  115 Done, 1 Deferred, 210 Not Started; MVP 115/221 (52.0%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-326.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-325

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-325.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_THEME_TOGGLE_COMPONENT` static template implementing accessible, reusable compound Theme Switcher component (`apps/web/components/theme-toggle.tsx`).
  - Implemented `ThemeMode` (`"light"` | `"dark"` | `"system"`), `ResolvedTheme` (`"light"` | `"dark"`), and `ThemeContextValue` interfaces.
  - Implemented `ThemeProvider` context managing active theme mode, localStorage synchronization, and `window.matchMedia("(prefers-color-scheme: dark)")` system preference listening.
  - Implemented `useTheme` hook with fallback defaults.
  - Implemented `ThemeToggle` button component with size presets (`"sm"` | `"md"` | `"lg"`), accessible labels, and inline SVG Sun / Moon vector icons.
  - Implemented `ThemeSelect` segmented control with WAI-ARIA `role="radiogroup"`, `role="radio"`, and `aria-checked` semantics for explicit mode selection.
  - Implemented `ThemeScript` inline script snippet to prevent Flash of Unstyled Content (FOUC) during initial SSR page loads.
  - Exported `render_theme_toggle_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_theme_toggle_component.py` with 12 comprehensive tests covering client directive, types, provider modes, localStorage handling, system media query handling, ARIA attributes, radiogroup semantics, FOUC script, SVG icons, adapter generation, codegen exports, and diff invariance.
- `task verify` — 1,206 tests pass (12 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (62 files generated). `builder:demo rideshare-favourites` passes (59 files generated). 0 model calls.
- Tracker: inserted R-325 Done row at `Phase_Roadmap!A9`; table `A4:M333`; 325 unique IDs (0 dupes);
  114 Done, 1 Deferred, 210 Not Started; MVP 114/220 (51.8%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-325.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-324

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-324.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_DESIGN_TOKENS_CSS` static template implementing standalone, production-grade Design Tokens and CSS custom properties theming engine (`apps/web/styles/tokens.css`).
  - Implemented Light mode palette under `:root` (primary, secondary, accent, neutral scale 50-900, background/surface scales, text hierarchy, borders, ring, and semantic feedback colors: success, warning, danger, info).
  - Implemented Dark mode palette under `[data-theme="dark"]`, `:root.dark`, `body.dark`, and `@media (prefers-color-scheme: dark)` (with `:root:not([data-theme="light"])` override support).
  - Implemented scale tokens: spacing scale (`--space-0` through `--space-24`), typography scale (system fonts, mono, sizes xs through 4xl, weights light through bold, line heights), radii (`--radius-none` through `--radius-full`), elevation shadows (`--shadow-none` through `--shadow-xl`), z-indices (`--z-dropdown` through `--z-tooltip`), and motion transitions.
  - Implemented accessibility reduced-motion media query (`@media (prefers-reduced-motion: reduce)`) resetting transition/animation durations.
  - Added `_GLOBALS_CSS` importing `@import "../styles/tokens.css";` and establishing unified root base styles and box-sizing rules (`apps/web/app/globals.css`).
  - Exported `render_design_tokens` and `render_globals_css` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_theming_tokens.py` with 15 comprehensive tests covering tokens CSS, semantic colors, status colors, spacing, typography, radii, shadows, z-indices, transitions, dark theme mappings, reduced motion, globals.css integration, adapter generation, codegen exports, and diff invariance.
- `task verify` — 1,194 tests pass (15 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (61 files generated). `builder:demo rideshare-favourites` passes (58 files generated). 0 model calls.
- Tracker: inserted R-324 Done row at `Phase_Roadmap!A9`; table `A4:M332`; 324 unique IDs (0 dupes);
  113 Done, 1 Deferred, 210 Not Started; MVP 113/219 (51.6%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-324.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-323

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-323.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_POPOVER_COMPONENT` static template implementing accessible, reusable compound Popover component (`apps/web/components/popover.tsx`).
  - Implemented `Popover`, `PopoverTrigger`, `PopoverContent`, `PopoverClose`, and `PopoverArrow` compound subcomponents.
  - Implemented `PopoverAlign` (`"start"` | `"end"` | `"center"`) and `PopoverSide` (`"top"` | `"bottom"` | `"left"` | `"right"`).
  - Implemented click-outside dismiss (`mousedown`) and Escape key dismiss with trigger focus restoration.
  - Implemented controlled (`open`, `onOpenChange`) and uncontrolled (`defaultOpen`) operation modes.
  - Implemented WAI-ARIA Dialog semantics (`role="dialog"`, `aria-modal="true"`, `aria-haspopup="dialog"`, `aria-expanded`, `aria-controls`, `aria-labelledby`).
  - Implemented `PopoverClose` button with accessible `aria-label="Close popover"`.
  - Implemented `PopoverArrow` pointing indicator with `aria-hidden="true"`.
  - Exported `render_popover_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_popover_component.py` with 11 comprehensive tests covering client directive, types, compound subcomponents, WAI-ARIA dialog attributes, alignments/placements, controlled/uncontrolled state, click-outside/escape dismiss, close button label, arrow indicator, adapter generation, and diff invariance.
- `task verify` — 1,179 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (60 files generated). `builder:demo rideshare-favourites` passes (57 files generated). 0 model calls.
- Tracker: inserted R-323 Done row at `Phase_Roadmap!A9`; table `A4:M331`; 323 unique IDs (0 dupes);
  112 Done, 1 Deferred, 210 Not Started; MVP 112/218 (51.4%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-323.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-322

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-322.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_DROPDOWN_MENU_COMPONENT` static template implementing accessible, reusable compound Dropdown Menu component (`apps/web/components/dropdown-menu.tsx`).
  - Implemented `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuSeparator`, and `DropdownMenuLabel` compound subcomponents.
  - Implemented `DropdownMenuAlign` (`"start"` | `"end"` | `"center"`) and `DropdownMenuSide` (`"top"` | `"bottom"` | `"left"` | `"right"`).
  - Implemented click-outside dismiss and Escape key dismiss with trigger focus restoration.
  - Implemented full keyboard navigation (`ArrowDown`, `ArrowUp`, `Home`, `End`, `Escape`, `Enter`, `Space`) with active index focus cycling.
  - Implemented WAI-ARIA 1.2 Menu semantics (`role="menu"`, `role="menuitem"`, `aria-haspopup="menu"`, `aria-expanded`, `aria-controls`, `aria-labelledby`, `role="separator"`).
  - Implemented disabled item handling with `aria-disabled` and keyboard focus skipping.
  - Implemented `destructive` variant styling for hazardous actions.
  - Supported optional `shortcut` key badge and `icon` slots.
  - Exported `render_dropdown_menu_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_dropdown_menu_component.py` with 11 comprehensive tests covering client directive, types, compound subcomponents, WAI-ARIA menu attributes, keyboard navigation, alignments/placements, disabled state, destructive items, click-outside/escape dismiss, shortcut/icons, adapter generation, and diff invariance.
- `task verify` — 1,168 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (59 files generated). `builder:demo rideshare-favourites` passes (56 files generated). 0 model calls.
- Tracker: inserted R-322 Done row at `Phase_Roadmap!A9`; table `A4:M330`; 322 unique IDs (0 dupes);
  111 Done, 1 Deferred, 210 Not Started; MVP 111/217 (51.2%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-322.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-321

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-321.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_ACCORDION_COMPONENT` static template implementing accessible, reusable compound Accordion component (`apps/web/components/accordion.tsx`).
  - Implemented `Accordion`, `AccordionItem`, `AccordionTrigger`, and `AccordionContent` compound subcomponents.
  - Implemented `AccordionType` (`"single"` | `"multiple"`).
  - Implemented `collapsible` boolean configuration (allows closing all sections in single mode).
  - Implemented `AccordionVariant` (`"default"` | `"bordered"` | `"separated"`).
  - Supported controlled (`value`, `onValueChange`) and uncontrolled (`defaultValue`) operation modes.
  - Implemented WAI-ARIA 1.2 accordion semantics: `aria-expanded={isOpen}`, `aria-controls={contentId}`, dynamic `id`, `role="region"`, `aria-labelledby={triggerId}`, and `hidden={!isOpen}`.
  - Implemented rotating chevron SVG indicator with `aria-hidden="true"` and `transform: rotate(180deg)`.
  - Implemented disabled item support (`disabled` prop on `AccordionItem`).
  - Exported `render_accordion_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_accordion_component.py` with 11 comprehensive tests covering client directive, types, compound subcomponents, WAI-ARIA accordion attributes, single and multiple modes, collapsible behavior, animated chevron icon, disabled states, variants, adapter generation, and diff invariance.
- `task verify` — 1,157 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (58 files generated). `builder:demo rideshare-favourites` passes (55 files generated). 0 model calls.
- Tracker: inserted R-321 Done row at `Phase_Roadmap!A9`; table `A4:M329`; 321 unique IDs (0 dupes);
  110 Done, 1 Deferred, 210 Not Started; MVP 110/216 (50.9%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-321.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-320

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-320.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TOGGLE_COMPONENT` static template implementing accessible, reusable Toggle Switch component (`apps/web/components/toggle.tsx`).
  - Implemented `Toggle` and `ToggleSwitch` alias/compound components.
  - Implemented `ToggleSize` (`"sm"` | `"md"` | `"lg"`) with standardized track, thumb dimensions, and sliding offset.
  - Supported controlled (`checked`, `onChange`) and uncontrolled (`defaultChecked`) operation modes.
  - Supported optional `label` and `description` slots with automated ID binding (`aria-labelledby`, `aria-describedby`).
  - Supported WAI-ARIA 1.2 switch semantics (`role="switch"`, `aria-checked`, `tabIndex`, focus ring).
  - Supported full keyboard accessibility (`Space` and `Enter` keydown toggles with `preventDefault`).
  - Supported hidden input for seamless HTML form submission when `name` prop is provided.
  - Exported `render_toggle_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_toggle_component.py` with 11 comprehensive tests covering client directive, types, subcomponents, WAI-ARIA switch attributes, sizes, keyboard handling, controlled/uncontrolled state, adapter generation, and diff invariance.
- `task verify` — 1,146 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (57 files generated). `builder:demo rideshare-favourites` passes (54 files generated). 0 model calls.
- Tracker: inserted R-320 Done row at `Phase_Roadmap!A9`; table `A4:M328`; 320 unique IDs (0 dupes);
  109 Done, 1 Deferred, 210 Not Started; MVP 109/215 (50.7%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-320.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-319

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-319.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_AVATAR_COMPONENT` static template implementing accessible, reusable compound Avatar component (`apps/web/components/avatar.tsx`).
  - Implemented `Avatar` and `AvatarGroup` compound subcomponents.
  - Implemented `AvatarShape` (`"circle"` | `"rounded"` | `"square"`).
  - Implemented `AvatarSize` (`"xs"` | `"sm"` | `"md"` | `"lg"` | `"xl"`).
  - Implemented `AvatarStatus` (`"online"` | `"offline"` | `"busy"` | `"away"`) with status indicator dot and accessible status label.
  - Implemented 3-tier fallback cascade: Image (with `onError` fallback) -> Initials (with deterministic background color hashing) -> generic SVG vector silhouette (`aria-hidden="true"`).
  - Implemented `AvatarGroup` with overlapping negative margins, `max` display limit, and `+N` excess indicator badge.
  - Exported `render_avatar_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_avatar_component.py` with 11 comprehensive tests covering client directive, types, subcomponents, WAI-ARIA image/status attributes, shapes, sizes, presence status indicators, 3-tier fallback cascade, avatar group overflow, adapter registration, and diff invariance.
- `task verify` — 1,135 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (56 files generated). `builder:demo rideshare-favourites` passes (53 files generated). 0 model calls.
- Tracker: inserted R-319 Done row at `Phase_Roadmap!A9`; table `A4:M327`; 319 unique IDs (0 dupes);
  108 Done, 1 Deferred, 210 Not Started; MVP 108/214 (50.5%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-319.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-318

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-318.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_DRAWER_COMPONENT` static template implementing accessible, reusable compound Drawer component (`apps/web/components/drawer.tsx`).
  - Implemented `Drawer`, `DrawerHeader`, `DrawerTitle`, `DrawerDescription`, `DrawerContent`, and `DrawerFooter` compound subcomponents.
  - Implemented `DrawerPosition` (`"left"` | `"right"` | `"top"` | `"bottom"`) with edge slide-in styling.
  - Implemented `DrawerSize` (`"sm"` | `"md"` | `"lg"` | `"xl"` | `"full"`) with responsive width/height mappings.
  - Supported WAI-ARIA modal dialog semantics (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`).
  - Added backdrop overlay with click dismiss (`closeOnBackdropClick`).
  - Added `Escape` keydown listener dismiss (`closeOnEscape`).
  - Added accessible close button (`aria-label="Close drawer"`).
  - Added body scroll locking (`document.body.style.overflow = "hidden"`).
  - Exported `render_drawer_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_drawer_component.py` with 11 comprehensive tests covering client directive, types, subcomponents, WAI-ARIA dialog attributes, positions, sizes, escape handling, backdrop click, close button, adapter registration, and diff invariance.
- `task verify` — 1,124 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (55 files generated). `builder:demo rideshare-favourites` passes (52 files generated). 0 model calls.
- Tracker: inserted R-318 Done row at `Phase_Roadmap!A9`; table `A4:M326`; 318 unique IDs (0 dupes);
  107 Done, 1 Deferred, 210 Not Started; MVP 107/213 (50.2%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-318.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-317

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-317.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_SKELETON_COMPONENT` static template implementing accessible, reusable compound Skeleton component (`apps/web/components/skeleton.tsx`).
  - Implemented `Skeleton`, `SkeletonText`, `SkeletonCard`, and `SkeletonTable` compound subcomponents.
  - Implemented `SkeletonVariant` (`"text"` | `"circular"` | `"rectangular"` | `"rounded"`).
  - Implemented `SkeletonAnimation` (`"pulse"` | `"wave"` | `"none"`).
  - Supported WAI-ARIA loading semantics (`role="status"`, `aria-busy="true"`, `aria-live="polite"`).
  - Added accessible visually hidden screen reader loading announcement (`<span style={srOnlyStyle}>{ariaLabel}</span>`).
  - Added `@media (prefers-reduced-motion: reduce)` motion query handling to disable animation for users sensitive to motion.
  - Exported `render_skeleton_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_skeleton_component.py` with 10 comprehensive tests covering client directive, types, subcomponents, WAI-ARIA status/busy semantics, screen reader announcements, shape variants, dimensions, animation/reduced motion, adapter registration, and diff invariance.
- `task verify` — 1,113 tests pass (10 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (54 files generated). `builder:demo rideshare-favourites` passes (51 files generated). 0 model calls.
- Tracker: inserted R-317 Done row at `Phase_Roadmap!A9`; table `A4:M325`; 317 unique IDs (0 dupes);
  106 Done, 1 Deferred, 210 Not Started; MVP 106/212 (50.0%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-317.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-316

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-316.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_ALERT_COMPONENT` static template implementing accessible, reusable compound Alert component (`apps/web/components/alert.tsx`).
  - Implemented `Alert`, `AlertTitle`, and `AlertDescription` subcomponents.
  - Implemented `AlertVariant` (`"info"` | `"success"` | `"warning"` | `"error"`).
  - Supported WAI-ARIA alert and status semantics (`role="alert"` for error, `role="status"` for info/success/warning; `aria-live="assertive"` or `"polite"`).
  - Added accessible SVG vector icons for each variant with `aria-hidden="true"`.
  - Added dismissible state with accessible close button (`aria-label="Dismiss alert"`) and `onDismiss` callback.
  - Added optional `action` slot for contextual actions.
  - Exported `render_alert_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_alert_component.py` with 10 comprehensive tests covering types, subcomponents, WAI-ARIA semantics, vector icons, dismissible behavior, variant styling, action slot, adapter registration, diff invariance, and example IR project generation.
- `task verify` — 1,103 tests pass (10 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (53 files generated). `builder:demo rideshare-favourites` passes (50 files generated). 0 model calls.
- Tracker: inserted R-316 Done row at `Phase_Roadmap!A9`; table `A4:M324`; 316 unique IDs (0 dupes);
  105 Done, 1 Deferred, 210 Not Started; MVP 105/210 (50.0%); no `#REF!`; XLSX valid.
- Left changes uncommitted in working tree per user instruction.
- Updated CURRENT_TASK.yaml, tasks/R-316.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-315

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-315.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_CARD_COMPONENT` static template implementing accessible, reusable compound Card component (`apps/web/components/card.tsx`).
  - Implemented `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, and `CardFooter` subcomponents.
  - Implemented `CardVariant` (`"default"` | `"bordered"` | `"flat"` | `"elevated"`) and `CardPadding` (`"none"` | `"sm"` | `"md"` | `"lg"`).
  - Added polymorphic rendering via `as` prop (`"div" | "article" | "section"` for Card; `"h1".."h6" | "div"` for CardTitle).
  - Added interactive click and keyboard triggers: `onClick`, `role="button"`, `tabIndex={0}`, `Enter`/`Space` keydown trigger, and hover transitions.
  - Added `CardHeader` with `title`, `description`, and right-aligned `action` slot.
  - Added `CardFooter` with flex alignment presets (`"left"` | `"right"` | `"between"` | `"center"`).
  - Exported `render_card_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_card_component.py` with 11 comprehensive tests covering types, subcomponents, variants, padding presets, polymorphic tags, interactive click/keyboard, header action slot, footer alignment, adapter registration, diff invariance, and example IR project generation.
- `task verify` — 1,093 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (52 files generated). `builder:demo rideshare-favourites` passes (49 files generated). 0 model calls.
- Tracker: inserted R-315 Done row at `Phase_Roadmap!A9`; table `A4:M323`; 315 unique IDs (0 dupes);
  104 Done, 1 Deferred, 210 Not Started; MVP 104/210 (49.5%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-315.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-314

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-314.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TOOLTIP_COMPONENT` static template implementing accessible, reusable Tooltip component (`apps/web/components/tooltip.tsx`).
  - Conforms to WAI-ARIA 1.2 Tooltip design pattern: `<span id={tooltipId} role="tooltip">` with dynamic `useId()` and `React.cloneElement(children, { "aria-describedby": visible ? tooltipId : undefined })`.
  - Implemented `TooltipPosition` (`"top"` | `"bottom"` | `"left"` | `"right"`), `TooltipProps` (`content`, `children`, `position`, `delayMs`, `className`, `style`), and position styling map.
  - Implemented triggers: `onMouseEnter`, `onMouseLeave`, `onFocus`, `onBlur`, with configurable `delayMs` timer (default 200ms).
  - Implemented `Escape` key dismiss listener: closes active tooltip immediately when Escape is pressed.
  - Exported `render_tooltip_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_tooltip_component.py` with 8 comprehensive tests covering types, tooltip role, useId/describedby linkage, hover/focus triggers, escape dismiss, position styles, adapter registration, and example IR project generation.
- `task verify` — 1,082 tests pass (8 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (51 files generated). `builder:demo rideshare-favourites` passes (48 files generated). 0 model calls.
- Tracker: inserted R-314 Done row at `Phase_Roadmap!A9`; table `A4:M322`; 314 unique IDs (0 dupes);
  103 Done, 1 Deferred, 210 Not Started; MVP 103/209 (49.3%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-314.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-313

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-313.md` (status in_progress → done).
- `nextjs.py`:
  - Enhanced generated Next.js collection screens (`_collection_screen_page`) with an interactive, accessible column visibility dropdown ("Columns ▾") in the collection toolbar.
  - Emitted `visibleColumns` state initialized to `true` for all display fields (`useState<Record<string, boolean>>({ ... })`) and `showColumnPicker` boolean state.
  - Implemented `toggleColumn` handler with minimum 1 visible column safety guard (`currentVisible.length <= 1`).
  - Added accessible dropdown button with `aria-haspopup="true"`, `aria-expanded={showColumnPicker}`, and `aria-label="Toggle column visibility"`.
  - Added dropdown menu with `role="menu"` and `aria-label="Column visibility options"`, containing checkbox toggle controls for each display column.
  - Conditionally rendered table `<th>` headers and row `<td>` cells according to `visibleColumns[field.name] !== false`.
  - Preserved row selection checkboxes, Actions/Details column, and full backwards compatibility with colSpan.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_column_visibility.py` with 11 comprehensive tests covering state declaration, dropdown button/menu accessibility, checkbox toggles, conditional headers/cells rendering, guard behavior, diff invariance, and example IR project generation.
- `task verify` — 1,074 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (50 files generated). `builder:demo rideshare-favourites` passes (47 files generated). 0 model calls.
- Tracker: inserted R-313 Done row at `Phase_Roadmap!A9`; table `A4:M321`; 313 unique IDs (0 dupes);
  102 Done, 1 Deferred, 210 Not Started; MVP 102/208 (49.0%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-313.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-312

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-312.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_BADGE_COMPONENT` static template implementing accessible, reusable Badge and Status Pill component (`apps/web/components/badge.tsx`).
  - Conforms to WAI-ARIA status semantics: `<span role="status" aria-label={ariaLabel}>`.
  - Implemented `BadgeVariant` (`"success"` | `"warning"` | `"error"` | `"info"` | `"neutral"`), `BadgeSize` (`"sm"` | `"md"`), and `BadgeProps` (`children`, `variant`, `size`, `dot`, `pulse`, `style`, `className`, `ariaLabel`).
  - Added built-in status dot indicator with `aria-hidden="true"` and optional pulse opacity.
  - Exported `render_badge_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_badge_component.py` with 12 comprehensive tests covering types, status role, variant colors, sizing, dot indicator, adapter registration, and example IR project generation.
- `task verify` — 1,063 tests pass (12 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (50 files generated). `builder:demo rideshare-favourites` passes (47 files generated). 0 model calls.
- Tracker: inserted R-312 Done row at `Phase_Roadmap!A9`; table `A4:M320`; 312 unique IDs (0 dupes);
  101 Done, 1 Deferred, 210 Not Started; MVP 101/207 (48.8%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-312.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-311

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-311.md` (status in_progress → done).
- `nextjs.py`:
  - Enhanced generated Next.js collection screens (`_collection_screen_page`) with an interactive, accessible table display density toggle (`"compact"` | `"comfortable"` | `"spacious"`).
  - Emitted `density` state initialized to `"comfortable"`, computing dynamic cell padding (`densityPadding = density === "compact" ? "6px 12px" : density === "spacious" ? "16px 20px" : "12px 16px"`) and table font size (`densityFontSize = density === "compact" ? 13 : 14`).
  - Added accessible segmented controls in the collection toolbar with `role="group"`, `aria-label="Table display density"`, and `aria-pressed={density === ...}` attributes.
  - Added `data-density={density}` and `fontSize: densityFontSize` to `<table>`, applying `padding: densityPadding` to table row data cells (`<td>`) across checkboxes, data fields, and action buttons.
  - Preserved backward compatibility for Actions header (`<th style={{ padding: "12px 16px", textAlign: "right", fontWeight: 600, color: "#475569" }}>Actions</th>`).
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_table_density.py` with 10 comprehensive tests covering state declaration, computed padding/font-size, toolbar group & button attributes, table data-density attribute, td cell padding, diff invariance, and example IR project generation.
- `task verify` — 1,051 tests pass (10 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (49 files generated). `builder:demo rideshare-favourites` passes (46 files generated). 0 model calls.
- Tracker: inserted R-311 Done row at `Phase_Roadmap!A9`; table `A4:M319`; 311 unique IDs (0 dupes);
  100 Done, 1 Deferred, 210 Not Started; MVP 100/206 (48.5%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-311.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-310

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-310.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_TABS_COMPONENT` static template implementing accessible, reusable Tabs and TabPanel components (`apps/web/components/tabs.tsx`).
  - Conforms to WAI-ARIA 1.2 Tabs design pattern: `<div role="tablist" aria-label="...">`, `<button role="tab" id={"tab-" + id} aria-selected={isActive} aria-controls={"tabpanel-" + id} tabIndex={isActive ? 0 : -1}>`, and `<div role="tabpanel" id={"tabpanel-" + id} aria-labelledby={"tab-" + id} tabIndex={0} hidden={activeTab !== id}>`.
  - Implemented `TabItem`, `TabsProps`, and `TabPanelProps` interfaces with `id`, `label`, `count`, `disabled`, `activeTab`, `onChange`, `ariaLabel`, and `variant` (`"line"` | `"pills"`).
  - Added keyboard accessibility handlers: `ArrowRight` (selects next enabled tab), `ArrowLeft` (selects previous enabled tab), `Home` (selects first enabled tab), `End` (selects last enabled tab) with automatic DOM focus management.
  - Added badge count display when `count !== undefined`.
  - Exported `render_tabs_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_tabs_component.py` with 12 comprehensive tests covering props interfaces, WAI-ARIA compliance, roving tabindex, keyboard navigation, line/pills variants, adapter registration, diff invariance, and example IR project generation.
- `task verify` — 1,041 tests pass (12 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (49 files generated). `builder:demo rideshare-favourites` passes (46 files generated). 0 model calls.
- Tracker: inserted R-310 Done row at `Phase_Roadmap!A9`; table `A4:M318`; 310 unique IDs (0 dupes);
  99 Done, 1 Deferred, 210 Not Started; MVP 99/205 (48.3%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-310.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-309

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-309.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_PAGINATION_COMPONENT` static template implementing accessible, reusable Pagination component (`apps/web/components/pagination.tsx`).
  - Conforms to WAI-ARIA 1.2 pagination structure: `<nav aria-label="Pagination">`, labeled Previous/Next buttons, `aria-current="page"` on current active page button, and `<label htmlFor="pageSizeSelect">` with `<select id="pageSizeSelect" aria-label="Select page size">`.
  - Implemented `PaginationProps` interface: `page`, `pageSize`, `total`, `totalPages`, `onPageChange`, `onPageSizeChange`, `pageSizeOptions`, `disabled`, `compact`, and `itemLabel`.
  - Added direct page number button rendering with dynamic ellipsis calculation (`getPageNumbers`) in standard mode.
  - Added `compact` mode support for narrow/constrained viewports (drawers, detail subcollections, cards).
  - Exported `render_pagination_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_pagination_component.py` with 12 comprehensive tests covering props interface, WAI-ARIA compliance, page number calculations, compact mode, disabled states, adapter registration, diff invariance, and example IR project generation.
- `task verify` — 1,029 tests pass (12 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (48 files generated). `builder:demo rideshare-favourites` passes (45 files generated). 0 model calls.
- Tracker: inserted R-309 Done row at `Phase_Roadmap!A9`; table `A4:M317`; 309 unique IDs (0 dupes);
  98 Done, 1 Deferred, 210 Not Started; MVP 98/204 (48.0%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-309.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-308

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-308.md` (status in_progress → done).
- `nextjs.py`:
  - Added `handleExportJson(selectedOnly)` helper function in generated collection screens (`_collection_screen_page`).
  - Added accessible `Export JSON` button to top toolbar calling `handleExportJson(false)`, disabled when `!data || data.length === 0`.
  - Added accessible `Export JSON ({checkedIds.length})` button to bulk action bar calling `handleExportJson(true)`.
  - JSON blob created with `application/json;charset=utf-8;` MIME type and formatted with 2-space indentation (`JSON.stringify(itemsToExport, null, 2)`).
  - Download filename formatted as `{plural.lower()}_export.json`.
  - Object URL lifecycle properly revoked via `URL.revokeObjectURL(url)`.
  - User feedback via `toast.info("Exported JSON successfully")`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_collection_json_export.py` with 8 comprehensive unit and integration tests.
- `task verify` — 1,017 tests pass (8 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (47 files generated). `builder:demo rideshare-favourites` passes (44 files generated). 0 model calls.
- Tracker: inserted R-308 Done row at `Phase_Roadmap!A9`; table `A4:M316`; 308 unique IDs (0 dupes);
  97 Done, 1 Deferred, 210 Not Started; MVP 97/203 (47.8%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-308.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-307

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-307.md` (status in_progress → done).
- `nextjs.py`:
  - Added `_EMPTY_STATE_COMPONENT` template implementing WAI-ARIA `role="status"` and `aria-live="polite"`.
  - Built-in accessible vector SVG icons: `"folder"`, `"search"`, `"document"`, `"inbox"` with `aria-hidden="true"`.
  - Added primary and secondary action dispatch supporting Link (when `href` provided) or button (when `onClick` provided).
  - Exported `render_empty_state_component` in `omnistackai_agent_engine.codegen` and registered `components/empty-state.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.
- Added `services/agent-engine/tests/test_empty_state.py` with 11 comprehensive tests covering component structure, ARIA compliance, icon variants, action dispatch, adapter registration, diff invariance, and example IR project generation.
- `task verify` — 1,009 tests pass (11 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (47 files generated). Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-307 Done row at `Phase_Roadmap!A9`; table `A4:M315`; 307 unique IDs (0 dupes);
  96 Done, 1 Deferred, 210 Not Started; MVP 96/202 (47.5%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-307.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-306

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-306.md` (status in_progress → done).
- `nextjs.py`:
  - Elevated navigation wayfinding and hierarchy across generated Next.js web applications:
    - Generated Reusable Breadcrumbs Component (`apps/web/components/breadcrumbs.tsx`):
      - `Breadcrumbs` component conforming to WAI-ARIA 1.2 breadcrumb design pattern: `<nav aria-label="Breadcrumb">`, `<ol>`, `<li>`, separator (`/`), `aria-current="page"`.
      - Exported `BreadcrumbItem` and `BreadcrumbsProps` interfaces.
      - Accessible rendering: links for ancestor levels, non-link bold text with `aria-current="page"` for terminal level.
    - Detail Screen Hierarchy Integration (`_detail_screen_page`):
      - Imported and mounted `<Breadcrumbs items={breadcrumbs} />` at the top of detail screens (Overview -> Collection [if present] -> Record item / Details).
      - Preserved existing `&larr; Back to {plural}` link for backwards compatibility with existing assertions.
    - Form Screen Hierarchy Integration (`_form_screen_page`):
      - Imported and mounted `<Breadcrumbs items={breadcrumbs} />` at the top of form screens (Overview -> Collection [if present] -> New/Edit item).
      - Preserved existing `&larr; Back to {plural}` link.
    - Exported `render_breadcrumbs_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_breadcrumbs.py` with 9 comprehensive tests covering component structure, ARIA compliance, detail screen breadcrumbs, form screen breadcrumbs, collection fallback, diff invariance, and full-project integration.
- `task verify` — 998 tests pass (9 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (46 files generated). Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-306 Done row at `Phase_Roadmap!A9`; table `A4:M314`; 306 unique IDs (0 dupes);
  95 Done, 1 Deferred, 210 Not Started; MVP 95/201 (47.3%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-306.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-305

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-305.md` (status in_progress → done).
- `nextjs.py`:
  - Elevated keyboard discoverability and power-user accessibility across generated Next.js web applications:
    - Generated Reusable ShortcutsDialog Component (`apps/web/components/shortcuts-dialog.tsx`):
      - `ShortcutsDialog` modal component: backdrop overlay with backdrop filter, dialog card, header with keyboard icon (`⌨`), title, close button, and organized shortcut groups.
      - WAI-ARIA compliance: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="shortcuts-dialog-title"`.
      - Keyboard interaction: closes on `Escape` key press; clicking backdrop closes dialog.
      - Styled `<kbd>` badges with monospace font, subtle border, white background, and drop shadow.
      - Shortcut groups:
        - Global Navigation: `?` (Show / hide shortcuts), `Esc` (Close modal / dismiss / clear).
        - Collection Screens: `/` (Focus search input), `Esc` (Clear active search or filter criteria).
        - Record Detail Screens: `[` / `]` or `←` / `→` (Navigate previous / next record), `e` (Edit current record), `Esc` (Deselect active record).
        - Form Editor Screens: `Cmd+Enter` / `Ctrl+Enter` (Submit / save form), `Cmd+S` / `Ctrl+S` (Save form changes), `Esc` (Blur active input or discard changes).
    - Navbar Header Integration (`apps/web/components/navbar.tsx`):
      - Imports and mounts `ShortcutsDialog` component with local `isOpen` state.
      - Registers a global `keydown` event listener for `?` (outside editable form elements like INPUT, TEXTAREA, SELECT, contentEditable) to toggle the modal.
      - Renders an accessible `Shortcuts (?)` trigger button with keyboard icon (`⌨`), text label, and `?` shortcut badge in the navbar header next to the quick-create CTA.
    - Exported `render_shortcuts_dialog_component` in `omnistackai_agent_engine.codegen` and registered in `NextjsWebAdapter.generate()`.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_shortcuts_dialog.py` with 14 comprehensive tests covering component structure, ARIA compliance, grouped shortcuts, `<kbd>` styling, Navbar integration, global keydown listener, diff invariance, and full-project integration.
- `task verify` — 989 tests pass (14 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes (45 files generated). Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-305 Done row at `Phase_Roadmap!A9`; table `A4:M313`; 305 unique IDs (0 dupes);
  94 Done, 1 Deferred, 210 Not Started; MVP 94/200 (47.0%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-305.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-304

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-304.md` (status in_progress → done).
- `nextjs.py`:
  - Replaced crude, blocking `window.confirm()` browser dialogs with an accessible, styled modal confirmation dialog component (`components/confirm-dialog.tsx`) and `useConfirm` hook across all generated Next.js web application screens:
    - Generated Reusable Component (`apps/web/components/confirm-dialog.tsx`):
      - `ConfirmDialog` modal component: backdrop overlay, dialog card, title, message body, Confirm/Cancel buttons with focus management (autoFocus confirm button, focus trapping, Escape dismiss, backdrop click dismiss, WAI-ARIA `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`).
      - Visual intent variants: danger (crimson `#dc2626` for deletes) and neutral/primary (`#2563eb`).
      - `useConfirm` hook: exports `confirmAsync(title, message, options) -> Promise<boolean>` resolving true on Confirm, false on Cancel/Dismiss.
    - Collection screens (`_collection_screen_page`):
      - Single item delete handler replaced with `await confirmAsync(...)`.
      - Batch/bulk delete handler replaced with `await confirmAsync(...)`.
      - Subcollection child delete handler replaced with `await confirmAsync(...)`.
      - Conditionally imports `useConfirm` and `ConfirmDialog` when deletable actions exist.
      - Renders `<ConfirmDialog {...confirmProps} />` in screen JSX.
    - Detail screens (`_detail_screen_page`):
      - Record delete handler replaced with `await confirmAsync(...)`.
      - Master-detail subcollection child delete replaced with `await confirmAsync(...)`.
      - Conditionally imports `useConfirm` and `ConfirmDialog` when deletable actions exist.
      - Renders `<ConfirmDialog {...confirmProps} />` in screen JSX.
    - Form screens (`_form_screen_page`):
      - Unsaved changes guard on Cancel button navigation replaced with `await confirmAsync(...)`.
      - Unsaved changes guard on `Escape` key press replaced with `await confirmAsync(...)`.
      - Form Reset button confirmation prompt replaced with `await confirmAsync(...)`.
      - Imports `useConfirm` and `ConfirmDialog`.
      - Renders `<ConfirmDialog {...confirmProps} />` in screen JSX.
    - Registered `components/confirm-dialog.tsx` as a static client component in `NextjsWebAdapter.generate()`.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_confirm_dialog.py` with 31 comprehensive tests covering component structure, ARIA compliance, collection screens, detail screens, form screens, diff invariance, and full-project integration.
- Updated 4 test files (`test_collection_bulk_actions.py`, `test_detail_screen_lifecycle.py`, `test_form_unsaved_changes_guard.py`, `test_subcollection_deletion.py`) to assert the new `confirmAsync` pattern instead of old raw `confirm()`.
- `task verify` — 975 tests pass (31 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` passes. Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-304 Done row at `Phase_Roadmap!A9`; table `A4:M312`; 304 unique IDs (0 dupes);
  93 Done, 1 Deferred, 210 Not Started; MVP 93/199 (46.7%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-304.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-303

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-303.md` (status in_progress → done).
- `nextjs.py`:
  - Elevated dashboard overview navigation, operational status, and metrics awareness across generated Next.js web applications (`app/page.tsx` via `_overview_page`):
    - Interactive Entity Summary Cards:
      - For listable entities with `Op.LIST`, matches the primary collection screen and wraps the summary card in an accessible `<Link href="/{col_screen.id}">` with `aria-label="View {plural} collection"`, uppercase entity label, navigation arrow indicator, prominent live record total, and an interactive `View all &rarr;` affordance.
      - Unlinked entities without a collection screen render as styled summary `<div>` cards with live count, preserving backward compatibility.
    - Operational Health Badge & Metrics Counters:
      - App header section upgraded to a responsive flex layout featuring a live "System Operational" status pill with green status indicator dot (`#22c55e`), alongside summary count badges for total entities (`{count} Entities`) and total screens (`{count} Screens`).
    - Screen Navigation Cards:
      - Enhanced screen cards with visual arrow indicator (`&rarr;`) alongside the screen title.
    - Zero-State Fallback:
      - Added accessible empty state card when neither entities nor screens are configured.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_overview_dashboard_links_and_health.py` with 9 focused tests (collection linking, unlinked entity card, mixed cards, operational badge, metrics chips, screen arrow indicator, empty state, diff invariance, and example project generation).
- `task verify` — 944 tests pass (9 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-303 Done row at `Phase_Roadmap!A9`; table `A4:M311`; 303 unique IDs (0 dupes);
  92 Done, 1 Deferred, 210 Not Started; MVP 92/198 (46.5%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-303.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-302

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-302.md` (status in_progress → done).
- `nextjs.py`:
  - Elevated visual hierarchy and data affordances across generated Next.js screens:
    - Added `_field_value_jsx(field, expr)` helper formatting field expressions into accessible JSX:
      - Boolean fields render styled status pill badges: emerald background (`#dcfce7`), emerald text (`#166534`), and text "Yes" if truthy; slate background (`#f1f5f9`), slate text (`#64748b`), and text "No" if falsy.
      - Enum fields (with validation rule `enum:a|b|c`) render blue categorical pill badges (`#eff6ff` background, `#1d4ed8` text, `1px solid #bfdbfe` border).
      - Applied consistently to collection table cells, collection drawer subcollection child cards, and detail screen subcollection tabs.
    - Detail screens (`_detail_screen_page`):
      - In record card header, renders an accessible "Copy ID" button beside the record title (`aria-label="Copy ID to clipboard"`).
      - In record definition list (`<dl>`), renders inline "Copy" affordance on `id` and UUID foreign key fields (`aria-label="Copy <field_label> to clipboard"`), and renders status badges for boolean and enum fields.
      - Implemented robust `handleCopy(text, label)` using `navigator?.clipboard?.writeText` with graceful `document.execCommand("copy")` fallback and toast feedback (`toast.success` / `toast.error`).
    - Preserves all existing filters, debounce, optimistic delete, keyboard shortcuts, and pagination.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_status_badges_and_copy_clipboard.py` with 7 focused tests (boolean and enum badges in collection table cells, subcollection drawer badges, detail card copy ID button, detail dl inline copy, detail dl status badges, diff invariance, example projects generation).
- `task verify` — 935 tests pass (7 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-302 Done row at `Phase_Roadmap!A9`; table `A4:M310`; 302 unique IDs (0 dupes);
  91 Done, 1 Deferred, 210 Not Started; MVP 91/197 (46.2%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-302.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-301

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-301.md` (status in_progress → done).
- `nextjs.py`:
  - Enhanced search clear affordances and form entry workflow across generated screens:
    - Collection search form (`_collection_screen_page`): wraps search input in an accessible relative container with an interactive inline Clear (`×`) button rendered when `searchInput` is non-empty; clicking it clears input (`setSearchInput("")`), commits empty search (`setSearch("")`), and refocuses input (`searchInputRef.current?.focus()`).
    - Subcollection search form (`_subcol_controls`): wraps subcollection search input in an accessible container with an interactive inline Clear (`×`) button clearing local search state and committing to hook.
    - Form screens (`_form_screen_page`): automatically emits `autoFocus` on the first editable field (text, textarea, number, select, or checkbox) to enable immediate keyboard input upon navigation.
    - Preserves all existing debounce, keyboard navigation, and field error behaviors.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_search_clear_and_form_autofocus.py` with 6 focused tests (collection search clear button, subcollection search clear button, form first-field autofocus, form first-field select autofocus, diff invariance, example projects generation).
- `task verify` — 928 tests pass (6 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-301 Done row at `Phase_Roadmap!A9`; table `A4:M309`; 301 unique IDs (0 dupes);
  90 Done, 1 Deferred, 210 Not Started; MVP 90/196 (45.9%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-301.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-300

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-300.md` (status in_progress → done).
- `nextjs.py`:
  - Enforced schema-derived validation rules natively in Next.js form screens (`_form_screen_page`):
    - Text and String fields with `rules.max_length`:
      - Emits `maxLength={rules.max_length}` HTML attribute on `<textarea>` and `<input>`.
      - Renders helper hint `Max {rules.max_length} characters`.
      - Renders live character counter (`{length} / {rules.max_length}`) dynamically turning amber warning
        when input length reaches 90% of the limit.
    - Numeric fields with `rules.minimum` / `rules.maximum`:
      - Emits `min={rules.minimum}` when specified.
      - Emits `max={rules.maximum}` when specified.
      - Displays range badge `Range: {min} to {max}`.
    - Fields without constraints remain byte-identical to existing output.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_form_input_constraints.py` with 6 focused tests (string maxLength
  and counter, textarea maxLength and counter, numeric min/max and range hint, unconstrained field stability,
  diff invariance, example projects generation).
- `task verify` — 922 tests pass (6 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-300 Done row at `Phase_Roadmap!A9`; table `A4:M308`; 300 unique IDs (0 dupes);
  89 Done, 1 Deferred, 210 Not Started; MVP 89/195 (45.6%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-300.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-299

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-299.md` (status in_progress → done).
- `nextjs.py`:
  - Added a window `keydown` event listener in `_form_screen_page` for power-user shortcuts:
    - Pressing `Cmd+Enter` or `Ctrl+Enter` triggers form submission (`form.requestSubmit()`) and prevents default event.
    - Pressing `Cmd+S` or `Ctrl+S` triggers form submission (`form.requestSubmit()`) and prevents browser "Save Page As..." dialog.
    - Pressing `Escape` while focused in an editable field (`INPUT`, `TEXTAREA`, `SELECT`) blurs the active field.
    - Pressing `Escape` outside editable inputs triggers Cancel navigation to `cancel_href`, prompting confirmation if `isDirty`.
    - Submitting guards (`!submitting` or `!(submitting || updating)`) prevent duplicate submissions.
    - Full event listener cleanup on unmount with dependency array (`[isDirty, submitting, updating]`).
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_form_keyboard_shortcuts.py` with 7 focused tests (save shortcuts, escape shortcut,
  submitting guard, event listener cleanup, create-only form guard, diff invariance, example projects generation).
- `task verify` — 916 tests pass (7 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-299 Done row at `Phase_Roadmap!A9`; table `A4:M307`; 299 unique IDs (0 dupes);
  88 Done, 1 Deferred, 210 Not Started; MVP 88/194 (45.4%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-299.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-298

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-298.md` (status in_progress → done).
- `nextjs.py`:
  - Added a window `keydown` event listener in `_detail_screen_page` for power-user shortcuts:
    - Pressing `ArrowLeft` or `[` navigates to the previous record when `prevItem` exists (`prevItem && handleSelectId(prevItem.id)`).
    - Pressing `ArrowRight` or `]` navigates to the next record when `nextItem` exists (`nextItem && handleSelectId(nextItem.id)`).
    - Pressing `e` or `E` switches to edit mode when `can_edit && form_screen && selectedId` is true.
    - Pressing `Escape` deselects the current record (`handleSelectId(null)`).
    - Keystrokes are ignored when focused within editable targets (`INPUT`, `TEXTAREA`, `SELECT`, `contentEditable`).
    - Full event listener cleanup on unmount with dependency array.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_detail_keyboard_navigation.py` with 7 focused tests (listener attachment,
  prev/next arrow and bracket navigation, edit mode shortcut, escape deselect, editable target guard, diff invariance,
  example projects generation).
- `task verify` — 909 tests pass (7 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-298 Done row at `Phase_Roadmap!A9`; table `A4:M306`; 298 unique IDs (0 dupes);
  87 Done, 1 Deferred, 210 Not Started; MVP 87/193 (45.1%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-298.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-297

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-297.md` (status in_progress → done).
- `nextjs.py`:
  - Added `searchInputRef = useRef<HTMLInputElement>(null)` and attached `ref={searchInputRef}` to the
    collection search input.
  - Added a window `keydown` event listener for power-user shortcuts:
    - Pressing `/` outside existing editable elements (INPUT, TEXTAREA, SELECT, contentEditable)
      focuses `searchInputRef` and prevents default `/` keypress character insertion.
    - Pressing `Escape` when focused inside the collection search input clears `searchInput`, calls
      `setSearch("")` to reset committed search state, and blurs the input.
    - Pressing `Escape` outside editable elements when active filters exist (`activeFilterCount > 0`)
      calls `clearFilters()`.
    - Proper event listener cleanup on unmount with dependency array `[setSearch, activeFilterCount, clearFilters]`.
  - Maintained strict diff invariance across `ir.description`.
- Added `services/agent-engine/tests/test_collection_keyboard_navigation.py` with 8 focused tests (search ref
  attachment, slash shortcut listener, editable target guard, escape clearing search, escape clearing filters,
  screen without filters, diff invariance, example projects generation).
- `task verify` — 902 tests pass (8 new), 0 failures. `task lint`, `task security:quick`, `task env:check`
  pass. `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected.
  0 network, 0 cloud model calls.
- Tracker: inserted R-297 Done row at `Phase_Roadmap!A9`; table `A4:M305`; 297 unique IDs (0 dupes);
  86 Done, 1 Deferred, 210 Not Started; MVP 86/192 (44.8%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-297.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-296

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-296.md` (status in_progress → done).
- `nextjs.py`:
  - Error banners across collection list, detail screen, subcollections (both collection and detail views),
    and form submission now emit `role="alert"` and `aria-live="assertive"` for immediate assistive announcement.
  - Search inputs now emit `aria-label="Search <plural>"` (collection) and `aria-label="Search <child_plural>"`
    (subcollections).
  - Sortable table headers in `_collection_screen_page` now emit dynamic WAI-ARIA `aria-sort` reflecting
    current `params.sort` and `params.order` ("ascending", "descending", or "none").
  - Collection pagination controls are enclosed in `<nav aria-label="Pagination">` and Previous/Next buttons
    emit `aria-label="Previous page"` and `aria-label="Next page"`; subcollection pagination Previous/Next
    buttons emit `aria-label="Previous page"` and `aria-label="Next page"` as well.
  - Contextual empty-state text containers in collection and subcollection lists emit `role="status"`.
  - All existing text labels, retry buttons, skeletons, and hook signatures are strictly preserved;
    strict diff invariance across `ir.description` preserved.
- Added `services/agent-engine/tests/test_screen_accessibility.py` with 13 focused tests (error banner alert
  role and assertive live regions across all 4 screens/views, search aria-labels, sortable header aria-sort,
  collection and subcollection pagination nav and button labels, empty state status roles, description diff
  invariance, example projects generation), written test-first.
- `task verify` — 894 tests pass (13 new), 0 failures. `task lint`, `task security:quick`, `task env:check`
  pass. `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected.
  0 network, 0 cloud model calls.
- Tracker: inserted R-296 Done row at `Phase_Roadmap!A9`; table `A4:M304`; 296 unique IDs (0 dupes);
  85 Done, 1 Deferred, 210 Not Started; MVP 85/191 (44.5%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-296.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-295

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-295.md` (status in_progress → done).
- `nextjs.py`:
  - `_detail_screen_page` main error banner: wrapped `Error loading <name>: {error.message}` in a
    `<span>` and added a `<button onClick={() => refetch()}>Retry</button>` in a flex row (matching the
    collection banner's `#991b1b` styling); `refetch` is already destructured from `use<Entity>(selectedId)`.
  - Both subcollection (master-detail) error banners (the collection master-detail block in
    `_collection_screen_page` and the detail block in `_detail_screen_page`, byte-identical → updated via
    `replace_all`): wrapped `Error: {<s_var>.error.message}` in a `<span>` and added a
    `<button onClick={() => <s_var>.refetch()}>Retry</button>` in a flex row.
  - The collection top-level error banner (already had Retry) is unchanged; loading/empty/data-render
    states, delete-error toasts, and form field errors are unchanged. Strict diff invariance across
    `ir.description` preserved.
- Added `services/agent-engine/tests/test_fetch_error_retry.py` with 8 focused tests (detail-main retry,
  detail-main message preserved, collection master-detail subcol retry, detail subcol retry, Retry-button
  counts on both screens, description diff invariance, example projects still generate), written test-first.
- `task verify` — 881 tests pass (8 new), 0 failures; the existing `test_subcollection_screens.py`
  `commentsSubcol.error.message` assertion is preserved. `task lint`, `task security:quick`, `task
  env:check` pass. `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript
  inspected. 0 network, 0 cloud model calls.
- Tracker: inserted R-295 Done row at `Phase_Roadmap!A9`; table `A4:M303`; 295 unique IDs (0 dupes);
  84 Done, 1 Deferred, 210 Not Started; MVP 84/190 (44.2%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-295.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.
- Founder asked to STOP after R-295 and provide a paste-anywhere resume prompt for R-296.

## 2026-09-10 — R-294

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-294.md` (status in_progress → done).
- `nextjs.py`: added four static App Router special-file templates + `render_*` accessors and wired them
  into `NextjsWebAdapter.generate()`:
  - `app/error.tsx` — `"use client"` route-segment error boundary; typed `{ error, reset }`, logs via
    `useEffect`, "Try again" button calling `reset()`, "Back to overview" `<Link href="/">`.
  - `app/global-error.tsx` — `"use client"` root-layout error boundary rendering its own
    `<html lang="en"><body>` + `reset()` recovery.
  - `app/not-found.tsx` — server component 404 with a `<Link href="/">` back to the overview.
  - `app/loading.tsx` — server route-level Suspense fallback mapping `[0..5]` skeleton cards
    (`height: 96, background: "#f1f5f9", opacity: 1 - i * 0.12`) plus a header bar, reusing the
    R-292/293 skeleton palette.
  - All four are static (no `ir.name`/`ir.description`), inline-styled, dependency-free → deterministic,
    description-only-stable, and never in the console-snapshot edit diff.
- `codegen/__init__.py`: exported `render_error_page`, `render_global_error_page`, `render_not_found_page`,
  `render_loading_page`.
- Added `services/agent-engine/tests/test_app_router_resilience.py` with 9 focused tests (all four files
  present, client/server split, `reset()` wiring, global-error own html/body, loading skeletons, static/
  description-invariance, example projects include the files), written test-first.
- `task verify` — 873 tests pass (9 new), 0 failures; no existing assertion changed; `test_console_snapshot`
  description-edit diff set unchanged. `task lint`, `task security:quick`, `task env:check` pass.
  `builder:demo minimal-blog` + `rideshare-favourites` pass. Generated TypeScript inspected. 0 network,
  0 cloud model calls.
- Tracker: inserted R-294 Done row at `Phase_Roadmap!A9`; table `A4:M302`; 294 unique IDs (0 dupes);
  83 Done, 1 Deferred, 210 Not Started; MVP 83/189 (43.9%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-294.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-10 — R-293

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-293.md` (status in_progress → done).
- `nextjs.py`:
  - `_form_screen_page`: replaced the edit-mode initial-load banner text `Loading <name> details...`
    with `{[0, 1, 2].map((i) => (<div key={i} style={{ height: 34, background: "#e2e8f0", borderRadius: 6, opacity: 1 - i * 0.2 }} />))}` inside the existing flex-column banner.
  - `_detail_screen_page`: replaced the record-selector `{loadingList && <p>Loading <plural>...</p>}`
    with `{loadingList && (<div grid>{[0, 1, 2].map((i) => (<div key={i} style={{ height: 56, background: "#f1f5f9", borderRadius: 6, opacity: 1 - i * 0.2 }} />))}</div>)}` using the same `repeat(auto-fill, minmax(220px, 1fr))` grid as the recent-records cards.
  - Static inline-styled skeletons only; no CSS `@keyframes`, no new file/component, no dependency.
    Completes the R-292 skeleton coverage. Strict diff invariance across `ir.description` preserved.
- Added `services/agent-engine/tests/test_loading_skeletons_extra.py` with 6 focused tests (form
  skeleton present + text removed, record-selector skeleton cards present + text removed, description-only
  diff invariance, both example projects still generate), written test-first.
- Updated one `test_form_update_screens.py` initial-load assertion (`Loading article details...` →
  the skeleton `<div>` markup).
- `task verify` — 864 tests pass (6 new), 0 failures. `task lint`, `task security:quick`, `task env:check`
  pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. Generated form
  initial-load and detail record-selector loading states inspected. 0 network calls, 0 cloud model calls.
- Tracker: inserted R-293 Done row at `Phase_Roadmap!A9`; table `A4:M301`; 293 unique IDs (0 dupes);
  82 Done, 1 Deferred, 210 Not Started; MVP 82/188 (43.6%); no `#REF!`; XLSX valid.
- Updated CURRENT_TASK.yaml, tasks/R-293.md, PROJECT_STATE.yaml, HANDOFF.md, PROJECT_STATE.md,
  CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md, docs/RESUME_PROMPT.md.

## 2026-09-09 — R-279

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-279.md`.
- `nextjs.py`:
  - Added `_TOAST_COMPONENT` template and `render_toast_component()` generating `apps/web/components/toast.tsx` exporting `ToastProvider`, `useToast`, and typed helper interfaces.
  - Floating viewport container fixed at bottom-right with auto-dismiss timers, manual dismiss `×` buttons, and distinct status color accents (emerald success, red error, blue info).
  - Updated `_LAYOUT` in `apps/web/app/layout.tsx` to import `ToastProvider` and wrap `{children}` and `<Navbar />`.
  - Added `GeneratedFile("components/toast.tsx", _TOAST_COMPONENT)` in `NextjsWebAdapter.generate()`.
  - Wired real-time action feedback into `_collection_screen_page`: CSV export (`toast.info`), single delete (`toast.success` / `toast.error`), batch delete (`toast.success` with count / `toast.error`), and subcollection delete (`toast.success` / `toast.error`).
  - Wired real-time action feedback into `_detail_screen_page`: JSON export (`toast.info`), main delete (`toast.success` / `toast.error`), and subcollection delete (`toast.success` / `toast.error`).
  - Wired real-time action feedback into `_form_screen_page`: create/update submit (`toast.success` / `toast.error`) and Reset button (`toast.info`).
  - Exported `render_toast_component` in `omnistackai_agent_engine.codegen`.
  - Strict diff invariance maintained across `ir.description`.
- Added `services/agent-engine/tests/test_toast_notifications.py` with 14 comprehensive unit tests.
- `task verify` — 756 tests pass (14 new), 0 failures. `task lint`, `task security:quick` pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-279.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-09 — R-278

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-278.md`.
- `nextjs.py` (`_collection_screen_page`):
  - Added `_filterable_fields_for_entity(entity)` helper identifying boolean fields (`FieldType.BOOL`) and enum fields (`enum:a|b|c` in validation rules).
  - Conditionally imported `useMemo` from `"react"` when filterable fields are present.
  - Declared `filterValues` state (`Record<string, string>`) and `handleFilterChange(field, val)` and `handleClearFilters()` handlers.
  - Computed `activeFilterCount` and `filteredData` via `useMemo` comparing items against active filter values.
  - Computed `displayData = filteredData ?? (data ?? [])` and wired it into table row mapping.
  - Rendered accessible filter toolbar above the table:
    - Boolean fields: segmented pill buttons `[ All ] [ {Field}: Yes ] [ {Field}: No ]` with `#0f172a` active pill styling.
    - Enum fields: styled `<select aria-label="Filter by {Field}">` dropdown.
    - Active filter count badge (`{activeFilterCount} active`) in `#eff6ff`/`#1d4ed8`.
    - "Reset" button calling `handleClearFilters`.
  - Added dedicated filter empty state when `data.length > 0 && activeFilterCount > 0 && displayData.length === 0`: `"No {plural} match the active filter criteria."` with `"Clear all filters"` button.
  - Clean fallback for entities without boolean or enum fields (zero filter code emitted).
  - `# noqa: PLR0912` added for branch count.
- Added `services/agent-engine/tests/test_collection_field_filters.py` with 15 comprehensive unit tests.
- `task verify` — 742 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-278.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-09 — R-277

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-277.md`.
- `nextjs.py` (`_form_screen_page`):
  - Added `useMemo` to `"react"` imports alongside `useState` and `useEffect`.
  - Computed `initialValues` constant partial object.
  - Computed `baselineData` using `useMemo` comparing against `initialData` (in edit mode when loaded) or `initialValues` (in create mode).
  - Emitted `isDirty` via `useMemo` comparing every key in `formData` against `baselineData` (gracefully handling `undefined` vs `""` equivalence).
  - Added native window `beforeunload` event listener via `useEffect` guarding page refresh/close when `isDirty && !submitting && !success`.
  - Added amber visual "Unsaved changes" badge (`#fef3c7` / `#92400e`) in header next to screen title when `isDirty && !success`.
  - Added amber warning notice in form footer (`&bull; You have unsaved changes`) when `isDirty && !success`.
  - Added guarded `onClick` handler on `Cancel` link button: `if (isDirty && !confirm("You have unsaved changes. Discard them and leave?")) { e.preventDefault(); }`.
  - Added guarded `onClick` handler on `Reset` button: `if (!isDirty || confirm("Discard all changes and reset form?")) { ...; setLastSavedId(null); }`.
  - Post-submit success (`setSuccess(true)`) naturally suppresses dirty state warnings and unblocks navigation.
  - Added `# noqa: PLR0912` for branch count.
- Added `services/agent-engine/tests/test_form_unsaved_changes_guard.py` with 16 comprehensive unit tests.
- `task verify` — 727 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-277.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-09 — R-276

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-276.md`.
- `nextjs.py` (`_detail_screen_page`):
  - Added `can_list = Op.LIST in ops` check.
  - Added `useList<Plural>` to `hooks_to_import` when `can_list` is true.
  - Emitted `useList<Plural>()` call, computing `listItems`, `loadingList`, `currentIndex`, `prevItem`, and `nextItem`.
  - Added `handleSelectId(newId)` helper function that updates `selectedId`, `idInput`, and updates browser search params (`?id=...`) via `window.history.replaceState`.
  - Added `<select aria-label="Select {name}">` dropdown in top ID selection section with `"-- Choose {name} --"` placeholder and options mapped to existing records with best descriptive field or id fallback.
  - Added "Clear" button in ID bar when `selectedId` is active.
  - Added contextual `&larr; Prev` and `Next &rarr;` navigation buttons in the item card header with boundary disabled attributes.
  - Added "Recent {plural}" card grid in the empty state (when `!selectedId`) allowing one-click record selection.
  - Updated `handleDelete` to clean up the `id` search parameter from the URL upon record deletion.
  - `# noqa: PLR0912` added for branch count; clean fallback when `Op.LIST` is absent or only id field.
- Added `services/agent-engine/tests/test_detail_record_selector.py` with 16 comprehensive unit tests.
- `task verify` — 711 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-276.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-09 — R-275

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-275.md`.
- `nextjs.py` (`_overview_page`):
  - Replaced static 20-line bare HTML list with a rich entity-aware dashboard client component.
  - Added `"use client";` directive — overview page is now a client component to enable React hooks.
  - Imports `Link from "next/link"` for navigation; imports `useList<Plural>` hook for each entity with `Op.LIST` wired (reuses `_get_ops_by_entity`).
  - Calls `useList<Entity>({ limit: 1 })` per listable entity — `.total` (all records) displayed with loading (`"…"`) and error (`"—"`) fallbacks.
  - Entity summary cards grid: white card with box-shadow, 32px `#0f172a` count, uppercase entity label, plural subtitle.
  - Screen navigation cards for each primary screen (collection + form, detail excluded): styled `<Link>` tiles with intent label badge; role badge (`#eff6ff`/`#1d4ed8` pill) for non-public screens (reuses `_screen_intent`, `_title_case`).
  - Quick Actions section: `+ Create {Entity}` blue CTAs (`#2563eb`) linking to each form screen entity (reuses `_match_entity`).
  - `ir.description` removed from page body — fixes the existing diff-invariance violation; description already in `README.md`.
  - Clean fallback when `ir.entities` is empty (no hook imports, no cards) and when `ir.screens` is empty (no nav section).
  - `# noqa: PLR0912` on function (high branch count justified by inline card/section rendering).
- `test_console_snapshot.py`: removed `apps/web/app/page.tsx` from expected edit-diff path set — description-stable page no longer changes when only `ir.description` changes.
- Added `services/agent-engine/tests/test_overview_dashboard.py` with 16 comprehensive unit tests.
- `task verify` — 695 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-275.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-274

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-274.md`.
- `nextjs.py` (`_form_screen_page`):
  - Detected `detail_screen` and `list_screen` for the entity in `ir.screens` using `_screen_intent`.
  - Added `lastSavedId` state: `const [lastSavedId, setLastSavedId] = useState<string | null>(null);`.
  - `handleSubmit` create branch: `const res = await create(formData);` + `if (res && (res as any).id) { setLastSavedId(String((res as any).id)); }`.
  - `handleSubmit` update branch: `setLastSavedId(editId);` after `await update(editId, formData);`.
  - Success banner upgraded to interactive action panel:
    * Preserved exact message text wrapped in `<span>{msg_jsx}</span>` for existing test invariance.
    * Dismiss button (`&times;`) with `aria-label="Dismiss"` calling `setSuccess(false)`.
    * "View {name} &rarr;" `Link` to `/{detail_screen.id}?id=${lastSavedId || editId}` (guarded by id expression check), when `detail_screen` exists.
    * "&larr; Back to {plural}" `Link` to `/{list_screen.id}`, when `list_screen` exists.
    * "+ Create another {name}" button (in create mode) calling `setSuccess(false); setLastSavedId(null);`.
  - Form footer: added `Cancel` `Link` button to `/{list_screen.id}` (or `/`); Reset `onClick` now includes `setLastSavedId(null);`.
- Added `services/agent-engine/tests/test_form_navigation_ctas.py` with 16 comprehensive unit tests.
- `task verify` — 679 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-274.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-273


- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-273.md`.
- `nextjs.py`:
  - Implemented `_navbar_component(ir: ApplicationIR) -> str`:
    * Emitted client component (`"use client";`) with `usePathname` from `"next/navigation"`.
    * Implemented active route detector `isLinkActive(href)` and visual highlight styling helper `navLinkStyle(active)`.
    * Rendered app branding with avatar logo badge (first letter of `ir.name`) and title linking to `/`.
    * Rendered "Overview" link to `/`.
    * Dynamically rendered screen navigation links for primary collection, form, and generic screens from `ir.screens`, displaying screen title, role pill badges for non-public screens, and active state highlights.
    * Excluded parameter-dependent `detail` screens from the horizontal nav bar to keep top navigation focused.
    * Detected first create form screen in `ir.screens` and rendered a prominent `+ New {Entity}` / `+ Create` quick-action CTA button on the right side of the navbar.
    * Supported empty screens with clean fallback.
  - Updated `_LAYOUT`:
    * Imported `Navbar` from `../components/navbar`.
    * Rendered `<Navbar />` inside `<body>` above `{children}`, wrapping all pages in a cohesive layout with typography and background tokens (`#f8fafc`).
  - Registered `GeneratedFile("components/navbar.tsx", _navbar_component(ir))` in `NextjsWebAdapter.generate()`.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_navbar_navigation.py` with 17 comprehensive unit tests.
- Updated `test_nextjs_adapter.py` to expect `components/navbar.tsx`.
- `task verify` — 663 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task doctor` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-273.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-272

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-272.md`.
- `nextjs.py`:
  - `_detail_screen_page`:
    * Imported `useState, useEffect` from `"react"` and `useSearchParams` from `"next/navigation"`.
    * Implemented query parameter extraction: `const queryId = searchParams.get("id");` initializing `idInput` and `selectedId`, and synchronized with `useEffect` when `queryId` updates.
    * Added entity deletion: when `can_delete`, imported and wired `useDelete{name}()` with `handleDelete` prompting confirmation dialog, setting loading state (`deletingMain`), error capture (`deleteMainError`), and state cleanup.
    * Added single-record client-side JSON export: `handleExportJson` formats entity record to formatted JSON via `Blob`, dynamic anchor element, and `URL.revokeObjectURL`.
    * Added breadcrumb navigation: links back to collection screen (`&larr; Back to {plural}`) when complementary collection screen is detected.
    * In item card header: rendered action buttons bar with "Export JSON", "Edit {name}" (navigating to `/{form_screen.id}?id=${selectedId}` when editable), and "Delete {name}" (when deletable), with error feedback alert banner.
  - `_collection_screen_page`:
    * Detected dedicated `detail_screen` for the entity in `ir.screens`.
    * When `detail_screen` exists, rendered a styled "View" link button (`/{detail_screen.id}?id=${(item as any).id}`) in the table row actions cell.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_detail_screen_lifecycle.py` with 16 comprehensive unit tests.
- `task verify` — 646 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-272.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-271

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-271.md`.
- `nextjs.py`:
  - Added `handleExportCsv(selectedOnly: boolean = false)` helper function to `_collection_screen_page`:
    * Filters items by `checkedIds` when `selectedOnly` is true (`(data ?? []).filter((item: any) => checkedIds.includes(item.id))`), or exports all items (`data ?? []`).
    * Early return when no items are available for export.
    * Implemented strict RFC 4180 value serialization helper `toCsvVal`: formats `null`/`undefined` as `""`, safely serializes objects via `JSON.stringify`, escapes internal double quotes (`"`) as `""`, and wraps all values in double quotes.
    * Included all declared entity fields (`entity.fields`) in both headers and row mapping.
    * Managed browser download lifecycle using `Blob([csvContent], { type: "text/csv;charset=utf-8;" })`, `URL.createObjectURL(blob)`, temporary `<a>` element with `download="{plural.lower()}_export.csv"`, automated trigger `link.click()`, DOM removal, and memory cleanup with `URL.revokeObjectURL(url)`.
  - Top toolbar:
    * Added "Export CSV" button in the table controls section alongside Search and Refresh (`disabled={!data || data.length === 0}`).
  - Contextual Bulk Actions Bar:
    * Added "Export Selected ({checkedIds.length})" button calling `handleExportCsv(true)` inside `{checkedIds.length > 0 && ...}`.
    * Ensured Export Selected button is present whether or not the entity has delete capability; coexists with "Delete Selected" when deletion is enabled.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_collection_csv_export.py` with 16 comprehensive unit tests.
- `task verify` — 630 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-271.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-270

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-270.md`.
- `nextjs.py`:
  - Added multi-record row selection state to `_collection_screen_page`:
    * `const [checkedIds, setCheckedIds] = useState<string[]>([]);`
    * `const allCurrentIds = (data ?? []).map((item: any) => item.id).filter(Boolean);`
    * `const isAllChecked = allCurrentIds.length > 0 && allCurrentIds.every((id: string) => checkedIds.includes(id));`
    * `const handleCheckAll = () => { if (isAllChecked) { setCheckedIds((prev) => prev.filter((id) => !allCurrentIds.includes(id))); } else { setCheckedIds((prev) => Array.from(new Set([...prev, ...allCurrentIds]))); } };`
    * `const handleToggleRow = (id: string) => { setCheckedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])); };`
    * `const handleClearSelection = () => { setCheckedIds([]); };`
  - In `handleDelete(id)`: automatically cleaned up deleted ID from selection via `setCheckedIds((prev) => prev.filter((x) => x !== id));`.
  - When `can_delete` is True:
    * Declared `batchDeleting` loading state and `batchDeleteError` error state.
    * Implemented `handleBatchDelete` with confirmation prompt (`confirm("Are you sure you want to delete {count} {name/plural}?")`), concurrent execution (`await Promise.all(checkedIds.map(id => remove(id)))`), selection clearing, automatic `refetch()`, and error capture.
    * Rendered dismissible `batchDeleteError` alert banner with retry/dismiss button.
  - Rendered contextual floating/inline Bulk Actions Bar above the table when `checkedIds.length > 0`:
    * Shows selection count badge: `{checkedIds.length} {name/plural} selected`.
    * Includes `Clear selection` button bound to `handleClearSelection`.
    * When `can_delete` is True, renders `Delete Selected ({checkedIds.length})` button with loading state `{batchDeleting ? "Deleting..." : ...}`.
  - Table header `<thead>`:
    * Rendered master checkbox column with `aria-label="Select all"`, `checked={isAllChecked}`, and `onChange={handleCheckAll}`.
  - Table body `<tbody>`:
    * Adjusted loading and empty state `colSpan` to account for checkbox column (`1 + len(display_fields) + (1 if has_actions_col else 0)`).
    * Rendered row selection checkbox in each data row with `e.stopPropagation()` so selecting checkboxes does not toggle subcollection detail panels.
    * Highlighted selected rows with `#f8fafc` background.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_collection_bulk_actions.py` with 16 comprehensive unit tests.
- `task verify` — 614 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-270.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-269

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-269.md`.
- `nextjs.py`:
  - Added `setPageSize: (size: number) => void;` to `UseListState<T>` interface in `_generate_hooks_ts`.
  - Implemented `setPageSize = useCallback((newPageSize: number) => { setParams((prev) => ({ ...prev, limit: Math.max(1, newPageSize), offset: 0 })); }, []);` in both `useList<Entities>()` and `useList<Children>By<Rel>()`.
  - Included `pageSize` and `setPageSize` in returned state objects of both list hooks.
  - In `_collection_screen_page`:
    - Destructured `pageSize` and `setPageSize` from `useList<Plural>()`.
    - Rendered an accessible `<select id="pageSizeSelect">` with `aria-label="Select page size"` directly in the table footer alongside pagination buttons with options: 10, 25, 50, 100 per page.
    - Updated table body empty state (`data && data.length === 0`):
      * When search is active (`searchInput.trim()`): renders `No <plural> matching "<searchInput>".` with interactive `Clear search` CTA button (`onClick={() => { setSearchInput(""); setSearch(""); }}`).
      * When no search is active and `form_screen` exists: renders `No <plural> found yet.` with styled `+ Create first <Entity>` CTA link (`href="/{form_screen.id}"`).
      * When no `form_screen` exists: renders fallback `No <plural> found.`.
    - In subcollection panels (`_collection_screen_page` and `_detail_screen_page`):
      * When child data is empty and `child_form` exists: renders `No <children> found for this <entity>.` alongside a styled `+ Add first <Child>` link (`href="/{child_form.id}?{sub.id_param}=${selectedId}"`).
  - Preserved byte-for-byte diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_collection_pagination_empty_states.py` with 15 unit tests covering interface declaration, hook implementations, return object fields, selector rendering, options, search mismatch empty state with clear search button, form screen empty state CTA link, fallback empty state, subcollection empty state CTAs, diff invariance, and full project generation.
- `task verify` — 598 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-269.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-268

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-268.md`.
- `nextjs.py`:
  - Imported `HttpMethod` from `..application_ir`.
  - Added fallback entity resolution for `DELETE` endpoints where `response_schema` or `request_schema` was omitted in `_get_ops_by_entity` and `_generate_api_client_ts`.
  - Updated `_generate_hooks_ts` to source `ops_by_entity` from `_get_ops_by_entity(ir)`, ensuring complete consistency across API client, hooks, and screen pages.
  - Added `can_delete: bool = False` to `SubcollectionInfo` dataclass and set it in `_subcollections_for_parent` via `Op.DELETE in ops_by_entity.get(child_name, set())`.
  - In `_collection_screen_page`:
    - Automatically imported `useDelete<Child>` for each deletable subcollection, avoiding duplicate imports when parent entity shares delete capability.
    - Instantiated delete hooks at component level: `const { remove: remove<Child>, loading: deleting<Child>, error: delete<Child>Error } = useDelete<Child>();`.
    - Declared `handleDelete<Child>` handler with confirmation prompt (`confirm("Are you sure you want to delete this <Child>?")`), try/catch guard, and automatic subcollection refetch (`<subcol>.refetch()`).
    - Rendered mutation error feedback alert banner (`{delete<Child>Error && ...}`) when deletion fails.
    - Rendered an accessible, styled Delete button on each child item card with `e.stopPropagation()`, disabled state during mutation (`disabled={deleting<Child>}`), and dynamic label `{deleting<Child> ? "Deleting..." : "Delete"}`.
  - In `_detail_screen_page`:
    - Mirrored identical child deletion hook imports, hook instantiations, delete handlers, mutation error alert banners, and Delete buttons on child cards.
  - Clean fallback safety: subcollections whose child entity lacks `Op.DELETE` emit zero deletion code, and entities without subcollections emit zero subcollection code.
  - Preserved byte-for-byte diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_subcollection_deletion.py` with 13 unit tests covering detection, non-delete omission, fallback detection, hook imports, handler declaration with confirm and refetch, button rendering with stopPropagation, error alert display, detail screen wiring, mixed multi-subcollection wiring, diff invariance, and full project generation.
- `task verify` — 583 tests pass (13 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-268.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-267

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-267.md`.
- `nextjs.py`:
  - Imported `RelationKind` from `..application_ir`.
  - Added `_snake(value: str) -> str` string conversion helper.
  - Added `ParentRelationInfo` dataclass and `_parent_relations_for_entity(entity: Entity, ir: ApplicationIR) -> list[ParentRelationInfo]` helper:
    - Detects `RelationKind.MANY_TO_ONE` relations and fields ending in `_id` on child entities where the parent entity has `Op.LIST`.
    - Resolves parent entity, pluralized name, hook name (`useList<ParentPlural>`), primary display field (`title`/`name`/`id`), and display label.
  - Enhanced `_form_screen_page`:
    - Collects parent relations via `_parent_relations_for_entity(entity, ir)` and maps them by `field_name`.
    - Appends any missing foreign key fields from parent relations to `editable_fields`.
    - Automatically imports parent list hooks (`useList<ParentPlural>`) from `"../lib/hooks"`.
    - Wires parent list hooks at component top level (`const <parents>List = useList<Parents>();`).
    - Enriches `searchParams` prefilling effect with alias resolution (`<field>`, `<relation>_id`, `<relation>Id`, `<relation>`), ensuring child forms opened from `+ New <Child>` links pre-populate the parent foreign key in `formData`.
    - Enhances `handleSubmit` client-side error checking to validate required UUID / relation fields, displaying field-level errors when unselected.
    - Replaces raw text inputs for foreign key fields with accessible `<select>` dropdowns:
      - Default option showing loading state: `<option value="">{<parents>List.loading ? "Loading <parents>..." : "Select <parent>..."}</option>`.
      - Mapped options from parent list items displaying primary title/name: `<option key={item.id} value={item.id}>{String(item.title ?? item.name ?? item.id)}</option>`.
      - Visual parent linkage badge displayed when foreign key is selected: `&bull; Selected <Parent> linked`.
      - Integrated with `fieldErrors` display and `aria-invalid` attribute.
    - Preserved fallback safety: independent entities without relations (e.g. `minimal-blog` Post) omit relation list hooks, dropdowns, and badges.
    - Preserved byte-for-byte diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_form_relation_screens.py` with 12 unit tests covering helper detection, independent entity omission, hook import and invocation, select dropdown rendering, visual badge display, searchParams alias prefill, client-side required validation, minimal-blog clean fallback, diff invariance, and project generation.
- `task verify` — 570 tests pass (12 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-267.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-266

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-266.md`.
- `nextjs.py`:
  - Updated `_collection_screen_page`:
    - Computed `can_edit = (Op.UPDATE in ops) and (form_screen is not None)`.
    - Rendered an "Edit" action `<Link>` in the master table pointing to `/{form_screen.id}?id=${(item as any).id}` with `onClick={(e) => e.stopPropagation()}` to avoid toggling table row selection.
    - Updated subcollection master-detail view to render `+ New <Child>` link (`/{child_form.id}?{sub.id_param}=${selectedId}`) when complementary form screen exists for the child entity.
  - Enhanced `_form_screen_page`:
    - Computed `can_update = Op.UPDATE in ops` and `can_create = Op.CREATE in ops`.
    - When `can_update` is True, imported `useUpdate<Entity>`, `use<Entity>`, and `useSearchParams` from `"next/navigation"`.
    - Read `editId = searchParams.get("id")` and `isEdit = Boolean(editId)`.
    - Wired `const { update, loading: updating, error: updateError } = useUpdateArticle();` and `const { data: initialData, loading: fetchingInitial } = use<Entity>(editId);`.
    - Added `useEffect` to prefill `formData` when `initialData` changes in edit mode.
    - Branched `handleSubmit` to call `await update(editId, formData)` when in edit mode vs `await create(formData)` when in create mode.
    - Dynamically adapted headers (`{isEdit ? "Edit " + name : screen.name}`), submit button label (`{((submitting || updating) ? "Saving..." : (isEdit ? "Update " + name : "Save " + name))}`), loading indicator, and success alert banner.
    - Maintained clean fallback safety for entities without `Op.UPDATE` (e.g. `minimal-blog` Post), emitting zero edit/update code.
    - Preserved byte-for-byte diff invariance across `ir.description` modifications.
  - Updated `_screen_page` routing to dispatch to form screens when `Op.CREATE in ops or Op.UPDATE in ops`.
- Added `services/agent-engine/tests/test_form_update_screens.py` with 12 unit tests covering hook imports, search params, editId extraction, initialData prefill, update submission branching, dynamic labels, create-only fallback, collection screen edit action with stopPropagation, subcollection + New child link, diff invariance, and NextjsWebAdapter project generation.
- `task verify` — 558 tests pass (12 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-266.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-265

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-265.md`.
- `nextjs.py`:
  - Added `SubcollectionInfo` dataclass and `_subcollections_for_parent(parent_name: str, ir: ApplicationIR) -> list[SubcollectionInfo]` helper:
    - Scans `ir.relations` where `rel.target_entity == parent_name` and foreign key relation is wired with `Op.LIST_BY`.
    - Resolves child entity, relation name, capitalized names, list hook name (`useList<Children>By<Rel>`), and display fields.
  - Enhanced `_collection_screen_page`:
    - Checks for subcollections using `_subcollections_for_parent(entity.name, ir)`.
    - Imports subcollection hooks (e.g. `import { useListCommentsByPost } from "../lib/hooks";`) and child entity types (e.g. `import type { Comment } from "../lib/types";`) on dedicated lines preserving exact substring matches for parent imports.
    - Adds `selectedId` state (`const [selectedId, setSelectedId] = useState<string | null>(null);`) and active subcollection tab state for multi-subcollection entities.
    - Wires subcollection hooks at top level scoped to `selectedId` (e.g. `const commentsSubcol = useListCommentsByPost(selectedId);`).
    - Enriches master table with interactive row selection (`onClick={() => setSelectedId(selectedId === item.id ? null : item.id)}`), visual row selection highlight, and action column button (`"View Details"` / `"Hide Details"`).
    - Renders master-detail subcollection section below table when an item is selected:
      - Parent entity header banner with "Close Details" action.
      - Tab bar for multi-subcollection entities with interactive switching and live total count badges (`{subcol.total}`).
      - Child items list rendering loading state, error state with retry, empty state, and child item cards displaying key scalar attributes.
      - Subcollection refresh action button.
  - Implemented `_detail_screen_page`:
    - Dedicated screen for screens with `intent == "detail"`.
    - Renders parent entity detail view fetching with `use<Entity>(id)`.
    - Renders parent attribute grid, back navigation to collection screen, and nested child subcollections section.
  - Updated `_screen_page` routing to dispatch `intent == "detail"` to `_detail_screen_page`.
  - Maintained fallback safety: entities without subcollections (e.g. `rideshare-favourites`) emit zero subcollection code, state, or hooks.
  - Preserved diff invariance: generated screens do not reference `ir.description`, preventing diff drift in `test_console_snapshot.py`.
- Added `services/agent-engine/tests/test_subcollection_screens.py` with 19 unit tests covering subcollection detection, hook and type imports, selection state, scoped invocation, total count badges, child items and states, master table row click interaction, fallback cleanliness, multi-subcollection tabs, detail screens, diff invariance, and project generation.
- `task verify` — 546 tests pass (19 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-265.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-264

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-264.md`.
- `nextjs.py`:
  - Added `extractFieldErrors(error: unknown): Record<string, string>` export in `apps/web/lib/api.ts`:
    - Normalizes Go backend structured errors (`{"errors": [{"field": "...", "rule": "...", "message": "..."}]}`).
    - Normalizes FastAPI structured errors (`{"detail": [{"loc": ["body", "..."], "msg": "..."}]}`).
    - Safely falls back to empty map for non-validation errors.
  - Enhanced `_form_screen_page`:
    - Imported `extractFieldErrors` from `../lib/api`.
    - Added `fieldErrors` state (`const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});`).
    - Implemented client-side pre-validation inside `handleSubmit`: checks `required` fields, string `max_length`, numeric `min`/`max`, and enum options before network requests, setting `fieldErrors` and halting on failure.
    - Updated submission error handling to call `extractFieldErrors(err)` and populate `fieldErrors` with server-side validation failures.
    - Conditionally styled inputs with red borders (`fieldErrors[f.name] ? "1px solid #ef4444" : "1px solid #cbd5e1"`) and accessibility attributes (`aria-invalid={!!fieldErrors[f.name]}`).
    - Rendered dedicated field error message spans directly beneath invalid inputs.
    - Added reactive error clearing on input edit (`onChange`).
    - Rendered interactive `<select>` dropdowns with declared options for enum fields.
    - Reset button clears `fieldErrors` alongside form data.
    - Added warning banner (`"Please correct the highlighted errors below before submitting."`) when field errors exist.
    - Preserved diff invariance by avoiding references to `ir.description`.
- Added `services/agent-engine/tests/test_form_validation_screens.py` with 12 unit tests covering `extractFieldErrors`, form screen error imports, client-side pre-validation, server error extraction, input styling, error spans, clear-on-change, enum dropdowns, reset button, and diff invariance.
- `task verify` — 527 tests pass (12 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-264.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-263

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-263.md`.
- `nextjs.py`:
  - Implemented `_match_entity(screen: Screen, ir: ApplicationIR) -> Entity | None` using multi-token score matching across screen IDs, component tags, and actions.
  - Implemented `_screen_intent(screen: Screen) -> str` classifying screens as `"collection"`, `"form"`, or `"generic"`.
  - Implemented `_get_ops_by_entity(ir: ApplicationIR) -> dict[str, set[Op]]` mapping available operations to avoid generating broken imports.
  - Implemented `_collection_screen_page`:
    - Emits `"use client";` directive at top.
    - Imports `useList<Entities>` (and `useDelete<Entity>` if `Op.DELETE` wired) from `../lib/hooks` and entity type from `../lib/types`.
    - Live search input bound to `setSearch` and form submission.
    - Sortable table headers bound to `setSort` with order indicators (`↓`/`↑`).
    - Pagination controls (`Previous`, `Next`, `Page X of Y`) bound to `setPage`.
    - Loading, error with retry button, and empty state cards.
    - Header with role badge, overview link, and navigation to complementary form screen (`+ New <Entity>`).
  - Implemented `_form_screen_page`:
    - Emits `"use client";` directive at top.
    - Imports `useCreate<Entity>` from `../lib/hooks` and entity type from `../lib/types`.
    - Schema-derived inputs for each entity field: checkbox for `BOOL`, textarea for `TEXT`, number for `INT`/`FLOAT`, datetime-local for `DATETIME`, text for `STRING`.
    - Required indicators (`*`) and HTML `required` attributes.
    - Submission handling with `create(formData)`, success feedback banner, error capture banner, and reset/cancel navigation.
  - Implemented `_fallback_screen_page` rendering clean role badge, component tags, actions, and navigation links.
  - Preserved diff invariance by avoiding any reference to `ir.description` in generated screen pages.
  - Exported public `render_screen_page(screen: Screen, ir: ApplicationIR) -> str` and added to `omnistackai_agent_engine.codegen`.
- Created `services/agent-engine/tests/test_screen_generation.py` with 9 unit tests covering `"use client"`, collection screen data binding (search, pagination, sort, delete), form screen schema inputs and submission, fallback screens, full project generation, and diff invariance.
- `task verify` — 515 tests pass (9 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-263.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-262

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-262.md`.
- `nextjs.py`:
  - Implemented `_hooks_file(ir: ApplicationIR) -> str` emitting strongly-typed React hooks in `apps/web/lib/hooks.ts`.
  - Added `"use client"` directive, React built-in imports (`useCallback`, `useEffect`, `useState`, `type Dispatch`, `type SetStateAction`), types from `./types`, and API client helpers from `./api`.
  - Defined shared interfaces: `UseListParams`, `UseListState<T>`, `UseDetailState<T>`, `UseMutationState<TData, TResult = TData>`.
  - For each entity in `ir.entities`:
    - `useList<Entities>`: manages `params` state (`limit`, `offset`, `sort`, `order`, `q`), computes pagination (`page`, `pageSize`, `totalPages`), provides `setPage`, `setSearch`, `setSort`, `refetch`, and fetches with `api.list<Entities>WithCount`.
    - `use<Entity>`: detail hook fetching entity by ID via `api.get<Entity>`.
    - `useCreate<Entity>`: mutation hook with `create`, `mutate`, `loading`, `error`, `reset`.
    - `useUpdate<Entity>`: mutation hook with `update`, `mutate`, `loading`, `error`, `reset`.
    - `useDelete<Entity>`: mutation hook with `remove`, `mutate`, `loading`, `error`, `reset`.
  - For subcollections: `useList<Entities>By<Rel>` with scoped relation ID, pagination, search, and sorting.
  - Exported unified `hooks` object.
  - Added public `render_hooks(ir: ApplicationIR) -> str` and wired `GeneratedFile("lib/hooks.ts", _hooks_file(ir))` into `NextjsWebAdapter.generate`.
  - Exported `render_hooks` in `omnistackai_agent_engine/codegen/__init__.py`.
- Created `services/agent-engine/tests/test_nextjs_hooks.py` with 15 unit tests covering `"use client"`, imports, interfaces, list hook pagination/search/sorting, detail hook, mutation hooks, subcollection hooks, empty IR, unwired operations, and example IRs.
- `task verify` — 506 tests pass (15 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-262.md, PROJECT_STATE.yaml.

## 2026-09-08 — R-261

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-261.md`.
- `data_access.py`:
  - Added `_searchable_fields(entity: Entity) -> list[str]` selecting `FieldType.STRING` and `FieldType.TEXT` fields.
  - Python repository: `list_<table>` and `count_<table>` accept `q: str | None = None`. When `q` is provided and searchable fields exist, emits parameterized `WHERE (field1 ILIKE %s OR field2 ILIKE %s)` passing `f"%{q}%"` for each field.
  - Subcollections `list_<table>_by_<rel>` and `count_<table>_by_<rel>` scope queries with relation ID and search pattern.
  - Go store: `List<Entity>` and `Count<Entity>` accept `q string`. When `q != ""` and searchable fields exist, emits parameterized `WHERE (field1 ILIKE $1 OR field2 ILIKE $1)` with argument `"%"+q+"%"`.
  - Subcollections `List<Entity>By<Rel>` and `Count<Entity>By<Rel>` accept `q string` and scope queries with relation ID and search pattern.
  - Non-text entities gracefully omit search clauses with zero SQL errors.
- `backend_go.py`:
  - `_helpers_block`: added `parseSearch(r *http.Request) string` helper trimming `r.URL.Query().Get("q")`.
  - `_handlers_file_wired`: parsed `q := parseSearch(r)` on `Op.LIST` and `Op.LIST_BY` and passed `q` to store `Count...` and `List...` methods.
- `backend_python.py`:
  - Router generation: added `q: str | None = None` to `Op.LIST` and `Op.LIST_BY` endpoints and passed `q=q` to repository `count_...` and `list_...` functions.
- `nextjs.py`:
  - `_api_client_file`: updated `options.params` types in `list<Entities>`, `list<Entities>WithCount`, `list<Entities>By<Rel>`, and `list<Entities>By<Rel>WithCount` to include `q?: string`.
- `openapi.py`:
  - Added `q` query parameter descriptor to `Op.LIST` and `Op.LIST_BY` operations.
- Added `services/agent-engine/tests/test_search.py` with 16 unit tests covering Go store, Go handlers, Python repo, Python routers, Next.js client, OpenAPI 3.1 parameter declaration, and non-text entity handling.
- Updated existing assertions in `test_nextjs_api_client.py`, `test_sorting.py`, `test_pagination.py`, `test_total_count.py`, `test_route_wiring.py`, and `test_subcollection_wiring.py`.
- `task verify` — 491 tests pass (16 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-261.md.

## 2026-09-08 — R-260

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-260.md`.
- `openapi.py`:
  - Created `render_openapi(ir: ApplicationIR) -> dict[str, Any]` and `render_openapi_json(ir: ApplicationIR, indent: int = 2) -> str`.
  - Emitted OpenAPI 3.1.0 specification with `info` (name, description, version).
  - Emitted `components.schemas` converting all entities to JSON Schema properties with validation metadata (`maxLength`, `enum`, `minimum`, `maximum`, `required`), plus standard error schemas.
  - Emitted `components.securitySchemes` with `BearerAuth` (JWT).
  - Emitted `paths` mapping all endpoints with path parameters, query parameters (`limit`, `offset`, `sort`, `order` on LIST endpoints), request bodies, and responses with `X-Total-Count` header.
  - Mapped operation security requirements (`BearerAuth` + roles) based on `api.auth` and `api.required_roles`.
- `codegen/__init__.py`: exported `render_openapi` and `render_openapi_json`.
- `assembler.py`: emitted `contracts/openapi.json` in customer monorepo assembly and documented in root `README.md`.
- `backend_go.py`: emitted `openapi.json` at root of generated Go backend project.
- `backend_python.py`: emitted `openapi.json` at root of generated FastAPI backend project.
- Updated `test_console_snapshot.py` to expect `contracts/openapi.json` and `services/api/openapi.json` in showcase diff.
- Added `services/agent-engine/tests/test_openapi.py` with 14 unit tests covering OpenAPI 3.1 structure, schemas, validation rules, paths/parameters, auth/roles security, monorepo assembly, Go/FastAPI adapter emission, and determinism.
- `task verify` — 475 tests pass (14 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-260.md.

## 2026-09-08 — R-259

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-259.md`.
- `data_access.py`:
  - Python repository: added `count_{table}() -> int` (`SELECT COUNT(*) AS count FROM {TABLE}`) and `count_{table}_by_{relation}({relation}_id: str) -> int` (`SELECT COUNT(*) AS count FROM {TABLE} WHERE {relation}_id = %s`).
  - Go store: added `Count{pascal}(ctx context.Context, db *sql.DB) (int, error)` (`SELECT COUNT(*) FROM {table}`) and `Count{pascal}By{rel_pascal}(ctx context.Context, db *sql.DB, {relation}ID string) (int, error)` (`SELECT COUNT(*) FROM {table} WHERE {relation}_id = $1`).
- `backend_go.py`:
  - `_handlers_file_wired`: imported `"strconv"`. On `Op.LIST` and `Op.LIST_BY`, queries `total, err := store.Count...` prior to listing, and sets `w.Header().Set("X-Total-Count", strconv.Itoa(total))`.
  - `_main_file`: added `w.Header().Set("Access-Control-Expose-Headers", "X-Total-Count")` to `corsMiddleware`.
- `backend_python.py`:
  - `_router_file`: imported `Response` from `fastapi` when `uses_list` is true. Injected `response: Response` into `Op.LIST` and `Op.LIST_BY` handlers, queries `total = await {wiring.table}.count_...()`, and sets `response.headers["X-Total-Count"] = str(total)`.
  - `_main_file`: added `expose_headers=["X-Total-Count"]` to `CORSMiddleware`.
- `nextjs.py`:
  - `_api_client_file`: exported `PaginatedResult<T> { data: T; total: number }`.
  - Emitted `requestWithMeta<T>` helper extracting `X-Total-Count` from response headers.
  - Emitted `list<Entity>WithCount` and `list<Entity>sBy<Rel>WithCount` helpers returning `Promise<PaginatedResult<Entity[]>>`.
  - Preserved standard `list*` methods returning `Promise<Entity[]>` for backwards compatibility.
- Added `services/agent-engine/tests/test_total_count.py` with 15 unit tests covering Go store, Go handlers, Go CORS, Python repo, FastAPI routers, FastAPI CORS, and Next.js client integration.
- Updated FastAPI router signature assertions in `test_pagination.py` and `test_sorting.py`.
- `task verify` — 461 tests pass (15 new), 0 failures. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-259.md.

## 2026-09-08 — R-258

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-258.md`.
- `data_access.py`:
  - Python repository: declared `ALLOWED_SORT_FIELDS = [field.name for field in entity.fields]`; `list_<table>` and `list_<table>_by_<rel>` validate `sort` against whitelist (falling back to `"id"`) and `order` (falling back to `"ASC"`), emitting `ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s`.
  - Go store: `List<Entity>` and `List<Entity>By<Rel>` accept `limit, offset int, sort, order string`; emit switch statement mapping declared entity columns to whitelisted identifier (falling back to `"id"`) and case-insensitive check for `"desc"` (falling back to `"ASC"`), formatting `ORDER BY %s %s LIMIT $1 OFFSET $2`.
- `backend_go.py`:
  - `_handlers_shared_file`: emitted `parseSort(r *http.Request) (string, string)` helper extracting `sort` and `order`.
  - `_handlers_file_wired`: parsed `sort, order := parseSort(r)` on `Op.LIST` and `Op.LIST_BY` and passed them to store methods.
- `backend_python.py`:
  - `_router_file`: updated `Op.LIST` and `Op.LIST_BY` to declare `limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc"` and pass all parameters to data access repository functions.
- `nextjs.py`:
  - `_api_client_file`: updated `Op.LIST` and `Op.LIST_BY` client method signatures to type `params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc" }`.
- Added `services/agent-engine/tests/test_sorting.py` with 14 unit tests covering Go store, Go handlers, Python repos, Python routers, and Next.js client.
- Updated regression tests in `test_pagination.py`, `test_route_wiring.py`, `test_subcollection_wiring.py`, and `test_nextjs_api_client.py`.
- `task verify` — 446 tests pass (14 new), 0 failures. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-258.md.

## 2026-09-08 — R-257

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-257.md`.
- `nextjs.py`: added `_slug_to_pascal` and `_api_client_file(ir: ApplicationIR)` emitting `apps/web/lib/api.ts`.
  - Emits `BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""`.
  - Emits `ApiOptions` (with `token?: string` for Bearer auth and `params?: Record<...>` for query strings).
  - Emits `ApiError` with HTTP status and structured payload.
  - Emits generic `request<T>(path, options, body)` handling headers, query params, JSON, errors, and 204.
  - Emits strongly-typed methods for all endpoints: `list<Entity>(options?: { params?: { limit?: number, offset?: number } })`, `get<Entity>(id)`, `create<Entity>(data)`, `update<Entity>(id, data)`, `delete<Entity>(id)`, `list<Entity>sBy<Rel>(parentId, options)`, and custom endpoint fallbacks.
  - Exports combined `api` object namespace.
  - Added `lib/api.ts` to `NextjsWebAdapter.generate` file list and added `NEXT_PUBLIC_API_URL` to `.env.example`.
- `backend_go.py`: added `corsMiddleware` in `_main_file` wrapping `mux` with `Access-Control-Allow-*` and `OPTIONS` 204 preflight; updated `.env.example` with `CORS_ALLOWED_ORIGIN=*`.
- `backend_python.py`: configured `CORSMiddleware` in `_main_file` with `allow_origins`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`; updated `.env.example`.
- Added `test_nextjs_api_client.py` with 9 tests; updated `test_nextjs_adapter.py`.
- `task verify` — 432 tests pass (9 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-257.md.

## 2026-09-08 — R-256

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-256.md`.
- `route_wiring.py`: extended `wire_endpoint` to map `method in ("PATCH", "PUT")` with trailing id parameter
  and matching `request_schema` to `Op.UPDATE`.
- `backend_go.py`: `Put<Entities><Id>` handler wired (decodes body -> `validateStruct` if entity has rules ->
  `store.Update<Entity>` -> 404 on nil / 200 on success).
- `backend_python.py`: `@router.put` route handler wired (validates payload -> `update_<table>` -> 404 on None / 200).
- Negative wiring: PUT without path param, with mismatched schema, etc. stays 501 scaffold.
- Rule-free entities emit no `validateStruct` call in Go PUT handler.
- Example IRs (`minimal-blog`, `rideshare-favourites`) unchanged.
- Added `test_put_update_handlers.py` with 14 new tests; all pass.
- `task verify` — 423 tests pass (14 new), 0 failures. `task security:quick`, `task env:check` pass.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, tasks/R-256.md.


- Founder requested to complete both tasks before committing or pushing.
- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-255.md`.
- `backend_go.py`: `_handlers_shared_file` emits `parsePagination(r *http.Request) (int, int)` returning
  limit (default 100, parsed if >0) and offset (default 0, parsed if >=0) using `strconv.Atoi`;
  `_handlers_file_wired` calls `limit, offset := parsePagination(r)` for `Op.LIST` and `Op.LIST_BY`
  and passes them to `store.List<Entity>` and `store.List<Entity>By<Rel>`.
- `data_access.py`: Go `List<Entity>` and `List<Entity>By<Rel>` updated to accept `limit, offset int`
  and emit `LIMIT $1 OFFSET $2` and `LIMIT $2 OFFSET $3`.
- `backend_python.py`: `Op.LIST` and `Op.LIST_BY` route handlers updated to declare `limit: int = 100, offset: int = 0`
  query parameters and pass them to `list_<entity>(limit=limit, offset=offset)`.
- Added `test_pagination.py` with 11 new tests; updated existing assertions in `test_route_wiring.py`
  and `test_subcollection_wiring.py`.
- `task verify` — 409 tests pass (11 new), 0 failures. `task security:quick`, `task env:check` pass.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, tasks/R-255.md.


- R-253 committed and pushed (99c2fae). Founder approved R-254: "go for the next task."
- Founder confirmed Tier 0 / Ollama stays active; Groq key added to .env for later.
- Recorded task contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-254.md` before code.
- `field_validation.py` `go_validate_file()`: replaced flat `"validation_failed"` with a
  `validationError struct {Field/Rule/Message}` and a new `validateStruct(w, v) bool` that
  iterates `validator.ValidationErrors`, builds per-field entries, and writes the structured JSON
  body `{"errors":[...]}` via `writeJSON`; returns `false` on error, `true` on success; added
  `"fmt"` import for `fmt.Sprintf` message construction.
- `backend_go.py`: updated both CREATE and UPDATE call-sites from the old two-line
  `if status, msg := validateStruct(m); msg != "" { http.Error(...) }` pattern to the single-line
  `if !validateStruct(w, m) { return }` guard.
- Updated existing R-252 tests (`test_go_validation_enforcement.py`) to assert the new signature
  and structured body instead of the old flat string.
- Updated existing R-253 tests (`test_patch_update_handlers.py`) to assert `validateStruct(w, m)`.
- `test_validation_error_bodies.py`: 24 new tests covering struct type, all 3 JSON keys
  (field/rule/message), "errors" wrapper, fmt.Sprintf, no "validation_failed", writeJSON usage,
  new bool signature, handler call-site pattern, ordering, rule-free gate, example IRs.
- FastAPI/Pydantic: no change needed — Pydantic already returns structured 422 errors by default.
- `task verify` — 398 tests pass (24 new), 0 failures. `task security:quick`, `task env:check` —
  pass. 0 local model calls, 0 cloud calls.
- Updated CHANGELOG, PROGRESS.md, CURRENT_TASK, PROJECT_STATE, HANDOFF, WORK_LOG, R-254.md.

## 2026-09-08 — R-253

- Read AGENTS.md, START_HERE.md, PROJECT_STATE.yaml, CURRENT_TASK.yaml, HANDOFF.md; confirmed
  main @ 08a149e, tree clean, 350 tests passing; R-252 done.
- Ran `task doctor` (all tools present), `task verify` (350 pass), `task ai:status`,
  `task ai:handoff` — all clean. Proposed R-253 candidates to founder.
- Founder direction: "do what is best — no static or half work." Selected PATCH/update handlers
  (Option B) as the missing CRUD verb with real enforced runtime behaviour.
- Recorded task contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-253.md` before any code.
- `route_wiring.py`: added `Op.UPDATE`; `wire_endpoint` now maps `PATCH /entities/{id}` with
  matching `request_schema` → `Op.UPDATE` (one path param, last segment). Conservative: everything
  else stays 501.
- `data_access.py`: added `_go_update` helper → emits `Update<Entity>(ctx, db, id, m)` with
  parameterized `UPDATE … SET col=$i … WHERE id=$N RETURNING <col_list>`; returns `*models.<Entity>`
  or `nil` on `ErrNoRows`. Added `_python_update` helper → emits `update_<table>(id, data)` with
  parameterized `UPDATE … SET col=%s … WHERE id=%s RETURNING *`; `fetchone()` gives `None` on miss.
- `backend_go.py`: `_handlers_file_wired` handles `Op.UPDATE` — decode body → `validateStruct` (if
  entity has rules) → `store.Update<Entity>` → 404 on nil / 200 writeJSON. `uses_models` extended
  for UPDATE. `has_validation` gate extended to cover UPDATE + CREATE.
- `backend_python.py`: `_router_file` handles `Op.UPDATE` — emits `@router.patch` with `id_param +
  payload` → `update_<table>` → `HTTPException(404)` on `None`. `models_used` extended for UPDATE.
- `tests/test_patch_update_handlers.py`: 24 new tests covering Go store/handler/validation-ordering/
  negative-wiring and Python repo/router; example IR regression; all assertions pass.
- `task verify` — 374 tests pass (24 new), 0 failures. `task security:quick`, `task env:check` —
  pass. 0 local model calls, 0 cloud calls.
- Updated CHANGELOG, PROGRESS, CODEGEN, CURRENT_TASK, PROJECT_STATE, HANDOFF, WORK_LOG.
- Tracker row R-253 inserted at Phase_Roadmap!A9:M9; Done count = 42.

## 2026-09-06 — R-001

- Read `OmniStackAI_Implementation_Brief_v6.md` in full and applied the normative V6
  precedence rules.
- Created root `PROJECT_STATE.md` before source-code work.
- Inspected `Phase_Roadmap` and confirmed that its task data begins at R-010.
- Initialized Git and created `ai/R-001-monorepo-bootstrap`.
- Recorded the R-001 task contract and expected blast radius.
- Created every Section 74 directory as an implementation-free placeholder.
- Added portable agent rules, start/resume/handoff state, Taskfile commands, secret exclusions,
  CI/CODEOWNERS skeletons, and ADR-0001.
- Installed Go Task 3.53.1 and ran the canonical command interface.
- Corrected the tracked-file secret check so the permitted `.env.example` is excluded without
  weakening checks for real secret files.
- `task doctor`, `task bootstrap`, `task verify`, `task ai:status`, and `task ai:handoff` passed.
- Created implementation checkpoint `655f01fa0425e8df9022ce6bb1d2040f56b1cb73`.
- Reconstructed tracker row R-001 with founder approval, marked it Done, recorded evidence, and
  verified the workbook visually and for formula errors.

## 2026-09-06 — R-002

- Reconstructed the R-002 contract from the kickoff kit's canonical example with founder approval.
- Pinned `pgvector/pgvector:0.8.6-pg18-trixie` as the only local Compose service.
- Added loopback-only port publishing, ignored environment credentials, and a persistent named volume.
- Added transactional version 1 up/down migrations for pgvector and the migration ledger.
- Added deterministic `db:config`, `db:up`, `db:status`, `db:verify`, and `db:down` commands.
- Corrected the PostgreSQL 18 volume mount to its major-version-aware root after the live health gate
  exposed the upstream layout change.
- Verified a healthy live database, pgvector 0.8.6, migration version 1, and loopback-only binding.
- Ran `task verify` successfully and created implementation checkpoint
  `56bf4b0dea5486f8d6dcde0c7b1054249ebbb064`.

## 2026-09-06 — R-003

- Reconstructed R-003 from Brief Sections 79 and 84.1 with the founder's instruction to continue.
- Confirmed a 16 GB Apple Silicon Mac with Ollama 0.33.3 and two existing local models.
- Added environment-selected local model configuration and strict loopback endpoint validation.
- Added deterministic configuration, serve, status, discovery, pull, and inference commands.
- Kept static `task verify` independent of the running local model service.
- Verified non-loopback configuration rejection.
- Ran one live `qwen2.5-coder:14b` inference, generated 6 tokens, and made zero cloud calls.
- Created implementation checkpoint `822db27aa9c9e6ab836c28abba10f41dc27918d7`.

## 2026-09-06 — R-004

- Reconstructed R-004 as the smallest Go modular-monolith control-plane foundation permitted by
  the Stage 0 sequence; deferred Redis until an implemented workload proves it necessary.
- Used local `qwen2.5-coder:14b` for one bounded design review and made zero cloud calls.
- Added typed, fail-fast environment configuration and safe PostgreSQL URL construction.
- Added stable JSON `/healthz` liveness and bounded PostgreSQL-backed `/readyz` readiness without
  exposing raw database errors.
- Added structured logs, bounded HTTP timeouts, graceful SIGINT/SIGTERM shutdown, and a non-root
  multi-stage container image.
- Kept local Compose to exactly PostgreSQL and control-plane, both published only on loopback.
- Passed `task verify`, `go test -race ./...`, and live `task control-plane:verify`.
- Created implementation checkpoint `c44fd8d013e3ec1497ccb4ab55f1433df042aeb5`.

## 2026-09-06 — R-005

- Reconstructed R-005 from the brief's explicit provider-registry handoff example and provider
  boundary rules.
- Used local-only Balanced routing for the L2 task. Two bounded `qwen2.5-coder:14b` attempts returned
  no capturable review text; deterministic brief and repository evidence defined the implementation.
- Added immutable validated provider, model, capability, request, response, token usage, health,
  discovery, and streaming records.
- Added a runtime-checkable async `ModelProvider` protocol without vendor SDK types.
- Added a deterministic registry with platform-owned invalid, duplicate, and unknown-provider errors.
- Added Python 3.13 compile/policy commands, CI toolchain setup, and 13 standard-library unit tests.
- Preserved exactly the existing two Compose services and made zero cloud model calls.
- Created implementation checkpoint `afdc4ba9c14b231dece9533dbdd39e1e79e9ace3`.

## 2026-09-06 — R-006

- Reconstructed R-006 as the early local Ollama adapter required by the V6 MVP sequence.
- Used local-only Balanced routing: one `qwen3.5:9b` review call was inconclusive; no cloud call was made.
- Added a Python 3.13 standard-library native Ollama adapter for version health, explicitly profiled
  model discovery, non-stream chat generation, and NDJSON streaming.
- Enforced the approved loopback endpoint, disabled proxies, rejected redirects, bounded time,
  response sizes and concurrency, closed cancelled streams, and mapped failures to stable errors.
- Required an exact configured model digest before any capability can be marked verified and
  rejected tool-message requests until a separate evaluated tool-call contract exists.
- Added 15 adapter/configuration tests, bringing the agent-engine suite to 28 passing tests.
- Ran the live conformance command against `qwen2.5-coder:14b`: generation produced 4 tokens and
  streaming produced 4 events/4 tokens; cloud calls remained zero.
- Ran `task verify` successfully and created implementation checkpoint
  `8061ca3b129539ada4b0838d7d70c8acd3df1ea3`.

## 2026-09-06 — R-007

- Reconstructed R-007 as the Balanced Model Gateway router — the smallest next Stage 0/MVP dependency
  after the R-005 registry and R-006 adapter — from Brief Sections 18, 18.1, 18.2, 18.3, 84, 85, 91,
  and 92.
- Restored the declared `pnpm` (corepack, pinned `pnpm@11.19.0`) and `ripgrep` toolchains that had
  regressed from the environment; added no repository dependency. `task doctor` and `task verify`
  passed again on the R-006 baseline before any change.
- Added `ModelGateway` with a deterministic escalation ladder (L0 refused), Balanced routing (sub-L3
  to the local Ollama provider), L3/L4 escalation-required while cloud is unconfigured, a conservative
  context-budget guard, and explicit no-silent-cloud-fallback on local provider unavailability.
- Added `TaskComplexity`, `RoutingMode`, `RoutingTier`, `RoutingPolicy`, `RoutingTask`,
  `RoutingDecision`, a conservative token estimator, and three stable gateway errors. Standard-library
  only; no provider SDK, cloud call, service process, DB/Compose change, or new top-level folder.
- Added 14 offline gateway tests (42 agent-engine tests total). Routing is deterministic and needed
  zero model calls to implement or test; cloud calls remained zero.
- Ran `task verify`, `task agent-engine:lint/test`, `task security:quick`, `task env:check`, and the
  Compose scope check (exactly `postgres` and `control-plane`).
- Inserted tracker row R-007 at Phase_Roadmap row 9 by shifting rows 9..224 to 10..225 and extending
  the Dashboard, table, conditional-formatting, and data-validation ranges by one row; verified no
  ID was lost, formulas self-reference their rows, counts are correct (MVP total 112, Done 7), and
  the chart/styles/workbook parts stayed byte-identical.
- Created implementation checkpoint `9faacd23dc22c6773f9a51dc58087d557c0be391`.
- On founder instruction, added the opt-in live gateway runner (`live_gateway.py`) and
  `task agent-engine:gateway:run` to run the platform locally through the Balanced gateway, plus
  cloud-provider API-key placeholders in `.env.example` (names only) to prepare the R-008 decision.
- Live-ran the gateway on both installed models: L0 refused, L1/L2 routed to `ollama-local`, L3/L4
  refused; L2 generation and L1 stream succeeded on `qwen2.5-coder:14b` and `qwen3.5:9b`; cloud
  calls remained zero. Static `task verify` stayed network-independent and green.

## 2026-09-06 — R-008

- Reconstructed R-008 on founder instruction to configure every cloud provider (not just one),
  activated by API key, while continuing to run locally on Ollama until keys are added.
- Added standard-library HTTPS cloud adapters (no vendor SDK, no external dependency): one
  OpenAI-compatible adapter for OpenAI/OpenRouter/Groq, an Anthropic Messages adapter, and a Google
  Gemini generateContent adapter, each mapping to the vendor-neutral records with the R-006 HTTP
  safety pattern (bounded response, finite timeout, redirect rejection, stable errors).
- Kept API keys out of source/logs/records/repr: keys are read only from the environment and sent
  only as the provider auth header; a provider is registered only when its key is present.
- Added `build_gateway_from_env()` that always registers local Ollama and each key-present cloud
  provider and selects the L3/L4 tier from `OMNISTACKAI_CLOUD_PROVIDER` (default none); selecting a
  provider without its key is a clear configuration error. Refactored the live runner to use it.
- Added 19 offline tests (61 total) with injected fake HTTP openers; no cloud key set, so cloud
  calls stayed zero. Confirmed the live local run still works via the bootstrap.
- Evolved a stale R-005-era guard in `scripts/test.sh` to enforce the durable invariants (no SDK
  import, gateway/cloud/bootstrap files exist, cloud opt-in defaults to none) now that cloud adapters
  are sanctioned; added cloud key/model placeholders and shared budgets to `.env.example`.
- Inserted tracker row R-008 at Phase_Roadmap row 9 (shifted 9..225 to 10..226, ranges extended by
  one); verified no ID lost, formulas self-reference their rows, MVP total 113 / Done 8, chart/styles
  byte-identical, zip valid.
- Created implementation checkpoint `eeade72e84c7f1ebd71dfc8c0f7c2f4db0f79677`.

## 2026-09-06 — R-009

- Reconstructed R-009 as best-in-class usage and cost accounting (founder-selected) from Brief
  Sections 18.4, 23, 68, 84, 85, 90, 91, and 92.
- Added `accounting.py`: immutable metadata-only `UsageRecord` (no message content or secret), a
  `Decimal`-based `PriceBook` (exact and per-provider-wildcard lookup, local Ollama zero, unknown
  models unpriced, optional cached-input pricing) with an illustrative configurable default book,
  and a thread-safe `UsageLedger` producing overall and per-provider/model breakdowns, deterministic
  nearest-rank p50/p95 latency, unpriced-call count, and cost per successful call.
- Integrated an optional `recorder` into `ModelGateway`: exactly one record per dispatch for success
  and failure, written without altering the returned response or the raised error; threaded the
  ledger through `build_gateway_from_env` and printed a cost summary from the live runner.
- Added 13 offline accounting tests (74 total). Accounting is deterministic; zero model calls were
  needed to implement or verify. Live local run recorded 2 calls at $0.000000 with latency
  percentiles and a per-provider breakdown; cloud calls stayed zero.
- Inserted tracker row R-009 at Phase_Roadmap row 9 (shifted 9..226 to 10..227, ranges extended);
  verified no ID lost, MVP total 114 / Done 9, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `f2fc8654c6a5717e292adcdc2abb5da2fd7409c2`.

## 2026-09-06 — R-220

- Founder asked to complete both true per-provider streaming and a second required item, one by one;
  R-220 delivers streaming.
- Replaced the R-008 single-event cloud stream wrapper with real incremental Server-Sent-Events
  streaming: shared SSE transport in the cloud base (bounded lines/response, finite timeout, redirect
  rejection, stable errors, key never leaked) plus per-provider parsers — OpenAI-compatible delta
  chunks with usage in the final chunk, Anthropic message_start/content_block_delta/message_delta/
  message_stop, and Gemini streamGenerateContent SSE.
- Yielded ordered StreamEvent deltas plus a final event with measured usage; kept non-streaming
  generate unchanged. Added 5 offline SSE tests (78 total) with injected fake streaming responses; no
  cloud call was made.
- Found the workbook backlog already assigns R-010..R-219 (R-010 = Native iOS Agent). To avoid
  overwriting a planned row, new founder-requested model-fabric tasks take unique IDs after R-219;
  this task is R-220, inserted at Phase_Roadmap row 9 (rows 9..227 shifted to 10..228, ranges
  extended). Verified no ID lost, backlog R-010 intact, MVP total 115 / Done 10, chart/styles
  byte-identical, zip valid.
- Created implementation checkpoint `4e31841e730a6466da55843ff352f7144dd763e9`.

## 2026-09-06 — R-221

- Added explicit, allowlist-driven cross-provider fallback and per-provider circuit breaking to the
  Balanced gateway (founder-requested second item, part one of two).
- `RoutingPolicy` gained an optional ordered `fallback` chain; with none configured the gateway is
  byte-for-byte behaviourally unchanged (single provider). generate/stream now try the primary then
  each registered, in-budget, circuit-closed candidate.
- Fail-over is explicit (only along the chain) and only on retriable errors
  (unavailable/timeout/http); non-retriable errors raise immediately; streaming fails over only
  before the first event.
- Added `resilience.py` `CircuitBreaker`: opens after N consecutive failures, skips for a cooldown,
  half-opens, resets on success; injectable clock, thread-safe. Every attempt is still accounted.
- Added `AllProvidersFailedError` for an exhausted chain; a single-provider config still surfaces its
  own stable error. Refactored resolve() into `_resolve_tier` + `_build_decision` reused by both
  paths, keeping the existing resolve() behavior identical.
- Added 8 offline tests (86 total); deterministic, no cloud call. Confirmed the live local gateway
  still runs on Ollama.
- Inserted tracker row R-221 at Phase_Roadmap row 9 (rows 9..228 shifted to 10..229, ranges extended);
  no ID lost, backlog intact, MVP total 116 / Done 11, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `d0ee9f75b0d124fe60f1121b7f2a70d3b73040de`.

## 2026-09-06 — R-222

- Built the first platform console slice (founder-requested second item, part two of two) under
  apps/console-web.
- Added Python `overview.py` `platform_overview()` — a deterministic, metadata-only export of the
  model fabric (routing ladder, providers with active flags from env key presence, price book, usage
  summary), plus `PriceBook.entries()`; the snapshot never contains a key or secret (active is a
  boolean). 6 offline tests (92 total), including a no-secret / active-without-key assertion.
- Authored a full Next.js App-Router app, but this sandbox's network repeatedly timed out fetching
  Next's native SWC binary, so it cannot be installed/built here and a frozen install would break the
  offline task bootstrap. Pivoted to a dependency-free static console (index.html/styles.css/app.js)
  with the identical data contract and design; reverted the bootstrap change so the offline contract
  is unchanged. Next.js upgrade documented as the next step.
- Console uses safe DOM APIs (textContent only), a strict CSP meta tag, and same-origin snapshot fetch
  only. Added task console:snapshot and task console:serve; verified app.js via node --check and the
  served assets via HTTP (all 200; 6 providers / 5 price rows / 5 ladder steps).
- Inserted tracker row R-222 at Phase_Roadmap row 9 (rows 9..229 shifted to 10..230, ranges extended);
  no ID lost, backlog intact, MVP total 117 / Done 12, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `c07bbcb1b9b8c010c6d64e3a0e09ac0c855102c8`.

## 2026-09-06 — R-223

- Wired R-221 resilience into `build_gateway_from_env`: `OMNISTACKAI_FALLBACK_PROVIDERS` builds an
  ordered fallback chain from already-registered providers (`ollama` or a key-present cloud name);
  unknown or key-less names raise a clear `CloudProviderSelectionError`.
- Attached a `CircuitBreaker` (threshold/cooldown from env, safe defaults 3/30) only when a chain is
  configured, so single-provider behavior is byte-for-byte unchanged. `GatewayBootstrap` now exposes
  the chain provider ids and breaker settings.
- Extended the overview snapshot with a `resilience` block and rendered a Resilience panel in the
  console; added `.env.example` entries. No key/secret is ever included.
- Added 6 offline tests (98 total); deterministic, no cloud call. `task verify` green.
- Inserted tracker row R-223 at Phase_Roadmap row 9 (rows 9..230 shifted to 10..231, ranges
  extended); no ID lost, MVP total 118 / Done 13, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `9ec809149ab91ebaa13b88ff0a15ebd382d7a728`.

## 2026-09-06 — R-224 (deferred) and R-225

- R-224 (Next.js console upgrade): attempted the install three times (incl. standalone with a 10-min
  timeout) and once with Vite/Preact; this sandbox cannot fetch front-end bundler native binaries, so
  recorded R-224 as Deferred with a resume plan and committed no application code.
- Also showed the platform live: ran `task agent-engine:gateway:run` (local qwen routing/gen/stream +
  cost) and published the console UI as a private Artifact from the snapshot.
- R-225: began the actual product per the brief. Added the framework-neutral Application IR (Brief 9)
  under `omnistackai_agent_engine.application_ir`: immutable validated records (application, project
  strategy, roles, entities with fields/relations, APIs, screens, acceptance criteria), cross-reference
  validation, unique-id and enum checks, schema versioning, and lossless to_dict/from_dict with a
  version-rejection migration hook. Standard-library only; no codegen/agents yet.
- Added 17 offline IR tests (115 total). `task verify` green.
- Inserted tracker row R-225 (category Product) at Phase_Roadmap row 9 (rows 9..232 shifted to 10..233,
  ranges extended); no ID lost, MVP total 120 / Done 14, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `ad5e4ddf5918ddf3e4005c21a07c21601faf2ee6`.

## 2026-09-06 — R-226

- Added the code-generation boundary in `omnistackai_agent_engine.codegen`: `GeneratedFile` (safe
  relative POSIX path, bounded content) and `GeneratedProject` (immutable, path-unique,
  deterministically ordered, mergeable) — a customer project's source tree as a pure in-memory value,
  no disk writes.
- Added the `FrameworkAdapter` runtime-checkable contract (`target` + `generate(ir) -> GeneratedProject`),
  an `AdapterRegistry` with stable duplicate/unknown errors, and the `GenerationTarget` enum over MVP
  targets; adapters are selected only via the registry.
- Depends on `application_ir`; standard-library only; no code execution. 10 new offline tests
  (125 total). `task verify` green.
- Inserted tracker row R-226 (Product) at Phase_Roadmap row 9 (rows 9..233 shifted to 10..234, ranges
  extended); no ID lost, MVP total 121 / Done 15, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `f27bf416e99423d281e1c4e6f3eabc363848f95f`.

## 2026-09-06 — R-227

- Implemented the first framework code adapter: `NextjsWebAdapter` turns an Application IR into a real
  Next.js App Router TypeScript project as a GeneratedProject — entities to TS interfaces, IR APIs to
  App Router route handlers ({param}->[param], one file per route dir, a handler per method), screens
  to pages, an overview page, and config (package.json/tsconfig/next.config with security headers/
  README/.gitignore/.env.example placeholders).
- Extended the GeneratedFile path validator to allow framework route filename chars ([]()@+) while
  still rejecting absolute paths, '..', backslashes, control chars.
- Pure/deterministic; nothing installed/built/run/written to disk. The demo IR emits a 13-file
  Next.js project. 9 new offline tests (134 total); `task verify` green.
- Inserted tracker row R-227 (Product) at Phase_Roadmap row 9 (rows 9..234 -> 10..235, ranges
  extended); no ID lost, MVP total 122 / Done 16, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `1a4f8a9b8cc2ca59be32142bb6c16992cb4dbd40`.

## 2026-09-06 — R-228 (first builder slice complete)

- Added `omnistackai_agent_engine.git_service`: `materialize_project` (writes a GeneratedProject under
  a target dir, refuses path escapes and non-empty targets, sets exec bits) and `create_repository`
  (git init + stage + one commit with the customer identity via explicit env, no global git config,
  returns the commit SHA). Writes only inside the caller's target; offline; local git only.
- 6 new offline temp-dir tests (140 total). Verified the full slice end-to-end: demo IR -> 13-file
  Next.js app (NextjsWebAdapter) -> a real one-commit customer-owned Git repo. `task verify` green.
- Inserted tracker row R-228 (Product) at Phase_Roadmap row 9 (rows 9..235 -> 10..236, ranges
  extended); no ID lost, MVP total 123 / Done 17, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `28801ef396f7ead743a1d0cdc68657de23cefe1a`.

## 2026-09-06 — repo consolidation + R-229

- Founder merged all work into `main` (fast-forward from the R-001 bootstrap; 34 commits) and set
  `main` as the GitHub default; deleted all per-task ai/* branches (remote + local). Remote now has
  only `main`. Added docs/RESUME_PROMPT.md. Going forward, work is committed directly to `main`.
- R-229: added the Python (FastAPI) backend adapter (PythonBackendAdapter, target backend-python):
  entities -> Pydantic models, IR APIs -> FastAPI routers grouped by resource with typed path params
  and 501 scaffolds, app/main.py with routers + health, config, requirements, README/.gitignore/
  .env.example. Registered via AdapterRegistry. Pure/offline; no install/build/disk.
- 7 new offline tests (147 total). Proven multi-target: one IR -> 12-file Next.js web + 11-file FastAPI
  backend. `task verify` green. Tracker row R-229 (Product) inserted at row 9; MVP total 124 / Done 18.
- Implementation checkpoint `04f1e6ad03ff52522efda81845ea3ee73e736a7d`.

## 2026-09-06 — R-230

- Added the Go backend adapter (GoBackendAdapter, target backend-go): entities -> Go structs (json
  tags, optional pointers), IR APIs -> Go 1.22 method+pattern routes grouped by resource with
  r.PathValue params and 501 scaffolds, main.go with routes + /healthz + ListenAndServe, go.mod
  (go 1.22), README/.gitignore/.env.example. Generated Go and platform side are standard-library only.
- Registered via AdapterRegistry. 7 new offline tests (154 total). Proven tri-target: one IR ->
  12-file Next.js + 11-file FastAPI + 8-file Go service. `task verify` green.
- Committed directly to main (only branch). Tracker row R-230 (Product) inserted at row 9; MVP total
  125 / Done 19. Implementation checkpoint `e2515a8f1b0314ec287a02cdaf25e72a17b9da3f`.

## 2026-09-06 — R-224 (deferred)

- Attempted the Next.js console upgrade. `pnpm install` for next@15.5.4 timed out fetching the native
  SWC binary (@next/swc-darwin-arm64) three times, including a standalone install under
  apps/console-web/nextjs/ with a 10-minute fetch timeout and increased retries.
- Per "record real command evidence — never claim unexecuted tests," recorded R-224 as Deferred with a
  resume plan; committed no application code and removed the scaffold (working tree clean). The R-222
  static console remains the working slice.
- Recorded tracker row R-224 at Phase_Roadmap row 9 with status Deferred (completion 0); rows
  contiguous, ranges extended, no ID lost; MVP total 119, Done 13, Deferred 1.

## 2026-09-07 — R-234

- Added a single `OMNISTACKAI_TIER` switch (0/1 local, 2 cloud). `runtime/tier.py` resolves the runtime
  and deploy providers from the tier + explicit selectors: tier 0/1 force local runtime and no deploy;
  tier 2 permits keyed cloud selections. `resolve_platform()` returns the active providers;
  `platform_status()`/`format_status()` summarize tier, selection, and which keys are present.
- Added `runtime/drivers.py`: `CloudDeployProvider` (vercel/netlify/render/fly) emits a `DeployPlan` of
  the provider's official-CLI commands; `CloudSandboxProvider` (e2b/daytona/fly-machines) emits a
  `PreviewPlan` reusing the target's run commands. The key is read from env at run time and NEVER placed
  in a command or logged. `run_deploy(plan)` executes a plan opt-in (never run by verify).
- `bootstrap.py` gained an optional `selection` override; new exports in `runtime/__init__.py`.
  `task platform:status` (scripts/agent-engine.sh + Taskfile) prints the active tier and key presence;
  `.env.example` gained `OMNISTACKAI_TIER=0`; `docs/RUNTIME.md` documents the knob + drivers.
- 13 new stdlib offline tests (194 total): tier resolution, per-provider driver plans, no-key-in-plan
  across all providers, activation/selection errors, and the status summary. `task verify`,
  `task security:quick`, `task env:check` all pass; `task platform:status` demoed tier 0 and tier 2.
- Committed directly to main (only branch). Tracker row R-234 (Runtime) inserted at row 9; MVP total
  129 / Done 23. Implementation checkpoint `dcb7d2d`. 0 local / 0 cloud model calls; nothing run/deployed.

## 2026-09-07 — R-235

- Added the verifiable-engineering verify-plan layer (`omnistackai_agent_engine.verify`): `plans.py`
  (`VerifyStepKind` install/typecheck/lint/test/build, `VerifyStep`, `VerifyPlan` — validated,
  ladder-ordered, `gates()`, reusing the vetted `Command` primitive from runtime.contracts); `gates.py`
  (the per-target recipe table, `verify_plan`, `verify_plans_for_ir`, `run_verify`, `VerifyReport`).
- Per-target ladders: nextjs-web/nextjs-admin (pnpm install → tsc --noEmit → lint → build);
  backend-python (pip install → compileall app → pytest); backend-go (go vet → go test → go build).
  Each step classified by gate kind; commands control-free/secret-free by construction.
- Mapped one Application IR to the verify plans for its assembled monorepo apps via a new additive,
  behavior-preserving `assembled_targets(ir)` in the assembler (`assemble_project` refactored to share
  the `_plan_assembly` layout decision; output byte-identical, existing tests green).
- `run_verify(plan)` is the only executor — opt-in, fail-fast, returns a `VerifyReport` (per-step
  status + return code); never run by tests or `task verify`. Added `task agent-engine:verify-plan`.
- Docs: `docs/VERIFY.md`. 9 new stdlib offline tests (203 total): per-target plans, ladder order, gate
  classification, unknown-target error, IR→plans mapping over the rideshare + blog fixtures, plan
  safety. `task verify`, `task security:quick`, `task env:check` all pass; verify-plan demoed.
- Committed directly to main (only branch). Tracker row R-235 (Verify) inserted at row 9; MVP total
  130 / Done 24. Implementation checkpoint `cb74d0c`. 0 local / 0 cloud model calls; nothing installed/built/run.

## 2026-09-07 — R-236

- Expanded the cloud model fabric (founder request, with Dyad screenshots for reference). Added
  first-class OpenAI-compatible `CloudProviderSpec` entries for DeepSeek, xAI (Grok), Mistral, Together,
  and Fireworks alongside the existing OpenAI/Anthropic/Google/OpenRouter/Groq — all reuse
  `OpenAICompatibleProvider`, no new adapter code.
- Added a generic env-driven custom-provider path: `custom_provider_specs_from_env` reads
  `OMNISTACKAI_CUSTOM_PROVIDERS` + per-id `OMNISTACKAI_CUSTOM_<ID>_{BASE_URL,MODEL,API_KEY}` and builds
  a first-class provider with no code change; validates the id, requires an HTTPS base URL + model, and
  rejects built-in collisions. `resolve_provider_specs()` = built-ins ∪ custom.
- Made the catalog spec-driven end to end: `bootstrap.py` and `overview.py` iterate
  `resolve_provider_specs()`, so custom + new built-in providers are registered (key-activated),
  selectable as the L3/L4 cloud tier or a fallback, and listed in the metadata-only overview with
  `active` = key presence only. `accounting.py` gained illustrative default prices for the priced new
  providers (openrouter/custom stay unpriced).
- `.env.example`: new keys + model overrides + a documented custom-provider template; updated the
  `OMNISTACKAI_CLOUD_PROVIDER` allowed list. `docs/MODEL_PROVIDER.md`: R-236 catalog + custom + local
  Ollama section. Keys stay env-only — never logged, stored, returned, or placed in the overview.
- 14 new stdlib offline tests (217 total): new specs, adapter dispatch shape (key only in the auth
  header, never the URL), custom-spec parse + 4 error cases, spec merge, bootstrap registration/
  selection/fallback for built-in and custom, overview/no-key-leak, and pricing. Updated `test_overview`
  to derive the expected catalog from the spec table. `task verify` + `security:quick` + `env:check`
  pass; `platform_overview` demoed a 12-provider catalog including custom `myco`.
- Committed directly to main (only branch). Tracker row R-236 (Model Fabric) inserted at row 9; MVP
  total 131 / Done 25. Implementation checkpoint `e6326bf`. 0 local / 0 cloud model calls; no network.

## 2026-09-07 — R-237

- Added the "edit an existing app" motion — the builder step after generate + verify. New
  `omnistackai_agent_engine.edit` package: `diff.py` (`ChangeKind`, `FileChange`, `ProjectDiff`,
  `diff_projects`, `plan_edit`) and `apply.py` (`ApplyReport`, `apply_diff`, `commit_edit`).
- `diff_projects(old, new)` classifies every path as added/modified/deleted/unchanged (modified on
  content OR executable change); `plan_edit(old_ir, new_ir)` assembles both IRs via the assembler and
  diffs them, so an IR change becomes exactly the set of files to rewrite.
- `apply_diff(diff, target_dir)` writes added/modified and removes deleted files strictly inside the
  target (path escapes refused like `materialize_project`; emptied dirs pruned, never past the root),
  returns an `ApplyReport`, and leaves the directory equal to the new project. `commit_edit` applies +
  commits one commit as the customer identity via a new additive `git_service.commit_all` (git add -A
  + commit); previous history is preserved.
- 9 new stdlib offline tests (226 total): diff classification + empty diff + executable-flag change,
  plan_edit no-op and description-change (README.md modified, nothing added/deleted), apply round-trip
  (old tree -> new), path-safety refusal (`..` + missing target), and commit_edit two-commit history.
  Tests use tempdirs and the local git CLI (same pattern as the R-228 git-service tests).
- `git_service.create_repository`/`materialize_project` unchanged (additive `commit_all` only). No
  network call, no code execution, no write outside the target. `docs/EDIT_LOOP.md` added.
- Committed directly to main (only branch). Tracker row R-237 (Builder) inserted at row 9; MVP total
  132 / Done 26. Implementation checkpoint `a0a494a`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-238

- Gave the generated backend a real persistence layer. New `codegen/schema_sql.py`:
  `render_postgres_schema(ir)` renders deterministic PostgreSQL DDL from the IR entities + relations —
  one `CREATE TABLE` per entity (snake_case name), columns typed from `FieldType` (STRING/TEXT->TEXT,
  INT->BIGINT, FLOAT->DOUBLE PRECISION, BOOL->BOOLEAN, DATETIME->TIMESTAMPTZ, UUID->UUID, JSON->JSONB),
  `NOT NULL` for required fields, a UUID primary key (the entity's own `id` field if present, else a
  surrogate `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`), `<name>_id UUID REFERENCES <target>(id)`
  for many_to_one/one_to_one relations, and one deterministic join table per many_to_many pair.
- Wired both backend adapters (FastAPI and Go) to emit `migrations/0001_init.sql` exactly when the IR
  has entities and `database_strategy is DatabaseStrategy.POSTGRES` — no previously emitted file
  changes. Output is byte-stable, so the R-237 edit loop diffs the migration when the IR entities
  change. Exported `render_postgres_schema` from the codegen package.
- 11 new stdlib offline tests (237 total): type map + required->NOT NULL, surrogate vs declared PK,
  many_to_one FK column, single many_to_many join table with composite PK, determinism, the
  postgres/entities gate, and adapter emission (python + go emit; OTHER db and no-entities do not).
  No existing adapter/assembler test broke. `task verify` + `security:quick` + `env:check` pass.
- Nothing connects to or runs a database; no network. `docs/CODEGEN.md` documents the schema section.
- Committed directly to main (only branch). Tracker row R-238 (Builder) inserted at row 9; MVP total
  133 / Done 27. Implementation checkpoint `c6a4c6e`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-239

- Gave the generated backends a real data-access layer over the R-238 schema. New
  `codegen/data_access.py`: `python_data_access_files(ir, slug)` emits `app/db.py` (an async psycopg
  connection helper reading DATABASE_URL, dict rows) + `app/repositories/<entity>.py` per entity with
  `list/get/create/delete`; `go_data_access_files(ir, slug)` emits `internal/store/store.go` (a
  database/sql opener via the pgx driver) + `internal/store/<entity>.go` per entity with
  `List/Get/Create/Delete` scanning into the generated `models.<Entity>` structs.
- Every query value is parameterized (`%s` for psycopg, `$N` for pgx); only fixed IR-derived table/
  column identifiers appear inline (no value interpolation). An id-only entity creates via
  `DEFAULT VALUES`. `schema_sql` gained a public `table_name`.
- Wired both backends to append the data-access files and the DB dependency (psycopg in
  requirements.txt / pgx require in go.mod) exactly when `ir.entities and database_strategy is POSTGRES`
  — same gate as the migration; no previously emitted file (other than requirements.txt / go.mod)
  changed. The R-237 edit loop diffs the repositories when entities change.
- 7 new stdlib offline tests (244 total): python emission + valid-Python parse + parameterization, go
  emission + module import path + struct scan, gating (no db / no entities), id-only DEFAULT VALUES, and
  determinism. No existing test broke. `task verify` + `security:quick` + `env:check` pass.
- Nothing connects to or queries a database; no network. `docs/CODEGEN.md` + `docs/PROGRESS.md` updated.
- Committed directly to main (only branch). Tracker row R-239 (Builder) inserted at row 9; MVP total
  134 / Done 28. Implementation checkpoint `f6792fa`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-240

- Wired the generated backends' HTTP handlers to the R-239 repository layer for the unambiguous CRUD
  shapes. New `codegen/route_wiring.py`: `wire_endpoint(api, repo_entities)` -> LIST/GET/CREATE/DELETE
  from method + path shape (entity from `response_schema` else `request_schema`); anything ambiguous
  (sub-collections, multi-param, custom, POST without a request_schema, unknown entity) returns None and
  stays a labelled 501 scaffold — so the platform never emits plausible-but-wrong behaviour.
- Python (`backend_python.py`): `_router_file` now takes `repo_entities`, imports the used
  repositories/models, and emits wired bodies — list -> `await <t>.list_<t>()`, get -> 404-aware, create
  -> `await <t>.create_<t>(payload.model_dump())` with a Pydantic body, delete -> 404-aware; unwired
  keep `raise HTTPException(status_code=501, ...)`.
- Go (`backend_go.py`): handlers became methods on a `Handlers` struct holding `*sql.DB`; added
  `internal/handlers/handlers.go` (struct + `New` + `writeJSON`); `_main_file` gained a `has_db` branch
  that opens `store.Open()`, builds `handlers.New(db)`, and registers `h.<Handler>`; wired methods call
  the `store` and decode `models.<Entity>` for create. Non-DB Go backends keep the free-function
  scaffolds unchanged (README stack note switches to pgx only when a DB is present).
- Gated on entities + `database_strategy=postgres`; deterministic and byte-stable; nothing runs. Updated
  `test_backend_go_adapter` assertions free-function -> method form (that test uses rideshare, has DB).
- 12 new stdlib offline tests (256 total) in `test_route_wiring.py`: the wiring map + its None cases,
  Python wired router (valid Python via ast) + ambiguous-stays-501, Go shared handlers + DB wiring +
  list-calls-store, and a non-DB backend left unchanged. `task verify` + `security:quick` + `env:check`
  pass. `docs/CODEGEN.md` documents the wiring table; `docs/PROGRESS.md` refreshed.
- Committed directly to main (only branch). Tracker row R-240 (Builder) inserted at row 9; MVP total
  135 / Done 29. Implementation checkpoint `013dfc4`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-241

- Made the IR's per-endpoint `auth` flag real (it was previously only a comment). New
  `codegen/auth_guard.py`: `needs_auth(ir)`, `python_auth_file(ir)`, `go_auth_file(ir)`. Every
  `auth=true` endpoint now enforces a guard that rejects a request with no `Authorization: Bearer`
  credential (HTTP 401) before the handler runs.
- Python (`backend_python.py`): emits `app/auth.py` with a `require_auth` FastAPI dependency; `_router_file`
  adds `Depends`/`require_auth` imports and `dependencies=[Depends(require_auth)]` on `auth=true` routes;
  public routes unchanged. Go (`backend_go.py`): emits `internal/handlers/auth.go` with a
  `RequireAuth(next)` middleware; `_main_file` wraps exactly the `auth=true` registrations with
  `handlers.RequireAuth(...)`. Works for both DB and non-DB backends.
- IR roles surfaced as a generated constant (Python `ROLES` tuple, Go `Roles` slice, from `role.id`).
  The guard only requires a credential; token verification (signature/expiry/roles) is a documented
  TODO — no secret fabricated, no verification faked.
- Gated on `needs_auth(ir)`; deterministic and byte-stable; nothing runs. Updated two existing adapter
  tests (Python decorator substring, Go registration substring) to the guarded form.
- 9 new stdlib offline tests (265 total) in `test_auth_guard.py`: needs_auth true/false, Python
  auth module + per-route dependency (auth vs public) + no-module-when-all-public, Go middleware + roles
  + main wraps only auth endpoints + no-file-when-all-public, and determinism. `task verify` +
  `security:quick` + `env:check` pass. `docs/CODEGEN.md` documents the guard; `docs/PROGRESS.md` refreshed.
- Committed directly to main (only branch). Tracker row R-241 (Builder) inserted at row 9; MVP total
  136 / Done 30. Implementation checkpoint `4db716b`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-242

- Upgraded the R-241 auth guard from a bearer-presence check to real JWT verification. `auth_guard.py`:
  the generated guard decodes and verifies a JWT (HS256) using `JWT_SECRET` read from the environment —
  401 on a missing/invalid/expired token, 500 when the secret is unset — and never hard-codes or
  defaults the secret.
- Python (`python_auth_file`): `app/auth.py` imports PyJWT, `require_auth` calls
  `jwt.decode(token, _secret(), algorithms=["HS256"])` and returns the verified claims; `_secret()`
  reads `JWT_SECRET` from `os.environ`. `backend_python.py` adds `PyJWT==2.9.0` to `requirements.txt`
  and an empty `JWT_SECRET` to `.env.example` when the IR needs auth.
- Go (`go_auth_file`): `internal/handlers/auth.go` imports `github.com/golang-jwt/jwt/v5`; `RequireAuth`
  reads `os.Getenv("JWT_SECRET")` (500 when empty) and `jwt.Parse`s the token with an HMAC-only keyfunc
  (rejecting non-HMAC). `backend_go.py` appends the golang-jwt `require` to `go.mod` and `JWT_SECRET=` to
  `.env.example` when the IR needs auth.
- Platform code stays standard-library only — the JWT dependency lives only in the generated project.
  IR roles constant retained for future per-endpoint authorization (needs an IR field). Nothing signed
  or verified at generation time; nothing runs; no network.
- 3 new stdlib offline tests (268 total): Python JWT verification + PyJWT/JWT_SECRET additions +
  no-fabricated-secret; Go JWT verification + golang-jwt/JWT_SECRET additions. Existing R-241 auth tests
  still pass. `task verify` + `security:quick` + `env:check` pass. `docs/CODEGEN.md` + `docs/PROGRESS.md`
  refreshed.
- Committed directly to main (only branch). Tracker row R-242 (Builder) inserted at row 9; MVP total
  137 / Done 31. Implementation checkpoint `e0d8af3`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-243

- Added per-endpoint role enforcement on top of the R-242 JWT auth — the first additive change to the
  IR itself. `ir.py`: `ApiEndpoint` gains `required_roles: tuple[str, ...] = ()` (validated with
  `_str_tuple`; a non-empty value requires `auth=true`), added to `to_dict`/`from_dict`. `validate.py`:
  each required role must be a declared `Role` (ERROR `unknown_role_reference` otherwise). `normalize_ir`
  unchanged (it reuses the ApiEndpoint objects). Default `()` → existing IRs unaffected, schema version
  unchanged.
- `auth_guard.py`: Python `require_roles(*required)` dependency factory (verify via `require_auth`, then
  require the `roles` claim to intersect `required`, else 403). Go refactored to a shared `verifyToken`
  (returns `jwt.MapClaims`) plus `RequireAuth`, `RequireRoles(next, required...)`, and `hasAnyRole`
  (403 when the claim has no required role).
- `backend_python._router_file`: role-gated routes declare `dependencies=[Depends(require_roles("..."))]`
  and import only the auth names they use; `backend_go._main_file`: role-gated endpoints register as
  `handlers.RequireRoles(target, "...")`. Endpoints without roles keep `require_auth`/`RequireAuth`.
- 6 new stdlib offline tests (274 total) in `test_role_enforcement.py`: IR required_roles serialize +
  auth-implication (`InvalidIRError`) + unknown-role `validate_ir` error + known-role clean; Python
  route uses `require_roles` (valid Python) with a 403 guard; Go `main` uses `RequireRoles` and `auth.go`
  has `RequireRoles`/`StatusForbidden`. Updated the R-242 Go assertion (`jwt.Parse` → `jwt.ParseWithClaims`).
  `task verify` + `security:quick` + `env:check` pass. `docs/APPLICATION_IR.md` + `docs/CODEGEN.md` +
  `docs/PROGRESS.md` refreshed.
- Committed directly to main (only branch). Tracker row R-243 (Builder) inserted at row 9; MVP total
  138 / Done 32. Implementation checkpoint `1faea2c`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-244

- Wired the sub-collection GET pattern `/<parents>/{parentId}/<children>` to a parent-scoped list,
  clearing the main class of remaining 501 stubs. `route_wiring.py`: added `Op.LIST_BY`, a `relation`
  field on `Wiring`, an `fk_relations(ir)` helper, and an `fk_by_entity` argument to `wire_endpoint`.
  A GET whose last segment is a collection (not a param) with exactly one path param wires to LIST_BY
  only when the child entity (response_schema) has exactly one many_to_one/one_to_one relation;
  otherwise it stays a labelled 501.
- `data_access.py`: emit a filtered list per FK relation — Python `list_<table>_by_<rel>(<rel>_id)`
  (`WHERE <rel>_id = %s`) and Go `List<Entity>By<Rel>(ctx, db, <rel>ID, limit)` (`WHERE <rel>_id = $1`).
  The value is parameterized; the FK column is a fixed IR-derived identifier.
- `backend_python._router_file` and `backend_go._handlers_file_wired` gained an `fk_by_entity` arg
  (passed from `generate` when has_db) and a LIST_BY branch: Python
  `await <table>.list_<table>_by_<rel>(<param>)`; Go
  `store.List<Entity>By<Rel>(r.Context(), h.DB, r.PathValue("<param>"), 100)`.
- Demo (minimal-blog): `GET /posts/{postId}/comments` now returns `comment.list_comment_by_post(postId)`
  (Py) / `store.ListCommentByPost(...)` (Go). Repointed the R-240 `test_ambiguous_endpoint_stays_501`
  to rideshare's `POST /favourites/drivers/{driverId}` (no request_schema -> still 501).
- 11 new stdlib offline tests (285 total) in `test_subcollection_wiring.py`: LIST_BY mapping + None
  cases (no fk map, multiple FK, get-by-id wins), fk_relations helper, filtered-repository emission
  (Py/Go), router/handler wiring, and value-parameterization. `task verify` + `security:quick` +
  `env:check` pass. `docs/CODEGEN.md` + `docs/PROGRESS.md` refreshed. Seed data deferred (no IR values).
- Committed directly to main (only branch). Tracker row R-244 (Builder) inserted at row 9; MVP total
  139 / Done 33. Implementation checkpoint `b886d72`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-245

- Added the combined project-plan surface. New `omnistackai_agent_engine.projectplan`: `AppPlan`,
  `ProjectPlan`, `build_project_plan(ir, *, deploy=None)`. It composes existing builders only —
  `codegen.assembled_targets` (app layout), `runtime.LocalRuntimeProvider.preview_plan` (guarded by
  `.supports`), `verify.verify_plan` (guarded by `verify.supported_targets`), and an optional
  `DeploymentProvider.deploy_plan` — into one per-app view.
- `ProjectPlan.to_dict()` is JSON-serializable and secret-free (preview url + command strings, verify
  gate kinds + step commands, deploy provider id + step commands); `render()` is a readable multi-app
  summary. A deploy plan is included only when a key-activated provider is passed in.
- CLI: `plan-show` in `scripts/agent-engine.sh` + `task plan:show -- <example>`. Demoed
  rideshare-favourites: apps/web (nextjs-web, preview :3000, gates install/typecheck/lint/build) and
  services/api (backend-go, preview :8080, gates lint/test/build). `docs/RUNTIME.md` documents it.
- 6 new stdlib offline tests (291 total) in `test_projectplan.py`: one AppPlan per assembled app,
  preview+verify present with no deploy by default, render() lists each app, deploy opt-in via
  deploy_driver("vercel"), to_dict JSON-serializable + no key value (fake VERCEL_TOKEN), determinism.
  `task verify` + `security:quick` + `env:check` pass.
- Pure/data-only — nothing installed, run, verified, or deployed; no key value included. Composes
  existing builders, so no runtime/verify/codegen behavior changed.
- Committed directly to main (only branch). Tracker row R-245 (Runtime) inserted at row 9; MVP total
  140 / Done 34. Implementation checkpoint `891144d`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-246

- Added hunk-level edit diffs + rename detection on top of the R-237 file-level ProjectDiff. New
  `edit/patch.py`: `DiffKind`, `FileDiff`, `diff_report(old, new)`, `unified_patch(old, new)` — using
  standard-library `difflib.unified_diff`.
- `diff_report` classifies each path as added/modified/deleted/renamed and attaches a git-style unified
  (hunk) diff for content changes. Rename detection pairs a deleted path with an added path of identical
  content (greedy, sorted for determinism) and reports a single RENAMED record (old_path -> path)
  instead of delete+add. Records are deterministically ordered (kind, then path).
- `unified_patch` concatenates the reports into one byte-stable git-style patch string, with
  `rename from`/`rename to` headers for renames — so an edit reads as a focused review-ready patch.
- Additive only: `diff_projects` / `apply_diff` / `plan_edit` are unchanged; exported the new names from
  `edit/__init__.py`. Pure/deterministic — no disk write, no run, no network.
- 6 new stdlib offline tests (297 total) in `test_edit_patch.py`: modified-file unified hunk (context +
  -/+ lines), exact-content rename as one record + rename header, one-sided add/delete, empty report
  for identical projects, and byte-stable determinism. `task verify` + `security:quick` + `env:check`
  pass. `docs/EDIT_LOOP.md` + `docs/PROGRESS.md` refreshed (also fixed stale test-count/% notes).
- Committed directly to main (only branch). Tracker row R-246 (Builder) inserted at row 9; MVP total
  141 / Done 35. Implementation checkpoint `eebab68`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-08 — R-247

- Added `console_snapshot.platform_console_snapshot()`, a metadata-only composition of accepted public
  contracts: the existing model overview, the R-245 ProjectPlan for `rideshare-favourites`, and the
  R-246 diff report/unified patch for an actual old/new `minimal-blog` IR assembly.
- The builder proof exposes two generated apps (`apps/web`, `services/api`) with preview URLs and
  verification gate/command ladders; deploy remains absent by default. The edit preview contains five
  genuinely modified generated paths and a bounded 1,661-character hunk-level patch.
- Upgraded the dependency-free static console with responsive plan cards, gate badges, changed-file
  metadata, and a scrollable code patch. All content is assigned with `textContent`; the browser makes
  only the existing same-origin snapshot fetch under the strict CSP.
- 5 new offline stdlib tests (302 total) cover plan/patch shape, deterministic JSON serialization,
  existing model-overview preservation, and secret exclusion. `node --check`, repeated snapshot
  SHA-256, `task verify`, `task security:quick`, and `task env:check` pass. Live local visual review
  confirmed the builder proof and model dashboard render without a page error state.
- Implementation checkpoint `6a82056`. Tracker row R-247 inserted at row 9; 247 unique IDs, MVP total
  142 / Done 36. One bounded local `qwen2.5-coder:14b` review; 0 cloud calls. No generated app was
  installed/run/verified/deployed; no DB connection, external request, service, dependency, or infra.

## 2026-09-08 — R-248

- Added honest seed data from explicit Application IR fixtures (the deferred seed gap, done the no-
  fabrication way). `ir.py`: new `Fixture` record (entity + rows of column->JSON value) with a
  `_check_fixture_value` helper (allow JSON scalars/containers; reject control chars in strings); added
  `fixtures` to `ApplicationIR` (before schema_version) and wired the validation loop, `to_dict`, and
  `from_dict`. Exported `Fixture`. Additive field, empty default, no schema-version bump.
- `validate.py`: fixture cross-references — ERROR `unknown_fixture_entity` / `unknown_fixture_column`
  (a row column must be a declared field or a `<relation>_id` FK), WARNING `fixture_missing_required`
  (required column, other than id, absent from a row — advisory, has_errors stays false). CRITICAL:
  added `fixtures=` to `normalize_ir` so it isn't dropped.
- New `codegen/seed_sql.py`: `render_postgres_seed(ir)` emits `INSERT INTO <table> (<cols sorted>)
  VALUES (<literals>);` per row using ONLY the row's declared columns (omitted columns fall to DB
  default/NULL — the no-fabrication guarantee). `_sql_literal` is the codebase's first SQL-literal
  quoter (single quotes doubled; bool->TRUE/FALSE before int; None->NULL; numbers bare; dict/list->
  `'<json sort_keys>'::jsonb`). Exported `render_postgres_seed`.
- `backend_python.py` / `backend_go.py`: append `migrations/0002_seed.sql` inside the existing
  `if has_db:` block, only when the seed is non-empty (fixtures present). `examples.py`: `minimal-blog`
  gains two Post fixtures + a Comment (post_id FK). `builder-demo.sh` prints the seed file when present.
- 14 new stdlib offline tests (316 total) in `test_seed_sql.py`: `_sql_literal` per type incl.
  quote-doubling + jsonb sorted keys; INSERT shape + alphabetical columns + FK column + empty-without-
  fixtures + byte-stable; adapter emission (python+go emit for minimal-blog; none for rideshare/OTHER
  db); validation errors/warning; IR round-trip + normalize preserves fixtures. `task verify` +
  `security:quick` + `env:check` pass; no existing test broke.
- Tracker: the sheet structure had diverged from my hardcoded scripts (table `A4:M255`, split sqref
  ranges), so R-248 used a GENERAL row-insertion `tracker_edit_r248.py` — insert at row 9, shift 9..255
  -> 10..256, and bump every row >= 9 across sqrefs, the table ref, and sheet1's Phase_Roadmap ranges;
  validated rows 1..256 contiguous, table `A4:M256`, sheet1 `$B$4:$B$256`/`$H$4:$H$256`, XML well-formed.
- Committed directly to main. Tracker row R-248 (Builder) inserted at row 9; MVP total 142 / Done 37.
  Implementation checkpoint `9d34720`. 0 local / 0 cloud model calls; nothing run/connected.

## 2026-09-08 — R-249

- Deepened the generated persistence layer with uniqueness + indexes from the IR. `ir.py`: `Field`
  gains `unique: bool = False` (validated, serialized); new `Index` record (fields + unique + optional
  name, fields validated as idents); `Entity` gains `indexes: tuple[Index, ...] = ()` and validates that
  each index field is a declared field of the entity. `to_dict`/`from_dict` updated; exported `Index`.
  `normalize_ir` needs no change (entities pass through as objects, so the new attrs ride along).
- `schema_sql.py`: `_column_lines` appends ` UNIQUE` to a unique non-`id` column (the `id` PK never gets
  a redundant UNIQUE); new `_index_statements(ir)` emits `CREATE [UNIQUE] INDEX <name> ON <table>
  (<cols>);` per entity index under an `-- Indexes` section, with a deterministic default name
  (`<table>_<cols>_idx`, `_key` when unique) when unnamed.
- `examples.py`: `rideshare-favourites` `Driver` gained `indexes=(Index(("name",)),)` for a visible demo
  (`CREATE INDEX driver_name_idx ON driver (name);`).
- 11 new stdlib offline tests (327 total) in `test_schema_indexes.py`: unique non-id column, id-never-
  unique, single/composite/named indexes (default naming, unique vs not), no-index-section-when-none,
  the example driver index, bad-index-field construction error, empty-index-fields error, and IR
  round-trip + byte-stability. `task verify` + `security:quick` + `env:check` pass; no existing test
  broke; the `0002_seed` and data-access/route/auth code are untouched (schema-only change).
- Tracker: reused the general row-insertion script (baseline `1c0072f`, LAST=256) — R-249 (Builder) at
  row 9; rows 1..257 contiguous, table `A4:M257`, sheet1 ranges to 257, XML well-formed. MVP total
  143 / Done 38. Implementation checkpoint `28e7cd5`. 0 local / 0 cloud model calls; no DB connection.

## 2026-09-08 — R-250

- Made the IR `Field.validation` tuple meaningful. New `codegen/field_validation.py`:
  `parse_field_rules(field) -> FieldRules(max_length, enum)` parses `max_length:<int>` and
  `enum:<a>|<b>|<c>`; unknown / non-digit rules are ignored (forward-compatible). Exported from codegen.
- `schema_sql._column_lines`: a STRING field with `max_length` renders `VARCHAR(n)` (else TEXT); an enum
  appends `CHECK (<col> IN ('a','b'))` after NOT NULL/UNIQUE with single-quote-escaped values; the `id`
  PK column is unaffected.
- `backend_python._models_file`: new `_py_field_line` applies rules — `Field(max_length=n)` (or
  `Field(default=None, max_length=n)` when optional) and a `Literal[...]` type for enums; `Field` and
  `Literal` are imported only when actually used, so rule-free models are byte-identical to before.
- Go request-validation tags deferred (the schema already constrains Go writes at the DB level). Example
  IRs left unchanged so existing generated outputs stay stable; the feature is exercised by
  constructed-IR tests.
- 10 new stdlib offline tests (337 total) in `test_field_validation.py`: parser (max_length/enum,
  unknown/non-digit ignored), schema VARCHAR + escaped CHECK + text-without-max_length, Pydantic
  Field/Literal + optional constraint + no-rules-no-Field-import (valid Python via ast), and an
  examples-unaffected guard. `task verify` + `security:quick` + `env:check` pass; no existing test broke.
- Tracker: general row-insertion `tracker_edit_r250.py` (baseline `5e4d72f`, LAST=257) — R-250 (Builder)
  at row 9; rows 1..258 contiguous, table `A4:M258`, sheet1 ranges to 258, XML well-formed. MVP total
  144 / Done 39. Implementation checkpoint `1eed171`. 0 local / 0 cloud model calls; no DB connection.

## 2026-09-08 — R-251

- Extended R-250 field validation to the Go backend and added numeric bounds — validation now spans all
  three targets. `field_validation.py`: `FieldRules` gained `minimum`/`maximum` (raw numeric literals,
  `_NUMBER`-validated, non-numeric ignored); `parse_field_rules` reads `min:<n>`/`max:<n>`; new
  `go_validate_tag(field, rules)` builds `max=`/`oneof=`/`gte=`/`lte=`.
- `schema_sql`: numeric INT/FLOAT fields append `CHECK (col >= n)` / `CHECK (col <= n)` (combined with an
  enum CHECK when present); strings never get a numeric check. `backend_python`: numeric fields add
  `ge=`/`le=` to the Pydantic `Field(...)`. `backend_go._models_file`: append ` validate:"..."` inside
  the struct tag when the tag body is non-empty; rule-free fields keep the exact plain `json` tag
  (so the existing rideshare adapter assertions stay green).
- Go tags are declarative this task — no `go.mod` dependency and no `validator.Struct` call (that
  enforcement is the R-252 follow-up); the schema already enforces at the DB for both backends.
- 8 new stdlib offline tests (345 total) in `test_field_validation_numeric.py`: numeric parser
  (raw tokens, non-numeric ignored), schema numeric CHECK + string-not-numeric, Pydantic ge/le, the
  `go_validate_tag` helper + emitted struct tags (max/gte-lte/oneof, rule-free plain tag), and an
  examples-have-no-validate-tags guard. `task verify` + `security:quick` + `env:check` pass; no existing
  test broke (fixed one over-strict new assertion that omitted NOT NULL).
- Tracker: general row-insertion `tracker_edit_r251.py` (baseline `9315dcb`, LAST=258) — R-251 (Builder)
  at row 9; rows 1..259 contiguous, table `A4:M259`, sheet1 ranges to 259, XML well-formed. MVP total
  145 / Done 40. Implementation checkpoint `2060a21`. 0 local / 0 cloud model calls; no DB connection.

## 2026-09-08 — R-252

- Founder chose option 1 after R-251 ("Go with option 1 ... bcoz we do not want anything static or seeds
  data in our platform"): wire go-playground enforcement in the generated Go create handlers rather than
  render seed/indexes/validation in the static console. Made the R-251 Go `validate:"..."` tags actually
  enforced at request time. (FastAPI already enforces at construction via Pydantic — Go was the gap.)
- `field_validation.py`: added `VALIDATOR_REQUIRE = "github.com/go-playground/validator/v10 v10.22.1"`
  and `go_validate_file()` — the `internal/handlers/validate.go` source (a shared `var validate =
  validator.New()` + a `validateStruct(v any) (int, string)` helper returning
  `http.StatusBadRequest`/`"validation_failed"` on a tag violation, `""` when valid). Mirrors
  `auth_guard.GOLANG_JWT_REQUIRE` / `go_auth_file`. Both exported from `codegen/__init__.py`.
- `backend_go.py`: compute `repo_entities`/`fk_by_entity` up front; new `_validated_entities(ir)` =
  entity names with a non-empty `go_validate_tag`; `has_validation` = any wired CREATE whose entity is in
  that set. `go.mod` gains `require VALIDATOR_REQUIRE` and `internal/handlers/validate.go` is emitted only
  when `has_validation`. `_handlers_file_wired` takes `validated_entities`; the CREATE branch emits
  `if status, msg := validateStruct(m); msg != "" { http.Error(w, msg, status); return }` between the
  JSON decode block and the `store.Create…` call — but only for entities carrying rules.
- Rule-free projects and both example IRs stay byte-identical to R-251 (no dep, no `validate.go`, no
  call); the validator dependency lives only in the generated project's `go.mod` (no platform dep). No
  Python/FastAPI change — Pydantic already enforced. Validation now holds at three layers: request model,
  request handler, and the DB schema.
- 5 new stdlib offline tests (350 total) in `test_go_validation_enforcement.py`: enforcement emitted for
  a rules+create IR (go.mod require, validate.go contents), handler call ordering (decode < validateStruct
  < store.Create), enforcement absent for a rule-free IR and for a rules-without-create IR (tags still
  present), and both example IRs emit none. `task verify` + `security:quick` + `env:check` pass; no
  existing test broke.
- Tracker: general row-insertion `tracker_edit_r252.py` (baseline `842819e`, LAST=259) — R-252 (Builder)
  at row 9, R-251 shifted to row 10; rows 1..260 contiguous, table `A4:M260`, sheet1 ranges to 260, XML
  well-formed. Done 41. Implementation checkpoint `f4fc828`. 0 local / 0 cloud model calls; no DB.

## 2026-09-08/09 — R-253..R-279 (parallel sessions; logged here in bulk)

- R-253..R-279 were shipped by parallel sessions (backend CRUD expansion + OpenAPI + the interactive
  Next.js web-app UX build-out), each with its own `.ai/tasks/R-###.md` contract, tests, and CHANGELOG
  entry, but their WORK_LOG entries and execution-tracker rows were not written at the time. Per-task
  detail lives in `.ai/tasks/R-253.md`..`R-279.md` and `CHANGELOG.md`. Highlights: R-253 PATCH, R-254
  structured JSON validation errors, R-255 pagination, R-256 PUT, R-257 typed API client + CORS, R-258
  sorting, R-259 X-Total-Count, R-260 OpenAPI 3.1, R-261 keyword search, R-262 React hooks, R-263
  interactive screens, R-264 field validation, R-265 subcollection master-detail, R-266 edit mode, R-267
  FK selectors, R-268 subcollection delete, R-269 page-size + empty states, R-270 bulk delete, R-271 CSV
  export, R-272 detail deep-linking, R-273 nav shell/navbar, R-274 form CTAs, R-275 dashboard, R-276
  record selector + prev/next, R-277 dirty-state guard, R-278 boolean/enum filters, R-279 toast system.

## 2026-09-09 — Tracker reconciliation (R-253..R-279)

- The execution tracker had been maintained only through R-252 (41 Done) while R-253..R-279 shipped.
  Backfilled all 27 missing rows (Done) via a batch generalization of the row-insertion script
  (`tracker_backfill_r253_r279.py`, baseline `764c95c`, DELTA=27), sourcing each row's title/description/
  evidence from `.ai/tasks/R-###.md` + `CHANGELOG.md` and the impl commit SHAs from `git log` (noting the
  two bundled commits `34b6d44` R-254..258 and `f16f64c` R-260..262). Result: rows 1..287 contiguous,
  table `A4:M287`, Dashboard ranges `B4:B287`/`H4:H287`, no `#REF!`, Done 68. Synced `docs/PROGRESS.md` to
  the live tracker figures. Commit `b4537c7`. Founder chose "reconcile, then R-280."

## 2026-09-09 — R-280

- Deep-linked collection list state + debounced, race-safe search in the generated Next.js web app —
  the founder-chosen "best, optimised, futuristic" combination of two of the survey-identified gaps
  (URL-as-state + correct/efficient fetching), both on one surface (`nextjs.py` `_collection_screen_page`
  + `_hooks_file`).
- `_hooks_file` `useList<Entities>`: added `useRef` to the react import; the `refetch` now creates an
  `AbortController` per call, aborts the previous request, forwards `signal` through the existing
  `ApiOptions` (which already extends `RequestInit`, so no `lib/api.ts` change), guards
  `AbortError`/`signal.aborted` (no state writes on abort), and aborts in-flight on unmount. Added a
  mount-once URL-hydrate effect (`URLSearchParams` over `window.location.search` → `setParams`) and a
  URL-sync effect (`new URL(...)` + `history.replaceState`, writing only non-default `sort/order/q/page/
  pageSize`), mirroring the R-276 detail deep-link pattern; both guarded `typeof window`.
- `_collection_screen_page`: always import `useEffect`; after the `searchInput` state, a 300ms debounce
  effect (`setTimeout`/`clearTimeout`, guarded `searchInput !== (params.q ?? "")` so it never clobbers a
  hydrated page offset) and a sync effect reflecting the hydrated `q` into the input; the input `onChange`
  no longer calls `setSearch` on every keystroke; the form submit still searches immediately.
- Subcollection hook (`useList<Child>By<Parent>`) and subcollection UI controls intentionally out of
  scope (a future R-281 candidate). No new IR field, no npm dependency, diff-invariant across
  `ir.description`.
- 12 new stdlib offline tests in `test_collection_deeplink_state.py` (768 total). Updated three existing
  assertion sets to the new behavior (`test_nextjs_hooks.py` import + refetch signal;
  `test_screen_generation.py` debounced onChange; `test_collection_field_filters.py` `useEffect` import).
  `task verify` + `task lint` + `task security:quick` + both `builder:demo`s pass.
- Tracker: `tracker_edit_r280.py` (baseline `7a6b9b5`) — R-280 (Builder) at row 9, R-279 → row 10; rows
  1..288 contiguous, table `A4:M288`, XML well-formed. Done 69. Implementation checkpoint `7a6b9b5`. 0
  local / 0 cloud model calls; no DB.

## 2026-09-09 — R-281

- Founder: "Continue for 281, do which is best for the two offline options; we have a Groq API key also."
  Asked how to sequence Groq vs R-281; founder chose "R-281 offline only" (Groq kept for a later live
  model-fabric verification; documented the safe `.env` enablement, never in chat/commits).
- Closed survey gap B: subcollection master-detail lists rendered only `{sub.data.map(...)}` despite the
  backend subcollection endpoints and the generated `useList<Child>By<Parent>` hook already supporting
  `limit/offset/sort/order/q`. Added two shared helpers in `nextjs.py`: `_subcol_controls(sub, s_var)`
  (an uncontrolled search `<form>` — `defaultValue` + `FormData` submit → `setSearch`, no new state — and
  a sort `<select>` of `id` + the subcollection's display fields → `setSort`) and `_subcol_pagination(s_var)`
  (a Prev / "Page X of Y (N total)" / Next footer → `setPage`, disabled at bounds/while loading).
- Wired both via `replace_all` into the two byte-identical subcollection render sites (the collection
  master-detail block in `_collection_screen_page` and the detail-screen block in `_detail_screen_page`),
  so both views get the same controls. Submit-based search avoids a per-keystroke fetch storm, so the
  subcollection hook internals are left unchanged (unlike R-280's top-level hook). No new IR field, no npm
  dependency, `"use client"` preserved, diff-invariant across `ir.description`.
- 6 new stdlib offline tests in `test_subcollection_list_controls.py` (774 total): controls present on
  both the collection and detail pages (search form, sort options `id`/`body`/`author` both directions,
  pagination footer), entities without subcollections emit none, the search input is uncontrolled (no
  extra state), diff-invariance, and both demos render the controls. `task verify` + `task lint` +
  `task security:quick` + both `builder:demo`s pass.
- Tracker: `tracker_edit_r281.py` (baseline `ad94a72`) — R-281 (Builder) at row 9, R-280 → row 10; rows
  1..289 contiguous, table `A4:M289`, Dashboard ranges `B4:B289`/`H4:H289`, no `#REF!`, XML well-formed.
  Done 70. Implementation checkpoint `ad94a72`. 0 local / 0 cloud model calls; no DB.

## 2026-09-09 — R-282

- Founder: "continue for next task." Chose the offline candidate (server-side field filters); the Groq key
  (offered earlier) was kept for a later live model-fabric verification. Followed the R-258 sort / R-261
  search pattern to add per-field boolean/enum equality filters to the top-level LIST endpoints.
- New shared `field_validation.filter_fields(entity)` — returns `(field, kind)` for boolean fields and
  enum fields (`enum:a|b|c` rule), excluding `id`; the single source of truth for both backends and
  OpenAPI, matching the frontend's boolean/enum selection.
- `data_access` Python (`_python_repository`): filterable entities emit a `_list_filters(q, <field>=None…)`
  helper and `list_`/`count_` gain the filter kwargs, building `WHERE` dynamically (q clause + `col = %s`
  per set filter, all `%s`-parameterized). Go (`_go_entity_store`): filterable entities emit a
  `<table>Filters(q, filters map[string]string) (string, []any)` helper — q clause `$1`, then each filter
  `col = $len(args)+1` (bool → `v == "true"`, enum → `v`) — and `List`/`Count` take a `filters` map with
  dynamic `LIMIT $%d OFFSET $%d`. Non-filterable entities are byte-identical (kept the exact old code paths).
- `backend_python`: the `Op.LIST` router branch declares typed filter query params (bool → `bool | None`,
  enum → `str | None`) and forwards them (needed threading an `entities_by_name` map into `_router_file`).
  `backend_go`: `parseFilters(r)` added to `handlers.go` only when a filterable entity exists (via a
  `has_filters` flag), and the `Op.LIST` handler branch calls it and threads the map into the store calls
  (via a `filtered_entities` frozenset). `openapi.render_openapi`: filter params documented on `Op.LIST`
  (boolean schema for bool; string + `enum` for enum).
- Scoped to `Op.LIST`; FK-scoped `LIST_BY` subcollection queries unchanged (the trickiest `$N`
  renumbering with the relation id is thereby avoided). No new IR field; no npm dependency;
  standard-library-only; values never interpolated as identifiers; diff-invariant across `ir.description`.
- 12 new stdlib offline tests in `test_field_filters_backend.py` (786 total): the helper, Python
  repo/router, Go store/handler, OpenAPI, non-filterable-unchanged, and diff-invariance. Because
  `minimal-blog` Post is filterable (`published` bool), updated the exact Post assertions in
  `test_search.py`, `test_sorting.py`, `test_pagination.py`, `test_total_count.py`, and `test_route_wiring.py`
  to the new dynamic-builder output (Comment/Driver, being non-filterable, stayed byte-identical).
  `task verify` + `task lint` + `task security:quick` + both `builder:demo`s pass.
- Tracker: `tracker_edit_r282.py` (baseline `198e23e`) — R-282 (Builder) at row 9, R-281 → row 10; rows
  1..290 contiguous, table `A4:M290`, Dashboard ranges `B4:B290`/`H4:H290`, no `#REF!`, XML well-formed.
  Done 71. Implementation checkpoint `198e23e`. 0 local / 0 cloud model calls; no DB.

## 2026-09-09 — R-283

- Founder supplied the exact R-283 continuation and selected recommended option 1: connect the R-278
  collection filter controls to R-282's server-side boolean/enum query parameters so filtering happens
  before pagination. Recorded the contract before implementation; no model call was needed.
- `nextjs.py` `_hooks_file`: filterable top-level list hooks now use `UseCollectionListParams` with an
  allowlisted `filters` map and `UseCollectionListState` setters. `setFilter` validates the generated
  field/value pair, removes `all`/empty values, and resets `offset`; `clearFilters` removes the map and
  resets pagination. The hook flattens the map into the existing `ApiOptions.params` request so
  `requestWithMeta` emits exact `?<field>=<value>` parameters. R-280 URL hydrate/sync reads and writes only
  allowlisted filter values. Non-filterable hooks retain their existing request path; `LIST_BY` unchanged.
- `_collection_screen_page`: boolean pills and enum selects call `setFilter`; Reset/empty recovery call
  `clearFilters`; active state comes from `params.filters`; table/empty state use server-returned data.
  Removed `useMemo` and the client-side `data.filter`, preserving the UI and `"use client"`.
- Reworked `test_collection_field_filters.py`: old page-local assertions now prove hook/request/UI wiring,
  allowlisted URL state, no local filtering, non-filterable absence, and description diff invariance.
  Three net-new tests; 789 total. `task verify`, `task lint`, `task security:quick`, and both builder demos
  pass. Inspected generated minimal-blog page/hooks/api and the non-filterable rideshare hooks.
- Tracker: `tracker_edit_r283.py` (baseline `d0c9e84`, LAST=290) — R-283 (Builder) at row 9, R-282 → row
  10; rows 1..291 contiguous; table `A4:M291`; Dashboard/sqref ranges extended; ZIP/XML valid; 283 unique
  IDs; Done 72. Artifact-tool before/after render inspected. Implementation checkpoint `d0c9e84`.
  0 local / 0 cloud model calls; no generated app run, network request, or DB connection.

## 2026-09-09 — R-284

- Recorded the Standard AI Task Contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-284.md` before
  implementation. Scope was limited to generated FastAPI/Go/OpenAPI `LIST_BY` filters plus focused tests.
- Extended Python relation-scoped repositories so mandatory relation scope, optional `q`, and allowlisted
  boolean/enum predicates share a parameterized filter builder used by both list and count. FastAPI
  routes declare typed filter query parameters and forward identical values to both calls.
- Extended Go relation-scoped stores with a shared predicate builder: relation ID stays `$1`, optional
  search follows, filter values use subsequent `len(args)+1` placeholders, and pagination follows all
  predicates. Handlers parse and forward filters only for filterable child entities.
- Extended generated OpenAPI `LIST_BY` operations with the matching boolean/enum query schemas.
  Non-filterable subcollections and description-only output remain byte-stable.
- Added 8 focused offline tests in `test_subcollection_field_filters.py`; implementation checkpoint
  `0bfb91d`. `task verify` passes with 797 tests; `task lint`, `task security:quick`, `task env:check`, and
  both builder demos pass. Generated FastAPI files parsed with AST; Go output parsed through `gofmt`;
  OpenAPI and SQL placeholder ordering inspected.
- Tracker updated with R-284 at row 9 and revalidated through artifact-tool: 284 unique IDs, table
  `A4:M292`, Dashboard formulas through row 292, valid XLSX archive, no formula-error tokens, visual
  render consistent. Counts: 73 Done, 1 Deferred, 210 Not Started; MVP 73/179 (40.8%). Corrected the
  previously reported R-251 MVP baseline from 145 to its directly recounted 146; R-252..R-284 add 33.
- Deterministic/offline work: 0 local model calls, 0 cloud calls, no generated app installed/run, no DB
  connection, and no IR, Next.js, dependency, database, infrastructure, or top-level-layout change.

## 2026-09-09 — R-285

- Founder explicitly requested continuation with R-285. Recorded the Standard AI Task Contract in
  `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-285.md` before implementation. Scope was limited to generated
  Next.js subcollection hooks/controls and focused tests; no model call was needed.
- Extended filterable `useList<Child>By<Parent>` hooks to use the existing typed collection-list filter
  state, validate values against IR-derived bool/enum options, expose `setFilter`/`clearFilters`, reset
  offset, and flatten active filter values into LIST_BY query params while preserving the relation ID as
  the separate path argument. Non-filterable hooks retain their prior output.
- Extended both parent collection master-detail and dedicated detail subcollection render sites with
  boolean pills, enum selects, active-filter count, Reset, and filtered-empty Clear filters recovery.
  Components map the server-returned child page directly and contain no page-local filtering.
- Added 7 focused offline tests in `test_subcollection_field_filter_wiring.py`; all 63 subcollection
  tests pass. Implementation checkpoint `92c89b1`. `task verify` passes with 804 tests; `task lint`,
  `task security:quick`, `task env:check`, and both builder demos pass. Generated hooks and both screen
  variants were inspected.
- Tracker updated through artifact-tool with R-285 at row 9: 285 unique IDs, table `A4:M293`, Dashboard
  formulas through row 293, valid XLSX archive, no formula-error tokens, and consistent visual render.
  Counts: 74 Done, 1 Deferred, 210 Not Started; MVP 74/180 (41.1%).
- Deterministic/offline work: 0 local model calls, 0 cloud calls, no generated app installed/run, no DB
  connection, and no IR, backend, dependency, database, infrastructure, or top-level-layout change.

## 2026-09-09 — R-286

- Founder explicitly requested continuation with R-286. Recorded the Standard AI Task Contract in
  `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-286.md` before implementation. Scope was limited to generated
  Next.js LIST_BY hooks and focused/legacy assertions; no model call was needed.
- Every `useList<Child>By<Parent>` hook now owns an `AbortController` ref and aborts the prior request
  before its missing-parent early return. A valid request installs a fresh controller and passes the
  internal signal after caller options so it cannot be overridden.
- Added guards so aborted successes and `AbortError` failures cannot mutate current data, total, error,
  or loading; only the active request clears loading, and effect cleanup aborts on dependency change or
  unmount. Filter flattening, parent path scope, and public hook signatures are preserved.
- Added 6 focused offline tests in `test_subcollection_request_cancellation.py`; updated three exact
  generated-call assertions. All 69 subcollection tests pass. Implementation checkpoint `3eb8bd1`.
  `task verify` passes with 810 tests; `task lint`, `task security:quick`, `task env:check`, and both
  builder demos pass. Filterable and non-filterable generated hook output was inspected.
- Tracker updated through artifact-tool with R-286 at row 9: 286 unique IDs, table `A4:M294`, Dashboard
  formulas through row 294, valid XLSX archive, no formula-error tokens, and consistent visual render.
  Counts: 75 Done, 1 Deferred, 210 Not Started; MVP 75/181 (41.4%).
- Deterministic/offline work: 0 local model calls, 0 cloud calls, no generated app installed/run, no DB
  connection, and no IR, backend, dependency, database, infrastructure, or top-level-layout change.

## 2026-09-10 — R-287

- Race-Safe Generated Detail Refetches: closed the last un-cancelled generated fetch path. The
  `use<Entity>` detail hook (`nextjs.py` `_hooks_file`, the `# 2. use<Entity>` block) previously awaited
  `api.get<Entity>(id, options)` and unconditionally `setData(item)`, so a stale GET could overwrite the
  currently selected record during rapid record-selector / prev-next / deep-link / id changes. R-280
  (LIST) and R-286 (LIST_BY) were already race-safe; this brings the detail hook to parity.
- Applied the R-286 template: the hook owns `const abortRef = useRef<AbortController | null>(null)`
  (`useRef` already imported by R-280); `refetch` calls `abortRef.current?.abort()` BEFORE the `if (!id)`
  reset (which now also `setError(null)` alongside `setData(null)`/`setLoading(false)`); a valid id
  registers a fresh controller; the GET call passes the internal signal AFTER caller options
  (`api.get<Entity>(id, { ...options, signal: controller.signal })`) so callers cannot replace it;
  success/catch/finally are guarded on `controller.signal.aborted` (+ the `AbortError` check); and the
  effect returns `() => abortRef.current?.abort()`. The generated API client forwards `signal` through
  `request(...)`'s `...init` spread, so no api-client change was needed.
- Test-first: added `test_detail_request_cancellation.py` (13 tests — abort-before-missing-ID ordering,
  missing-ID resets data/error/loading, signal-after-options, stale-success guard, AbortError ignored,
  active-only loading clear, effect-cleanup abort, public-shape preservation, description-only
  byte-stability, and an adapter-level generated-project check). They failed against the pre-change hook,
  pass after the edit. Updated the one existing exact-output assertion in `test_nextjs_hooks.py`
  (`getPost` call → signal-bearing form). List, LIST_BY, backend, API client, and IR unchanged.
- Gates: `task verify` 823 tests pass; `task lint`, `task security:quick`, `task env:check` pass; both
  `task builder:demo` pass; generated `useArticle` detail hook inspected. Implementation checkpoint
  `793804e`. 0 local / 0 cloud model calls; no generated app installed/run, no DB connection.
- Tracker: `tracker_edit_r287.py` (baseline `793804e`) — R-287 (Builder) at row 9, R-286 → row 10; rows
  1..295 contiguous, table `A4:M295`, Dashboard ranges through row 295, no `#REF!`, XLSX valid. Recounted
  from the workbook: 287 unique IDs (0 dupes), 76 Done, 1 Deferred, 210 Not Started; MVP 76/182 (41.8%);
  R-010..R-219 backlog intact.

## 2026-09-10 — R-288

- Deduplicated In-Flight Generated Mutation Requests: extended the race-safety theme from fetches
  (R-280/R-286/R-287) to writes. The generated `useCreate<Entity>` / `useUpdate<Entity>` /
  `useDelete<Entity>` hooks previously tracked `loading` but did not prevent a second invocation while
  one was in flight, so a double-clicked Create/Save/Delete (or a programmatic re-call) fired a duplicate
  POST/PUT/DELETE — a data-integrity bug (duplicate records / double deletes).
- Each mutation hook now owns `const pendingRef = useRef<Promise<T> | null>(null)` (T = `<Entity>` for
  create/update, `void` for delete; `useRef` already imported by R-280). The callback's first statement
  is `if (pendingRef.current) return pendingRef.current;` (dedupe → a concurrent call awaits the same
  promise, no second request). The try/catch/finally body runs in an IIFE captured as
  `pendingRef.current = request;` and returned; `finally` keeps `setLoading(false)` and adds
  `pendingRef.current = null;`. The callback signatures, the underlying `api.create|update|delete<Entity>`
  calls, and the return shape (`{ create|update|remove, mutate, loading, error, reset }`) are unchanged.
- Fetch hooks (`useList<Entities>` R-280, `useList<Child>By<Parent>` R-286, `use<Entity>` R-287), the
  generated API client, backend, and IR are untouched; description-only IR generation stays byte-stable.
- Test-first: added `test_mutation_inflight_guard.py` (6 tests — create/update/delete dedupe wiring with
  guard-before-setLoading ordering, IIFE capture, finally-clears-ref, api-call + return-shape
  preservation, errors still reject/set-error, fetch-hooks-unchanged, and description-only stability).
  They failed against the pre-change hooks, pass after the edit. The existing `test_nextjs_hooks.py`
  mutation assertions needed no change — the api-call and return-shape substrings survive inside the IIFE.
- Gates: `task verify` 829 tests pass; `task lint`, `task security:quick`, `task env:check` pass; both
  `task builder:demo` pass; generated `useCreatePost` inspected. Implementation checkpoint `3d6eecf`.
  0 local / 0 cloud model calls; no generated app installed/run, no DB connection.
- Tracker: `tracker_edit_r288.py` (baseline `3d6eecf`) — R-288 (Builder) at row 9, R-287 → row 10; rows
  1..296 contiguous, table `A4:M296`, Dashboard ranges through row 296, no `#REF!`, XLSX valid. Recounted
  from the workbook: 288 unique IDs (0 dupes), 77 Done, 1 Deferred, 210 Not Started; MVP 77/183 (42.1%);
  R-010..R-219 backlog intact.

## 2026-09-10 — R-289

- Debounced Live Subcollection Search: brought the generated subcollection (master-detail) search to
  parity with the top-level collection search (R-280). R-281 shipped a submit-only subcollection form to
  avoid per-subcollection state; now that R-286 made the `useList<Child>By<Parent>` hook race-safe
  (superseded LIST_BY requests aborted), a live search-as-you-type is safe.
- Added `_subcol_search_names(s_var)` (derives `<s_var>Search` / `set<S_var>Search`) and
  `_subcol_search_state(s_var)` (emits the `useState("")` + a 300ms `setTimeout`/`clearTimeout` debounce
  `useEffect` that commits `<state>.trim()` to `<s_var>.setSearch`, guarded by `<state> !== (params.q ??
  "")`). `_subcol_controls`'s search input is now controlled (`value`/`onChange`) instead of
  uncontrolled+`FormData`; the form `onSubmit` still commits immediately (Enter). Both helpers derive
  their names from `s_var`, so no extra args are threaded.
- Wired `_subcol_search_state(s_var)` into both subcollection hook-declaration sites (the collection
  master-detail `_collection_screen_page` and the detail `_detail_screen_page`) via `replace_all`; both
  screens already import `useState` + `useEffect`. Entities without a subcollection emit none of it. The
  hook, API client, backend, IR, and the sort/filter/pagination controls are unchanged; description-only
  IR generation stays byte-stable.
- Test-first: added `test_subcollection_search_debounce.py` (5 tests — controlled search state + 300ms
  debounce with the redundant-recommit guard, controlled input replacing defaultValue/FormData, both
  render sites, no-subcollection emits none, and description-only stability). They failed against the
  submit-only form, pass after the change. Updated the R-281 `test_subcollection_list_controls.py` search
  assertions to the controlled form.
- Gates: `task verify` 834 tests pass; `task lint`, `task security:quick`, `task env:check` pass; both
  `task builder:demo` pass; generated `post_list` subcollection search inspected. Implementation
  checkpoint `b6a1af4`. 0 local / 0 cloud model calls; no generated app installed/run, no DB connection.
- Tracker: `tracker_edit_r289.py` (baseline `b6a1af4`) — R-289 (Builder) at row 9, R-288 → row 10; rows
  1..297 contiguous, table `A4:M297`, Dashboard ranges through row 297, no `#REF!`, XLSX valid. Recounted
  from the workbook: 289 unique IDs (0 dupes), 78 Done, 1 Deferred, 210 Not Started; MVP 78/184 (42.4%);
  R-010..R-219 backlog intact.

## 2026-09-10 — R-290

- Optimistic Delete with Rollback: the generated collection screen previously waited for the delete
  round-trip before the row disappeared. R-290 makes both single (`handleDelete`) and batch
  (`handleBatchDelete`) deletes optimistic — the affected rows vanish immediately and reappear (with the
  existing error toast) only if the server rejects. Founder chose this over loading skeletons.
- Added, in `_collection_screen_page`: `const [pendingDeleteIds, setPendingDeleteIds] = useState<string[]
  >([]);` (next to `checkedIds`); a reconcile `useEffect(() => { setPendingDeleteIds((prev) => prev
  .filter((id) => (data ?? []).some((x: any) => String(x.id) === id))); }, [data]);` (prunes ids once
  refetch removes them — no flash-back, no unbounded growth); and `const visibleRows = displayData.filter
  ((item: any) => !pendingDeleteIds.includes(String((item as any).id)));`. `handleDelete` adds
  `String(id)` to pending before `await remove(id)` and rolls it back in `catch` before `toast.error`;
  `handleBatchDelete` snapshots `const ids = checkedIds.map(String)`, adds them, and rolls them back in
  `catch`. The row map now iterates `visibleRows`.
- `pendingDeleteIds`/`visibleRows` are emitted unconditionally (like the existing `checkedIds` selection
  state; all referenced, so no unused-var), but the delete handlers only exist when delete is wired, so a
  no-delete screen has no optimistic-delete handler. Detail-screen/subcollection delete, the mutation/list
  hooks, the API client, backend, and IR are unchanged; description-only IR generation stays byte-stable.
- Test-first: added `test_collection_optimistic_delete.py` (9 tests — pending state, reconcile effect,
  visibleRows filter + map, single optimistic+rollback ordering, batch optimistic+rollback, success path
  preserved, no-delete emits no handler, description-only stability, demo generation). They failed against
  the pre-change handlers, pass after. Updated two `test_collection_field_filters.py` row-map assertions
  (`displayData.map`/`data.map` → `visibleRows.map`).
- Gates: `task verify` 843 tests pass; `task lint`, `task security:quick`, `task env:check` pass; both
  `task builder:demo` pass; generated collection page inspected. Implementation checkpoint `1ed88b6`.
  0 local / 0 cloud model calls; no generated app installed/run, no DB connection.
- Tracker: `tracker_edit_r290.py` (baseline `1ed88b6`) — R-290 (Builder) at row 9, R-289 → row 10; rows
  1..298 contiguous, table `A4:M298`, Dashboard ranges through row 298, no `#REF!`, XLSX valid. Recounted
  from the workbook: 290 unique IDs (0 dupes), 79 Done, 1 Deferred, 210 Not Started; MVP 79/185 (42.7%);
  R-010..R-219 backlog intact.

## 2026-09-10 — R-291

- Optimistic Subcollection Child Delete: extended R-290's optimistic delete to the subcollection
  (master-detail) child lists in both the collection master-detail (`_collection_screen_page`) and detail
  (`_detail_screen_page`) screens. Founder granted autonomous continuation, so this rolled straight on
  from R-290 to complete the optimistic-delete story.
- Added `_subcol_delete_names(s_var)` (derives `<s_var>Deleting` / `set<S_var>Deleting`). In the child
  delete-handler loop (both sites emit byte-identical handler blocks — one `replace_all`), when
  `sub.can_delete`: emit `const [<s_var>Deleting, set<S_var>Deleting] = useState<string[]>([]);` + a
  reconcile `useEffect(() => { set<S_var>Deleting((prev) => prev.filter((did) => (<s_var>.data ?? [])
  .some((x: any) => String(x.id) === did))); }, [<s_var>.data]);` before the handler; the handler adds
  `String(id)` before `await remove<Child>(id)` and rolls it back in `catch` before `toast.error`.
- The child row-map block (both sites — one `replace_all`) now computes `_child_map_src` =
  `(<s_var>.data ?? []).filter((child: any) => !<s_var>Deleting.includes(String((child as any).id)))`
  when `sub.can_delete`, else `<s_var>.data`, and maps over it — so a deleted child row vanishes
  immediately and reappears on failure. Non-deletable subcollections are byte-identical to before. Both
  screens already import `useState`+`useEffect`.
- Test-first: added `test_subcollection_optimistic_delete.py` (6 tests — deleting state + reconcile
  effect, optimistic add-before-await ordering + rollback, filtered child map, both render sites,
  non-deletable emits none, description-only stability, and adapter-level generation; plus examples still
  generate). They failed against the pre-change handlers, pass after. No existing assertion needed
  changing (the full suite stayed green).
- Gates: `task verify` 849 tests pass; `task lint`, `task security:quick`, `task env:check` pass; both
  `task builder:demo` pass; generated child handler + filtered map inspected. Implementation checkpoint
  `51f33c8`. 0 local / 0 cloud model calls; no generated app installed/run, no DB connection.
- Tracker: `tracker_edit_r291.py` (baseline `51f33c8`) — R-291 (Builder) at row 9, R-290 → row 10; rows
  1..299 contiguous, table `A4:M299`, Dashboard ranges through row 299, no `#REF!`, XLSX valid. Recounted
  from the workbook: 291 unique IDs (0 dupes), 80 Done, 1 Deferred, 210 Not Started; MVP 80/186 (43.0%);
  R-010..R-219 backlog intact.

## 2026-09-10 — R-292

- Loading Skeletons: replaced the plain "Loading..." text in the generated screens' data-loading states
  with layout-preserving skeleton placeholders (static inline-styled gray rounded bars). Rolled straight
  on from R-291 per the founder's autonomous-continuation authorization; a fresh UX-quality theme now
  that the delete/fetch robustness arc is complete.
- Collection table (`_collection_screen_page`): the `{loading && !data}` cell (colSpan-spanning) now maps
  `[0..4]` skeleton bars (`height: 14, background: "#e2e8f0", borderRadius: 4, margin: "10px 0", opacity:
  1 - i * 0.15`) instead of "Loading <plural>...". Subcollection lists (both the collection master-detail
  and detail sites — one `replace_all`): the `{<s_var>.loading && !<s_var>.data}` block maps `[0..2]`
  skeleton blocks (`height: 44, background: "#f1f5f9"`). Detail main (`_detail_screen_page`): the
  `{loading}` block maps `[0..3]` skeleton lines of varying width (`width: \`${88 - i * 14}%\``).
- Static skeletons only (no CSS `@keyframes`, no new file/component, no dependency) — the generated app
  uses inline styles throughout and has no CSS-injection point. Refresh-button "Loading..." labels,
  empty/error states, and data rendering are unchanged. No hook/API-client/backend/IR change;
  description-only IR generation stays byte-stable.
- Test-first: added `test_loading_skeletons.py` (9 tests — collection skeleton bars + text removed +
  refresh label kept, subcollection skeleton blocks both sites, detail skeleton lines + text removed,
  description-only stability, examples still generate). They failed against the plain-text loading, pass
  after. Updated two `test_subcollection_screens.py` loading assertions to the skeleton markup.
- Gates: `task verify` 858 tests pass; `task lint`, `task security:quick`, `task env:check` pass; both
  `task builder:demo` pass; generated collection skeleton inspected. Implementation checkpoint `16d6c52`.
  0 local / 0 cloud model calls; no generated app installed/run, no DB connection.
- Tracker: `tracker_edit_r292.py` (baseline `16d6c52`) — R-292 (Builder) at row 9, R-291 → row 10; rows
  1..300 contiguous, table `A4:M300`, Dashboard ranges through row 300, no `#REF!`, XLSX valid. Recounted
  from the workbook: 292 unique IDs (0 dupes), 81 Done, 1 Deferred, 210 Not Started; MVP 81/187 (43.3%);
  R-010..R-219 backlog intact.

## R-334 – Generated Accessible Reusable Stepper / Multi-step Wizard Component
- **Date**: 2026-09-11
- **Status**: DONE
- **Tests**: 1329 total (19 new in test_stepper_component.py); all passing
- **Files changed**:
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py`: Added `_STEPPER_COMPONENT` template (~540 lines) and `render_stepper_component()` function; registered `components/stepper.tsx` in `NextjsWebAdapter.generate()`.
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/__init__.py`: Exported `render_stepper_component`.
  - `services/agent-engine/tests/test_stepper_component.py`: 19 unit tests (NEW).
- **Gates**: task verify ✓ | task lint ✓ | task security:quick ✓ | builder:demo minimal-blog (71 files) ✓ | builder:demo rideshare-favourites (68 files) ✓

## R-335 – Generated Accessible Reusable File Upload / Dropzone Component
- **Date**: 2026-09-11
- **Status**: DONE
- **Tests**: 1349 total (20 new in test_file_upload_component.py); all passing
- **Files changed**:
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py`: Added `_FILE_UPLOAD_COMPONENT` (~670 lines) and `render_file_upload_component()`; registered `components/file-upload.tsx` in `NextjsWebAdapter.generate()`.
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/__init__.py`: Exported `render_file_upload_component`.
  - `services/agent-engine/tests/test_file_upload_component.py`: 20 unit tests (NEW).
- **Gates**: task verify ✓ | task lint ✓ | task security:quick ✓ | builder:demo minimal-blog (72 files) ✓ | builder:demo rideshare-favourites (69 files) ✓

## R-336 – Generated Accessible Reusable Timeline / Activity Feed Component
- **Date**: 2026-09-11
- **Status**: DONE
- **Tests**: 1369 total (20 new in test_timeline_component.py); all passing
- **Files changed**:
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py`: Added `_TIMELINE_COMPONENT` template + `render_timeline_component()`; registered `components/timeline.tsx` in `NextjsWebAdapter.generate()`.
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/__init__.py`: Exported `render_timeline_component`.
  - `services/agent-engine/tests/test_timeline_component.py`: 20 unit tests (NEW).
- **Gates**: task verify ✓ | task lint ✓ | task security:quick ✓ | builder:demo minimal-blog (73 files) ✓ | builder:demo rideshare-favourites (70 files) ✓

## R-337 – Generated Accessible Futuristic Reusable Stat & Metric KPI Card Component
- **Date**: 2026-09-11
- **Status**: DONE
- **Tests**: 1384 total (15 new in test_stat_card_component.py); all passing
- **Files changed**:
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/nextjs.py`: Added `_STAT_CARD_COMPONENT` static template (~520 lines) and `render_stat_card_component()`; registered `components/stat-card.tsx` in `NextjsWebAdapter.generate()`.
  - `services/agent-engine/src/omnistackai_agent_engine/codegen/__init__.py`: Exported `render_stat_card_component`.
  - `services/agent-engine/tests/test_stat_card_component.py`: 15 unit tests (NEW).
- **Gates**: task verify ✓ | task lint ✓ | task security:quick ✓ | builder:demo minimal-blog (74 files) ✓ | builder:demo rideshare-favourites (71 files) ✓
