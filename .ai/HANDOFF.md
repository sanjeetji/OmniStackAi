# Current Handoff

Task ID: R-239
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `f6792fa`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-239) — data-access/repository layer for the backends

- New `codegen/data_access.py`. Python (FastAPI): `app/db.py` (async psycopg connection helper reading
  `DATABASE_URL`, dict rows) + `app/repositories/<entity>.py` per entity (`list/get/create/delete`);
  `requirements.txt` gains `psycopg`. Go: `internal/store/store.go` (a `database/sql` opener via pgx) +
  `internal/store/<entity>.go` per entity (`List/Get/Create/Delete` scanning the generated
  `models.<Entity>` structs); `go.mod` gains the pgx `require`.
- All query values are parameterized (`%s` / `$N`); only fixed IR-derived identifiers appear inline; an
  id-only entity creates via `DEFAULT VALUES`. Emitted with the migration when entities+postgres; no
  previously emitted file (other than requirements.txt / go.mod) changed. The R-237 edit loop diffs the
  repositories when the IR changes.

## Verification

- `task verify` — pass (244 agent-engine tests; 7 new). Generated `app/db.py`+repositories parse as
  valid Python; the Go store scans into `models.<Entity>` with the module import path. `task
  security:quick`, `task env:check` — pass. No DB connection, no query executed, no network.
- Tracker — R-239 (Builder) at `Phase_Roadmap!A9:M9`; MVP total 134, Done 28; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric (an **11-provider cloud catalog** —
OpenAI/Anthropic/Google/OpenRouter/Groq/DeepSeek/xAI/Mistral/Together/Fireworks + bring-your-own custom
endpoints, all key-activated, local Ollama always-on), the **Tier 0-3 runtime/deploy layer** (single
tier switch + a driver for every provider), the **verifiable-engineering layer** (per-target gate
ladders and one-IR→monorepo verify plans), the **edit loop** (plan_edit → diff → apply → commit), a
**generated PostgreSQL schema** (migrations/0001_init.sql from IR entities + relations), and a
**data-access layer** (Python repositories + Go store) over that schema. The builder is generate
(web/api + DB schema + data access) → verify → edit → commit, fully offline. 28 tracker tasks Done;
0 cloud calls; the platform's own PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-240, pick with the founder — all offline-doable)

1. **Wire route handlers to the repositories**: turn the 501 stubs into real CRUD that calls the R-239
   data-access layer (+ optional seed data), so the generated endpoints actually run.
2. **Auth/roles through the adapters**: the IR already models `roles`; flow them into route guards and
   a users/roles schema.
3. **Combined build/verify/preview plan surface**: a single per-target plan set the console/CLI can
   render, tying R-233/234/235 together.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
