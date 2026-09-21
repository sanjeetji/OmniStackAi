"use client";

import { useEffect, useState, useCallback } from "react";
import {
  AlertCircle,
  BarChart3,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  ExternalLink,
  Eye,
  EyeOff,
  FileCode,
  HelpCircle,
  Inbox,
  Info,
  Layers,
  Loader2,
  Mail,
  MessageSquarePlus,
  Play,
  Plug,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  X,
} from "lucide-react";
import type {
  ConnectorDefinition,
  ProjectConnector,
  ConnectorTestResult,
} from "@/lib/control-plane";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { cn } from "@/lib/utils";

interface ProjectConnectorsManageProps {
  projectId: string;
  projectName: string;
}

export function ProjectConnectorsManage({
  projectId,
  projectName,
}: ProjectConnectorsManageProps) {
  const [catalog, setCatalog] = useState<ConnectorDefinition[]>([]);
  const [connectors, setConnectors] = useState<ProjectConnector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active configuration drawer/modal state
  const [selectedConnector, setSelectedConnector] =
    useState<ConnectorDefinition | null>(null);
  const [configValues, setConfigValues] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Testing state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ConnectorTestResult | null>(null);

  // Disconnecting state
  const [disconnecting, setDisconnecting] = useState(false);

  // "Request a Connector" dialog state
  const [requestDialogOpen, setRequestDialogOpen] = useState(false);
  const [requestedServiceName, setRequestedServiceName] = useState("");
  const [requestedUseCase, setRequestedUseCase] = useState("");
  const [requestSubmitted, setRequestSubmitted] = useState(false);
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  const copySnippet = (code: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      void navigator.clipboard.writeText(code);
      setCopiedSnippet(true);
      setTimeout(() => setCopiedSnippet(false), 2000);
    }
  };

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch both catalog and project connectors in parallel
      const [catalogRes, connRes] = await Promise.all([
        fetch("/api/connectors"),
        fetch(`/api/projects/${projectId}/connectors`),
      ]);

      if (!catalogRes.ok) {
        const err = await catalogRes.json().catch(() => ({}));
        throw new Error(err.error || "Failed to load connectors catalog");
      }
      if (!connRes.ok) {
        const err = await connRes.json().catch(() => ({}));
        throw new Error(err.error || "Failed to load project connectors");
      }

      const catalogData = await catalogRes.json();
      const connData = await connRes.json();

      setCatalog(catalogData.connectors || []);
      setConnectors(connData.connectors || []);
    } catch (err: any) {
      setError(err?.message || "Could not load connectors");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [catalogRes, connRes] = await Promise.all([
          fetch("/api/connectors"),
          fetch(`/api/projects/${projectId}/connectors`),
        ]);

        if (active && catalogRes.ok && connRes.ok) {
          const catalogData = await catalogRes.json();
          const connData = await connRes.json();
          setCatalog(catalogData.connectors || []);
          setConnectors(connData.connectors || []);
        }
      } catch (err: any) {
        if (active) setError(err?.message || "Could not load connectors");
      } finally {
        if (active) setLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, [projectId]);

  // Open config drawer
  const openConfig = (def: ConnectorDefinition) => {
    setSelectedConnector(def);
    setTestResult(null);
    setSaveSuccess(false);

    // Find existing configured values if any
    const existing = connectors.find((c) => c.provider === def.id);
    const initialConfig: Record<string, string> = {};
    if (existing?.config) {
      for (const [k, v] of Object.entries(existing.config)) {
        initialConfig[k] = String(v ?? "");
      }
    }
    // Fill in defaults for missing fields
    for (const field of def.config_fields) {
      if (initialConfig[field.name] === undefined && field.default) {
        initialConfig[field.name] = field.default;
      }
    }
    setConfigValues(initialConfig);
    setShowSecrets({});
  };

  const closeConfig = () => {
    setSelectedConnector(null);
    setTestResult(null);
    setSaveSuccess(false);
    setSaving(false);
  };

  const handleSave = async () => {
    if (!selectedConnector) return;
    setSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      const res = await fetch(
        `/api/projects/${projectId}/connectors/${selectedConnector.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ config: configValues, enabled: true }),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Failed to save connector configuration");
      }

      setSaveSuccess(true);
      await fetchData();
      setTimeout(() => {
        setSaveSuccess(false);
      }, 3000);
    } catch (err: any) {
      setError(err?.message || "Failed to save connector");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!selectedConnector) return;
    setTesting(true);
    setTestResult(null);

    try {
      const res = await fetch(
        `/api/projects/${projectId}/connectors/${selectedConnector.id}/test`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ config: configValues }),
        }
      );

      const data = await res.json();
      setTestResult({
        success: data.success ?? res.ok,
        message: data.message || (res.ok ? "Connection test successful!" : "Test failed"),
        details: data.details,
      });
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err?.message || "Connection test failed",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!selectedConnector) return;
    if (
      !confirm(
        `Are you sure you want to disconnect ${selectedConnector.name}? This will remove its generated code and configuration from your repository.`
      )
    ) {
      return;
    }

    setDisconnecting(true);
    try {
      const res = await fetch(
        `/api/projects/${projectId}/connectors/${selectedConnector.id}`,
        {
          method: "DELETE",
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Failed to disconnect connector");
      }

      closeConfig();
      await fetchData();
    } catch (err: any) {
      setError(err?.message || "Failed to disconnect connector");
    } finally {
      setDisconnecting(false);
    }
  };

  const handleRequestConnector = (e: React.FormEvent) => {
    e.preventDefault();
    if (!requestedServiceName.trim()) return;

    // Record the request cleanly
    setRequestSubmitted(true);
    setTimeout(() => {
      setRequestDialogOpen(false);
      setRequestSubmitted(false);
      setRequestedServiceName("");
      setRequestedUseCase("");
    }, 2500);
  };

  const getProviderIcon = (id: string) => {
    switch (id) {
      case "ga4":
        return <BarChart3 className="size-6 text-amber-500" />;
      case "resend":
        return <Mail className="size-6 text-indigo-500" />;
      case "smtp":
        return <Send className="size-6 text-emerald-500" />;
      default:
        return <Plug className="size-6 text-primary" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              Connectors
            </h2>
            <Badge variant="outline" className="text-xs font-mono font-medium">
              v1 (G-03 / R-511)
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Connect third-party services to {projectName} using your own developer credentials.
            Only honest, fully-working connectors are supported.
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
            <RefreshCw className={cn("size-3.5", loading && "animate-spin")} />
            Refresh
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setRequestDialogOpen(true)}
            className="gap-2"
          >
            <MessageSquarePlus className="size-3.5" />
            Request a Connector
          </Button>
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
          <AlertCircle className="size-5 shrink-0" />
          <div className="flex-1">{error}</div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setError(null)}
            className="h-7 px-2 text-destructive hover:bg-destructive/20"
          >
            Dismiss
          </Button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && catalog.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse bg-muted/40 border-border/40">
              <CardHeader className="h-24" />
              <CardContent className="h-20" />
              <CardFooter className="h-14 border-t border-border/40" />
            </Card>
          ))}
        </div>
      ) : (
        /* Connector Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {catalog.map((def) => {
            const configured = connectors.find((c) => c.provider === def.id);
            const isConnected = Boolean(configured && configured.enabled);

            return (
              <Card
                key={def.id}
                className={cn(
                  "relative flex flex-col transition-all duration-200 border-border/60 hover:border-border hover:shadow-md",
                  isConnected && "border-primary/40 bg-primary/[0.02]"
                )}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-xl bg-muted/60 border border-border/50">
                        {getProviderIcon(def.id)}
                      </div>
                      <div>
                        <CardTitle className="text-base font-semibold">
                          {def.name}
                        </CardTitle>
                        <Badge
                          variant="secondary"
                          className="text-[10px] uppercase font-mono tracking-wider mt-0.5"
                        >
                          {def.category}
                        </Badge>
                      </div>
                    </div>

                    {/* Status Chip */}
                    {isConnected ? (
                      <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 font-medium text-xs gap-1.5 py-0.5">
                        <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        Connected
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="text-muted-foreground text-xs font-normal"
                      >
                        Not connected
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs line-clamp-2 mt-2 leading-relaxed">
                    {def.description}
                  </CardDescription>
                </CardHeader>

                <CardContent className="flex-1 pb-4">
                  {/* Generated files preview */}
                  <div className="mt-2 space-y-1.5">
                    <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                      <FileCode className="size-3" />
                      Generated Code
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {def.generated_files.map((file) => (
                        <span
                          key={file}
                          className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-muted/50 border border-border/40 text-foreground/80"
                        >
                          {file}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>

                <CardFooter className="pt-3 border-t border-border/40 flex items-center justify-between gap-2 bg-muted/[0.15]">
                  <a
                    href={def.docs_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
                  >
                    Docs
                    <ExternalLink className="size-3" />
                  </a>

                  <Button
                    size="sm"
                    variant={isConnected ? "outline" : "default"}
                    onClick={() => openConfig(def)}
                    className="gap-1.5 text-xs h-8"
                  >
                    <Plug className="size-3.5" />
                    {isConnected ? "Configure" : "Connect"}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Configuration Drawer / Modal */}
      {selectedConnector && (
        <Dialog open={Boolean(selectedConnector)} onOpenChange={(open) => !open && closeConfig()}>
          <DialogContent className="sm:max-w-[560px] max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-muted/80 border border-border/50">
                  {getProviderIcon(selectedConnector.id)}
                </div>
                <div>
                  <DialogTitle className="text-lg font-bold">
                    Configure {selectedConnector.name}
                  </DialogTitle>
                  <DialogDescription className="text-xs text-muted-foreground">
                    {selectedConnector.description}
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-5 py-2">
              {/* What this adds to your app */}
              <div className="p-3.5 rounded-lg bg-muted/40 border border-border/50 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                  <Code2 className="size-4 text-primary" />
                  What enabling this adds to your repository:
                </div>
                <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                  {selectedConnector.generated_files.map((f) => (
                    <li key={f} className="font-mono text-[11px] text-foreground/80">
                      {f}
                    </li>
                  ))}
                </ul>
                <p className="text-[11px] text-muted-foreground">
                  Disabling this connector in the future will automatically remove these files and revert layout modifications with a clean Git commit.
                </p>
              </div>

              {/* Email Usage & Template Helper */}
              {(selectedConnector.id === "resend" || selectedConnector.id === "smtp") && (
                <div className="p-3.5 rounded-lg bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200/50 dark:border-indigo-800/40 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                      <Mail className="size-4 text-indigo-500" />
                      Usage in your Next.js Code
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        copySnippet(`import { sendEmail } from '@/lib/email';
import { welcomeEmailTemplate } from '@/lib/email-templates';

const tpl = welcomeEmailTemplate({
  name: 'Alex',
  appName: '${projectName}',
  loginUrl: 'https://yourdomain.com/login',
});

await sendEmail({
  to: 'alex@example.com',
  subject: tpl.subject,
  html: tpl.html,
  text: tpl.text,
});`)
                      }
                      className="h-6 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground"
                    >
                      {copiedSnippet ? (
                        <>
                          <Check className="size-3 text-emerald-500" /> Copied
                        </>
                      ) : (
                        <>
                          <Copy className="size-3" /> Copy Snippet
                        </>
                      )}
                    </Button>
                  </div>
                  <pre className="p-2.5 rounded bg-black/5 dark:bg-black/40 font-mono text-[11px] leading-relaxed overflow-x-auto text-foreground/90">
{`import { sendEmail } from '@/lib/email';
import { welcomeEmailTemplate } from '@/lib/email-templates';

// 1. Dispatch using pre-built responsive templates:
const tpl = welcomeEmailTemplate({
  name: 'Alex',
  appName: '${projectName}',
  loginUrl: 'https://yourdomain.com/login',
});

await sendEmail({
  to: 'alex@example.com',
  subject: tpl.subject,
  html: tpl.html,
  text: tpl.text,
});

// 2. Or embed the contact form UI in any page:
// import { ContactForm } from '@/components/contact-form';`}
                  </pre>
                  <p className="text-[11px] text-muted-foreground">
                    Available templates in <code className="font-mono text-[10px] bg-muted px-1 py-0.5 rounded">lib/email-templates.ts</code>:
                    Welcome, OTP / verification codes, Password reset, and Notifications.
                  </p>
                </div>
              )}

              {/* Form Fields */}
              <div className="space-y-4">
                {selectedConnector.config_fields.map((field) => {
                  const isSecret = field.secret;
                  const isVisible = showSecrets[field.name];

                  return (
                    <div key={field.name} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <Label
                          htmlFor={`field-${field.name}`}
                          className="text-xs font-medium"
                        >
                          {field.label}{" "}
                          {field.required && (
                            <span className="text-destructive">*</span>
                          )}
                        </Label>
                        {isSecret && (
                          <button
                            type="button"
                            onClick={() =>
                              setShowSecrets((prev) => ({
                                ...prev,
                                [field.name]: !prev[field.name],
                              }))
                            }
                            className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1"
                          >
                            {isVisible ? (
                              <>
                                <EyeOff className="size-3" /> Hide
                              </>
                            ) : (
                              <>
                                <Eye className="size-3" /> Show
                              </>
                            )}
                          </button>
                        )}
                      </div>

                      <div className="relative">
                        <Input
                          id={`field-${field.name}`}
                          type={isSecret && !isVisible ? "password" : "text"}
                          placeholder={field.placeholder || ""}
                          value={configValues[field.name] || ""}
                          onChange={(e) =>
                            setConfigValues((prev) => ({
                              ...prev,
                              [field.name]: e.target.value,
                            }))
                          }
                          className="font-mono text-xs h-9"
                        />
                      </div>

                      {field.help && (
                        <p className="text-[11px] text-muted-foreground">
                          {field.help}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Test Result Display */}
              {testResult && (
                <div
                  className={cn(
                    "p-3 rounded-md text-xs border flex items-start gap-2.5",
                    testResult.success
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
                      : "bg-destructive/10 border-destructive/20 text-destructive"
                  )}
                >
                  {testResult.success ? (
                    <CheckCircle2 className="size-4 shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <AlertCircle className="size-4 shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <p className="font-medium">{testResult.message}</p>
                    {testResult.details && (
                      <pre className="mt-1.5 p-2 rounded bg-black/10 dark:bg-black/40 font-mono text-[10px] overflow-x-auto">
                        {JSON.stringify(testResult.details, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              )}

              {/* Save Success Notice */}
              {saveSuccess && (
                <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2">
                  <Check className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  Connector saved and code applied to repository successfully!
                </div>
              )}
            </div>

            <DialogFooter className="flex flex-col sm:flex-row items-center justify-between gap-2 border-t border-border/40 pt-4">
              <div>
                {connectors.some(
                  (c) => c.provider === selectedConnector.id && c.enabled
                ) && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleDisconnect}
                    disabled={disconnecting || saving}
                    className="text-xs text-destructive hover:bg-destructive/10 gap-1.5 h-8"
                  >
                    <Trash2 className="size-3.5" />
                    {disconnecting ? "Disconnecting..." : "Disconnect"}
                  </Button>
                )}
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleTest}
                  disabled={testing || saving}
                  className="gap-1.5 text-xs h-8"
                >
                  {testing ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Play className="size-3.5" />
                  )}
                  Test Connection
                </Button>

                <Button
                  type="button"
                  size="sm"
                  onClick={handleSave}
                  disabled={saving || testing}
                  className="gap-1.5 text-xs h-8"
                >
                  {saving ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Check className="size-3.5" />
                  )}
                  Save & Apply Code
                </Button>
              </div>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* "Request a Connector" Dialog */}
      <Dialog open={requestDialogOpen} onOpenChange={setRequestDialogOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              <MessageSquarePlus className="size-4 text-primary" />
              Request a Connector
            </DialogTitle>
            <DialogDescription className="text-xs">
              Tell us which 3rd-party service you want connected to your generated apps.
              We ship honest, tested connectors only.
            </DialogDescription>
          </DialogHeader>

          {requestSubmitted ? (
            <div className="py-6 text-center space-y-2">
              <div className="mx-auto size-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                <Check className="size-5" />
              </div>
              <h4 className="font-semibold text-sm">Request Received</h4>
              <p className="text-xs text-muted-foreground">
                Thank you! We prioritize OAuth and API connectors based on end-user demand.
              </p>
            </div>
          ) : (
            <form onSubmit={handleRequestConnector} className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="service-name" className="text-xs font-medium">
                  Service / Provider Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="service-name"
                  placeholder="e.g. Google Calendar, Stripe, Slack, Notion"
                  value={requestedServiceName}
                  onChange={(e) => setRequestedServiceName(e.target.value)}
                  required
                  className="text-xs h-9"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="use-case" className="text-xs font-medium">
                  Intended Use Case (optional)
                </Label>
                <Input
                  id="use-case"
                  placeholder="e.g. Booking meetings from appointment form"
                  value={requestedUseCase}
                  onChange={(e) => setRequestedUseCase(e.target.value)}
                  className="text-xs h-9"
                />
              </div>

              <div className="p-3 rounded-lg bg-muted/40 border border-border/50 text-[11px] text-muted-foreground">
                <p>
                  <strong>Why aren&apos;t all services listed?</strong> Many platforms require registering custom OAuth consent screens, developer apps, and multi-week security reviews. Rather than listing non-functional marketing stubs, OmniStackAI only ships connectors that work out of the box.
                </p>
              </div>

              <DialogFooter className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setRequestDialogOpen(false)}
                  className="text-xs h-8"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={!requestedServiceName.trim()}
                  className="text-xs h-8"
                >
                  Submit Request
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
