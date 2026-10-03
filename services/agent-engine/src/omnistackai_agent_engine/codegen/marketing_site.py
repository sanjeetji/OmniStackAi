"""PC-131: the product's public website - a multi-section marketing site, written from the brief.

When the scope keeps "Public website" (PC-127), the build adds `apps/site`: a Next.js site beside the
product's apps, with a hero, the product's features, how it works, questions and answers, a call to
sign up in the web app, and search-engine metadata (title, description, Open Graph, sitemap, robots).

The words are the model's, the code is the platform's. The model is asked for copy only - a JSON
document checked against a schema (lengths, a fixed icon set) - and the page is a template that
renders it, so the site always compiles and contains no invented code. It is honest: no testimonials,
user counts, ratings or awards, which nobody has given yet. Without a model, or when its answer
does not pass, the copy is written from the plan and the brief.

The site uses the web app's scaffolding exactly (same package.json, so the shared type-check cache
applies) and `brand.json` (PC-020), so a rebrand reaches it too.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ..application_ir import ApplicationIR
from .files import GeneratedFile

#: lucide-react icons the copy may name; anything else becomes Sparkles.
ICONS = ("Sparkles", "Zap", "ShieldCheck", "Clock", "Bell", "CreditCard", "MapPin", "Star", "MessageCircle",
         "BarChart3", "Users", "Calendar", "Search", "Smartphone", "Heart", "Package", "Truck", "Camera",
         "Globe", "Lock", "Rocket", "CheckCircle2", "Layers", "Wand2")
_KEEP = ("package.json", "tsconfig.json", "next.config.mjs", "tailwind.config.ts", "postcss.config.mjs", ".gitignore",
         "app/icon.svg", "lib/utils.ts", "lib/brand.ts", "styles/tokens.css", "app/globals.css", "app/not-found.tsx",
         "app/opengraph-image.tsx")
_FORBIDDEN = re.compile(r"\b(?:testimonials?|trusted by|\d[\d,.]*\s*(?:\+\s*)?(?:users|customers|downloads|reviews|stars)|"
                        r"award|rated \d|#1\b|number one)\b", re.I)


def _clip(value: Any, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def fallback_copy(ir: ApplicationIR, features: list[str] | None = None) -> dict[str, Any]:
    """Copy from the plan alone - plain and true."""
    things = [e.name for e in ir.entities][:6]
    blocks = list(features or [])
    for extra in [f"Manage {name.lower()}s" for name in things] + ["Works on every device", "Your data, kept safe"]:
        if len(blocks) >= 3:
            break
        if extra not in blocks:
            blocks.append(extra)
    return {
        "hero": {"headline": ir.name, "subheadline": _clip(ir.description, 220) or f"{ir.name}, ready when you are.",
                 "cta": "Get started"},
        "features": [{"title": _clip(b, 60), "body": f"{_clip(b, 60)} in one place, on any device.", "icon": ICONS[i % len(ICONS)]}
                     for i, b in enumerate(blocks[:6])],
        "steps": [{"title": "Create your account", "body": "Sign up in a minute."},
                  {"title": "Add what you need", "body": f"Set up your {things[0].lower() + 's' if things else 'records'}."},
                  {"title": "Get going", "body": "Everything updates as you work."}],
        "faq": [{"q": f"What is {ir.name}?", "a": _clip(ir.description, 300) or ir.name},
                {"q": "Does it work on my phone?", "a": "Yes - it works in any browser on phones, tablets and computers."}],
        "cta": {"headline": f"Start using {ir.name}", "body": "Create your account and get going.", "button": "Create an account"},
        "seo": {"title": ir.name, "description": _clip(ir.description, 160) or ir.name},
    }


def validate_copy(data: Any) -> tuple[dict[str, Any] | None, str]:
    """The model's copy, normalised, or the reason it was not usable."""
    if not isinstance(data, dict):
        return None, "not a JSON object"
    try:
        hero, cta, seo = data["hero"], data.get("cta") or {}, data.get("seo") or {}
        copy = {
            "hero": {"headline": _clip(hero["headline"], 80), "subheadline": _clip(hero["subheadline"], 240),
                     "cta": _clip(hero.get("cta") or "Get started", 30)},
            "features": [{"title": _clip(f["title"], 60), "body": _clip(f["body"], 220),
                          "icon": f.get("icon") if f.get("icon") in ICONS else "Sparkles"}
                         for f in data["features"][:6] if isinstance(f, dict)],
            "steps": [{"title": _clip(s["title"], 60), "body": _clip(s["body"], 180)}
                      for s in (data.get("steps") or [])[:4] if isinstance(s, dict)],
            "faq": [{"q": _clip(f["q"], 120), "a": _clip(f["a"], 400)} for f in (data.get("faq") or [])[:6] if isinstance(f, dict)],
            "cta": {"headline": _clip(cta.get("headline") or "Get started today", 80), "body": _clip(cta.get("body"), 200),
                    "button": _clip(cta.get("button") or "Create an account", 30)},
            "seo": {"title": _clip(seo.get("title") or hero["headline"], 60), "description": _clip(seo.get("description") or hero["subheadline"], 160)},
        }
    except (KeyError, TypeError) as error:
        return None, f"missing {error}"
    if not copy["hero"]["headline"] or len(copy["features"]) < 3:
        return None, "it needs a headline and at least three features"
    text = json.dumps(copy)
    if _FORBIDDEN.search(text):
        return None, "it claims testimonials, numbers or awards nobody has given yet"
    return copy, ""


def copy_request(ir: ApplicationIR, prompt: str, features: list[str]) -> str:
    return (
        "Write the copy for the public marketing website of this product. Return JSON only.\n\n"
        f"The product: {prompt[:800]}\nName: {ir.name}\nWhat it stores: {', '.join(e.name for e in ir.entities[:10])}\n"
        f"Features: {', '.join(features) or 'from the description'}\n\n"
        "Write like a sharp product marketer: concrete, benefit-led, short sentences, no buzzwords. Be honest: "
        "no testimonials, no user or download counts, no ratings, no awards - the product is new.\n\n"
        '{"hero": {"headline": "<= 8 words", "subheadline": "one or two sentences", "cta": "<= 3 words"},\n'
        ' "features": [{"title": "...", "body": "one or two sentences", "icon": "<one of: ' + ", ".join(ICONS) + '>"}] (4-6),\n'
        ' "steps": [{"title": "...", "body": "..."}] (3),\n'
        ' "faq": [{"q": "...", "a": "..."}] (4-5),\n'
        ' "cta": {"headline": "...", "body": "...", "button": "<= 3 words"},\n'
        ' "seo": {"title": "<= 60 chars", "description": "<= 155 chars"}}'
    )


async def write_copy(ir: ApplicationIR, prompt: str, features: list[str], provider: Any, model_id: str | None,
                     timeout: float = 120.0) -> tuple[dict[str, Any], str]:
    """(copy, who wrote it): the model's when it passes, else the plan's."""
    if provider is None:
        return fallback_copy(ir, features), "plan"
    import uuid

    from ..codegen.llm_ui import _resolve_target
    from ..model_gateway.contracts import ChatRole, GenerateRequest, Message

    try:
        target, max_output = _resolve_target(provider, model_id)
        response = await provider.generate(GenerateRequest(
            f"site-copy-{uuid.uuid4().hex[:12]}", target,
            (Message(ChatRole.SYSTEM, "You write website copy. Respond with one JSON object only."),
             Message(ChatRole.USER, copy_request(ir, prompt, features))), min(4096, max(1024, max_output)), timeout))
        raw = getattr(response, "text", "") or ""
        match = re.search(r"\{.*\}", raw, re.S)
        copy, why = validate_copy(json.loads(match.group(0)) if match else None)
        if copy is not None:
            return copy, "model"
        return fallback_copy(ir, features), f"plan (the model's copy was not used: {why})"
    except Exception as error:  # noqa: BLE001 - the site is built either way
        return fallback_copy(ir, features), f"plan (the model could not answer: {type(error).__name__})"


_PAGE = r'''import Link from "next/link";
import {
  ArrowRight, BarChart3, Bell, Calendar, Camera, CheckCircle2, Clock, CreditCard, Globe, Heart, Layers, Lock, MapPin,
  MessageCircle, Package, Rocket, Search, ShieldCheck, Smartphone, Sparkles, Star, Truck, Users, Wand2, Zap,
} from "lucide-react";
import copy from "@/content/site.json";
import { brandLogo, brandName } from "@/lib/brand";

// Generated by OmniStackAI (PC-131): the words are in content/site.json - edit them there.
const ICONS = { ArrowRight, BarChart3, Bell, Calendar, Camera, CheckCircle2, Clock, CreditCard, Globe, Heart, Layers, Lock,
  MapPin, MessageCircle, Package, Rocket, Search, ShieldCheck, Smartphone, Sparkles, Star, Truck, Users, Wand2, Zap };
const base = process.env.NEXT_PUBLIC_BASE_PATH || "";
// The product itself: NEXT_PUBLIC_APP_URL once published; in the preview, the web app beside this site.
const appUrl = process.env.NEXT_PUBLIC_APP_URL || (base ? base.replace(/\/site$/, "/web") : "/");

function Icon({ name }: { name: string }) {
  const Glyph = (ICONS as Record<string, typeof Sparkles>)[name] ?? Sparkles;
  return <Glyph className="size-5" aria-hidden="true" />;
}

export default function Home() {
  const name = brandName || copy.hero.headline;
  return (
    <div className="min-h-screen bg-[var(--color-background,#fff)] text-[var(--color-text,#0f172a)]">
      <header className="sticky top-0 z-20 border-b border-black/5 bg-white/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
            <span className="flex size-8 items-center justify-center overflow-hidden rounded-lg bg-[var(--color-primary)] text-sm font-bold text-[var(--color-primary-foreground,#fff)]">
              {brandLogo ? <img src={brandLogo} alt="" className="size-full object-cover" /> : name.slice(0, 1)}
            </span>
            {name}
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-slate-600 sm:flex">
            <a href="#features" className="hover:text-slate-900">Features</a>
            <a href="#how" className="hover:text-slate-900">How it works</a>
            <a href="#faq" className="hover:text-slate-900">Questions</a>
          </nav>
          <a href={appUrl} className="rounded-full bg-[var(--color-primary)] px-4 py-2 text-sm font-medium text-[var(--color-primary-foreground,#fff)] shadow-sm transition hover:opacity-90">
            {copy.hero.cta}
          </a>
        </div>
      </header>

      <section className="relative overflow-hidden">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,var(--color-primary-subtle,#eef2ff),transparent_65%)]" />
        <div className="relative mx-auto max-w-6xl px-5 pb-20 pt-20 text-center sm:pt-28">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-medium text-slate-600 shadow-sm">
            <Sparkles className="size-3.5 text-[var(--color-primary)]" aria-hidden="true" /> {name}
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-balance font-[family-name:var(--font-heading)] text-4xl font-bold tracking-tight sm:text-6xl">
            {copy.hero.headline}
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-pretty text-lg leading-relaxed text-slate-600">{copy.hero.subheadline}</p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <a href={appUrl} className="inline-flex items-center gap-2 rounded-full bg-[var(--color-primary)] px-6 py-3 text-sm font-semibold text-[var(--color-primary-foreground,#fff)] shadow-lg shadow-[var(--color-primary)]/20 transition hover:-translate-y-0.5">
              {copy.hero.cta} <ArrowRight className="size-4" aria-hidden="true" />
            </a>
            <a href="#features" className="rounded-full border border-black/10 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
              See what it does
            </a>
          </div>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-6xl px-5 py-20">
        <h2 className="text-center font-[family-name:var(--font-heading)] text-3xl font-bold tracking-tight">Everything in one place</h2>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {copy.features.map((feature) => (
            <article key={feature.title} className="group rounded-2xl border border-black/5 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
              <span className="flex size-11 items-center justify-center rounded-xl bg-[var(--color-primary-subtle,#eef2ff)] text-[var(--color-primary)]">
                <Icon name={feature.icon} />
              </span>
              <h3 className="mt-4 text-lg font-semibold">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{feature.body}</p>
            </article>
          ))}
        </div>
      </section>

      {copy.steps.length > 0 ? (
        <section id="how" className="border-y border-black/5 bg-slate-50/70">
          <div className="mx-auto max-w-6xl px-5 py-20">
            <h2 className="text-center font-[family-name:var(--font-heading)] text-3xl font-bold tracking-tight">How it works</h2>
            <ol className="mt-12 grid gap-6 sm:grid-cols-3">
              {copy.steps.map((step, index) => (
                <li key={step.title} className="rounded-2xl bg-white p-6 shadow-sm">
                  <span className="flex size-9 items-center justify-center rounded-full bg-[var(--color-primary)] text-sm font-bold text-[var(--color-primary-foreground,#fff)]">
                    {index + 1}
                  </span>
                  <h3 className="mt-4 font-semibold">{step.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>
      ) : null}

      {copy.faq.length > 0 ? (
        <section id="faq" className="mx-auto max-w-3xl px-5 py-20">
          <h2 className="text-center font-[family-name:var(--font-heading)] text-3xl font-bold tracking-tight">Questions</h2>
          <div className="mt-10 divide-y divide-black/5 rounded-2xl border border-black/5 bg-white">
            {copy.faq.map((item) => (
              <details key={item.q} className="group px-6 py-4">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium">
                  {item.q}
                  <span className="text-slate-400 transition group-open:rotate-45">+</span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-slate-600">{item.a}</p>
              </details>
            ))}
          </div>
        </section>
      ) : null}

      <section className="px-5 pb-24">
        <div className="mx-auto max-w-5xl overflow-hidden rounded-3xl bg-[var(--color-primary)] px-8 py-14 text-center text-[var(--color-primary-foreground,#fff)] shadow-xl">
          <h2 className="font-[family-name:var(--font-heading)] text-3xl font-bold tracking-tight">{copy.cta.headline}</h2>
          {copy.cta.body ? <p className="mx-auto mt-3 max-w-xl text-white/85">{copy.cta.body}</p> : null}
          <a href={appUrl} className="mt-8 inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-900 transition hover:-translate-y-0.5">
            {copy.cta.button} <ArrowRight className="size-4" aria-hidden="true" />
          </a>
        </div>
      </section>

      <footer className="border-t border-black/5">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-8 text-sm text-slate-500">
          <span>© {new Date().getFullYear()} {name}</span>
          <a href={appUrl} className="hover:text-slate-800">Open the app</a>
        </div>
      </footer>
    </div>
  );
}
'''


def _layout(ir: ApplicationIR, copy: dict[str, Any]) -> str:
    title = json.dumps(copy["seo"]["title"] or ir.name)
    description = json.dumps(copy["seo"]["description"] or ir.description)
    return (
        'import type { Metadata } from "next";\n'
        'import "./globals.css";\n'
        'import { brandCss } from "@/lib/brand";\n\n'
        f'export const viewport = {{ themeColor: "{ir.brand.primary_color}" }};\n\n'
        "export const metadata: Metadata = {\n"
        '  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"),\n'
        f"  title: {title},\n  description: {description},\n"
        f"  openGraph: {{ title: {title}, description: {description}, type: \"website\" }},\n"
        f"  twitter: {{ card: \"summary_large_image\", title: {title}, description: {description} }},\n"
        '  alternates: { canonical: "/" },\n'
        "};\n\n"
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return (\n"
        '    <html lang="en">\n'
        "      <head>\n"
        '        <style dangerouslySetInnerHTML={{ __html: brandCss() }} />\n'
        "      </head>\n"
        '      <body style={{ margin: 0, fontFamily: "var(--font-sans, system-ui, -apple-system, sans-serif)" }}>{children}</body>\n'
        "    </html>\n"
        "  );\n"
        "}\n"
    )


_SITEMAP = '''import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  return [{ url: `${site}/`, changeFrequency: "weekly", priority: 1 }];
}
'''
_ROBOTS = '''import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  return { rules: [{ userAgent: "*", allow: "/" }], sitemap: `${site}/sitemap.xml` };
}
'''


def site_files(ir: ApplicationIR, copy: dict[str, Any]) -> list[GeneratedFile]:
    """apps/site: the web app's scaffolding, and the marketing pages around the copy."""
    from .nextjs import NextjsWebAdapter

    web = {f.path: f for f in NextjsWebAdapter().generate(ir).files()}
    files = [GeneratedFile(f"apps/site/{path}", web[path].content) for path in _KEEP if path in web]
    package = json.loads(web["package.json"].content)
    package["name"] = re.sub(r"-web$|$", "-site", package.get("name", "site"), count=1)
    files = [f if not f.path.endswith("/package.json") else GeneratedFile(f.path, json.dumps(package, indent=2) + "\n")
             for f in files]
    files += [
        GeneratedFile("apps/site/content/site.json", json.dumps(copy, indent=2) + "\n"),
        GeneratedFile("apps/site/app/layout.tsx", _layout(ir, copy)),
        GeneratedFile("apps/site/app/page.tsx", _PAGE),
        GeneratedFile("apps/site/app/sitemap.ts", _SITEMAP),
        GeneratedFile("apps/site/app/robots.ts", _ROBOTS),
        GeneratedFile("apps/site/README.md", f"# {ir.name} - website\n\nThe public website. The words are in "
                      "`content/site.json`; the look comes from the project's `brand.json`.\n"),
    ]
    return files
