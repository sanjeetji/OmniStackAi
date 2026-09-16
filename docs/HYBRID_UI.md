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

## Run it

```bash
# Paid, per-generation model calls (your Groq/Gemini key lives only in the gitignored .env):
OMNISTACKAI_CLOUD_PROVIDER=groq task agent-engine:ui:synthesize -- "Create a food delivery app with restaurants and couriers"
# Optional: OMNISTACKAI_APP_OUT_DIR=/path/to/repo  OMNISTACKAI_GROQ_MODEL=llama-3.3-70b-versatile
```

It compiles the prompt into an IR, builds the owned repo with every page model-written, and prints a per-file
outcome table (`path | mode | attempts | model | last_reason`). Then compile it:

```bash
cd <repo>/apps/web && pnpm install --ignore-scripts && ./node_modules/.bin/tsc --noEmit
```

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
8k chars, and **rate-limit-aware pacing (HTTP 429 `retry-after`) in the model gateway is the R-466 companion**.
To run the full hybrid flow today, use a provider/tier with a larger TPM budget (e.g. Gemini via `GOOGLE_API_KEY`,
`OMNISTACKAI_CLOUD_PROVIDER=google`, or the Groq Dev tier).

## Limits and what comes next

- The validator is string-level (imports, balance, default export). A file can pass validation and still have
  **type errors** — that is exactly what **R-466** addresses: a capturing `tsc` executor feeding per-file
  compiler errors back through the same repair channel, with per-file template fallback.
- The product UI shell (chat, live preview, file tree) that drives this engine is **R-467**.
- The backend, DB, auth and data layer stay deterministic by design — that is the point.
