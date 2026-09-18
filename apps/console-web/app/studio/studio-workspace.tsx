"use client";

import { useState } from "react";
import type { BuildFileContentResponse, BuildJobUsage } from "@/lib/control-plane";

/** The single "latest state" the workspace panel renders - not per chat message. A build's
 * response fully populates this (it's the only response with `name`/`description`/`files`); an
 * edit's narrower response (R-476: no `files` key) patches the parts it has and the caller
 * refreshes `files` separately via `GET /api/jobs/build/{id}/files` (R-474). */
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

      {snapshot.files.length > 0 ? (
        <FileBrowser buildId={snapshot.buildId} files={snapshot.files} />
      ) : null}
    </section>
  );
}

type FileErrorBody = { error?: string };

function FileBrowser({ buildId, files }: { buildId?: string; files: string[] }) {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [content, setContent] = useState<BuildFileContentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  async function openFile(path: string) {
    setSelectedPath(path);
    setContent(null);
    setFileError(null);
    if (!buildId) {
      setFileError("this build has no browsable id");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(
        `/api/jobs/build/${encodeURIComponent(buildId)}/file?path=${encodeURIComponent(path)}`,
      );
      const body = (await response
        .json()
        .catch(() => ({}))) as Partial<BuildFileContentResponse> & FileErrorBody;
      if (!response.ok) {
        setFileError(body.error ?? `could not read file (status ${response.status})`);
        return;
      }
      setContent(body as BuildFileContentResponse);
    } catch {
      setFileError("could not reach the server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h3 style={{ marginTop: 20, fontSize: 15 }}>Files ({files.length})</h3>
      <div className="overflow file-list">
        <ul>
          {files.slice(0, 40).map((file) => (
            <li key={file}>
              <button
                type="button"
                className={
                  file === selectedPath ? "file-list-item mono selected" : "file-list-item mono"
                }
                onClick={() => openFile(file)}
              >
                {file}
              </button>
            </li>
          ))}
        </ul>
      </div>
      {files.length > 40 ? <p className="muted">+{files.length - 40} more files</p> : null}

      {selectedPath ? (
        <div className="file-viewer">
          <div className="file-viewer-header mono">{selectedPath}</div>
          {loading ? <p className="muted">Loading…</p> : null}
          {fileError ? <div className="error-banner">{fileError}</div> : null}
          {content && content.binary ? <p className="muted">Binary file, not shown.</p> : null}
          {content && !content.binary ? (
            <pre className="mono overflow file-viewer-content">{content.content}</pre>
          ) : null}
          {content?.truncated ? (
            <p className="muted">File truncated for display (it&apos;s larger than the preview limit).</p>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
