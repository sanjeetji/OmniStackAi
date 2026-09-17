# Hybrid UI generation — the model writes the UI over the deterministic data layer (R-465)

OmniStackAI's competitors (v0 / Bolt / Lovable / Emergent) get "modern, describe-anything" UI by having a
frontier LLM write the code — and pay for it with output that often doesn't compile, hallucinates APIs, and
has a thin or missing backend. Pure templates have the opposite problem: verifiable, but a hard ceiling on
what the UI can look like. OmniStackAI's approach is a **hybrid**, and it is the moat:

```
┌──────────────────────────────────────────────────────────────────────┐
│  LLM writes the UI (app/page.tsx + app/<screen>/page.tsx)            │  ← opt-in model
│    constrained to import ONLY …                                      │
│  the REAL generated data layer: lib/types.ts, lib/hooks.ts, lib/api.ts│  ← deterministic
│    backed by …                                                        │
│  the deterministic backend: DB schema + migrations + FastAPI/Go      │  ← deterministic
│  + JWT auth + RBAC/row-ownership + pagination/filter/search           │
│    then …                                                            │
│  validate → feed the rejection back → retry (bounded) → template     │  ← repair loop
└──────────────────────────────────────────────────────────────────────┘
```

The model owns **look and features**; the deterministic core owns **correctness**. A generated app is both
modern and verifiably wired to a real API + DB + auth.

## What "grounded" means (and why the R-462 seed hallucinated)

The R-462 seed asked the model to use hooks that it *described by hand* — and that description had already
drifted from the generator (`refresh()` that never existed, `page/pageSize` params instead of the real
`limit/offset`, missing `use<Entity>`, `useUpdate/useDelete<Entity>`, `useList<Child>By<Rel>`, `useAuth`
advertised even when no auth-provider is generated). It also told the model to hardcode hex colours although
a complete design-token layer already ships in every app.

R-465 grounds the prompt in the **real** project, derived from the same generators so it cannot drift:

| Block | Source (`codegen/nextjs.py`) | What the model sees |
|---|---|---|
| `summarize_data_layer(ir)` | parses `_entity_interface`, `_hooks_file`, `_api_client_file` output | the entity interfaces, the `Use*` state interfaces, **every exported hook signature** (mutation hooks rendered from their real bodies), the `api.*` names — or an explicit "NO data hooks" line |
| `summarize_components(ir)` | the real `components/*.tsx` file set (`_component_files`) | every component file with its **real export names**; `auth-provider`/`useAuth` only when `needs_auth(ir)` |
| `summarize_design_tokens()` | `styles/tokens.css` (`_DESIGN_TOKENS_CSS`) | the real `--color-*`, `--space-*`, `--radius-*`, … names (never values), so `var(--…)` styling and dark mode just work |

`tests/test_llm_ui_grounding.py` has a **drift guard**: every `use*` name in the summary must be an exported
function in `render_hooks(ir)`, and signatures are reproduced verbatim.

## The repair loop (`codegen/llm_ui.py`)

One core, `_synthesize_file`, produces every model-written file:

1. Send `[SYSTEM, USER(grounded prompt)]`.
2. `clean_and_validate_jsx` checks the output: markdown fences stripped, `"use client"` ensured, **every
   static import** validated against the whitelist (multi-line aware; exactly `react`/`react-dom` plus
   `next/*`, `@/lib/*`, `@/components/*`, relative — `react-*` third-party packages, `require()` and dynamic
   `import()` are rejected), brace/paren balance, default export.
3. On rejection: append the prior output as `ASSISTANT` and a corrective `USER` turn carrying the reason
   ("Your previous `app/x/page.tsx` was REJECTED: …") and re-generate — up to `max_attempts` (default 3).
4. **Retry only on validator rejection, never on exceptions** (a timeout/transport error falls back at once).
5. Exhaustion or exception → the deterministic template for that file, with **no marker** (byte-equal to the
   template output). A successful file starts with
   `// [OmniStackAI] Mode: LLM-Synthesized Bespoke UI (<model>; attempt k/N)`.

Every file records a JSON-safe, secret-free `UiSynthesisOutcome(path, mode, attempts, model_id, last_reason)`
into the `ui_outcomes` sink you pass in. `last_reason` is a validator reason or an exception *type name* only
— provider errors can embed response bodies and must never leak into state or logs.

The corrective turn (`_repair_message`) is deliberately generic so R-466 can feed **compiler** output (`tsc`
errors) through the same channel.

## Opt-in switches (never in `task verify`)

- `provider=None` (the default everywhere) ⇒ every file is the deterministic template. This is what
  `task verify`, the builder demos and the snapshot/diff-invariance tests exercise (0 model calls).
- `provider=…` ⇒ the overview page `app/page.tsx` is model-written (R-462 behaviour).
- `synthesize_screens=True` (+ `provider`) ⇒ every `app/<screen>/page.tsx` is model-written too. It is an
  explicit keyword threaded `NextjsWebAdapter.generate → assemble_project → build_app_from_ir /
  build_app_from_prompt` (R-465 replaced a never-set `OMNISTACKAI_SYNTHESIZE_ALL_SCREENS` env gate).

## Compile-level repair (R-466, `codegen/hybrid_repair.py` + `verify/compile.py`)

The validator is string-level; the compiler has the last word. `verify/compile.py` runs the app's own
`tsc --noEmit --pretty false` and parses every diagnostic into a `CompileError(path, line, column, code,
message)` (`run_verify` only ever recorded exit codes). `compile_and_repair` then:

1. compiles; on failure groups the errors by file;
2. for **LLM-written files only** (`app/page.tsx`, `app/<screen>/page.tsx` — `llm_file_specs` reproduces the
   exact R-465 prompt and template for each), sends `[SYSTEM, USER(original grounded prompt),
   ASSISTANT(current file), USER("REJECTED: TypeScript reported N error(s): L12:5 TS2339 …")]` — the same
   `_repair_message` channel — validates the answer with `clean_and_validate_jsx`, and marks a success
   `… (<model>; compile-repair k/N)`;
3. applies the new content as a `ProjectDiff` of `MODIFIED apps/web/<path>` changes via `edit/apply_diff`,
   recompiles, and repeats for `max_rounds` (default 2: one model round, then a **revert round** that puts the
   deterministic template back for anything still failing);
4. returns a JSON-safe `CompileRepairReport(rounds, repaired, reverted, untouched_failures, final_ok)`.

A deterministic file with an error is listed in `untouched_failures` and **never rewritten** — that is a
generator bug to fix in the platform, not something to paper over with a model. The CLI commits the repair as
the customer identity, so the repo you get compiles.

## Rate-limit pacing (R-466, `model_gateway/cloud.py`)

A 429 is now a typed `ProviderRateLimitedError` (a `ProviderHTTPError` with `status_code` and
`retry_after_seconds`). `parse_retry_after` reads the standard `Retry-After` header (delay-seconds or an
HTTP-date) and falls back to the "Please try again in 6.495s" phrase Groq puts in the body. The adapter's
`generate()` waits that long (plus 0.5s; exponential 2s/4s backoff when no hint) and **re-sends the same
request**, up to `OMNISTACKAI_RATE_LIMIT_RETRIES` (default 2) and never longer than
`OMNISTACKAI_MAX_RETRY_AFTER_SECONDS` (default 60) — a longer ask re-raises immediately so the caller decides,
and every wait or give-up is logged with the numbers. Free tiers can ask for 1–3 minute waits: raise the cap
(e.g. `OMNISTACKAI_MAX_RETRY_AFTER_SECONDS=180`) for the hybrid CLI. No other error is ever retried; the
sleep is injectable, so the behaviour is unit-tested with 0 network. Every outcome record now carries the HTTP
status of a failed call (`ProviderRateLimitedError(429)`, `ProviderHTTPError(413)`) — never the body.

## Too-large requests: shrink and retry (R-466, `codegen/llm_ui.py`)

Waiting cannot fix a request that is too large on its own: Groq answers **413** when one request exceeds the
8k-tokens-per-minute limit by itself, and a full grounded UI request is ~9k tokens (≈5k prompt + 4k requested
output). On a 413 (or a 400 that says "context length"/"too large") the transcript shrinks and the engine
retries, each shrink costing one attempt from the same bounded budget:

1. **drop the echoed prior output** — the corrective text ("REJECTED: …" or the compiler's errors) is merged
   into the prompt turn, so a repair still carries its reason;
2. **switch to the compact grounding** — `compact_grounding(ir)` keeps every hook signature
   (`summarize_data_layer(max_chars=5_000)`), each component's primary export
   (`summarize_components(max_chars=4_000, max_names_per_file=1)`) and the token names
   (`summarize_design_tokens(max_chars=1_000)`); the compact overview/screen prompts are ≈12k chars (≈3k
   tokens), leaving room for a 4k-token page under an 8k limit (a test keeps them ≤ 14k chars).

`NextjsWebAdapter.generate` computes the compact blocks only when a provider is present (the deterministic
default is untouched), `llm_file_specs` carries a `compact_prompt`, and compile repair shrinks the same way.
Nothing else is ever retried on an exception.

## Run it

```bash
# Paid, per-generation model calls (your Groq/Gemini key lives only in the gitignored .env):
OMNISTACKAI_CLOUD_PROVIDER=groq task agent-engine:ui:synthesize -- "Create a food delivery app with restaurants and couriers"
# Optional: OMNISTACKAI_APP_OUT_DIR=/path/to/repo  OMNISTACKAI_GROQ_MODEL=llama-3.3-70b-versatile
#           OMNISTACKAI_WEB_NODE_MODULES=/path/to/an/existing/node_modules   (skips `pnpm install`)
```

Step 1 compiles the prompt into an IR; Step 2 builds the owned repo with every page model-written; Step 3
type-checks it with `tsc`, repairs model-written files from the compiler's errors, reverts what still fails,
commits the repair, and prints each compile round, what was repaired/reverted, and the final verdict, followed
by the per-file outcome table (`path | mode | attempts | model | last_reason`; compile repairs follow synthesis).
When pnpm/tsc are not available Step 3 is skipped with a clean message and the command to run later.

Local Ollama also works but the grounded prompt plus the repair transcript can exceed its 8192-token context;
the CLI warns about this. Groq/Gemini are the intended providers for the hybrid engine.

## What the first live run showed (Groq, free tier)

The founder's Groq account is on the free `on_demand` tier: **8,000 tokens per minute** and exactly one accessible
model (`openai/gpt-oss-120b`). A grounded prompt is ~5–6k tokens and a page is up to ~4k output, so the engine's
multi-call flow (intake + one call per page + repairs) cannot fit in that quota. In a scoped single-page run the
engine behaved exactly as designed: the model answered, the validator rejected the file with an exact reason
("Mismatched curly braces … truncated" — it hit the 4096 max-output), the repair loop engaged, the repair call was
rate-limited (HTTP 429), and the file fell back to the template with a truthful outcome record
(`mode=deterministic, attempts=2, last_reason=ProviderHTTPError`). Two consequences: the repair echo is capped at
8k chars, and R-466 added the rate-limit pacing described above, so the adapter now waits the provider's own
`Retry-After` instead of aborting. A larger TPM budget (Gemini via `GOOGLE_API_KEY`,
`OMNISTACKAI_CLOUD_PROVIDER=google`, or the Groq Dev tier) still makes the flow much faster.

**R-466 live runs (same account, reported as found):** the full three-step CLI ran end-to-end in 13 s —
intake succeeded, all five UI calls failed instantly with a non-429 HTTP status (hidden at the time behind the
bare type name — hence the status now in every outcome), every page fell back, and Step 3 compiled the repo
at 0 errors. A direct probe with the full 19k-char grounded prompt then **succeeded** on an empty window
(5,024 in / 3,639 out tokens), and a reproduction of the CLI path showed the 429 path working exactly as built
— typed `ProviderRateLimitedError(429)`, `Retry-After: 112` honoured — but giving up because 112 s exceeded
the 60 s cap (now tunable). That 429 was the **tokens-per-day** limiter (`Limit 200000, Used 191262`): the
day's proofs had spent the free tier's daily budget, so a further full live proof waits for the daily reset
or a Gemini key. The shrink-on-413 behaviour above is built from Groq's documented limit semantics and the
measured request sizes, and is covered by stub tests — not yet by a live run.

## The Studio: a file browser and a hybrid-UI toggle (R-467)

The engine (R-465/R-466) is opt-in-CLI-only; **R-467** is the first slice of it reaching the actual product
UI — the Studio a user opens in a browser (`task agent-engine:studio:serve` /
`task agent-engine:studio:preview`, `studio/server.py` + `live_serve.py` + `page.py`):

- **File browser.** Every recorded build gets `GET /api/build/{id}/files` (a sorted, flat, secret-free file
  list — `.git`, `node_modules`, `__pycache__`, `.next`, `.venv`, and any real `.env*` file are excluded;
  `.env.example` is kept) and `GET /api/build/{id}/file?path=...` (one file's content, path-safety-checked
  the same way `edit/apply.py` checks a write target — a `../` or symlink escape is refused). Both are pure,
  bounded filesystem reads (`studio/files.py`) — no toolchain, no running preview required, wired in
  build-only mode too. The page's file list is now clickable and opens the selected file in a read-only
  viewer pane.
- **Hybrid UI toggle.** `/api/build` accepts `hybrid_ui: bool`. When true, it threads
  `synthesize_screens=True` + a `ui_outcomes` sink into the **plain-prompt** and **Ecosystem Pack** paths
  (the two that already accept those kwargs); `ui_outcomes` comes back in the response, gets recorded in
  `StudioBuildHistory`, and the page shows a one-line summary plus a 🤖 badge on model-written files. The
  **Solution Pack** path has no such parameter on `build_solution_pack_project` — a request there is
  reported honestly as `hybrid_ui_active: false`, never silently ignored.
- Compile-level repair (R-466's `compile_and_repair`, which needs the `pnpm`/`tsc` toolchain) is **not**
  wired into the live server yet — that and multi-turn "continue editing this app" chat are follow-ups
  (see `.ai/tasks/R-467.md`'s Follow-ups).

## Limits and what comes next

- Brace/paren counting is a heuristic; the compiler (R-466) is the authority, and a file the compiler rejects
  twice goes back to its template rather than shipping broken.
- The engine reaches the Studio's file browser and a build-time toggle (R-467); the rest of the product-UI
  shell — multi-turn chat / in-place edits, and wiring compile-repair into the live server — is **R-468+**.
- The backend, DB, auth and data layer stay deterministic by design — that is the point.
