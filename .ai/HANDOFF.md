# Current Handoff

Task ID: R-244
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `b886d72`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-244) — sub-collection route wiring

- `route_wiring.py` gains `Op.LIST_BY` + `fk_relations(ir)`: `GET /<parents>/{parentId}/<children>`
  wires to a parent-scoped list **only** when the child entity (response_schema) has exactly one FK
  relation (many_to_one/one_to_one); otherwise it stays a labelled `501`.
- The data-access layer emits a filtered list per FK relation — Python `list_<table>_by_<rel>(<rel>_id)`
  (`WHERE <rel>_id = %s`), Go `List<Entity>By<Rel>(ctx, db, <rel>ID, limit)` (`WHERE <rel>_id = $1`);
  the value is parameterized, the column a fixed IR-derived identifier. Python routers and Go handlers
  call it (`await comment.list_comment_by_post(postId)` / `store.ListCommentByPost(...)`).
- Genuinely-ambiguous endpoints (0/>1 FK relations, multi-param, unknown entity) stay `501`. Nothing
  runs. Seed/fixture data deferred (no IR fixture values).

## Verification

- `task verify` — pass (285 agent-engine tests; 11 new). `minimal-blog` `GET /posts/{postId}/comments`
  is wired in both backends; `rideshare-favourites` `POST /favourites/drivers/{driverId}` stays `501`.
  `task security:quick`, `task env:check` — pass. No DB connection, no handler executed, no network.
- Tracker — R-244 (Builder) at `Phase_Roadmap!A9:M9`; MVP total 139, Done 33; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric (an **11-provider cloud catalog** —
OpenAI/Anthropic/Google/OpenRouter/Groq/DeepSeek/xAI/Mistral/Together/Fireworks + bring-your-own custom
endpoints, all key-activated, local Ollama always-on), the **Tier 0-3 runtime/deploy layer** (single
tier switch + a driver for every provider), the **verifiable-engineering layer** (per-target gate
ladders and one-IR→monorepo verify plans), the **edit loop** (plan_edit → diff → apply → commit), a
**generated PostgreSQL schema** (migrations/0001_init.sql from IR entities + relations), a
**data-access layer** (Python repositories + Go store) over that schema, **wired handlers** (the
unambiguous CRUD endpoints call the repositories), **JWT-verified authentication guards** (each
`auth=true` endpoint verifies an HS256 token with the secret from the env), **per-endpoint role
enforcement** (IR `required_roles` → 403), and now **sub-collection lists** (`GET /parents/{id}/children`
→ FK-filtered list). The builder is generate (web/api with full CRUD incl. sub-collections + JWT auth +
roles + DB schema + data access) → verify → edit → commit, fully offline. 33 tracker tasks Done;
0 cloud calls; the platform's own PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-245, pick with the founder — all offline-doable)

1. **Combined build/verify/preview plan surface**: a single per-target plan set (preview + verify +
   deploy) the console/CLI can render, tying R-233/234/235 together.
2. **Richer edit-loop diff**: rename detection or hunk-level diffs on the R-237 `ProjectDiff`.
3. **IR fixtures + seed data**: add an optional fixtures field to the IR so seed rows can be emitted
   honestly (no fabricated values).
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
