# Current Handoff

Task ID: R-238
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `c6a4c6e`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-238) — PostgreSQL schema/migration from the IR

- New `codegen/schema_sql.py`: `render_postgres_schema(ir)` renders deterministic SQL DDL from the IR
  entities + relations — one `CREATE TABLE` per entity (snake_case), FieldType→PG column types,
  `NOT NULL` for required fields, a UUID primary key (the entity's `id` field or a surrogate),
  `<name>_id UUID REFERENCES <target>(id)` for many_to_one/one_to_one relations, and one deterministic
  join table per many_to_many.
- Both backend adapters (FastAPI + Go) emit `migrations/0001_init.sql` exactly when the IR has entities
  and `database_strategy=postgres`; no previously emitted file changed. Output is byte-stable, so the
  R-237 edit loop diffs the migration when the IR changes.

## Verification

- `task verify` — pass (237 agent-engine tests; 11 new). Demo: rideshare-favourites → `driver` +
  `favourite_driver` with a `driver_id` FK; python/go backends emit the migration. `task
  security:quick`, `task env:check` — pass. No DB connection, no migration run, no network.
- Tracker — R-238 (Builder) at `Phase_Roadmap!A9:M9`; MVP total 133, Done 27; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric (an **11-provider cloud catalog** —
OpenAI/Anthropic/Google/OpenRouter/Groq/DeepSeek/xAI/Mistral/Together/Fireworks + bring-your-own custom
endpoints, all key-activated, local Ollama always-on), the **Tier 0-3 runtime/deploy layer** (single
tier switch + a driver for every provider), the **verifiable-engineering layer** (per-target gate
ladders and one-IR→monorepo verify plans), the **edit loop** (plan_edit → diff → apply → commit), and
a **generated PostgreSQL schema** (migrations/0001_init.sql from IR entities + relations). The builder
is generate (web/api + DB schema) → verify → edit → commit, fully offline. 27 tracker tasks Done;
0 cloud calls; the platform's own PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-239, pick with the founder — all offline-doable)

1. **Wire models to the schema**: a repository/ORM layer + seed data so the generated backend actually
   reads/writes the tables from R-238 (deepens the persistence slice end to end).
2. **Auth/roles through the adapters**: the IR already models `roles`; flow them into route guards and
   a users/roles schema.
3. **Combined build/verify/preview plan surface**: a single per-target plan set the console/CLI can
   render, tying R-233/234/235 together.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
