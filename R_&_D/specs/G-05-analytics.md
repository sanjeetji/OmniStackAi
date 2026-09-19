# G-05 · Analytics for published apps (proposed Tracker ID: R-513)

**Status:** specified. **Depends on:** G-01 (there must be a public app to measure) and, for the
zero-cost option, G-03's GA4 connector.

## Why it is last

Analytics measures traffic. Until an app is publicly reachable there is nothing to measure, so
building this earlier would mean building an empty dashboard. Note also that **AI usage
analytics — the thing a builder checks daily — is F-06**, not this task. This one is about the
*generated app's* visitors.

## Two options

| Option | How | Cost | Data ownership |
| --- | --- | --- | --- |
| **A. Surface the user's GA4** *(recommended)* | The GA4 connector (G-03) is already installed in the app; we read the GA Data API with the user's OAuth token and render the numbers inside our Manage → Analytics page. | ₹0 | Theirs, in their Google account |
| **B. First-party analytics we run** | A tiny script in generated apps posts pageviews to our collector; we store and aggregate. | Storage + write load that scales with *their* traffic, plus privacy/consent obligations in the EU and India's DPDP Act | Ours — which also makes us responsible for it |

**Recommendation: A.** It is free, it is more accurate than a home-grown counter, and it keeps us
out of being a data processor for our users' visitors. Revisit B only if users ask for analytics
without a Google account.

## Design (option A)

- Reads the **GA4 Data API** (`runReport`) with the connector's token for the property the project
  is linked to.
- Metrics: active users, sessions, pageviews, average engagement time, top pages, top referrers,
  device split, country split. Ranges: 24 h / 7 d / 30 d / custom.
- Cached for 5 minutes per project to stay inside Google's quotas; the UI shows the cache age.
- If no property is linked, the page explains how to link one rather than showing zeros.

### Database

```sql
-- migrations/000014_project_analytics.up.sql
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS analytics_provider    TEXT NOT NULL DEFAULT ''
        CHECK (analytics_provider IN ('', 'ga4')),
    ADD COLUMN IF NOT EXISTS analytics_property_id TEXT NOT NULL DEFAULT '';
```

No metric storage: the numbers stay in Google's system and are fetched on demand.

### API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET`/`PUT` | `/projects/{id}/analytics` | The linked GA4 property. |
| `GET` | `/projects/{id}/analytics/report?range=7d` | Metrics + top tables, with `cached_at`. |

## UI

Reference: Lovable's Analytics page (`Lova-05`) — including its honest empty state, which is the
part most products get wrong.

- **Manage → Analytics**: range selector; four stat cards (visitors, pageviews, avg. time, bounce)
  with `tabular-nums`; a sparkline by day; Top pages and Top referrers tables; device and country
  splits.
- Not linked: an explainer with a **Connect Google Analytics** button (G-03).
- Published but no data yet: "No visits recorded yet" with the live URL to share — never a
  fabricated chart.

## Acceptance criteria

- [ ] A published app with GA4 installed shows real visitor numbers that match the GA dashboard
      for the same range.
- [ ] Without a linked property the page explains what to do instead of showing zeros.
- [ ] API quota errors are surfaced honestly with the retry time.
- [ ] No visitor data is stored on our side (explicit statement in the task evidence).
- [ ] Gates as usual.
