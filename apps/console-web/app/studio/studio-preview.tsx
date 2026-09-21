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
import { MultiAppPreview } from "./studio-preview-apps";

const POLL_INTERVAL_MS = 5000;
// Template projects start in the background (R-520); poll faster while they do.
const STARTING_POLL_INTERVAL_MS = 1500;

type ErrorBody = { error?: string };

async function getJSON(path: string): Promise<{ status: number; body: PreviewStatus | ErrorBody }> {
  const response = await fetch(path, { method: "GET" });
  const body = (await response.json().catch(() => ({}))) as PreviewStatus | ErrorBody;
  return { status: response.status, body };
}

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

const PHASE_LABELS: Record<string, string> = {
  install: "Installing dependencies…",
  migrate: "Running database migrations…",
  start: "Starting development servers…",
  ready: "Application ready",
};

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
  const [phase, setPhase] = useState<{ starting: boolean; elapsedMs: number; fetchError: string | null }>({
    starting: false,
    elapsedMs: 0,
    fetchError: null,
  });
  const [disabled, setDisabled] = useState(false);
  const [busy, setBusy] = useState(false);
  const [preset, setPreset] = useState<PresetKey>("desktop");
  const startedAtRef = useRef<number | null>(null);

  // Auto-start or refresh preview for this project / build
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

        // Check current status first if projectId is present
        if (projectId && previewVersion === 0) {
          const { status: checkStatus, body: checkBody } = await getJSON(previewUrl);
          if (cancelled) return;
          if (checkStatus === 404) {
            setDisabled(true);
            setStatus(null);
            return;
          }
          const curr = checkBody as PreviewStatus;
          // "starting": a template preview is already on its way (e.g. after a page reload);
          // follow it instead of restarting it.
          if (curr.status === "ready" || curr.status === "starting") {
            setDisabled(false);
            setStatus(curr);
            setPhase((p) => ({ ...p, starting: false }));
            return;
          }
        }

        // Start (or re-start) preview
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

  // Real elapsed time while starting
  useEffect(() => {
    if (!phase.starting) return;
    const tick = setInterval(() => {
      setPhase((p) => ({ ...p, elapsedMs: Date.now() - (startedAtRef.current ?? Date.now()) }));
    }, 500);
    return () => clearInterval(tick);
  }, [phase.starting]);

  // Follow a template preview that is starting in the background (R-520)
  useEffect(() => {
    if (!projectId || disabled || status?.status !== "starting") return;
    const url = `/api/projects/${encodeURIComponent(projectId)}/preview`;
    const interval = setInterval(async () => {
      try {
        const { status: httpStatus, body } = await getJSON(url);
        if (httpStatus === 404) {
          setDisabled(true);
          return;
        }
        if (body && "status" in body) {
          setStatus(body as PreviewStatus);
        }
      } catch {
        // Transient fetch failure is ignored until next tick
      }
    }, STARTING_POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [projectId, disabled, status?.status]);

  // Periodic liveness check while ready
  useEffect(() => {
    if (!buildId && !projectId) return;
    if (disabled || status?.status !== "ready") return;

    const pollUrl = projectId
      ? `/api/projects/${encodeURIComponent(projectId)}/preview`
      : "/api/preview";

    const interval = setInterval(async () => {
      try {
        const { status: httpStatus, body } = await getJSON(pollUrl);
        if (httpStatus === 404) {
          setDisabled(true);
          return;
        }
        if (body && "status" in body) {
          setStatus(body as PreviewStatus);
        }
      } catch {
        // Transient fetch failure is ignored until next tick
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [buildId, projectId, disabled, status?.status]);

  async function handleRestart() {
    setBusy(true);
    try {
      const restartUrl = projectId
        ? `/api/projects/${encodeURIComponent(projectId)}/preview`
        : "/api/preview/restart";
      const { status: httpStatus, body } = await postJSON(restartUrl);
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
      const stopUrl = projectId
        ? `/api/projects/${encodeURIComponent(projectId)}/preview/stop`
        : "/api/preview/stop";
      const { status: httpStatus, body } = await postJSON(stopUrl);
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

  if (!buildId && !projectId) return null;

  if (disabled) {
    return (
      <div className="grid justify-items-center gap-2 rounded-xl border border-dashed border-border/70 px-6 py-12 text-center">
        <MonitorOff className="size-5 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm font-medium">Live preview isn&rsquo;t running</p>
        <p className="max-w-sm text-pretty text-sm text-muted-foreground">
          This server runs in build-only mode. Restart it with:
        </p>
        <code className="mt-1 rounded-lg bg-muted px-2.5 py-1.5 font-mono text-xs">
          ./scripts/omnistack.sh up
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
    const activePhaseLabel = (status?.phase && PHASE_LABELS[status.phase]) || "Starting preview…";
    return (
      <div className="overflow-hidden rounded-xl border border-border/60 bg-card" aria-busy="true">
        <div className="flex items-center gap-2 border-b border-border/60 px-3 py-2 text-xs">
          <StatusPill tone="starting" />
          <span className="text-muted-foreground tabular-nums">
            {activePhaseLabel} {Math.round(phase.elapsedMs / 1000)}s
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

  if (projectId && status.kind === "multi" && (status.status === "ready" || status.status === "starting")) {
    return (
      <MultiAppPreview
        projectId={projectId}
        status={status}
        busy={busy}
        onRestart={handleRestart}
        onStop={handleStop}
      />
    );
  }

  if (status.status === "ready" && status.web_url) {
    const active = WIDTH_PRESETS.find((entry) => entry.key === preset) ?? WIDTH_PRESETS[0];
    const proxyUrl = projectId ? `/preview/${encodeURIComponent(projectId)}/` : status.web_url;
    const targetUrl = proxyUrl;

    return (
      <div className="overflow-hidden rounded-xl border border-border/60 bg-card">
        <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-3 py-2">
          <StatusPill tone="live" />
          <a
            href={targetUrl}
            target="_blank"
            rel="noreferrer"
            className="min-w-0 flex-1 truncate font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            {targetUrl}
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
            <a href={targetUrl} target="_blank" rel="noreferrer">
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
              src={targetUrl}
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
          {status.status === "stopped" ? "Start" : "Restart"}
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
