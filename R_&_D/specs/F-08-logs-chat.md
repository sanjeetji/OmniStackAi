# F-08 · Logs and chat controls (proposed Tracker ID: R-506)

**Status:** specified, unblocked. **Depends on:** F-01; the Logs half is better after F-02.

Two related gaps: the user cannot see what happened, and cannot stop what is happening.

---

## Part 1 — Logs

### What exists

The build already streams real events over SSE (R-484/R-485) and the preview runner already
captures the generated app's stdout/stderr (`localrun/run.py` writes them). Neither is kept or
shown. `/jobs/build/{id}/problems` shows `tsc` output only.

### Design

- The agent-engine appends every build/edit event to `<workspace>/logs/build-<timestamp>.jsonl`
  (`{ts, level, phase, message}`), and the preview runner tees the app's output to
  `<workspace>/logs/app.log` with a size cap and rotation (`OMNISTACKAI_LOG_MAX_BYTES`,
  default 5 MB, 3 files).
- Secrets scrubbing before write: any value that matches a known project secret is replaced with
  `***` (F-05 provides the value set). Environment dumps are never logged.
- `GET /api/workspaces/{id}/logs?source=build|app&since=<cursor>` returns lines after a cursor;
  `?follow=1` streams them as SSE.

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/projects/{id}/logs?source=build\|app&since=` | Page of lines + next cursor. |
| `GET` | `/projects/{id}/logs/stream?source=` | SSE tail. |
| `DELETE` | `/projects/{id}/logs?source=` | Clear. |

### UI

Reference: Lovable's Logs page (`Lova-17`).

**Manage → Logs**: source switch (Build / App), level filter, search box, a monospace virtualised
list with timestamps, Follow toggle (auto-scroll), Copy and Download. Empty state: "Nothing logged
yet — run a build or start the preview." Error lines are tinted with the destructive colour; the
Problems tab links into the relevant log line.

---

## Part 2 — Chat controls

### Stop (real cancellation, not just a UI reset)

- The console's SSE reader gets an `AbortController`; pressing Stop aborts the fetch **and** calls
  `POST /projects/{id}/build/cancel` so the server does not keep generating and billing.
- Control-plane → agent-engine `POST /api/workspaces/{id}/cancel` sets a cancellation flag the
  generation loop checks between streamed chunks and between files; the loop exits cleanly,
  writes the partial state, and emits a final `{"phase":"cancelled"}` frame.
- Credits are charged for what was actually consumed up to the cancel — recorded in `model_calls`
  with `purpose = 'build'`, `error_code = 'cancelled'`. Honest, not free and not full price.
- The chat shows "Stopped. Nothing was committed." (or "…partial work discarded") and the composer
  returns to idle.

### Voice input

- Browser `SpeechRecognition` (Web Speech API) — no dependency, no server cost, no key.
- Mic button in the composer with three states (idle / listening with a level indicator /
  transcribing), inserting text into the composer for the user to edit before sending.
- Unsupported browsers: the button is hidden, not shown-and-broken (feature-detect
  `window.SpeechRecognition || window.webkitSpeechRecognition`).

### Attachments

- Accepts **text-like** files (`.md`, `.txt`, `.json`, `.csv`, `.sql`, `.ts`, `.tsx`, `.py`, …) up
  to 256 KB each, 4 per message: content is appended to the prompt as a fenced block with the
  filename, and shown as a chip the user can remove.
- Accepts **images** only when the resolved model is vision-capable (F-06 knows this); otherwise
  the picker says "The current model can't read images — switch model in Manage → AI."
- Files are sent with the message and stored with the turn (`<workspace>/attachments/<turn>/`),
  never uploaded anywhere else, and counted in the context cap from F-04.

### UI

Composer gains: paperclip (attachments), mic (voice), and the send button becomes **Stop** with a
square icon while a build is running — the pattern the founder asked for and that every reference
platform uses.

## Acceptance criteria

- [ ] Stop during a streaming build ends it within a second, emits `cancelled`, commits nothing,
      and records the partial usage.
- [ ] Logs show real build events and real app output, with secrets masked (explicit test with a
      secret value present in the app's output).
- [ ] Voice input transcribes into the composer in a supported browser; the button is absent
      elsewhere.
- [ ] A `.csv` attachment measurably reaches the model (the generated app uses its columns), and
      an image attachment is refused with the honest message on a text-only model.
- [ ] Gates as usual; the cancel path has agent-engine unit tests with a stub provider (offline).
