"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileCode,
  Globe,
  KeyRound,
  Loader2,
  RefreshCw,
  Rocket,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

function GithubIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
      <path d="M9 18c-4.51 2-5-2-7-2" />
    </svg>
  );
}
import type { PublishReadiness, TriggerPublishResponse } from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

interface PublishDialogProps {
  projectId: string;
  projectName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPublished?: (liveUrl: string) => void;
}

export function PublishDialog({
  projectId,
  projectName,
  open,
  onOpenChange,
  onPublished,
}: PublishDialogProps) {
  const [readiness, setReadiness] = useState<PublishReadiness | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected provider
  const [selectedProvider, setSelectedProvider] = useState<"vercel" | "netlify">("vercel");
  const [providerToken, setProviderToken] = useState("");
  const [savingToken, setSavingToken] = useState(false);

  // Deploying state
  const [deploying, setDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<TriggerPublishResponse | null>(null);
  const [deployError, setDeployError] = useState<string | null>(null);

  // Config tab
  const [showConfig, setShowConfig] = useState(false);

  const fetchReadiness = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/publish`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Failed to assess publish readiness");
      }
      const data: PublishReadiness = await res.json();
      setReadiness(data);
      if (data.provider === "netlify") {
        setSelectedProvider("netlify");
      } else {
        setSelectedProvider("vercel");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load publish readiness");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!open) return;
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/projects/${projectId}/publish`);
        if (!active) return;
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error || "Failed to assess publish readiness");
        }
        const data: PublishReadiness = await res.json();
        if (active) {
          setReadiness(data);
          setDeployResult(null);
          setDeployError(null);
          setShowConfig(false);
          if (data.provider === "netlify") {
            setSelectedProvider("netlify");
          } else {
            setSelectedProvider("vercel");
          }
        }
      } catch (err: any) {
        if (active) setError(err.message || "Failed to load publish readiness");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [open, projectId]);

  const handleConnectProvider = async () => {
    if (!providerToken.trim()) return;
    setSavingToken(true);
    setError(null);
    try {
      const res = await fetch(`/api/deploy/connections/${selectedProvider}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: providerToken.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Failed to save token");
      }
      setProviderToken("");
      await fetchReadiness();
    } catch (err: any) {
      setError(err.message || "Failed to connect provider");
    } finally {
      setSavingToken(false);
    }
  };

  const handlePublish = async () => {
    setDeploying(true);
    setDeployError(null);
    try {
      const res = await fetch(`/api/projects/${projectId}/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: selectedProvider }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Deployment trigger failed");
      }
      const result: TriggerPublishResponse = await res.json();
      setDeployResult(result);
      if (result.live_url && onPublished) {
        onPublished(result.live_url);
      }
    } catch (err: any) {
      setDeployError(err.message || "Failed to publish project");
    } finally {
      setDeploying(false);
    }
  };

  const getPathBadge = (path: number) => {
    switch (path) {
      case 1:
        return (
          <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            Path 1: Web-only
          </Badge>
        );
      case 2:
        return (
          <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400">
            Path 2: Web + Backend
          </Badge>
        );
      case 3:
        return (
          <Badge variant="outline" className="border-blue-500/30 bg-blue-500/10 text-blue-600 dark:text-blue-400">
            Path 3: Full-stack with DB
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Rocket className="h-5 w-5 text-primary" />
            <DialogTitle>Publish {projectName}</DialogTitle>
          </div>
          <DialogDescription>
            Deploy your repository directly to your connected Vercel or Netlify account.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-sm text-muted-foreground gap-3">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span>Evaluating project architecture and readiness...</span>
          </div>
        ) : deployResult ? (
          <div className="space-y-4 py-4">
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5 text-center space-y-3">
              <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
              <h3 className="font-semibold text-lg text-emerald-700 dark:text-emerald-300">
                Deployment Triggered Successfully!
              </h3>
              <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                Your build was submitted to {deployResult.deployment.provider.toUpperCase()}. Status:{" "}
                <span className="font-medium text-foreground">{deployResult.deployment.status}</span>.
              </p>

              {deployResult.live_url && (
                <div className="pt-2">
                  <a
                    href={deployResult.live_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-xs font-medium text-primary-foreground shadow hover:bg-primary/90"
                  >
                    <span>Visit Live Site</span>
                    <ArrowUpRight className="h-4 w-4" />
                  </a>
                </div>
              )}
            </div>

            <div className="rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
              <p>
                Deployment ID: <span className="font-mono text-foreground">{deployResult.deployment.id}</span>
              </p>
              {deployResult.deployment.commit_sha && (
                <p>
                  Commit: <span className="font-mono text-foreground">{deployResult.deployment.commit_sha.slice(0, 7)}</span>
                </p>
              )}
              {deployResult.deployment.url && (
                <p>
                  URL:{" "}
                  <a
                    href={deployResult.deployment.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {deployResult.deployment.url}
                  </a>
                </p>
              )}
            </div>

            <DialogFooter>
              <Button onClick={() => onOpenChange(false)} className="w-full">
                Done
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {error && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {deployError && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{deployError}</span>
              </div>
            )}

            {readiness && (
              <>
                {/* Path Classification Card */}
                <div className="rounded-xl border bg-card p-4 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Architecture Assessment
                    </span>
                    {getPathBadge(readiness.path)}
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {readiness.path_description}
                  </p>

                  {(readiness.path === 2 || readiness.path === 3) && (
                    <div className="pt-1">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs gap-1.5"
                        onClick={() => setShowConfig(!showConfig)}
                      >
                        <FileCode className="h-3.5 w-3.5" />
                        {showConfig ? "Hide" : "View"} Backend Config (render.yaml / fly.toml)
                      </Button>

                      {showConfig && (
                        <div className="mt-2 space-y-2">
                          {readiness.render_yaml && (
                            <div>
                              <span className="text-[11px] font-mono text-muted-foreground">render.yaml</span>
                              <pre className="mt-1 max-h-32 overflow-auto rounded bg-muted p-2 font-mono text-[11px]">
                                {readiness.render_yaml}
                              </pre>
                            </div>
                          )}
                          {readiness.fly_toml && (
                            <div>
                              <span className="text-[11px] font-mono text-muted-foreground">fly.toml</span>
                              <pre className="mt-1 max-h-32 overflow-auto rounded bg-muted p-2 font-mono text-[11px]">
                                {readiness.fly_toml}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {readiness.path === 3 && (
                    <div className="flex items-start gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 text-xs text-blue-700 dark:text-blue-300">
                      <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        <p className="font-medium">External Database Required</p>
                        <p className="text-[11px] text-muted-foreground">
                          Create a free PostgreSQL database on Neon (neon.tech) or Supabase (supabase.com), then add your connection string as <code className="font-mono text-foreground">DATABASE_URL</code> in Project Secrets.
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Git Repository Check */}
                <div className="rounded-xl border bg-card p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <GithubIcon className="h-4 w-4" />
                      <span className="text-xs font-medium">GitHub Repository</span>
                    </div>
                    {readiness.git_connected ? (
                      <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1 text-[11px]">
                        <CheckCircle2 className="h-3 w-3" />
                        {readiness.repo_name}
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[11px]">
                        Not connected
                      </Badge>
                    )}
                  </div>
                  {!readiness.git_connected && (
                    <p className="text-xs text-muted-foreground">
                      Deploying to Vercel/Netlify requires an active GitHub repository. Connect and push this project from the Git panel in the Studio header first.
                    </p>
                  )}
                </div>

                {/* Provider Selection & Connect */}
                <div className="rounded-xl border bg-card p-4 space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Target Hosting Provider
                  </span>

                  <Tabs
                    value={selectedProvider}
                    onValueChange={(val) => setSelectedProvider(val as "vercel" | "netlify")}
                  >
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="vercel">Vercel</TabsTrigger>
                      <TabsTrigger value="netlify">Netlify</TabsTrigger>
                    </TabsList>
                  </Tabs>

                  {/* Provider Key status */}
                  {readiness.provider_connected && readiness.provider === selectedProvider ? (
                    <div className="flex items-center justify-between rounded-lg bg-muted/50 p-2.5 text-xs">
                      <span className="text-muted-foreground">
                        Connected: <span className="font-medium text-foreground">{readiness.account_label || selectedProvider}</span>
                      </span>
                      <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 gap-1 text-[11px]">
                        <CheckCircle2 className="h-3 w-3" />
                        Ready
                      </Badge>
                    </div>
                  ) : (
                    <div className="space-y-2 rounded-lg border border-dashed p-3">
                      <div className="flex items-center gap-1.5 text-xs font-medium">
                        <KeyRound className="h-3.5 w-3.5 text-primary" />
                        <span>Connect {selectedProvider === "vercel" ? "Vercel" : "Netlify"} Token</span>
                      </div>
                      <div className="flex gap-2">
                        <Input
                          type="password"
                          placeholder={selectedProvider === "vercel" ? "vercel_pat_..." : "nfp_..."}
                          value={providerToken}
                          onChange={(e) => setProviderToken(e.target.value)}
                          className="h-8 text-xs font-mono"
                        />
                        <Button
                          size="sm"
                          className="h-8 text-xs shrink-0"
                          onClick={handleConnectProvider}
                          disabled={savingToken || !providerToken.trim()}
                        >
                          {savingToken && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
                          Connect
                        </Button>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        Or manage your hosting tokens in{" "}
                        <Link href="/settings#hosting" className="text-primary hover:underline" target="_blank">
                          Settings &rarr; Hosting
                        </Link>
                        .
                      </p>
                    </div>
                  )}
                </div>

                {/* Secrets propagation notice */}
                <div className="flex items-center justify-between rounded-lg bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                  <span>Environment secrets configured</span>
                  <span className="font-medium text-foreground">
                    {readiness.secrets_count} {readiness.secrets_count === 1 ? "secret" : "secrets"}
                  </span>
                </div>
              </>
            )}

            <DialogFooter className="pt-2 gap-2 sm:gap-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
                disabled={deploying}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handlePublish}
                disabled={
                  deploying ||
                  !readiness?.git_connected ||
                  !(readiness?.provider_connected && readiness?.provider === selectedProvider)
                }
                className="gap-1.5"
              >
                {deploying ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Publishing...</span>
                  </>
                ) : (
                  <>
                    <Rocket className="h-3.5 w-3.5" />
                    <span>Publish Now</span>
                  </>
                )}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
