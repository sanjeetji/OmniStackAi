import Link from "next/link";
import { ArrowUpRight, Sparkles, Users } from "lucide-react";
import type { TemplateSummary } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { APP_KIND_META, categoryMeta, templateAssetUrl } from "@/components/template-meta";

/** A marketplace card: cover, name, category, tagline and which apps the template ships. */
export default function TemplateCard({ template }: { template: TemplateSummary }) {
  const category = categoryMeta(template.category);
  const CategoryIcon = category.icon;
  return (
    <Link
      href={`/templates/${encodeURIComponent(template.slug)}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-border/60 bg-card outline-none transition-all hover:-translate-y-0.5 hover:border-foreground/25 hover:shadow-md focus-visible:ring-3 focus-visible:ring-ring/50"
    >
      <div className="relative aspect-[16/9] overflow-hidden bg-muted">
        {template.cover ? (
          // eslint-disable-next-line @next/next/no-img-element -- assets are relayed as-is; no optimiser needed
          <img
            src={templateAssetUrl(template.slug, template.cover)}
            alt=""
            className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            loading="lazy"
          />
        ) : (
          <div className="grid size-full place-items-center bg-gradient-to-br from-muted to-secondary">
            <CategoryIcon className="size-10 text-muted-foreground/60" aria-hidden="true" />
          </div>
        )}
        <Badge variant="secondary" className="absolute left-3 top-3 gap-1 bg-background/85 backdrop-blur">
          <CategoryIcon aria-hidden="true" />
          {category.label}
        </Badge>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="flex items-center gap-1.5 font-semibold tracking-tight">
            {template.name}
            <ArrowUpRight
              className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
              aria-hidden="true"
            />
          </h3>
          <p className="mt-1 line-clamp-2 text-pretty text-sm text-muted-foreground">{template.tagline}</p>
        </div>
        <ul className="flex flex-wrap gap-1.5" aria-label="Apps included">
          {template.apps.map((app) => {
            const Icon = APP_KIND_META[app.kind]?.icon;
            return (
              <li key={app.id}>
                <Badge variant="outline" className="gap-1 font-normal">
                  {Icon ? <Icon aria-hidden="true" /> : null}
                  {app.name}
                </Badge>
              </li>
            );
          })}
        </ul>
        <div className="mt-auto flex items-center gap-3 border-t border-border/60 pt-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Sparkles className="size-3.5" aria-hidden="true" />
            {template.features.length} features
          </span>
          <span className="inline-flex items-center gap-1">
            <Users className="size-3.5" aria-hidden="true" />
            {template.roles.length} roles
          </span>
          <span className="ml-auto tabular-nums">v{template.version}</span>
        </div>
      </div>
    </Link>
  );
}
