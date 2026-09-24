"""The stylesheet a generated home page ships with (R-558).

The generated project already carries a real design system — 59 colour tokens, a type scale, a
space scale, six shadows, seven motion tokens. The pages ignored almost all of it: measured on a
storefront home page, `--shadow-*` appeared 0 times, `--transition-*` 0, `--font-size-*` 0,
`--space-*` 0, against 26 hardcoded pixel values and **zero hover or focus states**. It looked
flat and static because it was.

Part of that was structural rather than a matter of taste. Inline React styles cannot express
`:hover`, `:focus-visible` or a media query, so no amount of tuning inline values could have
produced an interface that responds to a cursor or a keyboard. Hence a real stylesheet, emitted
with the page and scoped by class.

Three things here are not decoration:

* **focus-visible** is styled rather than removed. A keyboard user who cannot see where they are
  cannot use the page at all, and `outline: none` with nothing in its place is the single most
  common way generated interfaces become unusable.
* **prefers-reduced-motion** switches every transition off. Motion is a comfort setting for some
  people and a medical one for others.
* **Depth and motion come from the tokens**, so a rebrand through `brand.json` moves them too
  rather than leaving a hardcoded shadow behind.
"""

from __future__ import annotations

#: One class prefix for the whole page, so the stylesheet cannot collide with a component's own
#: classes or with anything a user adds later.
PREFIX = "osa"


def page_stylesheet() -> str:
    """The CSS a generated public home page ships with. Pure tokens, no hardcoded palette."""
    return f""".{PREFIX}-page {{
  --osa-shell: min(1120px, 100% - (var(--space-6) * 2));
}}

/* Type — the shipped scale, with a fluid headline that stays readable on a phone. */
.{PREFIX}-display {{
  margin: 0 0 var(--space-5);
  font-size: clamp(var(--font-size-3xl), 5vw, var(--font-size-4xl));
  line-height: var(--line-height-tight, 1.1);
  letter-spacing: -0.03em;
  font-weight: 800;
  text-wrap: balance;
}}
.{PREFIX}-lede {{
  margin: 0 0 var(--space-8);
  max-width: 62ch;
  font-size: var(--font-size-lg);
  line-height: var(--line-height-relaxed, 1.65);
  color: var(--color-text-muted);
  text-wrap: pretty;
}}
.{PREFIX}-eyebrow {{
  display: inline-block;
  margin-bottom: var(--space-4);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  border: 1px solid var(--color-primary-subtle);
  box-shadow: var(--shadow-sm);
  font-size: var(--font-size-xs);
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-primary);
}}
.{PREFIX}-heading {{
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-3xl);
  font-weight: 700;
  letter-spacing: -0.02em;
  text-wrap: balance;
}}
.{PREFIX}-sub {{
  margin: 0 0 var(--space-10);
  max-width: 54ch;
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
}}

/* Layout */
.{PREFIX}-shell {{ width: var(--osa-shell); margin-inline: auto; }}
.{PREFIX}-section {{ padding-block: var(--space-16); }}
.{PREFIX}-hero {{ padding-block: var(--space-20) var(--space-16); }}
.{PREFIX}-center {{ text-align: center; }}
.{PREFIX}-center .{PREFIX}-lede,
.{PREFIX}-center .{PREFIX}-sub {{ margin-inline: auto; }}
.{PREFIX}-grid {{
  display: grid;
  gap: var(--space-5);
  grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
}}
.{PREFIX}-split {{
  display: grid;
  gap: var(--space-12);
  align-items: center;
  grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
}}
.{PREFIX}-actions {{ display: flex; gap: var(--space-3); flex-wrap: wrap; }}
.{PREFIX}-center .{PREFIX}-actions {{ justify-content: center; }}

/* Surfaces — depth from the shipped shadows, so a rebrand moves them too. */
.{PREFIX}-wash {{
  background:
    radial-gradient(60% 120% at 50% -10%, var(--color-primary-subtle) 0%, transparent 70%),
    var(--color-background);
}}
.{PREFIX}-band {{
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-hover) 100%);
  color: var(--color-primary-foreground);
}}
.{PREFIX}-panel {{
  min-height: 280px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--color-primary-subtle) 0%, var(--color-surface) 100%);
  border: 1px solid var(--color-border, var(--color-neutral-200));
  box-shadow: var(--shadow-lg);
}}
.{PREFIX}-card {{
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  border: 1px solid var(--color-border, var(--color-neutral-200));
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-duration-fast) var(--transition-timing),
              box-shadow var(--transition-duration-fast) var(--transition-timing),
              border-color var(--transition-duration-fast) var(--transition-timing);
}}
.{PREFIX}-card:hover {{
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
  border-color: var(--color-primary-subtle);
}}
.{PREFIX}-card h3 {{ margin: 0 0 var(--space-2); font-size: var(--font-size-lg); font-weight: 650; }}
.{PREFIX}-card p {{ margin: 0; color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: 1.6; }}

/* An index row, for the arrangements that list rather than tile. */
.{PREFIX}-rows {{ margin: 0; padding: 0; list-style: none; display: grid; }}
.{PREFIX}-row {{
  display: flex;
  gap: var(--space-5);
  padding-block: var(--space-5);
  border-top: 1px solid var(--color-border, var(--color-neutral-200));
  transition: background var(--transition-duration-fast) var(--transition-timing);
}}
.{PREFIX}-row:hover {{ background: var(--color-surface-hover, var(--color-surface-subtle)); }}
.{PREFIX}-num {{
  min-width: 2.25rem;
  font-size: var(--font-size-sm);
  font-weight: 700;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}}
.{PREFIX}-row strong {{ display: block; font-size: var(--font-size-base); font-weight: 650; }}
.{PREFIX}-row span span {{ color: var(--color-text-muted); font-size: var(--font-size-sm); }}

/* Actions — the part inline styles could not do at all. */
.{PREFIX}-btn {{
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 600;
  text-decoration: none;
  transition: transform var(--transition-duration-fast) var(--transition-timing),
              box-shadow var(--transition-duration-fast) var(--transition-timing),
              background var(--transition-duration-fast) var(--transition-timing);
}}
.{PREFIX}-btn-primary {{
  background: var(--color-primary);
  color: var(--color-primary-foreground);
  box-shadow: var(--shadow-md);
}}
.{PREFIX}-btn-primary:hover {{ background: var(--color-primary-hover); transform: translateY(-1px); box-shadow: var(--shadow-lg); }}
.{PREFIX}-btn-secondary {{
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border, var(--color-neutral-200));
}}
.{PREFIX}-btn-secondary:hover {{ border-color: var(--color-primary); color: var(--color-primary); }}
.{PREFIX}-band .{PREFIX}-btn-primary {{ background: var(--color-surface); color: var(--color-primary); }}
.{PREFIX}-band .{PREFIX}-btn-secondary {{ background: transparent; color: inherit; border-color: currentColor; }}

.{PREFIX}-pill {{
  display: inline-flex;
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border, var(--color-neutral-200));
  font-size: var(--font-size-sm);
  font-weight: 550;
  text-decoration: none;
  transition: all var(--transition-duration-fast) var(--transition-timing);
}}
.{PREFIX}-pill:hover {{ border-color: var(--color-primary); color: var(--color-primary); box-shadow: var(--shadow-sm); }}

/* Styled, never removed: a keyboard user who cannot see where they are cannot use the page. */
.{PREFIX}-page a:focus-visible {{
  outline: 2px solid var(--color-border-focus, var(--color-primary));
  outline-offset: 3px;
  border-radius: var(--radius-sm);
}}

.{PREFIX}-footer {{
  padding-block: var(--space-10);
  border-top: 1px solid var(--color-border, var(--color-neutral-200));
  color: var(--color-text-subtle);
  font-size: var(--font-size-sm);
  text-align: center;
}}
.{PREFIX}-rule {{ margin: var(--space-12) 0 0; border: 0; border-top: 1px solid var(--color-border, var(--color-neutral-200)); }}

/* Motion is a comfort setting for some people and a medical one for others. */
@media (prefers-reduced-motion: reduce) {{
  .{PREFIX}-page *, .{PREFIX}-page *::before, .{PREFIX}-page *::after {{
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }}
  .{PREFIX}-card:hover, .{PREFIX}-btn-primary:hover {{ transform: none; }}
}}
"""


def style_tag(indent: str = "      ") -> list[str]:
    """The `<style>` element carrying `page_stylesheet()`, as JSX lines.

    Emitted inline with the page rather than written to a file: it belongs to this page, it is a
    couple of kilobytes, and shipping it inline means no extra request and no chance of a
    stylesheet and a page disagreeing about which version they are.
    """
    css = page_stylesheet().replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    lines = [f"{indent}<style dangerouslySetInnerHTML={{{{ __html: `"]
    lines += [line for line in css.splitlines()]
    lines.append(f"{indent}` }}}} />")
    return lines
