"use client";

import type { BuildJobUsage } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";

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
}: {
  snapshot: WorkspaceSnapshot | null;
  buildId: string | null;
}) {
  if (!snapshot) {
    if (!buildId) {
      return null;
    }
    return (
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Your app</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Restored from this session&rsquo;s history. File details fill in after your next
            change.
          </p>
        </div>
        <p className="font-mono text-xs text-muted-foreground">build {buildId.slice(0, 8)}</p>
      </header>
    );
  }

  const hiddenEntities = snapshot.entities.length - MAX_ENTITY_BADGES;

  return (
    <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-xl font-semibold tracking-tight">
          {snapshot.name ?? "Your app"}
        </h1>
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

      <dl className="grid shrink-0 grid-cols-[auto_auto] gap-x-3 gap-y-1 text-xs text-muted-foreground">
        <dt>Files</dt>
        <dd className="font-mono tabular-nums text-foreground">{snapshot.fileCount ?? "—"}</dd>
        {snapshot.commitSha ? (
          <>
            <dt>Commit</dt>
            <dd className="font-mono text-foreground">{snapshot.commitSha.slice(0, 12)}</dd>
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
    </header>
  );
}
