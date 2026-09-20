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
  Play,
  RefreshCw,
  Search,
  Sparkles,
  Terminal,
  XCircle,
} from "lucide-react";
import type {
  ProjectTestReport,
  TestSuiteResult,
  TestCaseResult,
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

interface ProjectTestsManageProps {
  projectId: string;
}

export function ProjectTestsManage({ projectId }: ProjectTestsManageProps) {
  const router = useRouter();
  const [report, setReport] = useState<ProjectTestReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedSuites, setExpandedSuites] = useState<Record<string, boolean>>({});
  const [showRawOutput, setShowRawOutput] = useState<Record<string, boolean>>({});

  // Fetch initial cached test report
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/tests`);
        if (!active) return;
        if (res.ok) {
          const data = (await res.json()) as ProjectTestReport;
          if (active && data && data.ran_at) {
            setReport(data);
          }
        }
      } catch {
        // Report might not exist yet
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  const handleRunTests = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/tests/run`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `Running tests failed (HTTP ${res.status})`);
      }
      const newReport = (await res.json()) as ProjectTestReport;
      setReport(newReport);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run tests");
    } finally {
      setRunning(false);
    }
  };

  const toggleSuite = (suiteKey: string) => {
    setExpandedSuites((prev) => ({
      ...prev,
      [suiteKey]: !prev[suiteKey],
    }));
  };

  const toggleRaw = (suiteKey: string) => {
    setShowRawOutput((prev) => ({
      ...prev,
      [suiteKey]: !prev[suiteKey],
    }));
  };

  const handleAskChatForTests = () => {
    const prompt = "Please generate unit and integration tests for this project and wire them into the test script.";
    router.push(`/studio/${encodeURIComponent(projectId)}?prompt=${encodeURIComponent(prompt)}`);
  };

  const handleFixTestWithAI = (suiteName: string, test: TestCaseResult) => {
    const prompt = `The test "${test.name}" in suite "${suiteName}" failed:\n${
      test.message || "Unknown error"
    }\nPlease fix the failing test or underlying implementation.`;
    navigator.clipboard.writeText(prompt);
    router.push(`/studio/${encodeURIComponent(projectId)}?prompt=${encodeURIComponent(prompt)}`);
  };

  const filteredSuites = useMemo(() => {
    if (!report || !report.suites) return [];
    return report.suites.map((suite) => {
      let filteredTests = suite.tests || [];
      if (statusFilter !== "all") {
        filteredTests = filteredTests.filter((t) => t.status === statusFilter);
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        filteredTests = filteredTests.filter(
          (t) =>
            t.name.toLowerCase().includes(q) ||
            (t.message && t.message.toLowerCase().includes(q)),
        );
      }
      return {
        ...suite,
        tests: filteredTests,
      };
    });
  }, [report, statusFilter, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            <CheckCircle2 className="size-5 text-primary" />
            Automated Tests
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Discover and run test suites across web, Python, and Go backends.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {report?.ran_at && (
            <span className="text-xs text-muted-foreground flex items-center gap-1.5" title={formatDateTime(report.ran_at)}>
              <Clock className="size-3.5" />
              Last run {formatRelativeTime(report.ran_at)}
            </span>
          )}
          <Button
            onClick={handleRunTests}
            disabled={running}
            className="flex items-center gap-2"
          >
            {running ? (
              <>
                <LoaderCircle className="size-4 animate-spin" />
                Running Tests...
              </>
            ) : (
              <>
                <Play className="size-4 fill-current" />
                Run Tests
              </>
            )}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex items-start gap-3">
          <AlertCircle className="size-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Test execution error</p>
            <p className="mt-1 text-xs opacity-90">{error}</p>
          </div>
        </div>
      )}

      {loading ? (
        <Card className="p-8 text-center">
          <LoaderCircle className="size-6 animate-spin mx-auto text-muted-foreground" />
          <p className="text-sm text-muted-foreground mt-2">Loading test report...</p>
        </Card>
      ) : !report ? (
        <Card className="p-12 text-center border-dashed">
          <CheckCircle2 className="size-12 mx-auto text-muted-foreground/50 mb-3" />
          <h3 className="text-base font-semibold">No Tests Run Yet</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1 mb-5">
            Execute project test runners to verify application behavior, regression suites, and integration contracts.
          </p>
          <Button onClick={handleRunTests} disabled={running} className="mx-auto flex items-center gap-2">
            {running ? <LoaderCircle className="size-4 animate-spin" /> : <Play className="size-4 fill-current" />}
            Run Tests
          </Button>
        </Card>
      ) : report.suites.length === 0 || report.summary.total === 0 ? (
        /* Honest empty state as required by spec */
        <Card className="p-10 text-center border-dashed bg-muted/20">
          <AlertCircle className="size-10 mx-auto text-muted-foreground mb-3" />
          <h3 className="text-base font-semibold">This project has no test suite yet</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto mt-1 mb-5">
            Ask the chat to add automated tests for your endpoints, components, and data workflows.
          </p>
          <Button onClick={handleAskChatForTests} className="mx-auto flex items-center gap-2">
            <Sparkles className="size-4" />
            Ask Chat to Add Tests
          </Button>
        </Card>
      ) : (
        <>
          {/* Summary Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <Card className="p-4">
              <p className="text-xs font-medium text-muted-foreground">Total Tests</p>
              <p className="text-2xl font-bold mt-1">{report.summary.total}</p>
            </Card>
            <Card className="p-4 border-emerald-500/40 bg-emerald-500/5">
              <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Passed</p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{report.summary.passed}</p>
            </Card>
            <Card className="p-4 border-destructive/40 bg-destructive/5">
              <p className="text-xs font-medium text-destructive">Failed</p>
              <p className="text-2xl font-bold text-destructive mt-1">{report.summary.failed}</p>
            </Card>
            <Card className="p-4 border-muted">
              <p className="text-xs font-medium text-muted-foreground">Skipped</p>
              <p className="text-2xl font-bold text-muted-foreground mt-1">{report.summary.skipped}</p>
            </Card>
            <Card className="p-4">
              <p className="text-xs font-medium text-muted-foreground">Duration</p>
              <p className="text-2xl font-bold mt-1">
                {report.summary.duration_ms < 1000
                  ? `${report.summary.duration_ms}ms`
                  : `${(report.summary.duration_ms / 1000).toFixed(2)}s`}
              </p>
            </Card>
          </div>

          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="relative w-full sm:w-72">
              <Search className="size-4 absolute left-3 top-2.5 text-muted-foreground" />
              <Input
                placeholder="Filter tests by name or message..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-xs h-9"
              />
            </div>
            <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto">
              <Button
                variant={statusFilter === "all" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setStatusFilter("all")}
                className="text-xs h-8"
              >
                All ({report.summary.total})
              </Button>
              <Button
                variant={statusFilter === "passed" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setStatusFilter("passed")}
                className="text-xs h-8 text-emerald-600 dark:text-emerald-400"
              >
                Passed ({report.summary.passed})
              </Button>
              <Button
                variant={statusFilter === "failed" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setStatusFilter("failed")}
                className="text-xs h-8 text-destructive"
              >
                Failed ({report.summary.failed})
              </Button>
              <Button
                variant={statusFilter === "skipped" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setStatusFilter("skipped")}
                className="text-xs h-8 text-muted-foreground"
              >
                Skipped ({report.summary.skipped})
              </Button>
            </div>
          </div>

          {/* Test Suites List */}
          <div className="space-y-4">
            {filteredSuites.map((suite) => {
              const isExpanded = expandedSuites[suite.name] !== false; // default expanded
              const isRawShown = showRawOutput[suite.name] === true;
              const hasFailed = suite.status === "failed";
              const isSkipped = suite.status === "skipped";

              return (
                <Card key={suite.name} className="overflow-hidden border">
                  <div className="flex items-center justify-between p-3.5 bg-muted/20 border-b">
                    <button
                      type="button"
                      onClick={() => toggleSuite(suite.name)}
                      className="flex items-center gap-2 truncate text-left text-sm font-medium hover:opacity-80 transition-opacity"
                    >
                      {isExpanded ? (
                        <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                      )}
                      <span className="font-semibold">{suite.name}</span>
                      <span className="text-xs text-muted-foreground font-mono">
                        {suite.duration_ms < 1000 ? `${suite.duration_ms}ms` : `${(suite.duration_ms / 1000).toFixed(2)}s`}
                      </span>
                    </button>

                    <div className="flex items-center gap-2">
                      <Badge
                        variant={hasFailed ? "destructive" : isSkipped ? "secondary" : "outline"}
                        className={cn(
                          "text-[10px] uppercase font-mono tracking-wider",
                          !hasFailed && !isSkipped && "border-emerald-500/40 text-emerald-600 dark:text-emerald-400 bg-emerald-500/10",
                        )}
                      >
                        {suite.status}
                      </Badge>
                      {suite.raw_output && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleRaw(suite.name)}
                          className="h-7 text-[11px] px-2 text-muted-foreground flex items-center gap-1"
                        >
                          <Terminal className="size-3" />
                          {isRawShown ? "Hide Output" : "Raw Output"}
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Raw Output Pane */}
                  {isRawShown && suite.raw_output && (
                    <div className="bg-zinc-950 p-3 font-mono text-[11px] text-zinc-300 overflow-x-auto max-h-72 border-b">
                      <pre className="whitespace-pre-wrap">{suite.raw_output}</pre>
                    </div>
                  )}

                  {/* Test Cases */}
                  {isExpanded && (
                    <div className="divide-y divide-border">
                      {suite.tests.length === 0 ? (
                        <div className="p-4 text-xs text-muted-foreground text-center">
                          {isSkipped
                            ? "Suite skipped (missing toolchain runner or requirements)."
                            : "No matching test cases found."}
                        </div>
                      ) : (
                        suite.tests.map((test, idx) => {
                          const testFailed = test.status === "failed";
                          const testSkipped = test.status === "skipped";

                          return (
                            <div key={idx} className="p-3 text-xs space-y-1.5 hover:bg-muted/10 transition-colors">
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-2 truncate">
                                  {testFailed ? (
                                    <XCircle className="size-4 shrink-0 text-destructive" />
                                  ) : testSkipped ? (
                                    <AlertTriangle className="size-4 shrink-0 text-muted-foreground" />
                                  ) : (
                                    <CheckCircle2 className="size-4 shrink-0 text-emerald-500" />
                                  )}
                                  <span className={cn("font-medium truncate", testFailed && "text-destructive")}>
                                    {test.name}
                                  </span>
                                </div>

                                <div className="flex items-center gap-2 shrink-0">
                                  {test.duration_ms !== undefined && (
                                    <span className="text-[11px] text-muted-foreground font-mono">
                                      {test.duration_ms}ms
                                    </span>
                                  )}
                                  {testFailed && (
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => handleFixTestWithAI(suite.name, test)}
                                      className="h-6 text-[11px] px-2 flex items-center gap-1 text-primary hover:text-primary"
                                    >
                                      <Sparkles className="size-3" />
                                      Fix with AI
                                    </Button>
                                  )}
                                </div>
                              </div>

                              {test.message && (
                                <div className="rounded bg-destructive/10 border border-destructive/20 p-2.5 font-mono text-[11px] text-destructive whitespace-pre-wrap mt-1">
                                  {test.message}
                                </div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
