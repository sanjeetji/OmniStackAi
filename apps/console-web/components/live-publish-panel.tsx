"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, ExternalLink, Globe, Loader2, RotateCcw, Trash2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { LiveStatus } from "@/lib/control-plane";

/** PC-008: publish the whole app — database, API, web app and admin console — to one live URL.
 *
 * Publishing runs on the server in the background; this panel starts it and polls until it is live
 * or has failed, showing the step it is on. A failed publish keeps the previous release running and
 * says which step failed and why. Rollback and unpublish act on the same app.
 */
const STEPS: Record<string, string> = {
  bundle: "Preparing production files",
  build: "Building in production mode",
  database: "Starting the database",
  migrate: "Applying the database schema",
  start: "Starting the release",
  check: "Checking sign-up, sign-in and every page",
  live: "Live",
};

export function LivePublishPanel({ projectId }: { projectId: string }) {
  const [live, setLive] = useState<LiveStatus | null>(null);
  const [busy, setBusy] = useState<"publish" | "rollback" | "unpublish" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showLog, setShowLog] = useState(false);
  // Bumped to start watching again (after Publish); the effect polls while a publish runs.
  const [watch, setWatch] = useState(0);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/projects/${projectId}/live`, { cache: "no-store" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Could not read the publish status");
      setLive(data as LiveStatus);
      setError(null);
      return data as LiveStatus;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read the publish status");
      return null;
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const run = async () => {
      const data = await load();
      if (cancelled) return;
      if (data?.status === "publishing") {
        timer = setTimeout(run, 2000);
      } else {
        setBusy(null);
      }
    };
    void run();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [load, watch]);

  const act = async (action: "publish" | "rollback" | "unpublish") => {
    if (action === "unpublish" && !window.confirm("Take the live app offline? Its database is kept.")) return;
    setBusy(action);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/live`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Could not ${action}`);
      setLive(data as LiveStatus);
      if (action === "publish") {
        setWatch((n) => n + 1);
        return;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not ${action}`);
    }
    setBusy(null);
  };

  const publishing = live?.status === "publishing" || busy === "publish";
  const earlier = (live?.releases ?? []).filter((r) => r.status === "previous").length > 0;

  return (
    <section aria-label="Publish the whole app" className="rounded-lg border bg-muted/20 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 font-medium">
            <Globe className="size-4 text-primary" aria-hidden="true" />
            Whole app
            <Badge variant="secondary">Recommended</Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Database, API, web app and admin console together at one address — built for production,
            checked with a real sign-up and sign-in, with rollback.
          </p>
        </div>
        {live?.status === "live" && (
          <Badge className="shrink-0 gap-1" variant="outline">
            <CheckCircle2 className="size-3 text-emerald-500" aria-hidden="true" /> Live
          </Badge>
        )}
      </div>

      {live?.url && live.status !== "unpublished" && (
        <a href={live.url} target="_blank" rel="noreferrer"
           className="flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:border-primary">
          <span className="truncate">{live.url}</span>
          <ExternalLink className="size-3.5 shrink-0" aria-hidden="true" />
        </a>
      )}
      {live?.surfaces && live.surfaces.length > 1 && live.status === "live" && (
        <ul className="flex flex-wrap gap-2 text-xs">
          {live.surfaces.map((s) => (
            <li key={s.name}>
              <a href={s.url} target="_blank" rel="noreferrer" className="underline underline-offset-2">
                {s.name === "web" ? "Site" : s.name === "admin" ? "Admin console" : s.name}
              </a>
            </li>
          ))}
          <li className="text-muted-foreground">API under /api</li>
        </ul>
      )}

      {live?.admin && live.status === "live" && (
        <details className="rounded-md border bg-background px-3 py-2 text-xs">
          <summary className="cursor-pointer font-medium">Admin sign-in for the live app</summary>
          <p className="mt-2 text-muted-foreground">
            The development password was replaced when you published. Only you can see this.
          </p>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono">
            <dt className="text-muted-foreground">Email</dt>
            <dd>{live.admin.email}</dd>
            <dt className="text-muted-foreground">Password</dt>
            <dd className="select-all break-all">{live.admin.password}</dd>
          </dl>
        </details>
      )}

      {publishing && (
        <p role="status" className="flex items-center gap-2 text-sm">
          <Loader2 className="size-4 animate-spin text-primary" aria-hidden="true" />
          {STEPS[live?.step ?? ""] ?? "Starting"}…
        </p>
      )}
      {live?.error && !publishing && (
        <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
          <XCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{live.message}</span>
        </p>
      )}
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}

      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => act("publish")} disabled={publishing || busy !== null}>
          {publishing ? "Publishing…" : live?.status === "live" ? "Publish again" : "Publish whole app"}
        </Button>
        {earlier && live?.status === "live" && (
          <Button size="sm" variant="outline" onClick={() => act("rollback")} disabled={busy !== null || publishing}>
            <RotateCcw className="size-3.5" aria-hidden="true" /> Roll back
          </Button>
        )}
        {live?.status === "live" && (
          <Button size="sm" variant="ghost" onClick={() => act("unpublish")} disabled={busy !== null || publishing}>
            <Trash2 className="size-3.5" aria-hidden="true" /> Unpublish
          </Button>
        )}
        {(live?.log?.length ?? 0) > 0 && (
          <Button size="sm" variant="ghost" onClick={() => setShowLog((v) => !v)}>
            {showLog ? "Hide log" : "Show log"}
          </Button>
        )}
      </div>
      {showLog && (
        <pre className="max-h-48 overflow-auto rounded-md bg-background p-2 text-[11px] leading-relaxed">
          {(live?.log ?? []).slice(-60).join("\n")}
        </pre>
      )}
      {live?.target && <p className="text-[11px] text-muted-foreground">Runs on: {live.target}</p>}
    </section>
  );
}
