"use client";

/**
 * ProjectAnalyticsManage — Lova-05 analytics dashboard
 *
 * Surfaces the user's own Google Analytics 4 data via the GA4 Data API
 * (Option A). OmniStackAI stores zero visitor data; all metrics live in the
 * user's GA property. No tracking cookies, no IP logging, no GDPR/DPDP risk
 * on our side.
 */

import { useCallback, useEffect, useState } from "react";
import {
  BarChart3,
  Clock,
  ExternalLink,
  Globe,
  Info,
  Link2,
  Loader2,
  Monitor,
  MousePointerClick,
  RefreshCw,
  Share2,
  Smartphone,
  Tablet,
  TrendingDown,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import type {
  AnalyticsCountryItem,
  AnalyticsDailyPoint,
  AnalyticsReport,
  AnalyticsTopItem,
  ProjectAnalyticsResponse,
} from "@/lib/control-plane";
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
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────

interface Props {
  projectId: string;
  projectName: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type RangeKey = "24h" | "7d" | "30d";

const RANGES: { key: RangeKey; label: string }[] = [
  { key: "24h", label: "24 hours" },
  { key: "7d", label: "7 days" },
  { key: "30d", label: "30 days" },
];

// ─────────────────────────────────────────────────────────────────────────────
// Utility helpers
// ─────────────────────────────────────────────────────────────────────────────

function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function fmtDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function fmtPct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function cacheAge(cachedAt: string): string {
  const diffMs = Date.now() - new Date(cachedAt).getTime();
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return `${secs}s ago`;
  return `${Math.floor(secs / 60)}m ago`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  trend,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sub?: string;
  trend?: "up" | "down" | "neutral";
}) {
  return (
    <Card className="relative overflow-hidden group">
      <CardContent className="pt-6 pb-5">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
              {label}
            </p>
            <p className="text-3xl font-bold tabular-nums leading-none tracking-tight">
              {value}
            </p>
            {sub && (
              <p className="text-xs text-muted-foreground mt-1">{sub}</p>
            )}
          </div>
          <div className="rounded-xl bg-primary/10 p-2.5 text-primary group-hover:bg-primary/15 transition-colors">
            <Icon className="size-5" />
          </div>
        </div>
        {trend && (
          <div className="absolute bottom-3 right-3">
            {trend === "up" ? (
              <TrendingUp className="size-3.5 text-emerald-500 opacity-60" />
            ) : trend === "down" ? (
              <TrendingDown className="size-3.5 text-rose-500 opacity-60" />
            ) : null}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MiniSparkline({ data }: { data: AnalyticsDailyPoint[] }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data.map((d) => d.sessions), 1);
  const points = data
    .map((d, i) => {
      const x = (i / Math.max(data.length - 1, 1)) * 100;
      const y = 100 - (d.sessions / max) * 90;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      viewBox="0 0 100 100"
      className="w-full h-full"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
          <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polyline
        points={points}
        fill="none"
        stroke="hsl(var(--primary))"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      <polygon
        points={`0,100 ${points} 100,100`}
        fill="url(#sparkFill)"
      />
    </svg>
  );
}

function TopItemsTable({
  title,
  items,
  valueLabel,
}: {
  title: string;
  items: AnalyticsTopItem[];
  valueLabel: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <h4 className="text-sm font-semibold mb-3">{title}</h4>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-3 text-sm">
            <div className="flex-1 min-w-0">
              <p className="truncate text-xs font-mono text-foreground/80">
                {item.label || "(direct)"}
              </p>
              <div className="mt-1 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary/70 transition-all"
                  style={{ width: `${(item.fraction * 100).toFixed(1)}%` }}
                />
              </div>
            </div>
            <div className="shrink-0 text-right">
              <p className="text-xs font-semibold tabular-nums">
                {fmtNum(item.value)}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {valueLabel}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CountryList({ countries }: { countries: AnalyticsCountryItem[] }) {
  if (!countries || countries.length === 0) return null;
  const FLAG_BASE = "https://flagcdn.com/16x12";
  const iso: Record<string, string> = {
    "United States": "us", India: "in", "United Kingdom": "gb",
    Germany: "de", France: "fr", Canada: "ca", Australia: "au",
    Japan: "jp", Brazil: "br", Netherlands: "nl", Singapore: "sg",
    Indonesia: "id", Poland: "pl", Spain: "es", Italy: "it",
  };
  return (
    <div className="space-y-2">
      {countries.slice(0, 8).map((c) => {
        const code = iso[c.country];
        return (
          <div key={c.country} className="flex items-center gap-3 text-sm">
            <div className="shrink-0 w-4">
              {code ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`${FLAG_BASE}/${code}.png`}
                  alt={c.country}
                  width={16}
                  height={12}
                  className="rounded-[2px]"
                />
              ) : (
                <Globe className="size-3.5 text-muted-foreground" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-xs">{c.country}</p>
              <div className="mt-1 h-1 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500/60"
                  style={{ width: `${(c.fraction * 100).toFixed(1)}%` }}
                />
              </div>
            </div>
            <span className="shrink-0 text-xs tabular-nums font-medium">
              {fmtNum(c.sessions)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export function ProjectAnalyticsManage({ projectId, projectName }: Props) {
  const [status, setStatus] = useState<ProjectAnalyticsResponse | null>(null);
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [range, setRange] = useState<RangeKey>("7d");
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  // Connect form state
  const [propertyId, setPropertyId] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);

  // Share link copy
  const [copied, setCopied] = useState(false);

  // ── Fetch analytics status ─────────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const resp = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/analytics`
      );
      if (!resp.ok) throw new Error("Failed to load analytics status");
      const data: ProjectAnalyticsResponse = await resp.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  // ── Fetch report ──────────────────────────────────────────────────────────
  const fetchReport = useCallback(
    async (r: RangeKey) => {
      if (!status?.connected) return;
      setReportLoading(true);
      setReportError(null);
      try {
        const resp = await fetch(
          `/api/projects/${encodeURIComponent(projectId)}/analytics/report?range=${r}`
        );
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          throw new Error(body.error || "Failed to fetch analytics report");
        }
        const data: AnalyticsReport = await resp.json();
        setReport(data);
      } catch (err) {
        setReportError(
          err instanceof Error ? err.message : "Failed to load report"
        );
      } finally {
        setReportLoading(false);
      }
    },
    [projectId, status?.connected]
  );

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const resp = await fetch(
          `/api/projects/${encodeURIComponent(projectId)}/analytics`
        );
        if (!resp.ok) throw new Error("Failed to load analytics status");
        const data: ProjectAnalyticsResponse = await resp.json();
        if (active) {
          setStatus(data);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  useEffect(() => {
    if (!status?.connected) return;
    let active = true;
    void (async () => {
      try {
        const resp = await fetch(
          `/api/projects/${encodeURIComponent(projectId)}/analytics/report?range=${range}`
        );
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          throw new Error(body.error || "Failed to fetch analytics report");
        }
        const data: AnalyticsReport = await resp.json();
        if (active) {
          setReport(data);
        }
      } catch (err) {
        if (active) {
          setReportError(
            err instanceof Error ? err.message : "Failed to load report"
          );
        }
      } finally {
        if (active) {
          setReportLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId, status?.connected, range]);

  // ── Connect GA4 ───────────────────────────────────────────────────────────
  const handleConnect = async () => {
    const pid = propertyId.trim();
    if (!pid || !/^\d+$/.test(pid)) {
      setConnectError(
        "Property ID must be a numeric string (e.g. 123456789). Find it in GA4 → Admin → Property Settings."
      );
      return;
    }
    setConnecting(true);
    setConnectError(null);
    try {
      const resp = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/analytics`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ provider: "ga4", property_id: pid }),
        }
      );
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.error || "Failed to connect analytics");
      }
      setPropertyId("");
      await fetchStatus();
    } catch (err) {
      setConnectError(
        err instanceof Error ? err.message : "Failed to connect analytics"
      );
    } finally {
      setConnecting(false);
    }
  };

  // ── Disconnect GA4 ────────────────────────────────────────────────────────
  const handleDisconnect = async () => {
    if (
      !confirm(
        "Disconnect Google Analytics 4? Your GA4 account and data are not affected — only the Property ID link in OmniStackAI is removed."
      )
    )
      return;
    setDisconnecting(true);
    try {
      const resp = await fetch(
        `/api/projects/${encodeURIComponent(projectId)}/analytics`,
        { method: "DELETE" }
      );
      if (!resp.ok) throw new Error("Failed to disconnect analytics");
      setReport(null);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect");
    } finally {
      setDisconnecting(false);
    }
  };

  const handleCopyLink = () => {
    if (!status?.live_url) return;
    void navigator.clipboard.writeText(status.live_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Loading / error states
  // ─────────────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
        <Loader2 className="size-4 animate-spin" />
        <span className="text-sm">Loading analytics…</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-destructive">
          {error}
        </CardContent>
      </Card>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Empty state: project not published yet
  // ─────────────────────────────────────────────────────────────────────────

  if (!status?.published) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <BarChart3 className="size-5 text-primary" />
            <CardTitle className="text-lg">Analytics</CardTitle>
          </div>
          <CardDescription>
            Publish your app first to start tracking real visitor traffic.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border-2 border-dashed border-muted p-8 text-center space-y-2">
            <Globe className="size-8 mx-auto text-muted-foreground/50" />
            <p className="text-sm font-medium">Project not yet published</p>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xs mx-auto">
              Deploy your app via the{" "}
              <span className="font-semibold">Publish</span> tab, then come back
              here to connect Google Analytics 4 and view live visitor data.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Not connected state
  // ─────────────────────────────────────────────────────────────────────────

  if (!status.connected) {
    return (
      <div className="space-y-6">
        {/* Header card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <BarChart3 className="size-5 text-primary" />
              <CardTitle className="text-lg">Analytics</CardTitle>
              {status.published && status.live_url && (
                <Badge
                  variant="outline"
                  className="text-emerald-600 dark:text-emerald-400 border-emerald-500/30 ml-auto"
                >
                  <Globe className="size-3 mr-1" />
                  Published
                </Badge>
              )}
            </div>
            <CardDescription>
              Connect your Google Analytics 4 property to see real visitor
              traffic — no data ever stored by OmniStackAI.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Zero-storage notice */}
            <div className="flex items-start gap-3 rounded-lg border bg-muted/30 p-4 text-sm">
              <Info className="size-4 shrink-0 text-primary mt-0.5" />
              <div>
                <p className="font-medium">Privacy-first: zero platform storage</p>
                <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                  OmniStackAI reads your GA4 data directly from Google&apos;s API on
                  demand and caches it for 5 minutes. We never store visitor IPs,
                  cookies, or any personal data — keeping you fully compliant with
                  GDPR and India&apos;s DPDP Act.
                </p>
              </div>
            </div>

            {/* GA4 OAuth connector check */}
            {!status.ga4_linked && (
              <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-400">
                <Info className="size-4 shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Google Analytics connector not linked</p>
                  <p className="text-xs mt-0.5 leading-relaxed opacity-90">
                    Go to <strong>Manage → Connectors</strong> and connect your
                    Google Analytics account first. This gives OmniStackAI
                    read-only access to pull your GA4 data.
                  </p>
                </div>
              </div>
            )}

            {/* Connect form */}
            <div className="space-y-3">
              <Label htmlFor="analytics-property-id" className="text-sm font-medium">
                GA4 Property ID
              </Label>
              <p className="text-xs text-muted-foreground">
                Find it in{" "}
                <a
                  href="https://analytics.google.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline underline-offset-2 hover:text-foreground"
                >
                  GA4 → Admin → Property Settings
                </a>
                . It&apos;s a numeric ID like <code className="rounded bg-muted px-1 py-0.5 text-[11px]">123456789</code>.
              </p>
              <div className="flex gap-2">
                <Input
                  id="analytics-property-id"
                  value={propertyId}
                  onChange={(e) => setPropertyId(e.target.value)}
                  placeholder="123456789"
                  className="font-mono max-w-xs"
                  disabled={connecting}
                  onKeyDown={(e) => e.key === "Enter" && void handleConnect()}
                />
                <Button
                  id="analytics-connect-btn"
                  onClick={() => void handleConnect()}
                  disabled={connecting || !propertyId.trim()}
                  className="gap-2"
                >
                  {connecting ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Link2 className="size-3.5" />
                  )}
                  Connect GA4
                </Button>
              </div>
              {connectError && (
                <p className="text-xs text-destructive">{connectError}</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Connected — full dashboard
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BarChart3 className="size-5 text-primary" />
          <h2 className="text-lg font-semibold">Analytics</h2>
          <Badge
            variant="outline"
            className="text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
          >
            GA4 connected
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {/* Live URL */}
          {status.live_url && (
            <Button
              id="analytics-copy-link-btn"
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={handleCopyLink}
            >
              {copied ? (
                <>✓ Copied!</>
              ) : (
                <>
                  <Share2 className="size-3.5" />
                  Share
                </>
              )}
            </Button>
          )}
          {status.live_url && (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
            >
              <a
                href={status.live_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink className="size-3.5" />
                Open app
              </a>
            </Button>
          )}
          <Button
            id="analytics-disconnect-btn"
            variant="ghost"
            size="sm"
            className="gap-1.5 text-xs text-muted-foreground hover:text-destructive"
            onClick={() => void handleDisconnect()}
            disabled={disconnecting}
          >
            {disconnecting ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <X className="size-3.5" />
            )}
            Disconnect
          </Button>
        </div>
      </div>

      {/* Property chip */}
      <div className="flex items-center gap-2 rounded-md border bg-muted/30 px-3 py-2 text-xs text-muted-foreground w-fit">
        <BarChart3 className="size-3.5 text-primary" />
        <span>
          GA4 Property ID:{" "}
          <code className="font-mono font-semibold text-foreground">
            {status.property_id}
          </code>
        </span>
      </div>

      {/* Range selector */}
      <div className="flex items-center gap-1 rounded-lg border bg-muted/40 p-1 w-fit">
        {RANGES.map((r) => (
          <button
            key={r.key}
            id={`analytics-range-${r.key}`}
            type="button"
            onClick={() => setRange(r.key)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition-all",
              range === r.key
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* Report loading / error */}
      {reportLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
          <Loader2 className="size-4 animate-spin" />
          Loading analytics data…
        </div>
      )}
      {reportError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive flex items-start gap-3">
          <Info className="size-4 shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Failed to load report</p>
            <p className="text-xs mt-0.5 opacity-90">{reportError}</p>
          </div>
        </div>
      )}

      {/* Empty state: published with no traffic yet */}
      {!reportLoading && !reportError && report?.empty && (
        <Card>
          <CardContent className="py-10 text-center space-y-3">
            <MousePointerClick className="size-10 mx-auto text-muted-foreground/40" />
            <p className="text-sm font-medium">No visits recorded yet</p>
            <p className="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed">
              Your app is live but hasn&apos;t received traffic in the selected
              period. Share your link to get your first visitors!
            </p>
            {status.live_url && (
              <div className="flex items-center justify-center gap-2 pt-1">
                <code className="rounded bg-muted px-2 py-1 text-xs font-mono">
                  {status.live_url}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5 text-xs"
                  onClick={handleCopyLink}
                >
                  <Share2 className="size-3.5" />
                  {copied ? "Copied!" : "Share"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Dashboard */}
      {!reportLoading && !reportError && report && !report.empty && (
        <>
          {/* 4 stat cards */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard
              icon={Users}
              label="Visitors"
              value={fmtNum(report.active_users)}
              sub="active users"
              trend="up"
            />
            <StatCard
              icon={Globe}
              label="Pageviews"
              value={fmtNum(report.pageviews)}
              sub="total views"
            />
            <StatCard
              icon={Clock}
              label="Avg. Engagement"
              value={fmtDuration(report.avg_engagement_seconds)}
              sub="per session"
            />
            <StatCard
              icon={TrendingDown}
              label="Bounce Rate"
              value={fmtPct(report.bounce_rate)}
              sub="single-page visits"
              trend={report.bounce_rate > 0.7 ? "down" : "neutral"}
            />
          </div>

          {/* Timeline sparkline */}
          {report.timeline && report.timeline.length > 1 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  Daily Traffic — {RANGES.find((r) => r.key === range)?.label}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-28">
                  <MiniSparkline data={report.timeline} />
                </div>
                <div className="mt-2 flex justify-between text-[10px] text-muted-foreground">
                  <span>{report.timeline[0]?.date}</span>
                  <span>
                    {report.timeline[report.timeline.length - 1]?.date}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tables row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top pages */}
            {report.top_pages && report.top_pages.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">
                    Top Pages
                  </CardTitle>
                  <CardDescription className="text-xs">
                    by pageviews
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <TopItemsTable
                    title=""
                    items={report.top_pages}
                    valueLabel="views"
                  />
                </CardContent>
              </Card>
            )}

            {/* Top referrers */}
            {report.top_referrers && report.top_referrers.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">
                    Top Referrers
                  </CardTitle>
                  <CardDescription className="text-xs">
                    by sessions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <TopItemsTable
                    title=""
                    items={report.top_referrers}
                    valueLabel="sessions"
                  />
                </CardContent>
              </Card>
            )}
          </div>

          {/* Devices & Countries row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Device breakdown */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Devices</CardTitle>
              </CardHeader>
              <CardContent>
                {(() => {
                  const { mobile, desktop, tablet } = report.devices;
                  const total = mobile + desktop + tablet || 1;
                  const bars = [
                    { label: "Desktop", value: desktop, Icon: Monitor, color: "bg-primary/70" },
                    { label: "Mobile", value: mobile, Icon: Smartphone, color: "bg-blue-500/60" },
                    { label: "Tablet", value: tablet, Icon: Tablet, color: "bg-violet-500/60" },
                  ];
                  return (
                    <div className="space-y-3">
                      {bars.map(({ label, value, Icon, color }) => (
                        <div key={label} className="flex items-center gap-3">
                          <Icon className="size-4 shrink-0 text-muted-foreground" />
                          <div className="flex-1">
                            <div className="flex justify-between text-xs mb-1">
                              <span>{label}</span>
                              <span className="font-medium tabular-nums">
                                {fmtPct(value / total)}
                              </span>
                            </div>
                            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                              <div
                                className={cn("h-full rounded-full transition-all", color)}
                                style={{ width: `${((value / total) * 100).toFixed(1)}%` }}
                              />
                            </div>
                          </div>
                          <span className="text-xs text-muted-foreground tabular-nums w-12 text-right">
                            {fmtNum(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </CardContent>
            </Card>

            {/* Countries */}
            {report.countries && report.countries.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">Top Countries</CardTitle>
                </CardHeader>
                <CardContent>
                  <CountryList countries={report.countries} />
                </CardContent>
              </Card>
            )}
          </div>

          {/* Cache age + refresh */}
          {report.cached_at && (
            <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
              <span className="flex items-center gap-1">
                <Clock className="size-3" />
                Data cached {cacheAge(report.cached_at)} · refreshes every 5 minutes
              </span>
              <Button
                id="analytics-refresh-btn"
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={() => void fetchReport(range)}
                disabled={reportLoading}
              >
                <RefreshCw className={cn("size-3", reportLoading && "animate-spin")} />
                Refresh
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
