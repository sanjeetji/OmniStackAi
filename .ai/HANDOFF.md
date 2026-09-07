# Current Handoff

Task ID: R-236
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `e6326bf`

## Repo/workflow state

- All work is on `main`; there are NO other branches. Commit new work directly to `main` with the
  Tracker-ID discipline (contract → tests → gates → tracker → commit tagged `[R-###]` → push).
- Every commit is authored solely by `sanjeetji <sk698166@gmail.com>`. Commit messages also carry a
  tooling-required `Co-Authored-By: Claude Opus 4.8` trailer; the owner may strip it from history.

## Completed (R-236) — expanded model-provider catalog + custom providers

- Added first-class OpenAI-compatible providers `deepseek`, `xai` (Grok), `mistral`, `together`,
  `fireworks` alongside `openai`/`anthropic`/`google`/`openrouter`/`groq` — all reuse
  `OpenAICompatibleProvider`, no new adapter code. Each is key-activated (its `*_API_KEY` env).
- Added a generic **custom provider** path: `OMNISTACKAI_CUSTOM_PROVIDERS` + per-id
  `OMNISTACKAI_CUSTOM_<ID>_{BASE_URL,MODEL,API_KEY}` → a first-class provider with no code change
  (`custom_provider_specs_from_env`, validated). `resolve_provider_specs()` = built-ins ∪ custom, and
  `bootstrap.py`/`overview.py` iterate it, so any provider is registered, selectable as the cloud tier
  or a fallback, and listed in the overview (`active` = key presence only). Price-book defaults added
  for the priced new providers; openrouter/custom unpriced.
- The local Ollama tier already runs any installed model via `OMNISTACKAI_OLLAMA_MODEL` /
  `OMNISTACKAI_OLLAMA_BASE_URL`. `.env.example` + `docs/MODEL_PROVIDER.md` document the whole catalog.

## Verification

- `task verify` — pass (217 agent-engine tests; 14 new). `platform_overview` demoed a 12-provider
  catalog including a custom `myco` provider; no key value in the snapshot. `task security:quick`,
  `task env:check` — pass. No network call anywhere; no external dependency; no vendor SDK.
- Tracker — R-236 (Model Fabric) at `Phase_Roadmap!A9:M9`; MVP total 131, Done 25; chart/styles intact.

## Product state

Offline builder complete (spec → IR + validate/normalize/fixtures → Next.js/FastAPI/Go adapters →
assembler → Git service → owned monorepo), plus the model fabric (now an **11-provider cloud catalog** —
OpenAI/Anthropic/Google/OpenRouter/Groq/DeepSeek/xAI/Mistral/Together/Fireworks + bring-your-own custom
endpoints, all key-activated, local Ollama always-on), the **Tier 0-3 runtime/deploy layer** (single
tier switch + a driver for every provider), and the **verifiable-engineering layer** (per-target gate
ladders and one-IR→monorepo verify plans). 25 tracker tasks Done; 0 cloud calls;
PostgreSQL/Compose untouched.

## Free-tier note (for the founder, verify before relying)

Recurring monthly free: local (forever), GitHub Codespaces, Vercel Hobby, Render/Netlify, Neon/Supabase.
One-time trials: E2B/Daytona credits, Fly credit, Railway credit, AWS/GCP/Azure. Prefer the recurring
ones for ongoing free use.

## Next action (R-237, pick with the founder — all offline-doable)

1. **IR-diff → patch-apply edit loop**: given an IR change, compute the changed generated files and
   apply them to an existing generated project (the "edit an app" motion, still deterministic/offline).
2. **Expand IR + adapter coverage**: auth/roles, entity relations, or DB migrations flowing through the
   adapters — deepens what one IR can express and generate.
3. **Combined build+verify surface**: a single per-target plan set (preview + deploy + verify) the
   console/CLI can render, tying R-233/234/235 together.
Cloud-gated (need a network machine or keys): run a Tier-0 preview end-to-end
(`task agent-engine:preview-plan`), live-verify a cloud driver (`OMNISTACKAI_TIER=2` + key), and the
deferred R-224 Next.js console upgrade. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
