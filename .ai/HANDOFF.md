# Current Handoff

Task ID: R-241
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `4db716b`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-241) — authentication guards from the IR

- New `codegen/auth_guard.py`: `needs_auth`, `python_auth_file`, `go_auth_file`. Every `auth=true`
  endpoint enforces a guard that rejects a request with no `Authorization: Bearer` credential (`401`).
- Python (`backend_python.py`): emits `app/auth.py` (`require_auth` dependency); `auth=true` routes
  declare `dependencies=[Depends(require_auth)]`, public routes unchanged. Go (`backend_go.py`): emits
  `internal/handlers/auth.go` (`RequireAuth(next)` middleware); `main.go` wraps exactly the `auth=true`
  registrations with `handlers.RequireAuth(...)`. Both DB and non-DB backends.
- IR roles surfaced as a generated constant (Python `ROLES`, Go `Roles`, from `role.id`). The guard only
  requires a credential; token verification (signature/expiry/roles) is a documented TODO — no secret
  fabricated. Emitted only when the IR has an `auth=true` endpoint; deterministic; nothing runs.

## Verification

- `task verify` — pass (265 agent-engine tests; 9 new in `test_auth_guard.py`). `minimal-blog`:
  `POST /posts` guarded via `Depends(require_auth)`, `GET /posts` public; `app/auth.py` parses as valid
  Python with `ROLES = ("author", "reader")`. `rideshare-favourites`: `main.go` wraps the 3 auth
  endpoints with `handlers.RequireAuth(...)`, `GET /drivers` direct. `task security:quick`, `task
  env:check` — pass. No handler executed, no network.
- Tracker — R-241 (Builder) at `Phase_Roadmap!A9:M9`; MVP total 136, Done 30; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric (an **11-provider cloud catalog** —
OpenAI/Anthropic/Google/OpenRouter/Groq/DeepSeek/xAI/Mistral/Together/Fireworks + bring-your-own custom
endpoints, all key-activated, local Ollama always-on), the **Tier 0-3 runtime/deploy layer** (single
tier switch + a driver for every provider), the **verifiable-engineering layer** (per-target gate
ladders and one-IR→monorepo verify plans), the **edit loop** (plan_edit → diff → apply → commit), a
**generated PostgreSQL schema** (migrations/0001_init.sql from IR entities + relations), a
**data-access layer** (Python repositories + Go store) over that schema, **wired handlers** (the
unambiguous CRUD endpoints call the repositories), and now **authentication guards** (each `auth=true`
endpoint enforces a bearer credential). The builder is generate (web/api with working CRUD + auth
guards + DB schema + data access) → verify → edit → commit, fully offline. 30 tracker tasks Done;
0 cloud calls; the platform's own PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-242, pick with the founder — all offline-doable)

1. **Real token verification + per-endpoint roles**: build on the R-241 guard — verify a JWT
   (signature/expiry) and enforce roles per endpoint (the IR `roles` are already surfaced as a constant).
2. **Seed data + ambiguous routes**: generate seed/fixture rows and handle the endpoints still left as
   `501` (sub-collections like `/posts/{postId}/comments`, custom/multi-param routes).
3. **Combined build/verify/preview plan surface**: a single per-target plan set the console/CLI can
   render, tying R-233/234/235 together.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
