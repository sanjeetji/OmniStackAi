# The brand kit

Every generated project has one place that defines how it looks: `brand.json` at the root of the
project. Every app follows it: the web app, the admin console and the phone app.

## Changing it in the Studio

Open the project and press **Brand**, next to Publish. You can change:

| Setting | What it changes |
|---|---|
| Name | The product's name in every app's header and pages, the phone app's name, and the project's name in the console |
| Logo (PNG or SVG, up to 512 KB) | Every web app's header, the browser-tab icon, and the phone app's home-screen icon (PNG only; an SVG keeps the generated phone icon) |
| Main colour, accent colour | The whole palette, light and dark, derived from them |
| Text font, heading font | Typography in every app (Google Fonts) |
| Corners | From square to very round |
| Style | The design direction later page design follows |

Press **Save brand**. The change is committed to the project's history, and the running preview
follows it without a rebuild. If the project is busy, for example while its pages are being
designed, the change is kept and saved as soon as the project is free.

The platform's own icons are regenerated. An icon you replaced by hand in the code is never
overwritten.

## Changing it in the code

Edit `brand.json` and run `pnpm run brand` to regenerate the icons. See `brand/README.md` in the
project. Colours, fonts and corners need no regeneration: the apps read them when they render.
