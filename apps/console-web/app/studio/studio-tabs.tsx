"use client";

import { useEffect, useState } from "react";
import type { BuildFileContentResponse, ProblemsReport } from "@/lib/control-plane";
import { languageForPath, tokenizeCodeLine } from "./code-highlight";
import { FileIcon, WarningIcon } from "./studio-icons";
import { StudioPreview } from "./studio-preview";
import type { WorkspaceSnapshot } from "./studio-workspace";

type TabKey = "preview" | "files" | "code" | "problems";

const TABS: { key: TabKey; label: string }[] = [
  { key: "preview", label: "Preview" },
  { key: "files", label: "Files" },
  { key: "code", label: "Code" },
  { key: "problems", label: "Problems" },
];

/** The four-tab workspace (R-481): Preview/Files/Code/Problems, assembling R-474 (files), R-479
 * (preview), and R-480 (problems) into one shell. Files and Code stay separate real tabs, per the
 * founder's explicit choice - Files is a lightweight browse list, Code is the full reader, both
 * reading/writing one lifted `selectedFile` so picking a file in Files opens it in Code. */
export function StudioTabs({
  buildId,
  previewVersion,
  workspace,
}: {
  buildId: string | null;
  previewVersion: number;
  workspace: WorkspaceSnapshot | null;
}) {
  const [activeTab, setActiveTab] = useState<TabKey>("preview");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  if (!buildId) {
    return null;
  }

  function openFileInCode(path: string) {
    setSelectedFile(path);
    setActiveTab("code");
  }

  const files = workspace?.files ?? [];

  return (
    <div className="panel studio-tabs">
      <div className="tab-bar" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            className={activeTab === tab.key ? "tab-button tab-button--active" : "tab-button"}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="tab-panel">
        {activeTab === "preview" ? (
          <StudioPreview buildId={buildId} previewVersion={previewVersion} />
        ) : null}
        {activeTab === "files" ? (
          <FilesTab files={files} selectedFile={selectedFile} onOpen={openFileInCode} />
        ) : null}
        {activeTab === "code" ? (
          <CodeTab buildId={buildId} files={files} selectedFile={selectedFile} onSelect={setSelectedFile} />
        ) : null}
        {activeTab === "problems" ? <ProblemsTab buildId={buildId} /> : null}
      </div>
    </div>
  );
}

function FilesTab({
  files,
  selectedFile,
  onOpen,
}: {
  files: string[];
  selectedFile: string | null;
  onOpen: (path: string) => void;
}) {
  if (files.length === 0) {
    return <p className="muted tab-empty">No files yet.</p>;
  }
  return (
    <div className="overflow file-list">
      <ul>
        {files.slice(0, 200).map((file) => (
          <li key={file}>
            <button
              type="button"
              className={file === selectedFile ? "file-list-item mono selected" : "file-list-item mono"}
              onClick={() => onOpen(file)}
            >
              <FileIcon width={14} height={14} /> {file}
            </button>
          </li>
        ))}
      </ul>
      {files.length > 200 ? <p className="muted">+{files.length - 200} more files</p> : null}
    </div>
  );
}

type ErrorBody = { error?: string };

function CodeTab({
  buildId,
  files,
  selectedFile,
  onSelect,
}: {
  buildId: string;
  files: string[];
  selectedFile: string | null;
  onSelect: (path: string) => void;
}) {
  const [content, setContent] = useState<BuildFileContentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedFile) {
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `/api/jobs/build/${encodeURIComponent(buildId)}/file?path=${encodeURIComponent(selectedFile)}`,
        );
        const body = (await response.json().catch(() => ({}))) as Partial<BuildFileContentResponse> &
          ErrorBody;
        if (cancelled) return;
        if (!response.ok) {
          setError(body.error ?? `could not read file (status ${response.status})`);
          return;
        }
        setContent(body as BuildFileContentResponse);
      } catch {
        if (!cancelled) setError("could not reach the server");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [buildId, selectedFile]);

  return (
    <div className="code-tab">
      <select
        className="code-file-select"
        aria-label="Choose a file to view"
        value={selectedFile ?? ""}
        onChange={(event) => onSelect(event.target.value)}
      >
        <option value="" disabled>
          Choose a file…
        </option>
        {files.map((file) => (
          <option key={file} value={file}>
            {file}
          </option>
        ))}
      </select>
      {!selectedFile ? <p className="muted tab-empty">Choose a file to view its code.</p> : null}
      {loading ? <p className="muted">Loading…</p> : null}
      {error ? <div className="error-banner">{error}</div> : null}
      {content && content.binary ? <p className="muted">Binary file, not shown.</p> : null}
      {content && !content.binary ? <CodeViewer path={content.path} content={content.content} /> : null}
      {content?.truncated ? (
        <p className="muted">File truncated for display (it&apos;s larger than the preview limit).</p>
      ) : null}
    </div>
  );
}

function CodeViewer({ path, content }: { path: string; content: string }) {
  const language = languageForPath(path);
  const lines = content.split("\n");
  return (
    <div className="code-viewer">
      <div className="file-viewer-header mono">{path}</div>
      <pre className="mono overflow code-viewer-content">
        <code>
          {lines.map((line, index) => (
            <div className="code-line" key={index}>
              <span className="code-line-number">{index + 1}</span>
              <span className="code-line-text">
                {tokenizeCodeLine(line, language).map((token, tokenIndex) => (
                  <span key={tokenIndex} className={`code-tok-${token.type}`}>
                    {token.text}
                  </span>
                ))}
              </span>
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}

function ProblemsTab({ buildId }: { buildId: string }) {
  const [report, setReport] = useState<ProblemsReport | null>(null);
  const [hasChecked, setHasChecked] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch(`/api/jobs/build/${encodeURIComponent(buildId)}/problems`);
        if (cancelled) return;
        if (response.ok) {
          const body = (await response.json()) as ProblemsReport;
          setReport(body);
          setHasChecked(true);
        }
      } catch {
        // No prior report is a normal, common state - nothing to surface here.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [buildId]);

  async function handleCheck() {
    setChecking(true);
    setError(null);
    try {
      const response = await fetch(`/api/jobs/build/${encodeURIComponent(buildId)}/problems`, {
        method: "POST",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<ProblemsReport> & ErrorBody;
      if (!response.ok) {
        setError(body.error ?? `could not check for problems (status ${response.status})`);
        return;
      }
      setReport(body as ProblemsReport);
      setHasChecked(true);
    } catch {
      setError("could not reach the server");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="problems-tab">
      <div className="problems-header">
        <button type="button" className="button" onClick={handleCheck} disabled={checking}>
          {checking ? <span className="spinner" /> : null} {checking ? "Checking…" : "Check for problems"}
        </button>
        {report ? (
          <span className="muted">
            {report.error_count} problem{report.error_count === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      {error ? <div className="error-banner">{error}</div> : null}
      {!hasChecked && !checking && !error ? (
        <p className="muted tab-empty">
          Not checked yet — click &quot;Check for problems&quot; to run a real TypeScript check.
        </p>
      ) : null}
      {report && report.ok ? <p className="problems-clean">No problems found.</p> : null}
      {report && !report.ok ? (
        <div className="problems-list">
          {Object.entries(report.files).map(([path, lines]) => (
            <div key={path} className="problems-file-group">
              <div className="mono problems-file-name">
                <WarningIcon width={14} height={14} /> {path}
              </div>
              <ul>
                {lines.map((line, index) => (
                  <li key={index} className="mono">
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
