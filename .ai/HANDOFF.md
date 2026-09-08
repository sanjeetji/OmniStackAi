# Current Handoff

Task ID: R-279
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.

## Completed (R-279) — Global Notification Toast System & Action Feedback in Generated Next.js Web App

- **`ToastProvider` and `useToast` Hook (`apps/web/components/toast.tsx`)**:
  - Emits client component (`"use client";`) with `createContext`, `useContext`, `useState`, `useCallback`, and `useEffect`.
  - Exports `ToastProvider`, `useToast`, `ToastType = "success" | "error" | "info"`, `ToastItem`, and `ToastContextValue`.
  - Methods: `addToast(message, type, duration)`, `removeToast(id)`, and typed helpers `toast.success()`, `toast.error()`, and `toast.info()`.
  - Floating viewport container fixed at bottom-right (`position: "fixed"`, `bottom: 24`, `right: 24`, `zIndex: 9999`, `aria-live="polite"`).
  - Toast cards with auto-dismiss timers (`setTimeout` / `clearTimeout`), manual dismiss `×` buttons, and distinct status color accents:
    - Emerald (`#a7f3d0`/`#15803d`/`✓`) for success.
    - Red (`#fecaca`/`#b91c1c`/`✕`) for error.
    - Blue (`#bfdbfe`/`#1d4ed8`/`ℹ`) for info.
- **RootLayout Integration (`apps/web/app/layout.tsx`)**:
  - Imports `ToastProvider` from `../components/toast` and wraps `<Navbar />` and `{children}`.
- **Screen Action Feedback**:
  - Collection screens: CSV export (`toast.info`), single delete (`toast.success` / `toast.error`), batch delete (`toast.success` with count / `toast.error`), and subcollection delete (`toast.success` / `toast.error`).
  - Detail screens: JSON export (`toast.info`), main delete (`toast.success` / `toast.error`), and subcollection delete (`toast.success` / `toast.error`).
  - Form screens: create and update submit (`toast.success` / `toast.error`) and Reset button (`toast.info`).
- **Quality & Safety**:
  - 100% offline, zero new external npm dependencies, zero new IR fields, strict diff invariance across `ir.description`.

## Test Coverage (R-279)

`services/agent-engine/tests/test_toast_notifications.py` — 14 new tests:
1. `test_toast_component_is_client_component`
2. `test_toast_component_exports_types_and_provider`
3. `test_toast_component_has_viewport_and_aria_live`
4. `test_toast_component_has_distinct_status_accents`
5. `test_toast_component_has_dismiss_button_and_auto_timer`
6. `test_toast_provider_in_generated_files`
7. `test_layout_imports_and_wraps_toast_provider`
8. `test_collection_screen_wires_use_toast`
9. `test_collection_screen_csv_export_triggers_toast`
10. `test_collection_screen_delete_actions_trigger_toast`
11. `test_detail_screen_wires_use_toast_and_feedback`
12. `test_form_screen_wires_use_toast_and_feedback`
13. `test_diff_invariance_across_ir_description_changes`
14. `test_demo_projects_generate_toast_component`

## Preceded by:
- **R-278**: Collection Screen Boolean & Enum Field Filtering with Segmented Controls.
- **R-277**: Form Screen Dirty State Tracking, Unsaved Changes Guard & Reset Confirmation in Generated Next.js Forms.
- **R-276**: Record Selector Dropdown, Prev/Next Record Navigation & Deep-Link Sync in Generated Next.js Detail Screens.
- **R-275**: Rich App Dashboard Overview Page in Generated Next.js Web App.
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

## Verification

- `task verify` — pass (756 agent-engine tests; 14 new in `test_toast_notifications.py`).
- `task lint`, `task security:quick` — all pass.
- `task builder:demo -- minimal-blog` and `task builder:demo -- rideshare-favourites` — both pass.
- 0 local model calls, 0 cloud calls. Offline and deterministic.
