# Current Handoff

Task ID: R-274
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- All work is on `main`; commit directly with the Tracker-ID discipline (contract → tests → gates →
  tracker → two commits tagged `[R-###]` → push → remote SHA check).
- Commits use `sanjeetji <sk698166@gmail.com>` as author.
- User permission is required prior to committing or pushing code.

## Completed (R-274) — Form Screen Post-Submit Contextual CTAs, Record Navigation & Cancel Actions

- **`lastSavedId` State & ID Capture**:
  - `_form_screen_page` declares `const [lastSavedId, setLastSavedId] = useState<string | null>(null);`.
  - Create branch: `const res = await create(formData);` + `if (res && (res as any).id) { setLastSavedId(String((res as any).id)); }`.
  - Update branch: `setLastSavedId(editId);` after `await update(editId, formData);`.
- **Interactive Success Banner**:
  - Exact message text preserved in `<span>{msg_jsx}</span>` (invariant to existing assertions).
  - Dismiss button (`&times;`) with `aria-label="Dismiss"` calling `setSuccess(false)`.
  - "View {name} →" `Link` to `/{detail_screen.id}?id=${lastSavedId || editId}` when `detail_screen` exists for entity.
  - "← Back to {plural}" `Link` to `/{list_screen.id}` when `list_screen` exists for entity.
  - "+ Create another {name}" button (create mode only) resetting `setSuccess(false); setLastSavedId(null);`.
- **Form Footer Cancel Button**:
  - Styled `Cancel` `Link` button navigating to `/{list_screen.id}` (or `/` when no list screen exists).
  - Reset `onClick` extended with `setLastSavedId(null);`.
- **Quality & Diff Invariance**:
  - 100% offline, zero external npm dependencies, zero new IR fields.
  - Zero references to `ir.description` in new output, preserving snapshot diff invariance.

## Test Coverage (R-274)

`services/agent-engine/tests/test_form_navigation_ctas.py` — 16 new tests:
1. `test_form_declares_lastsavedid_state`
2. `test_form_captures_created_record_id`
3. `test_form_captures_updated_record_id`
4. `test_success_banner_preserves_existing_message`
5. `test_view_record_link_rendered_when_detail_screen_exists`
6. `test_view_record_link_omitted_when_no_detail_screen`
7. `test_back_to_collection_link_in_success_banner`
8. `test_create_another_button_in_create_mode`
9. `test_dismiss_button_in_success_banner`
10. `test_cancel_button_rendered_in_footer`
11. `test_cancel_button_links_to_list_screen`
12. `test_cancel_button_links_to_root_when_no_list_screen`
13. `test_form_reset_clears_lastsavedid`
14. `test_diff_invariance_across_ir_description_changes`
15. `test_full_project_generation_succeeds`
16. `test_form_screens_without_update_op`

## Preceded by:
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

- `task verify` — pass (679 agent-engine tests; 16 new in `test_form_navigation_ctas.py`).
- `task lint`, `task security:quick` — all pass.
- `task builder:demo -- minimal-blog` and `task builder:demo -- rideshare-favourites` — both pass.
- 0 local model calls, 0 cloud calls. Offline and deterministic.
