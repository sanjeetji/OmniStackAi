# Current Handoff

Task ID: R-275
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-275) — Rich App Dashboard Overview Page in Generated Next.js Web App

- **Rich Entity-Aware Overview Page**:
  - `_overview_page(ir)` upgraded from a static 20-line bare HTML list to a full client component.
  - `"use client";` at top — matches pattern of all other generated screen pages.
  - Imports `useList<Plural>` for each entity with `Op.LIST` wired (via `_get_ops_by_entity`).
  - Calls `useList<Entity>({ limit: 1 })` per listable entity for live count; displays `.total`
    with loading fallback (`"…"`) and error fallback (`"—"`).

- **Entity Summary Cards**:
  - CSS Grid (`minmax(220px, 1fr)`) of white cards with box-shadow and border.
  - 32px `#0f172a` count, uppercase `#64748b` entity label, `#94a3b8` plural subtitle.
  - Only shown for entities with `Op.LIST` wired.

- **Screen Navigation Cards**:
  - CSS Grid (`minmax(240px, 1fr)`) of styled `<Link>` tiles.
  - Detail screens excluded via `_screen_intent` — keeps navigation clean.
  - Intent label badge (`Collection`, `Form`, `Screen`); role badge for non-public screens
    (`#eff6ff`/`#1d4ed8` pill with role ID).

- **Quick Actions Section**:
  - `+ Create {Entity}` blue CTAs (`#2563eb`) for each form screen, using `_match_entity` to
    resolve entity name.

- **Diff Invariance Fix**:
  - `ir.description` removed from `app/page.tsx` — was an existing violation (page changed when
    only description changed). Description already in `README.md`.
  - `test_console_snapshot.py` updated: `apps/web/app/page.tsx` removed from the expected edit-diff
    path set — the page is now stable across description-only changes.

- **Quality**:
  - Clean fallback when no entities (no hook calls/imports) and when no screens (no nav section).
  - 100% offline, zero external npm dependencies, zero new IR fields.
  - `# noqa: PLR0912` on function (high branch count justified).

## Test Coverage (R-275)

`services/agent-engine/tests/test_overview_dashboard.py` — 16 new tests:
1. `test_overview_page_is_client_component`
2. `test_overview_page_imports_uselist_hooks`
3. `test_overview_page_has_entity_cards`
4. `test_overview_page_has_screen_nav_links`
5. `test_overview_page_has_quick_actions`
6. `test_overview_page_no_ir_description`
7. `test_overview_page_shows_total_count`
8. `test_overview_page_no_entities_fallback`
9. `test_overview_page_no_screens_fallback`
10. `test_overview_page_diff_invariance`
11. `test_overview_page_link_to_collection_screen`
12. `test_overview_page_link_to_form_screen`
13. `test_overview_page_role_badge_on_restricted_screen`
14. `test_overview_page_entity_without_list_op_no_hook`
15. `test_full_project_overview_page_present`
16. `test_overview_page_no_detail_screens_in_nav`

## Preceded by:
- **R-274**: Form Screen Post-Submit Contextual CTAs, Record Navigation & Cancel Actions.
- **R-273**: Global Responsive Navigation Shell & Header Navbar in Generated Next.js Web App.
- **R-272**: Deep-Linking & Entity Lifecycle in Next.js Detail Screens.
- **R-271**: CSV Data Export & Bulk Export in Generated Next.js Collection Screens.
- **R-270**: Bulk Selection & Batch Deletion in Generated Next.js Collection Screens.
- **R-269**: Page Size Selector & Contextual Empty State CTAs in Generated Next.js Screens.
- **R-268**: Subcollection Child Item Deletion & Mutation Feedback in Master-Detail Views.
- **R-267**: Foreign-Key Relation Selectors & Parent Auto-Population in Generated Next.js Forms.
- **R-266**: Update/Edit Mode in Generated Next.js Forms & Collection Screen Edit Actions.
- **R-265**: Subcollection Navigation & Master-Detail Views in Generated Screens.
- **R-254** through **R-264**: Full CRUD, validation error bodies, pagination, sorting, total count headers, React hooks, interactive screens, field-level validation.

## Verification

- `task verify` — pass (695 agent-engine tests; 16 new in `test_overview_dashboard.py`).
- `task lint`, `task security:quick` — all pass.
- `task builder:demo -- minimal-blog` and `task builder:demo -- rideshare-favourites` — both pass.
- 0 local model calls, 0 cloud calls. Offline and deterministic.
