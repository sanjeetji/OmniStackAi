"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, ExternalLink, KeyRound, Loader2, Smartphone, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { StoreAction, StorePlatform, StoreResult } from "@/lib/control-plane";

/** R-574: the project's mobile app to Google Play and the App Store.
 *
 * Builds run in Expo's cloud (EAS), so an iOS build needs no Mac. The credentials are the app
 * owner's and live in the project's secrets; this panel lists what is missing for each store and
 * where to get it, and runs the build or the upload once they are there. A project without a
 * mobile app shows nothing.
 */
const STORES: { platform: StorePlatform; name: string }[] = [
  { platform: "android", name: "Google Play" },
  { platform: "ios", name: "App Store" },
];

async function post(projectId: string, platform: StorePlatform, action: StoreAction): Promise<StoreResult> {
  const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/stores`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform, action }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `The store request failed (${res.status})`);
  return data as StoreResult;
}

export function StorePublishPanel({ projectId }: { projectId: string }) {
  const [checks, setChecks] = useState<Partial<Record<StorePlatform, StoreResult>>>({});
  const [runs, setRuns] = useState<Partial<Record<StorePlatform, StoreResult>>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const results = await Promise.all(STORES.map((st) => post(projectId, st.platform, "check")));
        if (!cancelled) setChecks(Object.fromEntries(results.map((r) => [r.platform, r])));
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    };
    void check();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const run = async (platform: StorePlatform, action: "build" | "submit") => {
    setBusy(`${platform}:${action}`);
    try {
      const result = await post(projectId, platform, action);
      setRuns((prev) => ({ ...prev, [platform]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };

  const noApp = Object.values(checks).some((c) => c && !c.details?.app && c.output.includes("no mobile app"));
  if (noApp) return null;

  return (
    <section className="space-y-3 rounded-lg border border-border/60 p-4" aria-labelledby="store-publish-title">
      <div className="flex items-center gap-2">
        <Smartphone className="h-4 w-4 text-primary" aria-hidden />
        <h3 id="store-publish-title" className="text-sm font-semibold">App stores</h3>
      </div>
      <p className="text-xs text-muted-foreground">
        The mobile app is built in Expo&apos;s cloud and uploaded with your own store accounts. Their credentials are
        this project&apos;s secrets.
      </p>
      {error ? <p role="alert" className="text-xs text-destructive">{error}</p> : null}
      {STORES.map(({ platform, name }) => {
        const check = checks[platform];
        const last = runs[platform];
        if (!check) {
          return (
            <div key={platform} className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> Checking {name}…
            </div>
          );
        }
        return (
          <div key={platform} className="space-y-2 rounded-md border border-border/60 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium">{name}</span>
              {check.ok ? (
                <Badge variant="outline" className="gap-1"><CheckCircle2 className="h-3 w-3" aria-hidden /> Ready</Badge>
              ) : (
                <Badge variant="outline" className="gap-1"><KeyRound className="h-3 w-3" aria-hidden /> Needs {check.missing.length} credential{check.missing.length === 1 ? "" : "s"}</Badge>
              )}
            </div>
            {check.missing.length > 0 ? (
              <ul className="space-y-1 text-xs">
                {check.missing.map((m) => (
                  <li key={m.name}>
                    <code className="rounded bg-muted px-1 py-0.5">{m.name}</code> — {m.what}.{" "}
                    <span className="text-muted-foreground">{m.where}</span>
                  </li>
                ))}
                <li>
                  <Link href={`/studio/${encodeURIComponent(projectId)}/manage?section=secrets`} className="font-medium text-primary hover:underline">
                    Add them in Manage → Secrets
                  </Link>
                </li>
              </ul>
            ) : null}
            {check.warnings.map((w) => (
              <p key={w} className="flex gap-1.5 text-xs text-muted-foreground">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden /> {w}
              </p>
            ))}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" disabled={!check.details?.can_build || busy !== null} onClick={() => run(platform, "build")}>
                {busy === `${platform}:build` ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Smartphone className="h-4 w-4" aria-hidden />}
                Build for {name}
              </Button>
              <Button size="sm" variant="outline" disabled={!check.details?.can_submit || busy !== null} onClick={() => run(platform, "submit")}>
                {busy === `${platform}:submit` ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Upload className="h-4 w-4" aria-hidden />}
                Upload the latest build
              </Button>
            </div>
            {last ? (
              <div className="space-y-1 text-xs">
                <p className={last.ok ? "text-foreground" : "text-destructive"}>
                  {last.ok ? (last.action === "build" ? "Build queued in Expo's cloud." : "Upload started.") : `The ${last.action} did not go through.`}
                  {last.details?.url ? (
                    <a href={last.details.url} target="_blank" rel="noreferrer" className="ml-1 inline-flex items-center gap-1 text-primary hover:underline">
                      Follow it on expo.dev <ExternalLink className="h-3 w-3" aria-hidden />
                    </a>
                  ) : null}
                </p>
                {last.output ? <pre className="max-h-40 overflow-auto rounded bg-muted p-2 text-[11px] whitespace-pre-wrap">{last.output.slice(-1500)}</pre> : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}
