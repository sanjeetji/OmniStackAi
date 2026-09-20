"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  Coins,
  DollarSign,
  Layers,
  LoaderCircle,
  RefreshCw,
  TriangleAlert,
  Zap,
} from "lucide-react";
import type { AccountUsageReport } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function AccountUsageViewer() {
  const [days, setDays] = useState<number>(30);
  const [report, setReport] = useState<AccountUsageReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/usage?days=${days}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || "Failed to load usage");
        }
        const data = (await res.json()) as AccountUsageReport;
        if (active) setReport(data);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load usage data");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [days, refreshTrigger]);

  const handleRefresh = () => {
    setLoading(true);
    setRefreshTrigger((c) => c + 1);
  };

  const costDollars = report ? (report.totals.cost_micros_usd / 1_000_000).toFixed(4) : "0.0000";

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-medium flex items-center gap-2">
            <Activity className="size-4 text-brand" />
            AI & Model Usage
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Audit trail of model calls across all projects. Local models and BYOK calls incur 0 credits.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="inline-flex rounded-lg border border-border p-0.5 bg-muted/30">
            {[7, 30, 90].map((d) => (
              <button
                key={d}
                type="button"
                onClick={() => setDays(d)}
                className={cn(
                  "px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
                  days === d
                    ? "bg-background text-foreground shadow-xs font-semibold"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {d}d
              </button>
            ))}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
            className="h-8 px-2.5"
          >
            <RefreshCw className={cn("size-3.5", loading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg">
          <TriangleAlert className="size-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {/* Summary KPI Cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card size="sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Total Model Calls</CardDescription>
            <CardTitle className="text-2xl font-mono tabular-nums">
              {report ? report.totals.total_calls.toLocaleString() : "-"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-[11px] text-muted-foreground">
            {report ? `${report.totals.successful_calls} successful · ${report.totals.failed_calls} failed` : "Loading..."}
          </CardContent>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Tokens Processed</CardDescription>
            <CardTitle className="text-2xl font-mono tabular-nums">
              {report
                ? ((report.totals.input_tokens + report.totals.output_tokens) / 1000).toFixed(1) + "k"
                : "-"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-[11px] text-muted-foreground">
            {report
              ? `${report.totals.input_tokens.toLocaleString()} in · ${report.totals.output_tokens.toLocaleString()} out`
              : "Loading..."}
          </CardContent>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Estimated Cost (USD)</CardDescription>
            <CardTitle className="text-2xl font-mono tabular-nums">
              ${costDollars}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-[11px] text-muted-foreground">
            {report?.totals.unpriced_calls
              ? `${report.totals.unpriced_calls} unpriced calls (local / BYOK)`
              : "Across all provider calls"}
          </CardContent>
        </Card>

        <Card size="sm">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Credits Spent</CardDescription>
            <CardTitle className="text-2xl font-mono tabular-nums text-brand">
              {report ? report.totals.credits_spent.toLocaleString() : "-"}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-[11px] text-muted-foreground flex justify-between">
            <span>Balance:</span>
            <span className="font-mono text-foreground font-medium">
              {report ? report.credit_balance.toLocaleString() : "-"} credits
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Per-Project Breakdown */}
      {report && report.by_project && report.by_project.length > 0 ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Layers className="size-4 text-brand" />
              Usage by Project
            </CardTitle>
            <CardDescription className="text-xs">
              Model calls and credit charges incurred by each project over the selected period.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="border-b border-border bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Project</th>
                    <th className="px-4 py-2.5 font-medium text-right">Calls</th>
                    <th className="px-4 py-2.5 font-medium text-right">Cost (USD)</th>
                    <th className="px-4 py-2.5 font-medium text-right">Credits Spent</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {report.by_project.map((p) => (
                    <tr key={p.project_id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-2.5 font-medium text-foreground">
                        {p.project_name || p.project_id}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                        {p.calls.toLocaleString()}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                        ${(p.cost_micros_usd / 1_000_000).toFixed(4)}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-brand font-medium">
                        {p.credits_spent.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Daily Usage Table */}
      {report && report.by_day && report.by_day.length > 0 ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Activity className="size-4 text-brand" />
              Daily Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="border-b border-border bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Date</th>
                    <th className="px-4 py-2.5 font-medium text-right">Calls</th>
                    <th className="px-4 py-2.5 font-medium text-right">Input Tokens</th>
                    <th className="px-4 py-2.5 font-medium text-right">Output Tokens</th>
                    <th className="px-4 py-2.5 font-medium text-right">Cost (USD)</th>
                    <th className="px-4 py-2.5 font-medium text-right">Credits Spent</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {report.by_day.map((d) => (
                    <tr key={d.date} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-2.5 font-mono text-muted-foreground">{d.date}</td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">{d.calls.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">{d.input_tokens.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">{d.output_tokens.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">${(d.cost_micros_usd / 1_000_000).toFixed(4)}</td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-brand font-medium">{d.credits_spent.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
