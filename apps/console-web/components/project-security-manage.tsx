"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  ExternalLink,
  FileCode2,
  LoaderCircle,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type {
  ProjectSecurityReport,
  SecurityFinding,
} from "@/lib/control-plane";
import { formatDateTime, formatRelativeTime } from "@/lib/time";
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

interface ProjectSecurityManageProps {
  projectId: string;
}

export function ProjectSecurityManage({ projectId }: ProjectSecurityManageProps) {
  const router = useRouter();
  const [report, setReport] = useState<ProjectSecurityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedFiles, setExpandedFiles] = useState<Record<string, boolean>>({});

  // Fetch initial cached report
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/security`);
        if (!active) return;
        if (res.ok) {
          const data = (await res.json()) as ProjectSecurityReport;
          if (active && data && data.scanned_at) {
            setReport(data);
          }
        }
      } catch {
        // Cached report might not exist yet
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  const handleRunScan = async () => {
    setScanning(true);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/security/scan`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `Security scan failed (HTTP ${res.status})`);
      }
      const newReport = (await res.json()) as ProjectSecurityReport;
      setReport(newReport);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run security scan");
    } finally {
      setScanning(false);
    }
  };

  const toggleFile = (fileKey: string) => {
    setExpandedFiles((prev) => ({
      ...prev,
      [fileKey]: !prev[fileKey],
    }));
  };

  const handleFixWithAI = (finding: SecurityFinding, idx: number) => {
    const fileLabel = finding.file || "unknown file";
    const lineLabel = finding.line ? `:${finding.line}` : "";
    const prompt = `Fix the following security issue in ${fileLabel}${lineLabel}:\nRule: ${finding.rule}\nMessage: ${finding.message}${
      finding.fix ? `\nRecommended fix: ${finding.fix}` : ""
    }`;
    navigator.clipboard.writeText(prompt);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2500);
    // Navigate to studio chat with prompt encoded in searchParams
    router.push(`/studio/${encodeURIComponent(projectId)}?prompt=${encodeURIComponent(prompt)}`);
  };

  const filteredFindings = useMemo(() => {
    if (!report || !report.findings) return [];
    return report.findings.filter((f) => {
      if (severityFilter !== "all" && f.severity !== severityFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesFile = (f.file || "").toLowerCase().includes(q);
        const matchesRule = f.rule.toLowerCase().includes(q);
        const matchesMsg = f.message.toLowerCase().includes(q);
        return matchesFile || matchesRule || matchesMsg;
      }
      return true;
    });
  }, [report, severityFilter, searchQuery]);

  // Group filtered findings by file
  const findingsByFile = useMemo(() => {
    const groups: Record<string, SecurityFinding[]> = {};
    for (const f of filteredFindings) {
      const groupKey = f.file || "General Findings";
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(f);
    }
    return groups;
  }, [filteredFindings]);

  return (
    <div className="space-y-6">
      {/* Top Banner & Action */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            <ShieldAlert className="size-5 text-primary" />
            Security Scanning
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Audit dependencies, check for hardcoded secrets, and verify framework security rules.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {report?.scanned_at && (
            <span className="text-xs text-muted-foreground flex items-center gap-1.5" title={formatDateTime(report.scanned_at)}>
              <Clock className="size-3.5" />
              Scanned {formatRelativeTime(report.scanned_at)}
            </span>
          )}
          <Button
            onClick={handleRunScan}
            disabled={scanning}
            className="flex items-center gap-2"
          >
            {scanning ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Scanning Project...
              </>
            ) : (
              <>
                <RefreshCw className="size-4" />
                Run Security Scan
              </>
            )}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex items-start gap-3">
          <AlertCircle className="size-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Security scan error</p>
            <p className="mt-1 text-xs opacity-90">{error}</p>
          </div>
        </div>
      )}

      {loading ? (
        <Card className="p-8 text-center">
          <LoaderCircle className="size-6 animate-spin mx-auto text-muted-foreground" />
          <p className="text-sm text-muted-foreground mt-2">Loading security report...</p>
        </Card>
      ) : !report ? (
        <Card className="p-12 text-center border-dashed">
          <Shield className="size-12 mx-auto text-muted-foreground/50 mb-3" />
          <h3 className="text-base font-semibold">No Security Scan Yet</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1 mb-5">
            Run a deterministic scan across dependencies, secret leaks, and framework rules to check your generated code.
          </p>
          <Button onClick={handleRunScan} disabled={scanning} className="mx-auto flex items-center gap-2">
            {scanning ? <LoaderCircle className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
            Start First Scan
          </Button>
        </Card>
      ) : (
        <>
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <Card className="p-4">
              <p className="text-xs font-medium text-muted-foreground">Total Findings</p>
              <p className="text-2xl font-bold mt-1">{report.summary.total_issues}</p>
            </Card>
            <Card className="p-4 border-destructive/40 bg-destructive/5">
              <p className="text-xs font-medium text-destructive">Critical</p>
              <p className="text-2xl font-bold text-destructive mt-1">{report.summary.critical}</p>
            </Card>
            <Card className="p-4 border-orange-500/40 bg-orange-500/5">
              <p className="text-xs font-medium text-orange-600 dark:text-orange-400">High</p>
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400 mt-1">{report.summary.high}</p>
            </Card>
            <Card className="p-4 border-amber-500/40 bg-amber-500/5">
              <p className="text-xs font-medium text-amber-600 dark:text-amber-400">Medium</p>
              <p className="text-2xl font-bold text-amber-600 dark:text-amber-400 mt-1">{report.summary.medium}</p>
            </Card>
            <Card className="p-4 border-blue-500/40 bg-blue-500/5">
              <p className="text-xs font-medium text-blue-600 dark:text-blue-400">Low</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{report.summary.low}</p>
            </Card>
          </div>

          {/* Checks Executed Card */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" />
                Checks Performed
              </CardTitle>
              <CardDescription className="text-xs">
                Real tools and deterministic rules executed against your codebase.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                {report.checks.map((check) => {
                  const isSkipped = check.status === "skipped";
                  const isPassed = check.status === "passed";
                  return (
                    <div
                      key={check.name}
                      className={cn(
                        "flex items-center justify-between p-2.5 rounded-md border text-xs",
                        isSkipped
                          ? "bg-muted/30 border-muted text-muted-foreground"
                          : isPassed
                          ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-700 dark:text-emerald-300"
                          : "bg-destructive/5 border-destructive/20 text-destructive",
                      )}
                    >
                      <div className="flex items-center gap-2 truncate">
                        {isSkipped ? (
                          <AlertTriangle className="size-3.5 shrink-0 text-muted-foreground" />
                        ) : isPassed ? (
                          <CheckCircle2 className="size-3.5 shrink-0 text-emerald-500" />
                        ) : (
                          <AlertCircle className="size-3.5 shrink-0 text-destructive" />
                        )}
                        <span className="font-medium truncate">{check.name}</span>
                      </div>
                      <Badge
                        variant={isSkipped ? "secondary" : isPassed ? "outline" : "destructive"}
                        className="text-[10px] uppercase font-mono tracking-wider ml-2 shrink-0"
                      >
                        {isSkipped ? (check.note ? `SKIPPED: ${check.note}` : "SKIPPED") : isPassed ? "PASSED" : "ISSUES FOUND"}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Findings or Clean State */}
          {report.findings.length === 0 ? (
            <Card className="p-8 text-center bg-emerald-500/5 border-emerald-500/30">
              <ShieldCheck className="size-12 mx-auto text-emerald-500 mb-2" />
              <h3 className="text-base font-semibold text-emerald-700 dark:text-emerald-300">
                No issues found by these checks
              </h3>
              <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                All executed secret scans, framework security rules, and dependency audits reported no vulnerabilities.
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Search & Filter Bar */}
              <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
                <div className="relative w-full sm:w-72">
                  <Search className="size-4 absolute left-3 top-2.5 text-muted-foreground" />
                  <Input
                    placeholder="Filter by file, rule, or message..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 text-xs h-9"
                  />
                </div>
                <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto">
                  <Button
                    variant={severityFilter === "all" ? "secondary" : "ghost"}
                    size="sm"
                    onClick={() => setSeverityFilter("all")}
                    className="text-xs h-8"
                  >
                    All ({report.summary.total_issues})
                  </Button>
                  <Button
                    variant={severityFilter === "critical" ? "secondary" : "ghost"}
                    size="sm"
                    onClick={() => setSeverityFilter("critical")}
                    className="text-xs h-8 text-destructive"
                  >
                    Critical ({report.summary.critical})
                  </Button>
                  <Button
                    variant={severityFilter === "high" ? "secondary" : "ghost"}
                    size="sm"
                    onClick={() => setSeverityFilter("high")}
                    className="text-xs h-8 text-orange-600 dark:text-orange-400"
                  >
                    High ({report.summary.high})
                  </Button>
                  <Button
                    variant={severityFilter === "medium" ? "secondary" : "ghost"}
                    size="sm"
                    onClick={() => setSeverityFilter("medium")}
                    className="text-xs h-8 text-amber-600 dark:text-amber-400"
                  >
                    Medium ({report.summary.medium})
                  </Button>
                  <Button
                    variant={severityFilter === "low" ? "secondary" : "ghost"}
                    size="sm"
                    onClick={() => setSeverityFilter("low")}
                    className="text-xs h-8 text-blue-600 dark:text-blue-400"
                  >
                    Low ({report.summary.low})
                  </Button>
                </div>
              </div>

              {/* Grouped Findings Accordion */}
              {Object.keys(findingsByFile).length === 0 ? (
                <Card className="p-6 text-center text-muted-foreground text-xs">
                  No findings match the current filter.
                </Card>
              ) : (
                <div className="space-y-3">
                  {Object.entries(findingsByFile).map(([file, findings]) => {
                    const isExpanded = expandedFiles[file] !== false; // default expanded
                    return (
                      <Card key={file} className="overflow-hidden border">
                        <button
                          type="button"
                          onClick={() => toggleFile(file)}
                          className="w-full flex items-center justify-between p-3.5 bg-muted/20 hover:bg-muted/40 transition-colors text-left text-sm font-medium"
                        >
                          <div className="flex items-center gap-2 truncate">
                            {isExpanded ? (
                              <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                            )}
                            <FileCode2 className="size-4 shrink-0 text-primary" />
                            <span className="font-mono text-xs truncate">{file}</span>
                            <Badge variant="outline" className="text-[10px] ml-1">
                              {findings.length} {findings.length === 1 ? "finding" : "findings"}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {findings.some((f) => f.severity === "critical") && (
                              <Badge variant="destructive" className="text-[9px] uppercase px-1.5 py-0">Critical</Badge>
                            )}
                            {findings.some((f) => f.severity === "high") && (
                              <Badge className="bg-orange-600 text-white text-[9px] uppercase px-1.5 py-0">High</Badge>
                            )}
                            {findings.some((f) => f.severity === "medium") && (
                              <Badge className="bg-amber-600 text-white text-[9px] uppercase px-1.5 py-0">Medium</Badge>
                            )}
                            {findings.some((f) => f.severity === "low") && (
                              <Badge variant="secondary" className="text-[9px] uppercase px-1.5 py-0">Low</Badge>
                            )}
                          </div>
                        </button>

                        {isExpanded && (
                          <div className="divide-y divide-border border-t">
                            {findings.map((finding, idx) => {
                              const globalIdx = report.findings.indexOf(finding);
                              const isCritical = finding.severity === "critical";
                              const isHigh = finding.severity === "high";
                              const isMedium = finding.severity === "medium";

                              return (
                                <div key={idx} className="p-4 space-y-2 text-xs">
                                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                                    <div className="flex items-center gap-2 flex-wrap">
                                      <Badge
                                        variant={
                                          isCritical
                                            ? "destructive"
                                            : isHigh
                                            ? "default"
                                            : isMedium
                                            ? "secondary"
                                            : "outline"
                                        }
                                        className={cn(
                                          "text-[10px] uppercase font-mono tracking-wider",
                                          isHigh && "bg-orange-600 hover:bg-orange-700 text-white",
                                          isMedium && "bg-amber-500/20 text-amber-700 dark:text-amber-300 hover:bg-amber-500/30",
                                        )}
                                      >
                                        {finding.severity}
                                      </Badge>
                                      <span className="font-mono text-muted-foreground">
                                        {finding.rule}
                                      </span>
                                      {finding.line && (
                                        <Badge variant="outline" className="text-[10px] font-mono">
                                          line {finding.line}
                                        </Badge>
                                      )}
                                    </div>

                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => handleFixWithAI(finding, globalIdx)}
                                      className="h-7 text-xs flex items-center gap-1.5 text-primary hover:text-primary self-start sm:self-auto"
                                    >
                                      <Sparkles className="size-3.5" />
                                      {copiedIndex === globalIdx ? "Prompt Copied!" : "Fix with AI"}
                                    </Button>
                                  </div>

                                  <p className="font-medium text-foreground text-xs leading-relaxed">
                                    {finding.message}
                                  </p>

                                  {finding.fix && (
                                    <div className="rounded bg-muted/50 p-2.5 text-xs text-muted-foreground border border-muted font-mono leading-relaxed mt-2">
                                      <span className="font-semibold text-foreground mr-1.5">Suggested fix:</span>
                                      {finding.fix}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
