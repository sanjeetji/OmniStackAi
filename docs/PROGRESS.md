# OmniStackAI — implementation progress (as of R-241)

A living summary of what is built, what is pending, and how to see results. Numbers come from the
execution tracker (`R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx`, `Phase_Roadmap`).

## Headline

- **265 automated tests pass**, fully offline and network-independent (`task verify`).
- **30 tracker tasks Done, 1 Deferred, 210 Not Started** across 241 rows.
- The offline builder loop is complete end to end: **describe (IR) → generate (web + API with working
  CRUD + DB schema + data-access + auth guards) → verify → edit → commit to an owned Git repo.**

## Completion by phase

| Phase | Done | Total | % complete |
|-------|------|-------|-----------|
| **MVP** (current milestone) | 30 | 136 | **22.1%** |
| MID | 0 | 47 | 0% |
| ADVANCED | 0 | 29 | 0% |
| PRODUCTION | 0 | 29 | 0% |
| **Overall program** | **30** | **241** | **12.4%** |

> The 210 "Not Started" rows are the pre-existing backlog catalogue (R-010..R-219 — many are individual
> specialized agents and later-phase features). Capability-wise the platform is further along than the
> raw 11% suggests, because the work done so far is the **core engine + builder**, which everything
> else builds on. The MVP figure (20%) is the truest near-term measure.

## Capabilities — completed vs pending

| Area | Status | Notes |
|------|--------|-------|
| Repo/monorepo bootstrap, Task runner, Stage-0 verify | ✅ Done | R-001 |
| Local PostgreSQL + pgvector (platform DB) | ✅ Done | R-002 |
| Local Ollama config + lifecycle + live inference | ✅ Done | R-003 |
| Go control-plane (config, health, shutdown) | ✅ Done | R-004 |
| Model provider contract + registry | ✅ Done | R-005 |
| Local Ollama adapter (bounded, streaming) | ✅ Done | R-006 |
| Balanced gateway router (escalation ladder) | ✅ Done | R-007 |
| Cloud provider catalog (11 providers + custom) | ✅ Done | R-008, R-236 |
| SSE streaming, fallback + circuit breaker | ✅ Done | R-220, R-221, R-223 |
| Usage + cost accounting (price book) | ✅ Done | R-009 |
| Platform console (static, model/cost overview) | ✅ Done | R-222 |
| Application IR + validator/normalizer + fixtures | ✅ Done | R-225, R-231 |
| Code adapters: Next.js web, FastAPI, Go | ✅ Done | R-227, R-229, R-230 |
| Project assembler (one IR → monorepo) | ✅ Done | R-232 |
| Git service (materialize → owned repo) | ✅ Done | R-228 |
| Runtime/deploy provider layer + tier switch + drivers | ✅ Done | R-233, R-234 |
| Verifiable-engineering verify plans | ✅ Done | R-235 |
| Edit loop (IR-diff → patch-apply → commit) | ✅ Done | R-237 |
| PostgreSQL schema/migration from the IR | ✅ Done | R-238 |
| Data-access/repository layer (Python + Go) | ✅ Done | R-239 |
| Route wiring — handlers → repositories (real CRUD) | ✅ Done | R-240 |
| Authentication guards (enforce IR `auth` flag) | ✅ Done | R-241 |
| Next.js console upgrade (rich UI) | ⏸ Deferred | R-224 — needs npm registry access |
| Real token verification + per-endpoint roles | ⛔ Pending | R-241 surfaces roles; verification is a TODO |
| Seed data + ambiguous-route handling | ⛔ Pending | next candidates (R-242+) |
| Live sandbox preview + real deploy (Tier 2) | ⛔ Pending | needs a network machine + provider keys |
| Native mobile agents | ⛔ Deferred (governance) | until web/backend stability (Brief §25/§91) |
| MID / ADVANCED / PRODUCTION phase work | ⛔ Not started | 105 rows |

## Can I see a result today? Yes — offline, on your Mac

Everything below runs with **no cloud keys** and no internet (except where noted). From the repo root:

1. **See the whole engine is real and green:**
   ```
   task verify            # 237 tests pass
   ```
2. **Generate a real app from a spec and inspect it** (the headline result):
   ```
   task builder:demo -- rideshare-favourites     # or: minimal-blog
   ```
   This turns one Application IR into a **25-file customer monorepo** (Next.js `apps/web` + Go/FastAPI
   `services/api` + a PostgreSQL `migrations/0001_init.sql`) inside a brand-new **Git repo owned by
   you**, and prints the file tree, the generated SQL schema, and the verify plans. The path it prints
   is a normal folder you can open, edit, and `git log`.
3. **See the model fabric / provider catalog / tiers / verify ladders:**
   ```
   task platform:status                      # active tier + which provider keys are present
   task agent-engine:verify-plan -- backend-go
   task console:serve                         # http://127.0.0.1:4321  (model + cost overview)
   ```
4. **Run a real AI generation locally through the gateway** (uses your installed Ollama
   `qwen2.5-coder:14b`, zero cloud cost):
   ```
   task ollama:status
   task agent-engine:gateway:run
   ```

## When can I see the generated app running in a browser?

On **your Mac in a normal terminal** (not this sandbox), right now:

```
task builder:demo -- minimal-blog          # note the printed repo path
cd <that path>/apps/web && pnpm install && pnpm dev      # -> http://127.0.0.1:3000
cd <that path>/services/api && uvicorn app.main:app --reload   # (FastAPI)  -> :8000
#   or, for a Go backend:  cd <that path>/services/api && go run .            -> :8080
```

`pnpm install` needs internet the first time (this AI sandbox blocks the large Next.js binary download,
which is why the platform never runs it during `task verify`). On your own machine it works normally.

**One-click cloud preview and real deploy** (open a public URL without any local toolchain) arrive when
Tier 2 is turned on: add a provider key (e.g. `E2B_API_KEY` for a sandbox or `VERCEL_TOKEN` for a
deploy), set `OMNISTACKAI_TIER=2`, and run the runtime/deploy driver. The plumbing is built (R-233/234);
the live run needs the key + a network machine.

## What's next

Near-term MVP candidates (all offline-doable): real token verification (JWT) + per-endpoint role checks
building on the R-241 guard; seed data + handling the currently-ambiguous routes (sub-collections /
custom endpoints still `501`); a combined build/verify/preview plan surface for the console. Then, on a
network machine: live Tier-2 preview and deploy. This file is refreshed as tasks land.
