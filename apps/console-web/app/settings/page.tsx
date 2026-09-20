import { Suspense } from "react";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import {
  Activity,
  CircleCheck,
  Cpu,
  Globe,
  KeyRound,
  Palette,
  Sparkles,
  TriangleAlert,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { getProviderStatus, type ProviderInfo, type ProviderStatus } from "@/lib/control-plane";
import { revealStyle } from "@/lib/motion";
import { getCurrentUser, getSessionToken } from "@/lib/session";
import { AccountUsageViewer } from "@/components/account-usage-viewer";
import { AIKeysManager } from "@/components/ai-keys-manager";
import { HostingKeysManager } from "@/components/hosting-keys-manager";
import { SkillsLibrary } from "@/components/skills-library";
import ThemeSwitcher from "@/components/theme-switcher";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Settings",
};

const SECTIONS: { id: string; label: string; icon: LucideIcon }[] = [
  { id: "account", label: "Account", icon: UserRound },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "skills", label: "Skills library", icon: Sparkles },
  { id: "providers", label: "Model providers", icon: Cpu },
  { id: "byok", label: "BYOK keys", icon: KeyRound },
  { id: "hosting", label: "Hosting", icon: Globe },
  { id: "usage", label: "AI usage", icon: Activity },
];

export default async function SettingsPage() {
  // The auth gate lives in this route's layout.tsx; this redirect only satisfies the type.
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  const token = await getSessionToken();

  return (
    <div className="grid gap-8">
      <header className="reveal" style={revealStyle(0)}>
        <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-pretty text-sm text-muted-foreground">
          Your account, how the console looks, and which model providers can run your builds.
        </p>
      </header>

      <div className="grid gap-8 lg:grid-cols-[200px_minmax(0,1fr)]">
        <nav aria-label="Settings sections" className="lg:sticky lg:top-20 lg:self-start">
          <ul className="flex gap-1 overflow-x-auto lg:flex-col">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <li key={id}>
                <a
                  href={`#${id}`}
                  className="inline-flex h-8 items-center gap-2 rounded-lg px-2.5 text-sm whitespace-nowrap text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <Icon className="size-4" aria-hidden="true" />
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="grid gap-8">
          <section
            id="account"
            aria-labelledby="account-title"
            className="reveal scroll-mt-20"
            style={revealStyle(1)}
          >
            <Card>
              <CardHeader>
                <CardTitle id="account-title" className="text-lg">
                  Account
                </CardTitle>
                <CardDescription>What the control-plane knows about you.</CardDescription>
              </CardHeader>
              <CardContent>
                <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
                  <Fact label="Name" value={user.name} />
                  <Fact label="Email" value={user.email} />
                  <Fact label="Plan">
                    <Badge variant="secondary" className="capitalize">
                      {user.plan}
                    </Badge>
                  </Fact>
                  <Fact label="Credit balance">
                    <span className="font-mono tabular-nums">
                      {user.credit_balance.toLocaleString("en-US")}
                    </span>
                    <span className="ml-1.5 text-xs text-muted-foreground">
                      spent on cloud model calls; local models are free
                    </span>
                  </Fact>
                  <Fact label="Role" value={user.role} className="capitalize" />
                  <Fact label="Bring your own key">
                    <Badge variant={user.byok_enabled ? "default" : "outline"}>
                      {user.byok_enabled ? "Enabled" : "Not enabled"}
                    </Badge>
                  </Fact>
                </dl>
                <p className="mt-5 text-xs text-muted-foreground">
                  Profile editing isn&rsquo;t available yet.
                </p>
              </CardContent>
            </Card>
          </section>

          <section
            id="appearance"
            aria-labelledby="appearance-title"
            className="reveal scroll-mt-20"
            style={revealStyle(2)}
          >
            <Card>
              <CardHeader>
                <CardTitle id="appearance-title" className="text-lg">
                  Appearance
                </CardTitle>
                <CardDescription>Dark is the default. Pick what you prefer.</CardDescription>
              </CardHeader>
              <CardContent>
                <ThemeSwitcher />
              </CardContent>
            </Card>
          </section>

          <section
            id="skills"
            aria-labelledby="skills-title"
            className="reveal scroll-mt-20"
            style={revealStyle(3)}
          >
            <SkillsLibrary />
          </section>

          <section
            id="providers"
            aria-labelledby="providers-title"
            className="reveal scroll-mt-20"
            style={revealStyle(4)}
          >
            {/* The only network-dependent section streams in behind the layout's auth gate
                (R-496), so the rest of Settings renders immediately. */}
            <Suspense fallback={<ProvidersSkeleton />}>
              <ProvidersSection token={token} />
            </Suspense>
          </section>

          <section
            id="byok"
            aria-labelledby="byok-title"
            className="reveal scroll-mt-20"
            style={revealStyle(5)}
          >
            <AIKeysManager />
          </section>

          <section
            id="hosting"
            aria-labelledby="hosting-title"
            className="reveal scroll-mt-20"
            style={revealStyle(6)}
          >
            <HostingKeysManager />
          </section>

          <section
            id="usage"
            aria-labelledby="usage-title"
            className="reveal scroll-mt-20"
            style={revealStyle(7)}
          >
            <AccountUsageViewer />
          </section>
        </div>
      </div>
    </div>
  );
}

function ProvidersFrame({ children }: { children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle id="providers-title" className="text-lg">
          Model providers
        </CardTitle>
        <CardDescription>
          Which providers have a key configured, and the one that would run your next build
          right now.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3">{children}</CardContent>
    </Card>
  );
}

function ProvidersSkeleton() {
  return (
    <ProvidersFrame>
      <div className="grid gap-2" role="status" aria-label="Loading provider status" aria-busy="true">
        <Skeleton className="h-5 w-64" />
        <Skeleton className="h-4 w-80 max-w-full" />
        <div className="mt-2 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      </div>
    </ProvidersFrame>
  );
}

async function ProvidersSection({ token }: { token: string | null }) {
  let status: ProviderStatus | null = null;
  let error: string | null = null;
  if (token) {
    try {
      status = await getProviderStatus(token);
    } catch {
      error = "Couldn't reach the model provider status service.";
    }
  }
  const configured = status?.providers.filter((provider) => provider.active).length ?? 0;

  return (
    <>
      <ProvidersFrame>
        {error ? (
          <p
            role="alert"
            className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          >
            <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {error}
          </p>
        ) : null}
        {status ? (
          <>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              {status.activeNow ? (
                <>
                  <Badge className="border-brand/30 bg-brand/15 text-brand">Ready</Badge>
                  <span>
                    Your next build uses{" "}
                    <span className="font-medium">{status.activeNow.providerId}</span>
                    <span className="text-muted-foreground"> · </span>
                    <span className="font-mono text-xs">{status.activeNow.modelId}</span>
                  </span>
                </>
              ) : (
                <>
                  <Badge variant="destructive">Not ready</Badge>
                  <span className="text-muted-foreground">
                    {status.activeNowError ?? "No provider is currently available."}
                  </span>
                </>
              )}
            </div>
            <p className="text-xs text-muted-foreground tabular-nums">
              Routing mode <span className="font-medium text-foreground">{status.routingMode}</span>
              {" · "}cloud tier{" "}
              <span className="font-medium text-foreground">
                {status.cloudTierSelected ?? "none selected"}
              </span>
              {" · "}
              {configured} of {status.providers.length} providers configured
            </p>
            {status.note ? <p className="text-xs text-muted-foreground">{status.note}</p> : null}
          </>
        ) : null}
      </ProvidersFrame>

      {status ? (
        <ul className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Providers">
          {status.providers.map((provider) => (
            <li key={provider.providerId}>
              <ProviderCard
                provider={provider}
                runsNext={status.activeNow?.providerId === provider.providerId}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

function Fact({
  label,
  value,
  className,
  children,
}: {
  label: string;
  value?: string;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="grid gap-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("text-sm", className)}>{children ?? value}</dd>
    </div>
  );
}

function ProviderCard({ provider, runsNext }: { provider: ProviderInfo; runsNext: boolean }) {
  return (
    <Card size="sm" className={cn("h-full", runsNext && "ring-brand/40")}>
      <CardHeader>
        <CardTitle className="font-mono text-sm">{provider.providerId}</CardTitle>
        <CardDescription className="flex items-center gap-1.5">
          <Badge variant={provider.tier === "local" ? "secondary" : "outline"}>{provider.tier}</Badge>
          <span className="text-xs">{provider.kind}</span>
        </CardDescription>
        <CardAction>
          {provider.active ? (
            <Badge className="gap-1 border-brand/30 bg-brand/15 text-brand">
              <CircleCheck aria-hidden="true" />
              Active
            </Badge>
          ) : (
            <Badge variant="outline" className="gap-1 text-muted-foreground">
              <KeyRound aria-hidden="true" />
              Needs key
            </Badge>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="grid gap-2 text-xs">
        <div>
          <p className="text-muted-foreground">Default model</p>
          <p className="truncate font-mono text-foreground" title={provider.defaultModel}>
            {provider.defaultModel}
          </p>
        </div>
        {!provider.active && provider.keyEnv ? (
          <p className="text-muted-foreground">
            Set <code className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">{provider.keyEnv}</code>{" "}
            in <code className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">.env</code> to enable.
          </p>
        ) : null}
        {runsNext ? <p className="font-medium text-brand">Runs your next build</p> : null}
      </CardContent>
    </Card>
  );
}
