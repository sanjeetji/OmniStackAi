"use client";

import { useEffect, useState } from "react";
import { Download, ExternalLink } from "lucide-react";
import type { BuildJobUsage, ProjectGitStatus } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

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
}: {
  snapshot: WorkspaceSnapshot | null;
  buildId: string | null;
  projectId?: string | null;
}) {
  const [gitStatus, setGitStatus] = useState<ProjectGitStatus | null>(null);

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
            <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
              <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download>
                <Download className="size-3.5" />
                Download code
              </a>
            </Button>
          ) : null}
          <p className="font-mono text-xs text-muted-foreground">
            {projectId ? `project ${projectId.slice(0, 8)}` : `build ${(buildId ?? "").slice(0, 8)}`}
          </p>
        </div>
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
          {gitStatus?.repo_url ? (
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
        {snapshot.entities.length > 0 ? (
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
      </div>

      <div className="flex flex-col items-end gap-2 shrink-0">
        {projectId ? (
          <Button asChild variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
            <a href={`/api/projects/${encodeURIComponent(projectId)}/export`} download>
              <Download className="size-3.5" />
              Download code
            </a>
          </Button>
        ) : null}
        <dl className="grid shrink-0 grid-cols-[auto_auto] gap-x-3 gap-y-1 text-xs text-muted-foreground">
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
    </header>
  );
}
