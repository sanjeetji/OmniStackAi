"use client";

import { useEffect, useState } from "react";
import {
  Check,
  CircleCheck,
  ExternalLink,
  Globe,
  KeyRound,
  LoaderCircle,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import type { DeployConnectionStatus } from "@/lib/control-plane";
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

interface ProviderConfig {
  id: "vercel" | "netlify";
  name: string;
  description: string;
  tokenDocsUrl: string;
  tokenDocsLabel: string;
  placeholder: string;
}

const PROVIDERS: ProviderConfig[] = [
  {
    id: "vercel",
    name: "Vercel",
    description: "Deploy frontend and Next.js applications directly to your Vercel team or personal account.",
    tokenDocsUrl: "https://vercel.com/account/tokens",
    tokenDocsLabel: "Generate a Vercel Personal Access Token",
    placeholder: "vercel_pat_...",
  },
  {
    id: "netlify",
    name: "Netlify",
    description: "Deploy static sites and single-page apps to global edge networks via Netlify.",
    tokenDocsUrl: "https://app.netlify.com/user/applications#personal-access-tokens",
    tokenDocsLabel: "Generate a Netlify Personal Access Token",
    placeholder: "nfp_...",
  },
];

export function HostingKeysManager() {
  const [connections, setConnections] = useState<Record<string, DeployConnectionStatus>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [activeProvider, setActiveProvider] = useState<ProviderConfig | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [accountLabelInput, setAccountLabelInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  // Delete state
  const [deletingProvider, setDeletingProvider] = useState<string | null>(null);

  const fetchConnections = async () => {
    setLoading(true);
    setError(null);
    try {
      const results: Record<string, DeployConnectionStatus> = {};
      for (const p of PROVIDERS) {
        const res = await fetch(`/api/deploy/connections/${p.id}`);
        if (res.ok) {
          const data: DeployConnectionStatus = await res.json();
          results[p.id] = data;
        } else {
          results[p.id] = { provider: p.id, connected: false };
        }
      }
      setConnections(results);
    } catch {
      setError("Unable to load hosting provider statuses. Please refresh to try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const results: Record<string, DeployConnectionStatus> = {};
        for (const p of PROVIDERS) {
          const res = await fetch(`/api/deploy/connections/${p.id}`);
          if (res.ok) {
            const data: DeployConnectionStatus = await res.json();
            results[p.id] = data;
          } else {
            results[p.id] = { provider: p.id, connected: false };
          }
        }
        if (active) setConnections(results);
      } catch {
        if (active) setError("Unable to load hosting provider statuses. Please refresh to try again.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const handleOpenDialog = (p: ProviderConfig) => {
    setActiveProvider(p);
    setApiKeyInput("");
    setAccountLabelInput(connections[p.id]?.account_label || "");
    setDialogError(null);
  };

  const handleSave = async () => {
    if (!activeProvider || !apiKeyInput.trim()) return;
    setSaving(true);
    setDialogError(null);

    try {
      const res = await fetch(`/api/deploy/connections/${activeProvider.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: apiKeyInput.trim(),
          account_label: accountLabelInput.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Failed to save access token.");
      }

      const updated: DeployConnectionStatus = await res.json();
      setConnections((prev) => ({ ...prev, [activeProvider.id]: updated }));
      setActiveProvider(null);
    } catch (err: any) {
      setDialogError(err.message || "Failed to save token");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (providerId: "vercel" | "netlify") => {
    setDeletingProvider(providerId);
    try {
      const res = await fetch(`/api/deploy/connections/${providerId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Failed to disconnect provider.");
      }
      setConnections((prev) => ({
        ...prev,
        [providerId]: { provider: providerId, connected: false },
      }));
    } catch (err: any) {
      setError(err.message || "Failed to disconnect provider");
    } finally {
      setDeletingProvider(null);
    }
  };

  return (
    <Card className="reveal">
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-primary" />
              <CardTitle>Hosting Providers</CardTitle>
            </div>
            <CardDescription>
              Connect your own Vercel or Netlify account via Personal Access Tokens. Deployments build and run directly in your own cloud accounts (₹0 hosting cost to OmniStackAI).
            </CardDescription>
          </div>
          <CardAction>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchConnections}
              disabled={loading}
              className="gap-2"
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              Refresh
            </Button>
          </CardAction>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            <TriangleAlert className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          {PROVIDERS.map((p) => {
            const conn = connections[p.id];
            const isConnected = conn?.connected;
            const isDeleting = deletingProvider === p.id;

            return (
              <div
                key={p.id}
                className="flex flex-col justify-between rounded-xl border bg-card p-5 shadow-sm transition-all hover:border-border/80"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-medium text-foreground">{p.name}</h3>
                      <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>
                    </div>
                    {isConnected ? (
                      <Badge variant="outline" className="gap-1 border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                        <CircleCheck className="h-3.5 w-3.5" />
                        Connected
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="text-xs">
                        Not connected
                      </Badge>
                    )}
                  </div>

                  {isConnected && (
                    <div className="rounded-lg bg-muted/50 p-2.5 text-xs text-muted-foreground space-y-1">
                      {conn.account_label && (
                        <p>
                          Account: <span className="font-medium text-foreground">{conn.account_label}</span>
                        </p>
                      )}
                      {conn.connected_at && (
                        <p>Connected: {new Date(conn.connected_at).toLocaleDateString()}</p>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-5 flex items-center justify-between gap-2 border-t pt-4">
                  {isConnected ? (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs text-destructive hover:bg-destructive/10 hover:text-destructive gap-1.5"
                        disabled={isDeleting}
                        onClick={() => handleDelete(p.id)}
                      >
                        {isDeleting ? (
                          <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="h-3.5 w-3.5" />
                        )}
                        Disconnect
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs gap-1.5"
                        onClick={() => handleOpenDialog(p)}
                      >
                        Update Key
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="default"
                      size="sm"
                      className="w-full text-xs gap-1.5"
                      onClick={() => handleOpenDialog(p)}
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Connect {p.name}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-start gap-3 rounded-lg border bg-muted/40 p-4 text-xs text-muted-foreground">
          <ShieldCheck className="h-4 w-4 shrink-0 text-primary mt-0.5" />
          <div className="space-y-1">
            <p className="font-medium text-foreground">Zero-knowledge key encryption</p>
            <p>
              Your personal access tokens are encrypted with AES-256-GCM using root machine keys before storage and are never returned in plaintext to the browser. Tokens are decrypted in memory only when triggering project deployments to your accounts.
            </p>
          </div>
        </div>
      </CardContent>

      {/* Connect Key Modal */}
      <Dialog open={!!activeProvider} onOpenChange={(open) => !open && setActiveProvider(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-primary" />
              Connect {activeProvider?.name}
            </DialogTitle>
            <DialogDescription>
              Enter a Personal Access Token with deployment permissions for your {activeProvider?.name} account.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {dialogError && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                <TriangleAlert className="h-4 w-4 shrink-0" />
                <span>{dialogError}</span>
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="api-key" className="text-xs font-medium">
                Personal Access Token <span className="text-destructive">*</span>
              </Label>
              <Input
                id="api-key"
                type="password"
                placeholder={activeProvider?.placeholder}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                className="font-mono text-xs"
              />
              {activeProvider && (
                <a
                  href={activeProvider.tokenDocsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline mt-1"
                >
                  {activeProvider.tokenDocsLabel}
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="account-label" className="text-xs font-medium">
                Account Label (Optional)
              </Label>
              <Input
                id="account-label"
                placeholder="e.g. personal, acme-team"
                value={accountLabelInput}
                onChange={(e) => setAccountLabelInput(e.target.value)}
                className="text-xs"
              />
              <p className="text-[11px] text-muted-foreground">
                Helps you identify which team or organization this token is associated with.
              </p>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveProvider(null)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving || !apiKeyInput.trim()}
              className="gap-1.5"
            >
              {saving && <LoaderCircle className="h-3.5 w-3.5 animate-spin" />}
              Save & Verify
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
