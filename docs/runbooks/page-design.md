# Model-designed pages

After a build, the platform asks the model to design the product's pages. The preview runs on the
built-in templates while this happens, and each page switches over as soon as it is ready.

## What is designed

- **Web and admin apps:** every app's home page first, then every screen.
- **Phone apps:** the home screen first, then every list screen. Each one is redesigned from its
  working template, so it keeps the same data, navigation and exports.

The default is every page. `OMNISTACKAI_PAGE_DESIGN_MAX_PAGES` lowers the cap, and
`OMNISTACKAI_PAGE_DESIGN=off` turns page design off. A run stops starting new pages after 40 minutes,
set by `OMNISTACKAI_PAGE_DESIGN_TIME_BUDGET`. The pages it did not reach keep their templates.

## Why a designed page never breaks the app

1. **It is grounded.** The model is given the app's data layer, design system and brand. Pages may
   import only an allowed set of packages. Phone screens may use only React Native, React
   Navigation, safe-area, the icon set, and the app's own modules and design-system kit.
2. **It is checked.** Every page is type-checked with the app's own TypeScript, using the shared
   caches that `./scripts/omnistack.sh up` prepares. Links must go to real pages, and text must not
   be set in a background colour (see PC-125).
3. **It is repaired, or put back.** A page that fails gets repaired from the compiler's own errors.
   If it still fails, or cannot be checked at all, it goes back to its template.

The build report lists every page as designed or kept as template, with the reason.

## Which model designs

The page chain is set out in [model-routing.md](model-routing.md). A paid key leads it once it is
set. Otherwise the free tiers design the pages, and local Ollama is the last resort.
