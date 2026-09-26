# Platform Completion

**This folder is the only work queue until the platform is finished.** Every open task from the
v6 tracker (task table, Production_Gates, RND_Gap_Audit), `.ai/ROADMAP.md`, `docs/ARCHITECTURE_MASTER_PLAN.md`, the draft specs in `R_&_D/specs/`, the template plan, the
commercial kickoff, the buildout plan and the V6 gap analysis has been reconciled here. Each has
a status, a priority and the queue item that covers it. Other documents are sources now, not
queues.

## What is here

| File | Use it for |
|---|---|
| `OmniStackAI_Master_Tasks.xlsx` | The main document. Sheets: **Start Here**, **Work Queue** (ordered), **All Tasks** (every item, filterable), **Summary**, **Pack Catalog**, **Tracker Phases** (how each v6 tracker phase is covered), **Targets**, **Decisions**, **Legend**. |
| `NATIVE_MOBILE_PREVIEW_PLAN.md` | How users preview Android and iOS apps: open source first, local then hosted, and how the sandbox isolates them. |
| `PACK_CATALOG.md` | Every horizontal and vertical pack (108 + 213 in 30 industries), with the roles and surfaces (app, web, admin panel, API) each industry gets. |
| `MASTER_TASKS.md` | The same content as Markdown, readable on GitHub and by any AI tool. |
| `tools/tasks_data.py` | The source of truth for statuses, priorities and order. |
| `tools/packs_data.py` | The source of truth for the pack catalog. |
| `tools/build_master_tasks.py` | Regenerates both documents. |

## The goal

A futuristic platform that turns a prompt into anything from one app to a whole ecosystem, with
modern UI and the maximum features the prompt implies, customisable afterwards.

- **Vibe Mode:** prompt → running app → live URL, machinery hidden. The API and database behind
  every feature are real.
- **Engineering Mode:** see the plan, choose the stack, import a repo, review diffs, see the
  verification report, open GitHub pull requests.

Stack policy: Next.js for web and admin. An app request that names no stack gets a React Native (Expo) app ready to
publish on Google Play and the App Store, **and** an installable PWA with a QR code. When the
user asks for native, Kotlin + Jetpack Compose and Swift + SwiftUI are generated (built in
Phase 5). Flutter and React.js are
not offered. PostgreSQL is the default database, with MongoDB as an option. Builds use NVIDIA
nemotron-3-ultra; its key lives only in `.env`.

## Rules for working from this folder

1. Take the first open task in the **Work Queue** whose dependencies are done. Do not skip ahead,
   and do not start anything outside the queue.
2. Follow `AGENTS.md` as usual: task branch, `.ai/CURRENT_TASK.yaml`, gates, CHANGELOG and
   PROJECT_STATE entries.
3. A task is marked **Completed** by its CHANGELOG entry. Then re-run the generator; do not edit
   the status by hand.
4. Any other change (a new task, a re-order, a founder decision) goes in `tools/tasks_data.py`,
   then re-run the generator. Commit the data file, the Markdown and the spreadsheet together.
5. **Keys last.** Build every integration completely (cloud, database, payments, email, stores,
   device services) so that only accounts and keys are missing; the founder supplies them at
   PC-070. Never put a key in code, prompts, logs or commits.
6. Stop and ask the founder before spending money, creating infrastructure or starting native
   (Kotlin/Swift) generation.

```bash
# Markdown only (any Python 3.9+):
python3 "R_&_D/Platform_Completion/tools/build_master_tasks.py"
# Markdown and spreadsheet:
python3 -m pip install openpyxl && python3 "R_&_D/Platform_Completion/tools/build_master_tasks.py"
```

## Statuses and priorities

| Status | Meaning |
|---|---|
| Completed | Built, tested and in CHANGELOG.md. |
| Completed - needs live proof | Built and tested offline, never run against a real account. |
| In Progress | Being worked on now. |
| Pending | Partly built, or waiting on a founder decision. |
| Not Started | Nothing built yet. |
| Superseded | Another task already did the job another way. |
| Deferred | Only after launch. |
| Dropped | Against the stack policy or no longer wanted. |

| Priority | Meaning |
|---|---|
| P0 | Launch blocker for Vibe Mode with real users. |
| P1 | Core promise: maximum features and Engineering Mode. |
| P2 | Hardening and depth: production trust, native, quality. |
| P3 | Nice to have. |
