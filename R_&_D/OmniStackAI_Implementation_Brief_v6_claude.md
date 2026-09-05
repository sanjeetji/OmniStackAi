# OmniStackAI - AI Software Engineering Platform Implementation Brief

Version: 6.0  
Date: 2026-09-05  
Purpose: Machine-friendly implementation rules for developers and AI coding agents. V5 turned the R&D blueprint into a cost-aware, production-oriented multi-platform software factory: instant-browser-first verification, QR/real-device delivery, durable project memory separated from chat, progressive context retrieval, LLM escalation/cost control, Temporal durability, database recommendation profiles, client handover, release provenance and current competitor benchmarks. **V6 closes four gaps found in review**: (1) local/offline LLM inference (Ollama + open coding models) as a first-class, zero-marginal-cost tier, not just a vague "private endpoint" mention; (2) a concrete multi-provider BYOK API-key settings module (OpenAI, Anthropic, Gemini, Groq, OpenRouter, custom OpenAI-compatible endpoints); (3) a session-continuity/resume protocol so any AI coding tool or human developer can stop today and pick up tomorrow with zero re-explaining; (4) a solo-founder low-cost build sequence so the platform can actually be built incrementally without paying for enterprise-grade infrastructure on day one.

---

## 1. Product Goal

Build a browser-based AI engineering platform that can create, modify, test, preview, deploy and maintain complete software products.

The product must support multiple project profiles instead of forcing one mobile framework on every customer.

### Mobile choices

1. **Auto / Recommended** - default option. The platform chooses the safest low-cost profile and explains why.
2. **Flutter** - one Dart codebase for Android and iOS. Best default for many small/medium mobile-first products.
3. **React Native** - one TypeScript/JavaScript codebase for Android and iOS. Strong option for React/TypeScript teams and projects that want more code/package reuse with web.
4. **Native** - Kotlin + Jetpack Compose for Android and Swift + SwiftUI for iOS. Recommended when deep native APIs, hardware, performance, complex background execution, platform-specific UX or compliance needs justify the extra cost.
5. **Web/PWA only** - lowest-cost option when App Store presence or native device capabilities are not required.

### Web and admin choices

- Public web default: **React + Next.js + TypeScript**.
- Admin default: **React + Next.js + TypeScript**.
- Flutter Web can be offered only for app-like browser experiences where SEO and desktop/admin constraints are acceptable.
- React Native Web / Expo Web can be offered when code sharing is valuable, but Next.js remains preferred for SEO-heavy public sites and complex admin panels.
- Do not force the mobile framework onto the web/admin layer.

### Backend and database choices

- Platform control plane: **Go** for transactional control-plane, scheduling, policy, Git/deployment and high-concurrency services; **Python** for agent/model/context services where the AI ecosystem materially benefits.
- Generated customer backend: **Go or Python by default**; Node.js/NestJS remains an optional profile for end-to-end TypeScript or ecosystem fit.
- **OmniStackAI control-plane database: PostgreSQL. This is non-negotiable for the default cloud product.**
- Generated customer database starts at **Auto / Recommended**. Default recommendation is PostgreSQL, but MongoDB, Supabase/Postgres, Firebase/Firestore and existing customer databases are selectable when the workload justifies them.
- PostgreSQL extensions: **JSONB** for flexible fields, **pgvector** for platform semantic retrieval, and **PostGIS** when location/geospatial products justify it.
- Redis is cache/ephemeral coordination, not the source of truth. NATS/managed queue handles asynchronous events where required. Large artifacts/logs live in S3/GCS-compatible object storage.

The user can use the product from Windows, Linux, macOS, ChromeOS or a tablet browser. The user's OS must not limit what code can be generated or previewed.

---

## 2. Core Product Rule

The LLM is an engineer inside the platform. It is not the source of truth.

The LLM cannot bypass:

- requirement specification,
- Application IR,
- architecture rules,
- change-impact analysis,
- compiler/build output,
- tests,
- security gates,
- Git,
- deployment approvals,
- cost limits.

Canonical flow:

```text
User Prompt
  -> Requirement Spec
  -> Framework / Target Recommendation
  -> Application IR
  -> Product Architect
  -> Change Impact Engine
  -> Task Graph
  -> Activate only required Agents/Framework Adapters
  -> Controlled Code Patch
  -> Compile + Test + Security
  -> Review
  -> Git Commit / PR
  -> Deployment
```

---

## 3. Framework Selection Strategy

### 3.1 Default behavior

Every new project starts with:

```text
Mobile Technology

(*) Auto / Recommended
( ) Flutter
( ) React Native
( ) Native: Kotlin + Swift
( ) Web/PWA only
```

The recommendation engine must show:

- recommended profile,
- reason,
- expected development complexity,
- expected build/runtime cost,
- important limitations,
- native capability risks,
- web/admin strategy.

The user can override the recommendation.

### 3.2 Do not choose only by industry name

Bad rule:

```text
Fintech -> Native
E-commerce -> Native
Taxi -> Flutter
```

Do not implement this.

A fintech app can be simple enough for Flutter or React Native. An e-commerce app can also work very well cross-platform. Native should be recommended from actual technical requirements, not from the app category alone.

### 3.3 Recommendation inputs

Score at least these factors:

- budget sensitivity,
- speed to market,
- existing React/TypeScript skills,
- custom UI consistency,
- desired web code sharing,
- deep native API usage,
- high-performance/latency requirements,
- complex background work,
- hardware needs such as NFC/BLE/sensors/CarPlay,
- security/compliance requirements,
- platform-specific UX/accessibility depth,
- existing repository/SDK constraints.

### 3.4 Recommended profiles

#### Flutter

Prefer when:

- small/medium product,
- one mobile team,
- fast delivery matters,
- custom consistent UI matters,
- most features are standard app flows,
- one Android/iOS codebase reduces cost.

Escalate to Native when:

- plugins/native bridges become the core of the product,
- OS background execution is unusually complex,
- hardware integration is deep,
- performance profiling proves a real bottleneck,
- platform-specific behavior is a major product requirement.

#### React Native

Prefer when:

- team is already strong in React/TypeScript,
- packages/types/validation can be shared with Next.js,
- mobile UI is product-oriented rather than extremely platform-specific,
- Expo/RN ecosystem covers the needed capabilities.

Escalate to Native when the bridge/native-module surface becomes too large or high-risk.

#### Native Kotlin + Swift

Prefer when measured requirements justify it:

- deep Apple/Android APIs,
- high-performance media/graphics,
- complex background execution,
- specialized hardware,
- platform-specific SDKs,
- premium native UX is a core differentiator,
- strict platform-specific security controls,
- long-lived enterprise app with separate native teams.

Native has higher development and maintenance cost because Android and iOS have separate source code and toolchains.

---

## 4. Web and Admin Sharing Rules

Do not promise "one codebase for everything" unless it is technically and commercially correct.

### Flutter project

```text
Mobile: Flutter
Public Web: Next.js by default
Admin: Next.js
Backend: Go/Python
```

Optional:

```text
Public Web: Flutter Web
```

Use Flutter Web only when the web experience is app-like and SEO/desktop needs are acceptable.

### React Native project

```text
Mobile: React Native
Public Web: Next.js by default
Admin: Next.js
Backend: Go/Python
```

Share where safe:

- TypeScript types,
- validation,
- API clients,
- domain logic,
- some UI primitives,
- design tokens.

Optional:

```text
React Native Web / Expo Web
```

Do not make a complex admin panel depend on React Native Web just to claim 100% sharing.

### Native project

```text
Android: Kotlin + Compose
iOS: Swift + SwiftUI
Public Web: Next.js
Admin: Next.js
Backend: Go/Python
```

Share contracts and product rules, not mobile runtime code.

---

## 5. Our Platform Repository Architecture

### 5.1 Start with a modular monorepo

Canonical OmniStackAI platform repository name:

```text
omnistackai-platform
```

Recommended structure:

```text
omnistackai-platform/
  apps/
    console-web/

  services/
    control-plane-go/
    realtime-gateway-go/
    agent-orchestrator-python/
    billing-go/

  workers/
    linux-runner/
    build-runner/
    mac-runner-controller/

  packages/
    contracts/
    policy-schemas/
    telemetry/
    ui/
    agent-sdk/

  ai/
    prompts/
    tool-definitions/
    evals/
    benchmark-cases/

  infra/
    terraform/
    kubernetes/
    environments/

  docs/
```

### 5.2 Why monorepo first

It is easier during MVP because:

- API contracts change with services,
- AI tools and control-plane APIs evolve together,
- one PR can update multiple modules safely,
- shared telemetry/security/policies stay synchronized,
- fewer repositories reduce DevOps overhead.

### 5.3 Root build orchestration

Use simple tools first:

- root `Taskfile.yml` or `Makefile`,
- pnpm + Turborepo for TypeScript packages,
- Go workspaces for Go,
- uv/Poetry for Python,
- Docker Compose for local dependencies,
- CI remote caching.

Do not start with Bazel/Pants unless repository scale actually requires them.

### 5.4 When our platform can split repos

Split only after there is a real boundary such as:

- separate security lifecycle,
- separate release ownership,
- independently scaled runtime,
- compliance/access restriction,
- large team ownership.

The Local Mac Agent may eventually become its own repository because it has a separate signing/update/security lifecycle.

---

## 6. Customer-Generated Git Repository Strategy

### 6.1 One repository per customer project

Never put source code for multiple customer projects in the same Git repository.

Default generated repository name:

```text
project-<project-slug>
```

Optional:

```text
<workspace-slug>-<project-slug>
```

The customer may instead connect their own GitHub/GitLab organization.

### 6.2 Customer project is a monorepo by default

Reason: one feature may require a coordinated change across mobile, web, admin, backend, schema and tests.

A monorepo lets the AI produce one atomic task branch and one reviewable change set.

Canonical structure:

```text
project-<slug>/
  .ai/
    ir/
    adr/
    policies/
    task-history/

  apps/
    <mobile target folders>
    web/
    admin/

  services/
    api/
    workers/

  packages/
    contracts/
    design-tokens/
    domain/
    validation/

  database/
  infra/
  tests/
  docs/
```

### 6.3 Flutter project structure

```text
apps/
  mobile-flutter/
  web/
  admin/
```

`mobile-flutter/` contains Android/iOS Flutter source. Flutter Web can exist as an optional target inside the Flutter application only when the project web strategy explicitly selects it.

### 6.4 React Native project structure

```text
apps/
  mobile-react-native/
  web/
  admin/
```

Reusable TypeScript packages can be imported by mobile and Next.js where runtime compatibility is safe.

### 6.5 Native project structure

```text
apps/
  android/
  ios/
  web/
  admin/
```

Android and iOS are separate applications but remain in one project repository so feature changes can be coordinated and reviewed together.

### 6.6 Branch and PR strategy

Use trunk-based development with short-lived AI branches.

Example:

```text
main
ai/FAV-001-favourite-driver
ai/PAY-014-stripe-refund
```

Rules:

- `main` is protected.
- Every AI task receives a task ID.
- Every task gets its own branch/worktree.
- One task produces one PR/change set when possible.
- Commits reference the task ID.
- CI gates must pass before merge.
- Sensitive paths use CODEOWNERS/approval rules.

### 6.7 When to split a customer monorepo

Do not split by default.

Review a split only when one or more are true:

- 3+ independent teams need unrelated release cycles,
- compliance/data boundaries require separate permissions,
- access controls cannot be handled safely inside one repo,
- build times remain unacceptable after caching/incremental optimization,
- repository/tooling size becomes a measured problem,
- services truly have independent ownership and contracts.

Splitting a repo is an architecture migration and must never happen silently.

---

## 7. Product Hierarchy

Canonical tenancy/product hierarchy:

```text
Organization
  -> Workspace
    -> Project
      -> Environment
        -> Target
          -> Deployment
```

Definitions:

- Organization: billing/security/legal boundary.
- Workspace: team/client grouping.
- Project: one software product + one default Git repository.
- Environment: development, preview, staging, production.
- Target: Flutter, React Native, native Android, native iOS, web, admin, backend.
- Deployment: immutable build/release for one target/environment.

---

## 8. Product UI Structure

Minimum project UI tabs:

1. Dashboard
2. Create Project / Stack
3. AI Chat / Requirements
4. Plan
5. Architecture
6. Code
7. Repository / Changes
8. Preview
9. Real Device
10. Cloud Device
11. Tests / Quality
12. API / Data
13. Integrations
14. Deployments / Stores
15. Logs / Observability
16. Usage / Cost
17. Team / Security
18. Client Handover
19. Settings

Create Project / Stack must show:

```text
Mobile: Auto | Flutter | React Native/Expo | Native | None
Web: Next.js | Optional framework-web profile | None
Admin: Next.js | None
Backend: Auto | Go | Python | Node when justified | BaaS
Database: Auto/Recommended | PostgreSQL | MongoDB | Supabase | Firebase/Firestore | Existing
Repository: New project monorepo | Import existing repo | Connect customer Git
Execution: Cloud Standard | Hybrid Local | Enterprise Private/BYOC
```

The Preview tab must never hide the verification hierarchy. The visible order is always:

```text
1. Instant Browser Preview            <- first/default
2. Test on My Real Phone              <- QR/link/build on demand
3. Cloud Android Emulator             <- optional/metered
4. Cloud iOS Simulator                <- optional/metered/highest cost
```

The UI must explain what each mode proves and what it does not prove.

## 9. Application IR v3

Application IR is framework-neutral. It is the source of truth between user intent and generated targets.

Minimum model:

```yaml
application:
  name: string
  description: string
  platforms: [mobile, web, admin, backend]

project_strategy:
  mobile_profile: auto | flutter | react_native | native | none
  web_strategy: nextjs | flutter_web | rn_web | pwa | none
  admin_strategy: nextjs | none
  backend_strategy: go | python | node
  database_strategy: postgres | other
  repo_strategy: customer_project_monorepo | approved_multi_repo

framework_config:
  flutter_version: optional
  react_native_version: optional
  expo_profile: optional
  kotlin_toolchain: optional
  swift_toolchain: optional

shared_code_policy:
  contracts: true
  design_tokens: true
  validation: true
  domain_rules: true
  ui_packages: controlled

roles:
  - id
  - permissions

screens:
  - id
  - role
  - components
  - states
  - navigation
  - actions

flows:
  - id
  - actor
  - steps
  - success
  - errors

entities:
  - name
  - fields
  - validation
  - relations

apis:
  - method
  - path
  - auth
  - request_schema
  - response_schema
  - error_schema

integrations:
  - provider
  - scopes
  - secret_schema
  - webhook_rules

architecture_rules:
  - module_boundaries
  - allowed_dependencies
  - approved_patterns

repo_modules:
  - path
  - owner
  - target
  - permissions

build_matrix:
  - target
  - toolchain
  - required_gates

acceptance_criteria:
  - requirement_id
  - measurable_expected_result

adrs:
  - decision
  - rationale
  - status
```

---

## 10. Ideal Agent Architecture

Only activate agents needed by the selected project profile.

```text
                         USER
                           |
                           v
                  Requirement Agent
                           |
                           v
                   Product Architect
                 + Framework Planning
                           |
                           v
                      Task Graph
                           |
       +-------------------+--------------------+
       |                   |                    |
       v                   v                    v
Cross-Platform       Native Android        Native iOS
Mobile Agent         Agent                 Agent
Flutter or RN        Kotlin/Compose        Swift/SwiftUI
       |                   |                    |
       +-------------------+--------------------+
                           |
                     Web/Admin Agent
                           |
                      Backend Agent
                           |
                      Database Agent
                           |
                    Integration Agent
                           |
                         QA Agent
                  /          |          \
               Unit      Integration      E2E
                           |
                    Security Agent
                           |
                      Review Agent
                           |
                   Deployment Agent
```

Additional platform capabilities:

- Supervisor/Orchestrator
- Context Manager
- Cost Controller
- Recovery Agent
- Framework Upgrade Agent in MID
- Evaluation/Benchmark system in ADVANCED

Do not run native Android/iOS agents for a Flutter/RN project unless a native module is actually required.

---

## 11. Agent Permission Model

Use least privilege.

Examples:

- Coding agent: read relevant context, write only task branch, run approved tools.
- Flutter/RN agent: cannot modify native platform folders outside approved plugin/native-module scope without impact approval.
- Database agent: can generate migration files but cannot apply destructive production migration automatically.
- Security agent: can inspect but cannot deploy.
- Deployment agent: can deploy only approved commit; cannot modify source code.
- Signing service: can use signing keys; raw private keys are never readable by agents.
- Local Mac Agent: must use explicit user permission, scoped workspace and signed secure protocol.

---

## 12. Change Impact Engine

Before edits:

```text
Requested Feature
  -> Map to Requirement + IR
  -> Determine selected framework profile
  -> Dependency/Symbol Graph
  -> Affected Modules
  -> Affected APIs
  -> Affected DB/Schema
  -> Affected Targets
  -> Affected Tests
  -> Risk Class
  -> Expected Blast Radius
  -> Allow Patch
```

After edits:

```text
Actual Diff
  -> Compare with Expected Blast Radius
  -> Compile affected targets
  -> Static Analysis
  -> Unit/Integration/E2E
  -> Security
  -> Cross-target consistency
  -> Review
  -> Merge or Reject
```

Example:

User asks to change a button color.

Expected:

- design token/UI style,
- visual baseline.

If the agent changes auth/backend/database, reject or require explicit approval.

---

## 13. Code Intelligence and Context

**Project memory is separate from chat.** Raw conversation history is an interface artifact, not the engineering source of truth.

Persist at minimum:

- Application IR and schema version,
- accepted requirements and acceptance criteria,
- ADRs and architecture/policy decisions,
- selected framework/profile/toolchain versions,
- repository/module graph,
- symbols/imports/callers/callees/dependency graph,
- API/OpenAPI/AsyncAPI contracts,
- database schema/indexes/migrations,
- task history/diffs/commits/PRs/approvals,
- tests/coverage/visual baselines,
- build/deployment/release history,
- crash reports/logs/traces/runtime evidence,
- dependency/template/plugin versions,
- semantic embeddings and retrieval metadata.

### 13.1 Context authority

When sources conflict, prefer current evidence in roughly this order:

```text
Current Git source + canonical contracts
  > Application IR
  > accepted requirements
  > ADRs / enforced policies
  > DB/API schema
  > executable tests
  > current deployment/runtime evidence
  > Git/task history
  > accepted conversation summaries
  > raw historical chat
```

Embeddings are a **locator, never truth**. A semantic hit must be resolved to authoritative code/IR/ADR/test/runtime evidence before a high-impact decision.

### 13.2 Progressive context retrieval

Do not insert the entire repository into the LLM. Build a task-specific Context Pack:

```text
Issue/Goal
 -> deterministic search + semantic search
 -> symbol/call/dependency graph
 -> relevant requirements + ADRs
 -> current deployment/crash evidence
 -> recent Git history
 -> top relevant code symbols/chunks
 -> Context Pack
 -> model
 -> on-demand readSymbol/readFile/findReferences tools
```

Start narrow and expand only when evidence requires it. Any material blast-radius expansion is recorded and, when risk requires, approved.

### 13.3 Long-project memory

A new chat opened months later must still be able to repair a project without replaying months of conversation. The Context Manager reconstructs current state from Git, IR, indexes and runtime evidence. Accepted decisions are extracted from chat into canonical project memory; abandoned brainstorming is not promoted.

### 13.4 Storage baseline

MVP storage:

- PostgreSQL for canonical metadata/event ledger/project memory,
- pgvector for semantic retrieval,
- Redis for cache/session/leases,
- NATS JetStream or managed queue for asynchronous events,
- S3/GCS-compatible object storage for logs, artifacts, snapshots, screenshots and large traces.

Do not start with Kafka, a separate vector database, graph database or search cluster until measured workload proves the need. The symbol/call graph may initially live in PostgreSQL/object indexes plus language-server/static-analysis indexes.

## 14. Structured Editing

Preferred tools:

- Dart/Flutter: analyzer AST / tree-sitter where useful.
- TypeScript/React Native/Next.js: TypeScript compiler API / ts-morph.
- Kotlin: Kotlin PSI where practical; tree-sitter for indexing.
- Swift: SwiftSyntax for precise edits; tree-sitter for indexing.
- Python: LibCST / ast.
- Go: go/ast.

Full-file rewrite is allowed for a new file or controlled fallback, but it increases review/test requirements.

---

## 15. Preview and Runtime Strategy

**Non-negotiable UX rule: Instant Browser Preview is always the first visible preview option. QR/device builds are optional next steps, never the default.**

### 15.1 Verification ladder

```text
Level 0 - Deterministic verification
  lint / typecheck / unit tests / static checks

Level 1 - Instant Browser Preview       <- always first
  web/admin: actual running code
  mobile/native: interactive IR/browser representation unless real web target exists

Level 2 - Real Physical Device
  Expo/RN: QR -> Expo Go or custom development client
  Android Flutter/bare RN/native: QR -> secure test APK
  iOS Flutter/RN/native: TestFlight/development build link or QR

Level 3 - Cloud Device
  Android Emulator on Linux/KVM or device cloud
  iOS Simulator on macOS/Xcode
```

The platform uses the **lowest-cost verification level capable of proving the requested change**. Cloud devices are on-demand tools for debugging, QA, automation, OS compatibility, support and cases where the user lacks a physical device.

### 15.2 Instant browser preview

For web/admin, run the actual application in an isolated Linux/browser-compatible runtime behind a temporary preview URL.

For mobile targets, the instant browser mode may be one of:

- actual Expo Web/RN Web when the selected profile supports it,
- actual Flutter Web only when the project selected a compatible web target,
- framework-neutral Application-IR browser renderer for Kotlin/Swift/native-only screens and flows.

The product must label IR/browser-renderer output as **Interactive Browser Preview**, not as proof that a native binary compiled or platform APIs work.

### 15.3 Expo / React Native fast-device path

When Expo compatibility remains valid:

```text
AI patch -> checks -> instant browser preview -> QR -> Expo Go/dev client -> real phone -> refresh
```

Do not rebuild APK/IPA for ordinary JS/TS/UI/business-logic changes. Compute a **Native Fingerprint** from native modules, SDK versions, permissions, Gradle/Xcode config, plugins and native configuration. Rebuild the development client only when the fingerprint changes.

### 15.4 Flutter real-device path

Flutter does not have a universal Expo-Go equivalent. Default flow:

```text
AI patch -> checks -> instant browser/design preview -> user selects Real Device
  Android -> cached Linux build -> APK -> QR
  iOS -> cached macOS build -> TestFlight/dev distribution
```

Use warm workers, pub cache, Gradle cache, CocoaPods/SPM cache and safe build-intermediate caching to reduce build latency.

### 15.5 Native Android real-device path

```text
AI patch -> instant browser preview -> Build Test APK on demand
 -> isolated signing -> encrypted artifact store -> short-lived signed URL
 -> QR -> install on user's Android phone
```

Testing APK links are temporary. Production AAB/APK artifacts are immutable, retained according to release policy and tied to commit/IR/toolchain provenance.

### 15.6 Native iOS real-device path

Do not promise unrestricted public IPA installation. Default real-device path is TestFlight or an approved Apple development/ad-hoc workflow:

```text
AI patch -> instant browser preview -> macOS/Xcode build on demand
 -> isolated signing -> App Store Connect/TestFlight or approved dev provisioning
 -> QR/invite link -> real iPhone
```

An optional Local Mac Agent can perform Xcode compile, simulator and device installation on a customer-owned Mac, avoiding OmniStackAI cloud-Mac compute.

### 15.7 Smart Verification Policy

Change Impact Engine classifies required proof:

- copy/style/layout change -> deterministic checks + browser preview,
- business/API change -> targeted unit/contract/integration + browser preview,
- native dependency/permission/background/hardware change -> real-device build required,
- OS/version-specific crash -> cloud emulator/simulator or matching physical device,
- release/signing/store change -> real release pipeline and approval required.

The UI shows **Recommended Verification**, reason, estimated compute/time and optional stronger verification.

### 15.8 Remote Debug Bridge

For opted-in development builds, support a secure device-to-platform channel for:

- application logs and crash stack traces,
- trace IDs and sanitized network diagnostics,
- device/OS/app-build metadata,
- screenshots or user-triggered screen capture,
- performance counters,
- optional development-only command channel.

The bridge uses mutual authentication, project/build-scoped short-lived credentials and explicit user consent. Production builds never expose an unrestricted remote shell.

## 16. Sandbox Requirements

Every task sandbox is ephemeral and isolated.

MVP:

- separate workspace,
- CPU/RAM/disk/process limits,
- tenant-isolated storage,
- scoped network,
- short-lived credentials,
- immutable base images,
- destroy after task.

Toolchain-specific worker images:

- Flutter Linux build image,
- React Native Android image,
- Native Android image,
- Next.js image,
- Go/Python backend images,
- macOS build worker for any iOS target.

Advanced:

- gVisor/Kata/Firecracker-style isolation for higher-risk arbitrary code execution.

---

## 17. Build Pipelines by Profile

### Flutter

```text
Dart source
 -> static analysis/tests
 -> Android build on Linux
 -> iOS compile/sign on macOS
 -> optional Flutter Web build on Linux
```

### React Native

```text
TS/RN source
 -> lint/typecheck/tests
 -> Android build on Linux
 -> iOS compile/sign on macOS
 -> optional RN Web/Expo Web on Linux
```

### Native

```text
Kotlin/Compose -> Linux Android build
Swift/SwiftUI -> macOS iOS build
```

### Web/Admin

```text
Next.js -> Linux build -> preview/staging/production
```

### Backend

```text
Go/Python -> Linux build/test -> container -> staging/production
```

---

## 18. Model Gateway

```text
Product -> Context/Cost Controller -> Model Gateway -> Router -> approved providers/private endpoints
```

Routing inputs:

- task type and risk,
- benchmark/quality score,
- cost and token budget,
- latency,
- context size,
- framework/language expertise score,
- provider availability/error rate,
- customer data/provider policy,
- BYOK/private-endpoint constraints.

### 18.1 LLM escalation ladder

Use deterministic software before a model whenever possible:

```text
L0 Deterministic engine
   grep/AST/LSP/compiler/Git/schema/test parser
      -> if reasoning needed
L1 Small/cheap model
   classify/summarize/rank/rewrite metadata
      -> if implementation needed
L2 Coding model
   scoped feature/bug work
      -> if complex/high-risk
L3 Strong reasoning model
   architecture/security/concurrency/hard repair
      -> only when critical
L4 Independent reviewer/model
   high-risk release/security/payment/signing work
```

Never ask an LLM to answer a fact that a deterministic tool already knows, such as whether compilation passed, which symbol imports another symbol, the current Git diff or current DB schema.

### 18.2 Context Budget Controller

Each run stores and enforces budgets for:

- maximum input/output tokens per stage,
- maximum model calls/retries,
- maximum retrieved code/context,
- maximum expensive-model escalation,
- maximum Linux/Android/macOS minutes,
- maximum tool/integration spend.

The Context Manager compresses long agent runs into evidence-backed checkpoints and re-fetches authoritative data when needed. Large compiler/log outputs are parsed to concise relevant failures before being sent to a model.

### 18.3 Provider abstraction

No product business logic directly imports a provider SDK. Implement a ModelProvider contract with routing, fallback, circuit breakers, idempotent accounting and observability. BYOK is a profile; private/self-hosted endpoints are advanced profiles.

### 18.4 Cost accounting

Track cost per successful task, not just tokens. A successful-task cost includes model calls, sandbox minutes, Mac minutes, storage, bandwidth, build cache misses and third-party tool costs. Failed retries caused by OmniStackAI infrastructure/agent defects must be bounded and normally absorbed rather than repeatedly charged to the user.

## 19. Testing and Regression Gates

MVP mandatory:

- compile/typecheck affected targets,
- unit tests,
- integration tests,
- API contract tests,
- critical E2E smoke,
- database migration safety,
- regression gate,
- SAST/dependency scan,
- blast-radius check.

Framework-specific examples:

- Flutter: analyzer + widget/unit/integration tests.
- React Native: TypeScript + Jest/component/E2E + Android/iOS build validation.
- Android Native: Gradle compile/unit/instrumentation where required.
- iOS Native: Xcode compile/unit/UI tests where required.
- Next.js: typecheck/unit/component/browser E2E.

MID:

- visual regression,
- accessibility,
- DAST,
- performance budgets,
- SBOM/license policy,
- framework upgrade compatibility.

ADVANCED:

- physical devices,
- fuzz/mutation testing for critical modules,
- cross-framework consistency checks.

---

## 20. Git and Recovery

- branch/worktree per task,
- main contains only accepted changes,
- automatic checkpoint after stable milestones,
- revert rather than destructive conversation rollback,
- cherry-pick useful later changes,
- task stores plan, diff, tests, model/version, framework, usage and commit,
- one IR/ADR update is committed with architecture-affecting changes.

Never make chat history the only recovery mechanism.

---

## 21. Security Rules

- multi-tenant isolation with zero cross-talk,
- least-privilege agent/tool identities,
- Vault/KMS/HSM-backed secret and signing storage,
- **Secret Broker**: agents reference scoped secret capabilities; raw production secrets are not inserted into prompts,
- short-lived credentials and workload identity,
- prompt-injection defense: repository/docs/tool output are untrusted data,
- default-deny network egress to internal/private infrastructure,
- dependency/license scanning and approved dependency catalogs,
- SAST/DAST where appropriate,
- SBOM and release provenance,
- artifact/container signing (for example Sigstore/Cosign-compatible workflow),
- immutable audit logs for tool calls, approvals, signing and deployment,
- mobile signing isolation from coding sandboxes,
- TLS + encryption at rest,
- CODEOWNERS/protected paths for sensitive modules,
- risk-based human approval,
- enterprise SSO/data residency/policy-as-code/BYOC later.

Local Agent:

- opt-in only,
- signed binary/application,
- mutual authentication,
- scoped directories,
- explicit command/tool allowlist,
- no hidden/unrestricted shell,
- signed update verification,
- audit every command/job,
- immediate revoke/disconnect.

Release credentials and signing keys are **capabilities**, not model-readable strings. Coding agents cannot read or export them.

## 22. Billing and Cost Rules

Recommended plans:

- Free: prototypes + browser preview.
- Developer: individual development.
- Pro: more projects/build minutes/mobile targets.
- Agency: teams + many client projects.
- Enterprise: SSO/VPC/BYOC/audit/data residency/SLA.
- BYOK: customer-owned LLM keys.

Cost rules:

- show estimated credits before expensive tasks,
- internal compile verification is included in feature-generation price,
- do not repeatedly charge for retries caused by platform/agent failures,
- interactive cloud iOS Simulator consumes extra Mac credits/minutes,
- Local Mac Agent avoids cloud Mac compute charge,
- track model tokens, Linux minutes, Mac minutes, storage and bandwidth per task,
- cross-platform projects should normally cost less than two separate native apps.

---

## 23. Observability and Analytics

Track at minimum:

- task success by framework,
- first-attempt build success,
- final task success within bounded retries,
- regression escape rate,
- unexpected blast radius rate,
- deployment success,
- model cost per successful task,
- Linux minutes per successful task,
- Mac minutes per successful iOS task,
- browser-preview-to-real-native-run ratio,
- build cache hit rate,
- repo size/growth,
- dependency graph growth,
- framework/plugin upgrade failure rate,
- gross margin by plan/framework/task type,
- support incidents by framework/version.

---

## 24. Phase Roadmap

### MVP

Goal: reliable cost-efficient multi-platform generation.

Architecture must support all target adapters, but delivery can be sequenced if the team is small.

Recommended rollout inside MVP:

1. Application IR + framework adapter contract.
2. Auto/Recommended selector.
3. Flutter target first if team capacity is limited.
4. React Native target next using the same IR.
5. Native Kotlin/Swift generation as Beta after change-impact and regression gates are stable.
6. Next.js Web/Admin.
7. Go/Python backend.
8. Customer project monorepo.
9. Platform modular monorepo.
10. Git branches/checkpoints/PR model.
11. Browser previews.
12. Compile/test/security gates.
13. Web/backend deploy.
14. Android release builds.
15. iOS compile/release build through macOS worker.

If the team is large enough, Flutter and React Native adapters can be developed in parallel, but do not build three independent architectures. They must all sit behind the same IR and agent contracts.

### MID

Goal: professional developer product.

Add:

- Native Kotlin/Swift GA,
- streamed Android emulator,
- streamed iOS Simulator,
- Local Mac Agent,
- Flutter Web optional profile,
- RN Web/Expo Web optional profile,
- verified integrations,
- visual regression,
- environment parity,
- App Store/Play Store automation,
- RBAC/review workflow,
- BYOK,
- existing repository import,
- long-project memory compaction,
- CODEOWNERS/protected paths,
- repository/build health metrics,
- repo-split recommendation.

### ADVANCED

Goal: enterprise flexibility and scale.

Add:

- existing multi-repo orchestration,
- framework migration planning,
- optional hybrid/native modules,
- physical device cloud,
- model benchmark service,
- private/self-hosted models,
- microVM sandbox,
- BYOC/VPC,
- data residency,
- policy-as-code,
- multi-region,
- cross-platform consistency checker,
- predictive compute scheduler,
- enterprise multi-repo mode.

### PRODUCTION READY

Blocking gates:

- SLO/SLA,
- HA control plane,
- backup/restore drills,
- disaster recovery,
- tenant isolation validation,
- independent penetration test,
- SOC2-ready controls,
- 24x7 incident process,
- capacity/load tests,
- spending caps/kill switches,
- full release qualification,
- canary platform releases,
- privacy/retention/deletion controls,
- billing reconciliation/unit economics,
- signing-key hardening,
- framework/version compatibility matrix.

---

## 25. MVP Anti-Overengineering Rules

Do not build these too early:

- Kafka when NATS/managed queue is enough,
- dedicated vector DB when pgvector is enough,
- dozens of microservice repositories,
- service-per-repo for generated customer apps,
- Flutter + RN + Native as three unrelated generation systems,
- Flutter Web as mandatory public website,
- RN Web as mandatory admin panel,
- physical device cloud before emulator/simulator pipeline is stable,
- dozens of specialist agents without benchmark evidence,
- production write/deploy permissions for normal coding agents,
- Bazel/Pants before build metrics prove need.

The correct strategy is **one IR, one project model, framework adapters**.

---

## 26. Standard AI Task Contract

```yaml
task_id: FAV-DRIVER-001
goal: Customer can add/remove a favourite driver.
project_profile:
  mobile: flutter
  web: nextjs
  admin: nextjs
  backend: go
  repo: customer_project_monorepo

platforms: [mobile, web, backend]
affected_roles: [customer]

expected_impact:
  entities: [FavouriteDriver]
  apis:
    - POST /favourites/drivers/{driverId}
    - DELETE /favourites/drivers/{driverId}
    - GET /favourites/drivers
  modules:
    - apps/mobile-flutter
    - apps/web
    - services/api
    - packages/contracts

must_not_change:
  - authentication_semantics
  - fare_calculation
  - driver_assignment_logic

acceptance:
  - add/remove is idempotent
  - UI reflects server state after refresh
  - unauthenticated access is rejected
  - existing booking regression remains green

required_gates:
  - impact_analysis
  - compile_affected_targets
  - unit_test
  - integration_test
  - api_contract_test
  - security_authorization_review
  - regression_gate
  - blast_radius_check
```

---

## 27. Definition of Done for Every AI Task

- [ ] Requirement recorded.
- [ ] Acceptance criteria recorded.
- [ ] Framework/profile is known.
- [ ] Impact plan created before edits.
- [ ] Actual diff matches expected impact or exception approved.
- [ ] Affected targets compile/typecheck.
- [ ] Required tests pass using real tool output.
- [ ] Security gates pass.
- [ ] Cross-target contracts remain compatible.
- [ ] Cost/model/tool trace saved.
- [ ] Accepted commit/PR created with task ID.
- [ ] IR/ADR/project memory updated when needed.

---

## 28. Core KPI Targets

- First-attempt build success: >=70% MVP, improve continuously.
- Final task success: >=95% within bounded retries.
- Regression escape rate: <2% MVP, target <0.5%.
- Unexpected blast radius: <5% MVP, target <1%.
- Deployment success: >=98%.
- Critical security issues released: 0.
- LLM cost per successful task: trend down.
- Mac minutes per successful iOS task: trend down.
- Build cache hit rate: trend up.
- Framework upgrade failure rate: trend down.
- Gross margin by plan/framework/compute class: visible before production scale.

---

## 29. Final Engineering Positioning

The product is not just a prompt-to-code generator.

It is:

```text
AI Engineering Team
+ Product Architect
+ Framework Recommendation Engine
+ Application IR
+ Change Impact Engine
+ Compiler/Build Farm
+ QA
+ Security
+ Git
+ DevOps
+ Cost Controller
```

The main commercial rule is:

> Cross-platform by default for cost and speed. Native by choice or measured complexity. Web/admin optimized independently. One IR keeps every target consistent.

The main repository rule is:

> Modular monorepo for our platform. One monorepo per customer project by default. Split only from evidence, never because microservices or multi-repo sounds more advanced.

---

## 30. Competitor Reference Notes

Keep competitor observations in a separate research/source layer and re-verify before marketing use.

Reference pages from the earlier research set:

- https://help.emergent.sh/mobile-app-development
- https://help.emergent.sh/faqs
- https://help.emergent.sh/context-limits
- https://help.emergent.sh/rollback-feature
- https://help.emergent.sh/platform-documentation
- https://help.emergent.sh/deployment-information

---

## 31. Framework Decision Wizard - Exact Product Behavior

This wizard is shown before first generation. The user can always override the recommendation.

```text
Step 1 - What are you building?
Mobile app | Web app | Admin panel | Full product

Step 2 - Mobile engineering preference
(*) Auto / Recommended
( ) Flutter
( ) React Native
( ) Native Android + Native iOS
( ) Web/PWA only

Step 3 - Important requirements
[ ] Fastest launch / lowest cost
[ ] Existing React/TypeScript team
[ ] Highly custom consistent mobile UI
[ ] Deep camera/BLE/NFC/sensors
[ ] Heavy background location/tasks
[ ] High-performance media/graphics
[ ] Strict platform-specific controls
[ ] Existing native SDKs
[ ] Strong SEO/public website
[ ] Complex desktop admin/operations

Step 4 - Platform recommendation
Recommended: Flutter / React Native / Native
Why: simple explanation
Cost class: Low / Medium / High
Codebases: number of major runtime codebases
Real iOS verification: Browser Preview / Cloud Mac / Local Mac
Web strategy: Next.js or approved shared-web profile
Admin strategy: Next.js

Step 5 - User confirms or overrides
```

### Recommendation rule

Use measurable requirements. Do not hard-code by industry.

- Small/medium standard mobile product -> prefer Flutter or React Native.
- React/TypeScript organization -> prefer React Native when capability fit is good.
- Strongly custom mobile UI and one mobile team -> Flutter is often a good fit.
- Deep platform APIs, heavy background work, platform-specific SDKs or measured performance need -> recommend Native.
- Fintech, e-commerce, mobility and healthcare are not automatically Native. Complexity and compliance requirements decide.

### Recommendation score model

The decision engine should store a score and reasons in Application IR.

Example weights:

```text
Cost / speed sensitivity              -> cross-platform +3
Existing React/TypeScript team        -> React Native +4
Custom consistent mobile UI           -> Flutter +3
Need web component/domain reuse        -> React Native +2
Deep platform APIs / native SDKs       -> Native +5
Complex background execution           -> Native +5
Heavy media / low-latency rendering    -> Native +5
Special hardware integration           -> Native +5
Platform-specific UX is core product   -> Native +3
```

The score is guidance, not an irreversible rule.

---

## 32. Code Sharing Policy - Share the Right Things

The platform must optimize total engineering cost, not chase a fake "100% shared code" percentage.

### Always try to share

- API contracts,
- event contracts,
- validation schemas,
- design tokens,
- localization keys,
- analytics event names,
- permissions definitions,
- feature flags,
- test fixtures,
- business rules expressed in Application IR.

### React Native + Next.js can additionally share

- TypeScript types,
- schema validation,
- API clients,
- selected domain logic,
- selected utility packages,
- selected UI primitives only when browser/mobile behavior remains correct.

### Flutter + Web

Flutter mobile uses Dart. Next.js uses TypeScript. Share contracts and generated rules rather than forcing runtime code sharing.

Flutter Web can be selected for an app-like web target, but it is not the default for public SEO websites or complex admin panels.

### Native mobile

Kotlin and Swift runtime code is separate. Keep both consistent through:

- Application IR,
- OpenAPI/AsyncAPI contracts,
- design tokens,
- acceptance tests,
- generated API clients,
- cross-target behavior tests.

### Core rule

> Share specifications and contracts first. Share runtime code only when it is naturally compatible and does not make a target worse.

---

## 33. Our Platform Architecture - MVP to Production

### MVP architecture

Do not begin with dozens of microservices.

```text
Browser / Next.js Console
        |
        v
Go Control Plane (modular monolith)
  - Auth / Organizations / Workspaces / Projects
  - Job API / Usage / Basic Billing
  - Git integration / Audit
        |
        +--------------------+
        |                    |
        v                    v
Python Agent Service      Runner Manager
  - Planning              - Linux sandboxes
  - Model gateway         - build jobs
  - Context/RAG           - artifact upload
  - Tool execution
        |
        v
PostgreSQL + pgvector
Redis
NATS or managed queue
S3-compatible object storage
```

Canonical platform repository name:

```text
omnistackai-platform
```

Internal example:

```text
omnistackai-platform
```

### MVP platform monorepo

```text
omnistackai-platform/
  apps/
    console-web/                 # Next.js product UI

  services/
    control-plane/               # Go modular monolith
    agent-engine/                # Python agent orchestration/model gateway
    runner-manager/              # Go job/sandbox scheduler

  workers/
    linux-runner/
    android-runner/
    web-runner/
    mac-runner-controller/       # controller only; actual worker is macOS

  packages/
    contracts/
    policy-schemas/
    telemetry/
    ui/
    agent-sdk/

  ai/
    prompts/
    tools/
    evals/
    benchmark-cases/
    safety-policies/

  infra/
    terraform/
    kubernetes/
    environments/

  docs/
    adr/
    runbooks/
    security/

  scripts/
  Taskfile.yml
  README.md
```

### MID architecture

Split only components that have proven independent scaling or security needs.

Typical candidates:

- model gateway,
- billing/entitlements,
- build service,
- code intelligence/indexing,
- realtime preview gateway,
- macOS build coordinator.

### ADVANCED architecture

Add:

- multi-region workers,
- enterprise private runners,
- BYOC,
- multi-repo orchestration,
- dedicated policy engine,
- physical device cloud integration,
- advanced eval platform,
- workload-aware scheduling.

### PRODUCTION READY

Require:

- HA control plane,
- tested backup/restore,
- disaster recovery,
- tenant isolation evidence,
- penetration test,
- full audit trails,
- SLOs/error budgets,
- capacity planning,
- unit economics alerts,
- incident runbooks.

---

## 34. Customer Git Strategy and Naming

### Default

One Git repository per customer product. Inside that repository, use a monorepo.

Recommended name:

```text
<organization-slug>-<product-slug>
```

Example:

```text
acme-rider
mobility-taxi-suite
```

If the platform owns the temporary repo before customer Git is connected:

```text
project-<project-id>-<slug>
```

Never expose internal numeric IDs as the only human-readable name.

### Why monorepo is the default

A single feature may modify:

- mobile,
- web,
- admin,
- backend,
- database,
- API contracts,
- tests.

One branch and one PR can keep that change atomic.

### Customer root structure

```text
<org>-<product>/
  .ai/
  apps/
  services/
  packages/
  database/
  infra/
  tests/
  docs/
  scripts/
  .github/ or .gitlab/
  Taskfile.yml
  README.md
```

### Git branch rules

```text
main                               # protected
ai/<task-id>-<short-slug>          # AI work
fix/<ticket>-<short-slug>          # human hotfix
release/<version>                  # only when release process needs it
```

Prefer trunk-based development with short-lived branches.

### Commit format

```text
<type>(<scope>): <summary> [<task-id>]
```

Examples:

```text
feat(booking): add favourite driver [FAV-001]
fix(payment): handle expired intent [PAY-014]
```

### Split to multiple repos only when measured need exists

Examples:

- independent teams with independent release cycles,
- separate compliance/access boundaries,
- customer already has a mature multi-repo environment,
- build/indexing remains unacceptable after caching and optimization,
- services have clear stable contracts and ownership.

The AI must never silently split a project repository.

---

## 35. Generated Project Root - Production-Grade Standard

Every generated project follows the same root contract so agents and developers can understand it immediately.

```text
<org>-<product>/
  .ai/
    ir/                            # canonical Application IR
    adr/                           # architecture decisions
    policies/                      # allowed dependencies, protected paths
    tasks/                         # accepted task summaries, not chat dumps
    baselines/                     # visual/API/quality baselines

  apps/                            # user-facing applications
  services/                        # deployable backend services/workers
  packages/                        # shared contracts/tokens/generated clients
  database/                        # schema/migrations/seeds
  infra/                           # IaC/deployment manifests
  tests/                           # cross-product E2E/contract/load fixtures
  docs/                            # human docs/runbooks/API architecture
  scripts/                         # deterministic automation

  .editorconfig
  .gitignore
  .gitattributes
  Taskfile.yml
  README.md
```

Rules:

- Feature code stays near its feature.
- Shared modules need a real reuse case; do not create a `utils` dumping ground.
- Secrets never enter Git.
- Generated files are clearly marked and reproducible.
- Every deployable target has its own README, test command and build command.
- Root Taskfile/Make exposes stable commands to AI agents regardless of framework.

Canonical commands:

```text
task bootstrap
task lint
task test
task build
task check
task preview
task ci
```

---

## 36. Flutter Project Structure - Optimized Default

Use feature-first architecture. Do not create hundreds of layers for a small app.

```text
apps/mobile-flutter/
  lib/
    app/
      app.dart
      bootstrap.dart
      router/
      di/
      theme/

    core/
      api/
      auth/
      config/
      error/
      logging/
      storage/
      telemetry/

    design_system/
      components/
      tokens/
      icons/

    features/
      auth/
        data/
        domain/
        presentation/
      booking/
        data/
        domain/
        presentation/
      profile/
        data/
        domain/
        presentation/

    shared/
      models/
      widgets/

    l10n/
    main.dart

  test/
  integration_test/
  assets/
  android/
  ios/
  web/                 # only used when flutter_web target is selected
  pubspec.yaml
  analysis_options.yaml
```

Rules:

- `features/` owns feature behavior.
- `core/` is infrastructure used by many features.
- `shared/` stays small; move code back into a feature when reuse is not real.
- State-management package is selected once by ADR; agents may not mix multiple patterns without approval.
- Platform channels/native plugins go behind explicit adapters.
- Use flavors/config for dev/staging/prod.
- Keep generated API client in a dedicated package or generated folder, not mixed with manual code.

MVP can simplify each feature to `data + presentation` if domain complexity is low. Add deeper domain/use-case layers only when needed.

---

## 37. React Native Project Structure - Optimized Default

Prefer TypeScript. Expo can be the default profile when its native capability set fits; allow bare React Native/native modules when required.

```text
apps/mobile-react-native/
  src/
    app/
      App.tsx
      providers/
      navigation/
      config/

    features/
      auth/
        api/
        model/
        ui/
        hooks/
      booking/
        api/
        model/
        ui/
        hooks/

    shared/
      api/
      auth/
      storage/
      telemetry/
      config/

    design-system/
      components/
      tokens/
      icons/

    services/
    assets/
    i18n/

  __tests__/
  e2e/
  android/
  ios/
  app.config.ts
  package.json
  tsconfig.json
```

If the customer repo also contains Next.js, reusable TypeScript packages live at root:

```text
packages/
  contracts-ts/
  validation-ts/
  api-client-ts/
  analytics-schema-ts/
  design-tokens/
```

Do not share React Native UI components with Next.js when doing so harms accessibility, SEO or desktop behavior.

---

## 38. Native Android Project Structure - Experienced Team Standard

Use Kotlin + Jetpack Compose. Start with sensible modules and expand only when build/team complexity requires it.

```text
apps/android/
  app/

  core/
    common/
    model/
    designsystem/
    ui/
    network/
    database/
    datastore/
    analytics/
    testing/

  feature/
    auth/
    booking/
    payments/
    profile/

  build-logic/
    convention/

  gradle/
    libs.versions.toml

  build.gradle.kts
  settings.gradle.kts
```

Recommended feature module internal structure:

```text
feature/booking/
  src/main/java/.../booking/
    data/
    domain/
    presentation/
    navigation/
```

Rules:

- Gradle Version Catalog for dependencies.
- Convention plugins in `build-logic` to remove copied Gradle configuration.
- Compose UI + unidirectional state flow.
- Coroutines/Flow for async state.
- DI standard selected once.
- Network/database hidden behind interfaces used by features.
- No Activity/Fragment/object passed into persistence or JSON models.
- Feature modules depend on approved core modules, not other features directly unless architecture explicitly allows it.

For very small MVP apps, combine core modules to reduce build overhead. The template engine should have `lean` and `scaled` variants.

---

## 39. Native iOS Project Structure - Experienced Team Standard

Use Swift + SwiftUI and Swift concurrency. Prefer local Swift Packages for modular boundaries once the project size justifies them.

Lean structure:

```text
apps/ios/
  App/
    AppEntry/
    Navigation/
    DI/

  Core/
    Models/
    Networking/
    Persistence/
    Auth/
    Analytics/
    DesignSystem/

  Features/
    Auth/
      Data/
      Domain/
      Presentation/
    Booking/
      Data/
      Domain/
      Presentation/

  Resources/
  Tests/
  UITests/
  Project.xcodeproj
```

Scaled structure:

```text
apps/ios/
  App/
  Packages/
    CoreModels/
    Networking/
    Persistence/
    DesignSystem/
    FeatureAuth/
    FeatureBooking/
  Tests/
  UITests/
```

Rules:

- SwiftUI + async/await by default.
- Actor/isolation rules for shared mutable state.
- Dependency injection at composition roots.
- Keychain wrapper for secrets/tokens; never store sensitive values in UserDefaults.
- Generated API client stays separate from hand-written domain code.
- Platform signing secrets are external to Git.
- Real compile/simulator/signing requires macOS, but browser preview is available from any OS.

Do not introduce Tuist/XcodeGen in the earliest template unless deterministic project generation or module scale proves the benefit. They can be an advanced profile.

---

## 40. Next.js Public Web Structure

```text
apps/web/
  src/
    app/                          # routes/layouts/server components
    features/
      auth/
      catalog/
      booking/
    components/
    design-system/
    lib/
      api/
      auth/
      config/
      telemetry/
      validation/
    hooks/
    types/

  public/
  tests/
  e2e/
  next.config.*
  package.json
```

Rules:

- Next.js App Router by default.
- Prefer server components where they reduce client JavaScript without harming UX.
- Keep client-only state at the smallest boundary.
- SEO metadata, accessibility and Core Web Vitals are quality gates for public web.
- API client/contracts are generated from canonical contracts.
- Never expose server secrets in browser bundles.

---

## 41. Admin Panel Structure

Admin is a separate product target because its UX, permissions and data density differ from mobile/public web.

```text
apps/admin/
  src/
    app/
    modules/
      users/
      orders/
      payments/
      operations/
      reports/
    components/
      data-grid/
      filters/
      forms/
      charts/
    auth/
    rbac/
    audit/
    lib/
      api/
      permissions/
      telemetry/
      exports/
    design-system/

  tests/
  e2e/
  package.json
```

Quality rules:

- Desktop/tablet first.
- RBAC/ABAC permissions from centralized policy definitions.
- Server-side pagination/filtering for large datasets.
- Audit logs for sensitive operations.
- Confirmation/approval flow for destructive actions.
- Export jobs should be asynchronous when data is large.
- Admin should not be forced into Flutter Web or React Native Web only to increase code-sharing percentage.

---

## 42. Backend Project Structures

Generated backends can use Go or Python. Node/NestJS is optional when justified.

### Go default

```text
services/api/
  cmd/
    api/
      main.go

  internal/
    app/
    config/
    domain/
      user/
      booking/
      payment/
    application/
      commands/
      queries/
    adapters/
      http/
      postgres/
      redis/
      messaging/
      external/
    platform/
      auth/
      observability/
      validation/

  migrations/
  tests/
  go.mod
```

Rules:

- Domain does not depend on HTTP/database frameworks.
- Transactions are explicit.
- Idempotency is required for payment/webhook/critical mutation flows.
- Context cancellation/timeouts propagate.
- Structured logging + traces + metrics from day one.

### Python default

```text
services/api/
  app/
    main.py
    api/
    core/
    domain/
    application/
    infrastructure/
      db/
      cache/
      messaging/
      external/
    schemas/
    observability/
  migrations/
  tests/
  pyproject.toml
```

Rules:

- Typed models and validation.
- Async only when it helps the workload; do not mix sync/async carelessly.
- Domain logic stays out of route handlers.
- Migrations are versioned and reversible where possible.

### Workers

Create `services/workers/` only when async workloads actually exist, such as:

- notifications,
- document generation,
- image processing,
- scheduled tasks,
- long-running integrations.

Do not create a separate microservice for every noun in the product.

---

## 43. API Contracts and Generated Clients

Contracts are a primary cross-platform consistency mechanism.

```text
packages/contracts/
  openapi/
    public-api.yaml
  asyncapi/
    events.yaml
  schemas/
  examples/
```

Generation outputs can include:

```text
packages/generated/
  dart-client/
  typescript-client/
  kotlin-client/
  swift-client/
```

Rules:

- Contract change is reviewed before target code regeneration.
- Breaking change requires versioning/migration plan.
- Client regeneration must be deterministic.
- Generated code is not hand-edited.
- Contract tests run against backend and required consumers.

---

## 44. CI/CD Standard for Every Generated Project

Minimum pipeline:

```text
PR opened
  -> Validate IR/architecture policy
  -> Format/Lint
  -> Static analysis
  -> Unit tests
  -> Contract tests
  -> Build affected targets
  -> Security/dependency scan
  -> E2E/visual tests selected by impact
  -> AI review + blast-radius check
  -> Human approval when risk policy requires
  -> Merge
```

Post-merge:

```text
main
  -> immutable artifacts
  -> preview/dev
  -> staging
  -> production approval
  -> progressive deploy
  -> automated health check
  -> rollback if SLO fails
```

Target-specific rules:

- Flutter/RN Android builds use Linux where possible.
- Any real iOS build, simulator or signing uses macOS.
- Native Android uses Linux Gradle workers.
- Web/admin use Linux/Node build workers.
- Backend uses reproducible container builds.

Cache:

- dependencies,
- Gradle,
- Dart/Flutter packages,
- npm/pnpm,
- build intermediates where safe,
- generated clients.

Do not cache secrets or user-specific sensitive output.

---

## 45. Cross-Platform to Native Migration Path

A customer must not become trapped by the original framework choice.

If a Flutter or React Native product outgrows cross-platform constraints:

```text
1. Measure the problem.
2. Record ADR and migration reason.
3. Identify affected capability/feature.
4. First prefer a small native adapter/module if it solves the problem safely.
5. If the entire target needs native, generate a parallel native app from Application IR + contracts.
6. Run behavior/visual parity tests.
7. Migrate feature-by-feature or release-by-release.
8. Retire old target only after verified parity.
```

The Application IR, API contracts and acceptance criteria make this migration possible without re-discovering product behavior from source code alone.

---

## 46. Template Governance and Dependency Policy

Every framework template has a versioned manifest.

```yaml
template:
  id: flutter-mobile-standard
  version: 3
  maturity: stable
  supported_platforms: [android, ios]
  architecture_profile: feature-first
  required_checks: [format, lint, unit, build]
```

Rules:

- Approved dependency catalog per template.
- New dependency requires license/security/maintenance evaluation.
- Lockfiles are committed.
- Framework/toolchain upgrades happen through controlled template upgrades, not random agent edits.
- Agents cannot silently switch state-management, DI, navigation or networking frameworks.
- Deprecation policy records supported template versions.

---

## 47. Phase-by-Phase Framework and Repository Delivery

### BASIC / MVP

Must ship:

- Auto/Recommended stack wizard.
- Flutter target stable.
- React Native target stable or controlled beta based on team capacity.
- Native Kotlin/Swift selectable beta.
- Next.js web/admin.
- Go/Python backend.
- One customer product = one monorepo.
- Platform modular monorepo.
- Application IR, contracts, Git branches, change impact, tests.
- Browser previews for all targets.
- Cloud iOS compile verification for generated native/cross-platform iOS code.

Do not ship every framework combination at equal maturity if quality suffers. It is better to label maturity honestly.

### MID

Add:

- Native Android/iOS GA.
- Real cloud Android/iOS interactive simulator sessions.
- Local Mac Agent.
- Existing repository import.
- Framework upgrade agent.
- advanced build caching.
- repo/build health metrics.
- BYOK.
- optional Flutter Web and RN Web profiles.

### ADVANCED

Add:

- enterprise multi-repo orchestration,
- private runners/BYOC,
- physical-device testing,
- cross-platform-to-native guided migration,
- advanced template marketplace,
- policy-as-code,
- private model endpoints,
- regional execution/data residency.

### PRODUCTION READY

Gate on measurable outcomes, not feature count:

- build success,
- regression rate,
- deployment success,
- security findings,
- restore/DR tests,
- tenant isolation,
- cost per successful task,
- support/incident readiness.

---

## 48. Additional Rules That Prevent Common AI Builder Problems

1. **No unrelated edits.** Change Impact Engine defines allowed blast radius.
2. **No full-file rewrite by default.** Use symbol/AST/structured patches.
3. **No architecture drift.** ADRs and dependency rules are enforced in CI.
4. **No hidden framework switching.** Framework profile is immutable unless user approves a migration task.
5. **No fake code sharing.** Optimize each target while sharing contracts/rules.
6. **No destructive rollback.** Git revert/cherry-pick/checkpoints preserve later work.
7. **No endless retry billing.** Internal failed retries are bounded and priced into task cost where possible.
8. **No preview-only confidence.** Production target must compile/test in the real toolchain.
9. **No production secrets in agents.** Use short-lived scoped brokered credentials.
10. **No permanent user sandboxes.** Use ephemeral isolated execution and immutable artifacts.
11. **No dependency explosion.** Templates use approved catalogs and upgrade policy.
12. **No premature microservices/multi-repo.** Split only from measured scale/security/ownership need.
13. **No lost project context.** IR + ADR + repo graph + accepted task summaries are persistent.
14. **No unverified schema change.** Migration/backfill/rollback and compatibility checks are mandatory.
15. **No one-model dependency.** Model gateway has routing, fallback, budgets and quality evaluation.

---

## 49. Final Recommended Default Product Configuration

For a normal new customer project:

```text
Mobile: Auto / Recommended
  -> usually Flutter or React Native for small/medium standard products
  -> Native only when requirements justify it or user explicitly selects it

Public Web: Next.js
Admin: Next.js
Backend: Go or Python
Database: PostgreSQL
Cache: Redis when needed
Async Events: NATS/managed queue when needed
Repository: one monorepo for the customer product
Contracts: OpenAPI + generated clients
Preview: browser preview included
Real iOS: cloud Mac credits OR optional Local Mac Agent
Git: protected main + short-lived task branches
Deployment: immutable build artifacts + staged promotion
```

The platform should explain every major architecture choice in plain language and persist it as an ADR so later AI agents cannot silently reverse the decision.


---

## 50. V4 Reference Study - What We Keep, Change and Reject

This section refines earlier architecture using the team reference study. If a V4 rule conflicts with an older section, the V4 rule wins.

### Core conclusion

The V3 blueprint is broader than the reference document because it already covers multi-platform generation, Application IR, change-impact control, AST/structured editing, native/cross-platform choices, repository architecture, testing, security, Git recovery, deployment and cost controls.

The reference study is still valuable because it adds concrete implementation patterns and technologies that should be benchmarked before we build everything ourselves. We should **borrow patterns, not blindly copy products or source code**.

| Reference | Useful idea | What not to copy blindly | Our decision |
|---|---|---|---|
| bolt.diy | Browser workbench, chat-to-actions flow, multi-model provider abstraction, WebContainer-based instant web runtime | Treating a JS/browser runtime as the universal sandbox | Use browser runtime only for eligible web/Node preview; keep server/mobile runtimes separate |
| beam lovable-clone | Small explicit tool definitions, agent + sandbox + streaming pattern | Demo-scale architecture as production architecture | Use only as a learning spike |
| OpenHands | Action -> observation loop, runtime boundary, error recovery, composable tools/workspaces | Tight coupling between agent logic and one sandbox/runtime | Create our own Runtime/Sandbox Provider interface and event ledger |
| Dyad | Local-first execution, privacy, BYOK and no lock-in | Local-only product model | Add optional Local/Private execution mode while keeping cloud builds and deployment |
| GPT Engineer | Historical baseline for whole-codebase generation | Whole-codebase rewriting as normal behavior | Keep only as a benchmark/anti-pattern; use impact-scoped patches |
| LangGraph | Durable execution, checkpointing, streaming and human-in-the-loop | Making platform domain logic depend directly on LangGraph APIs | Use behind an Orchestrator Adapter or replace with another durable engine later |
| CrewAI / AutoGen | Alternative delegation patterns | Framework-driven architecture | Benchmark, do not make core contracts depend on them |
| E2B / Daytona | Fast path to real isolated Linux sandboxes | Provider lock-in | Implement SandboxProvider abstraction; managed provider can be MVP implementation |
| WebContainers | Very fast browser-side Node/JS execution and preview | Native/Python/mobile execution | Tier-0 web runtime only |
| Supabase / Firebase / Atlas | Rapid generated-app backend options | Platform control-plane dependency or one mandatory customer backend | Offer as optional customer backend profiles |
| MCP | Standard tool/context extension surface | Unrestricted third-party tools | Add governed MCP Gateway + Tool Registry |
| OWASP | Security baseline | Treating a checklist as complete security | Map controls into automated release gates and threat models |

### Open-source / reference usage rule

Before reusing source or code structure from a reference repository:

1. record repository + commit reviewed,
2. record license and allowed use,
3. prefer clean-room implementation of architectural ideas,
4. do not copy source into proprietary modules without legal approval,
5. keep third-party notices/SBOM when code is intentionally reused.

---

## 51. Runtime and Sandbox Architecture - Tiered, Capability-Based and Cost-Aware

Do not use one sandbox technology for every task.

### Runtime tiers

```text
User Task
   |
   v
Capability Resolver
   |
   +--> Tier 0: Browser Runtime
   |      WebContainer / WASM-style runtime
   |      JS/TS/Node web preview only
   |
   +--> Tier 1: Managed Linux Sandbox
   |      E2B / Daytona / equivalent adapter
   |      Python/Go/Node/Dart/CLI/build/test
   |
   +--> Tier 2: Our Linux/Android Runner Fleet
   |      Kubernetes/microVM hardened execution
   |      production-scale web/backend/Android jobs
   |
   +--> Tier 3: macOS Runner
   |      Xcode, iOS simulator, signing, TestFlight build
   |
   +--> Tier 4: Local Agent / BYOC Runner
          trusted customer Mac/Windows/Linux or private VPC
```

### SandboxProvider contract

All execution providers implement the same platform interface:

```text
create(workspaceSpec) -> workspaceId
exec(workspaceId, command, limits) -> observation
readFile(workspaceId, path)
writePatch(workspaceId, patch)
exposePort(workspaceId, port) -> previewUrl
snapshot(workspaceId) -> snapshotRef
restore(snapshotRef) -> workspaceId
collectArtifacts(workspaceId) -> artifactRefs
terminate(workspaceId)
```

### Selection rules

- Use the **cheapest runtime that satisfies required capabilities**.
- WebContainer/browser runtime is allowed only when the project/task is JS/TS/Node compatible.
- Cloud execution of untrusted customer code is always isolated.
- Non-isolated execution is allowed only in an explicit trusted Local Agent mode.
- macOS capacity is allocated only for actual iOS compile/simulator/signing work.
- Every provider has CPU/RAM/disk/network/time quotas and usage metering.
- Runtime provider must be replaceable without rewriting agent logic.

### MVP provider strategy

MVP may start with a managed Linux sandbox provider to ship faster, but the code must depend on `SandboxProvider`, never directly on that vendor's SDK outside the adapter package.

---

## 52. Durable Agent Runtime - State, Checkpoints, Resume and Idempotency

Agent tasks may run for minutes or hours and must survive browser refreshes, worker crashes, provider failures and human approval pauses.

### Canonical run states

```text
CREATED
 -> SPECIFYING
 -> PLANNING
 -> WAITING_APPROVAL (optional)
 -> EXECUTING
 -> VERIFYING
 -> REVIEWING
 -> READY_TO_MERGE
 -> MERGED
 -> DEPLOY_PENDING (optional)
 -> DEPLOYING
 -> SUCCEEDED

Failure branches:
FAILED_RETRYABLE -> checkpoint -> retry
FAILED_FINAL
CANCELLED
```

### Hard requirements

- Persist task state after every meaningful agent/tool step.
- Every tool call has `run_id`, `task_id`, `step_id` and idempotency key.
- Side-effecting tool calls must be replay-safe or explicitly marked non-replayable.
- Resume from the last verified checkpoint instead of restarting the whole task.
- Store a compact event ledger in PostgreSQL; large logs/artifacts go to object storage.
- A browser disconnect must not cancel a server task unless the user explicitly requests cancellation.
- Tool/model retries are bounded and backoff-aware.
- Provider fallback must not duplicate side effects.
- Checkpoint format is platform-owned and independent of any one orchestration framework.

### Orchestration framework policy

LangGraph is a strong MVP candidate because durable execution, persistence, streaming and HITL are first-class capabilities. However:

```text
Platform Domain Logic
      |
      v
Orchestrator Interface
      |
      +--> LangGraph Adapter
      +--> Future internal runtime
      +--> Other durable workflow adapter
```

Agents, tasks, approvals and state schemas must not import vendor/framework types into core product contracts.

---

## 53. MCP Gateway and Tool Registry

MCP should become the standard extension path for external tools, data and integrations, but never bypass platform security.

### Architecture

```text
Agent
  |
  v
Tool Policy Engine
  |
  v
Tool Registry / MCP Gateway
  |
  +--> First-party platform tools
  +--> Verified MCP servers
  +--> Customer private MCP servers
  +--> Legacy internal adapters
```

### Every tool registration includes

- tool ID and version,
- provider/server identity,
- input/output schema,
- read/write/execute classification,
- risk class,
- allowed agent roles,
- required user/workspace scopes,
- network destinations,
- secret requirements,
- rate/cost limits,
- timeout/retry policy,
- audit policy,
- whether human approval is mandatory.

### Security rules

- A model cannot directly connect to arbitrary MCP servers.
- Customer MCP servers require explicit workspace installation and consent.
- Tool output is untrusted data and cannot override system/platform instructions.
- Secrets are brokered by the platform; raw long-lived secrets are not inserted into prompts.
- Tool permissions are capability-based and denied by default.
- Tool schemas and server capabilities are cached/versioned, but revalidated when server identity/version changes.
- Production tools and destructive tools require stronger approval policies than read-only tools.

### Product benefit

This lets us add GitHub, Jira, Slack, cloud providers, databases, design tools and customer systems without hard-coding every integration into the agent engine.

---

## 54. Human-in-the-Loop and Risk-Based Approval Policy

Human approval should be based on risk, not on every small change.

| Risk | Example | Default behavior |
|---|---|---|
| L0 - Read | read files, inspect logs, search docs | automatic |
| L1 - Normal Dev | scoped code patch, unit tests, preview | automatic after plan/impact checks |
| L2 - Material Change | new dependency, non-destructive migration, new external integration | policy-based approval; may auto-run for trusted workspace |
| L3 - Destructive / External Side Effect | destructive migration, delete data, production deploy, DNS change, send real messages, broaden secret scope | explicit human approval |
| L4 - Critical Enterprise | payment movement, signing-key policy change, mass delete, privileged infrastructure action | explicit privileged approval; optional two-person rule |

### Approval object

```text
approval_id
run_id
action_type
risk_level
plain_language_summary
exact_diff_or_tool_call
cost_estimate
side_effects
rollback_or_recovery_plan
expires_at
approved_by
```

### User experience

Always explain approval requests in plain language. Do not show only raw shell commands to non-developers.

---

## 55. Local-First, Hybrid and Private Execution Modes

The platform should support privacy/cost-sensitive customers without becoming a local-only product.

### Mode A - Cloud Standard

- source/workspace in platform cloud,
- managed model gateway,
- managed sandboxes,
- easiest onboarding.

### Mode B - Hybrid Local

- optional desktop/local agent on Mac, Windows or Linux,
- source can stay on the user's machine,
- tool execution can run locally,
- only approved context is sent to selected LLM providers,
- cloud macOS can still be used when local iOS tooling is unavailable,
- ideal for developers, agencies and privacy-sensitive teams.

### Mode C - Enterprise Private / BYOC

- control policies remain in our platform,
- runners/sandboxes live in customer VPC or private environment,
- optional private model endpoint/BYOK,
- region/data-residency controls,
- central audit and policy remain available.

### Local Agent requirements

- signed application/binary,
- explicit folder/workspace grants,
- no hidden full-disk access,
- mutually authenticated connection,
- permission prompts for sensitive operations,
- auto-update with signed releases,
- local execution logs visible to the user,
- revoke/disconnect at any time.

---

## 56. Generated Customer Backend Profiles - BaaS to Custom Services

Do not force every generated product to start with a custom backend if the customer needs speed and low cost.

### Backend option wizard

```text
Backend
  ( ) Auto / Recommended
  ( ) Rapid BaaS
  ( ) Managed Custom API
  ( ) Enterprise / Custom Architecture

Database
  (*) Auto / Recommended -> PostgreSQL default when no stronger reason exists
  ( ) PostgreSQL
  ( ) MongoDB
  ( ) Supabase/PostgreSQL
  ( ) Firebase/Firestore
  ( ) Existing customer database
```

### Profile A - Rapid BaaS

Good for prototypes and many small/medium apps.

Examples: Supabase or Firebase where requirements fit.

Can provide:

- authentication,
- database,
- object storage,
- realtime/subscriptions,
- serverless/functions where appropriate.

Do not use BaaS automatically when requirements need complex transactions, unusual compliance, custom networking, heavy background processing or portability constraints.

### Profile B - Managed Custom API

Default for serious commercial products.

```text
Go or Python API
PostgreSQL
Redis when required
Object storage
NATS/managed queue when required
OpenAPI contract
Generated clients
```

### Profile C - Enterprise / Custom

Use when measured requirements justify service separation, private networking, high throughput, regional deployment, custom identity or stricter compliance.

### Architecture portability rule

Application IR and domain contracts remain independent from the selected backend profile so a customer can migrate from BaaS to a custom backend without rewriting product requirements from scratch.

---

## 57. Real-Time Streaming Protocol for Agent UX

The user must see what the system is doing without coupling the frontend directly to agent internals.

### Transport

- WebSocket for bidirectional interactive sessions, approvals, terminal and simulator control.
- SSE may be used for simple one-way token/event streaming where bidirectional control is unnecessary.
- Reconnect must replay missed events from the persisted event ledger.

### Standard event envelope

```text
event_id
run_id
task_id
sequence
timestamp
type
stage
status
summary
payload_ref
cost_delta
tool_id
requires_approval
```

### Event types

```text
run.started
plan.updated
agent.started
model.delta
tool.requested
tool.started
tool.completed
file.patch
build.started
build.completed
test.result
approval.required
cost.updated
preview.ready
run.failed
run.completed
```

Do not make the UI parse vendor-specific model streams directly.

---

## 58. Architecture Research Lab, Build-vs-Buy and ADR Process

The reference document correctly treats exploration as input to architecture decisions, not proof of a decision. We should formalize this as a product-development rule.

### Mandatory spike before adopting major infrastructure

For sandbox providers, orchestration engines, MCP libraries, vector systems, queues, device clouds or BaaS providers, run a short benchmark and record:

- supported languages/toolchains,
- security/isolation model,
- cold-start latency,
- command/file latency,
- port/preview support,
- snapshot/restore support,
- network policy capability,
- secrets integration,
- concurrency/quota model,
- observability,
- geographic regions,
- cost per minute/task,
- vendor lock-in/exit path,
- license,
- operational burden,
- failure/recovery behavior.

### ADR template

Every important choice produces an ADR:

```text
ADR ID
Problem
Requirements
Options tested
Benchmark results
Security review
Cost model
Chosen option
Why
Rejected alternatives
Escape/migration strategy
Review date / trigger
```

### Initial architecture experiments

1. WebContainers vs cloud sandbox for instant Node/web preview.
2. E2B vs Daytona vs own runner for Linux execution.
3. Temporal managed vs self-hosted economics; custom/LangGraph agent graph behind a separate AgentGraphAdapter.
4. Cloud-only vs Hybrid Local Agent developer experience.
5. Supabase/Firebase vs custom backend for Rapid BaaS profile.
6. WebSocket event protocol at high concurrency and reconnect/replay behavior.

---

## 59. Phase-Wise Additions From the Reference Study

### MVP

Add these to the existing MVP scope:

- `SandboxProvider` abstraction.
- One managed Linux sandbox implementation.
- Browser runtime proof-of-concept for eligible JS/Node previews.
- durable task state + checkpointing + resume.
- standardized agent event ledger.
- WebSocket live progress with reconnect/replay.
- risk-based HITL approval policy.
- first-party Tool Registry.
- MCP Gateway foundation with MCP disabled for unverified servers by default.
- Temporal workflow adapter for durable execution; optional agent-graph framework remains replaceable.
- Build-vs-Buy/ADR benchmark process.
- Rapid BaaS architecture profile design, even if only one BaaS ships initially.
- team terminology/glossary.

### MID

- verified external MCP server installation flow,
- Local Agent for Mac/Windows/Linux,
- BYOK and hybrid local execution,
- additional sandbox provider adapter/failover,
- BaaS provider expansion,
- sandbox snapshots/warm pools where cost-effective,
- richer agent time-travel/debugging UI,
- tool marketplace with security verification,
- provider cost/latency auto-routing.

### ADVANCED

- customer private MCP servers,
- private/BYOC runners,
- cross-region runtime scheduling,
- own hardened microVM runner fleet where economics justify it,
- multi-provider sandbox failover,
- policy-as-code for agent/tool approvals,
- two-person enterprise approval workflows,
- customer-managed model endpoints,
- automated provider benchmark suite.

### PRODUCTION READY

Require measurable evidence for:

- task resume after worker crash,
- duplicate side-effect prevention,
- WebSocket reconnect/replay correctness,
- MCP permission isolation,
- malicious tool/resource prompt-injection tests,
- sandbox tenant isolation,
- provider outage failover,
- approval auditability,
- BaaS/custom-backend migration path tests,
- local-agent revoke/uninstall/security tests,
- open-source license/SBOM compliance.

---

## 60. Team Glossary - Required Shared Vocabulary

| Term | Platform meaning |
|---|---|
| Agent | LLM-driven worker with one bounded job and an allowed tool set |
| Tool Call | Structured request from an agent to platform code; model never executes directly |
| Supervisor | Orchestrates task plan, agent activation, policy, budget and final state |
| Application IR | Platform-owned source of truth describing product behavior/structure across frameworks |
| Change Impact Engine | Predicts allowed modules/APIs/schema/tests before edits |
| Sandbox | Isolated disposable execution environment for untrusted code |
| Browser Runtime | In-browser JS/WASM execution used only when capabilities fit |
| Runtime Provider | Adapter implementing our execution contract for browser, Linux, macOS, local or BYOC |
| Checkpoint | Persisted recoverable point in an agent run |
| Event Ledger | Ordered persisted history of task/agent/tool/build/test events |
| HITL | Human-in-the-loop approval/decision checkpoint |
| MCP | Standard protocol for exposing tools/resources/prompts to AI clients |
| Tool Registry | Governed inventory of first/third-party tools with permissions and schemas |
| BYOK | Customer provides LLM provider key |
| BYOC | Customer provides execution/cloud environment |
| BaaS | Managed backend platform used as optional generated-app backend profile |
| Structured Patch | Minimal symbol/AST/diff change instead of uncontrolled file rewrite |
| ADR | Architecture Decision Record with evidence, tradeoffs and escape plan |

---

## 61. V4 Non-Negotiable Architecture Rules

1. **Cloud untrusted code is always isolated.** Optional non-sandbox execution exists only for explicit trusted local mode.
2. **No sandbox vendor lock-in.** Agents depend on our Runtime/Sandbox Provider contract.
3. **No orchestration framework lock-in.** Core run state and task contracts belong to us.
4. **Every long-running task is resumable.** Checkpoints + event ledger are required.
5. **No duplicate side effects after retry/resume.** Idempotency is required for external actions.
6. **No unrestricted MCP.** All MCP access passes through Tool Registry, policy, consent, secret scope and audit.
7. **Human approval is risk-based.** Normal development stays fast; destructive/production actions stop for approval.
8. **Use browser execution only where it truly fits.** It is an optimization, not the universal runtime.
9. **Offer local/private execution without weakening cloud isolation.** Local and cloud are separate trust modes.
10. **BaaS is a customer backend option, not our platform core.** Keep our control plane on the approved platform stack.
11. **Every infrastructure choice needs measured evidence and an ADR.** References guide decisions; benchmarks decide them.
12. **Open-source code reuse is license-governed.** Architectural learning does not mean copying implementation.

---

## 62. V5 Working Brand, Naming and Repository Contract

**Working brand: OmniStackAI**  
**Tagline: From Intent to Production.**

Meaning: OmniStackAI combines product vision/intent with a software forge that turns requirements into governed, verifiable production artifacts. The name is a working architecture/product name only; trademark, company-name, domain, app-store and international legal clearance are mandatory before public launch.

Canonical repository naming:

```text
Platform:             omnistackai-platform
Local desktop agent:  omnistackai-local-agent        # split only when separate release/security lifecycle justifies it
SDK examples:         omnistackai-sdk-<language>
Customer project:     <org-slug>-<product-slug>
Temporary project:    vf-<project-ulid>-<slug>       # human slug remains visible
```

Product hierarchy remains:

```text
Organization -> Workspace -> Project -> Environment -> Target -> Deployment
```

Do not put customer projects inside the OmniStackAI platform repository.

## 63. Database Recommendation Architecture

### 63.1 OmniStackAI control plane

Default:

```text
PostgreSQL
  + pgvector       # semantic retrieval where useful
  + JSONB          # flexible event/tool metadata
  + optional PostGIS only if platform geospatial needs arise
Redis              # cache/locks/ephemeral state
NATS JetStream      # asynchronous events
Object Storage      # artifacts/logs/snapshots
```

Reasons for PostgreSQL as platform default:

- strong transactions and constraints for organizations, billing, permissions, tasks, deployments and approvals,
- relational integrity reduces AI-generated data-model mistakes,
- JSONB covers flexible metadata without requiring a second primary database,
- pgvector avoids a separate vector service during MVP,
- mature HA/backups/replication/tooling,
- easier consistent audit/query model across the control plane.

### 63.2 Generated customer database decision

The Database Recommender scores:

- relationship density,
- transaction/consistency requirements,
- schema flexibility,
- query/reporting complexity,
- realtime needs,
- geospatial needs,
- existing customer ecosystem,
- compliance/data-residency constraints,
- team skill,
- portability,
- cost/operational burden.

Default mapping:

| Workload | Recommended starting point | Notes |
|---|---|---|
| E-commerce / marketplace / booking / SaaS / finance | PostgreSQL | relations, transactions, constraints |
| Taxi/logistics/location-heavy | PostgreSQL + PostGIS | relational + spatial |
| Flexible content/document workload | PostgreSQL JSONB or MongoDB | benchmark real query/access patterns |
| Fast BaaS product | Supabase/Postgres or Firebase where fit | keep IR/contracts portable |
| Existing enterprise DB | Existing DB adapter | do not force migration without reason |

MongoDB remains a first-class optional adapter, not the OmniStackAI control-plane source of truth.

## 64. Preview, QR and Real-Device Product Contract

The Preview page must show explicit cards in this order:

```text
[1] Instant Browser Preview
    Fastest | included | default
    Open Preview

[2] Test on My Real Phone
    Real hardware | build/update only when required
    Android: QR / APK or Expo dev runtime
    iPhone: Expo dev runtime / TestFlight / approved dev build

[3] Cloud Android Device
    Emulator/device cloud | metered

[4] Cloud iOS Device
    Simulator/device cloud | metered Mac compute
```

Every card states:

- what is actually running,
- what capabilities are proven,
- known limitations,
- expected wait time,
- estimated credits/compute before starting.

Testing APKs/dev artifacts use encrypted object storage and short-lived signed URLs. QR codes encode a OmniStackAI download/launch URL rather than a permanent public artifact URL.

## 65. Smart Native Fingerprint and Rebuild Avoidance

For mobile projects compute a deterministic Native Fingerprint from:

- framework/SDK/toolchain versions,
- native dependencies/modules/plugins,
- Android Manifest / Gradle configuration,
- iOS entitlements/Info.plist/Xcode settings,
- permissions,
- signing profile class,
- native assets requiring compile-time packaging,
- build configuration/flavor.

If the fingerprint is unchanged, reuse compatible development runtimes and avoid unnecessary native rebuilds where the framework supports it. A change to pure JS/TS/IR/business code in an Expo-compatible project normally refreshes the dev runtime; a new native module invalidates the fingerprint and triggers a new development build.

## 66. Project Memory, Context Pack and Stale-Memory Validation

### 66.1 Memory record

Important reusable facts can be stored as evidence-backed records:

```yaml
memory:
  id: MEM-PAY-018
  fact: refunds_above_threshold_require_admin_approval
  value: true
  sources:
    - .ai/ir/payments/refund-policy.yaml
    - .ai/adr/ADR-041.md
    - services/api/payment/refund_policy.go
  first_seen_commit: <sha>
  last_verified_commit: <sha>
  confidence: 0.99
```

Before a high-impact task uses a memory, revalidate its evidence against the current branch. Invalid/stale memory is removed from active context and queued for refresh.

### 66.2 Context Quality Score

Before coding, calculate a Context Quality/Confidence score from evidence such as:

- requirement found,
- architecture/policy found,
- relevant symbols identified,
- reproduction/runtime evidence available,
- recent changes found,
- tests/acceptance available.

Low confidence causes investigation or a targeted user question rather than speculative editing.

## 67. Production Bug / Incident Repair Flow

Canonical large-project repair flow:

```text
User reports bug/crash
 -> identify production deployment + commit + IR + DB migration version
 -> collect crash/log/trace/device evidence
 -> Context Manager retrieves relevant IR/ADR/code symbols/Git history/tests
 -> create BUG task + expected blast radius
 -> task branch/worktree
 -> isolated reproduction
 -> minimal structured patch
 -> targeted tests
 -> regression + security + blast-radius checks
 -> Instant Browser Preview FIRST
 -> recommended real-device/cloud verification when necessary
 -> PR/review
 -> staging
 -> approved production deployment
 -> incident/task memory + regression test persisted
```

A browser preview cannot close a native-only bug. The verification policy must explicitly require the real runtime when the causal capability is native/hardware/OS-specific.

## 68. LLM and Compute Unit-Economics Policy

Optimization order:

1. deterministic tool before LLM,
2. retrieve before summarize,
3. small model before coding model,
4. coding model before strong reasoning model,
5. browser verification before native build,
6. physical device before paid cloud device when it proves the same requirement,
7. Linux before macOS when platform tooling permits,
8. cache dependencies/build outputs safely,
9. resume workflows instead of restarting,
10. stop after evidence satisfies acceptance criteria.

Per-task cost ledger:

```text
model_input_tokens
model_output_tokens
embedding/index_cost
linux_seconds
android_emulator_seconds
mac_seconds
device_cloud_seconds
object_storage_bytes
bandwidth_bytes
third_party_tool_cost
retry_waste
cache_savings
```

KPIs include **cost per successful task**, **cost per accepted change**, **browser-preview-to-real-build ratio**, **Mac minutes per successful iOS task**, **native rebuild avoidance rate** and **model escalation rate**.

## 69. Build/Artifact Provenance and Software Supply Chain

Every releasable artifact is tied to:

- source commit SHA,
- Application IR version/hash,
- template version,
- dependency lockfiles,
- builder image/toolchain version,
- test/security results,
- SBOM,
- signer identity/key version,
- artifact digest/checksum,
- deployment/store release ID.

Release artifacts are immutable. Prefer reproducible builds where practical. Sign OCI artifacts and maintain provenance/attestation compatible with modern supply-chain practices. Signing services can sign approved digests but cannot modify source.

## 70. Web, Android and iOS Publishing

### Web/backend

```text
approved commit -> BuildKit/reproducible build -> test/scan -> OCI image
 -> SBOM/sign -> registry -> preview/staging -> isolated new production version
 -> readiness/health -> guarded atomic traffic switch -> retain rollback pointer
```

### Android

```text
approved commit -> Linux/Gradle build -> tests/scans
 -> APK for test or AAB for store -> isolated signing
 -> Play Developer API -> internal/closed track -> approval -> production
```

### iOS

```text
approved commit -> macOS/Xcode -> tests/archive
 -> isolated signing/provisioning -> TestFlight/App Store Connect
 -> human/store review -> production
```

No normal coding agent has access to raw store signing keys.

## 71. Client Source Ownership and Handover

Support:

- customer GitHub/GitLab from day one through an installed app/integration,
- temporary OmniStackAI-managed repository with explicit transfer/export,
- enterprise GitHub Enterprise/GitLab/Bitbucket/Azure DevOps adapters later.

A **Prepare Client Handover** action generates/checks:

- complete source repository,
- Application IR + ADRs + requirement traceability,
- OpenAPI/AsyncAPI and DB schema/migrations,
- environment/deployment matrix,
- local developer setup,
- CI/CD and build commands,
- secrets/signing ownership checklist without secret values,
- test/quality/security reports,
- SBOM/licenses/provenance,
- release/build history,
- infrastructure diagram and runbooks,
- backup/restore/DR notes where applicable.

A customer must be able to continue development outside OmniStackAI without proprietary source-code lock-in.

## 72. Competitor Benchmark - Publicly Documented Position as of 2026-09

This table uses public product documentation/engineering posts, not reverse engineering. Competitor capabilities can change and must be revalidated before external marketing claims.

| Area | Emergent | Lovable | Bolt | Replit | OmniStackAI target |
|---|---|---|---|---|---|
| Natural-language full product build | Yes | Yes, web-focused | Yes | Yes | Yes |
| Generated native/cross-platform mobile | Expo/React Native | Public docs focus on web; mobile app is builder companion | Expo mobile | React Native/Expo | Expo/RN + Flutter + Kotlin + Swift |
| Flutter generation | Publicly documented as unsupported in Emergent Mobile Agent | Not core native target | Not core | Not core | First-class |
| Native Kotlin/Swift generation | Publicly documented as unsupported in Emergent Mobile Agent | Not core | Not core | Not core | First-class |
| Default/generated database | MongoDB common/default stack | PostgreSQL via Lovable Cloud/Supabase foundation | configurable JS ecosystem/Supabase | multiple platform services | PostgreSQL recommended + DB adapters |
| Full Linux runtime | K8s pods | managed cloud runtime | WebContainers/browser runtime focus | cloud workspace | tiered browser/Linux/microVM/macOS/local/BYOC |
| Long workflow durability | Temporal publicly documented | product-managed | product-managed | checkpoints/agent infra | Temporal + platform-owned state/event ledger |
| Mobile low-cost physical preview | Expo Go/EAS | N/A for native generation | Expo Go/EAS | Expo Go | Expo QR + APK QR + TestFlight/dev build |
| Project memory | large context/compression/forks + filtered subagents | project/workspace knowledge | Project Knowledge + context cleanup | checkpoints/context | IR + evidence-backed memory + code graph + runtime evidence |
| Customer code ownership | GitHub/exportable | Git sync/exportability | GitHub | Git | customer Git first-class + handover package |

### Public competitor/reference sources

- Emergent enterprise stack: https://emergent.sh/enterprise
- Emergent Kubernetes environments: https://emergent.sh/blog/real-environments-for-ai-agents-and-why-we-bet-on-kubernetes
- Emergent durable deployment/Temporal: https://emergent.sh/blog/why-we-rebuilt-our-deployment-engine
- Emergent E3 orchestration: https://emergent.sh/blog/introducing-e-3-autonomous-app-building-on-emergent
- Emergent context: https://help.emergent.sh/context-limits
- Lovable introduction/cloud/Supabase: https://docs.lovable.dev/introduction/welcome ; https://docs.lovable.dev/features/cloud ; https://docs.lovable.dev/integrations/supabase
- Bolt technologies/Expo/context: https://support.bolt.new/building/using-bolt/browser-support ; https://support.bolt.new/integrations/expo ; https://support.bolt.new/building/using-bolt/project-settings
- Replit Expo/checkpoints: https://docs.replit.com/learn/mobile/expo ; https://docs.replit.com/features/version-control/checkpoints-and-rollbacks
- Cursor context/rules/indexing: https://cursor.com/docs ; https://cursor.com/blog/dynamic-context-discovery ; https://www.cursor.com/security
- Windsurf memories/context awareness: https://docs.windsurf.com/windsurf/cascade/memories ; https://docs.windsurf.com/context-awareness/overview

## 73. Competitive Differentiation Rules

OmniStackAI must not compete by claiming "more AI". Its measurable differentiation is:

- broader target support behind one Application IR,
- instant-browser-first + cost-aware physical-device verification,
- real toolchain verification instead of preview-only confidence,
- evidence-backed long-term project memory independent of chat,
- Change Impact Engine and structured edits,
- Git-native customer ownership and atomic cross-target changes,
- runtime/model/database/provider abstractions that avoid vendor lock-in,
- enterprise security and local/private execution,
- cost per successful change as a product KPI,
- migration path from cross-platform to native without rediscovering product behavior.

## 74. Updated Platform Monorepo Contract

```text
omnistackai-platform/
  apps/
    console-web/                 # Next.js/TypeScript product UI

  services/
    control-plane/               # Go modular monolith initially
    agent-engine/                # Python orchestration/context/model adapters
    runner-manager/              # Go scheduler/runtime provider manager

  modules/                       # in-process/module boundaries; split only from measured need
    model-gateway/
    context-engine/
    code-intelligence/
    change-impact/
    git-service/
    preview-service/
    deployment-engine/
    release-publishing/
    billing-entitlements/
    audit-policy/
    integration-gateway/
    mcp-gateway/

  workers/
    browser-runner/
    linux-runner/
    web-runner/
    flutter-runner/
    react-native-runner/
    android-runner/
    mac-runner-controller/

  packages/
    contracts/
    policy-schemas/
    telemetry/
    ui/
    agent-sdk/
    runtime-sdk/
    provider-sdk/

  ai/
    prompts/
    agents/
    tools/
    policies/
    evals/
    benchmark-cases/
    context-templates/

  templates/
    flutter/
    react-native-expo/
    react-native-bare/
    android-compose/
    ios-swiftui/
    nextjs-web/
    nextjs-admin/
    backend-go/
    backend-python/
    backend-node/

  infra/
    terraform/
    kubernetes/
    temporal/
    environments/

  security/
    threat-models/
    policies/
    signing/
    supply-chain/

  docs/
    adr/
    runbooks/
    architecture/

  scripts/
  Taskfile.yml
  README.md
```

MVP keeps `control-plane`, `agent-engine`, and `runner-manager` as the principal deployable services. `modules/` are logical boundaries and must not automatically become microservices.

## 75. Platform Provider Interfaces

Define stable contracts for:

```text
ModelProvider
RuntimeProvider
BuildProvider
DeviceProvider
GitProvider
DatabaseProfileProvider
DeploymentProvider
ArtifactProvider
SigningProvider
SecretProvider
TelemetryProvider
MCPToolProvider
```

Platform agents depend on these contracts, not vendor SDKs. Provider-specific features can be exposed through capability discovery without contaminating the domain model.

## 76. V5 Phase Roadmap

### BASIC / MVP - Reliable software factory

Ship:

- OmniStackAI brand/internal repo normalization,
- product/org/workspace/project model,
- Application IR v4 + migration/versioning,
- Auto stack + database recommendation,
- Next.js web/admin, Go/Python backend,
- Flutter stable + Expo/RN stable/controlled beta according to team capacity,
- Native Kotlin/Swift selectable beta,
- one customer project = one monorepo,
- Git task branches/worktrees/PRs,
- Context Engine v1 + progressive retrieval + pgvector,
- Change Impact Engine v1,
- deterministic/AST structured edit tools,
- instant browser preview ALWAYS first,
- Expo QR real-device path, Android test APK QR path, iOS build verification path,
- Linux runtime provider + optional browser runtime,
- Temporal durable workflow + event ledger,
- model gateway + LLM escalation ladder + budget controller,
- compile/test/security/blast-radius gates,
- web/backend deployment + Android release builds + macOS iOS compile,
- PostgreSQL control plane, Redis, NATS, object storage,
- first-party Tool Registry/MCP foundation,
- baseline usage/cost observability.

### MID - Professional developer/agency product

Add:

- native Android/iOS GA,
- TestFlight/Play internal-track automation,
- streamed Android Emulator and iOS Simulator on demand,
- Remote Debug Bridge,
- Local Agent for Mac/Windows/Linux,
- existing repository import,
- richer code graph/call graph/indexing,
- evidence-backed project memory/revalidation,
- visual regression/accessibility/performance budgets,
- advanced build cache/warm pools/native fingerprint reuse,
- BYOK, verified external MCP install flow,
- customer Git onboarding and client handover generator,
- repo/build health and cost/unit-economics dashboards.

### ADVANCED - Enterprise flexibility and scale

Add:

- enterprise existing multi-repo orchestration,
- own hardened microVM runner fleet when economics prove it,
- provider failover/cross-region runtime scheduling,
- physical device cloud,
- private/BYOC runners and private model endpoints,
- policy-as-code and two-person critical approvals,
- data residency/multi-region,
- framework migration planner and cross-target consistency checker,
- advanced template marketplace/governance,
- predictive compute scheduler and capacity optimization,
- enterprise Git/identity/integration profiles.

### PRODUCTION READY - Evidence gates

Block GA/enterprise claims until measured evidence exists for:

- SLO/SLA/HA and multi-region failover where sold,
- backup/restore and disaster-recovery drills,
- task resume after worker failure and no duplicated side effects,
- tenant/sandbox/MCP isolation tests,
- independent penetration test,
- SOC 2-ready operational controls,
- signing-key and software-supply-chain hardening,
- privacy/retention/deletion controls,
- capacity/load tests and spending kill switches,
- app-store/web release qualification,
- billing reconciliation and positive unit-economics model.

## 77. V5 Non-Negotiable Architecture Rules

1. Instant Browser Preview is always visible before QR/device/cloud-device options.
2. Use the lowest-cost verification level that can prove the change; never claim a browser mock proves native behavior.
3. Project memory is separate from chat; raw chat is never the sole engineering memory.
4. Embeddings locate evidence; Git/IR/contracts/tests/runtime evidence establish truth.
5. Every long-running task is durable/resumable; Temporal is the preferred workflow foundation.
6. Deterministic tools precede LLM calls; expensive models are escalations, not defaults.
7. Context is progressively retrieved and budgeted; never send the whole project by default.
8. No unrelated edits; Change Impact defines and audits blast radius.
9. No uncontrolled full-file rewrites when structured/symbol patches are practical.
10. One customer project gets one default Git repository; customer source ownership is explicit.
11. OmniStackAI control plane uses PostgreSQL; generated projects use a requirement-based database recommender.
12. Cloud untrusted code is isolated; agents cannot reach control-plane private infrastructure.
13. Secrets/signing keys are brokered capabilities, never normal prompt context.
14. Agents depend on provider interfaces, not sandbox/model/build/database vendor SDKs.
15. App/store/deployment artifacts are immutable, traceable and signed according to release risk.
16. iOS Mac compute is allocated only when Apple tooling is actually required.
17. Cloud emulator/simulator sessions are optional/metered, not the normal preview path.
18. Cross-platform is preferred when requirements fit; native is selected by measured capability need, not industry label.
19. Major architecture/infrastructure decisions require benchmark evidence, ADR and exit strategy.
20. Competitor comparisons use current public sources and are never presented as knowledge of proprietary internals.

## 78. V5 Definition of Product Success

OmniStackAI is successful when a customer can:

```text
Describe an idea
 -> receive an explained stack/database recommendation
 -> approve a structured requirement/architecture plan
 -> watch AI build safely in isolated environments
 -> see an instant browser preview first
 -> optionally scan a QR/use TestFlight on a real phone
 -> validate with real toolchains when required
 -> own/review every change in Git
 -> deploy/publish through governed pipelines
 -> return months or years later and fix a production bug without replaying chat history
 -> hand the complete maintainable project to another engineering team
```

The north-star metric is not generated lines of code. It is **verified, accepted, production-ready change delivered at the lowest safe cost with full customer ownership**.

---

## 79. Local Model Runtime - Ollama and Open Coding Models (V6)

V5 mentioned "private/self-hosted endpoints" as an advanced profile. V6 makes local inference a **named, first-class ModelProvider available from MVP**, not an enterprise-only afterthought, because it is the cheapest way to run L0/L1 (and much of L2) work.

### 79.1 Why this matters

- Zero marginal token cost once hardware exists - the single biggest lever for "less cost for the operator."
- Keeps customer source code on-device for privacy-sensitive users (extends Mode B Hybrid Local from Section 55).
- Works offline / on a laptop, which is exactly what a solo founder needs during early development.

### 79.2 OllamaProvider contract

Implement `OllamaProvider` as one concrete implementation of the existing `ModelProvider` interface (Section 75/18.3). It must expose the same contract the Model Gateway already routes against:

```text
OllamaProvider implements ModelProvider
  baseUrl: http://localhost:11434 (or a configured LAN/host address)
  listModels()          -> calls Ollama /api/tags
  pullModel(name)        -> calls Ollama /api/pull, streamed progress to UI
  chat(model, messages)  -> calls Ollama /api/chat
  embeddings(model, text)-> calls Ollama /api/embeddings
  healthCheck()          -> ping before routing; auto-fallback if unreachable
  capabilities(model)    -> context window, tool-calling support, coding score (from local benchmark cache, not vendor marketing)
```

The Model Gateway treats a local Ollama endpoint exactly like any other provider entry - it goes through the same router, budget controller and circuit breaker as OpenAI/Anthropic/Gemini. No product code should special-case "local" vs "cloud"; capability discovery does that.

### 79.3 Recommended local model catalog (coding-oriented, update as new versions ship)

| Role | Model family | Typical size to run locally | Good for |
|---|---|---|---|
| Primary local coder | Qwen2.5-Coder / Qwen3-Coder | 7B-32B depending on VRAM | L1/L2 scoped edits, refactors, test writing |
| Alternative coder | DeepSeek-Coder-V2-Lite | 16B (MoE, runs lighter than size suggests) | L2 implementation tasks |
| General reasoning fallback | Llama 3.x / Mistral Small | 7B-14B | classification, summarization, log compaction (L1) |
| Embeddings | nomic-embed-text / mxbai-embed-large | small | pgvector context retrieval, fully local |

Rule: the platform must not hardcode one local model. It reads whatever the user has pulled into Ollama via `listModels()` and scores it against the capability table above; unknown models are treated as untrusted-capability until a benchmark run classifies them.

### 79.4 Routing rule with local models present

```text
L0 Deterministic engine        -> always, never a model call
L1 classify/summarize/rank     -> local model FIRST if healthy, else cheapest cloud model
L2 scoped coding task          -> local coder model FIRST if it passes the task's benchmark threshold,
                                   else escalate to cloud coding model
L3 architecture/security/hard  -> cloud strong-reasoning model (local models are not yet trusted for this tier)
L4 independent review          -> cloud reviewer model, always
```

A "Local-Only" routing mode (Section 80.4) can force everything below L3 to stay on-device; L3/L4 either wait for the user, are skipped, or explicitly require a one-time cloud escalation the user approves.

### 79.5 Failure handling

If `healthCheck()` fails (Ollama not running, model not pulled, out of memory), the gateway logs a routing-degradation event, notifies the user once per session (not per call), and falls back up the ladder to the next configured provider instead of blocking the task.

---

## 80. Multi-Provider API Key Management (BYOK Settings Module) (V6)

V5 named BYOK as a concept (Section 18.3, 55). V6 specifies the actual settings surface so it is buildable in the MVP phase, since the founder's own usage depends on switching between "free local" and "paid cloud" per task.

### 80.1 Settings screen: AI Providers

```text
Settings -> AI Providers

[+] Add Provider
  Provider type: OpenAI | Anthropic | Google Gemini | Groq | OpenRouter | Mistral | xAI | Custom (OpenAI-compatible URL) | Local (Ollama)
  API key: **************************** [Test Connection]
  Default model: <dropdown populated by capability probe>
  Priority: 1 (highest) - N
  Monthly spend cap: $____ (optional, hard stop when reached)
  Enabled: on/off
  Scope: this project only | all my projects
```

- Each saved key is written through `SecretProvider` (Section 75) - encrypted at rest, never placed in a prompt, never logged, never visible to any LLM as plain context. Agents receive a capability token, not the key.
- "Test Connection" performs one cheap call (list models / 1-token completion) and shows latency + confirmed model list, so a bad key is caught before it wastes a real task.
- A project can mix providers: e.g. local Ollama for L0/L1/L2, Anthropic key for L3, OpenAI key as L3 fallback.

### 80.2 Provider capability probe

On save, the platform calls the provider's model-list endpoint (or a static capability table for providers without one) and records: context window, max output tokens, function/tool-calling support, input/output price per million tokens, and a coding-benchmark score pulled from the platform's own eval suite (Section 26/`ai/evals`), never from vendor marketing claims alone.

### 80.3 Fallback and circuit breaking

If the top-priority provider errors, times out, or returns a rate-limit response, the router automatically retries on the next enabled provider for that tier, records the degradation, and surfaces it in Observability (Section 23). Users are never silently billed twice for the same failed step (Section 18.4).

### 80.4 Global routing preference

A single top-level toggle, visible on the project dashboard, controls default behavior for every task that doesn't have a more specific override:

```text
Routing Mode
(*) Cost-Optimized   - local-first, cheapest cloud model that meets the quality bar
( ) Balanced         - local for L0-L2, cloud reasoning for L3-L4 (default recommendation)
( ) Quality-First     - strongest available model at every tier regardless of cost
( ) Local-Only        - never call an external provider; L3/L4 tasks queue for manual approval or are skipped
```

This is the same routing engine from Section 18, just exposed as a single human-facing dial instead of forcing every user to configure the ladder manually.

---

## 81. Session Continuity and Resume Protocol (V6)

This closes the exact gap in the prompt: **"if any day I stop the work, how do I tell the AI tool where to start, what is completed already."** Chat history is explicitly *not* the mechanism (Section 66/68) - the mechanism is a small set of files every AI coding tool and every human developer is required to read before starting and required to update before stopping.

### 81.1 The three files that carry state (in the repo, never only in chat)

```text
PROJECT_STATE.md        <- single current snapshot, always overwritten (not appended)
CHANGELOG.md            <- append-only human-readable log, one line per completed task
OmniStackAI_Execution_Tracker.xlsx (or its DB-backed successor) <- phase/task Status column is
                                                                    the authoritative long-range plan
```

`PROJECT_STATE.md` is the one file an agent must read first. Its shape:

```markdown
# Project State - <project name>
Last updated: <ISO timestamp> by <human | agent name/model>

## Current Phase
BASIC/MVP - Milestone 2 of 5 (Context Engine + Change Impact Engine)

## Last Completed Task
Tracker ID: R-012 - Backend Agent (Go) - scoped CRUD generation - DONE, tests passing, merged in PR #14

## In Progress (if any)
Tracker ID: R-013 - Web/Admin Agent - editing packages/contracts and apps/console-web/src/api
Files touched so far: packages/contracts/src/project.ts, apps/console-web/src/api/projects.ts
Blocker: none / <describe exact blocker>

## Next Up (queued, in order)
1. R-014 - wire Change Impact Engine into PR gate
2. R-015 - pgvector context retrieval for console-web search
3. R-016 - Temporal workflow for build pipeline

## Decisions Made This Session
- Chose Qwen2.5-Coder-14B as default local model (7B was too weak on TypeScript generics)
- Deferred Kubernetes; running control-plane via docker-compose until MID phase

## Environment / Secrets Status
- Local Ollama: installed, models pulled: qwen2.5-coder:14b, nomic-embed-text
- Cloud keys configured: Anthropic (priority 1 for L3), none yet for OpenAI
- Postgres: running locally via docker-compose, migrations up to 0007
```

### 81.2 Non-negotiable rules

1. No AI coding agent (Claude Code, Cursor, Codex, or any other) may begin generating code in a session without first opening and reading `PROJECT_STATE.md` and checking the Execution Tracker Status column for the current phase.
2. No AI coding agent may end a session/turn that changed code without updating `PROJECT_STATE.md`'s "Last Completed" / "In Progress" / "Next Up" sections and appending one line to `CHANGELOG.md`.
3. `PROJECT_STATE.md` describes state, not chat history. It must reference Tracker IDs, file paths, and Git commit/PR references - never "as I said earlier" style pointers back into a conversation.
4. If `PROJECT_STATE.md` and the Tracker disagree (e.g. a task marked "Not Started" in the tracker but described as done in state), the agent must stop and ask the human to reconcile before proceeding, not guess.

### 81.3 The exact resume prompt for the human to use

Whatever AI tool is used (Claude Code, Cursor, Codex CLI, Windsurf), the same three-line prompt restarts work correctly:

```text
Read PROJECT_STATE.md, CHANGELOG.md, and the Execution_Tracker Status column.
Summarize where we left off in 3 bullet points, then continue with the next
queued task. Follow the Standard AI Task Contract (Section 26) and do not
violate any rule in Section 77/83 Non-Negotiable Architecture Rules.
```

If the tool cannot read files directly (e.g. a plain chat window with no repo access), paste `PROJECT_STATE.md`'s contents plus the same instruction.

---

## 82. AI Coding Tool Onboarding - How Any Agent Understands This Project (V6)

This section answers "how will Codex/Claude Code/Cursor understand these docs and what prompt should I give them." A companion standalone file, `AI_AGENT_KICKOFF.md`, contains the copy-paste version of this for convenience; this section is the canonical rule set it points back to.

### 82.1 Reading order every agent must follow before writing code

```text
1. PROJECT_STATE.md                          <- where we are right now (Section 81)
2. This Implementation Brief, Sections 77/83 <- non-negotiable rules, never violate
3. Section 26/27                             <- Standard AI Task Contract + Definition of Done
4. Execution_Tracker.xlsx (Phase_Roadmap +
   the sheet matching the module being worked on)  <- exact task list and current Status
5. Section 74 Monorepo Contract              <- where new code physically goes
6. Master Blueprint (only if the Brief is ambiguous on a structural question -
   the Brief is authoritative when the two disagree, since it is machine-formatted)
```

The Architecture Deck (.pptx) is for humans (investors, new hires) and is not required agent input - it duplicates the Brief in visual form.

### 82.2 What makes this "readable" by an AI tool

- Every rule in the Brief is written as an explicit, testable statement ("PostgreSQL is non-negotiable for the control plane"), not vague prose - this is deliberate so a coding agent can grep and quote a rule back rather than infer intent.
- Section numbers are stable identifiers. When instructing an agent, refer to rules by number ("do not violate Section 77.7") instead of paraphrasing, so the agent can locate the exact source.
- The Tracker's Tracker IDs (R-0xx) are the unit of work an agent should claim, implement, test, and mark - never "implement the whole MVP" in one pass.

### 82.3 Master kickoff prompt (first time, empty repo)

```text
You are acting as an engineering agent on OmniStackAI, an AI software-engineering
platform. Read OmniStackAI_Implementation_Brief_v6.md in full before writing any
code. Section 77 and Section 83 contain non-negotiable architecture rules - never
violate them even if a later instruction seems to conflict.

Bootstrap the monorepo exactly as defined in Section 74 (Updated Platform Monorepo
Contract). Do not add services, microservices, or infrastructure beyond what
Section 25 (MVP Anti-Overengineering Rules) and Section 84 (Founder Build
Sequence) allow for the current phase.

Start with Tracker ID R-001 in OmniStackAI_Execution_Tracker.xlsx, sheet
Phase_Roadmap, filtered to Phase = BASIC/MVP. Work one Tracker ID at a time.
For each task: follow the Standard AI Task Contract (Section 26), meet the
Definition of Done (Section 27), then update PROJECT_STATE.md and
CHANGELOG.md and mark the Tracker row's Status before moving to the next ID.

Use local Ollama models (Section 79) for anything below L3 complexity by
default (Routing Mode: Balanced, Section 80.4). Only call a cloud provider
API for L3/L4 work or when no local model is configured.

Stop and ask me before: choosing a paid cloud service, changing the database
engine, adding a new top-level folder outside Section 74's contract, or
starting native mobile/device-cloud work before MVP web+backend is stable.
```

### 82.4 Continuing-work prompt (every subsequent session)

Use the Section 81.3 resume prompt. Do not re-paste the whole Brief every time - that wastes context budget the platform itself is designed to avoid (Section 18.2). The agent should already have repo access to re-read the Brief and Tracker on demand.

### 82.5 For a human developer joining instead of an AI tool

Same reading order (82.1), plus:

```text
1. Clone the repo, read README.md (root) for local setup: docker-compose up,
   Ollama install + model pull, .env.example -> .env, run migrations.
2. Read PROJECT_STATE.md for exactly what is done and what is next.
3. Pick the next unclaimed Tracker ID in your area; do not start a task whose
   Status is not "Not Started" or "Ready" without checking with whoever
   marked it "In Progress."
4. Open a task branch per Section 34 naming convention, follow Section 26/27
   for every change, open a PR - the same gates apply to humans and agents.
```

---

## 83. V6 Additional Non-Negotiable Rules

These extend, and never override, Section 77.

21. Local inference (Ollama or equivalent) is a first-class ModelProvider from MVP, not an enterprise-only feature; the platform must run useful L0-L2 work with zero cloud API calls when the user chooses Local-Only or Cost-Optimized mode.
22. No API key is ever placed in a model prompt, log line, or client-visible payload; keys exist only inside the SecretProvider broker (extends Rule 13).
23. `PROJECT_STATE.md` must exist at the repo root from the first commit and must be updated at the end of every session that changed code or plans; a session that skips this update is not considered complete.
24. An AI coding agent must identify the Tracker ID it is working before writing code and must not silently expand scope beyond that ID's description (extends Change Impact / blast-radius rules in Section 12 and Rule 8).
25. Infrastructure additions (new services, queues, orchestrators, cloud regions) below the phase currently authorized in Section 84's build sequence require an explicit human approval, even if a rule elsewhere would technically allow them "eventually."

---

## 84. Founder Build Sequence - Lowest-Cost Path to a Working Platform (V6)

The full V5/V6 architecture is the end-state target, sized for an eventual team and paying customers. Built literally top-to-bottom on day one, it would be expensive and slow for a single founder. This section is the concrete, cost-minimizing order of construction that still respects every non-negotiable rule - it is a sequencing constraint, not a scope reduction.

### 84.1 Stage 0 - Local-only skeleton (cost target: ~$0/month beyond a laptop)

- `docker-compose` running: PostgreSQL (with pgvector), Redis, the control-plane service, the agent-engine service. No Kubernetes, no Temporal cluster yet (a single-process durable-workflow library or a simple job table with retry/idempotency keys satisfies Rule 5 at this scale - upgrade to Temporal in Stage 2).
- Ollama running locally with one coding model pulled (Section 79.3). This is the *only* model provider configured at first - prove the factory loop (Requirement -> IR -> Code -> Test -> Preview) works before paying for any cloud model call.
- Preview target: Web/PWA + Next.js only (Section 1's cheapest mobile choice). No Flutter/React Native/native runners yet.
- Git: local repo + one remote (GitHub free tier). No customer-facing Git automation yet.

### 84.2 Stage 1 - Add cloud escalation, keep everything else local

- Add one cloud provider (Anthropic or OpenAI) as the L3/L4 fallback only, with a small monthly spend cap (Section 80.1). This is the first real recurring cost, and it should be small because most work still resolves at L0-L2 on the local model.
- Add Change Impact Engine v1 and Context Engine v1 (Section 12/13) - these reduce future token spend more than any other single investment, so they come before scaling infrastructure.

### 84.3 Stage 2 - Real device preview, still cheap

- Add Expo/React Native QR preview (the device is the user's own phone - no device farm cost) before adding Flutter or Native, matching Section 1's cost ordering.
- Introduce Temporal (self-hosted, single node) once workflows regularly exceed a few minutes or need resume-after-crash guarantees (Rule 5), replacing the Stage 0 job table.

### 84.4 Stage 3 - Only after there is real usage or a paying pilot customer

- Native Kotlin/Swift generation, cloud emulator/simulator sessions, macOS cloud compute, Kubernetes/microVM runner fleets, multi-region, BYOC, and every "ADVANCED" item in Section 76's roadmap. Building these before there is a workload that needs them is the exact overengineering Section 25 already forbids - Section 84 simply makes the cost consequence explicit.

### 84.5 Rule

At every stage, prefer the configuration that satisfies the current milestone at the lowest infrastructure and API cost, and only add the next piece of infrastructure when a measured need (a real task failing, a real customer requirement, or a real performance ceiling) proves it is required - never speculatively. This is Section 25's Anti-Overengineering principle applied specifically to a one-person budget.

