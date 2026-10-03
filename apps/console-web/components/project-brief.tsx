"use client";

import { useState, type ReactNode } from "react";
import { Globe, LayoutDashboard, LoaderCircle, MonitorSmartphone, Smartphone } from "lucide-react";
import type { ProjectBrief as Brief, ProjectScope, ScopeApp } from "@/lib/control-plane";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ICONS: Record<ScopeApp["kind"], typeof Globe> = {
  web: MonitorSmartphone,
  admin: LayoutDashboard,
  mobile: Smartphone,
  site: Globe,
};
const LANGUAGES = ["English", "Hindi", "Spanish", "French", "German", "Portuguese", "Arabic", "Bengali", "Tamil", "Telugu",
  "Marathi", "Gujarati", "Japanese", "Chinese", "Indonesian"];
const BACKENDS: Record<string, string> = { python: "Python (FastAPI)", node: "Node.js (Express)", go: "Go" };

function Section({ title, hint, open, children }: { title: string; hint?: string; open?: boolean; children: ReactNode }) {
  return (
    <details open={open} className="group rounded-lg border border-border/60 px-2.5 py-2 open:pb-2.5">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-[13px] font-medium select-none">
        <span>{title}</span>
        {hint ? <span className="truncate text-xs font-normal text-muted-foreground">{hint}</span> : null}
      </summary>
      <div className="mt-2 space-y-1.5">{children}</div>
    </details>
  );
}

/**
 * PC-128: the project brief, after the prompt and before anything is built. Every answer is already
 * chosen for this prompt - the apps (PC-127), the building blocks it needs, a few questions only this
 * prompt raises, brand, region and stack - so "Use smart defaults" builds at once, and anything can
 * be changed first. Nothing here costs anything: no model is asked.
 */
export function ProjectBrief({
  brief,
  onBuild,
  onCancel,
}: {
  brief: Brief;
  onBuild: (brief: Brief) => void;
  onCancel: () => void;
}) {
  const [current, setCurrent] = useState(brief);
  const [updating, setUpdating] = useState(false);
  const set = (patch: Partial<Brief>) => setCurrent((prev) => ({ ...prev, ...patch }));
  const scope = current.scope;
  const chosenApps = scope.apps.filter((app) => app.included && app.kind !== "site").length;
  const choices = current.choices ?? { currencies: ["USD", "EUR", "GBP", "INR"], backends: ["python", "node", "go"], styles: [] };

  async function toggleApp(app: ScopeApp) {
    const included = Object.fromEntries(scope.apps.map((a) => [a.id, a.id === app.id ? !a.included : a.included]));
    set({ scope: { ...scope, apps: scope.apps.map((a) => ({ ...a, included: included[a.id] })) } });
    setUpdating(true);
    try {
      const res = await fetch("/api/scope", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: current.prompt, included }),
      });
      if (res.ok) {
        const next = (await res.json()) as ProjectScope;
        setCurrent((prev) => ({ ...prev, scope: next }));
      }
    } catch {
      // the toggle itself is kept; only the summary waits
    } finally {
      setUpdating(false);
    }
  }

  const languages = current.region.languages ?? ["English"];
  return (
    <section
      aria-labelledby="brief-title"
      className="reveal space-y-2.5 self-stretch rounded-xl border border-border/70 bg-card p-3.5 text-card-foreground"
    >
      <div className="space-y-1">
        <h3 id="brief-title" className="flex items-center gap-2 text-sm font-semibold">
          What we&apos;ll build: {scope.shape_label}
          {updating ? <LoaderCircle className="size-3.5 animate-spin text-muted-foreground" aria-hidden="true" /> : null}
        </h3>
        <p className="text-pretty text-xs text-muted-foreground">
          Everything below is already chosen for your idea. Change anything, or build it as it is.
        </p>
      </div>

      <Section title="Apps" hint={`${chosenApps} app${chosenApps === 1 ? "" : "s"}`} open>
        <p className="text-pretty text-xs text-muted-foreground">{scope.reason}</p>
        <ul className="space-y-1.5" aria-label="Apps">
          {scope.apps.map((app) => {
            const Icon = ICONS[app.kind] ?? Globe;
            return (
              <li key={app.id}>
                <label
                  className={cn(
                    "flex cursor-pointer items-start gap-2.5 rounded-lg border px-2.5 py-2 transition-colors",
                    app.included ? "border-primary/40 bg-primary/5" : "border-border/60 hover:bg-muted/40",
                  )}
                >
                  <input type="checkbox" className="mt-0.5 size-4 accent-[var(--primary)]" checked={app.included}
                    onChange={() => void toggleApp(app)} />
                  <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="min-w-0">
                    <span className="block text-[13px] font-medium">{app.name}</span>
                    <span className="block text-pretty text-xs text-muted-foreground">{app.reason}</span>
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </Section>

      <Section title="Features" hint={`${current.features.filter((f) => f.included).length} chosen`} open>
        <ul className="flex flex-wrap gap-1.5" aria-label="Features">
          {current.features.map((feature) => (
            <li key={feature.id}>
              <button
                type="button"
                title={feature.reason}
                aria-pressed={feature.included}
                disabled={feature.from_prompt}
                onClick={() => set({ features: current.features.map((f) => (f.id === feature.id ? { ...f, included: !f.included } : f)) })}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs transition-colors",
                  feature.included ? "border-primary/50 bg-primary/10 text-foreground" : "border-border/60 text-muted-foreground hover:bg-muted/40",
                  feature.from_prompt && "cursor-default",
                )}
              >
                {feature.included ? "✓ " : "+ "}
                {feature.label}
              </button>
            </li>
          ))}
        </ul>
        <p className="text-pretty text-xs text-muted-foreground">Ticked ones are built in. Hover a feature to see why.</p>
      </Section>

      {current.questions.length > 0 ? (
        <Section title="A few questions" hint="answers already chosen" open>
          {current.questions.map((question) => (
            <label key={question.id} className="block space-y-1">
              <span className="block text-xs font-medium">{question.question}</span>
              <select
                className="w-full rounded-md border border-border/70 bg-background px-2 py-1.5 text-xs"
                value={question.answer}
                onChange={(event) => set({
                  questions: current.questions.map((q) => (q.id === question.id ? { ...q, answer: event.target.value } : q)),
                })}
              >
                {question.options.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <span className="block text-pretty text-[11px] text-muted-foreground">{question.reason}</span>
            </label>
          ))}
        </Section>
      ) : null}

      <Section title="Brand" hint={current.name || current.brand.style || ""}>
        <label className="block space-y-1">
          <span className="block text-xs font-medium">Name</span>
          <input
            className="w-full rounded-md border border-border/70 bg-background px-2 py-1.5 text-xs"
            placeholder="Leave empty and we'll name it from your idea"
            maxLength={60}
            value={current.name}
            onChange={(event) => set({ name: event.target.value })}
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          {(["primary_color", "accent_color"] as const).map((key) => (
            <label key={key} className="flex items-center gap-1.5 text-xs">
              <input
                type="color"
                className="size-6 cursor-pointer rounded border border-border/70 bg-transparent"
                value={current.brand[key] || "#4f46e5"}
                onChange={(event) => set({ brand: { ...current.brand, [key]: event.target.value } })}
              />
              {key === "primary_color" ? "Main colour" : "Accent"}
            </label>
          ))}
          {choices.styles.length > 0 ? (
            <label className="flex items-center gap-1.5 text-xs">
              Style
              <select
                className="rounded-md border border-border/70 bg-background px-1.5 py-1 text-xs"
                value={current.brand.style || ""}
                onChange={(event) => set({ brand: { ...current.brand, style: event.target.value } })}
              >
                {choices.styles.map((style) => <option key={style} value={style}>{style}</option>)}
              </select>
            </label>
          ) : null}
        </div>
      </Section>

      <Section title="Language and region" hint={`${languages.join(", ")} · ${current.region.currency ?? ""}`}>
        <ul className="flex flex-wrap gap-1.5" aria-label="Languages">
          {LANGUAGES.map((language) => {
            const on = languages.includes(language);
            return (
              <li key={language}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => {
                    const next = on ? languages.filter((l) => l !== language) : [...languages, language];
                    set({ region: { ...current.region, languages: next.length ? next : ["English"] } });
                  }}
                  className={cn("rounded-full border px-2 py-0.5 text-[11px]",
                    on ? "border-primary/50 bg-primary/10" : "border-border/60 text-muted-foreground")}
                >
                  {language}
                </button>
              </li>
            );
          })}
        </ul>
        <div className="flex flex-wrap gap-3 text-xs">
          <label className="flex items-center gap-1.5">
            Currency
            <select
              className="rounded-md border border-border/70 bg-background px-1.5 py-1 text-xs"
              value={current.region.currency || "USD"}
              onChange={(event) => set({ region: { ...current.region, currency: event.target.value } })}
            >
              {choices.currencies.map((code) => <option key={code} value={code}>{code}</option>)}
            </select>
          </label>
          <span className="text-muted-foreground">Time zone: {current.region.timezone || "UTC"}</span>
        </div>
      </Section>

      <Section title="Advanced" hint={BACKENDS[current.advanced.backend || "python"] ?? ""}>
        <label className="flex items-center gap-1.5 text-xs">
          Backend
          <select
            className="rounded-md border border-border/70 bg-background px-1.5 py-1 text-xs"
            value={current.advanced.backend || "python"}
            onChange={(event) => set({ advanced: { ...current.advanced, backend: event.target.value } })}
          >
            {choices.backends.map((backend) => <option key={backend} value={backend}>{BACKENDS[backend] ?? backend}</option>)}
          </select>
        </label>
        <p className="text-xs text-muted-foreground">Database: PostgreSQL</p>
      </Section>

      <p className="text-pretty text-xs text-muted-foreground">{scope.summary}</p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" disabled={chosenApps === 0 || updating} onClick={() => onBuild(current)}>
          Build this
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={() => onBuild(brief)}>
          Use smart defaults
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Change the prompt
        </Button>
      </div>
    </section>
  );
}
