# Multi-turn chat / "continue editing this app" (R-468)

Every `/api/build` call used to be a fresh, stateless one-shot prompt: there was no way to say "now add a
favorites feature to the app I just built" and have it apply as a further edit to the *same* repo. R-468
adds exactly that, built entirely from primitives the platform already had — no new AI mechanism was
invented; the additive-delta pattern was already proven in `solution_packs/ai_delta.py`, and the
diff/commit half already worked, tested, and is reused **completely unmodified**.

```
follow-up prompt  →  generate_app_delta_proposal  →  a bounded, validated AppDeltaProposal
                       (new entities/apis/screens only — never a restatement of the whole app)
                              │
                              ▼
                      apply_app_delta(current_ir, proposal)   → new_ir  (tuple concatenation, re-validated)
                              │
                              ▼
                  plan_edit(current_ir, new_ir)   ← edit/diff.py, UNCHANGED
                              │
                              ▼
                  commit_edit(diff, repo_dir, …)  ← edit/apply.py, UNCHANGED
                              │
                              ▼
                a real second git commit on the SAME owned repo
```

## Why a delta, not a full re-generation

The obvious-looking alternative — re-call `generate_ir("{original}. Additionally: {follow_up}")` and diff
old vs new — was rejected after investigation: no code, no test, and no documented guarantee that the model
preserves every existing entity/screen verbatim (the intake system prompt actively tells it to "replace the
template content" of the example it's shown). A supersetting failure there would silently rename or drop
existing entities, producing a huge, confusing diff — the opposite of the clean incremental history this
feature exists for.

Instead, `intake/app_delta.py` is a **generic sibling of `solution_packs/ai_delta.py`**, with the same
shape (bounded typed proposal, strict JSON-only prompt, collision-checked merge, backstopped by
`ApplicationIR`'s own validation) but no Solution Pack coupling — any `ApplicationIR` can use it:

- `AppDeltaProposal(entities=(), apis=(), screens=(), rationale="")` — the same bounded/unique validation as
  `AIDeltaProposal`, minus the pack-specific fields.
- `build_app_delta_messages(base_ir, follow_up_prompt)` lists the app's **real** existing entities, APIs,
  screens, and roles as context, and instructs the model to propose *only* what's new.
- `parse_app_delta_proposal(text, base_ir=...)` strictly parses untrusted model output — rejecting a
  colliding entity name, API path, screen id, or a screen role that isn't one of the app's real roles — at
  parse time, so a rejection can be fed back for a retry.
- `apply_app_delta(base_ir, proposal)` re-checks every one of those collisions independently (defense in
  depth — a proposal reaching here might not have come through the parser) before merging by tuple
  concatenation (`base_ir.entities + proposal.entities`, mirroring `solution_packs/application.py`'s merge
  exactly) and a final `validate_ir`/`has_errors` semantic check.
- `generate_app_delta_proposal(...)` is a bounded validate→feedback→retry loop (default 3 attempts) —
  retries only on a validation rejection (the reason is fed back as a corrective turn), never on a provider
  exception, mirroring R-465's `_synthesize_file` idiom.

## The Studio wiring

`studio/session.py`'s `StudioSessionStore` is a small, bounded, in-memory, server-only store (same idiom as
`StudioBuildHistory`) keyed by the same build id, holding the app's **current** `ApplicationIR` (never sent
to the browser) and a bounded turn history. `live_serve.py::_build` starts a session only for the two build
kinds that produce exactly one IR — a plain-prompt build, or a **single-surface** Ecosystem Pack build.

`POST /api/build/{id}/edit` (body `{"prompt": "..."}`) runs the flow above and returns the updated
entities/file count/commit sha/diff summary/turn list; `GET /api/build/{id}/turns` returns the turn history
alone (used to repopulate the chat box, e.g. after a page reload). Both routes need no toolchain or running
preview — wired in build-only mode too, exactly like R-467's file browser.

## What's out of scope (v1)

- **Renaming, modifying, or removing** existing entities/fields — a collision with an existing name is
  always rejected, never merged. Only additive changes.
- **Multi-surface ("all surfaces") Ecosystem builds and Solution Pack builds.** Solution Pack apps already
  have their own, separate AI-delta mechanism (`ai_features`/`ai_delta_prompt`) at *initial build* time — a
  request to `/edit` a build recorded with a `pack_id` or `is_ecosystem: true` returns a clear, honest
  `EditNotSupportedError` (HTTP 400) rather than being silently ignored or guessed at. An "all surfaces"
  ecosystem build has no single IR to edit in the first place.
- **Wiring R-466's `compile_and_repair`** into the edit flow, so an edited hybrid-UI screen also gets
  type-checked/repaired — needs the toolchain, deferred.
- **Undo/revert UI** — the git history is real and on disk (`git log`/`git revert` work today from a
  terminal), but no UI exposes it yet.

## Run it

```bash
task agent-engine:studio:serve   # or :preview
```

Build an app, then use the "Continue editing this app" box under the file browser to add a follow-up
instruction — each one lands as a new commit on the same owned repo, visible in the chat log and in
`git log` on disk.
