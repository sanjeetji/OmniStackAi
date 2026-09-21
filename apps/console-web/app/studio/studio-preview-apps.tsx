"use client";

import { useState } from "react";
import {
  Check,
  Circle,
  CircleCheck,
  Copy,
  ExternalLink,
  Globe,
  KeyRound,
  LayoutDashboard,
  LoaderCircle,
  RefreshCw,
  Server,
  Smartphone,
  Square,
  type LucideIcon,
} from "lucide-react";
import type { PreviewApp, PreviewDemoUser, PreviewStatus } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const KIND_ICON: Record<PreviewApp["kind"], LucideIcon> = {
  web: Globe,
  admin: LayoutDashboard,
  pwa: Smartphone,
  api: Server,
};

const PHASE_LABELS: Record<string, string> = {
  install: "Installing dependencies",
  migrate: "Setting up the database and demo data",
  start: "Starting the apps",
  ready: "Ready",
};

const FRAME_HEIGHT = "h-[calc(100dvh-18rem)] min-h-[480px]";

/**
 * Preview for template projects that run several apps sharing one API (R-520). Shows one app at a
 * time with a switcher. Mobile (PWA) apps render in a phone frame. The template's demo logins are
 * listed underneath.
 */
export function MultiAppPreview({
  projectId,
  status,
  busy,
  onRestart,
  onStop,
}: {
  projectId: string;
  status: PreviewStatus;
  busy: boolean;
  onRestart: () => void;
  onStop: () => void;
}) {
  const apps = status.apps ?? [];
  const uiApps = apps.filter((app) => app.kind !== "api");
  const api = apps.find((app) => app.kind === "api");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = uiApps.find((app) => app.id === selectedId) ?? uiApps[0];

  if (status.status === "starting") {
    return <StartingPanel status={status} apps={apps} />;
  }

  if (!selected) {
    return null;
  }

  const base = `/preview/${encodeURIComponent(projectId)}`;
  const src = `${base}/${encodeURIComponent(selected.id)}`;
  const isPhone = selected.kind === "pwa";

  return (
    <div className="overflow-hidden rounded-xl border border-border/60 bg-card">
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-3 py-2">
        <Badge variant="outline" className="gap-1 border-brand/30 bg-brand/15 text-brand">
          <span aria-hidden="true" className="size-1.5 rounded-full bg-brand" />
          Live
        </Badge>
        <div role="tablist" aria-label="Apps in this project" className="flex flex-wrap items-center gap-1 rounded-lg bg-muted p-0.5">
          {uiApps.map((app) => {
            const Icon = KIND_ICON[app.kind];
            const active = app.id === selected.id;
            return (
              <button
                key={app.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setSelectedId(app.id)}
                className={cn(
                  "inline-flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50",
                  active && "bg-background text-foreground shadow-sm",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {app.name}
                {!app.ready ? <span className="size-1.5 rounded-full bg-destructive" aria-label="not running" /> : null}
              </button>
            );
          })}
        </div>
        <span className="min-w-0 flex-1" />
        {api ? (
          <Button asChild variant="ghost" size="sm" title="Check the API">
            <a href={`${base}/${encodeURIComponent(api.id)}/health`} target="_blank" rel="noreferrer">
              <Server aria-hidden="true" />
              API
            </a>
          </Button>
        ) : null}
        <Button asChild variant="ghost" size="icon-sm" aria-label={`Open ${selected.name} in a new tab`}>
          <a href={src} target="_blank" rel="noreferrer">
            <ExternalLink aria-hidden="true" />
          </a>
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onRestart} disabled={busy}>
          <RefreshCw className={cn(busy && "animate-spin")} aria-hidden="true" />
          Restart
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onStop} disabled={busy}>
          <Square aria-hidden="true" />
          Stop
        </Button>
      </div>

      <div className="bg-muted/40 p-3">
        {isPhone ? (
          <div className="mx-auto w-[390px] max-w-full rounded-[2.75rem] border-[10px] border-neutral-900 bg-neutral-900 shadow-xl dark:border-neutral-700">
            <div className="mx-auto mb-1 h-5 w-28 rounded-b-2xl bg-neutral-900 dark:bg-neutral-700" aria-hidden="true" />
            <iframe
              key={src}
              src={src}
              title={`${selected.name} preview`}
              className="block h-[720px] max-h-[calc(100dvh-16rem)] w-full rounded-b-[2rem] bg-white"
            />
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border/60 bg-white">
            <iframe key={src} src={src} title={`${selected.name} preview`} className={cn("block w-full", FRAME_HEIGHT)} />
          </div>
        )}
      </div>

      {status.demo_users && status.demo_users.length > 0 ? <DemoLogins users={status.demo_users} /> : null}
    </div>
  );
}

function StartingPanel({ status, apps }: { status: PreviewStatus; apps: PreviewApp[] }) {
  const seconds = Math.round((status.elapsed_ms ?? 0) / 1000);
  const phase = (status.phase && PHASE_LABELS[status.phase]) || "Starting";
  return (
    <div className="rounded-xl border border-border/60 bg-card p-4" aria-busy="true">
      <div className="flex items-center gap-2 text-sm">
        <LoaderCircle className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
        <span className="font-medium">{phase}</span>
        <span className="text-muted-foreground tabular-nums">{seconds}s</span>
      </div>
      <p className="mt-1 text-pretty text-sm text-muted-foreground">
        {status.message} The first start installs dependencies and can take a few minutes.
      </p>
      <ul className="mt-3 grid gap-1.5">
        {apps.map((app) => {
          const Icon = KIND_ICON[app.kind];
          return (
            <li key={app.id} className="flex items-center gap-2 text-sm">
              {app.ready ? (
                <CircleCheck className="size-4 text-brand" aria-label="ready" />
              ) : (
                <Circle className="size-4 text-muted-foreground/60" aria-label="waiting" />
              )}
              <Icon className="size-3.5 text-muted-foreground" aria-hidden="true" />
              <span>{app.name}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function DemoLogins({ users }: { users: PreviewDemoUser[] }) {
  return (
    <details className="group border-t border-border/60 px-3 py-2 text-sm" open>
      <summary className="flex cursor-pointer list-none items-center gap-2 font-medium outline-none focus-visible:ring-3 focus-visible:ring-ring/50">
        <KeyRound className="size-3.5 text-muted-foreground" aria-hidden="true" />
        Demo logins
        <span className="text-xs font-normal text-muted-foreground">local preview only</span>
      </summary>
      <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
        {users.map((user) => (
          <li key={`${user.role}-${user.email}`} className="flex min-w-0 items-center gap-2 rounded-lg bg-muted/60 px-2.5 py-1.5">
            <Badge variant="outline" className="shrink-0 capitalize">
              {user.role}
            </Badge>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-medium">{user.name}</div>
              <div className="truncate font-mono text-xs text-muted-foreground">{user.email}</div>
            </div>
            <CopyButton label={`Copy ${user.role} email`} value={user.email} />
            <CopyButton label={`Copy ${user.role} password`} value={user.password} icon={KeyRound} />
          </li>
        ))}
      </ul>
    </details>
  );
}

function CopyButton({ label, value, icon: Icon = Copy }: { label: string; value: string; icon?: LucideIcon }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      aria-label={label}
      title={label}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          // Clipboard access can be blocked; the value is still visible or selectable.
        }
      }}
    >
      {copied ? <Check aria-hidden="true" /> : <Icon aria-hidden="true" />}
    </Button>
  );
}
