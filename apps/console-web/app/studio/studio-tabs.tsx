"use client";

import { useEffect, useState } from "react";
import {
  Bug,
  CircleCheck,
  Code,
  FileText,
  FolderTree,
  LoaderCircle,
  MonitorPlay,
  Search,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { BuildFileContentResponse, ProblemsReport } from "@/lib/control-plane";
import { formatServerError } from "@/components/field";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { languageForPath, tokenizeCodeLine } from "./code-highlight";
import { FileTree } from "./file-tree";
import { StudioPreview } from "./studio-preview";
import type { WorkspaceSnapshot } from "./studio-workspace";

type TabKey = "preview" | "files" | "code" | "problems";

const TABS: { key: TabKey; label: string; icon: LucideIcon }[] = [
  { key: "preview", label: "Preview", icon: MonitorPlay },
  { key: "files", label: "Files", icon: FolderTree },
  { key: "code", label: "Code", icon: Code },
  { key: "problems", label: "Problems", icon: Bug },
];

type ErrorBody = { error?: string };

/** The four-tab workspace (R-481, rebuilt in R-494 on the vendored shadcn Tabs - real Radix
 * tabs with roving focus and ARIA wiring). Files and Code stay separate real tabs, per the
 * founder's explicit choice - Files is the browse tree, Code is tree + reader, both reading and
 * writing one lifted `selectedFile` so picking a file in Files opens it in Code. */
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
  const [problemCount, setProblemCount] = useState<number | null>(null);
  // R-497 (Lovable's "Search code"): one filter shared by the Files and Code trees.
  const [fileQuery, setFileQuery] = useState("");

  if (!buildId) {
    return null;
  }

  function openFileInCode(path: string) {
    setSelectedFile(path);
    setActiveTab("code");
  }

  const files = workspace?.files ?? [];
  const query = fileQuery.trim().toLowerCase();
  const visibleFiles = query ? files.filter((path) => path.toLowerCase().includes(query)) : files;
  const filter = { query: fileQuery, onQueryChange: setFileQuery, total: files.length };

  return (
    <Tabs
      value={activeTab}
      onValueChange={(value) => setActiveTab(value as TabKey)}
      className="gap-3"
    >
      <TabsList
        variant="line"
        aria-label="Workspace"
        className="w-full justify-start gap-1 border-b border-border/60 pb-1"
      >
        {TABS.map(({ key, label, icon: Icon }) => (
          <TabsTrigger key={key} value={key} className="flex-none px-2.5">
            <Icon aria-hidden="true" />
            {label}
            {key === "files" && files.length > 0 ? (
              <TabCount value={files.length} />
            ) : null}
            {key === "problems" && problemCount !== null ? (
              <TabCount value={problemCount} tone={problemCount > 0 ? "error" : "ok"} />
            ) : null}
          </TabsTrigger>
        ))}
      </TabsList>

      <TabsContent value="preview">
        <StudioPreview buildId={buildId} previewVersion={previewVersion} />
      </TabsContent>
      <TabsContent value="files">
        <FilesTab
          files={visibleFiles}
          filter={filter}
          selectedFile={selectedFile}
          onOpen={openFileInCode}
        />
      </TabsContent>
      <TabsContent value="code">
        <CodeTab
          buildId={buildId}
          files={visibleFiles}
          filter={filter}
          selectedFile={selectedFile}
          onSelect={setSelectedFile}
        />
      </TabsContent>
      <TabsContent value="problems">
        <ProblemsTab
          buildId={buildId}
          onOpenFile={openFileInCode}
          onCountChange={setProblemCount}
        />
      </TabsContent>
    </Tabs>
  );
}

function TabCount({ value, tone = "neutral" }: { value: number; tone?: "neutral" | "ok" | "error" }) {
  return (
    <span
      className={cn(
        "ml-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full px-1 font-mono text-[10px] tabular-nums",
        tone === "error" && "bg-destructive/15 text-destructive",
        tone === "ok" && "bg-brand/15 text-brand",
        tone === "neutral" && "bg-muted text-muted-foreground",
      )}
    >
      {value}
    </span>
  );
}

function TabEmpty({
  icon: Icon,
  title,
  body,
}: {
  icon: LucideIcon;
  title: string;
  body: string;
}) {
  return (
    <div className="grid justify-items-center gap-2 rounded-xl border border-dashed border-border/70 px-6 py-12 text-center">
      <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
      <p className="text-sm font-medium">{title}</p>
      <p className="max-w-sm text-pretty text-sm text-muted-foreground">{body}</p>
    </div>
  );
}

interface FileFilterProps {
  query: string;
  onQueryChange: (value: string) => void;
  total: number;
}

/** The search box above a file tree (R-497). `shown` is the filtered count; `total` the build's. */
function FileFilter({ filter, shown }: { filter: FileFilterProps; shown: number }) {
  return (
    <div className="mb-2 grid gap-1">
      <div className="relative">
        <Search
          className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          type="search"
          aria-label="Search files"
          placeholder="Search files…"
          value={filter.query}
          onChange={(event) => filter.onQueryChange(event.target.value)}
          className="h-8 pl-8 text-xs"
        />
      </div>
      {filter.query.trim() ? (
        <p className="px-1 text-[11px] text-muted-foreground tabular-nums" aria-live="polite">
          {shown} of {filter.total} files match
        </p>
      ) : null}
    </div>
  );
}

function FilesTab({
  files,
  filter,
  selectedFile,
  onOpen,
}: {
  files: string[];
  filter: FileFilterProps;
  selectedFile: string | null;
  onOpen: (path: string) => void;
}) {
  if (filter.total === 0) {
    return (
      <TabEmpty
        icon={FolderTree}
        title="No files yet"
        body="The file list appears as soon as the build finishes."
      />
    );
  }
  return (
    <div className="rounded-xl border border-border/60 bg-card p-2">
      <FileFilter filter={filter} shown={files.length} />
      {files.length > 0 ? (
        <FileTree files={files} selectedFile={selectedFile} onOpen={onOpen} />
      ) : (
        <p className="px-2 py-3 text-sm text-muted-foreground">No files match your search.</p>
      )}
    </div>
  );
}

function CodeTab({
  buildId,
  files,
  filter,
  selectedFile,
  onSelect,
}: {
  buildId: string;
  files: string[];
  filter: FileFilterProps;
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
          setError(
            formatServerError(body.error, `Couldn't read the file (status ${response.status}).`),
          );
          return;
        }
        setContent(body as BuildFileContentResponse);
      } catch {
        if (!cancelled) setError("Couldn't reach the server.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [buildId, selectedFile]);

  return (
    <div className="grid gap-3 lg:grid-cols-[240px_minmax(0,1fr)]">
      <div className="rounded-xl border border-border/60 bg-card p-2 lg:max-h-[calc(100dvh-18rem)] lg:overflow-y-auto">
        {filter.total > 0 ? <FileFilter filter={filter} shown={files.length} /> : null}
        {files.length > 0 ? (
          <FileTree files={files} selectedFile={selectedFile} onOpen={onSelect} />
        ) : (
          <p className="px-2 py-3 text-sm text-muted-foreground">
            {filter.total > 0 ? "No files match your search." : "No files yet."}
          </p>
        )}
      </div>
      <div className="min-w-0">
        {!selectedFile ? (
          <TabEmpty
            icon={Code}
            title="Choose a file to read"
            body="Pick any file from the tree on the left. It opens here with line numbers and syntax highlighting."
          />
        ) : null}
        {selectedFile && loading ? <CodeSkeleton path={selectedFile} /> : null}
        {error ? (
          <div
            role="alert"
            className="flex gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
          >
            <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {error}
          </div>
        ) : null}
        {!loading && !error && content && selectedFile === content.path ? (
          content.binary ? (
            <TabEmpty
              icon={FileText}
              title="Binary file"
              body={`${content.path} is not text, so it isn't shown here.`}
            />
          ) : (
            <CodeViewer
              path={content.path}
              content={content.content}
              size={content.size}
              truncated={content.truncated}
            />
          )
        ) : null}
      </div>
    </div>
  );
}

const SKELETON_WIDTHS = ["w-2/5", "w-3/5", "w-1/3", "w-4/5", "w-1/2", "w-2/3", "w-1/4", "w-3/5"];

function CodeSkeleton({ path }: { path: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border/60 bg-card" aria-busy="true">
      <div className="flex items-center gap-2 border-b border-border/60 px-3 py-2 text-xs">
        <FileText className="size-3.5 text-muted-foreground" aria-hidden="true" />
        <span className="truncate font-mono">{path}</span>
        <span className="ml-auto text-muted-foreground">Loading…</span>
      </div>
      <div className="grid gap-2.5 p-4">
        {SKELETON_WIDTHS.map((width, index) => (
          <Skeleton key={index} className={cn("h-3", width)} />
        ))}
      </div>
    </div>
  );
}

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function CodeViewer({
  path,
  content,
  size,
  truncated,
}: {
  path: string;
  content: string;
  size: number;
  truncated: boolean;
}) {
  const language = languageForPath(path);
  const extension = path.includes(".") ? path.slice(path.lastIndexOf(".") + 1) : "";
  const lines = content.split("\n");
  return (
    <div className="overflow-hidden rounded-xl border border-border/60 bg-card">
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-3 py-2 text-xs">
        <FileText className="size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate font-mono" title={path}>
          {path}
        </span>
        <Badge variant="outline" className="font-mono uppercase">
          {extension || language}
        </Badge>
        <span className="text-muted-foreground tabular-nums">
          {lines.length.toLocaleString("en-US")} lines · {formatBytes(size)}
        </span>
        <span className="text-muted-foreground">Read only</span>
      </div>
      <pre className="max-h-[calc(100dvh-20rem)] min-h-64 overflow-auto py-3 font-mono text-[13px] leading-6">
        <code>
          {lines.map((line, index) => (
            <div key={index} className="flex px-3 whitespace-pre hover:bg-muted/40">
              <span className="w-10 shrink-0 select-none pr-3 text-right text-muted-foreground tabular-nums">
                {index + 1}
              </span>
              <span>
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
      {truncated ? (
        <p className="border-t border-border/60 px-3 py-2 text-xs text-muted-foreground">
          Truncated for display: the file is larger than the preview limit.
        </p>
      ) : null}
    </div>
  );
}

/* tsc's rendered diagnostic form, exactly as verify/compile.py reports it: "L12:5 TS2339: msg".
 * Anything else is shown verbatim - no severity is invented (tsc only emits errors). */
const DIAGNOSTIC = /^L(\d+):(\d+)\s+(TS\d+):\s*(.*)$/;

export function parseDiagnostic(
  line: string,
): { line: string; column: string; code: string; message: string } | null {
  const match = DIAGNOSTIC.exec(line);
  return match ? { line: match[1], column: match[2], code: match[3], message: match[4] } : null;
}

function ProblemsTab({
  buildId,
  onOpenFile,
  onCountChange,
}: {
  buildId: string;
  onOpenFile: (path: string) => void;
  onCountChange: (count: number | null) => void;
}) {
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

  useEffect(() => {
    onCountChange(report ? report.error_count : null);
  }, [report, onCountChange]);

  async function handleCheck() {
    setChecking(true);
    setError(null);
    try {
      const response = await fetch(`/api/jobs/build/${encodeURIComponent(buildId)}/problems`, {
        method: "POST",
      });
      const body = (await response.json().catch(() => ({}))) as Partial<ProblemsReport> & ErrorBody;
      if (!response.ok) {
        setError(
          formatServerError(
            body.error,
            `Couldn't check for problems (status ${response.status}).`,
          ),
        );
        return;
      }
      setReport(body as ProblemsReport);
      setHasChecked(true);
    } catch {
      setError("Couldn't reach the server.");
    } finally {
      setChecking(false);
    }
  }

  const groups = report && !report.ok ? Object.entries(report.files) : [];

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" onClick={handleCheck} disabled={checking}>
          {checking ? (
            <LoaderCircle className="animate-spin" aria-hidden="true" />
          ) : (
            <Bug aria-hidden="true" />
          )}
          {checking ? "Checking…" : "Check for problems"}
        </Button>
        {report ? (
          report.ok ? (
            <Badge className="border-brand/30 bg-brand/15 text-brand">No problems</Badge>
          ) : (
            <Badge variant="destructive">
              {report.error_count} problem{report.error_count === 1 ? "" : "s"}
            </Badge>
          )
        ) : null}
        <p className="text-xs text-muted-foreground">
          Runs a real TypeScript check on the generated project. It can take a moment.
        </p>
      </div>

      {error ? (
        <div
          role="alert"
          className="flex gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
        >
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {error}
        </div>
      ) : null}

      {!hasChecked && !checking && !error ? (
        <TabEmpty
          icon={Bug}
          title="Not checked yet"
          body='Click "Check for problems" to run tsc against this build and see anything it reports, grouped by file.'
        />
      ) : null}

      {report && report.ok ? (
        <div className="flex items-center gap-2 rounded-xl border border-brand/30 bg-brand/10 px-4 py-3 text-sm">
          <CircleCheck className="size-4 text-brand" aria-hidden="true" />
          No problems found.
        </div>
      ) : null}

      {groups.length > 0 ? (
        <div className="grid gap-3">
          {groups.map(([path, lines]) => (
            <section key={path} className="overflow-hidden rounded-xl border border-border/60 bg-card">
              <button
                type="button"
                onClick={() => onOpenFile(path)}
                className="flex w-full items-center gap-2 border-b border-border/60 px-3 py-2 text-left text-xs outline-none transition-colors hover:bg-muted/60 focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <FileText className="size-3.5 shrink-0 text-destructive" aria-hidden="true" />
                <span className="min-w-0 flex-1 truncate font-mono">{path}</span>
                <Badge variant="destructive">{lines.length}</Badge>
                <span className="sr-only">Open in Code</span>
              </button>
              <ul className="divide-y divide-border/60">
                {lines.map((line, index) => {
                  const diagnostic = parseDiagnostic(line);
                  return (
                    <li key={index} className="flex flex-wrap items-start gap-2 px-3 py-2 text-xs">
                      {diagnostic ? (
                        <>
                          <span className="font-mono text-muted-foreground tabular-nums">
                            {diagnostic.line}:{diagnostic.column}
                          </span>
                          <Badge variant="outline" className="font-mono">
                            {diagnostic.code}
                          </Badge>
                          <span className="min-w-0 flex-1 break-words">{diagnostic.message}</span>
                        </>
                      ) : (
                        <span className="font-mono break-words">{line}</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      ) : null}

      {report && report.output_tail ? (
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            Raw tsc output
          </summary>
          <pre className="mt-2 overflow-auto rounded-lg bg-muted p-3 font-mono whitespace-pre-wrap">
            {report.output_tail}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
