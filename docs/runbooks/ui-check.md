# UI check: every page of a generated app, at phone and desktop width

`scripts/ui-check.mjs` opens a running preview in a headless Chrome and checks every page it can
reach from each app's home, at 390 px and 1360 px. It asks no model anything. For each page it
records:

| Check | Fails when |
|---|---|
| overflow | the page is wider than the screen (sideways scrolling on a phone); the widest elements are named |
| console | a console error or an uncaught exception |
| requests | a request the page made failed, or answered 4xx/5xx |
| images | an image did not load |
| contrast | visible text is below WCAG AA (4.5:1, or 3:1 for large text) |

Every page is screenshotted. `report.md` and `report.json` list every page, pass or fail, and the
script exits 1 when any page fails - a failing page is reported, never hidden. A preview runs the
Next.js dev server, which can drop a page's chunks while it compiles another page; a page whose only
errors are those is loaded once more, and if it is then clean the first error is kept as a note.

## After every preview (PC-106)

Once a preview is ready and its pages are warmed, the Studio runs the check by itself on the apps'
own ports (their API calls routed to the API) and shows the result under the preview. The report
and screenshots are kept in `~/.omnistackai/workspaces/<project>/logs/ui-check/`. It needs Node,
Chrome and `playwright-core`, which `scripts/omnistack.sh up` installs once into
`~/.omnistackai/ui-check` when Chrome is present; without them the Studio says the check was
skipped and why. `OMNISTACKAI_UI_CHECK=0` turns it off.

## Run it by hand

Playwright is never a dependency of the platform. Install `playwright-core` in a scratch folder
(it uses the Chrome already on the machine; `--chrome <path>` for another):

```bash
npm i --prefix "$SCRATCH/pw" playwright-core
UI_CHECK_PASSWORD='<console password>' node scripts/ui-check.mjs --playwright "$SCRATCH/pw" \
  --out "$SCRATCH/ui" --login you@example.com \
  --app web=http://127.0.0.1:4321/preview/<project-id>/web \
  --app admin=http://127.0.0.1:4321/preview/<project-id>/admin
```

`--login` signs in to the console first (a preview is served only to its owner). `--max-pages`
(default 25) bounds each app. Pages are found by following the app's own links, one page per route,
so a list with no records has no link to its detail page; add a record first to check that page too.

## Benchmark

PC-101 ran it on five prompts built through the console - a food delivery app, a clinic, a store, a
team task tracker and a public blog - to show the generated UI improving and never regressing.
Results are in CHANGELOG.md under PC-101.
