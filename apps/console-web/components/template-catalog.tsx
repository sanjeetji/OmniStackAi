"use client";

import { useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import type { TemplateSummary } from "@/lib/control-plane";
import { Input } from "@/components/ui/input";
import TemplateCard from "@/components/template-card";
import { TEMPLATE_CATEGORIES } from "@/components/template-meta";
import { cn } from "@/lib/utils";

function matches(template: TemplateSummary, query: string): boolean {
  if (!query) return true;
  const haystack = [
    template.name,
    template.tagline,
    template.category,
    ...template.features,
    ...template.entities,
    ...template.apps.map((app) => app.name),
    ...template.stack,
  ]
    .join(" ")
    .toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

/** Search and category filters over the catalogue. Filtering is client-side: the catalogue is
 * small and ships with the platform. */
export default function TemplateCatalog({ templates }: { templates: TemplateSummary[] }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | null>(null);

  const counts = useMemo(() => {
    const byCategory = new Map<string, number>();
    for (const template of templates) {
      byCategory.set(template.category, (byCategory.get(template.category) ?? 0) + 1);
    }
    return byCategory;
  }, [templates]);

  const visible = templates.filter(
    (template) => (!category || template.category === category) && matches(template, query.trim()),
  );
  const categories = TEMPLATE_CATEGORIES.filter((entry) => counts.has(entry.id));

  return (
    <div className="grid gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative sm:w-80">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search templates, features, data…"
            aria-label="Search templates"
            className="pl-9"
          />
        </div>
        <div role="group" aria-label="Filter by category" className="flex flex-wrap gap-1.5">
          <FilterChip active={category === null} onClick={() => setCategory(null)} label="All" count={templates.length} />
          {categories.map((entry) => (
            <FilterChip
              key={entry.id}
              active={category === entry.id}
              onClick={() => setCategory(category === entry.id ? null : entry.id)}
              label={entry.label}
              count={counts.get(entry.id) ?? 0}
            />
          ))}
        </div>
      </div>

      {visible.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {visible.map((template) => (
            <TemplateCard key={template.slug} template={template} />
          ))}
        </div>
      ) : (
        <div className="grid justify-items-center gap-2 rounded-xl border border-dashed border-border/70 px-6 py-12 text-center">
          <p className="text-sm font-medium">No templates match that search.</p>
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setCategory(null);
            }}
            className="inline-flex items-center gap-1 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
          >
            <X className="size-3.5" aria-hidden="true" />
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-sm outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
        active
          ? "border-foreground/20 bg-foreground text-background"
          : "border-border/70 text-muted-foreground hover:border-foreground/30 hover:text-foreground",
      )}
    >
      {label}
      <span className={cn("tabular-nums text-xs", active ? "text-background/70" : "text-muted-foreground/70")}>{count}</span>
    </button>
  );
}
