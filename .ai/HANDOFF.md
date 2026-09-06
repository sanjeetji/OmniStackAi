# Current Handoff

Task ID: R-227
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `ai/R-227-nextjs-adapter`
Last verified implementation SHA: `1a4f8a9b8cc2ca59be32142bb6c16992cb4dbd40`

## Completed — the platform now generates a real app

- `NextjsWebAdapter` (`codegen/nextjs.py`, target `nextjs-web`) turns an Application IR into a real
  Next.js App Router TypeScript project as a `GeneratedProject`:
  - entities → TypeScript interfaces (`lib/types.ts`; optional fields, typed relations),
  - IR APIs → App Router `route.ts` handlers, `{param}` → `[param]`, one file per route dir, a handler
    per method,
  - screens → `app/<id>/page.tsx`; `app/page.tsx` overview,
  - `package.json`, `tsconfig.json`, `next.config.mjs` (security headers), `README.md`, `.gitignore`,
    `.env.example` (placeholders only).
- Extended the `GeneratedFile` path validator to allow framework route filename chars (`[]()@+`) while
  still rejecting absolute paths, `..`, backslashes, and control chars.
- Pure/deterministic; nothing installed/built/run/written to disk. The demo IR emits a **13-file**
  Next.js project.

## Verification

- `task verify` — pass (134 agent-engine tests; 9 new). `task agent-engine:lint`, `task security:quick` — pass.
- Compose unchanged; offline `task bootstrap` unchanged.
- Tracker — R-227 (Product) at `Phase_Roadmap!A9:M9` (rows 9..234 shifted to 10..235, ranges extended);
  no ID lost; MVP total 122, Done 16; chart/styles/workbook byte-identical; zip verified.

## Product roadmap (vertical slice toward an Emergent-class builder)

1. R-225 Application IR — done.
2. R-226 framework adapter contract + file-set — done.
3. R-227 Next.js web adapter (IR → real app) — done.
4. **R-228 (next)** Git service v1 — materialize a `GeneratedProject` to disk as a customer-owned repo
   with an initial commit (offline; `git` is available). This completes the first end-to-end builder
   slice: IR → generated app → owned Git repo.
5. Later (needs a cloud/network env): sandbox run → instant browser preview → deploy; plus the deferred
   R-224 Next.js console upgrade.

## Next action

Proceed to **R-228** — Git service v1: write a `GeneratedProject` to a target directory as a real Git
repository (init, add, commit) with the customer as owner, verified offline by inspecting the
materialized tree and commit. Native mobile stays deferred per Brief §25/§91.

## Next command

`task ai:status`
