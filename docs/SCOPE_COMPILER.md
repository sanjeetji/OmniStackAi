# Ecosystem Scope Compiler (R-430)

The **first brick of OmniStackAI's differentiating spine** (Master Architecture Spec §2, "Product
Intelligence & Ecosystem Scope Compiler"). Competitor tools turn *"create a food delivery app"* into a single
customer screen; OmniStackAI proposes the **whole business ecosystem** — customer app + merchant portal +
driver portal + admin dashboard — **before** any expensive generation, asking at most 1–3 high-materiality
questions.

## What it does

`propose_ecosystem(prompt)` turns a plain-English business prompt into a framework-neutral **`ScopeProposal`**:

- `domain`, `domain_confidence`, `matched_keywords` — the detected business domain.
- `business_model` — a one-line description of how the domain makes money.
- `actors` — the human roles (Customer, Merchant, Driver, Admin, …).
- `surfaces` — the app surfaces in the ecosystem, each an `AppSurface` with `audience`
  (`"customer"` = the end consumer, `"operator"` = merchant/driver/staff/admin).
- `options` — the build-scope choices: **Complete Business Platform** (recommended, all surfaces),
  **Customer Experience Only** (just the customer-audience surfaces), and **Custom** (toggle any surface).
- `questions` — at most 3 clarifying questions that materially change the build.

## Design — deterministic core, offline, testable

Classification is a **deterministic curated keyword heuristic**, not a model call — so it is pure (the same
prompt yields a byte-identical proposal) and runs under `task verify` with **0 model calls, no network**.
This mirrors the intake agent's split (`nl_to_ir.py` deterministic core vs `live_run.py` opt-in model layer).

- `DOMAIN_LIBRARY` — a curated list of `DomainSpec`s (food-delivery, rideshare, marketplace, e-commerce,
  b2b-saas, healthcare-clinic, booking, learning, social, blog-cms). Each carries weighted keywords, the
  full-platform `AppSurface`s, ≤3 materiality questions, and a self-classifying example prompt.
- `classify_domain(prompt)` — case-insensitive weighted keyword scoring (a multi-word phrase scores higher
  than a single token); the highest-scoring domain at/above the threshold wins, ties broken by library order.
  Returns `None` when nothing matches → `propose_ecosystem` falls back to a single-app `custom-application`.

All value objects (`Actor`, `AppSurface`, `ScopeOption`, `ScopeProposal`, `DomainMatch`, `DomainSpec`) are
frozen dataclasses with a JSON-safe `to_dict()`, exported from `omnistackai_agent_engine.intake`.

## See it

```bash
task agent-engine:scope:propose -- "Create a food delivery app where customers order from restaurants and couriers deliver"
```

```
Domain: food-delivery  (confidence 1.0)
Proposed ecosystem (app surfaces):
  - [customer] Customer Ordering App (Customer)
  - [operator] Merchant Portal (Merchant)
  - [operator] Courier Dispatch App (Driver)
  - [operator] Super-Admin Dashboard (Admin)
Build-scope options:
  - Complete Business Platform (recommended): Customer Ordering App, Merchant Portal, Courier Dispatch App, Super-Admin Dashboard
  - Customer Experience Only: Customer Ordering App
  - Custom / Multi-Surface Configuration: …
```

## From proposal to real apps (R-431)

R-430 is the **proposal** engine; **R-431 (`intake/ecosystem.py`) makes it real** — it maps each proposed
`AppSurface` to a `validate_ir`-clean `ApplicationIR` (a curated per-domain data model + a deterministic CRUD
deriver whose endpoints wire to real repositories) and materializes the chosen build scope as **multiple
owned Git repos** from one prompt (reusing the assembler + git-service):

```bash
task agent-engine:ecosystem:plan  -- "Create a food delivery app with restaurants and couriers"   # shows the per-app IRs (deterministic, writes nothing)
task agent-engine:ecosystem:build -- "Create a food delivery app with restaurants and couriers"   # writes one owned repo per surface (opt-in)
```

A food-delivery prompt builds 4 apps (Customer Ordering App, Merchant Portal, Courier Dispatch App,
Super-Admin Dashboard); all four pass `tsc --noEmit` clean. See `docs/PROGRESS.md` and `.ai/tasks/R-431.md`.

## What's next

## Unknown-domain refinement (R-432)

The deterministic compiler remains the first pass. Known domains use their curated proposal and data model
with zero model calls. When it returns `custom-application`, an explicit local-only command can request a
tailored proposal and entity model through the platform `ModelProvider` boundary:

```bash
task agent-engine:ecosystem:refine -- "Build apiary operations software for beekeepers"
```

The response is untrusted and fail-closed: exact bounded JSON only, 1-8 actors/surfaces/entities, at most
three questions, IR-valid identifiers/types/relations, required UUID ids, no credential fields, no duplicate
relation-derived FK columns, and only supported validation rules. Parsed entities then flow through the
same deterministic CRUD/IR planner. The CLI imports only the loopback Ollama adapter, never falls back to
cloud, and is excluded from `task verify`; tests inject an in-memory provider.

## What's next

Surface-specific entity focus and role/permission scoping is the next brick, followed by Solution Packs
(pre-tested skeletons + AI-delta generation) and optionally a frontier model for generation quality.
