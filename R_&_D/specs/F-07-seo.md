# F-07 · SEO & AI search (proposed Tracker ID: R-505)

**Status:** specified, unblocked. **Depends on:** F-01. Better after G-01 (a public URL makes the
checks verifiable end to end), but everything here is testable on the generated source.

## Why

The founder asked for "SEO & AI Search with AI/ML — per page SEO". The honest, high-value version
is not a keyword-score widget: it is **generating apps that are actually indexable by search
engines and readable by AI crawlers**, then showing the user what was generated and letting them
edit it. Most competitors ship none of this, and it is pure codegen — no infrastructure, no gate.

## What gets generated (codegen changes)

For every generated Next.js app:

1. **Per-page metadata** — `title`, `description`, `openGraph`, `twitter`, `alternates.canonical`
   derived from the page's purpose in the IR, overridable per page by the user.
2. **`app/sitemap.ts`** — enumerates static routes and, for entity detail routes, reads the
   database at request time.
3. **`app/robots.ts`** — allows indexing, points at the sitemap; a "Discourage search engines"
   switch flips it to `disallow: /` for staging.
4. **`public/llms.txt`** — the emerging convention for AI crawlers: what the app is, its main
   routes, and its content policy. Cheap, and it is the "AI search" half of the request.
5. **JSON-LD structured data** — `WebSite` + `Organization` on the home page, and an entity-shaped
   schema (`Article`, `Product`, `Event`, …) on detail pages when the IR maps cleanly.
6. **`opengraph-image.tsx`** per app, generated with `next/og` from the app name and tagline (the
   same technique the console itself uses, R-496).
7. **Semantic correctness** — one `<h1>` per page, real `<title>`, `alt` on generated images,
   `lang` on `<html>`.

## Per-project SEO data

```sql
-- migrations/000009_seo.up.sql
CREATE TABLE IF NOT EXISTS project_seo (
    project_id     UUID PRIMARY KEY REFERENCES projects (id) ON DELETE CASCADE,
    site_name      TEXT NOT NULL DEFAULT '',
    default_title  TEXT NOT NULL DEFAULT '',
    description    TEXT NOT NULL DEFAULT '',
    canonical_host TEXT NOT NULL DEFAULT '',
    discourage     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_page_seo (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    route       TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    noindex     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, route)
);
```

Editing a page's SEO writes the row **and** regenerates that page's metadata block in the repo as
a normal edit commit — so the user's repository always contains the truth, not a hidden override.

## API

| Method | Route | Behaviour |
| --- | --- | --- |
| `GET`/`PUT` | `/projects/{id}/seo` | Site-level defaults. |
| `GET` | `/projects/{id}/seo/pages` | Every route the app exposes, with its current metadata. |
| `PUT` | `/projects/{id}/seo/pages/{route}` | Per-page overrides → regenerates and commits. |
| `POST` | `/projects/{id}/seo/audit` | Runs the audit (below) against the generated source. |

## The audit (the "AI/ML" part, honestly scoped)

A deterministic checker over the generated source — no model call needed, so it is free and fast:
missing/duplicate titles, description length (50–160), missing canonical, missing OG image,
multiple or missing `<h1>`, images without `alt`, no sitemap entry for a public route, `noindex`
left on, missing `llms.txt`. Each finding names the file and line and offers a one-click fix that
goes through the normal edit path.

**Optional model pass** (only when the user clicks "Suggest copy"): asks the model for a better
title/description for a page, shown as a suggestion the user accepts or rejects. That is the only
place a model is involved, and it is opt-in because it costs credits.

## UI

Reference: Lovable's SEO & AI search page (`Lova-29`).

- **Manage → SEO**: site defaults (name, title template, description, canonical host, discourage
  switch); a page table (route, title, description length bar, indexable) with inline edit; an
  **Audit** button that lists findings grouped by page with Fix buttons; a preview card showing
  how the page looks in Google and when shared.
- Copy stays plain: "Search engines and AI crawlers read these", no marketing claims about
  rankings.

## Acceptance criteria

- [ ] A freshly generated app contains per-page metadata, `sitemap.ts`, `robots.ts`, `llms.txt`,
      JSON-LD and an OG image, and still passes its own `tsc` check.
- [ ] Editing a page's title in the UI produces a commit in the project's repo.
- [ ] The audit reports real findings on a deliberately broken page and passes on a good one.
- [ ] The optional copy suggestion is opt-in and its credit cost is shown before running.
- [ ] Gates as usual, including codegen unit tests for every emitted file (offline).
