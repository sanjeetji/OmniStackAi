"use client";

import { useState } from "react";
import { Globe, LayoutDashboard, LoaderCircle, MonitorSmartphone, Smartphone } from "lucide-react";
import type { ProjectScope, ScopeApp } from "@/lib/control-plane";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ICONS: Record<ScopeApp["kind"], typeof Globe> = {
  web: MonitorSmartphone,
  admin: LayoutDashboard,
  mobile: Smartphone,
  site: Globe,
};

/**
 * PC-127: what the platform will build for this prompt, before it builds - one app, an app and its
 * admin, a few apps or a whole ecosystem. Every app says why it is there and can be switched off or
 * on; the build follows exactly what is ticked. Nothing here costs anything: no model is asked.
 */
export function ScopeProposal({
  prompt,
  scope,
  onBuild,
  onCancel,
}: {
  prompt: string;
  scope: ProjectScope;
  onBuild: (scope: ProjectScope) => void;
  onCancel: () => void;
}) {
  const [current, setCurrent] = useState(scope);
  const [updating, setUpdating] = useState(false);
  const chosen = current.apps.filter((app) => app.included && app.kind !== "site").length;

  async function toggle(app: ScopeApp) {
    const included = Object.fromEntries(current.apps.map((a) => [a.id, a.id === app.id ? !a.included : a.included]));
    // Shown at once; the shape and summary follow from the platform's answer.
    setCurrent({ ...current, apps: current.apps.map((a) => ({ ...a, included: included[a.id] })) });
    setUpdating(true);
    try {
      const res = await fetch("/api/scope", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, included }),
      });
      if (res.ok) setCurrent((await res.json()) as ProjectScope);
    } catch {
      // the toggle itself is kept; only the summary waits
    } finally {
      setUpdating(false);
    }
  }

  return (
    <section
      aria-labelledby="scope-title"
      className="reveal space-y-3 self-stretch rounded-xl border border-border/70 bg-card p-3.5 text-card-foreground"
    >
      <div className="space-y-1">
        <h3 id="scope-title" className="flex items-center gap-2 text-sm font-semibold">
          What we&apos;ll build: {current.shape_label}
          {updating ? <LoaderCircle className="size-3.5 animate-spin text-muted-foreground" aria-hidden="true" /> : null}
        </h3>
        <p className="text-pretty text-xs text-muted-foreground">{current.reason}</p>
      </div>
      <ul className="space-y-1.5" aria-label="Apps">
        {current.apps.map((app) => {
          const Icon = ICONS[app.kind] ?? Globe;
          return (
            <li key={app.id}>
              <label
                className={cn(
                  "flex cursor-pointer items-start gap-2.5 rounded-lg border px-2.5 py-2 transition-colors",
                  app.included ? "border-primary/40 bg-primary/5" : "border-border/60 hover:bg-muted/40",
                )}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 size-4 accent-[var(--primary)]"
                  checked={app.included}
                  onChange={() => void toggle(app)}
                />
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
      <p className="text-pretty text-xs text-muted-foreground">{current.summary}</p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" disabled={chosen === 0 || updating} onClick={() => onBuild(current)}>
          Build this
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Change the prompt
        </Button>
      </div>
    </section>
  );
}
