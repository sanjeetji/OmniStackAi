# Current Handoff

Task ID: R-363
Status: done
Phase: BASIC/MVP — Founder Stage 0
Branch: `main` (the only branch; the GitHub default)

## Repo/workflow state

- **Code clean and verified on `main`**.
- Tracker and state files kept fully consistent and verified.
- Resume from **R-364** when ready. Still stop-and-ask only for paid cloud / DB engine / new infra / native-mobile / a materially different architecture decision.

## Completed

### R-363 — Generated Accessible Futuristic Reusable Tour & Onboarding Spotlight Guide Suite (components/tour.tsx)

Enabled accessible, desktop-and-mobile-grade, futuristic tour and onboarding spotlight guide compound components across generated Next.js web applications:

- **Standalone Tour Suite (`apps/web/components/tour.tsx`)**:
  - Implemented `TourVariant` (`"default"` | `"card"` | `"glass"` | `"neon"`), `TourSize` (`"sm"` | `"md"` | `"lg"`), `TourPlacement` (`"top"` | `"bottom"` | `"left"` | `"right"` | `"center"`), `TourStep`, and `TourProps` interfaces.
  - Implemented compound exports: `Tour`, `TourStepDot`, `TourProgressBadge`, `TourCloseButton`.
  - Implemented dynamic target element bounding box lookup via `getBoundingClientRect()` with scroll and resize listeners and target scroll-into-view.
  - Implemented full-screen SVG cutout spotlight mask (`<mask id="...">` with `<rect fill="white"/>` and `<rect fill="black"/>`) over semi-transparent overlay backdrop.
  - Implemented floating card popover with auto placement resolution, edge clamping against `window.innerWidth`/`innerHeight`, and directional SVG arrow pointer notch.
  - Implemented step navigation controls: Previous, Next, Finish, Skip, and Close buttons.
  - Implemented step dots indicators with jump-to-step support and active pill state.
  - Implemented step counter badge ("X of Y").
  - Implemented full WAI-ARIA 1.2 dialog semantics (`role="dialog"`, `aria-modal="true"`, `aria-label`, `aria-describedby`).
  - Implemented full keyboard navigation (`Escape` to dismiss, `ArrowRight`/`Enter` to advance, `ArrowLeft` to go back, Tab trapping).
  - Implemented full React ref forwarding (`forwardRef`) and explicit `Tour.displayName = "Tour"`.
  - Exported `render_tour_component` in `omnistackai_agent_engine.codegen` and registered `components/tour.tsx` in `NextjsWebAdapter.generate()`.
  - Maintained 100% diff-invariance across `ir.description`.

## Verification

- `task verify` — pass (**1,838** agent-engine tests; 26 focused R-362 tests in `test_sidebar_component.py`).
- `task lint`, `task security:quick` — pass.
- `task builder:demo minimal-blog` — pass (99 files).
