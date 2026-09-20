"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowDown,
  Check,
  Copy,
  Download,
  LoaderCircle,
  RefreshCw,
  Search,
  Terminal,
  Trash2,
} from "lucide-react";
import type { BuildLogEntry, ProjectLogsResponse } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type LogSource = "build" | "app";
type LogLevel = "all" | "info" | "warn" | "error";

interface ProjectLogsManageProps {
  projectId: string;
}

export function ProjectLogsManage({ projectId }: ProjectLogsManageProps) {
  const [source, setSource] = useState<LogSource>("build");
  const [level, setLevel] = useState<LogLevel>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [follow, setFollow] = useState(true);

  const [logs, setLogs] = useState<(BuildLogEntry | string)[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const logEndRef = useRef<HTMLDivElement>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const refetchLogs = useCallback(
    async (isSilent = false) => {
      if (!isSilent) setLoading(true);
      else setRefreshing(true);
      setError(null);

      try {
        const res = await fetch(
          `/api/projects/${encodeURIComponent(projectId)}/logs?source=${source}&limit=1000`,
        );
        if (!res.ok) {
          throw new Error(`Failed to load logs (HTTP ${res.status})`);
        }
        const data = (await res.json()) as ProjectLogsResponse;
        setLogs(data.lines || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load logs");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [projectId, source],
  );

  // Load logs on mount or when source changes
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(
          `/api/projects/${encodeURIComponent(projectId)}/logs?source=${source}&limit=1000`,
        );
        if (!active) return;
        if (!res.ok) {
          throw new Error(`Failed to load logs (HTTP ${res.status})`);
        }
        const data = (await res.json()) as ProjectLogsResponse;
        if (active) setLogs(data.lines || []);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load logs");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId, source]);

  // Auto-refresh when follow is enabled
  useEffect(() => {
    if (!follow) return;
    const interval = setInterval(() => {
      void refetchLogs(true);
    }, 2500);
    return () => clearInterval(interval);
  }, [follow, refetchLogs]);

  // Auto-scroll when follow is enabled and logs update
  useEffect(() => {
    if (follow && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, follow]);

  async function handleClear() {
    if (!confirm(`Are you sure you want to clear the ${source} logs?`)) return;
    setClearing(true);
    try {
      const res = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/logs?source=${source}`,
        { method: "DELETE" },
      );
      if (res.ok) {
        setLogs([]);
      }
    } catch {
      // Best effort
    } finally {
      setClearing(false);
    }
  }

  function handleCopy() {
    const textToCopy = filteredLogs
      .map((entry) => {
        if (typeof entry === "string") return entry;
        const timeStr = entry.ts ? new Date(entry.ts * 1000).toLocaleTimeString() : "";
        return `[${timeStr}] [${entry.level.toUpperCase()}] [${entry.phase}] ${entry.message}`;
      })
      .join("\n");

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleDownload() {
    const text = filteredLogs
      .map((entry) => {
        if (typeof entry === "string") return entry;
        const timeStr = entry.ts ? new Date(entry.ts * 1000).toISOString() : "";
        return `[${timeStr}] [${entry.level.toUpperCase()}] [${entry.phase}] ${entry.message}`;
      })
      .join("\n");

    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${source}-logs-${projectId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Filter logs by level and search query
  const filteredLogs = logs.filter((entry) => {
    if (typeof entry === "string") {
      if (!searchQuery) return true;
      return entry.toLowerCase().includes(searchQuery.toLowerCase());
    }

    if (level !== "all" && entry.level !== level) {
      return false;
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        entry.message.toLowerCase().includes(query) ||
        entry.phase.toLowerCase().includes(query) ||
        entry.level.toLowerCase().includes(query)
      );
    }

    return true;
  });

  return (
    <Card className="border-border/60">
      <CardHeader>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-xl flex items-center gap-2">
              <Terminal className="size-5 text-brand" />
              Logs
            </CardTitle>
            <CardDescription className="mt-1">
              Live build events and application output with secrets masking.
            </CardDescription>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchLogs(true)}
              disabled={loading || refreshing}
              title="Refresh logs"
            >
              <RefreshCw className={cn("size-3.5 mr-1.5", refreshing && "animate-spin")} />
              Refresh
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              disabled={filteredLogs.length === 0}
              title="Copy visible logs"
            >
              {copied ? (
                <>
                  <Check className="size-3.5 mr-1.5 text-brand" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="size-3.5 mr-1.5" />
                  Copy
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={filteredLogs.length === 0}
              title="Download logs"
            >
              <Download className="size-3.5 mr-1.5" />
              Download
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClear}
              disabled={clearing || logs.length === 0}
              className="text-muted-foreground hover:text-destructive"
              title="Clear logs"
            >
              <Trash2 className="size-3.5 mr-1.5" />
              Clear
            </Button>
          </div>
        </div>

        {/* Toolbar: Source toggle, Level filter, Search box, Follow toggle */}
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-t border-border/60 pt-4">
          <div className="flex flex-wrap items-center gap-2">
            {/* Source Switch: Build / App */}
            <div className="inline-flex rounded-lg border border-border/80 bg-muted/40 p-0.5 text-xs font-medium">
              <button
                type="button"
                onClick={() => setSource("build")}
                className={cn(
                  "rounded-md px-3 py-1.5 transition-all select-none",
                  source === "build"
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                Build Logs
              </button>
              <button
                type="button"
                onClick={() => setSource("app")}
                className={cn(
                  "rounded-md px-3 py-1.5 transition-all select-none",
                  source === "app"
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                App Output
              </button>
            </div>

            {/* Level Filter (Build mode only) */}
            {source === "build" && (
              <div className="flex items-center gap-1 border-l border-border/60 pl-2">
                {(["all", "info", "warn", "error"] as const).map((lvl) => (
                  <button
                    key={lvl}
                    type="button"
                    onClick={() => setLevel(lvl)}
                    className={cn(
                      "rounded-md px-2 py-1 text-xs uppercase font-mono tracking-wider transition-colors",
                      level === lvl
                        ? "bg-secondary text-secondary-foreground font-semibold"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {lvl}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Search Box */}
            <div className="relative min-w-[180px] max-w-xs">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search logs…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-8 pl-8 text-xs font-mono"
              />
            </div>

            {/* Follow Toggle */}
            <Button
              variant={follow ? "secondary" : "outline"}
              size="sm"
              onClick={() => setFollow(!follow)}
              className={cn("h-8 text-xs gap-1.5", follow && "border-brand/40 text-brand font-medium")}
              title={follow ? "Auto-scroll enabled" : "Auto-scroll paused"}
            >
              <ArrowDown className={cn("size-3.5", follow && "animate-bounce")} />
              Follow
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {error ? (
          <div
            role="alert"
            className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
          >
            <AlertCircle className="size-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        {/* Monospace Terminal Log Viewer */}
        <div
          ref={logContainerRef}
          className="relative min-h-[360px] max-h-[560px] overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-300 select-text"
        >
          {loading ? (
            <div className="flex h-64 items-center justify-center gap-2 text-zinc-500">
              <LoaderCircle className="size-5 animate-spin text-brand" />
              <span>Loading {source} logs…</span>
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="flex h-64 flex-col items-center justify-center text-center text-zinc-500">
              <Terminal className="size-8 opacity-40 mb-2" />
              <p className="font-semibold text-zinc-400">
                {logs.length === 0
                  ? "Nothing logged yet — run a build or start the preview."
                  : "No log lines match the current filter or search."}
              </p>
              <p className="text-[11px] opacity-70 mt-1 max-w-sm">
                {source === "build"
                  ? "Build and edit events will appear here as your project generates."
                  : "Preview server stdout and stderr will be captured here when running."}
              </p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {filteredLogs.map((entry, idx) => {
                if (typeof entry === "string") {
                  return (
                    <div
                      key={idx}
                      className="flex items-start gap-3 hover:bg-zinc-900/60 px-1.5 py-0.5 rounded transition-colors"
                    >
                      <span className="w-8 shrink-0 text-right text-zinc-600 select-none tabular-nums">
                        {idx + 1}
                      </span>
                      <span className="flex-1 break-words whitespace-pre-wrap">{entry}</span>
                    </div>
                  );
                }

                const isError = entry.level === "error";
                const isWarn = entry.level === "warn";
                const timeStr = entry.ts
                  ? new Date(entry.ts * 1000).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })
                  : "--:--:--";

                return (
                  <div
                    key={idx}
                    className={cn(
                      "flex items-start gap-3 px-1.5 py-0.5 rounded transition-colors",
                      isError && "bg-red-950/30 text-red-300 border-l-2 border-red-500 pl-1",
                      isWarn && "bg-amber-950/20 text-amber-300 border-l-2 border-amber-500 pl-1",
                      !isError && !isWarn && "hover:bg-zinc-900/60",
                    )}
                  >
                    <span className="w-8 shrink-0 text-right text-zinc-600 select-none tabular-nums">
                      {idx + 1}
                    </span>
                    <span className="shrink-0 text-zinc-500 tabular-nums select-none">
                      [{timeStr}]
                    </span>
                    <Badge
                      variant="outline"
                      className={cn(
                        "shrink-0 text-[10px] uppercase font-mono px-1.5 py-0 select-none",
                        isError && "border-red-500/40 bg-red-950/40 text-red-400",
                        isWarn && "border-amber-500/40 bg-amber-950/40 text-amber-400",
                        !isError && !isWarn && "border-zinc-700 bg-zinc-900 text-zinc-400",
                      )}
                    >
                      {entry.level}
                    </Badge>
                    <span className="shrink-0 text-zinc-400 select-none font-semibold">
                      [{entry.phase}]
                    </span>
                    <span className="flex-1 break-words whitespace-pre-wrap">{entry.message}</span>
                  </div>
                );
              })}
              <div ref={logEndRef} />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
