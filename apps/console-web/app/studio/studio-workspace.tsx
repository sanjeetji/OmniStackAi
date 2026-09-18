"use client";

import type { BuildJobUsage } from "@/lib/control-plane";

/** The single "latest state" the workspace panel renders - not per chat message. A build's
 * response fully populates this (it's the only response with `name`/`description`/`files`); an
 * edit's narrower response (R-476: no `files` key) patches the parts it has and the caller
 * refreshes `files` separately via `GET /api/jobs/build/{id}/files` (R-474). `files` stays on this
 * type for the R-481 Files/Code tabs to read (via `StudioTabs`) - this component itself no longer
 * renders a file browser directly, that moved into the tabbed workspace. */
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

export function StudioWorkspace({ snapshot }: { snapshot: WorkspaceSnapshot | null }) {
  if (!snapshot) {
    return (
      <section className="panel workspace-empty">
        <p className="muted">
          Nothing built yet — describe an app in the chat to get started.
        </p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>{snapshot.name ?? "Build result"}</h2>
      {snapshot.description ? <p className="lede">{snapshot.description}</p> : null}

      <div className="grid">
        <div className="stat">
          <div className="label">Files</div>
          <div className="value">{snapshot.fileCount ?? "—"}</div>
        </div>
        {snapshot.commitSha ? (
          <div className="stat">
            <div className="label">Commit</div>
            <div className="value mono" style={{ fontSize: 13 }}>
              {snapshot.commitSha.slice(0, 12)}
            </div>
          </div>
        ) : null}
      </div>

      {snapshot.entities.length > 0 ? (
        <>
          <h3 style={{ marginTop: 20, fontSize: 15 }}>Entities</h3>
          <div className="pill-row">
            {snapshot.entities.map((entity) => (
              <span key={entity} className="pill">
                {entity}
              </span>
            ))}
          </div>
        </>
      ) : null}

      {snapshot.usage ? (
        <>
          <h3 style={{ marginTop: 20, fontSize: 15 }}>Model usage (latest turn)</h3>
          <div className="grid">
            <div className="stat">
              <div className="label">Calls</div>
              <div className="value">
                {snapshot.usage.successful_calls}/{snapshot.usage.total_calls}
              </div>
            </div>
            <div className="stat">
              <div className="label">Input tokens</div>
              <div className="value">{snapshot.usage.input_tokens}</div>
            </div>
            <div className="stat">
              <div className="label">Output tokens</div>
              <div className="value">{snapshot.usage.output_tokens}</div>
            </div>
            <div className="stat">
              <div className="label">Cost</div>
              <div className="value">${(snapshot.usage.cost_micros_usd / 1_000_000).toFixed(4)}</div>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
