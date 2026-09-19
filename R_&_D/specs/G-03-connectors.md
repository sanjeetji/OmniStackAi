# G-03 · Connectors (proposed Tracker ID: R-511)

**Status:** specified, **GATED — each provider needs an OAuth application the founder registers.**
**Depends on:** F-05 (token storage).

## What a connector is here

A connector lets a **generated app** talk to a third-party service using the **end user's own**
account: "send this form to my Gmail", "add the booking to my Google Calendar", "track visits in
my Google Analytics". Two things must be built: a small framework, and one provider at a time.

Lovable's Connectors screen lists ~113 services (`Lova-23` … `Lova-27`). Most of that list is
breadth-for-marketing. We should ship **few, working, and honest**.

## Recommended order (and the reasoning)

| Order | Connector | Why | Cost to register |
| --- | --- | --- | --- |
| 1 | **Google Analytics 4** | Highest value, lowest complexity — it is a measurement ID pasted into the generated app's layout. Not even OAuth in v1. | none |
| 2 | **Transactional email** (Resend or SMTP) | Every generated app needs "send the user an email". SMTP works with any provider the user already has. | none (user's own SMTP/API key via Secrets) |
| 3 | **Google Calendar** | Real, demoable use case (bookings). | Google Cloud OAuth consent screen |
| 4 | **Gmail send** | Same OAuth app as Calendar, different scope. | shares #3's app |
| 5 | Slack / Sheets / Drive | Common asks; add on demand. | one app each |
| — | **Google Ads** | **Not now.** Little value for a builder, heavy Google review, and the API is complex. | — |

Verdict: build the framework + 1 and 2 in this task; 3–4 only when the founder registers the
Google Cloud project and accepts the consent-screen review.

## Design

### Framework

```
ConnectorDefinition = {
  id, name, category, auth: "none" | "api_key" | "oauth2",
  scopes[], config_schema, codegen_hook
}
```

- `auth: none` / `api_key` → the value is stored as a project secret (F-05); no new machinery.
- `auth: oauth2` → the control-plane runs the standard authorization-code flow, stores the
  refresh token encrypted per user, and mints access tokens on demand (never stored).
- `codegen_hook` is what makes a connector *real*: enabling it changes the generated app — GA4
  injects the tag into the root layout; email generates a `lib/email.ts` plus a working
  server action; Calendar generates a typed client and an example route.
- Disabling a connector removes its generated code in the same edit commit.

### Database

```sql
-- migrations/000012_connectors.up.sql
CREATE TABLE IF NOT EXISTS connector_accounts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider                TEXT NOT NULL,
    external_account        TEXT NOT NULL DEFAULT '',
    refresh_token_ciphertext BYTEA,
    scopes                  TEXT NOT NULL DEFAULT '',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider, external_account)
);

CREATE TABLE IF NOT EXISTS project_connectors (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id           UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    provider             TEXT NOT NULL,
    connector_account_id UUID REFERENCES connector_accounts (id) ON DELETE SET NULL,
    config               JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, provider)
);
```

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/connectors` | The catalogue we actually support, with auth type and what enabling it generates. |
| `GET` | `/connectors/{provider}/authorize` · `/callback` | OAuth flow for `oauth2` connectors. |
| `GET` | `/projects/{id}/connectors` | Enabled connectors and their config. |
| `PUT` | `/projects/{id}/connectors/{provider}` | Enable/configure → triggers the codegen edit. |
| `DELETE` | `/projects/{id}/connectors/{provider}` | Disable → removes the generated code. |
| `POST` | `/projects/{id}/connectors/{provider}/test` | Makes one real call and reports the result. |

## UI

Reference: Lovable's Connectors browser (`Lova-23`, `Lova-24`).

- **Manage → Connectors**: a grid of supported connectors with icon, name, one-line description,
  and a state chip (Not connected / Connected / Needs key). A category filter appears only once
  there are enough to need one — no fake 113-item catalogue.
- Enabling opens a panel: what this will add to your app (the exact files), the fields it needs,
  and a **Test** button that makes a real call.
- A "Request a connector" link that records the ask, instead of listing services we cannot honour.

## Acceptance criteria

- [ ] Enabling GA4 with a measurement ID produces a commit that adds the tag, and the running
      preview sends a real pageview (verified in GA's realtime view).
- [ ] Enabling email produces a working send path; the Test button delivers a real message.
- [ ] Disabling a connector removes exactly the code it added (diff review in the task evidence).
- [ ] Tokens are encrypted, never returned, never logged, and revocable.
- [ ] The catalogue lists only connectors that work.
- [ ] Gates as usual; live evidence for each connector shipped.
