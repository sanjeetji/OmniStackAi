"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Download, ExternalLink, Globe } from "lucide-react";
import type { BuildJobUsage, ProjectGitStatus } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PublishDialog } from "@/components/publish-dialog";
import type { StudioMode } from "./studio-mode";

function GithubIcon({ className = "size-3.5" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}

/** The single "latest state" the workspace header renders - not per chat message. A build's
 * response fully populates this (it's the only response with `name`/`description`/`files`); an
 * edit's narrower response (R-476: no `files` key) patches the parts it has and the caller
 * refreshes `files` separately via `GET /api/jobs/build/{id}/files` (R-474). `files` stays on this
 * type for the Files/Code tabs to read (via `StudioTabs`). */
export interface WorkspaceSnapshot {
  buildId?: string;
  name?: string;
  description?: string;
  entities: string[];
  fileCount?: number;
  commitSha?: string;
  usage?: BuildJobUsage;
  files: string[];
  /** R-557: the apps an ecosystem build produced, and why there is more than one. Empty for a
   * single-app build — a user who received four directories should not have to guess. */
  ecosystemApps?: string[];
  ecosystemReason?: string;
  /** R-559: what was asked for, what was built instead, and why. Present only when the requested
   * stack had no adapter — a user who asked for a Flutter app and received React Native should
   * read the reason here rather than discover it in the repository. */
  substitutions?: StackSubstitution[];
  /** R-560: what happened when the generated code was type-checked. Unlike the fields above this
   * is present on every build, because "we did not check this, and here is why" is a different
   * message from saying nothing. */
  verification?: BuildVerification;
  /** PC-004: endpoints and screens with no real data behind them, by name. */
  notConnected?: { kind: string; name: string; reason: string }[];
  /** PC-084: seconds per build stage, measured on every build. */
  timings?: Record<string, number>;
}

/** R-560: the outcome of compiling the generated web app. Mirrors the agent-engine's record. */
export interface BuildVerification {
  status: "clean" | "repaired" | "failing" | "skipped";
  summary?: string;
  reason?: string;
  generator_failures?: string[];
}

/** R-559: one substituted layer of the stack. Mirrors the agent-engine's `Substitution`. */
export interface StackSubstitution {
  layer: string;
  asked: string;
  built: string;
  reason: string;
}

const MAX_ENTITY_BADGES = 8;

function formatUsd(micros: number): string {
  return `$${(micros / 1_000_000).toFixed(4)}`;
}

/** The compact project header above the tabs (R-493): name, description, entity badges and the
 * build's facts (files, commit, latest-turn model usage). Renders a "restored" header when the
 * session was rehydrated from `?build=` - turns come back from the server, but the file/usage
 * snapshot only exists for builds and edits made in this browser session (an honest, known
 * degradation from R-477 - see studio-chat.tsx). */
export function StudioWorkspace({
  snapshot,
  buildId,
  projectId,
  mode = "engineering",
}: {
  snapshot: WorkspaceSnapshot | null;
  buildId: string | null;
  projectId?: string | null;
  /** PC-005: Vibe hides the machinery (entities, commit, usage, type-check details). */
  mode?: StudioMode;
}) {
  const engineering = mode === "engineering";
  const [gitStatus, setGitStatus] = useState<ProjectGitStatus | null>(null);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    let active = true;
    void (async () => {
      try {
        const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/git`);
        if (resp.ok && active) {
          const data: ProjectGitStatus = await resp.json();
          setGitStatus(data);
        }
      } catch {
        // Silently ignore background git status fetch error in workspace header
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  if (!snapshot || !snapshot.name) {
    if (!buildId && !projectId) {
      return null;
    }
    const fileCount = snapshot?.files.length ?? 0;
    return (
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Your app</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Restored from this session&rsquo;s history.{" "}
            {fileCount > 0
              ? `${fileCount.toLocaleString("en-US")} files are listed in Files and Code; entity and usage details fill in after your next change.`
              : "File details fill in after your next change."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {projectId ? (
            <>
              <Button
                variant="default"
                size="sm"
                className="h-8 gap-1.5 text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm"
                onClick={() => setPublishDialogOpen(true)}
              >
                <Globe className="size-3.5" />
                Publish
              </Button>
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download>
                  <Download className="size-3.5" />
                  Download code
                </a>
              </Button>
            </>
          ) : null}
          <p className="font-mono text-xs text-muted-foreground">
            {projectId ? `project ${projectId.slice(0, 8)}` : `build ${(buildId ?? "").slice(0, 8)}`}
          </p>
        </div>
        {projectId && (
          <PublishDialog
            projectId={projectId}
            projectName={snapshot?.name ?? "Your App"}
            open={publishDialogOpen}
            onOpenChange={setPublishDialogOpen}
          />
        )}
      </header>
    );
  }

  const hiddenEntities = snapshot.entities.length - MAX_ENTITY_BADGES;

  return (
    <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="truncate text-xl font-semibold tracking-tight">
            {snapshot.name ?? "Your app"}
          </h1>
          {engineering && gitStatus?.repo_url ? (
            <a
              href={gitStatus.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground underline-offset-4 hover:underline"
              title={gitStatus.repo_full_name ?? "GitHub Repository"}
            >
              <GithubIcon className="size-3.5" />
              <span>GitHub</span>
              <ExternalLink className="size-3 opacity-60" />
            </a>
          ) : null}
        </div>
        {snapshot.description ? (
          <p className="mt-0.5 text-pretty text-sm text-muted-foreground">{snapshot.description}</p>
        ) : null}
        {engineering && snapshot.entities.length > 0 ? (
          <ul aria-label="Entities" className="mt-2 flex flex-wrap gap-1.5">
            {snapshot.entities.slice(0, MAX_ENTITY_BADGES).map((entity) => (
              <li key={entity}>
                <Badge variant="secondary">{entity}</Badge>
              </li>
            ))}
            {hiddenEntities > 0 ? (
              <li>
                <Badge variant="outline">+{hiddenEntities} more</Badge>
              </li>
            ) : null}
          </ul>
        ) : null}
        {snapshot.ecosystemApps && snapshot.ecosystemApps.length > 1 ? (
          <div className="mt-3 rounded-lg border border-border/60 bg-muted/40 p-3">
            <p className="text-xs font-medium text-foreground">
              {snapshot.ecosystemApps.length} apps, one API and one database
            </p>
            <ul aria-label="Apps in this project" className="mt-1.5 flex flex-wrap gap-1.5">
              {snapshot.ecosystemApps.map((app) => (
                <li key={app}>
                  <Badge variant="secondary">{app}</Badge>
                </li>
              ))}
            </ul>
            {snapshot.ecosystemReason ? (
              // Rendered as text, never as HTML: it is generated copy, and there is no reason for
              // it to be able to inject markup into the console.
              <p className="mt-2 text-pretty text-xs text-muted-foreground">
                {snapshot.ecosystemReason}
              </p>
            ) : null}
          </div>
        ) : null}
        {snapshot.verification && (engineering || snapshot.verification.status === "failing") ? (
          <div className="mt-3 rounded-lg border border-border/60 bg-muted/40 p-3">
            <p className="text-xs font-medium text-foreground">
              {snapshot.verification.status === "clean"
                ? "Type-checked"
                : snapshot.verification.status === "repaired"
                  ? "Type-checked and repaired"
                  : snapshot.verification.status === "failing"
                    ? "Type-check found problems"
                    : "Not type-checked"}
            </p>
            {/* Text, never HTML: generated copy has no reason to inject markup into the console. */}
            <p className="mt-1 text-pretty text-xs text-muted-foreground">
              {snapshot.verification.summary || snapshot.verification.reason}
            </p>
          </div>
        ) : null}
        {snapshot.substitutions && snapshot.substitutions.length > 0 ? (
          <div className="mt-3 rounded-lg border border-border/60 bg-muted/40 p-3">
            <p className="text-xs font-medium text-foreground">
              Built with a different stack than you asked for
            </p>
            <ul aria-label="Stack substitutions" className="mt-1.5 space-y-1.5">
              {snapshot.substitutions.map((substitution) => (
                // Keyed by layer: one substitution per layer of the stack, so it is unique.
                <li key={substitution.layer} className="text-pretty text-xs text-muted-foreground">
                  {/* Text, never HTML — same rule as the ecosystem reason above. */}
                  {substitution.reason}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {snapshot.notConnected && snapshot.notConnected.length > 0 ? (
          <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
            <p className="text-xs font-medium text-foreground">Not connected to data yet</p>
            <p className="mt-1 text-pretty text-xs text-muted-foreground">
              These parts say so in the app instead of pretending. Ask for them in the chat and they are built with a
              real API and database.
            </p>
            <ul aria-label="Not connected to data yet" className="mt-1.5 space-y-1">
              {snapshot.notConnected.map((gap) => (
                <li key={`${gap.kind}:${gap.name}`} className="text-pretty text-xs text-muted-foreground">
                  {/* Text, never HTML. */}
                  <span className="font-mono text-foreground">{gap.name}</span>
                  {engineering ? ` — ${gap.reason}` : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <div className="flex flex-col items-end gap-2 shrink-0">
        {projectId ? (
          <div className="flex items-center gap-2">
            <Button
              variant="default"
              size="sm"
              className="h-8 gap-1.5 text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-medium shadow-sm"
              onClick={() => setPublishDialogOpen(true)}
            >
              <Globe className="size-3.5" />
              Publish
            </Button>
            {engineering ? (
              <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
                <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download>
                  <Download className="size-3.5" />
                  Download code
                </a>
              </Button>
            ) : null}
          </div>
        ) : null}
        {snapshot.timings?.total ? (
          // PC-084: how long the user actually waited, on every build. Vibe gets one number;
          // Engineering sees where it went.
          <p className="text-xs text-muted-foreground" aria-label="Build time">
            Ready in {snapshot.timings.total.toFixed(0)}s
            {engineering
              ? ` · plan ${(snapshot.timings.plan ?? 0).toFixed(1)}s · assemble ${(snapshot.timings.assemble ?? 0).toFixed(1)}s` +
                ` · checks ${(snapshot.timings.verify ?? 0).toFixed(1)}s · preview ${(snapshot.timings.preview ?? 0).toFixed(1)}s`
              : null}
          </p>
        ) : null}
        <dl hidden={!engineering} className="grid shrink-0 grid-cols-[auto_auto] gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <dt>Files</dt>
          <dd className="font-mono tabular-nums text-foreground">{snapshot.fileCount ?? "—"}</dd>
          {snapshot.commitSha ? (
            <>
              <dt>Commit</dt>
              <dd className="font-mono text-foreground">{snapshot.commitSha.slice(0, 12)}</dd>
            </>
          ) : null}
          {gitStatus?.ahead_by && gitStatus.ahead_by > 0 ? (
            <>
              <dt>Git Sync</dt>
              <dd>
                <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-amber-500 border-amber-500/30">
                  {gitStatus.ahead_by} {gitStatus.ahead_by === 1 ? "commit" : "commits"} ahead
                </Badge>
              </dd>
            </>
          ) : null}
          {snapshot.usage ? (
            <>
              <dt>Latest turn</dt>
              <dd className="font-mono tabular-nums text-foreground">
                {snapshot.usage.successful_calls}/{snapshot.usage.total_calls} calls ·{" "}
                {snapshot.usage.input_tokens.toLocaleString("en-US")} in ·{" "}
                {snapshot.usage.output_tokens.toLocaleString("en-US")} out ·{" "}
                {formatUsd(snapshot.usage.cost_micros_usd)}
              </dd>
            </>
          ) : null}
        </dl>
      </div>
      {projectId && (
        <PublishDialog
          projectId={projectId}
          projectName={snapshot.name ?? "Your App"}
          open={publishDialogOpen}
          onOpenChange={setPublishDialogOpen}
        />
      )}
    </header>
  );
}
