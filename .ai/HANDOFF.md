# Current Handoff

Task ID: R-242
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `e0d8af3`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-242) — real JWT verification in the auth guard

- `codegen/auth_guard.py` now generates a guard that **verifies a JWT (HS256)** using `JWT_SECRET` from
  the environment — `401` on a missing/invalid/expired token, `500` when the secret is unset, never a
  fabricated default.
- Python (`app/auth.py`): `require_auth` imports PyJWT, `jwt.decode(.., algorithms=["HS256"])`, returns
  the verified claims; `requirements.txt` gains `PyJWT`, `.env.example` gains an empty `JWT_SECRET`. Go
  (`internal/handlers/auth.go`): `RequireAuth` uses `github.com/golang-jwt/jwt/v5`, `jwt.Parse` with an
  HMAC-only keyfunc; `go.mod` gains the golang-jwt `require`, `.env.example` gains `JWT_SECRET`.
- Route placement is unchanged from R-241 (auth routes guarded, public untouched). Platform code stays
  standard-library only — the JWT dependency lives in the generated project. The IR roles constant is
  retained for future per-endpoint authorization (needs an IR field).

## Verification

- `task verify` — pass (268 agent-engine tests; 3 new). `minimal-blog` `app/auth.py` parses as valid
  Python and reads `JWT_SECRET` from `os.environ` only; `rideshare-favourites` `auth.go` uses golang-jwt
  with an HMAC keyfunc; deps + `JWT_SECRET` placeholder added. `task security:quick`, `task env:check` —
  pass. No token signed/verified at generation time, no network.
- Tracker — R-242 (Builder) at `Phase_Roadmap!A9:M9`; MVP total 137, Done 31; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric (an **11-provider cloud catalog** —
OpenAI/Anthropic/Google/OpenRouter/Groq/DeepSeek/xAI/Mistral/Together/Fireworks + bring-your-own custom
endpoints, all key-activated, local Ollama always-on), the **Tier 0-3 runtime/deploy layer** (single
tier switch + a driver for every provider), the **verifiable-engineering layer** (per-target gate
ladders and one-IR→monorepo verify plans), the **edit loop** (plan_edit → diff → apply → commit), a
**generated PostgreSQL schema** (migrations/0001_init.sql from IR entities + relations), a
**data-access layer** (Python repositories + Go store) over that schema, **wired handlers** (the
unambiguous CRUD endpoints call the repositories), and now **JWT-verified authentication guards** (each
`auth=true` endpoint verifies an HS256 token with the secret from the env). The builder is generate
(web/api with working CRUD + JWT auth + DB schema + data access) → verify → edit → commit, fully
offline. 31 tracker tasks Done; 0 cloud calls; the platform's own PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-243, pick with the founder — all offline-doable)

1. **Per-endpoint role enforcement**: extend the IR `ApiEndpoint` with optional `required_roles` and
   check them against the R-242-verified token claims (the roles constant is already generated).
2. **Seed data + ambiguous routes**: generate seed/fixture rows and handle the endpoints still left as
   `501` (sub-collections like `/posts/{postId}/comments`, custom/multi-param routes).
3. **Combined build/verify/preview plan surface**: a single per-target plan set the console/CLI can
   render, tying R-233/234/235 together.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
