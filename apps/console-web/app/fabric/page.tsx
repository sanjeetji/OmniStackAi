import type { Metadata } from "next";
import overview from "@/data/overview.json";
import { getCurrentUser } from "@/lib/session";
import AppShell from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Model Fabric",
};

/** The Fabric page renders `data/overview.json` - a metadata-only snapshot that
 * `scripts/console.sh snapshot` regenerates from the agent-engine's `platform_console_snapshot()`
 * on every `task console:build`. It contains no keys; the page says what it is. Public route. */
export default async function FabricPage() {
  const { routingLadder, providers, priceBook, resilience, usage, builderShowcase } = overview;

  // The shell only needs to know whether to show the account menu or the sign-in actions, and
  // must not break if the control-plane is down.
  let user = null;
  try {
    user = await getCurrentUser();
  } catch {
    user = null;
  }

  const configured = providers.filter((provider) => provider.active).length;

  return (
    <AppShell user={user}>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          <p className="text-sm text-muted-foreground">Founder Stage 0 · local-first</p>
          <h1 className="mt-1 text-balance text-3xl font-semibold tracking-tight">
            Model fabric &amp; cost overview
          </h1>
          <p className="mt-2 text-pretty text-sm text-muted-foreground">{overview.note}</p>
        </div>
        <div className="grid justify-items-start gap-1 text-xs text-muted-foreground sm:justify-items-end sm:text-right">
          <Badge variant="outline" className="font-mono">
            snapshot v{String(overview.snapshotVersion)}
          </Badge>
          <span>
            Regenerated on every console build by{" "}
            <code className="font-mono">scripts/console.sh snapshot</code>.
          </span>
        </div>
      </header>

      <div className="mt-8 grid gap-6">
        <Section
          title="Routing ladder"
          description={`Routing mode: ${overview.routingMode}. Each level is tried before the next.`}
        >
          <ol className="grid gap-2">
            {routingLadder.map((step) => (
              <li
                key={step.level}
                className="flex flex-wrap items-center gap-3 rounded-lg border border-border/60 bg-card px-3 py-2.5"
              >
                <span className="w-7 font-mono text-xs font-semibold text-brand tabular-nums">
                  {step.level}
                </span>
                {step.tier ? (
                  <Badge variant="secondary">{step.tier}</Badge>
                ) : (
                  <Badge variant="outline">no model</Badge>
                )}
                <span className="text-sm">{step.action}</span>
              </li>
            ))}
          </ol>
        </Section>

        <div className="grid gap-6 xl:grid-cols-2">
          <Section
            title="Providers"
            description={`${configured} of ${providers.length} providers have a key configured in this snapshot.`}
          >
            <DataTable
              caption="Providers in the model fabric"
              head={[
                { label: "Provider" },
                { label: "Tier" },
                { label: "Default model" },
                { label: "Status", align: "right" },
              ]}
            >
              {providers.map((provider) => (
                <tr key={provider.providerId}>
                  <td className="px-3 py-2 font-mono text-xs">{provider.providerId}</td>
                  <td className="px-3 py-2">
                    <Badge variant={provider.tier === "local" ? "secondary" : "outline"}>
                      {provider.tier}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{provider.defaultModel}</td>
                  <td className="px-3 py-2 text-right">
                    {provider.active ? (
                      <Badge className="border-brand/30 bg-brand/15 text-brand">Active</Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground">
                        Needs key
                      </Badge>
                    )}
                  </td>
                </tr>
              ))}
            </DataTable>
          </Section>

          <Section title="Price book" description="List prices per million tokens, in USD.">
            <DataTable
              caption="Price book"
              head={[
                { label: "Provider" },
                { label: "Model" },
                { label: "Input $/M", align: "right" },
                { label: "Output $/M", align: "right" },
              ]}
            >
              {priceBook.map((entry) => (
                <tr key={`${entry.providerId}:${entry.modelId}`}>
                  <td className="px-3 py-2 font-mono text-xs">{entry.providerId}</td>
                  <td className="px-3 py-2 font-mono text-xs">{entry.modelId}</td>
                  <td className="px-3 py-2 text-right font-mono text-xs tabular-nums">
                    {entry.inputPerMTokUsd}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-xs tabular-nums">
                    {entry.outputPerMTokUsd}
                  </td>
                </tr>
              ))}
            </DataTable>
          </Section>
        </div>

        <Section
          title="Usage & resilience"
          description={
            usage.totalCalls === 0
              ? "No model calls are recorded in this snapshot."
              : "Recorded model calls in this snapshot."
          }
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Total calls" value={usage.totalCalls.toLocaleString("en-US")} />
            <Stat
              label="Successful / failed"
              value={`${usage.successfulCalls.toLocaleString("en-US")} / ${usage.failedCalls.toLocaleString("en-US")}`}
            />
            <Stat
              label="Tokens in / out"
              value={`${usage.inputTokens.toLocaleString("en-US")} / ${usage.outputTokens.toLocaleString("en-US")}`}
            />
            <Stat label="Total cost" value={`$${usage.totalCostUsd}`} />
            <Stat label="Latency p50 / p95" value={`${usage.latencyP50Ms} / ${usage.latencyP95Ms} ms`} />
            <Stat label="Unpriced calls" value={usage.unpricedCalls.toLocaleString("en-US")} />
            <Stat label="Circuit breaker">
              <Badge variant={resilience.circuitBreaker.enabled ? "default" : "outline"}>
                {resilience.circuitBreaker.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </Stat>
            <Stat
              label="Fallback chain"
              value={
                resilience.fallbackChain.length > 0
                  ? resilience.fallbackChain.join(" → ")
                  : "none configured"
              }
            />
          </div>
        </Section>

        <Section title="Builder showcase" description={builderShowcase.note}>
          <div className="grid gap-4">
            <div>
              <h3 className="text-sm font-medium">{builderShowcase.projectPlan.appName}</h3>
              <ul className="mt-2 grid gap-3 sm:grid-cols-2">
                {builderShowcase.projectPlan.apps.map((app) => (
                  <li key={app.appDir} className="rounded-lg border border-border/60 bg-card p-3">
                    <p className="text-sm font-medium">{app.label}</p>
                    <p className="mt-0.5 font-mono text-xs text-muted-foreground">{app.appDir}</p>
                    <ul className="mt-2 flex flex-wrap gap-1" aria-label="Verification gates">
                      {app.verify.gates.map((gate) => (
                        <li key={gate}>
                          <Badge variant="secondary" className="font-mono">
                            {gate}
                          </Badge>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium">
                Edit preview · <span className="font-mono">{builderShowcase.editPreview.baseExample}</span>
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {builderShowcase.editPreview.requestedChange}
              </p>
              <DiffBlock patch={builderShowcase.editPreview.unifiedPatch} />
            </div>
          </div>
        </Section>
      </div>
    </AppShell>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function DataTable({
  caption,
  head,
  children,
}: {
  caption: string;
  head: { label: string; align?: "left" | "right" }[];
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border/60 bg-background">
      <table className="w-full text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-muted/50 text-xs text-muted-foreground">
          <tr>
            {head.map((column) => (
              <th
                key={column.label}
                scope="col"
                className={cn("px-3 py-2 font-medium whitespace-nowrap", column.align === "right" ? "text-right" : "text-left")}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">{children}</tbody>
      </table>
    </div>
  );
}

function Stat({
  label,
  value,
  children,
}: {
  label: string;
  value?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-background p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-base tabular-nums">{children ?? value}</p>
    </div>
  );
}

/** Line-prefix coloring for a unified diff. The Code tab's tokenizer has no diff language, and
 * this page only ever shows one small patch, so three prefix rules do the job. */
function DiffBlock({ patch }: { patch: string }) {
  return (
    <pre className="mt-3 max-h-96 overflow-auto rounded-xl border border-border/60 bg-background p-3 font-mono text-xs leading-5">
      <code>
        {patch.split("\n").map((line, index) => {
          const added = line.startsWith("+") && !line.startsWith("+++");
          const removed = line.startsWith("-") && !line.startsWith("---");
          const hunk = line.startsWith("@@");
          return (
            <div
              key={index}
              className={cn(
                "px-1 whitespace-pre",
                added && "bg-brand/10 text-brand",
                removed && "bg-destructive/10 text-destructive",
                hunk && "text-muted-foreground",
              )}
            >
              {line || " "}
            </div>
          );
        })}
      </code>
    </pre>
  );
}
