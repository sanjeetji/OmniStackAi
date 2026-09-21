import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ArrowLeft, Check, Database, KeyRound, Plug, Users } from "lucide-react";
import { ControlPlaneError, getTemplate, type TemplateDetail } from "@/lib/control-plane";
import { revealStyle } from "@/lib/motion";
import { getCurrentUser } from "@/lib/session";
import AppShell from "@/components/app-shell";
import TemplateUseButton from "@/components/template-use-button";
import { APP_KIND_META, categoryMeta, templateAssetUrl } from "@/components/template-meta";
import { Badge } from "@/components/ui/badge";

export const dynamic = "force-dynamic";

async function load(slug: string): Promise<TemplateDetail> {
  try {
    return await getTemplate(slug);
  } catch (error) {
    if (error instanceof ControlPlaneError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  try {
    const template = await getTemplate(slug);
    return { title: `${template.name} template`, description: template.tagline };
  } catch {
    return { title: "Template" };
  }
}

export default async function TemplatePage({ params }: { params: Promise<{ slug: string }> }) {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  const { slug } = await params;
  const template = await load(slug);
  const category = categoryMeta(template.category);
  const CategoryIcon = category.icon;

  return (
    <AppShell user={user}>
      <Link
        href="/templates"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
      >
        <ArrowLeft className="size-3.5" aria-hidden="true" />
        All templates
      </Link>

      <header className="reveal mt-4 grid gap-6 lg:grid-cols-12" style={revealStyle(0)}>
        <div className="lg:col-span-7">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="gap-1">
              <CategoryIcon aria-hidden="true" />
              {category.label}
            </Badge>
            <span className="text-xs tabular-nums text-muted-foreground">
              v{template.version} · {template.file_count} files
            </span>
          </div>
          <h1 className="mt-2 text-balance text-4xl font-semibold tracking-tight">{template.name}</h1>
          <p className="mt-2 max-w-xl text-pretty text-lg text-muted-foreground">{template.tagline}</p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <TemplateUseButton slug={template.slug} templateName={template.name} />
            <p className="text-xs text-muted-foreground">Your own copy. The original never changes.</p>
          </div>
        </div>
        <div className="overflow-hidden rounded-xl border border-border/60 bg-muted lg:col-span-5">
          {template.cover ? (
            // eslint-disable-next-line @next/next/no-img-element -- relayed as-is
            <img src={templateAssetUrl(template.slug, template.cover)} alt={`${template.name} preview`} className="aspect-[16/10] size-full object-cover" />
          ) : (
            <div className="grid aspect-[16/10] place-items-center bg-gradient-to-br from-muted to-secondary">
              <CategoryIcon className="size-14 text-muted-foreground/60" aria-hidden="true" />
            </div>
          )}
        </div>
      </header>

      <div className="mt-10 grid gap-10 lg:grid-cols-12">
        <div className="grid content-start gap-10 lg:col-span-8">
          <Section title="About" index={1}>
            <p className="max-w-prose whitespace-pre-line text-pretty text-sm leading-relaxed text-muted-foreground">
              {template.description}
            </p>
          </Section>

          <Section title={`${template.apps.length} apps, one backend`} index={2}>
            <ul className="grid gap-3 sm:grid-cols-2">
              {template.apps.map((app) => {
                const meta = APP_KIND_META[app.kind];
                const Icon = meta.icon;
                return (
                  <li key={app.id} className="flex items-start gap-3 rounded-xl border border-border/60 bg-card p-4">
                    <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-secondary">
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium">{app.name}</p>
                      <p className="text-sm text-muted-foreground">{meta.label} · {meta.blurb}</p>
                      <p className="mt-1 truncate font-mono text-xs text-muted-foreground/80">{app.path}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Section>

          <Section title={`${template.features.length} features`} index={3}>
            <ul className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
              {template.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2 text-sm">
                  <Check className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden="true" />
                  {feature}
                </li>
              ))}
            </ul>
          </Section>

          {template.screenshots && template.screenshots.length > 0 ? (
            <Section title="Screens" index={4}>
              <ul className="grid gap-3 sm:grid-cols-2">
                {template.screenshots.map((shot, index) => (
                  <li key={shot} className="overflow-hidden rounded-xl border border-border/60 bg-muted">
                    {/* eslint-disable-next-line @next/next/no-img-element -- relayed as-is */}
                    <img src={templateAssetUrl(template.slug, shot)} alt={`${template.name} screen ${index + 1}`} className="w-full" loading="lazy" />
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}
        </div>

        <aside className="grid content-start gap-8 lg:col-span-4">
          <Section title="Who uses it" icon={Users} index={2}>
            <ul className="grid gap-2">
              {template.roles.map((role) => (
                <li key={role.id} className="rounded-lg bg-muted/50 px-3 py-2">
                  <p className="text-sm font-medium">{role.name}</p>
                  <p className="text-xs text-muted-foreground">{role.description}</p>
                </li>
              ))}
            </ul>
          </Section>

          {template.demo_users.length > 0 ? (
            <Section title="Demo logins" icon={KeyRound} index={3}>
              <p className="-mt-1 mb-2 text-xs text-muted-foreground">For trying the preview locally.</p>
              <ul className="grid gap-1.5">
                {template.demo_users.map((user) => (
                  <li key={user.email} className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate font-mono text-xs">{user.email}</span>
                    <Badge variant="outline" className="shrink-0 capitalize">{user.role}</Badge>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          <Section title="Data" icon={Database} index={4}>
            <ul className="flex flex-wrap gap-1.5">
              {template.entities.map((entity) => (
                <li key={entity}>
                  <Badge variant="outline" className="font-mono font-normal">{entity}</Badge>
                </li>
              ))}
            </ul>
          </Section>

          {template.integrations && template.integrations.length > 0 ? (
            <Section title="Integrations" icon={Plug} index={5}>
              <ul className="grid gap-1.5">
                {template.integrations.map((integration) => (
                  <li key={integration.id} className="flex items-center justify-between gap-2 text-sm">
                    <span className="capitalize">
                      {integration.kind} <span className="text-muted-foreground">· {integration.provider}</span>
                    </span>
                    {integration.mock ? (
                      <Badge variant="secondary" className="font-normal">Works without keys</Badge>
                    ) : null}
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          <Section title="Built with" index={6}>
            <ul className="flex flex-wrap gap-1.5">
              {template.stack.map((item) => (
                <li key={item}>
                  <Badge variant="secondary" className="font-normal">{item}</Badge>
                </li>
              ))}
            </ul>
          </Section>
        </aside>
      </div>
    </AppShell>
  );
}

function Section({
  title,
  icon: Icon,
  index,
  children,
}: {
  title: string;
  icon?: React.ComponentType<{ className?: string }>;
  index: number;
  children: React.ReactNode;
}) {
  return (
    <section className="reveal" style={revealStyle(index)}>
      <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold tracking-tight">
        {Icon ? <Icon className="size-4 text-muted-foreground" /> : null}
        {title}
      </h2>
      {children}
    </section>
  );
}
