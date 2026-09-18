"use client";

import { useState, type FormEvent } from "react";
import type { BuildFileContentResponse, BuildJobResponse } from "@/lib/control-plane";
import { CreditIcon } from "./studio-icons";

interface StudioFormProps {
  initialCreditBalance: number;
}

type BuildErrorBody = { error?: string };

export default function StudioForm({ initialCreditBalance }: StudioFormProps) {
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BuildJobResponse | null>(null);
  const [creditBalance, setCreditBalance] = useState(initialCreditBalance);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const response = await fetch("/api/jobs/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const body = (await response
        .json()
        .catch(() => ({}))) as Partial<BuildJobResponse> & BuildErrorBody;
      if (!response.ok) {
        setError(body.error ?? `build failed with status ${response.status}`);
        return;
      }
      setResult(body as BuildJobResponse);
      if (typeof body.credit_balance === "number") {
        setCreditBalance(body.credit_balance);
      }
    } catch {
      setError("could not reach the server");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="studio-credit-row">
        <span className="pill pill--accent">
          <CreditIcon width={14} height={14} />
          {creditBalance} credits
        </span>
      </div>

      <section className="panel">
        <h2>Build an app</h2>
        <p className="studio-intro muted">
          Describe an app in plain English — it becomes a real, owned Git repository.
        </p>
        {error ? <div className="error-banner">{error}</div> : null}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="prompt">Describe the app</label>
            <textarea
              id="prompt"
              name="prompt"
              rows={4}
              required
              placeholder="A task tracker where users create projects and each project has tasks with a title, status, and due date"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              disabled={submitting}
            />
          </div>
          <button
            className="button"
            type="submit"
            disabled={submitting || prompt.trim().length === 0}
          >
            {submitting ? "Building… this can take a minute or more" : "Build"}
          </button>
        </form>
      </section>

      {result ? <BuildResult result={result} /> : null}
    </>
  );
}

function BuildResult({ result }: { result: BuildJobResponse }) {
  return (
    <section className="panel">
      <h2>{result.name ?? "Build result"}</h2>
      {result.description ? <p className="lede">{result.description}</p> : null}

      <div className="grid">
        <div className="stat">
          <div className="label">Files</div>
          <div className="value">{result.file_count ?? "—"}</div>
        </div>
        <div className="stat">
          <div className="label">Credits spent</div>
          <div className="value">{result.credits_spent}</div>
        </div>
        <div className="stat">
          <div className="label">Credit balance</div>
          <div className="value">{result.credit_balance}</div>
        </div>
        {result.commit_sha ? (
          <div className="stat">
            <div className="label">Commit</div>
            <div className="value mono" style={{ fontSize: 13 }}>
              {result.commit_sha.slice(0, 12)}
            </div>
          </div>
        ) : null}
      </div>

      {result.entities && result.entities.length > 0 ? (
        <>
          <h3 style={{ marginTop: 20, fontSize: 15 }}>Entities</h3>
          <div className="pill-row">
            {result.entities.map((entity) => (
              <span key={entity} className="pill">
                {entity}
              </span>
            ))}
          </div>
        </>
      ) : null}

      {result.usage ? (
        <>
          <h3 style={{ marginTop: 20, fontSize: 15 }}>Model usage</h3>
          <div className="grid">
            <div className="stat">
              <div className="label">Calls</div>
              <div className="value">
                {result.usage.successful_calls}/{result.usage.total_calls}
              </div>
            </div>
            <div className="stat">
              <div className="label">Input tokens</div>
              <div className="value">{result.usage.input_tokens}</div>
            </div>
            <div className="stat">
              <div className="label">Output tokens</div>
              <div className="value">{result.usage.output_tokens}</div>
            </div>
            <div className="stat">
              <div className="label">Cost</div>
              <div className="value">${(result.usage.cost_micros_usd / 1_000_000).toFixed(4)}</div>
            </div>
          </div>
        </>
      ) : null}

      {result.files && result.files.length > 0 ? (
        <FileBrowser buildId={result.id} files={result.files} />
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
