# Edit loop — diff & patch-apply (Brief §6/§27/§34)

Generating an app once is the easy half. The differentiator is **editing** an existing app: change the
Application IR, regenerate, and apply *only the delta* to the customer's project — then record it as a
new commit on their owned repo. That is the edit loop.

Package: `omnistackai_agent_engine.edit` (diffing is pure/offline; applying is a bounded, path-safe disk
step, like the R-228 git service — no network, no code execution).

## Diff

`diff_projects(old, new)` compares two `GeneratedProject`s by path and returns a `ProjectDiff`:

- `added()` — paths in `new` only
- `modified()` — paths in both whose **content or executable bit** differs
- `deleted()` — paths in `old` only
- `unchanged` — identical in both

Identical projects diff to an empty change set (`is_empty()`), and `summary()` gives a one-line count.

`plan_edit(old_ir, new_ir)` is the entry point: it assembles both IRs into customer monorepos and diffs
them, so a change to the IR becomes exactly the set of files to rewrite. Changing the app description,
for example, yields a `modified` set containing `README.md` and nothing added or deleted.

## Apply

`apply_diff(diff, target_dir)` writes the added/modified files and removes the deleted ones, strictly
inside `target_dir` (a path that would escape the target is refused, mirroring `materialize_project`).
It returns an `ApplyReport` (added / modified / deleted paths); after it runs, the directory equals the
new project. Emptied directories left by a delete are pruned, never ascending past the target root.

## Commit

`commit_edit(diff, target_dir, *, author_name, author_email, message)` applies the diff and records one
commit as the customer identity, reusing the additive `git_service.commit_all` (`git add -A` +
`git commit`). Previous history is preserved — an edit is a normal commit on the owned repo.

```
old_ir → assemble → repo (commit 1)
          │
new_ir → plan_edit(old_ir, new_ir) → ProjectDiff → commit_edit → repo (commit 2)
```

Everything is deterministic and offline: no model call, no network, no build or run of generated code,
and no write outside the caller's target directory.

## Hunk-level diffs & rename detection (R-246)

On top of the file-level `ProjectDiff`, `diff_report(old, new)` produces a line-level view: each
`FileDiff` classifies a path as `added` / `modified` / `deleted` / `renamed` and carries a **git-style
unified (hunk) diff**. A deleted file whose content exactly matches an added file is reported as a
single `RENAMED` record (`old_path → path`), not a delete + add. `unified_patch(old, new)` concatenates
them into one byte-stable patch string (with `rename from`/`rename to` headers), so an edit reads as a
focused review-ready patch rather than whole-file churn. Pure/`difflib`-only; additive to the edit
package (`diff_projects` / `apply_diff` / `plan_edit` are unchanged).
