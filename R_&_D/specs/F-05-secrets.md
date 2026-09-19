# F-05 · Secrets — encrypted per-project configuration (proposed Tracker ID: R-503)

**Status:** specified, unblocked. **Depends on:** F-01. **Blocks:** G-03 connectors, G-04 payments,
and the token storage in F-03/F-06.

## Why

A generated app needs real configuration: a payment key, an SMTP password, a third-party API key.
Today the only place for those is the server's `.env`, which is ours, not the user's, and is
shared by everyone. Secrets are also the prerequisite for connectors and payments.

## Design

### Cryptography (Go standard library only)

The control-plane must keep **exactly one direct Go dependency** (`scripts/test.sh` asserts it),
so encryption uses `crypto/aes` + `crypto/cipher` (AES-256-GCM) from the standard library.

- Master key: `OMNISTACKAI_SECRETS_KEY` — 32 random bytes, base64, in `.env` (added to
  `.env.example` as an empty placeholder with a generation hint:
  `openssl rand -base64 32`).
- Each secret: random 12-byte nonce, `AES-256-GCM(value, nonce, aad = project_id || key)`.
  Stored as `nonce || ciphertext` in a `BYTEA`.
- Binding the project id and key name into the AAD means a stolen row cannot be replayed under a
  different key name or project.
- **Startup check:** if the key is missing or not 32 bytes, the secrets routes return 503 with a
  clear message rather than storing plaintext. `task env:check` gains an assertion for the
  placeholder's presence in `.env.example`.
- Rotation: `OMNISTACKAI_SECRETS_KEY_PREVIOUS` allows decrypt-with-old, re-encrypt-with-new on
  first read. Documented, implemented, tested.

### Database

```sql
-- migrations/000007_project_secrets.up.sql
CREATE TABLE IF NOT EXISTS project_secrets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    key              TEXT NOT NULL CHECK (key ~ '^[A-Z][A-Z0-9_]*$'),
    value_ciphertext BYTEA NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at     TIMESTAMPTZ,
    UNIQUE (project_id, key)
);
```

The `key` check enforces `UPPER_SNAKE_CASE`, so secrets map cleanly to environment variables.

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/projects/{id}/secrets` | Names, descriptions, updated_at, last_used_at. **Never values.** |
| `PUT` | `/projects/{id}/secrets/{key}` | `{value, description?}` — create or replace. |
| `DELETE` | `/projects/{id}/secrets/{key}` | Remove. |
| `POST` | `/projects/{id}/secrets/reveal/{key}` | Returns the value once, requires the session, writes an audit row. Used only by the "Show" control. |

Internal: `secrets.ForProject(projectID) → map[string]string` is used by the preview runner and,
later, by deployments. It is the **only** path values take out of the database.

### Where the values actually go

- **Preview (F-02):** injected into the generated app's process environment when the runner starts
  it, on top of the generated `.env.example` defaults. They are never written to a file inside the
  repo, so they cannot be committed or pushed to GitHub.
- **Publish (G-01):** set as environment variables on the deployment target through that
  provider's API.
- **Never** rendered into generated code, logs, the build stream, or the ZIP export.

### UI

Reference: Lovable Settings → Secrets (`Lova-12`, `Lova-13`).

- **Manage → Secrets**: table of key, description, updated, last used, actions (Show, Edit,
  Delete). "Add secret" dialog with key/value/description, a key-format hint, and an explicit
  line: *"Stored encrypted. Used when your app runs and when you publish it. Never written into
  your code."*
- Values are masked; **Show** calls the reveal route and re-masks after 30 seconds.
- Changing a secret shows "Restart the preview for this to take effect", with a Restart button.
- A generated app that reads an unset variable surfaces in Problems/Logs with a link that
  pre-fills the key name in the Add-secret dialog.

## Acceptance criteria

- [ ] A secret set in the UI is visible to the generated app at runtime (`process.env.X` /
      `os.environ["X"]`) after a preview restart, verified live.
- [ ] Values never appear in any list response, in the build stream, in a log file, in the ZIP, or
      in a pushed repository (explicit tests plus a grep over the exported archive).
- [ ] Deleting the project deletes its secrets (cascade test).
- [ ] With `OMNISTACKAI_SECRETS_KEY` unset, the routes return 503 and nothing is stored in
      plaintext.
- [ ] Key rotation re-encrypts on read and keeps values intact.
- [ ] Gates as usual, plus `task security:quick` extended with a "no secret value in responses"
      assertion.
