"use client";

import { useEffect, useRef, useState } from "react";
import {
  ExternalLink,
  LoaderCircle,
  Monitor,
  MonitorOff,
  RefreshCw,
  Smartphone,
  Square,
  Tablet,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { PreviewStatus } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const POLL_INTERVAL_MS = 5000;

type ErrorBody = { error?: string };

async function postJSON(path: string): Promise<{ status: number; body: PreviewStatus | ErrorBody }> {
  const response = await fetch(path, { method: "POST" });
  const body = (await response.json().catch(() => ({}))) as PreviewStatus | ErrorBody;
  return { status: response.status, body };
}

type PresetKey = "desktop" | "tablet" | "phone";

const WIDTH_PRESETS: { key: PresetKey; label: string; icon: LucideIcon; maxWidth: string }[] = [
  { key: "desktop", label: "Desktop", icon: Monitor, maxWidth: "100%" },
  { key: "tablet", label: "Tablet", icon: Tablet, maxWidth: "768px" },
  { key: "phone", label: "Phone", icon: Smartphone, maxWidth: "390px" },
];

const FRAME_HEIGHT = "h-[calc(100dvh-18rem)] min-h-[480px]";

export function StudioPreview({
  buildId,
  previewVersion,
  projectId,
}: {
  buildId: string | null;
  previewVersion: number;
  projectId?: string | null;
}) {
  const [status, setStatus] = useState<PreviewStatus | null>(null);
  // starting/elapsedMs/fetchError travel together as one state value so the effect below only
  // ever needs one setState call at its start, not several cascading ones.
  const [phase, setPhase] = useState<{ starting: boolean; elapsedMs: number; fetchError: string | null }>({
    starting: false,
    elapsedMs: 0,
    fetchError: null,
  });
  const [disabled, setDisabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [preset, setPreset] = useState<PresetKey>("desktop");
  const startedAtRef = useRef<number | null>(null);

  // Start (or re-start) the preview for this build whenever buildId first becomes real, or
  // previewVersion bumps (the parent bumps it after every successful edit - _edit() never restarts
  // the preview on its own, unlike _build(), so this call is what keeps the iframe fresh).
  useEffect(() => {
    if (!buildId && !projectId) {
      return;
    }
    let cancelled = false;
    startedAtRef.current = Date.now();
    (async () => {
      setPhase({ starting: true, elapsedMs: 0, fetchError: null });
      try {
        const previewUrl = projectId
          ? `/api/projects/${encodeURIComponent(projectId)}/preview`
          : `/api/jobs/build/${encodeURIComponent(buildId!)}/preview`;
        const { status: httpStatus, body } = await postJSON(previewUrl);
        if (cancelled) return;
        if (httpStatus === 404) {
          setDisabled(true);
          setStatus(null);
          return;
        }
        setDisabled(false);
        setStatus(body as PreviewStatus);
      } catch {
        if (!cancelled) setPhase((p) => ({ ...p, fetchError: "Couldn't reach the server." }));
      } finally {
        if (!cancelled) setPhase((p) => ({ ...p, starting: false }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [buildId, previewVersion, projectId]);

  // Real elapsed time while starting - cold starts confirmed live up to ~45s during R-478.
  useEffect(() => {
    if (!phase.starting) return;
    const tick = setInterval(() => {
      setPhase((p) => ({ ...p, elapsedMs: Date.now() - (startedAtRef.current ?? Date.now()) }));
    }, 500);
    return () => clearInterval(tick);
  }, [phase.starting]);

  // Crash detection, not progress-watching: preview start is synchronous, so the only thing worth
  // polling for is a "ready" preview whose subprocess died on its own since the last check.
  useEffect(() => {
    if (!buildId || disabled || status?.status !== "ready") return;
    const interval = setInterval(async () => {
      try {
        const response = await fetch("/api/preview");
        if (response.status === 404) {
          setDisabled(true);
          return;
        }
        const body = (await response.json().catch(() => null)) as PreviewStatus | null;
        if (body) setStatus(body);
      } catch {
        // A transient poll failure isn't worth surfacing - the next tick retries.
      }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [buildId, disabled, status?.status]);

  async function handleRestart() {
    setBusy(true);
    try {
      const { status: httpStatus, body } = await postJSON("/api/preview/restart");
      if (httpStatus === 404) {
        setDisabled(true);
      } else {
        setStatus(body as PreviewStatus);
      }
    } catch {
      setPhase((p) => ({ ...p, fetchError: "Couldn't reach the server." }));
    } finally {
      setBusy(false);
    }
  }

  async function handleStop() {
    setBusy(true);
    try {
      const { status: httpStatus, body } = await postJSON("/api/preview/stop");
      if (httpStatus === 404) {
        setDisabled(true);
      } else {
        setStatus(body as PreviewStatus);
      }
    } catch {
      setPhase((p) => ({ ...p, fetchError: "Couldn't reach the server." }));
    } finally {
      setBusy(false);
    }
  }

  if (!buildId) return null;

  if (disabled) {
    return (
      <div className="grid justify-items-center gap-2 rounded-xl border border-dashed border-border/70 px-6 py-12 text-center">
        <MonitorOff className="size-5 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm font-medium">Live preview isn&rsquo;t running</p>
        <p className="max-w-sm text-pretty text-sm text-muted-foreground">
          Start the agent-engine in preview mode, then open this tab again:
        </p>
        <code className="mt-1 rounded-lg bg-muted px-2.5 py-1.5 font-mono text-xs">
          task agent-engine:studio:preview
        </code>
      </div>
    );
  }

  if (phase.fetchError) {
    return (
      <div
        role="alert"
        className="flex flex-wrap items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
      >
        <TriangleAlert className="size-4 shrink-0" aria-hidden="true" />
        <span className="min-w-0 flex-1">{phase.fetchError}</span>
        <Button type="button" variant="outline" size="sm" onClick={handleRestart} disabled={busy}>
          <RefreshCw aria-hidden="true" />
          Restart
        </Button>
      </div>
    );
  }

  if (phase.starting) {
    return (
      <div className="overflow-hidden rounded-xl border border-border/60 bg-card" aria-busy="true">
        <div className="flex items-center gap-2 border-b border-border/60 px-3 py-2 text-xs">
          <StatusPill tone="starting" />
          <span className="text-muted-foreground tabular-nums">
            Starting preview… {Math.round(phase.elapsedMs / 1000)}s
          </span>
        </div>
        <div className="p-3">
          <Skeleton className={cn("w-full rounded-lg", FRAME_HEIGHT)} />
        </div>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  if (status.status === "ready" && status.web_url) {
    const active = WIDTH_PRESETS.find((entry) => entry.key === preset) ?? WIDTH_PRESETS[0];
    return (
      <div className="overflow-hidden rounded-xl border border-border/60 bg-card">
        <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-3 py-2">
          <StatusPill tone="live" />
          <a
            href={status.web_url}
            target="_blank"
            rel="noreferrer"
            className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            {status.web_url}
          </a>
          <div
            role="group"
            aria-label="Preview width"
            className="hidden items-center rounded-lg bg-muted p-0.5 sm:flex"
          >
            {WIDTH_PRESETS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                aria-pressed={preset === key}
                onClick={() => setPreset(key)}
                title={label}
                className={cn(
                  "inline-flex size-7 items-center justify-center rounded-md text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50",
                  preset === key && "bg-background text-foreground shadow-sm",
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                <span className="sr-only">{label}</span>
              </button>
            ))}
          </div>
          <Button asChild variant="ghost" size="icon-sm" aria-label="Open in new tab">
            <a href={status.web_url} target="_blank" rel="noreferrer">
              <ExternalLink aria-hidden="true" />
            </a>
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={handleRestart} disabled={busy}>
            <RefreshCw className={cn(busy && "animate-spin")} aria-hidden="true" />
            Restart
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={handleStop} disabled={busy}>
            <Square aria-hidden="true" />
            Stop
          </Button>
        </div>
        <div className="bg-muted/40 p-3">
          <div
            className="mx-auto overflow-hidden rounded-lg border border-border/60 bg-white transition-[max-width] duration-300"
            style={{ maxWidth: active.maxWidth }}
          >
            <iframe
              src={status.web_url}
              className={cn("block w-full", FRAME_HEIGHT)}
              title="Live preview"
            />
          </div>
        </div>
      </div>
    );
  }

  const tone: PillTone =
    status.status === "error" ? "error" : status.status === "unavailable" ? "unavailable" : "stopped";
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border/60 bg-card px-4 py-3 text-sm">
      <StatusPill tone={tone} />
      <span className="min-w-0 flex-1 text-muted-foreground">{status.message}</span>
      {status.status !== "unavailable" ? (
        <Button type="button" variant="outline" size="sm" onClick={handleRestart} disabled={busy}>
          <RefreshCw className={cn(busy && "animate-spin")} aria-hidden="true" />
          Restart
        </Button>
      ) : null}
    </div>
  );
}

type PillTone = "live" | "starting" | "stopped" | "error" | "unavailable";

const PILL: Record<PillTone, { label: string; className: string }> = {
  live: { label: "Live", className: "border-brand/30 bg-brand/15 text-brand" },
  starting: { label: "Starting", className: "bg-secondary text-secondary-foreground" },
  stopped: { label: "Stopped", className: "border-border text-muted-foreground" },
  error: { label: "Error", className: "bg-destructive/10 text-destructive" },
  unavailable: { label: "Unavailable", className: "border-border text-muted-foreground" },
};

function StatusPill({ tone }: { tone: PillTone }) {
  const { label, className } = PILL[tone];
  return (
    <Badge variant="outline" className={cn("gap-1", className)}>
      {tone === "starting" ? (
        <LoaderCircle className="animate-spin" aria-hidden="true" />
      ) : (
        <span
          aria-hidden="true"
          className={cn(
            "size-1.5 rounded-full",
            tone === "live" && "bg-brand",
            tone === "error" && "bg-destructive",
            (tone === "stopped" || tone === "unavailable") && "bg-muted-foreground",
          )}
        />
      )}
      {label}
    </Badge>
  );
}
