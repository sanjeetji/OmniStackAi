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

## Scope boundary / what's next

R-430 is the **proposal** engine only. It is **not yet wired into IR/repo generation**. The next brick maps
each proposed `AppSurface` → an Application IR, so choosing "Complete Business Platform" materializes
**multiple owned repos/apps** from one prompt (building on the existing project assembler + git-service that
already turn one IR into an owned repo). An opt-in cheap-LLM refinement over the deterministic classifier (for
prompts outside the curated domains) is a later, opt-in layer that must not enter `task verify`.
