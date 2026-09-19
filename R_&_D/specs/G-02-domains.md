# G-02 · Custom domain — bring your own (proposed Tracker ID: R-510)

**Status:** specified. **Founder decision (2026-09-19): bring-your-own only. We do not sell
domains and do not take on domain billing.** **Depends on:** G-01.

## Scope

The user already owns `app.theircompany.com` (or buys it anywhere they like) and points it at
their published app. We verify it and attach it through the hosting provider. We never touch
registrars, renewals, WHOIS or money.

## Flow

```
1. User enters a hostname in Manage → Domain.
2. We create the domain on the hosting provider (Vercel/Netlify API) and read back the exact
   DNS record it requires:
      apex        → A     76.76.21.21        (provider-specific; always read from the API)
      subdomain   → CNAME cname.vercel-dns.com
3. The UI shows the record with a copy button, per-registrar hints (GoDaddy, Namecheap,
   Cloudflare, Hostinger, BigRock) and a "Check now" button.
4. Verification: the control-plane resolves the hostname and asks the provider for its own
   verification status. Both must agree before we mark it verified.
5. TLS: issued by the provider automatically once DNS resolves. We show its real state
   (pending / issued / failed) — never a fake padlock.
6. The project's canonical host (F-07) and the app's public URL update to the custom domain.
```

DNS propagation can take minutes to 48 hours. The UI says exactly that, keeps polling every 30 s
for 10 minutes and then every 6 hours, and never claims failure before the provider does.

## Database

```sql
-- migrations/000011_domains.up.sql
CREATE TABLE IF NOT EXISTS project_domains (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id         UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    hostname           TEXT NOT NULL UNIQUE,
    provider           TEXT NOT NULL,
    record_type        TEXT NOT NULL DEFAULT 'CNAME',
    record_name        TEXT NOT NULL DEFAULT '',
    record_value       TEXT NOT NULL DEFAULT '',
    status             TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','verifying','verified','failed','removed')),
    tls_status         TEXT NOT NULL DEFAULT 'pending',
    is_primary         BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at    TIMESTAMPTZ,
    verified_at        TIMESTAMPTZ,
    error              TEXT NOT NULL DEFAULT '',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

The global `UNIQUE (hostname)` prevents two users claiming the same host and is also the
anti-hijack check: a hostname already verified elsewhere is refused.

## API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET` | `/projects/{id}/domains` | List with status and the required DNS record. |
| `POST` | `/projects/{id}/domains` | `{hostname}` → validates the format, registers it with the provider, returns the record to add. |
| `POST` | `/projects/{id}/domains/{domainId}/verify` | Re-checks DNS + provider status now. |
| `DELETE` | `/projects/{id}/domains/{domainId}` | Removes it here and at the provider. |

Validation: a real hostname (RFC 1123), not an IP, not a public suffix on its own, not one of our
own domains, and not already verified by another project.

## UI

Reference: Lovable's Domains page (`Lova-32`) — but with the "buy a domain" half deliberately
removed, replaced by one line: *"Buy a domain from any registrar, then point it here."*

- **Manage → Domain**: empty state explains it in one sentence; an input with live format
  validation; after submit, a DNS instruction card (type, name, value, TTL) with copy buttons and
  a registrar hint dropdown; a status row (DNS: pending/found, TLS: pending/issued) with **Check
  now**; once verified, the live link, a Primary toggle if several, and Remove.
- Errors are the provider's own words plus what to do next.

## Acceptance criteria

- [ ] Adding a real domain returns the provider's real DNS record; after the record is created,
      verification turns green and the site serves over HTTPS on that hostname.
- [ ] A hostname already verified by another project is refused with a clear message.
- [ ] Removing a domain removes it at the provider too.
- [ ] The UI never shows "secure" before the provider reports the certificate as issued.
- [ ] Gates as usual; live evidence uses a real domain the founder controls.

## Explicitly out of scope

Domain search, purchase, renewal, transfer, WHOIS privacy, DNS hosting. Founder's decision, and
the right one until platform billing exists.
