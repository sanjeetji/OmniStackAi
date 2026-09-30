#!/usr/bin/env node
// The UI quality check for a generated app (PC-101): every page, at phone and desktop width,
// screenshotted and checked. Deterministic - no model is asked anything.
//
// For each app of a preview it starts at the app's home, follows the app's own links (same app,
// one page per route, at most --max-pages pages) and on every page, at 390 px and 1360 px, records:
//   overflow     the page is wider than the screen (horizontal scrolling on a phone)
//   console      console errors and uncaught exceptions
//   requests     requests the page made that failed or answered 4xx/5xx
//   images       images that did not load
//   contrast     text below WCAG AA contrast (4.5:1, or 3:1 for large text)
// and saves a screenshot. It writes report.json and report.md to --out and exits 1 when any page
// fails, so a failing page is reported, never hidden.
//
// Playwright is never a dependency of the platform. Install playwright-core in a scratch folder;
// the check drives the Chrome already on this machine (or --chrome <path>):
//   npm i --prefix "$SCRATCH/pw" playwright-core
//   node scripts/ui-check.mjs --playwright "$SCRATCH/pw" --out "$SCRATCH/ui" \
//     --login you@example.com:password --app web=http://127.0.0.1:4321/preview/<id>/web \
//     --app admin=http://127.0.0.1:4321/preview/<id>/admin
// --login signs in to the console first (previews are served only to their owner). The password
// can come from UI_CHECK_PASSWORD instead, so it never appears in the process list.

import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const DEVICES = {
  phone: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  desktop: { viewport: { width: 1360, height: 900 }, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
};
const CHROME = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
];

function parseArgs(argv) {
  const args = { apps: [], maxPages: 25, out: "ui-check" };
  for (let i = 0; i < argv.length; i += 2) {
    const [key, value] = [argv[i], argv[i + 1]];
    if (key === "--playwright") args.playwright = value;
    else if (key === "--chrome") args.chrome = value;
    else if (key === "--out") args.out = value;
    else if (key === "--max-pages") args.maxPages = Number(value);
    else if (key === "--login") args.login = value;
    else if (key === "--app") {
      const at = value.indexOf("=");
      args.apps.push({ id: value.slice(0, at), url: value.slice(at + 1).replace(/\/$/, "") });
    } else throw new Error(`unknown option ${key}`);
  }
  if (!args.playwright || !args.apps.length) throw new Error("--playwright and at least one --app are required (see the header)");
  return args;
}

/** Runs in the page: what the eye would catch. */
function inspect() {
  const width = window.innerWidth;
  const overflow = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0) - width;
  const wide = [];
  if (overflow > 1) {
    for (const el of document.querySelectorAll("body *")) {
      const box = el.getBoundingClientRect();
      if (box.right > width + 1 && box.width > 0 && getComputedStyle(el).position !== "fixed") {
        wide.push(`${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}${el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : ""} (right ${Math.round(box.right)}px)`);
        if (wide.length >= 3) break;
      }
    }
  }
  const images = [...document.images]
    .filter((img) => img.complete && img.naturalWidth === 0 && img.getBoundingClientRect().width > 0)
    .map((img) => img.currentSrc || img.src)
    .slice(0, 5);

  const rgba = (value) => {
    const m = value.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const [r, g, b, a = 1] = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
    return [r, g, b, a];
  };
  const luminance = ([r, g, b]) => {
    const c = [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const background = (el) => {
    for (let node = el; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.backgroundImage && style.backgroundImage !== "none") return null; // gradient or image: cannot judge
      const bg = rgba(style.backgroundColor);
      if (bg && bg[3] >= 0.99) return bg;
      if (bg && bg[3] > 0.01) return null; // translucent layers: cannot judge reliably
    }
    return [255, 255, 255, 1];
  };
  const lowContrast = [];
  const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode() && lowContrast.length < 5) {
    const text = walker.currentNode.textContent.trim();
    const el = walker.currentNode.parentElement;
    if (!text || !el || seen.has(el)) continue;
    seen.add(el);
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    if (!box.width || !box.height || style.visibility === "hidden" || Number(style.opacity) < 0.5) continue;
    // Off-screen (a closed drawer) or a lone symbol such as a breadcrumb "/" is not read as text.
    if (box.right <= 0 || box.left >= width || !/[A-Za-z0-9]/.test(text)) continue;
    if (el.closest("[disabled],[aria-disabled='true'],[aria-hidden='true'],.sr-only,svg")) continue;
    const fg = rgba(style.color);
    const bg = background(el);
    if (!fg || !bg || fg[3] < 0.99) continue;
    const [hi, lo] = [luminance(fg), luminance(bg)].sort((x, y) => y - x);
    const ratio = (hi + 0.05) / (lo + 0.05);
    const size = parseFloat(style.fontSize);
    const large = size >= 24 || (size >= 18.66 && Number(style.fontWeight) >= 700);
    if (ratio < (large ? 3 : 4.5)) lowContrast.push(`"${text.slice(0, 40)}" ${ratio.toFixed(2)}:1`);
  }
  const links = [...document.querySelectorAll("a[href]")].map((a) => a.href);
  return { overflow: overflow > 1 ? overflow : 0, wide, images, lowContrast, links, title: document.title };
}

// The dev server's own chunks, and the dev overlay's requests after an error (sent to the site
// root, whatever the base path): never the app's.
const DEV_COMPILE = /\/_next\/static\/|ChunkLoadError|Loading chunk|\/__nextjs_/;

/** Open one page on one device and list what is wrong with it. The caller closes the context. */
async function view(browser, url, options, storageState, shotPath) {
  const context = await browser.newContext({ ...options, storageState });
  const page = await context.newPage();
  const consoleErrors = [];
  const failed = [];
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const where = msg.location()?.url;
    consoleErrors.push(`${msg.text().slice(0, 200)}${where ? ` (${where})` : ""}`);
  });
  page.on("pageerror", (err) => consoleErrors.push(`uncaught: ${String(err).slice(0, 200)}`));
  page.on("requestfailed", (req) => {
    const reason = req.failure()?.errorText || "failed";
    if (!/ERR_ABORTED/.test(reason)) failed.push(`${req.method()} ${req.url()} (${reason})`);
  });
  page.on("response", (res) => { if (res.status() >= 400) failed.push(`${res.request().method()} ${res.url()} -> ${res.status()}`); });
  let status = 0;
  try {
    const response = await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
    status = response?.status() ?? 0;
  } catch (err) {
    consoleErrors.push(`navigation: ${String(err).slice(0, 160)}`);
  }
  await page.waitForTimeout(800);
  const found = await page.evaluate(inspect).catch(() => ({ overflow: 0, wide: [], images: [], lowContrast: [], links: [], title: "" }));
  await page.screenshot({ path: shotPath, fullPage: true }).catch(() => {});
  const problems = [];
  if (status >= 400) problems.push(`page answered ${status}`);
  if (found.overflow) problems.push(`${found.overflow}px wider than the screen: ${found.wide.join(", ")}`);
  for (const e of consoleErrors) problems.push(`console: ${e}`);
  for (const f of failed) problems.push(`request: ${f}`);
  for (const i of found.images) problems.push(`image did not load: ${i}`);
  for (const c of found.lowContrast) problems.push(`low contrast: ${c}`);
  return { context, found, problems };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const require = createRequire(path.join(path.resolve(args.playwright), "package.json"));
  const { chromium } = require("playwright-core");
  const executablePath = args.chrome ?? CHROME.find((candidate) => existsSync(candidate));
  const browser = await chromium.launch({ executablePath });
  const out = path.resolve(args.out);
  await mkdir(path.join(out, "shots"), { recursive: true });

  let storageState;
  if (args.login) {
    const at = args.login.indexOf(":");
    const email = at > 0 ? args.login.slice(0, at) : args.login;
    const password = at > 0 ? args.login.slice(at + 1) : process.env.UI_CHECK_PASSWORD;
    const origin = new URL(args.apps[0].url).origin;
    const context = await browser.newContext();
    const answer = await context.request.post(`${origin}/api/auth/login`, { data: { email, password } });
    if (!answer.ok()) throw new Error(`console sign-in failed (${answer.status()})`);
    storageState = await context.storageState();
    await context.close();
  }

  const results = [];
  for (const app of args.apps) {
    const base = new URL(app.url);
    // One page per route: a list's many "?id=" links are one detail page, checked once.
    const queue = [app.url];
    const visited = new Set();
    const routeOf = (href) => new URL(href).pathname.replace(/\/$/, "");
    while (queue.length && visited.size < args.maxPages) {
      const url = queue.shift();
      if (visited.has(routeOf(url))) continue;
      visited.add(routeOf(url));
      for (const [device, options] of Object.entries(DEVICES)) {
        const route = new URL(url).pathname.slice(base.pathname.length) || "/";
        const shot = `${app.id}${route.replace(/[^a-z0-9]+/gi, "-").replace(/-$/, "") || "-home"}-${device}.png`;
        let { context, found, problems } = await view(browser, url, options, storageState, path.join(out, "shots", shot));
        // A dev server compiling another page can drop the chunks this one asked for (a 404 under
        // /_next/, a ChunkLoadError) or answer the page itself 404 mid-compile. That is the dev
        // server, not the app: the page is loaded once more, and if it is then clean the first
        // failure is kept in the report as a note. A real 404 is a 404 again, and fails.
        let notes = [];
        const devOnly = (p) => DEV_COMPILE.test(p) || p === "page answered 404" || (p.includes(url) && /404/.test(p));
        if (problems.length && problems.every(devOnly)) {
          await context.close();
          notes = problems.map((p) => `transient (dev server compiling, clean on reload): ${p}`);
          ({ context, found, problems } = await view(browser, url, options, storageState, path.join(out, "shots", shot)));
          if (problems.length) notes = [];
        }
        results.push({ app: app.id, route, device, title: found.title, shot: `shots/${shot}`, problems, notes });
        if (device === "desktop") {
          for (const link of found.links) {
            const next = new URL(link);
            next.hash = "";
            if (next.origin === base.origin && next.pathname.startsWith(base.pathname) && !visited.has(routeOf(next.href))) {
              queue.push(next.href);
            }
          }
        }
        await context.close();
      }
    }
  }
  await browser.close();

  const failing = results.filter((r) => r.problems.length);
  await writeFile(path.join(out, "report.json"), JSON.stringify({ pages: results.length, failing: failing.length, results }, null, 2));
  const md = [`# UI check`, "", `${results.length} page views (${results.length / 2} pages at phone and desktop width); ${failing.length} with problems.`, ""];
  for (const r of results) {
    md.push(`- ${r.problems.length ? "FAIL" : "ok"} **${r.app}${r.route}** (${r.device}) - [screenshot](${r.shot})`);
    for (const p of r.problems) md.push(`  - ${p}`);
    for (const n of r.notes) md.push(`  - note: ${n}`);
  }
  await writeFile(path.join(out, "report.md"), md.join("\n") + "\n");
  const noted = results.filter((r) => r.notes.length).length;
  if (noted) md.splice(3, 0, `${noted} page views had a transient dev-server error and were clean on reload (listed as notes).`, "");
  console.log(md.slice(0, 5).join("\n"));
  for (const r of failing) console.log(`FAIL ${r.app}${r.route} (${r.device}): ${r.problems.slice(0, 3).join(" | ")}`);
  process.exit(failing.length ? 1 : 0);
}

main().catch((err) => {
  console.error(String(err));
  process.exit(2);
});
