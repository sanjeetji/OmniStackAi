# Current Handoff

Task ID: R-243
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `1faea2c`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-243) — per-endpoint role enforcement

- **IR change (additive):** `ApiEndpoint` gains optional `required_roles` (role ids) — a non-empty value
  implies `auth`, each must be a declared `Role` (`validate_ir` errors otherwise), round-trips through
  `to_dict`/`from_dict`. Default `()`, schema version unchanged; `normalize_ir` unchanged.
- **Guard:** returns **403** when the R-242-verified token's `roles` claim includes no required role.
  Python (`app/auth.py`): `require_roles(*required)` dependency factory; role-gated routes declare
  `dependencies=[Depends(require_roles("..."))]`. Go (`internal/handlers/auth.go`): refactored to a
  shared `verifyToken` + `RequireAuth` + `RequireRoles(next, required...)` + `hasAnyRole`; `main.go`
  wraps role-gated endpoints with `handlers.RequireRoles(target, "...")`.
- Endpoints without `required_roles` keep the R-241/R-242 auth guard. Deterministic; nothing runs.

## Verification

- `task verify` — pass (274 agent-engine tests; 6 new). Demo (blog IR, `POST /posts` requires
  `author`): Python route uses `Depends(require_roles("author"))` and `app/auth.py` has a 403 path; Go
  `main.go` uses `handlers.RequireRoles(h.PostPosts, "author")`. `validate_ir` errors on an unknown
  role; a public endpoint with roles raises `InvalidIRError`. `task security:quick`, `task env:check` —
  pass. No handler executed, no network.
- Tracker — R-243 (Builder) at `Phase_Roadmap!A9:M9`; MVP total 138, Done 32; chart/styles intact.

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
`auth=true` endpoint verifies an HS256 token with the secret from the env), and now **per-endpoint role
enforcement** (IR `required_roles` → 403). The builder is generate (web/api with working CRUD + JWT
auth + roles + DB schema + data access) → verify → edit → commit, fully offline. 32 tracker tasks Done;
0 cloud calls; the platform's own PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-244, pick with the founder — all offline-doable)

1. **Seed data + ambiguous routes**: generate seed/fixture rows and handle the endpoints still left as
   `501` (sub-collections like `/posts/{postId}/comments`, custom/multi-param routes).
2. **Combined build/verify/preview plan surface**: a single per-target plan set the console/CLI can
   render, tying R-233/234/235 together.
3. **Richer edit-loop diff**: rename detection or hunk-level diffs on the R-237 `ProjectDiff`.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
