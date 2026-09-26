# Platform Completion

**This folder is the only work queue until the platform is finished.** Every open task from the
v6 tracker, `.ai/ROADMAP.md`, the draft specs in `R_&_D/specs/`, the template plan, the
commercial kickoff, the buildout plan and the V6 gap analysis has been reconciled here. Each has
a status, a priority and the queue item that covers it. Other documents are sources now, not
queues.

## What is here

| File | Use it for |
|---|---|
| `OmniStackAI_Master_Tasks.xlsx` | The main document. Sheets: **Start Here**, **Work Queue** (ordered), **All Tasks** (all 686, filterable), **Summary**, **Decisions**, **Legend**. |
| `MASTER_TASKS.md` | The same content as Markdown, readable on GitHub and by any AI tool. |
| `tools/tasks_data.py` | The source of truth for statuses, priorities and order. |
| `tools/build_master_tasks.py` | Regenerates both documents. |

## The goal

A futuristic platform that turns a prompt into anything from one app to a whole ecosystem, with
modern UI and the maximum features the prompt implies, customisable afterwards.

- **Vibe Mode:** prompt → running app → live URL, machinery hidden. The API and database behind
  every feature are real.
- **Engineering Mode:** see the plan, choose the stack, import a repo, review diffs, see the
  verification report, open GitHub pull requests.

Stack policy: Next.js for web and admin. An app request gets a React Native (Expo) app ready to
publish on Google Play and the App Store, **and** an installable PWA with a QR code. Native
Kotlin + Jetpack Compose and Swift + SwiftUI come **last** (Phase 5). Flutter and React.js are
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
5. Stop and ask the founder before anything in the **Decisions** sheet, paid cloud services, new
   infrastructure or native mobile work.

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
