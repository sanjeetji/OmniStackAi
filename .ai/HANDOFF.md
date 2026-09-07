# Current Handoff

Task ID: R-246
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `eebab68`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-246) — richer edit-loop diffs (hunk-level + rename detection)

- New `edit/patch.py`: `diff_report(old, new)` classifies each path as added/modified/deleted/renamed
  and attaches a git-style unified (hunk) diff for content changes; an exact-content delete+add
  collapses to one `RENAMED` record (old_path → path). `unified_patch(old, new)` concatenates them into
  one byte-stable git-style patch string (with rename headers).
- Standard-library `difflib` only; additive — `diff_projects` / `apply_diff` / `plan_edit` are
  unchanged. Pure/deterministic — no disk write, no run, no network.

## Verification

- `task verify` — pass (297 agent-engine tests; 6 new). Demo: a modified file yields a unified hunk
  (context + `-`/`+` lines); `old_name.txt`→`new_name.txt` (identical content) is one `RENAMED` record;
  add/delete render as one-sided `/dev/null` diffs. `task security:quick`, `task env:check` — pass.
- Tracker — R-246 (Builder) at `Phase_Roadmap!A9:M9`; MVP total 141, Done 35; chart/styles intact.

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
enforcement** (IR `required_roles` → 403), **sub-collection lists** (`GET /parents/{id}/children` →
FK-filtered list), a **combined project-plan surface** (`build_project_plan` / `task plan:show`), and
**hunk-level edit patches + rename detection** (`diff_report` / `unified_patch`). The builder is
generate (web/api with full CRUD + JWT auth + roles + DB schema + data access) → plan → verify → edit
(patch/rename-aware) → commit, fully offline. 35 tracker tasks Done; 0 cloud calls; the platform's own
PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Blockers and risks

- No blocker for the offline R-247 candidates. R-224 and live preview/deploy remain environment-gated;
  no cloud key or paid service is authorized.

## Next action

R-247 (pick with the founder — all offline-doable):

1. **IR fixtures + seed data**: add an optional fixtures field to the IR so seed rows can be emitted
   honestly (no fabricated values) as a `migrations/0002_seed.sql`.
2. **Render the R-245 plan / R-246 patch in the static console** (apps/console-web) so they're visible
   in the UI, not just the CLI.
3. **Deepen IR + adapter coverage**: entity indexes / unique constraints, richer field validation into
   the schema and models.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
