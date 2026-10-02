# Goal check: a prompt to paste any time

Paste the block below into Claude Code, Codex or any AI assistant, at the root of this repository. It
checks the whole platform against the goal and reports what is done, what remains and what to do
next. It measures and verifies; it does not take anyone's word for it, including the tracker's.

---

```text
You are reviewing the OmniStackAI platform in this repository against its founder's goal. Do not
change any code. Read, run read-only commands and the benchmark if allowed, and report honestly -
including what is weak or missing. Never print secrets or the contents of .env.

THE GOAL
A platform, more advanced, smoother and faster than Emergent, Lovable, Bolt and Dyad, where any
person - technical or not - describes what they want and gets it:
1. ANY domain, not a fixed list. The platform itself decides the scope from the prompt: a single
   app, an app plus an admin panel, a few apps, or a complete ecosystem (e.g. customer app, provider
   app, dispatch console, admin, marketing website), web and mobile (React Native/Expo first; native
   Swift/Kotlin after M6; Flutter is out).
2. After the prompt, a short project brief with smart, pre-filled defaults: which apps, features,
   brand (name, logo, colours, style), languages, currency - one click to accept them all.
3. WOW UI: modern, polished, distinctive pages - not template-looking screens.
4. REAL APIs and a REAL database: every page reads and writes real data; nothing fake.
5. MAXIMUM FEATURES: tested building blocks (sign-in and roles, privacy, workflows, payments,
   scheduled jobs, live updates, notifications and push, uploads, search, forms, languages ...)
   chosen per product, plus model-written code for what no block covers.
6. NO HALLUCINATION: every page, link and API call is verified (types, build, a browser walk) and
   repaired before the user sees it; the build report says what is verified.
7. FAST and SMOOTH: instant previews, the phone QR works, chat edits in seconds, click-to-edit,
   publish; the user keeps customising the project afterwards.
8. Works without a paid key (free cloud tiers first, local Ollama as fallback); a paid model only
   raises quality.
Nothing already built is removed; the domain library and templates are hints and fast starts, never
limits.

WHERE TO LOOK
- R_&_D/Platform_Completion/M1_M6_PLAN.md - the plan (milestones M1 to M6, then M7 native).
- R_&_D/Platform_Completion/MASTER_TASKS.md - every task and its status (generated from
  tools/tasks_data.py); .ai/CURRENT_TASK.yaml - the task in progress; CHANGELOG.md, PROJECT_STATE.md.
- docs/runbooks/benchmark.md - the quality benchmark; results in ~/.omnistackai/benchmark/<run>/.
- services/agent-engine (planner, generators, verification), services/control-plane,
  apps/console-web (the Studio).

WHAT TO DO
1. For each goal point 1-8: is it met, partly met or not met? Give the evidence (a file, a test, a
   benchmark result, a command you ran) - not the tracker's word alone. Say where it falls short.
2. M1-M6 progress: for each milestone, its tasks with status (from MASTER_TASKS.md), and which are
   proven live versus only coded.
3. Benchmark: the latest run's mean score, its weakest cases and parts, and the change from the run
   before. If no recent run exists, say so and give the command to run one
   (scripts/benchmark.sh --design).
4. "Any domain" test: take three prompts from domains the platform has never seen (e.g. a
   veterinary-clinic chain, a cricket academy, a construction-site safety app). Explain - from the
   code, without a model call - what scope, apps and records the platform would plan for each,
   and whether that plan would be good.
5. Against Emergent, Lovable, Bolt and Dyad: where the platform is ahead, level and behind today,
   honestly.
6. The 5 most valuable next steps, in order, each with the task id if one exists.
Keep it short and plain: tables where they help, no marketing language.
```
