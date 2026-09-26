"use client";

import { useEffect, useState } from "react";
import {
  Check,
  CircleCheck,
  Cpu,
  Eye,
  EyeOff,
  KeyRound,
  LoaderCircle,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  TriangleAlert,
  Zap,
} from "lucide-react";
import type { KeyMetadata, ProviderCatalogItem } from "@/lib/control-plane";
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

interface ProviderKeyEntry {
  providerId: string;
  name: string;
  kind: string;
  defaultModel: string;
  supportedModels: string[];
  keyMeta: KeyMetadata | null;
}

const DEFAULT_PROVIDERS: { id: string; name: string; kind: string; defaultModel: string; supportedModels: string[] }[] = [
  {
    id: "groq",
    name: "Groq",
    kind: "cloud",
    defaultModel: "openai/gpt-oss-120b",
    supportedModels: ["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
  },
  {
    id: "openai",
    name: "OpenAI",
    kind: "cloud",
    defaultModel: "gpt-4o",
    supportedModels: ["gpt-4o", "gpt-4o-mini", "o1-preview", "o3-mini"],
  },
  {
    id: "anthropic",
    name: "Anthropic",
    kind: "cloud",
    defaultModel: "claude-3-5-sonnet-20241022",
    supportedModels: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
  },
  {
    id: "nvidia",
    name: "NVIDIA",
    kind: "cloud",
    defaultModel: "nvidia/nemotron-3-ultra-550b-a55b",
    supportedModels: ["nvidia/nemotron-3-ultra-550b-a55b"],
  },
];

export function AIKeysManager() {
  const [providers, setProviders] = useState<ProviderKeyEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal edit/create state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<ProviderKeyEntry | null>(null);
  const [inputKey, setInputKey] = useState("");
  const [inputLabel, setInputLabel] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [savingKey, setSavingKey] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Testing key state
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; latency_ms?: number; message?: string; error?: string }>>({});

  // Delete state
  const [deletingProvider, setDeletingProvider] = useState<string | null>(null);

  const fetchKeysAndProviders = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch catalog
      let catalog = DEFAULT_PROVIDERS;
      try {
        const provRes = await fetch("/api/ai/providers");
        if (provRes.ok) {
          const pData = (await provRes.json()) as { providers: ProviderCatalogItem[] };
          if (pData.providers && pData.providers.length > 0) {
            catalog = pData.providers.map((p) => ({
              id: p.id,
              name: p.name,
              kind: p.kind,
              defaultModel: p.default_model,
              supportedModels: p.supported_models || [],
            }));
          }
        }
      } catch {
        // use fallback catalog
      }

      // 2. Fetch configured user keys
      const keysMap: Record<string, KeyMetadata> = {};
      for (const p of catalog) {
        try {
          const kRes = await fetch(`/api/ai/keys/${encodeURIComponent(p.id)}`);
          if (kRes.ok) {
            const kData = (await kRes.json()) as KeyMetadata;
            if (kData && kData.provider_id) {
              keysMap[kData.provider_id.toLowerCase()] = kData;
            }
          }
        } catch {
          // ignore
        }
      }

      const entries: ProviderKeyEntry[] = catalog.map((p) => ({
        providerId: p.id,
        name: p.name,
        kind: p.kind,
        defaultModel: p.defaultModel,
        supportedModels: p.supportedModels,
        keyMeta: keysMap[p.id.toLowerCase()] || null,
      }));

      setProviders(entries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load keys");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeysAndProviders();
  }, []);

  const handleOpenEdit = (entry: ProviderKeyEntry) => {
    setSelectedProvider(entry);
    setInputKey("");
    setInputLabel(entry.keyMeta?.label || `${entry.name} API Key`);
    setShowKey(false);
    setSaveError(null);
    setDialogOpen(true);
  };

  const handleSaveKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProvider) return;
    if (!inputKey.trim()) {
      setSaveError("API Key is required");
      return;
    }

    setSavingKey(true);
    setSaveError(null);
    try {
      const res = await fetch(`/api/ai/keys/${encodeURIComponent(selectedProvider.providerId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: inputKey.trim(),
          label: inputLabel.trim() || `${selectedProvider.name} Key`,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to save key");
      }

      setDialogOpen(false);
      await fetchKeysAndProviders();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Could not save key");
    } finally {
      setSavingKey(false);
    }
  };

  const handleDeleteKey = async (providerId: string) => {
    setDeletingProvider(providerId);
    try {
      const res = await fetch(`/api/ai/keys/${encodeURIComponent(providerId)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to delete key");
      }
      await fetchKeysAndProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete key");
    } finally {
      setDeletingProvider(null);
    }
  };

  const handleTestKey = async (providerId: string, testApiKey?: string) => {
    setTestingProvider(providerId);
    try {
      const res = await fetch(`/api/ai/keys/${encodeURIComponent(providerId)}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(testApiKey ? { api_key: testApiKey } : {}),
      });
      const data = await res.json();
      setTestResults((prev) => ({
        ...prev,
        [providerId]: {
          success: res.ok && data.success,
          latency_ms: data.latency_ms,
          message: data.message,
          error: data.error,
        },
      }));
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [providerId]: {
          success: false,
          error: err instanceof Error ? err.message : "Test failed",
        },
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-medium flex items-center gap-2">
            <KeyRound className="size-4 text-brand" />
            Bring Your Own Key (BYOK)
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Store your own provider keys securely (AES-256-GCM encrypted). When your key is used,{" "}
            <span className="text-foreground font-semibold">zero platform credits</span> are charged.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchKeysAndProviders}
          disabled={loading}
          className="gap-1.5 self-start sm:self-auto"
        >
          <RefreshCw className={cn("size-3.5", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg">
          <TriangleAlert className="size-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {providers.map((entry) => {
          const isConfigured = !!entry.keyMeta;
          const isTesting = testingProvider === entry.providerId;
          const isDeleting = deletingProvider === entry.providerId;
          const testRes = testResults[entry.providerId];

          return (
            <Card key={entry.providerId} size="sm" className="flex flex-col justify-between">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-sm font-semibold">{entry.name}</CardTitle>
                    <CardDescription className="text-xs font-mono mt-0.5">
                      {entry.providerId}
                    </CardDescription>
                  </div>
                  {isConfigured ? (
                    <Badge className="gap-1 border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                      <ShieldCheck className="size-3" />
                      BYOK Active
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="gap-1 text-muted-foreground">
                      Platform Shared
                    </Badge>
                  )}
                </div>
              </CardHeader>

              <CardContent className="grid gap-3 text-xs flex-1">
                <div>
                  <span className="text-muted-foreground block mb-0.5">Default Model:</span>
                  <span className="font-mono text-foreground font-medium">{entry.defaultModel}</span>
                </div>

                {entry.keyMeta ? (
                  <div className="rounded-md bg-muted/40 p-2 space-y-1">
                    <div className="flex justify-between text-muted-foreground text-[11px]">
                      <span>Label:</span>
                      <span className="text-foreground font-medium">{entry.keyMeta.label}</span>
                    </div>
                    {entry.keyMeta.last_used_at ? (
                      <div className="flex justify-between text-muted-foreground text-[11px]">
                        <span>Last used:</span>
                        <span>{new Date(entry.keyMeta.last_used_at).toLocaleDateString()}</span>
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="rounded-md border border-dashed border-border/80 p-2 text-muted-foreground text-[11px] leading-relaxed">
                    Using platform-provided credentials. Model calls will consume account credits.
                  </div>
                )}

                {testRes ? (
                  <div
                    className={cn(
                      "p-2 rounded text-[11px] flex items-center justify-between gap-1",
                      testRes.success
                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                        : "bg-destructive/10 text-destructive border border-destructive/20",
                    )}
                  >
                    <span>{testRes.success ? "Key valid & connected" : (testRes.error || "Connection failed")}</span>
                    {testRes.latency_ms ? (
                      <span className="font-mono tabular-nums">{testRes.latency_ms}ms</span>
                    ) : null}
                  </div>
                ) : null}

                <div className="pt-2 flex flex-wrap items-center gap-2 mt-auto">
                  {isConfigured ? (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleTestKey(entry.providerId)}
                        disabled={isTesting}
                        className="h-7 px-2 text-xs gap-1"
                      >
                        {isTesting ? (
                          <LoaderCircle className="size-3 animate-spin" />
                        ) : (
                          <Zap className="size-3" />
                        )}
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleOpenEdit(entry)}
                        className="h-7 px-2 text-xs gap-1"
                      >
                        Update
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteKey(entry.providerId)}
                        disabled={isDeleting}
                        className="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive gap-1 ml-auto"
                      >
                        {isDeleting ? (
                          <LoaderCircle className="size-3 animate-spin" />
                        ) : (
                          <Trash2 className="size-3" />
                        )}
                      </Button>
                    </>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleOpenEdit(entry)}
                      className="h-7 px-2.5 text-xs gap-1 w-full"
                    >
                      <Plus className="size-3" />
                      Configure Key
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Edit/Add Key Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={handleSaveKey}>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <KeyRound className="size-4 text-brand" />
                Configure {selectedProvider?.name} Key
              </DialogTitle>
              <DialogDescription>
                Your key will be encrypted at rest using AES-256-GCM. OmniStackAI will never expose
                it in any API response or log.
              </DialogDescription>
            </DialogHeader>

            <div className="grid gap-4 py-4">
              {saveError ? (
                <div className="flex items-center gap-2 p-2.5 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded">
                  <TriangleAlert className="size-3.5 shrink-0" />
                  <span>{saveError}</span>
                </div>
              ) : null}

              <div className="grid gap-1.5">
                <Label htmlFor="key-label" className="text-xs">
                  Key Label
                </Label>
                <Input
                  id="key-label"
                  placeholder="e.g. Production Key"
                  value={inputLabel}
                  onChange={(e) => setInputLabel(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>

              <div className="grid gap-1.5">
                <Label htmlFor="api-key" className="text-xs">
                  API Key Secret
                </Label>
                <div className="relative">
                  <Input
                    id="api-key"
                    type={showKey ? "text" : "password"}
                    placeholder="Enter API key secret"
                    value={inputKey}
                    onChange={(e) => setInputKey(e.target.value)}
                    className="h-8 text-sm pr-9 font-mono"
                    autoComplete="off"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-0.5"
                    tabIndex={-1}
                  >
                    {showKey ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                  </button>
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  Write-only: Once saved, the secret cannot be read back through the API.
                </p>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDialogOpen(false)}
                disabled={savingKey}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={savingKey || !inputKey.trim()} className="gap-1.5">
                {savingKey ? <LoaderCircle className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
                Save Key
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
