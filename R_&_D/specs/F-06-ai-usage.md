# F-06 · AI — model configuration and usage (proposed Tracker ID: R-504)

**Status:** specified, unblocked. **Depends on:** F-01 (per-project attribution), F-05 (key
encryption).

## Why

Two of the founder's asks meet here: *"AI uses, per project and overall"* and *"configure
different models: adding API key, models"*. This is also where the free-vs-paid strategy becomes
real: a user either brings their own provider key (their cost, no credits) or uses platform
credits, and can see exactly what each project consumed.

Today: keys live in the server's `.env` and are shared by every user; `byok_enabled` is a boolean
that does nothing; usage exists only per build response.

## Design

### Model resolution order (decided, and shown in the UI)

1. The **project's** pinned provider/model, if set.
2. The **user's** own key for that provider (BYOK) — no credits are charged.
3. The **platform's** configured cloud provider — credits are charged.
4. **Local Ollama** — free, and the fallback when nothing else is available.

Whichever wins is displayed in Settings and in the project's AI panel, with the reason
("Using your OpenAI key", "Using platform credits", "Using your local model") — the honest
version of what `/jobs/providers` already computes.

### Database

```sql
-- migrations/000008_ai_usage.up.sql
CREATE TABLE IF NOT EXISTS user_provider_keys (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider_id    TEXT NOT NULL,
    key_ciphertext BYTEA NOT NULL,
    label          TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at   TIMESTAMPTZ,
    UNIQUE (user_id, provider_id)
);

CREATE TABLE IF NOT EXISTS model_calls (
    id               BIGSERIAL PRIMARY KEY,
    user_id          UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    project_id       UUID REFERENCES projects (id) ON DELETE SET NULL,
    provider_id      TEXT NOT NULL,
    model_id         TEXT NOT NULL,
    tier             TEXT NOT NULL CHECK (tier IN ('local', 'cloud')),
    purpose          TEXT NOT NULL DEFAULT 'build',
    input_tokens     BIGINT NOT NULL DEFAULT 0,
    output_tokens    BIGINT NOT NULL DEFAULT 0,
    cost_micros_usd  BIGINT NOT NULL DEFAULT 0,
    credits_spent    BIGINT NOT NULL DEFAULT 0,
    billed_to        TEXT NOT NULL CHECK (billed_to IN ('platform', 'byok', 'local')),
    success          BOOLEAN NOT NULL DEFAULT TRUE,
    error_code       TEXT NOT NULL DEFAULT '',
    latency_ms       INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS model_calls_user_created_idx    ON model_calls (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS model_calls_project_created_idx ON model_calls (project_id, created_at DESC);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS model_provider_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS model_id          TEXT NOT NULL DEFAULT '';
```

`model_calls` is written from the same place credits are debited, inside the same transaction, so
the two can never disagree. The agent-engine already returns the full usage block (`RecordingProvider`
→ `UsageLedger`); this task persists it instead of discarding it.

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/ai/providers` | Existing provider status + which source would be used and why. |
| `GET`/`PUT`/`DELETE` | `/ai/keys/{providerId}` | The user's own key (write-only; never returned). |
| `GET` | `/ai/models` | Models available per provider, with price-book entries where known. |
| `GET`/`PUT` | `/projects/{id}/model` | The project's pinned provider/model. |
| `GET` | `/projects/{id}/usage?range=7d` | Calls, tokens, cost, credits, per day and per purpose. |
| `GET` | `/usage?range=30d` | Account-wide totals, plus a per-project breakdown. |

### UI

Reference: Lovable's AI page and Usage page (`Lova-20`, `Lova-18`, `Lova-34`).

- **Settings → AI** (account): provider cards (already built in R-495) gain "Use my own key" with
  a masked input, a Test button that makes one real cheap call and reports the result honestly,
  and a "Billed to you / Billed in credits" badge. Default model selector.
- **Manage → AI** (project): the resolved model for this project with the reason, an override
  selector, and this project's usage — calls, in/out tokens, cost, credits — with a small
  sparkline by day and a table by purpose (build / edit / UI synthesis / problems).
- **Settings → Usage** (account): totals for the range, a per-project table sorted by credits, and
  the credit balance with a note that local-model calls are free.
- Numbers use `tabular-nums`; zero states say "No model calls in this range" rather than showing
  a fake chart.

## Acceptance criteria

- [ ] A build's usage appears in `model_calls` with the right project, tokens, cost and
      `billed_to`, and the sum of `credits_spent` equals the `credit_ledger` delta for that build.
- [ ] With a user key set, a build makes the call with that key, charges **zero** credits, and is
      recorded as `billed_to = 'byok'`.
- [ ] Keys are never returned by any endpoint; a test asserts the JSON never contains the value.
- [ ] Pinning a model on a project makes that model run the next build (verified live, recorded).
- [ ] Local-model builds are recorded with `tier = 'local'`, `billed_to = 'local'`, zero credits.
- [ ] Gates as usual; the live evidence names the real provider/model used.

## Note on the existing price-book gap

Several tasks recorded `credits_spent: 0` because the configured cloud model has no price-book
entry. This task surfaces that honestly: calls with no price are recorded with
`cost_micros_usd = 0` and counted in an "unpriced calls" figure in the UI, instead of implying the
work was free.
