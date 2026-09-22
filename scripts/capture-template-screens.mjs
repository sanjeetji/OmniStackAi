#!/usr/bin/env node
// Capture a screenshot of every page of a template's apps (Phase T, R-530).
//
// The template drives the capture with its own plan, templates/catalog/<slug>/capture.mjs, which
// signs in as its demo users, stages live scenes through the API (a booking, an offer, ...) and
// calls `shot()` for each page. This runner provides the browser and writes:
//   <template>/media/<app>/<name>.jpg   one image per page
//   <template>/media/screens.json       the list, with app, route, title and description
//
// Playwright is never a dependency of the platform or of a template. Install it in a scratch
// folder and point this script at it:
//   npm i --prefix "$SCRATCH/pw" playwright && npx --prefix "$SCRATCH/pw" playwright install chromium-headless-shell
//   node scripts/capture-template-screens.mjs --template templates/catalog/_ride-now \
//     --playwright "$SCRATCH/pw" --api http://127.0.0.1:4000 \
//     --app rider=http://127.0.0.1:3101 --app driver=http://127.0.0.1:3102 --app admin=http://127.0.0.1:3103
//
// The apps must already be running against a freshly seeded database (see the template README).

import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { pathToFileURL } from "node:url";

function parseArgs(argv) {
  const args = { apps: {}, only: null };
  for (let i = 0; i < argv.length; i += 1) {
    const [key, value] = [argv[i], argv[i + 1]];
    if (key === "--template") args.template = value;
    else if (key === "--playwright") args.playwright = value;
    else if (key === "--api") args.api = value.replace(/\/$/, "");
    else if (key === "--out") args.out = value;
    else if (key === "--only") args.only = value;
    else if (key === "--app") {
      const [id, url] = value.split("=");
      args.apps[id] = url.replace(/\/$/, "");
    } else continue;
    i += 1;
  }
  for (const required of ["template", "playwright", "api"]) {
    if (!args[required]) throw new Error(`--${required} is required (see the header of this script)`);
  }
  return args;
}

const DEVICES = {
  desktop: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
  phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
};

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const templateDir = path.resolve(args.template);
  const outDir = path.resolve(args.out ?? path.join(templateDir, "media"));
  const require = createRequire(path.join(path.resolve(args.playwright), "package.json"));
  const { chromium } = require("playwright");
  const plan = await import(pathToFileURL(path.join(templateDir, "capture.mjs")).href);

  const browser = await chromium.launch();
  const sessions = new Map();
  const contexts = new Map();
  const screens = [];
  let failures = 0;

  async function call(as, method, route, body) {
    const headers = { "Content-Type": "application/json" };
    if (as) headers.Authorization = `Bearer ${(await session(as)).access_token}`;
    const response = await fetch(`${args.api}${route}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) throw new Error(`${method} ${route} as ${as ?? "anonymous"}: ${response.status} ${data?.error ?? text}`);
    return data;
  }

  async function session(as) {
    if (!sessions.has(as)) {
      const user = plan.users[as];
      if (!user) throw new Error(`capture.mjs has no user ${as}`);
      sessions.set(as, await call(null, "POST", "/auth/login", { email: user.email, password: user.password, role: user.role }));
    }
    return sessions.get(as);
  }

  // One browser context per (app, device, signed-in user), so local storage sessions never mix.
  async function contextFor(app, device, as) {
    const key = `${app}|${device}|${as ?? ""}`;
    if (!contexts.has(key)) {
      const context = await browser.newContext({ ...DEVICES[device], locale: "en-IN", timezoneId: "Asia/Kolkata", colorScheme: "light" });
      if (as) {
        const stored = JSON.stringify(await session(as));
        const storageKey = plan.storageKeys[app];
        await context.addInitScript(([k, v]) => window.localStorage.setItem(k, v), [storageKey, stored]);
      }
      contexts.set(key, context);
    }
    return contexts.get(key);
  }

  async function settle(page, waitFor) {
    await page.waitForLoadState("load");
    if (waitFor) await page.waitForSelector(waitFor, { timeout: 15_000 });
    // Pages keep an SSE stream open, so "network idle" never happens; wait for skeletons instead.
    await page
      .waitForFunction(() => !document.querySelector(".animate-pulse, [aria-busy='true']"), null, { timeout: 12_000 })
      .catch(() => undefined);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(700);
  }

  async function open(options) {
    const { app, route, device = "desktop", as = null } = options;
    const base = args.apps[app];
    if (!base) throw new Error(`no --app ${app}=<url> given`);
    const context = await contextFor(app, device, as);
    const page = await context.newPage();
    await page.goto(`${base}${route}`, { waitUntil: "domcontentloaded", timeout: 60_000 });
    await settle(page, options.waitFor);
    return page;
  }

  async function shot(options) {
    const { app, name, title, description, route, device = "desktop", fullPage = true, highlight = false } = options;
    if (args.only && !`${app}/${name}`.includes(args.only)) return;
    const file = path.join(outDir, app, `${name}.jpg`);
    let page;
    try {
      page = options.page ?? (await open(options));
      if (options.prepare) await options.prepare(page);
      await mkdir(path.dirname(file), { recursive: true });
      // Grow the viewport to the page instead of using fullPage: a sticky sidebar, a bottom tab
      // bar or a fixed sheet then covers the whole image, as it does on a tall screen.
      const size = page.viewportSize();
      if (fullPage) {
        const height = await page.evaluate(() => document.documentElement.scrollHeight);
        const target = Math.min(2600, Math.max(size.height, height));
        if (target !== size.height) {
          await page.setViewportSize({ width: size.width, height: target });
          await page.waitForTimeout(600);
        }
      }
      await page.screenshot({ path: file, type: "jpeg", quality: 72, animations: "disabled" });
      screens.push({ app, title, description, route: options.displayRoute ?? route, device, highlight, image: path.relative(templateDir, file).split(path.sep).join("/") });
      console.log(`  ✓ ${app}/${name}  ${title}`);
    } catch (error) {
      failures += 1;
      console.error(`  ✗ ${app}/${name}: ${error.message.split("\n")[0]}`);
    } finally {
      if (page && !options.page) await page.close();
    }
  }

  /** Render an HTML composition (for example the cover) to a JPEG. */
  async function render(html, { file, width, height }) {
    const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    await page.setContent(html, { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    const target = path.join(outDir, file);
    await mkdir(path.dirname(target), { recursive: true });
    await page.screenshot({ path: target, type: "jpeg", quality: 80 });
    await context.close();
    console.log(`  ✓ ${file}`);
  }

  const image = async (relative) => `data:image/jpeg;base64,${(await readFile(path.join(templateDir, relative))).toString("base64")}`;

  console.log(`Capturing ${path.basename(templateDir)} into ${path.relative(process.cwd(), outDir)}`);
  try {
    await plan.default({ api: call, session, open, shot, render, image, sleep: (ms) => new Promise((r) => setTimeout(r, ms)) });
  } finally {
    await browser.close();
  }
  if (!args.only) {
    await writeFile(path.join(outDir, "screens.json"), `${JSON.stringify(screens, null, 2)}\n`);
  }
  console.log(`${screens.length} screens captured, ${failures} failed.`);
  if (failures) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
