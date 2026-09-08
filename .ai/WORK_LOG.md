# Work Log

## 2026-09-08 — R-274

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-274.md`.
- `nextjs.py` (`_form_screen_page`):
  - Detected `detail_screen` and `list_screen` for the entity in `ir.screens` using `_screen_intent`.
  - Added `lastSavedId` state: `const [lastSavedId, setLastSavedId] = useState<string | null>(null);`.
  - `handleSubmit` create branch: `const res = await create(formData);` + `if (res && (res as any).id) { setLastSavedId(String((res as any).id)); }`.
  - `handleSubmit` update branch: `setLastSavedId(editId);` after `await update(editId, formData);`.
  - Success banner upgraded to interactive action panel:
    * Preserved exact message text wrapped in `<span>{msg_jsx}</span>` for existing test invariance.
    * Dismiss button (`&times;`) with `aria-label="Dismiss"` calling `setSuccess(false)`.
    * "View {name} &rarr;" `Link` to `/{detail_screen.id}?id=${lastSavedId || editId}` (guarded by id expression check), when `detail_screen` exists.
    * "&larr; Back to {plural}" `Link` to `/{list_screen.id}`, when `list_screen` exists.
    * "+ Create another {name}" button (in create mode) calling `setSuccess(false); setLastSavedId(null);`.
  - Form footer: added `Cancel` `Link` button to `/{list_screen.id}` (or `/`); Reset `onClick` now includes `setLastSavedId(null);`.
- Added `services/agent-engine/tests/test_form_navigation_ctas.py` with 16 comprehensive unit tests.
- `task verify` — 679 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. `builder:demo minimal-blog` and `builder:demo rideshare-favourites` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-274.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-273


- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-273.md`.
- `nextjs.py`:
  - Implemented `_navbar_component(ir: ApplicationIR) -> str`:
    * Emitted client component (`"use client";`) with `usePathname` from `"next/navigation"`.
    * Implemented active route detector `isLinkActive(href)` and visual highlight styling helper `navLinkStyle(active)`.
    * Rendered app branding with avatar logo badge (first letter of `ir.name`) and title linking to `/`.
    * Rendered "Overview" link to `/`.
    * Dynamically rendered screen navigation links for primary collection, form, and generic screens from `ir.screens`, displaying screen title, role pill badges for non-public screens, and active state highlights.
    * Excluded parameter-dependent `detail` screens from the horizontal nav bar to keep top navigation focused.
    * Detected first create form screen in `ir.screens` and rendered a prominent `+ New {Entity}` / `+ Create` quick-action CTA button on the right side of the navbar.
    * Supported empty screens with clean fallback.
  - Updated `_LAYOUT`:
    * Imported `Navbar` from `../components/navbar`.
    * Rendered `<Navbar />` inside `<body>` above `{children}`, wrapping all pages in a cohesive layout with typography and background tokens (`#f8fafc`).
  - Registered `GeneratedFile("components/navbar.tsx", _navbar_component(ir))` in `NextjsWebAdapter.generate()`.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_navbar_navigation.py` with 17 comprehensive unit tests.
- Updated `test_nextjs_adapter.py` to expect `components/navbar.tsx`.
- `task verify` — 663 tests pass (17 new), 0 failures. `task lint`, `task security:quick`, `task doctor` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-273.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-272

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-272.md`.
- `nextjs.py`:
  - `_detail_screen_page`:
    * Imported `useState, useEffect` from `"react"` and `useSearchParams` from `"next/navigation"`.
    * Implemented query parameter extraction: `const queryId = searchParams.get("id");` initializing `idInput` and `selectedId`, and synchronized with `useEffect` when `queryId` updates.
    * Added entity deletion: when `can_delete`, imported and wired `useDelete{name}()` with `handleDelete` prompting confirmation dialog, setting loading state (`deletingMain`), error capture (`deleteMainError`), and state cleanup.
    * Added single-record client-side JSON export: `handleExportJson` formats entity record to formatted JSON via `Blob`, dynamic anchor element, and `URL.revokeObjectURL`.
    * Added breadcrumb navigation: links back to collection screen (`&larr; Back to {plural}`) when complementary collection screen is detected.
    * In item card header: rendered action buttons bar with "Export JSON", "Edit {name}" (navigating to `/{form_screen.id}?id=${selectedId}` when editable), and "Delete {name}" (when deletable), with error feedback alert banner.
  - `_collection_screen_page`:
    * Detected dedicated `detail_screen` for the entity in `ir.screens`.
    * When `detail_screen` exists, rendered a styled "View" link button (`/{detail_screen.id}?id=${(item as any).id}`) in the table row actions cell.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_detail_screen_lifecycle.py` with 16 comprehensive unit tests.
- `task verify` — 646 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-272.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-271

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-271.md`.
- `nextjs.py`:
  - Added `handleExportCsv(selectedOnly: boolean = false)` helper function to `_collection_screen_page`:
    * Filters items by `checkedIds` when `selectedOnly` is true (`(data ?? []).filter((item: any) => checkedIds.includes(item.id))`), or exports all items (`data ?? []`).
    * Early return when no items are available for export.
    * Implemented strict RFC 4180 value serialization helper `toCsvVal`: formats `null`/`undefined` as `""`, safely serializes objects via `JSON.stringify`, escapes internal double quotes (`"`) as `""`, and wraps all values in double quotes.
    * Included all declared entity fields (`entity.fields`) in both headers and row mapping.
    * Managed browser download lifecycle using `Blob([csvContent], { type: "text/csv;charset=utf-8;" })`, `URL.createObjectURL(blob)`, temporary `<a>` element with `download="{plural.lower()}_export.csv"`, automated trigger `link.click()`, DOM removal, and memory cleanup with `URL.revokeObjectURL(url)`.
  - Top toolbar:
    * Added "Export CSV" button in the table controls section alongside Search and Refresh (`disabled={!data || data.length === 0}`).
  - Contextual Bulk Actions Bar:
    * Added "Export Selected ({checkedIds.length})" button calling `handleExportCsv(true)` inside `{checkedIds.length > 0 && ...}`.
    * Ensured Export Selected button is present whether or not the entity has delete capability; coexists with "Delete Selected" when deletion is enabled.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_collection_csv_export.py` with 16 comprehensive unit tests.
- `task verify` — 630 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-271.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-270

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-270.md`.
- `nextjs.py`:
  - Added multi-record row selection state to `_collection_screen_page`:
    * `const [checkedIds, setCheckedIds] = useState<string[]>([]);`
    * `const allCurrentIds = (data ?? []).map((item: any) => item.id).filter(Boolean);`
    * `const isAllChecked = allCurrentIds.length > 0 && allCurrentIds.every((id: string) => checkedIds.includes(id));`
    * `const handleCheckAll = () => { if (isAllChecked) { setCheckedIds((prev) => prev.filter((id) => !allCurrentIds.includes(id))); } else { setCheckedIds((prev) => Array.from(new Set([...prev, ...allCurrentIds]))); } };`
    * `const handleToggleRow = (id: string) => { setCheckedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])); };`
    * `const handleClearSelection = () => { setCheckedIds([]); };`
  - In `handleDelete(id)`: automatically cleaned up deleted ID from selection via `setCheckedIds((prev) => prev.filter((x) => x !== id));`.
  - When `can_delete` is True:
    * Declared `batchDeleting` loading state and `batchDeleteError` error state.
    * Implemented `handleBatchDelete` with confirmation prompt (`confirm("Are you sure you want to delete {count} {name/plural}?")`), concurrent execution (`await Promise.all(checkedIds.map(id => remove(id)))`), selection clearing, automatic `refetch()`, and error capture.
    * Rendered dismissible `batchDeleteError` alert banner with retry/dismiss button.
  - Rendered contextual floating/inline Bulk Actions Bar above the table when `checkedIds.length > 0`:
    * Shows selection count badge: `{checkedIds.length} {name/plural} selected`.
    * Includes `Clear selection` button bound to `handleClearSelection`.
    * When `can_delete` is True, renders `Delete Selected ({checkedIds.length})` button with loading state `{batchDeleting ? "Deleting..." : ...}`.
  - Table header `<thead>`:
    * Rendered master checkbox column with `aria-label="Select all"`, `checked={isAllChecked}`, and `onChange={handleCheckAll}`.
  - Table body `<tbody>`:
    * Adjusted loading and empty state `colSpan` to account for checkbox column (`1 + len(display_fields) + (1 if has_actions_col else 0)`).
    * Rendered row selection checkbox in each data row with `e.stopPropagation()` so selecting checkboxes does not toggle subcollection detail panels.
    * Highlighted selected rows with `#f8fafc` background.
  - Maintained strict diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_collection_bulk_actions.py` with 16 comprehensive unit tests.
- `task verify` — 614 tests pass (16 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-270.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-269

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-269.md`.
- `nextjs.py`:
  - Added `setPageSize: (size: number) => void;` to `UseListState<T>` interface in `_generate_hooks_ts`.
  - Implemented `setPageSize = useCallback((newPageSize: number) => { setParams((prev) => ({ ...prev, limit: Math.max(1, newPageSize), offset: 0 })); }, []);` in both `useList<Entities>()` and `useList<Children>By<Rel>()`.
  - Included `pageSize` and `setPageSize` in returned state objects of both list hooks.
  - In `_collection_screen_page`:
    - Destructured `pageSize` and `setPageSize` from `useList<Plural>()`.
    - Rendered an accessible `<select id="pageSizeSelect">` with `aria-label="Select page size"` directly in the table footer alongside pagination buttons with options: 10, 25, 50, 100 per page.
    - Updated table body empty state (`data && data.length === 0`):
      * When search is active (`searchInput.trim()`): renders `No <plural> matching "<searchInput>".` with interactive `Clear search` CTA button (`onClick={() => { setSearchInput(""); setSearch(""); }}`).
      * When no search is active and `form_screen` exists: renders `No <plural> found yet.` with styled `+ Create first <Entity>` CTA link (`href="/{form_screen.id}"`).
      * When no `form_screen` exists: renders fallback `No <plural> found.`.
    - In subcollection panels (`_collection_screen_page` and `_detail_screen_page`):
      * When child data is empty and `child_form` exists: renders `No <children> found for this <entity>.` alongside a styled `+ Add first <Child>` link (`href="/{child_form.id}?{sub.id_param}=${selectedId}"`).
  - Preserved byte-for-byte diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_collection_pagination_empty_states.py` with 15 unit tests covering interface declaration, hook implementations, return object fields, selector rendering, options, search mismatch empty state with clear search button, form screen empty state CTA link, fallback empty state, subcollection empty state CTAs, diff invariance, and full project generation.
- `task verify` — 598 tests pass (15 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-269.md, PROJECT_STATE.yaml, PROJECT_STATE.md, CHANGELOG.md, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-268

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-268.md`.
- `nextjs.py`:
  - Imported `HttpMethod` from `..application_ir`.
  - Added fallback entity resolution for `DELETE` endpoints where `response_schema` or `request_schema` was omitted in `_get_ops_by_entity` and `_generate_api_client_ts`.
  - Updated `_generate_hooks_ts` to source `ops_by_entity` from `_get_ops_by_entity(ir)`, ensuring complete consistency across API client, hooks, and screen pages.
  - Added `can_delete: bool = False` to `SubcollectionInfo` dataclass and set it in `_subcollections_for_parent` via `Op.DELETE in ops_by_entity.get(child_name, set())`.
  - In `_collection_screen_page`:
    - Automatically imported `useDelete<Child>` for each deletable subcollection, avoiding duplicate imports when parent entity shares delete capability.
    - Instantiated delete hooks at component level: `const { remove: remove<Child>, loading: deleting<Child>, error: delete<Child>Error } = useDelete<Child>();`.
    - Declared `handleDelete<Child>` handler with confirmation prompt (`confirm("Are you sure you want to delete this <Child>?")`), try/catch guard, and automatic subcollection refetch (`<subcol>.refetch()`).
    - Rendered mutation error feedback alert banner (`{delete<Child>Error && ...}`) when deletion fails.
    - Rendered an accessible, styled Delete button on each child item card with `e.stopPropagation()`, disabled state during mutation (`disabled={deleting<Child>}`), and dynamic label `{deleting<Child> ? "Deleting..." : "Delete"}`.
  - In `_detail_screen_page`:
    - Mirrored identical child deletion hook imports, hook instantiations, delete handlers, mutation error alert banners, and Delete buttons on child cards.
  - Clean fallback safety: subcollections whose child entity lacks `Op.DELETE` emit zero deletion code, and entities without subcollections emit zero subcollection code.
  - Preserved byte-for-byte diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_subcollection_deletion.py` with 13 unit tests covering detection, non-delete omission, fallback detection, hook imports, handler declaration with confirm and refetch, button rendering with stopPropagation, error alert display, detail screen wiring, mixed multi-subcollection wiring, diff invariance, and full project generation.
- `task verify` — 583 tests pass (13 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-268.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-267

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-267.md`.
- `nextjs.py`:
  - Imported `RelationKind` from `..application_ir`.
  - Added `_snake(value: str) -> str` string conversion helper.
  - Added `ParentRelationInfo` dataclass and `_parent_relations_for_entity(entity: Entity, ir: ApplicationIR) -> list[ParentRelationInfo]` helper:
    - Detects `RelationKind.MANY_TO_ONE` relations and fields ending in `_id` on child entities where the parent entity has `Op.LIST`.
    - Resolves parent entity, pluralized name, hook name (`useList<ParentPlural>`), primary display field (`title`/`name`/`id`), and display label.
  - Enhanced `_form_screen_page`:
    - Collects parent relations via `_parent_relations_for_entity(entity, ir)` and maps them by `field_name`.
    - Appends any missing foreign key fields from parent relations to `editable_fields`.
    - Automatically imports parent list hooks (`useList<ParentPlural>`) from `"../lib/hooks"`.
    - Wires parent list hooks at component top level (`const <parents>List = useList<Parents>();`).
    - Enriches `searchParams` prefilling effect with alias resolution (`<field>`, `<relation>_id`, `<relation>Id`, `<relation>`), ensuring child forms opened from `+ New <Child>` links pre-populate the parent foreign key in `formData`.
    - Enhances `handleSubmit` client-side error checking to validate required UUID / relation fields, displaying field-level errors when unselected.
    - Replaces raw text inputs for foreign key fields with accessible `<select>` dropdowns:
      - Default option showing loading state: `<option value="">{<parents>List.loading ? "Loading <parents>..." : "Select <parent>..."}</option>`.
      - Mapped options from parent list items displaying primary title/name: `<option key={item.id} value={item.id}>{String(item.title ?? item.name ?? item.id)}</option>`.
      - Visual parent linkage badge displayed when foreign key is selected: `&bull; Selected <Parent> linked`.
      - Integrated with `fieldErrors` display and `aria-invalid` attribute.
    - Preserved fallback safety: independent entities without relations (e.g. `minimal-blog` Post) omit relation list hooks, dropdowns, and badges.
    - Preserved byte-for-byte diff invariance across `ir.description` modifications.
- Added `services/agent-engine/tests/test_form_relation_screens.py` with 12 unit tests covering helper detection, independent entity omission, hook import and invocation, select dropdown rendering, visual badge display, searchParams alias prefill, client-side required validation, minimal-blog clean fallback, diff invariance, and project generation.
- `task verify` — 570 tests pass (12 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-267.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-266

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-266.md`.
- `nextjs.py`:
  - Updated `_collection_screen_page`:
    - Computed `can_edit = (Op.UPDATE in ops) and (form_screen is not None)`.
    - Rendered an "Edit" action `<Link>` in the master table pointing to `/{form_screen.id}?id=${(item as any).id}` with `onClick={(e) => e.stopPropagation()}` to avoid toggling table row selection.
    - Updated subcollection master-detail view to render `+ New <Child>` link (`/{child_form.id}?{sub.id_param}=${selectedId}`) when complementary form screen exists for the child entity.
  - Enhanced `_form_screen_page`:
    - Computed `can_update = Op.UPDATE in ops` and `can_create = Op.CREATE in ops`.
    - When `can_update` is True, imported `useUpdate<Entity>`, `use<Entity>`, and `useSearchParams` from `"next/navigation"`.
    - Read `editId = searchParams.get("id")` and `isEdit = Boolean(editId)`.
    - Wired `const { update, loading: updating, error: updateError } = useUpdateArticle();` and `const { data: initialData, loading: fetchingInitial } = use<Entity>(editId);`.
    - Added `useEffect` to prefill `formData` when `initialData` changes in edit mode.
    - Branched `handleSubmit` to call `await update(editId, formData)` when in edit mode vs `await create(formData)` when in create mode.
    - Dynamically adapted headers (`{isEdit ? "Edit " + name : screen.name}`), submit button label (`{((submitting || updating) ? "Saving..." : (isEdit ? "Update " + name : "Save " + name))}`), loading indicator, and success alert banner.
    - Maintained clean fallback safety for entities without `Op.UPDATE` (e.g. `minimal-blog` Post), emitting zero edit/update code.
    - Preserved byte-for-byte diff invariance across `ir.description` modifications.
  - Updated `_screen_page` routing to dispatch to form screens when `Op.CREATE in ops or Op.UPDATE in ops`.
- Added `services/agent-engine/tests/test_form_update_screens.py` with 12 unit tests covering hook imports, search params, editId extraction, initialData prefill, update submission branching, dynamic labels, create-only fallback, collection screen edit action with stopPropagation, subcollection + New child link, diff invariance, and NextjsWebAdapter project generation.
- `task verify` — 558 tests pass (12 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-266.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-265

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-265.md`.
- `nextjs.py`:
  - Added `SubcollectionInfo` dataclass and `_subcollections_for_parent(parent_name: str, ir: ApplicationIR) -> list[SubcollectionInfo]` helper:
    - Scans `ir.relations` where `rel.target_entity == parent_name` and foreign key relation is wired with `Op.LIST_BY`.
    - Resolves child entity, relation name, capitalized names, list hook name (`useList<Children>By<Rel>`), and display fields.
  - Enhanced `_collection_screen_page`:
    - Checks for subcollections using `_subcollections_for_parent(entity.name, ir)`.
    - Imports subcollection hooks (e.g. `import { useListCommentsByPost } from "../lib/hooks";`) and child entity types (e.g. `import type { Comment } from "../lib/types";`) on dedicated lines preserving exact substring matches for parent imports.
    - Adds `selectedId` state (`const [selectedId, setSelectedId] = useState<string | null>(null);`) and active subcollection tab state for multi-subcollection entities.
    - Wires subcollection hooks at top level scoped to `selectedId` (e.g. `const commentsSubcol = useListCommentsByPost(selectedId);`).
    - Enriches master table with interactive row selection (`onClick={() => setSelectedId(selectedId === item.id ? null : item.id)}`), visual row selection highlight, and action column button (`"View Details"` / `"Hide Details"`).
    - Renders master-detail subcollection section below table when an item is selected:
      - Parent entity header banner with "Close Details" action.
      - Tab bar for multi-subcollection entities with interactive switching and live total count badges (`{subcol.total}`).
      - Child items list rendering loading state, error state with retry, empty state, and child item cards displaying key scalar attributes.
      - Subcollection refresh action button.
  - Implemented `_detail_screen_page`:
    - Dedicated screen for screens with `intent == "detail"`.
    - Renders parent entity detail view fetching with `use<Entity>(id)`.
    - Renders parent attribute grid, back navigation to collection screen, and nested child subcollections section.
  - Updated `_screen_page` routing to dispatch `intent == "detail"` to `_detail_screen_page`.
  - Maintained fallback safety: entities without subcollections (e.g. `rideshare-favourites`) emit zero subcollection code, state, or hooks.
  - Preserved diff invariance: generated screens do not reference `ir.description`, preventing diff drift in `test_console_snapshot.py`.
- Added `services/agent-engine/tests/test_subcollection_screens.py` with 19 unit tests covering subcollection detection, hook and type imports, selection state, scoped invocation, total count badges, child items and states, master table row click interaction, fallback cleanliness, multi-subcollection tabs, detail screens, diff invariance, and project generation.
- `task verify` — 546 tests pass (19 new), 0 failures. `task lint`, `task security:quick` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-265.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-264

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-264.md`.
- `nextjs.py`:
  - Added `extractFieldErrors(error: unknown): Record<string, string>` export in `apps/web/lib/api.ts`:
    - Normalizes Go backend structured errors (`{"errors": [{"field": "...", "rule": "...", "message": "..."}]}`).
    - Normalizes FastAPI structured errors (`{"detail": [{"loc": ["body", "..."], "msg": "..."}]}`).
    - Safely falls back to empty map for non-validation errors.
  - Enhanced `_form_screen_page`:
    - Imported `extractFieldErrors` from `../lib/api`.
    - Added `fieldErrors` state (`const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});`).
    - Implemented client-side pre-validation inside `handleSubmit`: checks `required` fields, string `max_length`, numeric `min`/`max`, and enum options before network requests, setting `fieldErrors` and halting on failure.
    - Updated submission error handling to call `extractFieldErrors(err)` and populate `fieldErrors` with server-side validation failures.
    - Conditionally styled inputs with red borders (`fieldErrors[f.name] ? "1px solid #ef4444" : "1px solid #cbd5e1"`) and accessibility attributes (`aria-invalid={!!fieldErrors[f.name]}`).
    - Rendered dedicated field error message spans directly beneath invalid inputs.
    - Added reactive error clearing on input edit (`onChange`).
    - Rendered interactive `<select>` dropdowns with declared options for enum fields.
    - Reset button clears `fieldErrors` alongside form data.
    - Added warning banner (`"Please correct the highlighted errors below before submitting."`) when field errors exist.
    - Preserved diff invariance by avoiding references to `ir.description`.
- Added `services/agent-engine/tests/test_form_validation_screens.py` with 12 unit tests covering `extractFieldErrors`, form screen error imports, client-side pre-validation, server error extraction, input styling, error spans, clear-on-change, enum dropdowns, reset button, and diff invariance.
- `task verify` — 527 tests pass (12 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-264.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-263

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-263.md`.
- `nextjs.py`:
  - Implemented `_match_entity(screen: Screen, ir: ApplicationIR) -> Entity | None` using multi-token score matching across screen IDs, component tags, and actions.
  - Implemented `_screen_intent(screen: Screen) -> str` classifying screens as `"collection"`, `"form"`, or `"generic"`.
  - Implemented `_get_ops_by_entity(ir: ApplicationIR) -> dict[str, set[Op]]` mapping available operations to avoid generating broken imports.
  - Implemented `_collection_screen_page`:
    - Emits `"use client";` directive at top.
    - Imports `useList<Entities>` (and `useDelete<Entity>` if `Op.DELETE` wired) from `../lib/hooks` and entity type from `../lib/types`.
    - Live search input bound to `setSearch` and form submission.
    - Sortable table headers bound to `setSort` with order indicators (`↓`/`↑`).
    - Pagination controls (`Previous`, `Next`, `Page X of Y`) bound to `setPage`.
    - Loading, error with retry button, and empty state cards.
    - Header with role badge, overview link, and navigation to complementary form screen (`+ New <Entity>`).
  - Implemented `_form_screen_page`:
    - Emits `"use client";` directive at top.
    - Imports `useCreate<Entity>` from `../lib/hooks` and entity type from `../lib/types`.
    - Schema-derived inputs for each entity field: checkbox for `BOOL`, textarea for `TEXT`, number for `INT`/`FLOAT`, datetime-local for `DATETIME`, text for `STRING`.
    - Required indicators (`*`) and HTML `required` attributes.
    - Submission handling with `create(formData)`, success feedback banner, error capture banner, and reset/cancel navigation.
  - Implemented `_fallback_screen_page` rendering clean role badge, component tags, actions, and navigation links.
  - Preserved diff invariance by avoiding any reference to `ir.description` in generated screen pages.
  - Exported public `render_screen_page(screen: Screen, ir: ApplicationIR) -> str` and added to `omnistackai_agent_engine.codegen`.
- Created `services/agent-engine/tests/test_screen_generation.py` with 9 unit tests covering `"use client"`, collection screen data binding (search, pagination, sort, delete), form screen schema inputs and submission, fallback screens, full project generation, and diff invariance.
- `task verify` — 515 tests pass (9 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-263.md, PROJECT_STATE.yaml, docs/CODEGEN.md, docs/PROGRESS.md.

## 2026-09-08 — R-262

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-262.md`.
- `nextjs.py`:
  - Implemented `_hooks_file(ir: ApplicationIR) -> str` emitting strongly-typed React hooks in `apps/web/lib/hooks.ts`.
  - Added `"use client"` directive, React built-in imports (`useCallback`, `useEffect`, `useState`, `type Dispatch`, `type SetStateAction`), types from `./types`, and API client helpers from `./api`.
  - Defined shared interfaces: `UseListParams`, `UseListState<T>`, `UseDetailState<T>`, `UseMutationState<TData, TResult = TData>`.
  - For each entity in `ir.entities`:
    - `useList<Entities>`: manages `params` state (`limit`, `offset`, `sort`, `order`, `q`), computes pagination (`page`, `pageSize`, `totalPages`), provides `setPage`, `setSearch`, `setSort`, `refetch`, and fetches with `api.list<Entities>WithCount`.
    - `use<Entity>`: detail hook fetching entity by ID via `api.get<Entity>`.
    - `useCreate<Entity>`: mutation hook with `create`, `mutate`, `loading`, `error`, `reset`.
    - `useUpdate<Entity>`: mutation hook with `update`, `mutate`, `loading`, `error`, `reset`.
    - `useDelete<Entity>`: mutation hook with `remove`, `mutate`, `loading`, `error`, `reset`.
  - For subcollections: `useList<Entities>By<Rel>` with scoped relation ID, pagination, search, and sorting.
  - Exported unified `hooks` object.
  - Added public `render_hooks(ir: ApplicationIR) -> str` and wired `GeneratedFile("lib/hooks.ts", _hooks_file(ir))` into `NextjsWebAdapter.generate`.
  - Exported `render_hooks` in `omnistackai_agent_engine/codegen/__init__.py`.
- Created `services/agent-engine/tests/test_nextjs_hooks.py` with 15 unit tests covering `"use client"`, imports, interfaces, list hook pagination/search/sorting, detail hook, mutation hooks, subcollection hooks, empty IR, unwired operations, and example IRs.
- `task verify` — 506 tests pass (15 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated CURRENT_TASK.yaml, tasks/R-262.md, PROJECT_STATE.yaml.

## 2026-09-08 — R-261

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-261.md`.
- `data_access.py`:
  - Added `_searchable_fields(entity: Entity) -> list[str]` selecting `FieldType.STRING` and `FieldType.TEXT` fields.
  - Python repository: `list_<table>` and `count_<table>` accept `q: str | None = None`. When `q` is provided and searchable fields exist, emits parameterized `WHERE (field1 ILIKE %s OR field2 ILIKE %s)` passing `f"%{q}%"` for each field.
  - Subcollections `list_<table>_by_<rel>` and `count_<table>_by_<rel>` scope queries with relation ID and search pattern.
  - Go store: `List<Entity>` and `Count<Entity>` accept `q string`. When `q != ""` and searchable fields exist, emits parameterized `WHERE (field1 ILIKE $1 OR field2 ILIKE $1)` with argument `"%"+q+"%"`.
  - Subcollections `List<Entity>By<Rel>` and `Count<Entity>By<Rel>` accept `q string` and scope queries with relation ID and search pattern.
  - Non-text entities gracefully omit search clauses with zero SQL errors.
- `backend_go.py`:
  - `_helpers_block`: added `parseSearch(r *http.Request) string` helper trimming `r.URL.Query().Get("q")`.
  - `_handlers_file_wired`: parsed `q := parseSearch(r)` on `Op.LIST` and `Op.LIST_BY` and passed `q` to store `Count...` and `List...` methods.
- `backend_python.py`:
  - Router generation: added `q: str | None = None` to `Op.LIST` and `Op.LIST_BY` endpoints and passed `q=q` to repository `count_...` and `list_...` functions.
- `nextjs.py`:
  - `_api_client_file`: updated `options.params` types in `list<Entities>`, `list<Entities>WithCount`, `list<Entities>By<Rel>`, and `list<Entities>By<Rel>WithCount` to include `q?: string`.
- `openapi.py`:
  - Added `q` query parameter descriptor to `Op.LIST` and `Op.LIST_BY` operations.
- Added `services/agent-engine/tests/test_search.py` with 16 unit tests covering Go store, Go handlers, Python repo, Python routers, Next.js client, OpenAPI 3.1 parameter declaration, and non-text entity handling.
- Updated existing assertions in `test_nextjs_api_client.py`, `test_sorting.py`, `test_pagination.py`, `test_total_count.py`, `test_route_wiring.py`, and `test_subcollection_wiring.py`.
- `task verify` — 491 tests pass (16 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-261.md.

## 2026-09-08 — R-260

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-260.md`.
- `openapi.py`:
  - Created `render_openapi(ir: ApplicationIR) -> dict[str, Any]` and `render_openapi_json(ir: ApplicationIR, indent: int = 2) -> str`.
  - Emitted OpenAPI 3.1.0 specification with `info` (name, description, version).
  - Emitted `components.schemas` converting all entities to JSON Schema properties with validation metadata (`maxLength`, `enum`, `minimum`, `maximum`, `required`), plus standard error schemas.
  - Emitted `components.securitySchemes` with `BearerAuth` (JWT).
  - Emitted `paths` mapping all endpoints with path parameters, query parameters (`limit`, `offset`, `sort`, `order` on LIST endpoints), request bodies, and responses with `X-Total-Count` header.
  - Mapped operation security requirements (`BearerAuth` + roles) based on `api.auth` and `api.required_roles`.
- `codegen/__init__.py`: exported `render_openapi` and `render_openapi_json`.
- `assembler.py`: emitted `contracts/openapi.json` in customer monorepo assembly and documented in root `README.md`.
- `backend_go.py`: emitted `openapi.json` at root of generated Go backend project.
- `backend_python.py`: emitted `openapi.json` at root of generated FastAPI backend project.
- Updated `test_console_snapshot.py` to expect `contracts/openapi.json` and `services/api/openapi.json` in showcase diff.
- Added `services/agent-engine/tests/test_openapi.py` with 14 unit tests covering OpenAPI 3.1 structure, schemas, validation rules, paths/parameters, auth/roles security, monorepo assembly, Go/FastAPI adapter emission, and determinism.
- `task verify` — 475 tests pass (14 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-260.md.

## 2026-09-08 — R-259

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-259.md`.
- `data_access.py`:
  - Python repository: added `count_{table}() -> int` (`SELECT COUNT(*) AS count FROM {TABLE}`) and `count_{table}_by_{relation}({relation}_id: str) -> int` (`SELECT COUNT(*) AS count FROM {TABLE} WHERE {relation}_id = %s`).
  - Go store: added `Count{pascal}(ctx context.Context, db *sql.DB) (int, error)` (`SELECT COUNT(*) FROM {table}`) and `Count{pascal}By{rel_pascal}(ctx context.Context, db *sql.DB, {relation}ID string) (int, error)` (`SELECT COUNT(*) FROM {table} WHERE {relation}_id = $1`).
- `backend_go.py`:
  - `_handlers_file_wired`: imported `"strconv"`. On `Op.LIST` and `Op.LIST_BY`, queries `total, err := store.Count...` prior to listing, and sets `w.Header().Set("X-Total-Count", strconv.Itoa(total))`.
  - `_main_file`: added `w.Header().Set("Access-Control-Expose-Headers", "X-Total-Count")` to `corsMiddleware`.
- `backend_python.py`:
  - `_router_file`: imported `Response` from `fastapi` when `uses_list` is true. Injected `response: Response` into `Op.LIST` and `Op.LIST_BY` handlers, queries `total = await {wiring.table}.count_...()`, and sets `response.headers["X-Total-Count"] = str(total)`.
  - `_main_file`: added `expose_headers=["X-Total-Count"]` to `CORSMiddleware`.
- `nextjs.py`:
  - `_api_client_file`: exported `PaginatedResult<T> { data: T; total: number }`.
  - Emitted `requestWithMeta<T>` helper extracting `X-Total-Count` from response headers.
  - Emitted `list<Entity>WithCount` and `list<Entity>sBy<Rel>WithCount` helpers returning `Promise<PaginatedResult<Entity[]>>`.
  - Preserved standard `list*` methods returning `Promise<Entity[]>` for backwards compatibility.
- Added `services/agent-engine/tests/test_total_count.py` with 15 unit tests covering Go store, Go handlers, Go CORS, Python repo, FastAPI routers, FastAPI CORS, and Next.js client integration.
- Updated FastAPI router signature assertions in `test_pagination.py` and `test_sorting.py`.
- `task verify` — 461 tests pass (15 new), 0 failures. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-259.md.

## 2026-09-08 — R-258

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-258.md`.
- `data_access.py`:
  - Python repository: declared `ALLOWED_SORT_FIELDS = [field.name for field in entity.fields]`; `list_<table>` and `list_<table>_by_<rel>` validate `sort` against whitelist (falling back to `"id"`) and `order` (falling back to `"ASC"`), emitting `ORDER BY {sort_col} {sort_dir} LIMIT %s OFFSET %s`.
  - Go store: `List<Entity>` and `List<Entity>By<Rel>` accept `limit, offset int, sort, order string`; emit switch statement mapping declared entity columns to whitelisted identifier (falling back to `"id"`) and case-insensitive check for `"desc"` (falling back to `"ASC"`), formatting `ORDER BY %s %s LIMIT $1 OFFSET $2`.
- `backend_go.py`:
  - `_handlers_shared_file`: emitted `parseSort(r *http.Request) (string, string)` helper extracting `sort` and `order`.
  - `_handlers_file_wired`: parsed `sort, order := parseSort(r)` on `Op.LIST` and `Op.LIST_BY` and passed them to store methods.
- `backend_python.py`:
  - `_router_file`: updated `Op.LIST` and `Op.LIST_BY` to declare `limit: int = 100, offset: int = 0, sort: str = "id", order: str = "asc"` and pass all parameters to data access repository functions.
- `nextjs.py`:
  - `_api_client_file`: updated `Op.LIST` and `Op.LIST_BY` client method signatures to type `params?: { limit?: number; offset?: number; sort?: string; order?: "asc" | "desc" }`.
- Added `services/agent-engine/tests/test_sorting.py` with 14 unit tests covering Go store, Go handlers, Python repos, Python routers, and Next.js client.
- Updated regression tests in `test_pagination.py`, `test_route_wiring.py`, `test_subcollection_wiring.py`, and `test_nextjs_api_client.py`.
- `task verify` — 446 tests pass (14 new), 0 failures. 0 network calls, 0 cloud model calls.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-258.md.

## 2026-09-08 — R-257

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-257.md`.
- `nextjs.py`: added `_slug_to_pascal` and `_api_client_file(ir: ApplicationIR)` emitting `apps/web/lib/api.ts`.
  - Emits `BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""`.
  - Emits `ApiOptions` (with `token?: string` for Bearer auth and `params?: Record<...>` for query strings).
  - Emits `ApiError` with HTTP status and structured payload.
  - Emits generic `request<T>(path, options, body)` handling headers, query params, JSON, errors, and 204.
  - Emits strongly-typed methods for all endpoints: `list<Entity>(options?: { params?: { limit?: number, offset?: number } })`, `get<Entity>(id)`, `create<Entity>(data)`, `update<Entity>(id, data)`, `delete<Entity>(id)`, `list<Entity>sBy<Rel>(parentId, options)`, and custom endpoint fallbacks.
  - Exports combined `api` object namespace.
  - Added `lib/api.ts` to `NextjsWebAdapter.generate` file list and added `NEXT_PUBLIC_API_URL` to `.env.example`.
- `backend_go.py`: added `corsMiddleware` in `_main_file` wrapping `mux` with `Access-Control-Allow-*` and `OPTIONS` 204 preflight; updated `.env.example` with `CORS_ALLOWED_ORIGIN=*`.
- `backend_python.py`: configured `CORSMiddleware` in `_main_file` with `allow_origins`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`; updated `.env.example`.
- Added `test_nextjs_api_client.py` with 9 tests; updated `test_nextjs_adapter.py`.
- `task verify` — 432 tests pass (9 new), 0 failures. `task lint`, `task security:quick`, `task env:check` pass.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, PROJECT_STATE.yaml, tasks/R-257.md.

## 2026-09-08 — R-256

- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-256.md`.
- `route_wiring.py`: extended `wire_endpoint` to map `method in ("PATCH", "PUT")` with trailing id parameter
  and matching `request_schema` to `Op.UPDATE`.
- `backend_go.py`: `Put<Entities><Id>` handler wired (decodes body -> `validateStruct` if entity has rules ->
  `store.Update<Entity>` -> 404 on nil / 200 on success).
- `backend_python.py`: `@router.put` route handler wired (validates payload -> `update_<table>` -> 404 on None / 200).
- Negative wiring: PUT without path param, with mismatched schema, etc. stays 501 scaffold.
- Rule-free entities emit no `validateStruct` call in Go PUT handler.
- Example IRs (`minimal-blog`, `rideshare-favourites`) unchanged.
- Added `test_put_update_handlers.py` with 14 new tests; all pass.
- `task verify` — 423 tests pass (14 new), 0 failures. `task security:quick`, `task env:check` pass.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, tasks/R-256.md.


- Founder requested to complete both tasks before committing or pushing.
- Recorded contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-255.md`.
- `backend_go.py`: `_handlers_shared_file` emits `parsePagination(r *http.Request) (int, int)` returning
  limit (default 100, parsed if >0) and offset (default 0, parsed if >=0) using `strconv.Atoi`;
  `_handlers_file_wired` calls `limit, offset := parsePagination(r)` for `Op.LIST` and `Op.LIST_BY`
  and passes them to `store.List<Entity>` and `store.List<Entity>By<Rel>`.
- `data_access.py`: Go `List<Entity>` and `List<Entity>By<Rel>` updated to accept `limit, offset int`
  and emit `LIMIT $1 OFFSET $2` and `LIMIT $2 OFFSET $3`.
- `backend_python.py`: `Op.LIST` and `Op.LIST_BY` route handlers updated to declare `limit: int = 100, offset: int = 0`
  query parameters and pass them to `list_<entity>(limit=limit, offset=offset)`.
- Added `test_pagination.py` with 11 new tests; updated existing assertions in `test_route_wiring.py`
  and `test_subcollection_wiring.py`.
- `task verify` — 409 tests pass (11 new), 0 failures. `task security:quick`, `task env:check` pass.
- Updated docs/CODEGEN.md, docs/PROGRESS.md, CHANGELOG.md, CURRENT_TASK.yaml, tasks/R-255.md.


- R-253 committed and pushed (99c2fae). Founder approved R-254: "go for the next task."
- Founder confirmed Tier 0 / Ollama stays active; Groq key added to .env for later.
- Recorded task contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-254.md` before code.
- `field_validation.py` `go_validate_file()`: replaced flat `"validation_failed"` with a
  `validationError struct {Field/Rule/Message}` and a new `validateStruct(w, v) bool` that
  iterates `validator.ValidationErrors`, builds per-field entries, and writes the structured JSON
  body `{"errors":[...]}` via `writeJSON`; returns `false` on error, `true` on success; added
  `"fmt"` import for `fmt.Sprintf` message construction.
- `backend_go.py`: updated both CREATE and UPDATE call-sites from the old two-line
  `if status, msg := validateStruct(m); msg != "" { http.Error(...) }` pattern to the single-line
  `if !validateStruct(w, m) { return }` guard.
- Updated existing R-252 tests (`test_go_validation_enforcement.py`) to assert the new signature
  and structured body instead of the old flat string.
- Updated existing R-253 tests (`test_patch_update_handlers.py`) to assert `validateStruct(w, m)`.
- `test_validation_error_bodies.py`: 24 new tests covering struct type, all 3 JSON keys
  (field/rule/message), "errors" wrapper, fmt.Sprintf, no "validation_failed", writeJSON usage,
  new bool signature, handler call-site pattern, ordering, rule-free gate, example IRs.
- FastAPI/Pydantic: no change needed — Pydantic already returns structured 422 errors by default.
- `task verify` — 398 tests pass (24 new), 0 failures. `task security:quick`, `task env:check` —
  pass. 0 local model calls, 0 cloud calls.
- Updated CHANGELOG, PROGRESS.md, CURRENT_TASK, PROJECT_STATE, HANDOFF, WORK_LOG, R-254.md.

## 2026-09-08 — R-253

- Read AGENTS.md, START_HERE.md, PROJECT_STATE.yaml, CURRENT_TASK.yaml, HANDOFF.md; confirmed
  main @ 08a149e, tree clean, 350 tests passing; R-252 done.
- Ran `task doctor` (all tools present), `task verify` (350 pass), `task ai:status`,
  `task ai:handoff` — all clean. Proposed R-253 candidates to founder.
- Founder direction: "do what is best — no static or half work." Selected PATCH/update handlers
  (Option B) as the missing CRUD verb with real enforced runtime behaviour.
- Recorded task contract in `.ai/CURRENT_TASK.yaml` and `.ai/tasks/R-253.md` before any code.
- `route_wiring.py`: added `Op.UPDATE`; `wire_endpoint` now maps `PATCH /entities/{id}` with
  matching `request_schema` → `Op.UPDATE` (one path param, last segment). Conservative: everything
  else stays 501.
- `data_access.py`: added `_go_update` helper → emits `Update<Entity>(ctx, db, id, m)` with
  parameterized `UPDATE … SET col=$i … WHERE id=$N RETURNING <col_list>`; returns `*models.<Entity>`
  or `nil` on `ErrNoRows`. Added `_python_update` helper → emits `update_<table>(id, data)` with
  parameterized `UPDATE … SET col=%s … WHERE id=%s RETURNING *`; `fetchone()` gives `None` on miss.
- `backend_go.py`: `_handlers_file_wired` handles `Op.UPDATE` — decode body → `validateStruct` (if
  entity has rules) → `store.Update<Entity>` → 404 on nil / 200 writeJSON. `uses_models` extended
  for UPDATE. `has_validation` gate extended to cover UPDATE + CREATE.
- `backend_python.py`: `_router_file` handles `Op.UPDATE` — emits `@router.patch` with `id_param +
  payload` → `update_<table>` → `HTTPException(404)` on `None`. `models_used` extended for UPDATE.
- `tests/test_patch_update_handlers.py`: 24 new tests covering Go store/handler/validation-ordering/
  negative-wiring and Python repo/router; example IR regression; all assertions pass.
- `task verify` — 374 tests pass (24 new), 0 failures. `task security:quick`, `task env:check` —
  pass. 0 local model calls, 0 cloud calls.
- Updated CHANGELOG, PROGRESS, CODEGEN, CURRENT_TASK, PROJECT_STATE, HANDOFF, WORK_LOG.
- Tracker row R-253 inserted at Phase_Roadmap!A9:M9; Done count = 42.

## 2026-09-06 — R-001

- Read `OmniStackAI_Implementation_Brief_v6.md` in full and applied the normative V6
  precedence rules.
- Created root `PROJECT_STATE.md` before source-code work.
- Inspected `Phase_Roadmap` and confirmed that its task data begins at R-010.
- Initialized Git and created `ai/R-001-monorepo-bootstrap`.
- Recorded the R-001 task contract and expected blast radius.
- Created every Section 74 directory as an implementation-free placeholder.
- Added portable agent rules, start/resume/handoff state, Taskfile commands, secret exclusions,
  CI/CODEOWNERS skeletons, and ADR-0001.
- Installed Go Task 3.53.1 and ran the canonical command interface.
- Corrected the tracked-file secret check so the permitted `.env.example` is excluded without
  weakening checks for real secret files.
- `task doctor`, `task bootstrap`, `task verify`, `task ai:status`, and `task ai:handoff` passed.
- Created implementation checkpoint `655f01fa0425e8df9022ce6bb1d2040f56b1cb73`.
- Reconstructed tracker row R-001 with founder approval, marked it Done, recorded evidence, and
  verified the workbook visually and for formula errors.

## 2026-09-06 — R-002

- Reconstructed the R-002 contract from the kickoff kit's canonical example with founder approval.
- Pinned `pgvector/pgvector:0.8.6-pg18-trixie` as the only local Compose service.
- Added loopback-only port publishing, ignored environment credentials, and a persistent named volume.
- Added transactional version 1 up/down migrations for pgvector and the migration ledger.
- Added deterministic `db:config`, `db:up`, `db:status`, `db:verify`, and `db:down` commands.
- Corrected the PostgreSQL 18 volume mount to its major-version-aware root after the live health gate
  exposed the upstream layout change.
- Verified a healthy live database, pgvector 0.8.6, migration version 1, and loopback-only binding.
- Ran `task verify` successfully and created implementation checkpoint
  `56bf4b0dea5486f8d6dcde0c7b1054249ebbb064`.

## 2026-09-06 — R-003

- Reconstructed R-003 from Brief Sections 79 and 84.1 with the founder's instruction to continue.
- Confirmed a 16 GB Apple Silicon Mac with Ollama 0.33.3 and two existing local models.
- Added environment-selected local model configuration and strict loopback endpoint validation.
- Added deterministic configuration, serve, status, discovery, pull, and inference commands.
- Kept static `task verify` independent of the running local model service.
- Verified non-loopback configuration rejection.
- Ran one live `qwen2.5-coder:14b` inference, generated 6 tokens, and made zero cloud calls.
- Created implementation checkpoint `822db27aa9c9e6ab836c28abba10f41dc27918d7`.

## 2026-09-06 — R-004

- Reconstructed R-004 as the smallest Go modular-monolith control-plane foundation permitted by
  the Stage 0 sequence; deferred Redis until an implemented workload proves it necessary.
- Used local `qwen2.5-coder:14b` for one bounded design review and made zero cloud calls.
- Added typed, fail-fast environment configuration and safe PostgreSQL URL construction.
- Added stable JSON `/healthz` liveness and bounded PostgreSQL-backed `/readyz` readiness without
  exposing raw database errors.
- Added structured logs, bounded HTTP timeouts, graceful SIGINT/SIGTERM shutdown, and a non-root
  multi-stage container image.
- Kept local Compose to exactly PostgreSQL and control-plane, both published only on loopback.
- Passed `task verify`, `go test -race ./...`, and live `task control-plane:verify`.
- Created implementation checkpoint `c44fd8d013e3ec1497ccb4ab55f1433df042aeb5`.

## 2026-09-06 — R-005

- Reconstructed R-005 from the brief's explicit provider-registry handoff example and provider
  boundary rules.
- Used local-only Balanced routing for the L2 task. Two bounded `qwen2.5-coder:14b` attempts returned
  no capturable review text; deterministic brief and repository evidence defined the implementation.
- Added immutable validated provider, model, capability, request, response, token usage, health,
  discovery, and streaming records.
- Added a runtime-checkable async `ModelProvider` protocol without vendor SDK types.
- Added a deterministic registry with platform-owned invalid, duplicate, and unknown-provider errors.
- Added Python 3.13 compile/policy commands, CI toolchain setup, and 13 standard-library unit tests.
- Preserved exactly the existing two Compose services and made zero cloud model calls.
- Created implementation checkpoint `afdc4ba9c14b231dece9533dbdd39e1e79e9ace3`.

## 2026-09-06 — R-006

- Reconstructed R-006 as the early local Ollama adapter required by the V6 MVP sequence.
- Used local-only Balanced routing: one `qwen3.5:9b` review call was inconclusive; no cloud call was made.
- Added a Python 3.13 standard-library native Ollama adapter for version health, explicitly profiled
  model discovery, non-stream chat generation, and NDJSON streaming.
- Enforced the approved loopback endpoint, disabled proxies, rejected redirects, bounded time,
  response sizes and concurrency, closed cancelled streams, and mapped failures to stable errors.
- Required an exact configured model digest before any capability can be marked verified and
  rejected tool-message requests until a separate evaluated tool-call contract exists.
- Added 15 adapter/configuration tests, bringing the agent-engine suite to 28 passing tests.
- Ran the live conformance command against `qwen2.5-coder:14b`: generation produced 4 tokens and
  streaming produced 4 events/4 tokens; cloud calls remained zero.
- Ran `task verify` successfully and created implementation checkpoint
  `8061ca3b129539ada4b0838d7d70c8acd3df1ea3`.

## 2026-09-06 — R-007

- Reconstructed R-007 as the Balanced Model Gateway router — the smallest next Stage 0/MVP dependency
  after the R-005 registry and R-006 adapter — from Brief Sections 18, 18.1, 18.2, 18.3, 84, 85, 91,
  and 92.
- Restored the declared `pnpm` (corepack, pinned `pnpm@11.19.0`) and `ripgrep` toolchains that had
  regressed from the environment; added no repository dependency. `task doctor` and `task verify`
  passed again on the R-006 baseline before any change.
- Added `ModelGateway` with a deterministic escalation ladder (L0 refused), Balanced routing (sub-L3
  to the local Ollama provider), L3/L4 escalation-required while cloud is unconfigured, a conservative
  context-budget guard, and explicit no-silent-cloud-fallback on local provider unavailability.
- Added `TaskComplexity`, `RoutingMode`, `RoutingTier`, `RoutingPolicy`, `RoutingTask`,
  `RoutingDecision`, a conservative token estimator, and three stable gateway errors. Standard-library
  only; no provider SDK, cloud call, service process, DB/Compose change, or new top-level folder.
- Added 14 offline gateway tests (42 agent-engine tests total). Routing is deterministic and needed
  zero model calls to implement or test; cloud calls remained zero.
- Ran `task verify`, `task agent-engine:lint/test`, `task security:quick`, `task env:check`, and the
  Compose scope check (exactly `postgres` and `control-plane`).
- Inserted tracker row R-007 at Phase_Roadmap row 9 by shifting rows 9..224 to 10..225 and extending
  the Dashboard, table, conditional-formatting, and data-validation ranges by one row; verified no
  ID was lost, formulas self-reference their rows, counts are correct (MVP total 112, Done 7), and
  the chart/styles/workbook parts stayed byte-identical.
- Created implementation checkpoint `9faacd23dc22c6773f9a51dc58087d557c0be391`.
- On founder instruction, added the opt-in live gateway runner (`live_gateway.py`) and
  `task agent-engine:gateway:run` to run the platform locally through the Balanced gateway, plus
  cloud-provider API-key placeholders in `.env.example` (names only) to prepare the R-008 decision.
- Live-ran the gateway on both installed models: L0 refused, L1/L2 routed to `ollama-local`, L3/L4
  refused; L2 generation and L1 stream succeeded on `qwen2.5-coder:14b` and `qwen3.5:9b`; cloud
  calls remained zero. Static `task verify` stayed network-independent and green.

## 2026-09-06 — R-008

- Reconstructed R-008 on founder instruction to configure every cloud provider (not just one),
  activated by API key, while continuing to run locally on Ollama until keys are added.
- Added standard-library HTTPS cloud adapters (no vendor SDK, no external dependency): one
  OpenAI-compatible adapter for OpenAI/OpenRouter/Groq, an Anthropic Messages adapter, and a Google
  Gemini generateContent adapter, each mapping to the vendor-neutral records with the R-006 HTTP
  safety pattern (bounded response, finite timeout, redirect rejection, stable errors).
- Kept API keys out of source/logs/records/repr: keys are read only from the environment and sent
  only as the provider auth header; a provider is registered only when its key is present.
- Added `build_gateway_from_env()` that always registers local Ollama and each key-present cloud
  provider and selects the L3/L4 tier from `OMNISTACKAI_CLOUD_PROVIDER` (default none); selecting a
  provider without its key is a clear configuration error. Refactored the live runner to use it.
- Added 19 offline tests (61 total) with injected fake HTTP openers; no cloud key set, so cloud
  calls stayed zero. Confirmed the live local run still works via the bootstrap.
- Evolved a stale R-005-era guard in `scripts/test.sh` to enforce the durable invariants (no SDK
  import, gateway/cloud/bootstrap files exist, cloud opt-in defaults to none) now that cloud adapters
  are sanctioned; added cloud key/model placeholders and shared budgets to `.env.example`.
- Inserted tracker row R-008 at Phase_Roadmap row 9 (shifted 9..225 to 10..226, ranges extended by
  one); verified no ID lost, formulas self-reference their rows, MVP total 113 / Done 8, chart/styles
  byte-identical, zip valid.
- Created implementation checkpoint `eeade72e84c7f1ebd71dfc8c0f7c2f4db0f79677`.

## 2026-09-06 — R-009

- Reconstructed R-009 as best-in-class usage and cost accounting (founder-selected) from Brief
  Sections 18.4, 23, 68, 84, 85, 90, 91, and 92.
- Added `accounting.py`: immutable metadata-only `UsageRecord` (no message content or secret), a
  `Decimal`-based `PriceBook` (exact and per-provider-wildcard lookup, local Ollama zero, unknown
  models unpriced, optional cached-input pricing) with an illustrative configurable default book,
  and a thread-safe `UsageLedger` producing overall and per-provider/model breakdowns, deterministic
  nearest-rank p50/p95 latency, unpriced-call count, and cost per successful call.
- Integrated an optional `recorder` into `ModelGateway`: exactly one record per dispatch for success
  and failure, written without altering the returned response or the raised error; threaded the
  ledger through `build_gateway_from_env` and printed a cost summary from the live runner.
- Added 13 offline accounting tests (74 total). Accounting is deterministic; zero model calls were
  needed to implement or verify. Live local run recorded 2 calls at $0.000000 with latency
  percentiles and a per-provider breakdown; cloud calls stayed zero.
- Inserted tracker row R-009 at Phase_Roadmap row 9 (shifted 9..226 to 10..227, ranges extended);
  verified no ID lost, MVP total 114 / Done 9, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `f2fc8654c6a5717e292adcdc2abb5da2fd7409c2`.

## 2026-09-06 — R-220

- Founder asked to complete both true per-provider streaming and a second required item, one by one;
  R-220 delivers streaming.
- Replaced the R-008 single-event cloud stream wrapper with real incremental Server-Sent-Events
  streaming: shared SSE transport in the cloud base (bounded lines/response, finite timeout, redirect
  rejection, stable errors, key never leaked) plus per-provider parsers — OpenAI-compatible delta
  chunks with usage in the final chunk, Anthropic message_start/content_block_delta/message_delta/
  message_stop, and Gemini streamGenerateContent SSE.
- Yielded ordered StreamEvent deltas plus a final event with measured usage; kept non-streaming
  generate unchanged. Added 5 offline SSE tests (78 total) with injected fake streaming responses; no
  cloud call was made.
- Found the workbook backlog already assigns R-010..R-219 (R-010 = Native iOS Agent). To avoid
  overwriting a planned row, new founder-requested model-fabric tasks take unique IDs after R-219;
  this task is R-220, inserted at Phase_Roadmap row 9 (rows 9..227 shifted to 10..228, ranges
  extended). Verified no ID lost, backlog R-010 intact, MVP total 115 / Done 10, chart/styles
  byte-identical, zip valid.
- Created implementation checkpoint `4e31841e730a6466da55843ff352f7144dd763e9`.

## 2026-09-06 — R-221

- Added explicit, allowlist-driven cross-provider fallback and per-provider circuit breaking to the
  Balanced gateway (founder-requested second item, part one of two).
- `RoutingPolicy` gained an optional ordered `fallback` chain; with none configured the gateway is
  byte-for-byte behaviourally unchanged (single provider). generate/stream now try the primary then
  each registered, in-budget, circuit-closed candidate.
- Fail-over is explicit (only along the chain) and only on retriable errors
  (unavailable/timeout/http); non-retriable errors raise immediately; streaming fails over only
  before the first event.
- Added `resilience.py` `CircuitBreaker`: opens after N consecutive failures, skips for a cooldown,
  half-opens, resets on success; injectable clock, thread-safe. Every attempt is still accounted.
- Added `AllProvidersFailedError` for an exhausted chain; a single-provider config still surfaces its
  own stable error. Refactored resolve() into `_resolve_tier` + `_build_decision` reused by both
  paths, keeping the existing resolve() behavior identical.
- Added 8 offline tests (86 total); deterministic, no cloud call. Confirmed the live local gateway
  still runs on Ollama.
- Inserted tracker row R-221 at Phase_Roadmap row 9 (rows 9..228 shifted to 10..229, ranges extended);
  no ID lost, backlog intact, MVP total 116 / Done 11, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `d0ee9f75b0d124fe60f1121b7f2a70d3b73040de`.

## 2026-09-06 — R-222

- Built the first platform console slice (founder-requested second item, part two of two) under
  apps/console-web.
- Added Python `overview.py` `platform_overview()` — a deterministic, metadata-only export of the
  model fabric (routing ladder, providers with active flags from env key presence, price book, usage
  summary), plus `PriceBook.entries()`; the snapshot never contains a key or secret (active is a
  boolean). 6 offline tests (92 total), including a no-secret / active-without-key assertion.
- Authored a full Next.js App-Router app, but this sandbox's network repeatedly timed out fetching
  Next's native SWC binary, so it cannot be installed/built here and a frozen install would break the
  offline task bootstrap. Pivoted to a dependency-free static console (index.html/styles.css/app.js)
  with the identical data contract and design; reverted the bootstrap change so the offline contract
  is unchanged. Next.js upgrade documented as the next step.
- Console uses safe DOM APIs (textContent only), a strict CSP meta tag, and same-origin snapshot fetch
  only. Added task console:snapshot and task console:serve; verified app.js via node --check and the
  served assets via HTTP (all 200; 6 providers / 5 price rows / 5 ladder steps).
- Inserted tracker row R-222 at Phase_Roadmap row 9 (rows 9..229 shifted to 10..230, ranges extended);
  no ID lost, backlog intact, MVP total 117 / Done 12, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `c07bbcb1b9b8c010c6d64e3a0e09ac0c855102c8`.

## 2026-09-06 — R-223

- Wired R-221 resilience into `build_gateway_from_env`: `OMNISTACKAI_FALLBACK_PROVIDERS` builds an
  ordered fallback chain from already-registered providers (`ollama` or a key-present cloud name);
  unknown or key-less names raise a clear `CloudProviderSelectionError`.
- Attached a `CircuitBreaker` (threshold/cooldown from env, safe defaults 3/30) only when a chain is
  configured, so single-provider behavior is byte-for-byte unchanged. `GatewayBootstrap` now exposes
  the chain provider ids and breaker settings.
- Extended the overview snapshot with a `resilience` block and rendered a Resilience panel in the
  console; added `.env.example` entries. No key/secret is ever included.
- Added 6 offline tests (98 total); deterministic, no cloud call. `task verify` green.
- Inserted tracker row R-223 at Phase_Roadmap row 9 (rows 9..230 shifted to 10..231, ranges
  extended); no ID lost, MVP total 118 / Done 13, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `9ec809149ab91ebaa13b88ff0a15ebd382d7a728`.

## 2026-09-06 — R-224 (deferred) and R-225

- R-224 (Next.js console upgrade): attempted the install three times (incl. standalone with a 10-min
  timeout) and once with Vite/Preact; this sandbox cannot fetch front-end bundler native binaries, so
  recorded R-224 as Deferred with a resume plan and committed no application code.
- Also showed the platform live: ran `task agent-engine:gateway:run` (local qwen routing/gen/stream +
  cost) and published the console UI as a private Artifact from the snapshot.
- R-225: began the actual product per the brief. Added the framework-neutral Application IR (Brief 9)
  under `omnistackai_agent_engine.application_ir`: immutable validated records (application, project
  strategy, roles, entities with fields/relations, APIs, screens, acceptance criteria), cross-reference
  validation, unique-id and enum checks, schema versioning, and lossless to_dict/from_dict with a
  version-rejection migration hook. Standard-library only; no codegen/agents yet.
- Added 17 offline IR tests (115 total). `task verify` green.
- Inserted tracker row R-225 (category Product) at Phase_Roadmap row 9 (rows 9..232 shifted to 10..233,
  ranges extended); no ID lost, MVP total 120 / Done 14, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `ad5e4ddf5918ddf3e4005c21a07c21601faf2ee6`.

## 2026-09-06 — R-226

- Added the code-generation boundary in `omnistackai_agent_engine.codegen`: `GeneratedFile` (safe
  relative POSIX path, bounded content) and `GeneratedProject` (immutable, path-unique,
  deterministically ordered, mergeable) — a customer project's source tree as a pure in-memory value,
  no disk writes.
- Added the `FrameworkAdapter` runtime-checkable contract (`target` + `generate(ir) -> GeneratedProject`),
  an `AdapterRegistry` with stable duplicate/unknown errors, and the `GenerationTarget` enum over MVP
  targets; adapters are selected only via the registry.
- Depends on `application_ir`; standard-library only; no code execution. 10 new offline tests
  (125 total). `task verify` green.
- Inserted tracker row R-226 (Product) at Phase_Roadmap row 9 (rows 9..233 shifted to 10..234, ranges
  extended); no ID lost, MVP total 121 / Done 15, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `f27bf416e99423d281e1c4e6f3eabc363848f95f`.

## 2026-09-06 — R-227

- Implemented the first framework code adapter: `NextjsWebAdapter` turns an Application IR into a real
  Next.js App Router TypeScript project as a GeneratedProject — entities to TS interfaces, IR APIs to
  App Router route handlers ({param}->[param], one file per route dir, a handler per method), screens
  to pages, an overview page, and config (package.json/tsconfig/next.config with security headers/
  README/.gitignore/.env.example placeholders).
- Extended the GeneratedFile path validator to allow framework route filename chars ([]()@+) while
  still rejecting absolute paths, '..', backslashes, control chars.
- Pure/deterministic; nothing installed/built/run/written to disk. The demo IR emits a 13-file
  Next.js project. 9 new offline tests (134 total); `task verify` green.
- Inserted tracker row R-227 (Product) at Phase_Roadmap row 9 (rows 9..234 -> 10..235, ranges
  extended); no ID lost, MVP total 122 / Done 16, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `1a4f8a9b8cc2ca59be32142bb6c16992cb4dbd40`.

## 2026-09-06 — R-228 (first builder slice complete)

- Added `omnistackai_agent_engine.git_service`: `materialize_project` (writes a GeneratedProject under
  a target dir, refuses path escapes and non-empty targets, sets exec bits) and `create_repository`
  (git init + stage + one commit with the customer identity via explicit env, no global git config,
  returns the commit SHA). Writes only inside the caller's target; offline; local git only.
- 6 new offline temp-dir tests (140 total). Verified the full slice end-to-end: demo IR -> 13-file
  Next.js app (NextjsWebAdapter) -> a real one-commit customer-owned Git repo. `task verify` green.
- Inserted tracker row R-228 (Product) at Phase_Roadmap row 9 (rows 9..235 -> 10..236, ranges
  extended); no ID lost, MVP total 123 / Done 17, chart/styles byte-identical, zip valid.
- Created implementation checkpoint `28801ef396f7ead743a1d0cdc68657de23cefe1a`.

## 2026-09-06 — repo consolidation + R-229

- Founder merged all work into `main` (fast-forward from the R-001 bootstrap; 34 commits) and set
  `main` as the GitHub default; deleted all per-task ai/* branches (remote + local). Remote now has
  only `main`. Added docs/RESUME_PROMPT.md. Going forward, work is committed directly to `main`.
- R-229: added the Python (FastAPI) backend adapter (PythonBackendAdapter, target backend-python):
  entities -> Pydantic models, IR APIs -> FastAPI routers grouped by resource with typed path params
  and 501 scaffolds, app/main.py with routers + health, config, requirements, README/.gitignore/
  .env.example. Registered via AdapterRegistry. Pure/offline; no install/build/disk.
- 7 new offline tests (147 total). Proven multi-target: one IR -> 12-file Next.js web + 11-file FastAPI
  backend. `task verify` green. Tracker row R-229 (Product) inserted at row 9; MVP total 124 / Done 18.
- Implementation checkpoint `04f1e6ad03ff52522efda81845ea3ee73e736a7d`.

## 2026-09-06 — R-230

- Added the Go backend adapter (GoBackendAdapter, target backend-go): entities -> Go structs (json
  tags, optional pointers), IR APIs -> Go 1.22 method+pattern routes grouped by resource with
  r.PathValue params and 501 scaffolds, main.go with routes + /healthz + ListenAndServe, go.mod
  (go 1.22), README/.gitignore/.env.example. Generated Go and platform side are standard-library only.
- Registered via AdapterRegistry. 7 new offline tests (154 total). Proven tri-target: one IR ->
  12-file Next.js + 11-file FastAPI + 8-file Go service. `task verify` green.
- Committed directly to main (only branch). Tracker row R-230 (Product) inserted at row 9; MVP total
  125 / Done 19. Implementation checkpoint `e2515a8f1b0314ec287a02cdaf25e72a17b9da3f`.

## 2026-09-06 — R-224 (deferred)

- Attempted the Next.js console upgrade. `pnpm install` for next@15.5.4 timed out fetching the native
  SWC binary (@next/swc-darwin-arm64) three times, including a standalone install under
  apps/console-web/nextjs/ with a 10-minute fetch timeout and increased retries.
- Per "record real command evidence — never claim unexecuted tests," recorded R-224 as Deferred with a
  resume plan; committed no application code and removed the scaffold (working tree clean). The R-222
  static console remains the working slice.
- Recorded tracker row R-224 at Phase_Roadmap row 9 with status Deferred (completion 0); rows
  contiguous, ranges extended, no ID lost; MVP total 119, Done 13, Deferred 1.

## 2026-09-07 — R-234

- Added a single `OMNISTACKAI_TIER` switch (0/1 local, 2 cloud). `runtime/tier.py` resolves the runtime
  and deploy providers from the tier + explicit selectors: tier 0/1 force local runtime and no deploy;
  tier 2 permits keyed cloud selections. `resolve_platform()` returns the active providers;
  `platform_status()`/`format_status()` summarize tier, selection, and which keys are present.
- Added `runtime/drivers.py`: `CloudDeployProvider` (vercel/netlify/render/fly) emits a `DeployPlan` of
  the provider's official-CLI commands; `CloudSandboxProvider` (e2b/daytona/fly-machines) emits a
  `PreviewPlan` reusing the target's run commands. The key is read from env at run time and NEVER placed
  in a command or logged. `run_deploy(plan)` executes a plan opt-in (never run by verify).
- `bootstrap.py` gained an optional `selection` override; new exports in `runtime/__init__.py`.
  `task platform:status` (scripts/agent-engine.sh + Taskfile) prints the active tier and key presence;
  `.env.example` gained `OMNISTACKAI_TIER=0`; `docs/RUNTIME.md` documents the knob + drivers.
- 13 new stdlib offline tests (194 total): tier resolution, per-provider driver plans, no-key-in-plan
  across all providers, activation/selection errors, and the status summary. `task verify`,
  `task security:quick`, `task env:check` all pass; `task platform:status` demoed tier 0 and tier 2.
- Committed directly to main (only branch). Tracker row R-234 (Runtime) inserted at row 9; MVP total
  129 / Done 23. Implementation checkpoint `dcb7d2d`. 0 local / 0 cloud model calls; nothing run/deployed.

## 2026-09-07 — R-235

- Added the verifiable-engineering verify-plan layer (`omnistackai_agent_engine.verify`): `plans.py`
  (`VerifyStepKind` install/typecheck/lint/test/build, `VerifyStep`, `VerifyPlan` — validated,
  ladder-ordered, `gates()`, reusing the vetted `Command` primitive from runtime.contracts); `gates.py`
  (the per-target recipe table, `verify_plan`, `verify_plans_for_ir`, `run_verify`, `VerifyReport`).
- Per-target ladders: nextjs-web/nextjs-admin (pnpm install → tsc --noEmit → lint → build);
  backend-python (pip install → compileall app → pytest); backend-go (go vet → go test → go build).
  Each step classified by gate kind; commands control-free/secret-free by construction.
- Mapped one Application IR to the verify plans for its assembled monorepo apps via a new additive,
  behavior-preserving `assembled_targets(ir)` in the assembler (`assemble_project` refactored to share
  the `_plan_assembly` layout decision; output byte-identical, existing tests green).
- `run_verify(plan)` is the only executor — opt-in, fail-fast, returns a `VerifyReport` (per-step
  status + return code); never run by tests or `task verify`. Added `task agent-engine:verify-plan`.
- Docs: `docs/VERIFY.md`. 9 new stdlib offline tests (203 total): per-target plans, ladder order, gate
  classification, unknown-target error, IR→plans mapping over the rideshare + blog fixtures, plan
  safety. `task verify`, `task security:quick`, `task env:check` all pass; verify-plan demoed.
- Committed directly to main (only branch). Tracker row R-235 (Verify) inserted at row 9; MVP total
  130 / Done 24. Implementation checkpoint `cb74d0c`. 0 local / 0 cloud model calls; nothing installed/built/run.

## 2026-09-07 — R-236

- Expanded the cloud model fabric (founder request, with Dyad screenshots for reference). Added
  first-class OpenAI-compatible `CloudProviderSpec` entries for DeepSeek, xAI (Grok), Mistral, Together,
  and Fireworks alongside the existing OpenAI/Anthropic/Google/OpenRouter/Groq — all reuse
  `OpenAICompatibleProvider`, no new adapter code.
- Added a generic env-driven custom-provider path: `custom_provider_specs_from_env` reads
  `OMNISTACKAI_CUSTOM_PROVIDERS` + per-id `OMNISTACKAI_CUSTOM_<ID>_{BASE_URL,MODEL,API_KEY}` and builds
  a first-class provider with no code change; validates the id, requires an HTTPS base URL + model, and
  rejects built-in collisions. `resolve_provider_specs()` = built-ins ∪ custom.
- Made the catalog spec-driven end to end: `bootstrap.py` and `overview.py` iterate
  `resolve_provider_specs()`, so custom + new built-in providers are registered (key-activated),
  selectable as the L3/L4 cloud tier or a fallback, and listed in the metadata-only overview with
  `active` = key presence only. `accounting.py` gained illustrative default prices for the priced new
  providers (openrouter/custom stay unpriced).
- `.env.example`: new keys + model overrides + a documented custom-provider template; updated the
  `OMNISTACKAI_CLOUD_PROVIDER` allowed list. `docs/MODEL_PROVIDER.md`: R-236 catalog + custom + local
  Ollama section. Keys stay env-only — never logged, stored, returned, or placed in the overview.
- 14 new stdlib offline tests (217 total): new specs, adapter dispatch shape (key only in the auth
  header, never the URL), custom-spec parse + 4 error cases, spec merge, bootstrap registration/
  selection/fallback for built-in and custom, overview/no-key-leak, and pricing. Updated `test_overview`
  to derive the expected catalog from the spec table. `task verify` + `security:quick` + `env:check`
  pass; `platform_overview` demoed a 12-provider catalog including custom `myco`.
- Committed directly to main (only branch). Tracker row R-236 (Model Fabric) inserted at row 9; MVP
  total 131 / Done 25. Implementation checkpoint `e6326bf`. 0 local / 0 cloud model calls; no network.

## 2026-09-07 — R-237

- Added the "edit an existing app" motion — the builder step after generate + verify. New
  `omnistackai_agent_engine.edit` package: `diff.py` (`ChangeKind`, `FileChange`, `ProjectDiff`,
  `diff_projects`, `plan_edit`) and `apply.py` (`ApplyReport`, `apply_diff`, `commit_edit`).
- `diff_projects(old, new)` classifies every path as added/modified/deleted/unchanged (modified on
  content OR executable change); `plan_edit(old_ir, new_ir)` assembles both IRs via the assembler and
  diffs them, so an IR change becomes exactly the set of files to rewrite.
- `apply_diff(diff, target_dir)` writes added/modified and removes deleted files strictly inside the
  target (path escapes refused like `materialize_project`; emptied dirs pruned, never past the root),
  returns an `ApplyReport`, and leaves the directory equal to the new project. `commit_edit` applies +
  commits one commit as the customer identity via a new additive `git_service.commit_all` (git add -A
  + commit); previous history is preserved.
- 9 new stdlib offline tests (226 total): diff classification + empty diff + executable-flag change,
  plan_edit no-op and description-change (README.md modified, nothing added/deleted), apply round-trip
  (old tree -> new), path-safety refusal (`..` + missing target), and commit_edit two-commit history.
  Tests use tempdirs and the local git CLI (same pattern as the R-228 git-service tests).
- `git_service.create_repository`/`materialize_project` unchanged (additive `commit_all` only). No
  network call, no code execution, no write outside the target. `docs/EDIT_LOOP.md` added.
- Committed directly to main (only branch). Tracker row R-237 (Builder) inserted at row 9; MVP total
  132 / Done 26. Implementation checkpoint `a0a494a`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-238

- Gave the generated backend a real persistence layer. New `codegen/schema_sql.py`:
  `render_postgres_schema(ir)` renders deterministic PostgreSQL DDL from the IR entities + relations —
  one `CREATE TABLE` per entity (snake_case name), columns typed from `FieldType` (STRING/TEXT->TEXT,
  INT->BIGINT, FLOAT->DOUBLE PRECISION, BOOL->BOOLEAN, DATETIME->TIMESTAMPTZ, UUID->UUID, JSON->JSONB),
  `NOT NULL` for required fields, a UUID primary key (the entity's own `id` field if present, else a
  surrogate `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`), `<name>_id UUID REFERENCES <target>(id)`
  for many_to_one/one_to_one relations, and one deterministic join table per many_to_many pair.
- Wired both backend adapters (FastAPI and Go) to emit `migrations/0001_init.sql` exactly when the IR
  has entities and `database_strategy is DatabaseStrategy.POSTGRES` — no previously emitted file
  changes. Output is byte-stable, so the R-237 edit loop diffs the migration when the IR entities
  change. Exported `render_postgres_schema` from the codegen package.
- 11 new stdlib offline tests (237 total): type map + required->NOT NULL, surrogate vs declared PK,
  many_to_one FK column, single many_to_many join table with composite PK, determinism, the
  postgres/entities gate, and adapter emission (python + go emit; OTHER db and no-entities do not).
  No existing adapter/assembler test broke. `task verify` + `security:quick` + `env:check` pass.
- Nothing connects to or runs a database; no network. `docs/CODEGEN.md` documents the schema section.
- Committed directly to main (only branch). Tracker row R-238 (Builder) inserted at row 9; MVP total
  133 / Done 27. Implementation checkpoint `c6a4c6e`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-239

- Gave the generated backends a real data-access layer over the R-238 schema. New
  `codegen/data_access.py`: `python_data_access_files(ir, slug)` emits `app/db.py` (an async psycopg
  connection helper reading DATABASE_URL, dict rows) + `app/repositories/<entity>.py` per entity with
  `list/get/create/delete`; `go_data_access_files(ir, slug)` emits `internal/store/store.go` (a
  database/sql opener via the pgx driver) + `internal/store/<entity>.go` per entity with
  `List/Get/Create/Delete` scanning into the generated `models.<Entity>` structs.
- Every query value is parameterized (`%s` for psycopg, `$N` for pgx); only fixed IR-derived table/
  column identifiers appear inline (no value interpolation). An id-only entity creates via
  `DEFAULT VALUES`. `schema_sql` gained a public `table_name`.
- Wired both backends to append the data-access files and the DB dependency (psycopg in
  requirements.txt / pgx require in go.mod) exactly when `ir.entities and database_strategy is POSTGRES`
  — same gate as the migration; no previously emitted file (other than requirements.txt / go.mod)
  changed. The R-237 edit loop diffs the repositories when entities change.
- 7 new stdlib offline tests (244 total): python emission + valid-Python parse + parameterization, go
  emission + module import path + struct scan, gating (no db / no entities), id-only DEFAULT VALUES, and
  determinism. No existing test broke. `task verify` + `security:quick` + `env:check` pass.
- Nothing connects to or queries a database; no network. `docs/CODEGEN.md` + `docs/PROGRESS.md` updated.
- Committed directly to main (only branch). Tracker row R-239 (Builder) inserted at row 9; MVP total
  134 / Done 28. Implementation checkpoint `f6792fa`. 0 local / 0 cloud model calls.

## 2026-09-07 — R-240

- Wired the generated backends' HTTP handlers to the R-239 repository layer for the unambiguous CRUD
  shapes. New `codegen/route_wiring.py`: `wire_endpoint(api, repo_entities)` -> LIST/GET/CREATE/DELETE
  from method + path shape (entity from `response_schema` else `request_schema`); anything ambiguous
  (sub-collections, multi-param, custom, POST without a request_schema, unknown entity) returns None and
  stays a labelled 501 scaffold — so the platform never emits plausible-but-wrong behaviour.
- Python (`backend_python.py`): `_router_file` now takes `repo_entities`, imports the used
  repositories/models, and emits wired bodies — list -> `await <t>.list_<t>()`, get -> 404-aware, create
  -> `await <t>.create_<t>(payload.model_dump())` with a Pydantic body, delete -> 404-aware; unwired
  keep `raise HTTPException(status_code=501, ...)`.
- Go (`backend_go.py`): handlers became methods on a `Handlers` struct holding `*sql.DB`; added
  `internal/handlers/handlers.go` (struct + `New` + `writeJSON`); `_main_file` gained a `has_db` branch
  that opens `store.Open()`, builds `handlers.New(db)`, and registers `h.<Handler>`; wired methods call
  the `store` and decode `models.<Entity>` for create. Non-DB Go backends keep the free-function
  scaffolds unchanged (README stack note switches to pgx only when a DB is present).
- Gated on entities + `database_strategy=postgres`; deterministic and byte-stable; nothing runs. Updated
  `test_backend_go_adapter` assertions free-function -> method form (that test uses rideshare, has DB).
- 12 new stdlib offline tests (256 total) in `test_route_wiring.py`: the wiring map + its None cases,
  Python wired router (valid Python via ast) + ambiguous-stays-501, Go shared handlers + DB wiring +
  list-calls-store, and a non-DB backend left unchanged. `task verify` + `security:quick` + `env:check`
  pass. `docs/CODEGEN.md` documents the wiring table; `docs/PROGRESS.md` refreshed.
- Committed directly to main (only branch). Tracker row R-240 (Builder) inserted at row 9; MVP total
  135 / Done 29. Implementation checkpoint `013dfc4`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-241

- Made the IR's per-endpoint `auth` flag real (it was previously only a comment). New
  `codegen/auth_guard.py`: `needs_auth(ir)`, `python_auth_file(ir)`, `go_auth_file(ir)`. Every
  `auth=true` endpoint now enforces a guard that rejects a request with no `Authorization: Bearer`
  credential (HTTP 401) before the handler runs.
- Python (`backend_python.py`): emits `app/auth.py` with a `require_auth` FastAPI dependency; `_router_file`
  adds `Depends`/`require_auth` imports and `dependencies=[Depends(require_auth)]` on `auth=true` routes;
  public routes unchanged. Go (`backend_go.py`): emits `internal/handlers/auth.go` with a
  `RequireAuth(next)` middleware; `_main_file` wraps exactly the `auth=true` registrations with
  `handlers.RequireAuth(...)`. Works for both DB and non-DB backends.
- IR roles surfaced as a generated constant (Python `ROLES` tuple, Go `Roles` slice, from `role.id`).
  The guard only requires a credential; token verification (signature/expiry/roles) is a documented
  TODO — no secret fabricated, no verification faked.
- Gated on `needs_auth(ir)`; deterministic and byte-stable; nothing runs. Updated two existing adapter
  tests (Python decorator substring, Go registration substring) to the guarded form.
- 9 new stdlib offline tests (265 total) in `test_auth_guard.py`: needs_auth true/false, Python
  auth module + per-route dependency (auth vs public) + no-module-when-all-public, Go middleware + roles
  + main wraps only auth endpoints + no-file-when-all-public, and determinism. `task verify` +
  `security:quick` + `env:check` pass. `docs/CODEGEN.md` documents the guard; `docs/PROGRESS.md` refreshed.
- Committed directly to main (only branch). Tracker row R-241 (Builder) inserted at row 9; MVP total
  136 / Done 30. Implementation checkpoint `4db716b`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-242

- Upgraded the R-241 auth guard from a bearer-presence check to real JWT verification. `auth_guard.py`:
  the generated guard decodes and verifies a JWT (HS256) using `JWT_SECRET` read from the environment —
  401 on a missing/invalid/expired token, 500 when the secret is unset — and never hard-codes or
  defaults the secret.
- Python (`python_auth_file`): `app/auth.py` imports PyJWT, `require_auth` calls
  `jwt.decode(token, _secret(), algorithms=["HS256"])` and returns the verified claims; `_secret()`
  reads `JWT_SECRET` from `os.environ`. `backend_python.py` adds `PyJWT==2.9.0` to `requirements.txt`
  and an empty `JWT_SECRET` to `.env.example` when the IR needs auth.
- Go (`go_auth_file`): `internal/handlers/auth.go` imports `github.com/golang-jwt/jwt/v5`; `RequireAuth`
  reads `os.Getenv("JWT_SECRET")` (500 when empty) and `jwt.Parse`s the token with an HMAC-only keyfunc
  (rejecting non-HMAC). `backend_go.py` appends the golang-jwt `require` to `go.mod` and `JWT_SECRET=` to
  `.env.example` when the IR needs auth.
- Platform code stays standard-library only — the JWT dependency lives only in the generated project.
  IR roles constant retained for future per-endpoint authorization (needs an IR field). Nothing signed
  or verified at generation time; nothing runs; no network.
- 3 new stdlib offline tests (268 total): Python JWT verification + PyJWT/JWT_SECRET additions +
  no-fabricated-secret; Go JWT verification + golang-jwt/JWT_SECRET additions. Existing R-241 auth tests
  still pass. `task verify` + `security:quick` + `env:check` pass. `docs/CODEGEN.md` + `docs/PROGRESS.md`
  refreshed.
- Committed directly to main (only branch). Tracker row R-242 (Builder) inserted at row 9; MVP total
  137 / Done 31. Implementation checkpoint `e0d8af3`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-243

- Added per-endpoint role enforcement on top of the R-242 JWT auth — the first additive change to the
  IR itself. `ir.py`: `ApiEndpoint` gains `required_roles: tuple[str, ...] = ()` (validated with
  `_str_tuple`; a non-empty value requires `auth=true`), added to `to_dict`/`from_dict`. `validate.py`:
  each required role must be a declared `Role` (ERROR `unknown_role_reference` otherwise). `normalize_ir`
  unchanged (it reuses the ApiEndpoint objects). Default `()` → existing IRs unaffected, schema version
  unchanged.
- `auth_guard.py`: Python `require_roles(*required)` dependency factory (verify via `require_auth`, then
  require the `roles` claim to intersect `required`, else 403). Go refactored to a shared `verifyToken`
  (returns `jwt.MapClaims`) plus `RequireAuth`, `RequireRoles(next, required...)`, and `hasAnyRole`
  (403 when the claim has no required role).
- `backend_python._router_file`: role-gated routes declare `dependencies=[Depends(require_roles("..."))]`
  and import only the auth names they use; `backend_go._main_file`: role-gated endpoints register as
  `handlers.RequireRoles(target, "...")`. Endpoints without roles keep `require_auth`/`RequireAuth`.
- 6 new stdlib offline tests (274 total) in `test_role_enforcement.py`: IR required_roles serialize +
  auth-implication (`InvalidIRError`) + unknown-role `validate_ir` error + known-role clean; Python
  route uses `require_roles` (valid Python) with a 403 guard; Go `main` uses `RequireRoles` and `auth.go`
  has `RequireRoles`/`StatusForbidden`. Updated the R-242 Go assertion (`jwt.Parse` → `jwt.ParseWithClaims`).
  `task verify` + `security:quick` + `env:check` pass. `docs/APPLICATION_IR.md` + `docs/CODEGEN.md` +
  `docs/PROGRESS.md` refreshed.
- Committed directly to main (only branch). Tracker row R-243 (Builder) inserted at row 9; MVP total
  138 / Done 32. Implementation checkpoint `1faea2c`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-244

- Wired the sub-collection GET pattern `/<parents>/{parentId}/<children>` to a parent-scoped list,
  clearing the main class of remaining 501 stubs. `route_wiring.py`: added `Op.LIST_BY`, a `relation`
  field on `Wiring`, an `fk_relations(ir)` helper, and an `fk_by_entity` argument to `wire_endpoint`.
  A GET whose last segment is a collection (not a param) with exactly one path param wires to LIST_BY
  only when the child entity (response_schema) has exactly one many_to_one/one_to_one relation;
  otherwise it stays a labelled 501.
- `data_access.py`: emit a filtered list per FK relation — Python `list_<table>_by_<rel>(<rel>_id)`
  (`WHERE <rel>_id = %s`) and Go `List<Entity>By<Rel>(ctx, db, <rel>ID, limit)` (`WHERE <rel>_id = $1`).
  The value is parameterized; the FK column is a fixed IR-derived identifier.
- `backend_python._router_file` and `backend_go._handlers_file_wired` gained an `fk_by_entity` arg
  (passed from `generate` when has_db) and a LIST_BY branch: Python
  `await <table>.list_<table>_by_<rel>(<param>)`; Go
  `store.List<Entity>By<Rel>(r.Context(), h.DB, r.PathValue("<param>"), 100)`.
- Demo (minimal-blog): `GET /posts/{postId}/comments` now returns `comment.list_comment_by_post(postId)`
  (Py) / `store.ListCommentByPost(...)` (Go). Repointed the R-240 `test_ambiguous_endpoint_stays_501`
  to rideshare's `POST /favourites/drivers/{driverId}` (no request_schema -> still 501).
- 11 new stdlib offline tests (285 total) in `test_subcollection_wiring.py`: LIST_BY mapping + None
  cases (no fk map, multiple FK, get-by-id wins), fk_relations helper, filtered-repository emission
  (Py/Go), router/handler wiring, and value-parameterization. `task verify` + `security:quick` +
  `env:check` pass. `docs/CODEGEN.md` + `docs/PROGRESS.md` refreshed. Seed data deferred (no IR values).
- Committed directly to main (only branch). Tracker row R-244 (Builder) inserted at row 9; MVP total
  139 / Done 33. Implementation checkpoint `b886d72`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-245

- Added the combined project-plan surface. New `omnistackai_agent_engine.projectplan`: `AppPlan`,
  `ProjectPlan`, `build_project_plan(ir, *, deploy=None)`. It composes existing builders only —
  `codegen.assembled_targets` (app layout), `runtime.LocalRuntimeProvider.preview_plan` (guarded by
  `.supports`), `verify.verify_plan` (guarded by `verify.supported_targets`), and an optional
  `DeploymentProvider.deploy_plan` — into one per-app view.
- `ProjectPlan.to_dict()` is JSON-serializable and secret-free (preview url + command strings, verify
  gate kinds + step commands, deploy provider id + step commands); `render()` is a readable multi-app
  summary. A deploy plan is included only when a key-activated provider is passed in.
- CLI: `plan-show` in `scripts/agent-engine.sh` + `task plan:show -- <example>`. Demoed
  rideshare-favourites: apps/web (nextjs-web, preview :3000, gates install/typecheck/lint/build) and
  services/api (backend-go, preview :8080, gates lint/test/build). `docs/RUNTIME.md` documents it.
- 6 new stdlib offline tests (291 total) in `test_projectplan.py`: one AppPlan per assembled app,
  preview+verify present with no deploy by default, render() lists each app, deploy opt-in via
  deploy_driver("vercel"), to_dict JSON-serializable + no key value (fake VERCEL_TOKEN), determinism.
  `task verify` + `security:quick` + `env:check` pass.
- Pure/data-only — nothing installed, run, verified, or deployed; no key value included. Composes
  existing builders, so no runtime/verify/codegen behavior changed.
- Committed directly to main (only branch). Tracker row R-245 (Runtime) inserted at row 9; MVP total
  140 / Done 34. Implementation checkpoint `891144d`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-07 — R-246

- Added hunk-level edit diffs + rename detection on top of the R-237 file-level ProjectDiff. New
  `edit/patch.py`: `DiffKind`, `FileDiff`, `diff_report(old, new)`, `unified_patch(old, new)` — using
  standard-library `difflib.unified_diff`.
- `diff_report` classifies each path as added/modified/deleted/renamed and attaches a git-style unified
  (hunk) diff for content changes. Rename detection pairs a deleted path with an added path of identical
  content (greedy, sorted for determinism) and reports a single RENAMED record (old_path -> path)
  instead of delete+add. Records are deterministically ordered (kind, then path).
- `unified_patch` concatenates the reports into one byte-stable git-style patch string, with
  `rename from`/`rename to` headers for renames — so an edit reads as a focused review-ready patch.
- Additive only: `diff_projects` / `apply_diff` / `plan_edit` are unchanged; exported the new names from
  `edit/__init__.py`. Pure/deterministic — no disk write, no run, no network.
- 6 new stdlib offline tests (297 total) in `test_edit_patch.py`: modified-file unified hunk (context +
  -/+ lines), exact-content rename as one record + rename header, one-sided add/delete, empty report
  for identical projects, and byte-stable determinism. `task verify` + `security:quick` + `env:check`
  pass. `docs/EDIT_LOOP.md` + `docs/PROGRESS.md` refreshed (also fixed stale test-count/% notes).
- Committed directly to main (only branch). Tracker row R-246 (Builder) inserted at row 9; MVP total
  141 / Done 35. Implementation checkpoint `eebab68`. 0 local / 0 cloud model calls; nothing executed.

## 2026-09-08 — R-247

- Added `console_snapshot.platform_console_snapshot()`, a metadata-only composition of accepted public
  contracts: the existing model overview, the R-245 ProjectPlan for `rideshare-favourites`, and the
  R-246 diff report/unified patch for an actual old/new `minimal-blog` IR assembly.
- The builder proof exposes two generated apps (`apps/web`, `services/api`) with preview URLs and
  verification gate/command ladders; deploy remains absent by default. The edit preview contains five
  genuinely modified generated paths and a bounded 1,661-character hunk-level patch.
- Upgraded the dependency-free static console with responsive plan cards, gate badges, changed-file
  metadata, and a scrollable code patch. All content is assigned with `textContent`; the browser makes
  only the existing same-origin snapshot fetch under the strict CSP.
- 5 new offline stdlib tests (302 total) cover plan/patch shape, deterministic JSON serialization,
  existing model-overview preservation, and secret exclusion. `node --check`, repeated snapshot
  SHA-256, `task verify`, `task security:quick`, and `task env:check` pass. Live local visual review
  confirmed the builder proof and model dashboard render without a page error state.
- Implementation checkpoint `6a82056`. Tracker row R-247 inserted at row 9; 247 unique IDs, MVP total
  142 / Done 36. One bounded local `qwen2.5-coder:14b` review; 0 cloud calls. No generated app was
  installed/run/verified/deployed; no DB connection, external request, service, dependency, or infra.

## 2026-09-08 — R-248

- Added honest seed data from explicit Application IR fixtures (the deferred seed gap, done the no-
  fabrication way). `ir.py`: new `Fixture` record (entity + rows of column->JSON value) with a
  `_check_fixture_value` helper (allow JSON scalars/containers; reject control chars in strings); added
  `fixtures` to `ApplicationIR` (before schema_version) and wired the validation loop, `to_dict`, and
  `from_dict`. Exported `Fixture`. Additive field, empty default, no schema-version bump.
- `validate.py`: fixture cross-references — ERROR `unknown_fixture_entity` / `unknown_fixture_column`
  (a row column must be a declared field or a `<relation>_id` FK), WARNING `fixture_missing_required`
  (required column, other than id, absent from a row — advisory, has_errors stays false). CRITICAL:
  added `fixtures=` to `normalize_ir` so it isn't dropped.
- New `codegen/seed_sql.py`: `render_postgres_seed(ir)` emits `INSERT INTO <table> (<cols sorted>)
  VALUES (<literals>);` per row using ONLY the row's declared columns (omitted columns fall to DB
  default/NULL — the no-fabrication guarantee). `_sql_literal` is the codebase's first SQL-literal
  quoter (single quotes doubled; bool->TRUE/FALSE before int; None->NULL; numbers bare; dict/list->
  `'<json sort_keys>'::jsonb`). Exported `render_postgres_seed`.
- `backend_python.py` / `backend_go.py`: append `migrations/0002_seed.sql` inside the existing
  `if has_db:` block, only when the seed is non-empty (fixtures present). `examples.py`: `minimal-blog`
  gains two Post fixtures + a Comment (post_id FK). `builder-demo.sh` prints the seed file when present.
- 14 new stdlib offline tests (316 total) in `test_seed_sql.py`: `_sql_literal` per type incl.
  quote-doubling + jsonb sorted keys; INSERT shape + alphabetical columns + FK column + empty-without-
  fixtures + byte-stable; adapter emission (python+go emit for minimal-blog; none for rideshare/OTHER
  db); validation errors/warning; IR round-trip + normalize preserves fixtures. `task verify` +
  `security:quick` + `env:check` pass; no existing test broke.
- Tracker: the sheet structure had diverged from my hardcoded scripts (table `A4:M255`, split sqref
  ranges), so R-248 used a GENERAL row-insertion `tracker_edit_r248.py` — insert at row 9, shift 9..255
  -> 10..256, and bump every row >= 9 across sqrefs, the table ref, and sheet1's Phase_Roadmap ranges;
  validated rows 1..256 contiguous, table `A4:M256`, sheet1 `$B$4:$B$256`/`$H$4:$H$256`, XML well-formed.
- Committed directly to main. Tracker row R-248 (Builder) inserted at row 9; MVP total 142 / Done 37.
  Implementation checkpoint `9d34720`. 0 local / 0 cloud model calls; nothing run/connected.

## 2026-09-08 — R-249

- Deepened the generated persistence layer with uniqueness + indexes from the IR. `ir.py`: `Field`
  gains `unique: bool = False` (validated, serialized); new `Index` record (fields + unique + optional
  name, fields validated as idents); `Entity` gains `indexes: tuple[Index, ...] = ()` and validates that
  each index field is a declared field of the entity. `to_dict`/`from_dict` updated; exported `Index`.
  `normalize_ir` needs no change (entities pass through as objects, so the new attrs ride along).
- `schema_sql.py`: `_column_lines` appends ` UNIQUE` to a unique non-`id` column (the `id` PK never gets
  a redundant UNIQUE); new `_index_statements(ir)` emits `CREATE [UNIQUE] INDEX <name> ON <table>
  (<cols>);` per entity index under an `-- Indexes` section, with a deterministic default name
  (`<table>_<cols>_idx`, `_key` when unique) when unnamed.
- `examples.py`: `rideshare-favourites` `Driver` gained `indexes=(Index(("name",)),)` for a visible demo
  (`CREATE INDEX driver_name_idx ON driver (name);`).
- 11 new stdlib offline tests (327 total) in `test_schema_indexes.py`: unique non-id column, id-never-
  unique, single/composite/named indexes (default naming, unique vs not), no-index-section-when-none,
  the example driver index, bad-index-field construction error, empty-index-fields error, and IR
  round-trip + byte-stability. `task verify` + `security:quick` + `env:check` pass; no existing test
  broke; the `0002_seed` and data-access/route/auth code are untouched (schema-only change).
- Tracker: reused the general row-insertion script (baseline `1c0072f`, LAST=256) — R-249 (Builder) at
  row 9; rows 1..257 contiguous, table `A4:M257`, sheet1 ranges to 257, XML well-formed. MVP total
  143 / Done 38. Implementation checkpoint `28e7cd5`. 0 local / 0 cloud model calls; no DB connection.

## 2026-09-08 — R-250

- Made the IR `Field.validation` tuple meaningful. New `codegen/field_validation.py`:
  `parse_field_rules(field) -> FieldRules(max_length, enum)` parses `max_length:<int>` and
  `enum:<a>|<b>|<c>`; unknown / non-digit rules are ignored (forward-compatible). Exported from codegen.
- `schema_sql._column_lines`: a STRING field with `max_length` renders `VARCHAR(n)` (else TEXT); an enum
  appends `CHECK (<col> IN ('a','b'))` after NOT NULL/UNIQUE with single-quote-escaped values; the `id`
  PK column is unaffected.
- `backend_python._models_file`: new `_py_field_line` applies rules — `Field(max_length=n)` (or
  `Field(default=None, max_length=n)` when optional) and a `Literal[...]` type for enums; `Field` and
  `Literal` are imported only when actually used, so rule-free models are byte-identical to before.
- Go request-validation tags deferred (the schema already constrains Go writes at the DB level). Example
  IRs left unchanged so existing generated outputs stay stable; the feature is exercised by
  constructed-IR tests.
- 10 new stdlib offline tests (337 total) in `test_field_validation.py`: parser (max_length/enum,
  unknown/non-digit ignored), schema VARCHAR + escaped CHECK + text-without-max_length, Pydantic
  Field/Literal + optional constraint + no-rules-no-Field-import (valid Python via ast), and an
  examples-unaffected guard. `task verify` + `security:quick` + `env:check` pass; no existing test broke.
- Tracker: general row-insertion `tracker_edit_r250.py` (baseline `5e4d72f`, LAST=257) — R-250 (Builder)
  at row 9; rows 1..258 contiguous, table `A4:M258`, sheet1 ranges to 258, XML well-formed. MVP total
  144 / Done 39. Implementation checkpoint `1eed171`. 0 local / 0 cloud model calls; no DB connection.

## 2026-09-08 — R-251

- Extended R-250 field validation to the Go backend and added numeric bounds — validation now spans all
  three targets. `field_validation.py`: `FieldRules` gained `minimum`/`maximum` (raw numeric literals,
  `_NUMBER`-validated, non-numeric ignored); `parse_field_rules` reads `min:<n>`/`max:<n>`; new
  `go_validate_tag(field, rules)` builds `max=`/`oneof=`/`gte=`/`lte=`.
- `schema_sql`: numeric INT/FLOAT fields append `CHECK (col >= n)` / `CHECK (col <= n)` (combined with an
  enum CHECK when present); strings never get a numeric check. `backend_python`: numeric fields add
  `ge=`/`le=` to the Pydantic `Field(...)`. `backend_go._models_file`: append ` validate:"..."` inside
  the struct tag when the tag body is non-empty; rule-free fields keep the exact plain `json` tag
  (so the existing rideshare adapter assertions stay green).
- Go tags are declarative this task — no `go.mod` dependency and no `validator.Struct` call (that
  enforcement is the R-252 follow-up); the schema already enforces at the DB for both backends.
- 8 new stdlib offline tests (345 total) in `test_field_validation_numeric.py`: numeric parser
  (raw tokens, non-numeric ignored), schema numeric CHECK + string-not-numeric, Pydantic ge/le, the
  `go_validate_tag` helper + emitted struct tags (max/gte-lte/oneof, rule-free plain tag), and an
  examples-have-no-validate-tags guard. `task verify` + `security:quick` + `env:check` pass; no existing
  test broke (fixed one over-strict new assertion that omitted NOT NULL).
- Tracker: general row-insertion `tracker_edit_r251.py` (baseline `9315dcb`, LAST=258) — R-251 (Builder)
  at row 9; rows 1..259 contiguous, table `A4:M259`, sheet1 ranges to 259, XML well-formed. MVP total
  145 / Done 40. Implementation checkpoint `2060a21`. 0 local / 0 cloud model calls; no DB connection.

## 2026-09-08 — R-252

- Founder chose option 1 after R-251 ("Go with option 1 ... bcoz we do not want anything static or seeds
  data in our platform"): wire go-playground enforcement in the generated Go create handlers rather than
  render seed/indexes/validation in the static console. Made the R-251 Go `validate:"..."` tags actually
  enforced at request time. (FastAPI already enforces at construction via Pydantic — Go was the gap.)
- `field_validation.py`: added `VALIDATOR_REQUIRE = "github.com/go-playground/validator/v10 v10.22.1"`
  and `go_validate_file()` — the `internal/handlers/validate.go` source (a shared `var validate =
  validator.New()` + a `validateStruct(v any) (int, string)` helper returning
  `http.StatusBadRequest`/`"validation_failed"` on a tag violation, `""` when valid). Mirrors
  `auth_guard.GOLANG_JWT_REQUIRE` / `go_auth_file`. Both exported from `codegen/__init__.py`.
- `backend_go.py`: compute `repo_entities`/`fk_by_entity` up front; new `_validated_entities(ir)` =
  entity names with a non-empty `go_validate_tag`; `has_validation` = any wired CREATE whose entity is in
  that set. `go.mod` gains `require VALIDATOR_REQUIRE` and `internal/handlers/validate.go` is emitted only
  when `has_validation`. `_handlers_file_wired` takes `validated_entities`; the CREATE branch emits
  `if status, msg := validateStruct(m); msg != "" { http.Error(w, msg, status); return }` between the
  JSON decode block and the `store.Create…` call — but only for entities carrying rules.
- Rule-free projects and both example IRs stay byte-identical to R-251 (no dep, no `validate.go`, no
  call); the validator dependency lives only in the generated project's `go.mod` (no platform dep). No
  Python/FastAPI change — Pydantic already enforced. Validation now holds at three layers: request model,
  request handler, and the DB schema.
- 5 new stdlib offline tests (350 total) in `test_go_validation_enforcement.py`: enforcement emitted for
  a rules+create IR (go.mod require, validate.go contents), handler call ordering (decode < validateStruct
  < store.Create), enforcement absent for a rule-free IR and for a rules-without-create IR (tags still
  present), and both example IRs emit none. `task verify` + `security:quick` + `env:check` pass; no
  existing test broke.
- Tracker: general row-insertion `tracker_edit_r252.py` (baseline `842819e`, LAST=259) — R-252 (Builder)
  at row 9, R-251 shifted to row 10; rows 1..260 contiguous, table `A4:M260`, sheet1 ranges to 260, XML
  well-formed. Done 41. Implementation checkpoint `f4fc828`. 0 local / 0 cloud model calls; no DB.
