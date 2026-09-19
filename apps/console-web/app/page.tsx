import Link from "next/link";
import { redirect } from "next/navigation";
import {
  ArrowRight,
  Coins,
  Cpu,
  KeyRound,
  MessageSquareText,
  MonitorPlay,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import { getProviderStatus, type ProviderStatus } from "@/lib/control-plane";
import { getCurrentUser, getSessionToken } from "@/lib/session";
import AppShell from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/* The loop the Studio actually implements today (build → stream → live preview → multi-turn
 * edits), described plainly. */
const STEPS = [
  {
    icon: MessageSquareText,
    title: "Describe",
    body: "Say what the app should do, in plain language.",
  },
  {
    icon: Wrench,
    title: "Build",
    body: "Watch the code stream in: a real Next.js project with its backend.",
  },
  {
    icon: MonitorPlay,
    title: "Preview and edit",
    body: "Run it live, then keep changing it in the same chat.",
  },
];

export default async function HomePage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  // Same live provider status the Settings page shows, so the dashboard answers "can I build
  // right now?" without a second click. Unreachable → said so, never faked.
  const token = await getSessionToken();
  let status: ProviderStatus | null = null;
  let statusError: string | null = null;
  if (token) {
    try {
      status = await getProviderStatus(token);
    } catch {
      statusError = "Couldn't reach the model provider status service.";
    }
  }

  const firstName = user.name.trim().split(/\s+/)[0] || user.name;
  const configured = status ? status.providers.filter((provider) => provider.active).length : 0;

  return (
    <AppShell user={user}>
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Signed in as {user.email}</p>
          <h1 className="mt-1 text-balance text-3xl font-semibold tracking-tight">
            Good to see you, {firstName}
          </h1>
        </div>
        <Button asChild size="lg" className="h-10 px-4">
          <Link href="/studio">
            <Sparkles aria-hidden="true" />
            Open Studio
          </Link>
        </Button>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-12">
        <section aria-labelledby="start-building" className="grid gap-6 lg:col-span-7">
          <Card>
            <CardHeader>
              <CardTitle id="start-building" className="text-lg">
                Start building
              </CardTitle>
              <CardDescription>
                One conversation takes an idea to a running app. Here is the loop.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="grid gap-4">
                {STEPS.map(({ icon: Icon, title, body }, index) => (
                  <li key={title} className="flex gap-3">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <div className="grid gap-0.5">
                      <p className="font-medium">
                        <span className="mr-1.5 font-mono text-xs text-muted-foreground tabular-nums">
                          {index + 1}
                        </span>
                        {title}
                      </p>
                      <p className="text-sm text-muted-foreground">{body}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <Button asChild variant="link" className="mt-4 h-auto px-0">
                <Link href="/studio">
                  Start a new app
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Cpu className="size-4 text-muted-foreground" aria-hidden="true" />
                Model provider
              </CardTitle>
              <CardDescription>Which provider would run your next build right now.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              {statusError ? (
                <p role="status" className="text-sm text-destructive">
                  {statusError}
                </p>
              ) : status?.activeNow ? (
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="border-brand/30 bg-brand/15 text-brand">Ready</Badge>
                  <span className="text-sm">
                    <span className="font-medium">{status.activeNow.providerId}</span>
                    <span className="text-muted-foreground"> · </span>
                    <span className="font-mono text-xs">{status.activeNow.modelId}</span>
                  </span>
                </div>
              ) : status ? (
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="destructive">Not ready</Badge>
                  <span className="text-sm text-muted-foreground">
                    {status.activeNowError ?? "No provider is currently available."}
                  </span>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Provider status is unavailable.</p>
              )}
              {status ? (
                <p className="text-sm text-muted-foreground tabular-nums">
                  {configured} of {status.providers.length} providers configured.
                </p>
              ) : null}
              <Button asChild variant="link" className="h-auto w-fit px-0">
                <Link href="/settings">
                  Manage providers
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        </section>

        <aside
          aria-label="Your account"
          className="grid gap-4 self-start sm:grid-cols-2 lg:col-span-5 lg:grid-cols-1"
        >
          <Card size="sm">
            <CardHeader>
              <CardDescription>Plan</CardDescription>
              <CardTitle className="text-2xl font-semibold capitalize">{user.plan}</CardTitle>
            </CardHeader>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription className="flex items-center gap-1.5">
                <Coins className="size-3.5" aria-hidden="true" />
                Credit balance
              </CardDescription>
              <CardTitle className="font-mono text-2xl font-semibold tabular-nums">
                {user.credit_balance.toLocaleString("en-US")}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Spent on cloud model calls. Local models are free.
            </CardContent>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription className="flex items-center gap-1.5">
                <ShieldCheck className="size-3.5" aria-hidden="true" />
                Role
              </CardDescription>
              <CardTitle className="text-2xl font-semibold capitalize">{user.role}</CardTitle>
            </CardHeader>
          </Card>
          <Card size="sm">
            <CardHeader>
              <CardDescription className="flex items-center gap-1.5">
                <KeyRound className="size-3.5" aria-hidden="true" />
                Bring your own key
              </CardDescription>
              <CardTitle className="text-base">
                <Badge variant={user.byok_enabled ? "default" : "outline"}>
                  {user.byok_enabled ? "Enabled" : "Not enabled"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground">
              Use your own provider keys instead of platform credits.
            </CardContent>
          </Card>
        </aside>
      </div>
    </AppShell>
  );
}
