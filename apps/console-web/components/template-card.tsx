"use client";

import { useState, useId, useEffect } from "react";
import Link from "next/link";
import { ArrowUpRight, ChevronLeft, ChevronRight, Sparkles, Users } from "lucide-react";
import type { TemplateSummary } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { APP_KIND_META, categoryMeta, templateAssetUrl } from "@/components/template-meta";
import { cn } from "@/lib/utils";

interface SlideItem {
  image: string;
  label: string;
}

/** A marketplace card: interactive slide carousel, name, category, tagline and apps included. */
export default function TemplateCard({ template }: { template: TemplateSummary }) {
  const category = categoryMeta(template.category);
  const CategoryIcon = category.icon;
  const cardId = useId();

  // Build slides from cover + highlights/screenshots
  const slides: SlideItem[] = [];
  if (template.cover) {
    slides.push({ image: template.cover, label: "Overview" });
  }

  if (template.screens && template.screens.length > 0) {
    const highlights = template.screens.filter((s) => s.highlight);
    const toUse = highlights.length >= 3 ? highlights : template.screens.slice(0, 5);
    for (const s of toUse) {
      if (s.image !== template.cover) {
        slides.push({ image: s.image, label: s.title });
      }
    }
  } else if (template.screenshots && template.screenshots.length > 0) {
    for (const shot of template.screenshots.slice(0, 5)) {
      if (shot !== template.cover) {
        const name = shot.split("/").pop()?.replace(/\.[^/.]+$/, "").replace(/-/g, " ") || "Screen";
        slides.push({ image: shot, label: name });
      }
    }
  }

  const [activeIndex, setActiveIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);

  // Gentle auto-slide when card is hovered
  useEffect(() => {
    if (!isHovered || slides.length <= 1) return;
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % slides.length);
    }, 2400);
    return () => clearInterval(interval);
  }, [isHovered, slides.length]);

  const prevSlide = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveIndex((prev) => (prev - 1 + slides.length) % slides.length);
  };

  const nextSlide = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setActiveIndex((prev) => (prev + 1) % slides.length);
  };

  const currentSlide = slides[activeIndex] ?? slides[0];

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setActiveIndex(0);
      }}
      className="group relative flex flex-col overflow-hidden rounded-xl border border-border/60 bg-card outline-none transition-all hover:-translate-y-0.5 hover:border-foreground/25 hover:shadow-lg"
    >
      <Link
        href={`/templates/${encodeURIComponent(template.slug)}`}
        className="flex flex-1 flex-col outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
        aria-labelledby={`title-${cardId}`}
      >
        <div className="relative aspect-[16/9] w-full overflow-hidden bg-muted">
          {slides.length > 0 && currentSlide ? (
            // eslint-disable-next-line @next/next/no-img-element -- assets are relayed as-is
            <img
              src={templateAssetUrl(template.slug, currentSlide.image)}
              alt={`${template.name} - ${currentSlide.label}`}
              key={currentSlide.image}
              className="size-full object-cover transition-all duration-500 ease-out group-hover:scale-[1.02]"
              loading="lazy"
            />
          ) : (
            <div className="grid size-full place-items-center bg-gradient-to-br from-muted to-secondary">
              <CategoryIcon className="size-10 text-muted-foreground/60" aria-hidden="true" />
            </div>
          )}

          {/* Top badges */}
          <div className="absolute left-3 top-3 flex items-center gap-1.5">
            <Badge variant="secondary" className="gap-1 bg-background/85 backdrop-blur font-medium">
              <CategoryIcon className="size-3.5" aria-hidden="true" />
              {category.label}
            </Badge>
          </div>

          {/* Current view label badge */}
          {slides.length > 1 && currentSlide ? (
            <span className="absolute right-3 top-3 rounded-md bg-background/80 px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase text-muted-foreground backdrop-blur">
              {currentSlide.label}
            </span>
          ) : null}

          {/* Slide controls (visible on hover if multiple slides) */}
          {slides.length > 1 ? (
            <>
              <button
                type="button"
                onClick={prevSlide}
                aria-label="Previous screenshot"
                className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-background/80 p-1.5 text-foreground opacity-0 shadow backdrop-blur transition-opacity hover:bg-background group-hover:opacity-90"
              >
                <ChevronLeft className="size-3.5" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={nextSlide}
                aria-label="Next screenshot"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-background/80 p-1.5 text-foreground opacity-0 shadow backdrop-blur transition-opacity hover:bg-background group-hover:opacity-90"
              >
                <ChevronRight className="size-3.5" aria-hidden="true" />
              </button>

              {/* Dot Indicators */}
              <div className="absolute bottom-2.5 inset-x-0 flex items-center justify-center gap-1 z-10">
                {slides.map((slide, idx) => (
                  <button
                    key={slide.image}
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setActiveIndex(idx);
                    }}
                    aria-label={`Jump to ${slide.label}`}
                    className={cn(
                      "h-1.5 rounded-full transition-all duration-300",
                      idx === activeIndex
                        ? "w-5 bg-white shadow-sm"
                        : "w-1.5 bg-white/50 hover:bg-white/80"
                    )}
                  />
                ))}
              </div>
            </>
          ) : null}
        </div>

        <div className="flex flex-1 flex-col gap-3 p-4">
          <div>
            <h3 id={`title-${cardId}`} className="flex items-center gap-1.5 font-semibold tracking-tight">
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
    </div>
  );
}
