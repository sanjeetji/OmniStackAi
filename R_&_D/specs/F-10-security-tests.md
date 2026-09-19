# F-10 · Security scan & Tests (proposed Tracker ID: R-508)

**Status:** specified. **Depends on:** F-01, F-02 (both need the app's toolchain installed).

Same shape as the existing Problems tab: run a real tool against the generated project, show its
real output, never invent a score.

---

## Part 1 — Security

### What actually runs

1. **Dependency audit** — `pnpm audit --json` for the web app; `pip-audit`/`uv pip check` for the
   Python backend when present; `govulncheck` for the Go backend when present. All are opt-in,
   toolchain-dependent, and run only when the user clicks — exactly like Problems.
2. **Secret scan of the generated code** — a deterministic scan of the repository for things that
   look like live credentials (provider key prefixes, long base64 blobs in source, `.env` files
   that are not `.env.example`). This catches the one failure mode that actually matters: the
   model writing a key into a file that then gets pushed to the user's GitHub.
3. **Framework checks** — deterministic rules over the generated source: auth guard present on
   routes the IR marked as protected; no `dangerouslySetInnerHTML` with unsanitised input; CORS
   not `*` when auth exists; cookies `httpOnly`+`sameSite`; SQL built through the generated data
   layer rather than string concatenation.

Findings: `{severity, rule, file, line, message, fix?}` where severity comes from the tool for
audits and from the rule for our own checks. Nothing is labelled "secure" — the UI says "No issues
found by these checks", with the checks listed.

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `POST` | `/projects/{id}/security/scan` | Runs the scan; streams progress like a build. |
| `GET` | `/projects/{id}/security` | The last report. |

---

## Part 2 — Tests

### What actually runs

The generated apps already contain tests for the code we emit. This task runs them and shows the
results:

- web: `pnpm test` when the generated app has a test script;
- Python backend: `python -m unittest` / `pytest` as generated;
- Go backend: `go test ./...`.

Output is parsed into `{suite, name, status, duration_ms, message}` where the runner's format
allows, and shown verbatim otherwise. A failing test links to the file and line in the Code tab.

**Also**: "Generate a test for this" in the chat — an edit that asks the model to write a test for
a named behaviour, then runs it. That is a normal edit, so it needs no new machinery.

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `POST` | `/projects/{id}/tests/run` | Runs the available suites; streams output. |
| `GET` | `/projects/{id}/tests` | The last run. |

## UI

Reference: Dyad's Security and Tests tabs (`Dyad-09`, `Dyad-11`) — the one place Dyad is ahead of
Lovable.

- **Manage → Security**: a Run scan button, last-run timestamp, findings grouped by severity then
  file, each expandable with the rule explanation and a Fix-with-AI button that sends a
  pre-written edit prompt. The checks that ran are listed by name, with any that were skipped
  (missing toolchain) shown as skipped — not silently omitted.
- **Manage → Tests**: Run button, summary bar (passed / failed / skipped / duration), a per-suite
  list, output pane for failures, and the honest empty state "This project has no test suite yet
  — ask the chat to add one."

## Acceptance criteria

- [ ] A project with a deliberately vulnerable dependency reports it with the tool's real advisory
      text.
- [ ] A hard-coded key planted in a generated file is found by the secret scan, and the same file
      is refused by the F-03 push path (cross-check).
- [ ] Running tests on a generated app produces real pass/fail counts; a deliberately broken test
      shows its real failure message.
- [ ] Missing toolchains are reported as "skipped: pnpm not installed", never as "passed".
- [ ] Gates as usual (the scans themselves stay out of `task verify` — they need a toolchain).
