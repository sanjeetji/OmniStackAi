import type { CSSProperties } from "react";

/** Inline style for a `.reveal` element: sets `--reveal-index`, which the stylesheet turns
 * into a 60ms-per-step animation delay (see `.reveal` in globals.css). Motion is transform +
 * opacity only and is collapsed entirely under `prefers-reduced-motion`. */
export function revealStyle(index: number): CSSProperties {
  return { "--reveal-index": index } as CSSProperties;
}
