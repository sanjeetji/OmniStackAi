# Current Handoff

Task ID: R-281
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)
Last verified implementation SHA: `ad94a72`

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author (with the tooling `Co-Authored-By` trailer).

## Completed (R-281) — Pagination, Sort & Search Controls on Subcollection Master-Detail Lists

Closed survey gap B. The generated subcollection master-detail lists rendered only `{sub.data.map(...)}`
with no controls, though the backend subcollection endpoints and the generated `useList<Child>By<Parent>`
hook already fully support `limit/offset/sort/order/q`. Added two shared helpers in `nextjs.py`:

- `_subcol_controls(sub, s_var)` — an **uncontrolled** search `<form>` (`defaultValue={…params.q}` +
  `new FormData(...).get("q")` on submit → `setSearch`, so no new component state) and a sort `<select>`
  (`id` + the subcollection's display fields, both directions → `setSort`).
- `_subcol_pagination(s_var)` — a **Prev / "Page X of Y (N total)" / Next** footer driven by
  `page`/`totalPages`/`total`/`setPage`, disabled at bounds and while loading.

Wired via `replace_all` into **both** byte-identical subcollection render sites — the collection
master-detail block (`_collection_screen_page`) and the detail-screen block (`_detail_screen_page`).
Submit-based search avoids a per-keystroke fetch storm, so the subcollection hook internals are unchanged
(unlike R-280's top-level hook). No new IR field, no npm dependency, `"use client"` preserved,
diff-invariant across `ir.description`.

## Verification

- `task verify` — pass (774 agent-engine tests; 6 new in `test_subcollection_list_controls.py`).
  `task lint`, `task security:quick` — pass. Both `task builder:demo`s — pass. 0 model calls; no DB.
- Tracker — R-281 at `Phase_Roadmap!A9:M9` (R-280 → row 10); rows 1..289 contiguous; table `A4:M289`;
  Dashboard ranges `B4:B289`/`H4:H289`, no `#REF!`; Done 70.

## Founder note — Groq key available

A Groq API key is available. The founder chose to keep this session local-only ("R-281 offline only"), so
live model-fabric verification with Groq is deferred. To enable later: put `GROQ_API_KEY` in the
**gitignored `.env`** (never in chat/commits/source), then `task agent-engine:gateway:run` with
`OMNISTACKAI_CLOUD_PROVIDER=groq`. Note this AI sandbox may block outbound calls to `api.groq.com`, so it
may need a real terminal.

## Blockers and risks

- None for the offline R-282 candidate below. Live preview/deploy and the deferred R-224 Next.js console
  upgrade still need a network environment / provider keys. Native mobile remains deferred (Brief §25/§91).

## Next action

Continue from R-282:

1. **Promote the boolean/enum collection filters to server-side `?field=` query params** — R-278's
   filters are currently client-side over the loaded page only (misleading across pagination). This needs
   a matching backend filter capability (Go + FastAPI + OpenAPI), so it is cross-cutting — a good
   full-stack task. Or
2. **Live-verify the model fabric with Groq** (now unblocked) — Balanced gateway → groq, capture the real
   result + cost accounting (see the Groq note above).

## Next command

`task ai:status`
