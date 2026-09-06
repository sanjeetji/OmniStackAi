# Resume prompt (paste into any AI coding tool)

Copy everything in the block below into a fresh AI session to continue building OmniStackAI. It tells
the tool what we are building, where we are, the rules, and what to do next — and points it at the
repo's own state files, which are the real source of truth.

---

```text
You are continuing development of OmniStackAI, an AI software-engineering platform (an "Emergent-class"
builder: describe an app -> it generates a real, owned multi-platform app with verifiable engineering).

REPOSITORY
- GitHub: https://github.com/sanjeetji/OmniStackAi.git
- Local:  /Users/sanjeet_kumar/Documents/Projects/Startup/Omnistackai
- Work on branch `main` (it contains all work, R-001..R-228). Create ai/<task-id>-<slug> branches for
  new work. Git identity: user.name "sanjeetji", user.email "sk698166@gmail.com".

WHAT WE ARE BUILDING (differentiators, from the brief)
One Application IR -> many targets (web/mobile/backend); verifiable engineering (compile/test/security
gates); portable source the customer owns in Git; a local + cloud model fabric optimizing cost per
VERIFIED change; native mobile later. Closest competitor: Emergent.

SOURCE OF TRUTH — READ THESE FIRST, IN ORDER (do not trust this prompt over them; they are current):
1. AGENTS.md                      (portable working agreement / rules)
2. docs/START_HERE.md
3. .ai/PROJECT_STATE.yaml         (current phase, last task, next action)
4. .ai/CURRENT_TASK.yaml          (last task contract + completion evidence)
5. .ai/HANDOFF.md                 (exact status + next action + how to resume)
6. .ai/WORK_LOG.md                (chronological history)
7. R_&_D/OmniStackAI_Implementation_Brief_v6.md  (normative architecture; Sections 77 & 92 are
   NON-NEGOTIABLE; also follow 25, 26, 27, 74, 75, 83, 84, 85, 91)
8. R_&_D/OmniStackAI_Execution_Tracker_v6.xlsx, sheet `Phase_Roadmap` (task rows + status)
9. docs/MODEL_PROVIDER.md, docs/APPLICATION_IR.md, docs/CODEGEN.md, docs/GIT_SERVICE.md

START PROTOCOL
- Run: `task doctor` (needs pnpm+ripgrep; restore via corepack/brew if missing), `task verify`,
  `task ai:status`, `task ai:handoff`. `task verify` must stay green and network-independent.
- Confirm git branch/HEAD/clean tree. Then restate: phase, next Tracker ID, objective, blast radius.

WHAT IS ALREADY BUILT (all Python 3.13 stdlib-only, offline, in services/agent-engine; 140 tests pass)
- Model fabric: ModelProvider contract + registry; local Ollama adapter; Balanced ModelGateway
  (deterministic escalation ladder, no silent cloud fallback, context-budget guard); key-activated
  cloud adapters for Anthropic/OpenAI/Gemini/OpenRouter/Groq (no keys set -> zero cloud calls); true
  SSE streaming; usage/cost accounting (Decimal price book); env-driven cross-provider fallback +
  circuit breaker. Run it live: `task agent-engine:gateway:run` (routes to local Ollama qwen).
- FIRST BUILDER SLICE (the product): Application IR (framework-neutral spec) -> FrameworkAdapter
  contract + in-memory GeneratedProject -> NextjsWebAdapter (emits a real Next.js app from the IR) ->
  git_service (materializes it into a customer-owned Git repo with one commit). Proven end-to-end.
- Console: apps/console-web is a dependency-free static console (model/cost overview) +
  a Python snapshot exporter; `task console:serve`.

ID SCHEME (important): the workbook backlog already owns R-010..R-219 (planned agents/features). New
work this project added uses IDs AFTER R-219: R-220 streaming, R-221 fallback, R-222 console,
R-223 env-fallback, R-224 Next.js console upgrade (DEFERRED), R-225 IR, R-226 adapter contract,
R-227 Next.js adapter, R-228 git service. Do NOT overwrite backlog rows; continue from R-229.

ENVIRONMENT LIMITS discovered here
- npm front-end bundlers (Next.js SWC, Vite/esbuild) FAIL to install (native-binary downloads time
  out). So building/previewing generated apps and the Next.js console upgrade (R-224) need a
  network/cloud-capable environment. No cloud model keys are set (local Ollama only).

RULES (non-negotiable)
- One Tracker ID at a time; record a Standard AI Task Contract in .ai/CURRENT_TASK.yaml and
  .ai/tasks/<id>.md BEFORE coding. Make the smallest change. Deterministic tools before model calls.
- For <L3 work use local Ollama under Balanced routing; never silently use cloud if Ollama is down.
- Never put secrets in prompts/logs/source/state/tests/commits. Product code uses the platform
  provider interfaces, not vendor SDKs. Keep `task verify` network-independent (live checks are
  separate opt-in gates). Do NOT change PostgreSQL, add top-level folders, add infra beyond the
  current stage, or start native mobile/device-cloud before web/backend stability WITHOUT founder
  approval. STOP AND ASK before: any paid cloud service, DB engine change, new top-level folder,
  new infra, native/device work, or a materially different architecture decision.
- When updating the tracker .xlsx, insert the new row above the completed block, shift rows down,
  extend the Dashboard/table/conditional-formatting/data-validation ranges, and verify no ID is lost
  and the chart/styles stay intact (see prior tracker edits / .ai/WORK_LOG.md for the exact method).
- Definition of Done (Brief 27): requirement + acceptance recorded; impact plan; affected targets
  compile/tests pass with REAL command output; security gates; cost/model trace; commit tagged with
  the Tracker ID; update .ai/CURRENT_TASK.yaml, .ai/PROJECT_STATE.yaml, .ai/WORK_LOG.md,
  .ai/HANDOFF.md, PROJECT_STATE.md, CHANGELOG.md, and the tracker row. Push the branch; verify remote
  SHA == local HEAD. Never claim unexecuted tests.

WHAT TO DO NEXT (pick with the founder; all continue the builder slice)
- Offline-doable now: R-229 = a backend framework adapter (Go OR Python) so ONE IR emits web + backend
  together (the multi-target differentiator), same pattern as the Next.js adapter (emit files, assert
  contents, register in AdapterRegistry).
- Needs a network/cloud environment: sandbox/runtime provider + instant browser preview of the
  generated app (Brief 15/51); then deploy; and the deferred R-224 Next.js console upgrade.
- Deferred by governance: native mobile (R-010 etc.) until web/backend stability.

Begin by reading the files above and running the start protocol, then propose the next Tracker ID
(default R-229 backend adapter) with its task contract before writing code.
```
