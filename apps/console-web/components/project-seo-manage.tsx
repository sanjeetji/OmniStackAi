"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Bot,
  Check,
  CheckCircle2,
  ExternalLink,
  Eye,
  FileCode2,
  Globe,
  Info,
  LoaderCircle,
  RefreshCw,
  Search,
  Share2,
  Sparkles,
} from "lucide-react";
import type {
  ProjectPageSEO,
  ProjectSEO,
  SEOAuditReport,
  SEOFinding,
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

interface ProjectSEOManageProps {
  projectId: string;
  projectName?: string;
}

export function ProjectSEOManage({ projectId, projectName = "" }: ProjectSEOManageProps) {
  // Site defaults state
  const [siteSEO, setSiteSEO] = useState<ProjectSEO | null>(null);
  const [loadingSite, setLoadingSite] = useState(true);
  const [savingSite, setSavingSite] = useState(false);
  const [siteSavedSuccess, setSiteSavedSuccess] = useState(false);
  const [siteError, setSiteError] = useState<string | null>(null);

  // Form inputs for site defaults
  const [siteName, setSiteName] = useState("");
  const [defaultTitle, setDefaultTitle] = useState("");
  const [siteDescription, setSiteDescription] = useState("");
  const [canonicalHost, setCanonicalHost] = useState("");
  const [discourage, setDiscourage] = useState(false);

  // Pages state
  const [pages, setPages] = useState<ProjectPageSEO[]>([]);
  const [loadingPages, setLoadingPages] = useState(true);
  const [pagesError, setPagesError] = useState<string | null>(null);

  // Edit page dialog
  const [editingPage, setEditingPage] = useState<ProjectPageSEO | null>(null);
  const [pageTitle, setPageTitle] = useState("");
  const [pageDescription, setPageDescription] = useState("");
  const [pageNoindex, setPageNoindex] = useState(false);
  const [savingPage, setSavingPage] = useState(false);
  const [pageSavedSuccess, setPageSavedSuccess] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);

  // AI suggest state
  const [suggestingCopy, setSuggestingCopy] = useState(false);
  const [suggestConfirmOpen, setSuggestConfirmOpen] = useState(false);
  const [suggestNotice, setSuggestNotice] = useState<string | null>(null);

  // Preview simulator state
  const [previewRoute, setPreviewRoute] = useState<string>("/");
  const [previewTab, setPreviewTab] = useState<"google" | "social">("google");

  // Audit state
  const [auditReport, setAuditReport] = useState<SEOAuditReport | null>(null);
  const [auditing, setAuditing] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);

  // Fetch site-level SEO defaults
  const fetchSiteSEO = async () => {
    setLoadingSite(true);
    setSiteError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/seo`);
      if (!resp.ok) throw new Error("Failed to load site SEO defaults");
      const data: ProjectSEO = await resp.json();
      setSiteSEO(data);
      setSiteName(data.site_name || projectName);
      setDefaultTitle(data.default_title || projectName);
      setSiteDescription(data.description || "");
      setCanonicalHost(data.canonical_host || "");
      setDiscourage(data.discourage || false);
    } catch (err: unknown) {
      setSiteError(err instanceof Error ? err.message : "Failed to load site SEO");
    } finally {
      setLoadingSite(false);
    }
  };

  // Fetch pages
  const fetchPages = async () => {
    setLoadingPages(true);
    setPagesError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/seo/pages`);
      if (!resp.ok) throw new Error("Failed to load project pages");
      const data = await resp.json();
      setPages(data.pages ?? []);
    } catch (err: unknown) {
      setPagesError(err instanceof Error ? err.message : "Failed to load pages");
    } finally {
      setLoadingPages(false);
    }
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [siteResp, pagesResp] = await Promise.all([
          fetch(`/api/projects/${encodeURIComponent(projectId)}/seo`),
          fetch(`/api/projects/${encodeURIComponent(projectId)}/seo/pages`),
        ]);
        if (!active) return;
        if (siteResp.ok) {
          const data: ProjectSEO = await siteResp.json();
          setSiteSEO(data);
          setSiteName(data.site_name || projectName);
          setDefaultTitle(data.default_title || projectName);
          setSiteDescription(data.description || "");
          setCanonicalHost(data.canonical_host || "");
          setDiscourage(data.discourage || false);
        }
        if (pagesResp.ok) {
          const data = await pagesResp.json();
          setPages(data.pages ?? []);
        }
      } catch (err: unknown) {
        if (active) {
          setSiteError(err instanceof Error ? err.message : "Failed to load site SEO");
        }
      } finally {
        if (active) {
          setLoadingSite(false);
          setLoadingPages(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId, projectName]);

  // Handle saving site defaults
  const handleSaveSiteSEO = async (e: FormEvent) => {
    e.preventDefault();
    setSavingSite(true);
    setSiteSavedSuccess(false);
    setSiteError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/seo`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site_name: siteName.trim(),
          default_title: defaultTitle.trim(),
          description: siteDescription.trim(),
          canonical_host: canonicalHost.trim(),
          discourage,
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to update site SEO defaults");
      }
      const data: ProjectSEO = await resp.json();
      setSiteSEO(data);
      setSiteSavedSuccess(true);
      setTimeout(() => setSiteSavedSuccess(false), 3000);
    } catch (err: unknown) {
      setSiteError(err instanceof Error ? err.message : "Failed to save site SEO");
    } finally {
      setSavingSite(false);
    }
  };

  // Open edit dialog for a page
  const handleOpenEditPage = (page: ProjectPageSEO) => {
    setEditingPage(page);
    setPageTitle(page.title);
    setPageDescription(page.description);
    setPageNoindex(page.noindex);
    setPageError(null);
    setPageSavedSuccess(false);
  };

  // Save page metadata
  const handleSavePage = async (e: FormEvent) => {
    e.preventDefault();
    if (!editingPage) return;
    setSavingPage(true);
    setPageError(null);
    try {
      const rawRoute = editingPage.route.replace(/^\/+/, "");
      const targetUrl = `/api/projects/${encodeURIComponent(projectId)}/seo/pages/${rawRoute || "root"}`;
      const resp = await fetch(targetUrl, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          route: editingPage.route,
          title: pageTitle.trim(),
          description: pageDescription.trim(),
          noindex: pageNoindex,
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to update page SEO");
      }
      setPageSavedSuccess(true);
      await fetchPages();
      setTimeout(() => {
        setEditingPage(null);
        setPageSavedSuccess(false);
      }, 1000);
    } catch (err: unknown) {
      setPageError(err instanceof Error ? err.message : "Failed to save page SEO");
    } finally {
      setSavingPage(false);
    }
  };

  // Request AI copy suggestion
  const handleSuggestCopy = async () => {
    if (!editingPage) return;
    setSuggestConfirmOpen(false);
    setSuggestingCopy(true);
    setSuggestNotice(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/seo/suggest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          route: editingPage.route,
          page_name: pageTitle || undefined,
        }),
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to generate SEO copy suggestion");
      }
      const data = await resp.json();
      if (data.suggested_title) setPageTitle(data.suggested_title);
      if (data.suggested_description) setPageDescription(data.suggested_description);
      setSuggestNotice("AI suggestion applied! Review and save when ready.");
    } catch (err: unknown) {
      setPageError(err instanceof Error ? err.message : "Suggestion failed");
    } finally {
      setSuggestingCopy(false);
    }
  };

  // Run SEO audit
  const handleRunAudit = async () => {
    setAuditing(true);
    setAuditError(null);
    try {
      const resp = await fetch(`/api/projects/${encodeURIComponent(projectId)}/seo/audit`, {
        method: "POST",
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.error || "Failed to execute SEO audit");
      }
      const data: SEOAuditReport = await resp.json();
      setAuditReport(data);
    } catch (err: unknown) {
      setAuditError(err instanceof Error ? err.message : "Audit failed");
    } finally {
      setAuditing(false);
    }
  };

  // Current page selected for preview
  const activePreviewPage = pages.find((p) => p.route === previewRoute) || {
    route: previewRoute,
    title: defaultTitle || siteName,
    description: siteDescription || "Modern web application powered by OmniStackAI.",
    noindex: false,
    project_id: projectId,
  };

  const previewDisplayTitle = activePreviewPage.title || defaultTitle || siteName;
  const previewDisplayDesc = activePreviewPage.description || siteDescription || "Explore fast, reliable, and modern features.";
  const previewDomain = canonicalHost ? canonicalHost.replace(/^https?:\/\//, "") : "your-domain.com";
  const previewFullUrl = canonicalHost
    ? `${canonicalHost.replace(/\/+$/, "")}${activePreviewPage.route === "/" ? "" : activePreviewPage.route}`
    : `https://${previewDomain}${activePreviewPage.route === "/" ? "" : activePreviewPage.route}`;

  return (
    <div className="space-y-6">
      {/* Site Defaults Section */}
      <Card>
        <form onSubmit={handleSaveSiteSEO}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Globe className="size-4 text-brand" />
                  Site-Level SEO & AI Defaults
                </CardTitle>
                <CardDescription>
                  Search engines and AI crawlers read these to understand your application&apos;s identity and indexing policy.
                </CardDescription>
              </div>
              <Badge variant="outline" className="text-xs">
                Next.js App Router
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {siteError && (
              <div
                role="alert"
                className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                {siteError}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="seo-site-name">Site Name</Label>
                <Input
                  id="seo-site-name"
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  placeholder="e.g. Acme Corp"
                  disabled={loadingSite || savingSite}
                />
                <p className="text-xs text-muted-foreground">Used in JSON-LD structured data and OpenGraph tags.</p>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="seo-default-title">Default Title</Label>
                <Input
                  id="seo-default-title"
                  value={defaultTitle}
                  onChange={(e) => setDefaultTitle(e.target.value)}
                  placeholder="e.g. Acme — High Performance Task Management"
                  disabled={loadingSite || savingSite}
                />
                <p className="text-xs text-muted-foreground">Fallback title for pages without explicit overrides.</p>
              </div>
            </div>

            <div className="grid gap-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="seo-site-desc">Default Meta Description</Label>
                <span
                  className={cn(
                    "text-xs tabular-nums",
                    siteDescription.length > 0 && siteDescription.length < 50
                      ? "text-amber-500"
                      : siteDescription.length > 160
                      ? "text-amber-500"
                      : "text-muted-foreground"
                  )}
                >
                  {siteDescription.length} / 160 chars (recommended: 50–160)
                </span>
              </div>
              <Input
                id="seo-site-desc"
                value={siteDescription}
                onChange={(e) => setSiteDescription(e.target.value)}
                placeholder="Clear, concise summary of what this application does for users."
                disabled={loadingSite || savingSite}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t">
              <div className="grid gap-2">
                <Label htmlFor="seo-canonical-host">Canonical Host</Label>
                <Input
                  id="seo-canonical-host"
                  value={canonicalHost}
                  onChange={(e) => setCanonicalHost(e.target.value)}
                  placeholder="https://example.com"
                  disabled={loadingSite || savingSite}
                />
                <p className="text-xs text-muted-foreground">Base URL for sitemap.ts, robots.ts, and canonical links.</p>
              </div>

              <div className="flex flex-col justify-between p-3 rounded-lg border bg-muted/20">
                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="seo-discourage" className="font-medium cursor-pointer">
                      Discourage Search Engines
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Sets <code className="font-mono text-[11px]">disallow: /</code> in robots.txt for staging.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    id="seo-discourage"
                    checked={discourage}
                    onChange={(e) => setDiscourage(e.target.checked)}
                    disabled={loadingSite || savingSite}
                    className="size-4 rounded border-gray-300 text-brand focus:ring-brand cursor-pointer"
                  />
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex items-center justify-between border-t px-6 py-3">
            {siteSavedSuccess ? (
              <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                <Check className="size-3.5" />
                Site SEO defaults saved successfully
              </span>
            ) : (
              <span />
            )}
            <Button type="submit" size="sm" disabled={savingSite || loadingSite}>
              {savingSite ? (
                <>
                  <LoaderCircle className="size-3.5 animate-spin mr-1.5" />
                  Saving...
                </>
              ) : (
                "Save site defaults"
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>

      {/* Pages Table Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileCode2 className="size-4 text-brand" />
                Per-Page Metadata &amp; Indexability
              </CardTitle>
              <CardDescription>
                Customize individual page titles and descriptions. Edits generate clean metadata commits in your project repository.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchPages}
              disabled={loadingPages}
              className="gap-1.5"
            >
              <RefreshCw className={cn("size-3.5", loadingPages && "animate-spin")} />
              Refresh pages
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {pagesError && (
            <div
              role="alert"
              className="mb-4 flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              {pagesError}
            </div>
          )}

          {loadingPages ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <LoaderCircle className="size-5 animate-spin mr-2" />
              Discovering routes...
            </div>
          ) : pages.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/80 p-8 text-center">
              <Globe className="mx-auto size-8 text-muted-foreground/60" />
              <h3 className="mt-2 text-sm font-semibold">No custom page metadata yet</h3>
              <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
                Pages use site defaults until customized. Build or edit your application in Studio to discover routes.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-xs font-medium text-muted-foreground">
                    <th className="pb-3 pr-4">Route</th>
                    <th className="pb-3 pr-4">Title</th>
                    <th className="pb-3 pr-4">Description</th>
                    <th className="pb-3 pr-4">Indexable</th>
                    <th className="pb-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {pages.map((p) => {
                    const descLen = p.description?.length || 0;
                    const descStatus =
                      descLen === 0
                        ? "missing"
                        : descLen < 50 || descLen > 160
                        ? "warning"
                        : "optimal";

                    return (
                      <tr key={p.route} className="hover:bg-muted/30 transition-colors">
                        <td className="py-3 pr-4 font-mono text-xs font-semibold text-foreground">
                          {p.route}
                        </td>
                        <td className="py-3 pr-4 max-w-[200px] truncate text-xs text-foreground">
                          {p.title || <span className="text-muted-foreground italic">Default title</span>}
                        </td>
                        <td className="py-3 pr-4 max-w-[280px]">
                          <div className="truncate text-xs text-muted-foreground">
                            {p.description || <span className="italic">Default description</span>}
                          </div>
                          {descLen > 0 && (
                            <div className="mt-1 flex items-center gap-1 text-[10px] text-muted-foreground">
                              <div
                                className={cn(
                                  "h-1.5 rounded-full",
                                  descStatus === "optimal"
                                    ? "w-8 bg-green-500"
                                    : "w-5 bg-amber-500"
                                )}
                              />
                              <span>{descLen} chars</span>
                            </div>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          {p.noindex ? (
                            <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-600 dark:text-amber-400">
                              noindex
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-[10px] border-green-500/30 text-green-600 dark:text-green-400">
                              Indexed
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleOpenEditPage(p)}
                            className="h-7 text-xs"
                          >
                            Edit
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Preview Card: Google & Social Card Simulators */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Eye className="size-4 text-brand" />
                Live Search &amp; Social Preview
              </CardTitle>
              <CardDescription>
                Simulate how search engines and social media platforms display your pages.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-md border bg-muted/40 p-0.5 text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setPreviewTab("google")}
                  className={cn(
                    "flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors",
                    previewTab === "google" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Search className="size-3" />
                  Google
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewTab("social")}
                  className={cn(
                    "flex items-center gap-1.5 px-2.5 py-1 rounded transition-colors",
                    previewTab === "social" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Share2 className="size-3" />
                  Social
                </button>
              </div>

              {pages.length > 0 && (
                <select
                  value={previewRoute}
                  onChange={(e) => setPreviewRoute(e.target.value)}
                  className="h-8 rounded-md border border-input bg-transparent px-2 text-xs font-mono focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  {pages.map((p) => (
                    <option key={p.route} value={p.route}>
                      {p.route}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {previewTab === "google" ? (
            /* Google Search Snippet Preview */
            <div className="rounded-xl border bg-card p-4 max-w-xl font-sans shadow-sm">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <div className="size-4 rounded-full bg-muted flex items-center justify-center text-[9px] font-bold">
                  {siteName.charAt(0) || "O"}
                </div>
                <span className="text-[#202124] dark:text-[#bdc1c6] font-medium">{siteName}</span>
                <span>•</span>
                <span className="truncate text-muted-foreground">{previewFullUrl}</span>
              </div>
              <h4 className="text-lg font-normal text-[#1a0dab] dark:text-[#8ab4f8] hover:underline cursor-pointer leading-snug">
                {previewDisplayTitle}
              </h4>
              <p className="mt-1 text-xs text-[#4d5156] dark:text-[#bdc1c6] leading-relaxed line-clamp-2">
                {previewDisplayDesc}
              </p>
            </div>
          ) : (
            /* Social Card Preview (OpenGraph / Twitter) */
            <div className="rounded-xl border bg-card overflow-hidden max-w-md shadow-sm">
              <div className="h-44 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 p-6 flex flex-col justify-end text-white relative">
                <div className="absolute top-4 right-4">
                  <Badge variant="secondary" className="bg-white/10 text-white border-white/20 text-[10px]">
                    next/og 1200×630
                  </Badge>
                </div>
                <div className="text-lg font-bold tracking-tight text-white mb-1 line-clamp-1">
                  {previewDisplayTitle}
                </div>
                <div className="text-xs text-slate-300 line-clamp-2">
                  {previewDisplayDesc}
                </div>
              </div>
              <div className="p-3 bg-muted/20 border-t flex items-center justify-between text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{previewDomain}</span>
                <span className="text-[11px] font-mono">{activePreviewPage.route}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SEO & AI Search Audit Section */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bot className="size-4 text-brand" />
                SEO &amp; AI Search Audit
              </CardTitle>
              <CardDescription>
                Deterministic checker over generated source (sitemap, robots, llms.txt, headings, metadata, alt tags).
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-[11px] font-medium bg-green-500/10 text-green-700 dark:text-green-300 border-green-500/20">
                0 credits · Free
              </Badge>
              <Button
                size="sm"
                onClick={handleRunAudit}
                disabled={auditing}
                className="gap-1.5"
              >
                {auditing ? (
                  <>
                    <LoaderCircle className="size-3.5 animate-spin mr-1" />
                    Auditing source...
                  </>
                ) : (
                  <>
                    <Sparkles className="size-3.5 mr-1" />
                    Run SEO Audit
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {auditError && (
            <div
              role="alert"
              className="mb-4 flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              {auditError}
            </div>
          )}

          {!auditReport && !auditing && (
            <div className="rounded-xl border border-dashed border-border/80 p-8 text-center">
              <Bot className="mx-auto size-8 text-muted-foreground/60" />
              <h3 className="mt-2 text-sm font-semibold">No audit findings yet</h3>
              <p className="mt-1 text-xs text-muted-foreground max-w-sm mx-auto">
                Click &quot;Run SEO Audit&quot; to inspect your Next.js application for search engine indexability and AI search readiness.
              </p>
            </div>
          )}

          {auditReport && (
            <div className="space-y-6">
              {/* Score banner */}
              <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-xl border bg-muted/20 gap-4">
                <div className="flex items-center gap-4">
                  <div
                    className={cn(
                      "size-14 rounded-full flex items-center justify-center font-bold text-lg border-2",
                      auditReport.score >= 80
                        ? "border-green-500 text-green-600 bg-green-500/10"
                        : auditReport.score >= 50
                        ? "border-amber-500 text-amber-600 bg-amber-500/10"
                        : "border-destructive text-destructive bg-destructive/10"
                    )}
                  >
                    {auditReport.score}
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold">
                      {auditReport.score >= 80
                        ? "Excellent Search & AI Readiness"
                        : auditReport.score >= 50
                        ? "Good, but improvements recommended"
                        : "Requires attention before publishing"}
                    </h4>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {auditReport.passed ?? 0} of {auditReport.total ?? 0} automated checks passed cleanly.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1 font-medium text-destructive">
                    <AlertCircle className="size-3.5" />
                    {auditReport.findings.filter((f) => f.severity === "error").length} errors
                  </span>
                  <span className="flex items-center gap-1 font-medium text-amber-600 dark:text-amber-400">
                    <AlertTriangle className="size-3.5" />
                    {auditReport.findings.filter((f) => f.severity === "warning").length} warnings
                  </span>
                  <span className="flex items-center gap-1 font-medium text-blue-600 dark:text-blue-400">
                    <Info className="size-3.5" />
                    {auditReport.findings.filter((f) => f.severity === "info").length} notices
                  </span>
                </div>
              </div>

              {/* Findings list */}
              {auditReport.findings.length === 0 ? (
                <div className="flex items-center gap-3 p-4 rounded-xl border border-green-500/30 bg-green-500/10 text-green-700 dark:text-green-300 text-sm">
                  <CheckCircle2 className="size-5 shrink-0" />
                  <div>
                    <div className="font-semibold">All SEO &amp; AI search checks passed!</div>
                    <div className="text-xs opacity-90">
                      Your app includes valid sitemap.ts, robots.ts, llms.txt, OpenGraph image, structured data, and per-page metadata.
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Findings ({auditReport.findings.length})
                  </h4>
                  <div className="divide-y rounded-xl border overflow-hidden">
                    {auditReport.findings.map((f, idx) => (
                      <div key={`${f.id}-${idx}`} className="p-4 bg-card hover:bg-muted/10 transition-colors">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-2.5">
                            {f.severity === "error" ? (
                              <AlertCircle className="size-4 text-destructive shrink-0 mt-0.5" />
                            ) : f.severity === "warning" ? (
                              <AlertTriangle className="size-4 text-amber-500 shrink-0 mt-0.5" />
                            ) : (
                              <Info className="size-4 text-blue-500 shrink-0 mt-0.5" />
                            )}
                            <div>
                              <div className="text-xs font-semibold text-foreground flex items-center gap-2">
                                {f.message}
                                {f.route && (
                                  <Badge variant="outline" className="font-mono text-[10px] px-1 py-0 h-4">
                                    {f.route}
                                  </Badge>
                                )}
                              </div>
                              {f.suggestion && (
                                <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                  {f.suggestion}
                                </p>
                              )}
                              <div className="mt-1.5 flex items-center gap-2 text-[11px] font-mono text-muted-foreground/80">
                                <span>{f.file}</span>
                                {f.line ? <span>• Line {f.line}</span> : null}
                              </div>
                            </div>
                          </div>

                          {f.route && pages.some((p) => p.route === f.route) && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                const matched = pages.find((p) => p.route === f.route);
                                if (matched) handleOpenEditPage(matched);
                              }}
                              className="h-7 text-xs shrink-0"
                            >
                              Edit SEO
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Page SEO Dialog */}
      <Dialog open={editingPage !== null} onOpenChange={(open) => !open && setEditingPage(null)}>
        <DialogContent className="max-w-lg">
          <form onSubmit={handleSavePage}>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Globe className="size-4 text-brand" />
                Edit Page SEO: <span className="font-mono">{editingPage?.route}</span>
              </DialogTitle>
              <DialogDescription>
                Updates will be written into this page&apos;s Next.js layout metadata and committed to git.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {pageError && (
                <div
                  role="alert"
                  className="flex gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                >
                  <AlertCircle className="mt-0.5 size-4 shrink-0" />
                  {pageError}
                </div>
              )}

              {suggestNotice && (
                <div className="flex gap-2 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-xs text-green-700 dark:text-green-300">
                  <Check className="mt-0.5 size-3.5 shrink-0" />
                  {suggestNotice}
                </div>
              )}

              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="page-edit-title">Page Title</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setSuggestConfirmOpen(true)}
                    disabled={suggestingCopy}
                    className="h-6 px-2 text-[11px] text-brand hover:text-brand gap-1"
                  >
                    {suggestingCopy ? (
                      <LoaderCircle className="size-3 animate-spin" />
                    ) : (
                      <Sparkles className="size-3" />
                    )}
                    Suggest copy
                  </Button>
                </div>
                <Input
                  id="page-edit-title"
                  value={pageTitle}
                  onChange={(e) => setPageTitle(e.target.value)}
                  placeholder="Descriptive title under 60 characters"
                  required
                />
              </div>

              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="page-edit-desc">Meta Description</Label>
                  <span
                    className={cn(
                      "text-xs tabular-nums",
                      pageDescription.length < 50 || pageDescription.length > 160
                        ? "text-amber-500"
                        : "text-muted-foreground"
                    )}
                  >
                    {pageDescription.length} / 160 chars (recommended: 50–160)
                  </span>
                </div>
                <textarea
                  id="page-edit-desc"
                  value={pageDescription}
                  onChange={(e) => setPageDescription(e.target.value)}
                  placeholder="Provide an informative and relevant snippet describing this specific screen."
                  rows={3}
                  className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg border bg-muted/20">
                <div>
                  <Label htmlFor="page-edit-noindex" className="font-medium cursor-pointer">
                    Noindex this page
                  </Label>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Instructs search engines not to display this route in search results.
                  </p>
                </div>
                <input
                  type="checkbox"
                  id="page-edit-noindex"
                  checked={pageNoindex}
                  onChange={(e) => setPageNoindex(e.target.checked)}
                  className="size-4 rounded border-gray-300 text-brand focus:ring-brand cursor-pointer"
                />
              </div>
            </div>

            <DialogFooter className="flex items-center justify-between border-t pt-4">
              {pageSavedSuccess ? (
                <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                  <Check className="size-3.5" />
                  Saved &amp; committed to repository!
                </span>
              ) : (
                <div />
              )}
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setEditingPage(null)}
                >
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={savingPage || !pageTitle.trim()}>
                  {savingPage ? (
                    <>
                      <LoaderCircle className="size-3.5 animate-spin mr-1.5" />
                      Saving...
                    </>
                  ) : (
                    "Save & Commit"
                  )}
                </Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Credit Confirmation for AI Suggestion */}
      <Dialog open={suggestConfirmOpen} onOpenChange={setSuggestConfirmOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-brand" />
              Generate SEO Copy Suggestion
            </DialogTitle>
            <DialogDescription>
              Use an AI model to draft an optimized page title and meta description for{" "}
              <span className="font-mono font-semibold">{editingPage?.route}</span>.
            </DialogDescription>
          </DialogHeader>

          <div className="py-3 text-xs text-muted-foreground space-y-2">
            <div className="flex items-start gap-2 p-3 rounded-lg border bg-muted/20">
              <Info className="size-4 text-brand mt-0.5 shrink-0" />
              <div>
                <span className="font-medium text-foreground">Credit Cost Notice:</span>
                <p className="mt-0.5">
                  This pass calls the configured model and will debit approximately <strong>1 credit</strong> from your balance.
                  (0 credits if Bring-Your-Own-Key or local Ollama is active).
                </p>
              </div>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setSuggestConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleSuggestCopy}
              className="gap-1.5"
            >
              <Sparkles className="size-3.5" />
              Proceed with suggestion
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
