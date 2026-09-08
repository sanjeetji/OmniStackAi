# Current Handoff

Task ID: R-272
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-272) — Deep-Linking & Entity Lifecycle in Next.js Detail Screens

- **Query Param Auto-Loading**:
  - `_detail_screen_page` imports `useSearchParams` and `useEffect`.
  - Extracts `const queryId = searchParams.get("id");` and pre-populates `idInput` and `selectedId`.
  - Automatically loads the entity via `use<Entity>(selectedId)` on page mount when arriving from deep links or collection views.
  - Retains manual ID input search box as fallback when `?id=...` is absent.
- **Entity Lifecycle Actions in Detail View**:
  - "Export JSON" action button on the loaded item card: exports formatted record via client-side `Blob` (`application/json`) and dynamic anchor element with `URL.revokeObjectURL` cleanup.
  - "Edit {name}" action link: navigates to `/{form_screen.id}?id=${selectedId}` when `can_edit` and `form_screen` exist.
  - "Delete {name}" action button: when `can_delete` is True, prompts confirmation dialog, invokes `useDelete<Entity>()` with loading indicator (`deletingMain`), error banner (`deleteMainError`), and state cleanup (`setSelectedId(null); setIdInput("");`).
- **Breadcrumbs & Cross-Screen Navigation**:
  - Breadcrumb header links back to collection screen (`&larr; Back to {plural}`) when a complementary collection screen is detected in the IR.
  - Falls back to `&larr; Overview` when no collection screen is present.
- **Collection Screen Linkage**:
  - In `_collection_screen_page`, detects dedicated `detail_screen` for the entity in `ir.screens`.
  - Renders a styled "View" link button (`/{detail_screen.id}?id=${(item as any).id}`) in the table row actions cell.
- **Clean Isolation & Invariance**:
  - Zero substring collisions with subcollection selection state or controls.
  - Strict diff invariance maintained across `ir.description` changes.

## Preceded by:
- **R-271**: CSV Data Export & Bulk Export in Generated Next.js Collection Screens.
- **R-270**: Bulk Selection & Batch Deletion in Generated Next.js Collection Screens.
- **R-269**: Page Size Selector & Contextual Empty State CTAs in Generated Next.js Screens.
- **R-268**: Subcollection Child Item Deletion & Mutation Feedback in Master-Detail Views.
- **R-267**: Foreign-Key Relation Selectors & Parent Auto-Population in Generated Next.js Forms.
- **R-266**: Update/Edit Mode in Generated Next.js Forms & Collection Screen Edit Actions.
- **R-265**: Subcollection Navigation & Master-Detail Views in Generated Screens.
- **R-254** through **R-264**: Full CRUD, validation error bodies, pagination, sorting, total count headers, React hooks, interactive screens, field-level validation.

## Verification

- `task verify` — pass (646 agent-engine tests; 16 new in `test_detail_screen_lifecycle.py`).
- `task lint`, `task security:quick`, `task env:check` — all pass.
- 0 local model calls, 0 cloud calls. Offline and deterministic.
