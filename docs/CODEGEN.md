# Code generation boundary (Brief §16/§17/§46/§75)

Code generation turns an **Application IR** into a customer project's source. The boundary is pure and
deterministic: adapters produce an in-memory file-set; nothing is written to disk or executed here (a
later Git-service task materializes it).

Package: `omnistackai_agent_engine.codegen` (standard library only; depends on `application_ir`).

## Pieces

- **`GeneratedFile`** — one `path` → `content` record. The path is validated as a safe relative POSIX
  path: no absolute paths, no `..` traversal, no backslashes or control characters, bounded length,
  each segment `[A-Za-z0-9._-]`. Optional `executable` flag. Content is a bounded string.
- **`GeneratedProject`** — an immutable, **deterministically ordered** (sorted by path) set of
  `GeneratedFile`s for one `target`. Duplicate paths raise `DuplicateFileError`. Exposes `get`,
  `paths`, `files`, `__len__`, and `merge` (same target only).
- **`FrameworkAdapter`** — the runtime-checkable contract every generator implements:
  `target: GenerationTarget` and `generate(ir) -> GeneratedProject`.
- **`AdapterRegistry`** — registers adapters by target; product/agent code selects an adapter only via
  the registry (`get(target)`), never a concrete class. Stable `DuplicateAdapterError` /
  `UnsupportedTargetError`.
- **`GenerationTarget`** — bounded enum: `nextjs-web`, `nextjs-admin`, `backend-go`, `backend-python`,
  `backend-node`, `flutter`, `react-native`, `native-android`, `native-ios`.

## Why in-memory and deterministic

Generation is a pure function `IR → GeneratedProject`, so it is fully unit-testable offline by
asserting emitted file paths and contents — no install, no build, no disk. This keeps generation
reproducible and diffable before anything is written to a customer repo (R-228).

## First adapter: Next.js web (R-227)

`NextjsWebAdapter` (target `nextjs-web`) turns an Application IR into a real Next.js App Router
TypeScript project:

- **Config:** `package.json` (next/react), `tsconfig.json`, `next.config.mjs` with security headers,
  `.gitignore`, `.env.example` (placeholders only), `README.md`.
- **Types:** each IR entity → a TypeScript interface in `lib/types.ts` (field-type mapping;
  non-required fields become optional; relations become typed references, `[]` for to-many).
- **APIs:** each IR API → an App Router `route.ts` handler, grouped one file per route directory, with
  `{param}` mapped to Next's `[param]` dynamic segment and one exported `GET/POST/...` per method
  (scaffolded to a `501 not_implemented` response for now).
- **Screens:** each IR screen → an `app/<id>/page.tsx`; `app/page.tsx` is an overview of the app,
  entities, and screens.

The file-path validator (`GeneratedFile`) allows framework route filename characters (`[]()@+`) so
Next.js/Expo route conventions are valid, while still rejecting absolute paths, `..`, backslashes, and
control characters. The generated project is what a Next.js toolchain would install and build; this
platform verifies it offline by asserting the emitted files (no install/build here).

## Second adapter: Python backend (R-229)

`PythonBackendAdapter` (target `backend-python`) turns an Application IR into a real FastAPI backend:

- **Models:** each entity → a Pydantic model in `app/models.py` (types mapped; non-required fields
  become `Optional[...] = None`).
- **Routes:** IR APIs → FastAPI routes grouped into `app/routers/<segment>.py` by first path segment;
  `{param}` path params become typed function arguments; scaffold bodies raise `501 not_implemented`.
- **App:** `app/main.py` includes each router and a `/healthz` endpoint; plus `app/config.py`,
  `requirements.txt`, `README.md`, `.gitignore`, `.env.example` (placeholders only).

With R-227 (web) and R-229 (backend) registered together, **one Application IR emits web + backend
together** — the multi-target differentiator. Both are pure/offline: verified by asserting emitted
files; the Git service (R-228) materializes either into a customer-owned repo.
