# M1–M6: from "features" to "any prompt, complete product"

Founder direction, 2026-10-02. These six milestones come before every other task in the queue. The
rest of the queue (templates, domain packs, more features) follows on the same path.

## The goal

Any user, technical or not, describes what they want. The platform builds the right scope, from a
single app to a complete ecosystem, with:
- a **wow UI**;
- **real APIs and a real database**;
- the **most features** the product needs.

The user can then keep customising it.

## What stays

Nothing built so far is removed. Every feature becomes a **tested building block** that the
planner picks:
- sign-in and roles, privacy, lifecycles;
- payments with a ledger, scheduled jobs;
- live updates, notifications and push;
- uploads;
- publishing and safe database updates.

The model writes code freely only for what no block covers, and that code passes the same checks.
The domain library and templates stay as **hints and fast starts**, never as limits.

## The flow a user sees

1. **Prompt.**
2. **Project brief:** one screen, everything pre-filled with smart guesses.
   - What we'll build: the apps detected, plus switches for web, admin, Android/iOS and marketing site.
   - Features: from the catalogue, pre-ticked, with suggestions.
   - Brand: name, logo, colours, style, font.
   - Language(s), currency, time zone.
   - Advanced (hidden): backend language, database.
   - **Use smart defaults:** one click to skip.
3. **Build, with live progress.** Every page, link and API call is checked and repaired before the
   user sees it.
4. **Preview each app.** The phone app opens from a QR code.
5. **Keep customising:** chat edits, click-to-edit, code view, publish.

## Milestones

| | Milestone | Tasks |
|---|---|---|
| **M1** | Quality foundation | PC-124 the phone QR works, PC-122 benchmark, PC-125 check and repair (with PC-116), PC-126 model routing |
| **M2** | Scope and brief | PC-127 scope from the prompt, PC-128 project brief, PC-020 brand kit |
| **M3** | Wow UI | PC-129 model-designed pages, PC-130 design review, PC-050 component kit, PC-131 marketing sites, PC-077 realistic demo data |
| **M4** | Any domain | PC-133 model-planned products for any domain |
| **M5** | Features | R-571 escape hatch, PC-134 reviews, chat, maps, analytics, PC-058 search, PC-059 forms, PC-055 languages |
| **M6** | Speed and customisation | PC-096 instant previews, PC-135 chat edits in seconds, PC-019 click-to-edit |
| **M7** | Native mobile (after M6) | Kotlin/Compose and Swift/SwiftUI, phase "5 Native mobile". Flutter is out. |

## How hallucination is stopped

1. **One source of truth.** The plan, the API contract and the generated client are facts. A page may
   only call what exists, or the type check fails.
2. **Constrained output.** Plans are validated JSON, pages import from an allowed kit, and edits are
   small diffs.
3. **Verify everything.** Type check, build, every link and API call real, contract tests, and a real
   browser walk of every page.
4. **Repair with a budget, then fall back.** The exact error goes back to the model. If it still fails,
   a working version is used and the build report says so.
5. **Honest output.** No invented data, realistic demo data instead, and the report separates "verified"
   from "generated, not verified".

## Models

The platform works with no paid key:
- **Free cloud tiers** (groq, OpenRouter, Gemini) first.
- **Local Ollama** as the fallback.
- **A paid frontier model,** added later, raises quality without code changes.

Honest expectations:

| Setup | Expected result |
|---|---|
| Local Ollama, 5–10 min | A complete, working ecosystem. The model designs the key pages; templates do the rest. |
| Free cloud, about 10–20 min | Better design everywhere, slowed by rate limits. |
| Paid frontier model, about 5–10 min | Wow on every page. |

Templates and domain packs matter most in local mode, because they leave less for a weak model to write.

## Measure of success

The **benchmark** (PC-122) is about 50 varied prompts built end to end after each change. Each one
is scored on:
- builds and runs;
- every page and action works;
- features asked for versus delivered;
- a UI score from screenshots.

A drop in the score blocks the change. "Tasks completed" is not the measure; the benchmark is.

## Competitors, honestly

After M1–M6 the platform should lead on **complete, working business systems**: backend, admin, web
and phone. Emergent, Lovable and Bolt keep an edge in raw UI polish and speed while they use stronger
models. Closing that gap is the model-routing work (PC-126) plus a paid model when available.
