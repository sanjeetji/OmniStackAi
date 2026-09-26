"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Check,
  Cpu,
  Layers,
  LoaderCircle,
  RefreshCw,
  Sparkles,
  TriangleAlert,
  Zap,
} from "lucide-react";
import type { ProjectModelConfig, ProjectUsageReport } from "@/lib/control-plane";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface ProjectAIManageProps {
  projectId: string;
}

const PROVIDER_OPTIONS = [
  { id: "", name: "Default (Account / Platform)", defaultModel: "" },
  { id: "groq", name: "Groq", defaultModel: "llama-3.3-70b-versatile" },
  { id: "openai", name: "OpenAI", defaultModel: "gpt-4o" },
  { id: "anthropic", name: "Anthropic", defaultModel: "claude-3-5-sonnet-20241022" },
  { id: "nvidia", name: "NVIDIA", defaultModel: "nvidia/nemotron-3-ultra-550b-a55b" },
  { id: "ollama", name: "Local Ollama", defaultModel: "qwen2.5-coder:14b" },
];

export function ProjectAIManage({ projectId }: ProjectAIManageProps) {
  // Model config state
  const [modelConfig, setModelConfig] = useState<ProjectModelConfig | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [modelId, setModelId] = useState<string>("");
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [savingConfig, setSavingConfig] = useState(false);
  const [configSuccess, setConfigSuccess] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);

  // Usage state
  const [days, setDays] = useState<number>(30);
  const [usage, setUsage] = useState<ProjectUsageReport | null>(null);
  const [loadingUsage, setLoadingUsage] = useState(true);
  const [usageError, setUsageError] = useState<string | null>(null);
  const [refreshUsageTrigger, setRefreshUsageTrigger] = useState(0);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/model`);
        if (res.ok) {
          const data = (await res.json()) as ProjectModelConfig;
          if (active) {
            setModelConfig(data);
            setSelectedProvider(data.model_provider_id || "");
            setModelId(data.model_id || "");
          }
        }
      } catch (err) {
        if (active) setConfigError(err instanceof Error ? err.message : "Failed to load model config");
      } finally {
        if (active) setLoadingConfig(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/usage?days=${days}`);
        if (res.ok) {
          const data = (await res.json()) as ProjectUsageReport;
          if (active) setUsage(data);
        }
      } catch (err) {
        if (active) setUsageError(err instanceof Error ? err.message : "Failed to load usage data");
      } finally {
        if (active) setLoadingUsage(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId, days, refreshUsageTrigger]);

  const handleRefreshUsage = () => {
    setLoadingUsage(true);
    setRefreshUsageTrigger((c) => c + 1);
  };

  const handleProviderChange = (newProvider: string) => {
    setSelectedProvider(newProvider);
    const opt = PROVIDER_OPTIONS.find((p) => p.id === newProvider);
    if (opt && opt.defaultModel && !modelId) {
      setModelId(opt.defaultModel);
    }
  };

  const handleSaveModel = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingConfig(true);
    setConfigError(null);
    setConfigSuccess(false);
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/model`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_provider_id: selectedProvider.trim(),
          model_id: modelId.trim(),
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to update project model");
      }

      const updated = (await res.json()) as ProjectModelConfig;
      setModelConfig(updated);
      setConfigSuccess(true);
      setTimeout(() => setConfigSuccess(false), 3000);
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : "Failed to save model configuration");
    } finally {
      setSavingConfig(false);
    }
  };

  const costDollars = usage ? (usage.totals.cost_micros_usd / 1_000_000).toFixed(4) : "0.0000";

  return (
    <div className="space-y-6">
      {/* Model Pinning Card */}
      <Card>
        <form onSubmit={handleSaveModel}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Cpu className="size-4 text-brand" />
                  Model Configuration
                </CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  Pin a specific model or provider for this project. If unset, the project uses your
                  account BYOK key or the platform default.
                </CardDescription>
              </div>
              {modelConfig?.model_provider_id ? (
                <Badge variant="outline" className="border-brand/30 text-brand text-xs font-mono">
                  {modelConfig.model_provider_id}
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-xs">
                  Default
                </Badge>
              )}
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            {configError ? (
              <div className="flex items-center gap-2 p-2.5 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded">
                <TriangleAlert className="size-3.5 shrink-0" />
                <span>{configError}</span>
              </div>
            ) : null}

            {configSuccess ? (
              <div className="flex items-center gap-2 p-2.5 text-xs text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded">
                <Check className="size-3.5 shrink-0" />
                <span>Model settings updated successfully.</span>
              </div>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="model-provider" className="text-xs font-medium">
                  Provider
                </Label>
                <select
                  id="model-provider"
                  value={selectedProvider}
                  onChange={(e) => handleProviderChange(e.target.value)}
                  disabled={loadingConfig || savingConfig}
                  className="w-full h-8 px-2.5 rounded-md border border-input bg-background text-xs text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  {PROVIDER_OPTIONS.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="model-id" className="text-xs font-medium">
                  Model ID
                </Label>
                <Input
                  id="model-id"
                  placeholder="e.g. llama-3.3-70b-versatile or gpt-4o"
                  value={modelId}
                  onChange={(e) => setModelId(e.target.value)}
                  disabled={loadingConfig || savingConfig}
                  className="h-8 text-xs font-mono"
                />
              </div>
            </div>

            <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
              <p className="font-medium text-foreground">Billing Precedence:</p>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                <li>
                  <span className="font-semibold text-foreground">BYOK Key:</span> If you have saved a BYOK key for this provider, your key is used and <span className="text-emerald-600 dark:text-emerald-400 font-semibold">0 credits</span> are debited.
                </li>
                <li>
                  <span className="font-semibold text-foreground">Local Ollama:</span> Local model execution always incurs <span className="text-emerald-600 dark:text-emerald-400 font-semibold">0 credits</span>.
                </li>
                <li>
                  <span className="font-semibold text-foreground">Platform Cloud:</span> Uses platform shared keys and debits credits based on actual token usage.
                </li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex justify-end gap-2 border-t pt-3">
            <Button
              type="submit"
              size="sm"
              disabled={loadingConfig || savingConfig}
              className="gap-1.5"
            >
              {savingConfig ? (
                <LoaderCircle className="size-3.5 animate-spin" />
              ) : (
                <Check className="size-3.5" />
              )}
              Save Model Configuration
            </Button>
          </CardFooter>
        </form>
      </Card>

      {/* Project Usage Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Activity className="size-4 text-brand" />
                Project Usage
              </CardTitle>
              <CardDescription className="text-xs mt-0.5">
                Token consumption and cost breakdown for this project.
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <div className="inline-flex rounded-lg border border-border p-0.5 bg-muted/30">
                {[7, 30, 90].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDays(d)}
                    className={cn(
                      "px-2 py-0.5 text-xs font-medium rounded transition-colors",
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
                onClick={handleRefreshUsage}
                disabled={loadingUsage}
                className="h-7 px-2"
              >
                <RefreshCw className={cn("size-3", loadingUsage && "animate-spin")} />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {usageError ? (
            <div className="flex items-center gap-2 p-2.5 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded">
              <TriangleAlert className="size-3.5 shrink-0" />
              <span>{usageError}</span>
            </div>
          ) : null}

          {/* Project KPI Cards */}
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
            <div className="rounded-lg border p-3">
              <p className="text-[11px] text-muted-foreground">Calls</p>
              <p className="text-lg font-bold font-mono tabular-nums mt-0.5">
                {usage ? usage.totals.total_calls.toLocaleString() : "-"}
              </p>
            </div>
            <div className="rounded-lg border p-3">
              <p className="text-[11px] text-muted-foreground">Tokens</p>
              <p className="text-lg font-bold font-mono tabular-nums mt-0.5">
                {usage
                  ? ((usage.totals.input_tokens + usage.totals.output_tokens) / 1000).toFixed(1) + "k"
                  : "-"}
              </p>
            </div>
            <div className="rounded-lg border p-3">
              <p className="text-[11px] text-muted-foreground">Estimated Cost</p>
              <p className="text-lg font-bold font-mono tabular-nums mt-0.5">
                ${costDollars}
              </p>
            </div>
            <div className="rounded-lg border p-3">
              <p className="text-[11px] text-muted-foreground">Credits Spent</p>
              <p className="text-lg font-bold font-mono tabular-nums mt-0.5 text-brand">
                {usage ? usage.totals.credits_spent.toLocaleString() : "-"}
              </p>
            </div>
          </div>

          {/* Daily Table */}
          {usage && usage.by_day && usage.by_day.length > 0 ? (
            <div className="rounded-md border overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="border-b bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 font-medium">Date</th>
                    <th className="px-3 py-2 font-medium text-right">Calls</th>
                    <th className="px-3 py-2 font-medium text-right">Tokens</th>
                    <th className="px-3 py-2 font-medium text-right">Cost (USD)</th>
                    <th className="px-3 py-2 font-medium text-right">Credits</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {usage.by_day.map((d) => (
                    <tr key={d.date} className="hover:bg-muted/20">
                      <td className="px-3 py-2 font-mono text-muted-foreground">{d.date}</td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums">{d.calls}</td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums">
                        {((d.input_tokens + d.output_tokens) / 1000).toFixed(1)}k
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums">
                        ${(d.cost_micros_usd / 1_000_000).toFixed(4)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono tabular-nums text-brand font-medium">
                        {d.credits_spent}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-6 text-xs text-muted-foreground">
              No model activity recorded for this project in the selected period.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
