import { redirect } from "next/navigation";
import { LayoutTemplate } from "lucide-react";
import { listTemplates, type TemplateSummary } from "@/lib/control-plane";
import { revealStyle } from "@/lib/motion";
import { getCurrentUser } from "@/lib/session";
import AppShell from "@/components/app-shell";
import TemplateCatalog from "@/components/template-catalog";
import { TEMPLATE_CATEGORIES } from "@/components/template-meta";

export const metadata = { title: "Templates" };
export const dynamic = "force-dynamic";

export default async function TemplatesPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  let templates: TemplateSummary[] = [];
  let unavailable = false;
  try {
    templates = (await listTemplates()).templates;
  } catch {
    unavailable = true;
  }

  return (
    <AppShell user={user}>
      <section aria-labelledby="templates-title" className="reveal" style={revealStyle(0)}>
        <h1 id="templates-title" className="text-balance text-3xl font-semibold tracking-tight">
          Start from a template
        </h1>
        <p className="mt-2 max-w-2xl text-pretty text-sm text-muted-foreground">
          Complete apps for real businesses: every app, a shared API and a database with sample
          data. Using one gives you your own project to run, change and grow. The original stays
          as it is.
        </p>
      </section>

      <div className="reveal mt-6" style={revealStyle(1)}>
        {unavailable ? (
          <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            The template catalogue is unavailable right now. Check that the platform is running, then reload.
          </p>
        ) : templates.length > 0 ? (
          <TemplateCatalog templates={templates} />
        ) : (
          <EmptyCatalogue />
        )}
      </div>
    </AppShell>
  );
}

function EmptyCatalogue() {
  return (
    <div className="rounded-xl border border-dashed border-border/70 p-6">
      <div className="flex items-center gap-2">
        <LayoutTemplate className="size-5 text-muted-foreground" aria-hidden="true" />
        <p className="font-medium">The first templates are on their way</p>
      </div>
      <p className="mt-1 max-w-xl text-pretty text-sm text-muted-foreground">
        Each one will be a complete, multi-app product you can use as is or reshape by chatting.
        These are the categories being built:
      </p>
      <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {TEMPLATE_CATEGORIES.map(({ id, label, icon: Icon, blurb }) => (
          <li key={id} className="flex items-start gap-2.5 rounded-lg bg-muted/50 px-3 py-2.5">
            <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium">{label}</p>
              <p className="text-xs text-muted-foreground">{blurb}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
