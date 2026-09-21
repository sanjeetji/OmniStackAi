# Template catalogue

Every directory here is one template in the OmniStackAI template marketplace. A template is a
hand-built, complete application: real UI, API and database. It is not generated at request time.

## How templates behave

- **The original never changes for users.** It is read-only and identical for everyone.
- **"Use template" creates the user's own project.** The platform copies `repo/` into a new
  project workspace, creates a fresh git repository with one commit (`Template: <name> v<version>`)
  and records which template, version and digest it came from.
- **Users customise only their copy.** They can add or remove features and change behaviour. Other
  users and the original are never affected.
- **New template versions apply to new projects only.** Existing projects keep the code they
  started from.

## Layout

```
templates/catalog/<slug>/
  template.json   manifest (below)
  repo/           the complete source repository that gets copied
  media/          optional cover image and screenshots
```

Directories whose names start with `.` or `_` are ignored (useful for drafts).

## `template.json` (schema_version 1)

| Field | Rules |
| --- | --- |
| `schema_version` | `1` |
| `slug` | lowercase letters, digits and dashes. Must equal the directory name |
| `name` | display name, 60 characters or fewer |
| `version` | semantic version, for example `1.0.0`. Bump it whenever `repo/` changes |
| `category` | `mobility`, `commerce`, `healthcare`, `education`, `real-estate`, `services`, `fintech` or `content` |
| `tagline` | one line, 140 characters or fewer |
| `description` | the full description shown on the template page |
| `apps[]` | `{id, name, kind, path}`. `kind` is `web`, `admin`, `pwa` or `api`. `path` is relative to `repo/` and must exist. An `api` app needs `<path>/migrations/*.sql` |
| `roles[]` | `{id, name, description}`, one per stakeholder (customer, driver, admin, …) |
| `entities[]` | the main data entities, for example `"Trip"` |
| `features[]` | user-facing features |
| `integrations[]` | `{id, kind, provider, mock}`. `mock: true` means it runs without credentials |
| `demo_users[]` | `{role, name, email, password}`. `role` must be a declared role. These are local demo logins only |
| `stack[]` | technologies, for example `"Next.js"` |
| `cover`, `screenshots[]` | optional paths inside the template directory that must exist |

## Rules for `repo/`

- No `.git`, `node_modules`, `.next`, `.turbo` or `__pycache__` directories, and no symlinks.
- No real `.env` files. Ship `.env.example` with safe placeholder values. Real credentials never
  belong in a template.
- At most 5,000 files and 50 MB.
- The platform computes a digest (`sha256` over every file path and its content) so each project
  can prove which original it started from.

## How the preview runs a template project

"Use template" writes `omnistack.json` (apps, roles, demo logins) into the user's copy, so
templates must not ship a file with that name. The Preview tab reads it and runs every app together:

- **Dependencies:** one `pnpm install` at the repo root when `pnpm-workspace.yaml` exists (recommended),
  otherwise one per app. Every app directory needs a `package.json` with a `dev` script. The
  platform runs `pnpm run dev`.
- **Database:** a fresh database per project. The API app's `migrations/*.sql` run first, then its
  `seed/*.sql`, both in file-name order. Seed files carry the demo data and demo users.
- **Environment:** every app gets `PORT`.
  - The `api` app also gets `DATABASE_URL`, `JWT_SECRET` (new for every preview) and
    `PUBLIC_BASE_PATH`. It must answer `GET /health` with 200 once it can reach the database.
  - `web`, `admin` and `pwa` apps (Next.js) get `BASE_PATH`, which must be used as Next's
    `basePath`. They also get `API_URL` (the API's internal address, for server-side calls) and
    `NEXT_PUBLIC_API_URL` (the API's public path, for browser calls).
  - Project secrets set in the Studio are added. The Studio's own keys are never passed to apps.
- **Addresses:** each app is served at `/preview/<project>/<app-id>`. The API is served at
  `/preview/<project>/<api-id>` with that prefix removed before the request reaches it.
- **Limitation:** hot reload over WebSocket does not pass through the preview proxy yet. Reload the
  page to see code changes.

A template that breaks any rule is not listed. The Studio prints the reasons when it starts. The
agent-engine tests (`tests/test_studio_templates.py`) validate every template in this catalogue.
