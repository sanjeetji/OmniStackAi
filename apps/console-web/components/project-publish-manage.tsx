"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
  ExternalLink,
  FileCode,
  Globe,
  LoaderCircle,
  RefreshCw,
  Rocket,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import type { DeploymentRecord, PublishReadiness } from "@/lib/control-plane";
import { formatDateTime, formatRelativeTime } from "@/lib/time";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PublishDialog } from "@/components/publish-dialog";
import { cn } from "@/lib/utils";

interface ProjectPublishManageProps {
  projectId: string;
  projectName: string;
}

export function ProjectPublishManage({
  projectId,
  projectName,
}: ProjectPublishManageProps) {
  const [readiness, setReadiness] = useState<PublishReadiness | null>(null);
  const [deployments, setDeployments] = useState<DeploymentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [showConfig, setShowConfig] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [readinessRes, depsRes] = await Promise.all([
        fetch(`/api/projects/${projectId}/publish`),
        fetch(`/api/projects/${projectId}/deployments`),
      ]);

      if (readinessRes.ok) {
        const rData = await readinessRes.json();
        setReadiness(rData);
      }

      if (depsRes.ok) {
        const dData = await depsRes.json();
        setDeployments(dData.deployments || []);
      }
    } catch {
      setError("Failed to load publish details. Please try refreshing.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [readinessRes, depsRes] = await Promise.all([
          fetch(`/api/projects/${projectId}/publish`),
          fetch(`/api/projects/${projectId}/deployments`),
        ]);

        if (active && readinessRes.ok) {
          const rData = await readinessRes.json();
          setReadiness(rData);
        }

        if (active && depsRes.ok) {
          const dData = await depsRes.json();
          setDeployments(dData.deployments || []);
        }
      } catch {
        if (active) setError("Failed to load publish details. Please try refreshing.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  const latest = deployments.length > 0 ? deployments[0] : readiness?.latest_deployment;
  const liveUrl = readiness?.live_url || latest?.url;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "ready":
        return (
          <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Ready
          </Badge>
        );
      case "building":
      case "queued":
        return (
          <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 gap-1">
            <LoaderCircle className="h-3 w-3 animate-spin" />
            {status}
          </Badge>
        );
      case "error":
        return (
          <Badge variant="destructive" className="gap-1">
            <AlertCircle className="h-3 w-3" />
            Failed
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Deploy & Publish</h2>
          <p className="text-sm text-muted-foreground">
            Manage your project deployments to Vercel and Netlify edge networks.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={() => setPublishDialogOpen(true)}
            className="gap-1.5"
          >
            <Rocket className="h-4 w-4" />
            Publish
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Live Site Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-base flex items-center gap-2">
                <Globe className="h-4 w-4 text-primary" />
                Live Production Environment
              </CardTitle>
              <CardDescription>
                Current live endpoint and production deployment status.
              </CardDescription>
            </div>
            {latest && getStatusBadge(latest.status)}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {liveUrl ? (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border bg-muted/30 p-4">
              <div className="space-y-1">
                <span className="text-xs text-muted-foreground uppercase font-semibold tracking-wider">
                  Live URL
                </span>
                <div className="flex items-center gap-2">
                  <a
                    href={liveUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-foreground hover:text-primary hover:underline text-sm flex items-center gap-1.5 break-all"
                  >
                    {liveUrl}
                    <ArrowUpRight className="h-4 w-4 shrink-0" />
                  </a>
                </div>
                {latest && (
                  <p className="text-xs text-muted-foreground">
                    Provider: <span className="font-medium capitalize text-foreground">{latest.provider}</span>
                    {" · "}Deployed {formatRelativeTime(latest.created_at)}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="gap-1.5 text-xs"
                >
                  <a href={liveUrl} target="_blank" rel="noopener noreferrer">
                    <span>Visit Site</span>
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </Button>
                <Button
                  size="sm"
                  onClick={() => setPublishDialogOpen(true)}
                  className="gap-1.5 text-xs"
                >
                  <Rocket className="h-3.5 w-3.5" />
                  Redeploy
                </Button>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed p-8 text-center space-y-3">
              <Globe className="h-8 w-8 text-muted-foreground mx-auto" />
              <div className="space-y-1">
                <h3 className="text-sm font-medium">No live deployment yet</h3>
                <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                  Your project has not been published to Vercel or Netlify. Click Publish to assess readiness and deploy.
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => setPublishDialogOpen(true)}
                className="gap-1.5"
              >
                <Rocket className="h-4 w-4" />
                Publish Now
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Architecture Guidance Card */}
      {readiness && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Architecture & Deployment Path</CardTitle>
              <Badge variant="outline">Path {readiness.path}</Badge>
            </div>
            <CardDescription>{readiness.path_description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {(readiness.path === 2 || readiness.path === 3) && (
              <div className="space-y-3 rounded-lg border bg-muted/20 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCode className="h-4 w-4 text-primary" />
                    <span className="text-xs font-semibold">Backend Deployment Configurations</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => setShowConfig(!showConfig)}
                  >
                    {showConfig ? "Hide Config" : "Show Config"}
                  </Button>
                </div>

                <p className="text-xs text-muted-foreground">
                  The frontend deploys to Vercel or Netlify. For the backend service, deploy using Render (render.yaml) or Fly.io (fly.toml).
                </p>

                {showConfig && (
                  <div className="grid gap-4 md:grid-cols-2 pt-2">
                    {readiness.render_yaml && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-mono text-muted-foreground">render.yaml</span>
                        <pre className="max-h-40 overflow-auto rounded bg-muted p-2 font-mono text-[11px]">
                          {readiness.render_yaml}
                        </pre>
                      </div>
                    )}
                    {readiness.fly_toml && (
                      <div className="space-y-1">
                        <span className="text-[11px] font-mono text-muted-foreground">fly.toml</span>
                        <pre className="max-h-40 overflow-auto rounded bg-muted p-2 font-mono text-[11px]">
                          {readiness.fly_toml}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {readiness.path === 3 && (
              <div className="flex items-start gap-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-4 text-xs text-blue-700 dark:text-blue-300">
                <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold">Database Connection String Required</p>
                  <p className="text-muted-foreground">
                    This project requires a PostgreSQL database. Provision a database on Neon (neon.tech) or Supabase (supabase.com), copy the connection URL, and store it in{" "}
                    <Link href={`/studio/${projectId}/manage?tab=secrets`} className="text-primary underline">
                      Project Secrets
                    </Link>{" "}
                    under <code className="font-mono text-foreground">DATABASE_URL</code>.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Deployment History Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Deployment History</CardTitle>
          <CardDescription>
            Record of all deployment attempts and live builds triggered for this project.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {deployments.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              No deployments recorded yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b text-muted-foreground">
                    <th className="pb-3 font-medium">Provider</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">URL</th>
                    <th className="pb-3 font-medium">Commit</th>
                    <th className="pb-3 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {deployments.map((dep) => (
                    <tr key={dep.id} className="hover:bg-muted/30">
                      <td className="py-3 font-medium capitalize">{dep.provider}</td>
                      <td className="py-3">{getStatusBadge(dep.status)}</td>
                      <td className="py-3">
                        {dep.url ? (
                          <a
                            href={dep.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline flex items-center gap-1 font-mono"
                          >
                            <span>{dep.url.replace(/^https?:\/\//, "")}</span>
                            <ArrowUpRight className="h-3 w-3" />
                          </a>
                        ) : (
                          <span className="text-muted-foreground">&mdash;</span>
                        )}
                      </td>
                      <td className="py-3 font-mono text-muted-foreground">
                        {dep.commit_sha ? dep.commit_sha.slice(0, 7) : "—"}
                      </td>
                      <td className="py-3 text-muted-foreground">
                        {formatDateTime(dep.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <PublishDialog
        projectId={projectId}
        projectName={projectName}
        open={publishDialogOpen}
        onOpenChange={setPublishDialogOpen}
        onPublished={() => {
          fetchData();
        }}
      />
    </div>
  );
}
