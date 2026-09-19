import { cn } from "@/lib/utils";

/** The product mark: a dark rounded square with the amber stacked-layers glyph, matching
 * `app/icon.svg`. Purely decorative wherever it appears next to the wordmark, so it is hidden
 * from assistive tech by default; pass a `title` to make it a labelled image instead. */
export default function BrandMark({
  className,
  title,
}: Readonly<{ className?: string; title?: string }>) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={cn("shrink-0", className)}
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      <rect width="32" height="32" rx="8" className="fill-foreground" />
      <path d="M16 7.5 24.5 12 16 16.5 7.5 12Z" className="fill-brand" />
      <path
        d="M7.5 16.5 16 21l8.5-4.5M7.5 20.5 16 25l8.5-4.5"
        className="stroke-brand"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
        opacity="0.75"
      />
    </svg>
  );
}
