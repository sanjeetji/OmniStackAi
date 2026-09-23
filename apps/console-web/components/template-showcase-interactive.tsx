"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  ExternalLink,
  Globe,
  KeyRound,
  LayoutDashboard,
  Maximize2,
  QrCode as QrIcon,
  Server,
  Smartphone,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import type { TemplateApp, TemplateDetail, TemplateScreen } from "@/lib/control-plane";
import { templateAssetUrl } from "@/components/template-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { QrCode } from "@/components/qr-code";
import { cn } from "@/lib/utils";

const KIND_ICON: Record<string, LucideIcon> = {
  web: Globe,
  admin: LayoutDashboard,
  pwa: Smartphone,
  api: Server,
};

interface TemplateShowcaseInteractiveProps {
  template: TemplateDetail;
}

export function TemplateShowcaseInteractive({ template }: TemplateShowcaseInteractiveProps) {
  const uiApps = useMemo(() => template.apps.filter((a) => a.kind !== "api"), [template.apps]);
  const apiApp = useMemo(() => template.apps.find((a) => a.kind === "api"), [template.apps]);

  // Selected app in the interactive preview frame
  const [selectedAppId, setSelectedAppId] = useState<string>(() => uiApps[0]?.id || "admin");
  const selectedApp = useMemo(
    () => template.apps.find((a) => a.id === selectedAppId) || uiApps[0],
    [template.apps, selectedAppId, uiApps]
  );

  // Group screens by app
  const allScreens: TemplateScreen[] = useMemo(() => {
    if (template.screens && template.screens.length > 0) {
      return template.screens;
    }
    // Fallback if screens array not present
    return (template.screenshots || []).map((img, i) => {
      const parts = img.split("/");
      const appKey = parts[1] || "app";
      const name = parts[parts.length - 1].replace(/\.[^/.]+$/, "").replace(/-/g, " ");
      return {
        app: appKey,
        title: name.charAt(0).toUpperCase() + name.slice(1),
        description: `Screen ${i + 1} of ${template.name}`,
        route: `/${name}`,
        device: appKey === "admin" ? "desktop" : "mobile",
        highlight: i < 5,
        image: img,
      };
    });
  }, [template]);

  // Screens for the currently selected app
  const currentAppScreens = useMemo(() => {
    return allScreens.filter((s) => s.app === selectedApp?.id);
  }, [allScreens, selectedApp]);

  // Active scene inside the app frame
  const [activeScreenIndex, setActiveScreenIndex] = useState(0);

  // Switch app handler
  const handleSelectApp = (appId: string) => {
    setSelectedAppId(appId);
    setActiveScreenIndex(0);
  };

  const activeScreen = currentAppScreens[activeScreenIndex] || currentAppScreens[0];

  // Gallery filter
  const [galleryFilter, setGalleryFilter] = useState<string>("all");
  const filteredGalleryScreens = useMemo(() => {
    if (galleryFilter === "all") return allScreens;
    if (galleryFilter === "highlights") return allScreens.filter((s) => s.highlight);
    return allScreens.filter((s) => s.app === galleryFilter);
  }, [allScreens, galleryFilter]);

  // Lightbox modal state
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const openLightbox = (screen: TemplateScreen) => {
    const idx = allScreens.findIndex((s) => s.image === screen.image);
    if (idx !== -1) setLightboxIndex(idx);
  };

  const closeLightbox = () => setLightboxIndex(null);

  const prevLightbox = useCallback(() => {
    setLightboxIndex((prev) => (prev !== null ? (prev - 1 + allScreens.length) % allScreens.length : null));
  }, [allScreens.length]);

  const nextLightbox = useCallback(() => {
    setLightboxIndex((prev) => (prev !== null ? (prev + 1) % allScreens.length : null));
  }, [allScreens.length]);

  // Keyboard navigation for lightbox
  useEffect(() => {
    if (lightboxIndex === null) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") prevLightbox();
      else if (e.key === "ArrowRight") nextLightbox();
      else if (e.key === "Escape") closeLightbox();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [lightboxIndex, prevLightbox, nextLightbox]);

  // QR Code companion modal
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [copiedRole, setCopiedRole] = useState<string | null>(null);

  const copyCreds = (user: { role: string; name?: string; email: string; password: string }) => {
    const text = `Email: ${user.email}\nPassword: ${user.password}`;
    navigator.clipboard.writeText(text);
    setCopiedRole(user.role);
    toast.success(`Copied login for ${user.name || user.role} (${user.role})`);
    setTimeout(() => setCopiedRole(null), 2000);
  };

  const isPhone = selectedApp?.kind === "pwa" || activeScreen?.device === "mobile";

  // URL for QR code
  const currentHost = typeof window !== "undefined" ? window.location.origin : "https://omnistack.ai";
  const mobileDemoUrl = `${currentHost}/templates/${template.slug}?app=${selectedApp?.id || "driver"}`;

  return (
    <div className="grid gap-12">
      {/* ------------------------------------------------------------- */}
      {/* 1. INTERACTIVE LIVE APPS HUB                                  */}
      {/* ------------------------------------------------------------- */}
      <section id="interactive-hub" className="scroll-mt-20">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Sparkles className="size-5 text-brand" aria-hidden="true" />
              Interactive Experience Hub
            </h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Explore every app in real time. Switch roles, navigate scenes, and test the full city flow.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {(selectedApp?.kind === "pwa" || selectedApp?.kind === "web") && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setQrModalOpen(true)}
                className="gap-1.5 shadow-sm"
              >
                <QrIcon className="size-3.5" aria-hidden="true" />
                <span>Test on Phone (QR)</span>
              </Button>
            )}
          </div>
        </div>

        {/* Demo Users Quick Login Bar */}
        {template.demo_users && template.demo_users.length > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-border/60 bg-muted/40 p-3">
            <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <KeyRound className="size-3.5" aria-hidden="true" />
              1-Click Demo Logins:
            </span>
            <div className="flex flex-wrap items-center gap-2">
              {template.demo_users.map((u) => {
                const isCopied = copiedRole === u.role;
                return (
                  <button
                    key={u.email}
                    type="button"
                    onClick={() => copyCreds(u)}
                    className={cn(
                      "group inline-flex items-center gap-2 rounded-lg border border-border/70 bg-card px-2.5 py-1 text-xs transition-all hover:border-foreground/30 hover:shadow-xs",
                      isCopied && "border-brand/50 bg-brand/10 text-brand"
                    )}
                    title={`Click to copy login for ${u.name}`}
                  >
                    <span className="font-medium text-foreground">{u.name}</span>
                    <Badge variant="secondary" className="px-1.5 py-0 text-[10px] capitalize">
                      {u.role}
                    </Badge>
                    <span className="font-mono text-muted-foreground group-hover:text-foreground">
                      {u.email}
                    </span>
                    {isCopied ? (
                      <Check className="size-3 text-brand" aria-hidden="true" />
                    ) : (
                      <Copy className="size-3 text-muted-foreground/60 transition-opacity group-hover:opacity-100" aria-hidden="true" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* The Realistic App Frame */}
        <div className="overflow-hidden rounded-2xl border border-border/80 bg-card shadow-md">
          {/* Top Browser / Window Chrome */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 bg-muted/60 px-4 py-2.5">
            {/* Traffic lights */}
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span className="size-3 rounded-full bg-red-500/80 shadow-xs" />
              <span className="size-3 rounded-full bg-amber-500/80 shadow-xs" />
              <span className="size-3 rounded-full bg-emerald-500/80 shadow-xs" />
            </div>

            {/* App switcher tabs */}
            <div role="tablist" aria-label="Apps in this template" className="flex items-center gap-1 rounded-lg bg-background/80 p-0.5 shadow-xs border border-border/40">
              {uiApps.map((app) => {
                const Icon = KIND_ICON[app.kind] || Globe;
                const active = app.id === selectedApp?.id;
                return (
                  <button
                    key={app.id}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    onClick={() => handleSelectApp(app.id)}
                    className={cn(
                      "inline-flex h-7 items-center gap-1.5 rounded-md px-3 text-xs font-medium text-muted-foreground transition-all",
                      active
                        ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                        : "hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="size-3.5" aria-hidden="true" />
                    <span>{app.name}</span>
                  </button>
                );
              })}
              {apiApp && (
                <button
                  type="button"
                  role="tab"
                  aria-selected={selectedApp?.id === apiApp.id}
                  onClick={() => handleSelectApp(apiApp.id)}
                  className={cn(
                    "inline-flex h-7 items-center gap-1.5 rounded-md px-3 text-xs font-medium text-muted-foreground transition-all",
                    selectedApp?.id === apiApp.id
                      ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                      : "hover:bg-muted hover:text-foreground"
                  )}
                >
                  <Server className="size-3.5" aria-hidden="true" />
                  <span>API Engine</span>
                </button>
              )}
            </div>

            {/* Address bar / Route indicator */}
            <div className="hidden sm:flex items-center gap-2 rounded-md border border-border/60 bg-background/90 px-3 py-1 font-mono text-xs text-muted-foreground shadow-xs">
              <span className="text-emerald-500 font-bold">https://</span>
              <span className="text-foreground font-medium">
                {selectedApp?.id}.{template.slug}.internal
              </span>
              <span className="text-brand font-semibold">{activeScreen?.route || "/"}</span>
            </div>

            <div className="flex items-center gap-1">
              {activeScreen && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => openLightbox(activeScreen)}
                  title="Expand to Fullscreen Lightbox"
                >
                  <Maximize2 className="size-4 text-muted-foreground" aria-hidden="true" />
                </Button>
              )}
            </div>
          </div>

          {/* Sub-scene navigator chips (e.g. Dashboard, Live Map, Trip Detail, Surge) */}
          {selectedApp?.kind !== "api" && currentAppScreens.length > 0 && (
            <div className="flex items-center gap-1.5 overflow-x-auto border-b border-border/40 bg-muted/20 px-4 py-2 text-xs no-scrollbar">
              <span className="shrink-0 font-medium text-muted-foreground mr-1">Views:</span>
              {currentAppScreens.map((screen, idx) => {
                const active = idx === activeScreenIndex;
                return (
                  <button
                    key={screen.image}
                    type="button"
                    onClick={() => setActiveScreenIndex(idx)}
                    className={cn(
                      "shrink-0 rounded-full px-2.5 py-1 text-xs font-medium transition-all",
                      active
                        ? "bg-foreground text-background shadow-xs font-semibold"
                        : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    {screen.title}
                  </button>
                );
              })}
            </div>
          )}

          {/* Frame Viewer Body */}
          <div className="grid place-items-center bg-gradient-to-b from-muted/30 to-muted/80 p-4 sm:p-8">
            {selectedApp?.kind === "api" ? (
              /* API Engine Inspector */
              <div className="w-full max-w-3xl rounded-xl border border-border/60 bg-neutral-950 p-6 font-mono text-xs text-neutral-200 shadow-xl">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-3 mb-4">
                  <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="font-semibold text-emerald-400">Hono TypeScript API · Health: 200 OK</span>
                  </div>
                  <span className="text-neutral-500">v{template.version}</span>
                </div>
                <div className="grid gap-3 text-neutral-300">
                  <p className="text-neutral-400">
                    Shared microservice backend powering Rider web, Driver PWA, and Ops Console over Server-Sent Events.
                  </p>
                  <div className="grid gap-2 mt-2">
                    <div className="flex items-center gap-2 rounded bg-neutral-900 px-3 py-2">
                      <span className="font-bold text-sky-400">GET</span>
                      <span className="text-white">/api/trips/live</span>
                      <span className="ml-auto text-neutral-500">SSE EventStream</span>
                    </div>
                    <div className="flex items-center gap-2 rounded bg-neutral-900 px-3 py-2">
                      <span className="font-bold text-emerald-400">POST</span>
                      <span className="text-white">/api/trips/book</span>
                      <span className="ml-auto text-neutral-500">Upfront Fare + Surge</span>
                    </div>
                    <div className="flex items-center gap-2 rounded bg-neutral-900 px-3 py-2">
                      <span className="font-bold text-amber-400">POST</span>
                      <span className="text-white">/api/drivers/offers/:id/accept</span>
                      <span className="ml-auto text-neutral-500">Dispatch lock</span>
                    </div>
                    <div className="flex items-center gap-2 rounded bg-neutral-900 px-3 py-2">
                      <span className="font-bold text-purple-400">GET</span>
                      <span className="text-white">/api/admin/map/fleet</span>
                      <span className="ml-auto text-neutral-500">Real-time coordinates</span>
                    </div>
                  </div>
                  <p className="mt-2 text-[11px] text-neutral-500">
                    Database: PostgreSQL 16 · All mock integrations (Payments, SMS, Maps) are self-contained.
                  </p>
                </div>
              </div>
            ) : isPhone ? (
              /* Mobile Phone Frame for PWA / Mobile */
              <div className="relative mx-auto w-[380px] max-w-full rounded-[2.85rem] border-[10px] border-neutral-900 bg-neutral-950 p-2 shadow-2xl ring-1 ring-white/10 dark:border-neutral-800">
                {/* Dynamic island / speaker cutout */}
                <div className="mx-auto mb-2 flex h-5 w-28 items-center justify-center rounded-full bg-neutral-900" aria-hidden="true">
                  <span className="size-2.5 rounded-full bg-neutral-800 ring-1 ring-neutral-700" />
                </div>

                {/* Screen content */}
                <div className="relative aspect-[9/19.5] w-full overflow-hidden rounded-[2.1rem] bg-neutral-900">
                  {activeScreen ? (
                    // eslint-disable-next-line @next/next/no-img-element -- relayed as-is
                    <img
                      src={templateAssetUrl(template.slug, activeScreen.image)}
                      alt={`${template.name} - ${activeScreen.title}`}
                      className="size-full object-cover"
                    />
                  ) : (
                    <div className="grid size-full place-items-center text-muted-foreground text-sm">
                      No screen selected
                    </div>
                  )}

                  {/* Hotspot overlay button */}
                  {activeScreen && (
                    <button
                      type="button"
                      onClick={() => openLightbox(activeScreen)}
                      className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity hover:opacity-100 backdrop-blur-xs text-white"
                      title="Inspect full screen"
                    >
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-4 py-2 text-xs font-semibold backdrop-blur-md">
                        <Maximize2 className="size-3.5" aria-hidden="true" />
                        Inspect High-Res Screen
                      </span>
                    </button>
                  )}
                </div>

                {/* Home Indicator */}
                <div className="mx-auto mt-2 h-1 w-32 rounded-full bg-neutral-700" aria-hidden="true" />
              </div>
            ) : (
              /* Desktop Frame for Admin / Ops */
              <div className="relative w-full overflow-hidden rounded-xl border border-border/80 bg-background shadow-xl">
                {activeScreen ? (
                  // eslint-disable-next-line @next/next/no-img-element -- relayed as-is
                  <img
                    src={templateAssetUrl(template.slug, activeScreen.image)}
                    alt={`${template.name} - ${activeScreen.title}`}
                    className="w-full object-contain"
                  />
                ) : (
                  <div className="grid aspect-[16/10] place-items-center text-muted-foreground text-sm">
                    No screen selected
                  </div>
                )}

                {/* Hotspot overlay button */}
                {activeScreen && (
                  <button
                    type="button"
                    onClick={() => openLightbox(activeScreen)}
                    className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 transition-opacity hover:opacity-100 backdrop-blur-xs text-white"
                    title="Inspect full screen"
                  >
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-4 py-2 text-sm font-semibold backdrop-blur-md">
                      <Maximize2 className="size-4" aria-hidden="true" />
                      Inspect High-Res Screen
                    </span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Bottom active view description */}
          {activeScreen && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/60 bg-card px-4 py-3 text-sm">
              <div>
                <p className="font-semibold text-foreground flex items-center gap-2">
                  <span>{activeScreen.title}</span>
                  <Badge variant="outline" className="font-mono text-[11px] font-normal">
                    {activeScreen.route}
                  </Badge>
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">{activeScreen.description}</p>
              </div>

              {currentAppScreens.length > 1 && (
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Button
                    variant="outline"
                    size="icon-sm"
                    onClick={() =>
                      setActiveScreenIndex(
                        (prev) => (prev - 1 + currentAppScreens.length) % currentAppScreens.length
                      )
                    }
                    title="Previous scene"
                  >
                    <ChevronLeft className="size-3.5" aria-hidden="true" />
                  </Button>
                  <span className="tabular-nums font-mono px-1">
                    {activeScreenIndex + 1} / {currentAppScreens.length}
                  </span>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    onClick={() =>
                      setActiveScreenIndex((prev) => (prev + 1) % currentAppScreens.length)
                    }
                    title="Next scene"
                  >
                    <ChevronRight className="size-3.5" aria-hidden="true" />
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 2. ALL 48 SCREENS VISUAL JOURNEY EXPLORER                     */}
      {/* ------------------------------------------------------------- */}
      <section id="screens-journey" className="scroll-mt-20">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border/60 pb-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Complete Screen Flow & Architecture</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Explore all {allScreens.length} production screens captured from running live instances. Click any card to inspect high-resolution details.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setGalleryFilter("all")}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                galleryFilter === "all"
                  ? "bg-primary text-primary-foreground font-semibold"
                  : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              )}
            >
              All Screens ({allScreens.length})
            </button>
            <button
              type="button"
              onClick={() => setGalleryFilter("highlights")}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                galleryFilter === "highlights"
                  ? "bg-primary text-primary-foreground font-semibold"
                  : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              )}
            >
              Highlights ({allScreens.filter((s) => s.highlight).length})
            </button>
            <button
              type="button"
              onClick={() => setGalleryFilter("admin")}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                galleryFilter === "admin"
                  ? "bg-primary text-primary-foreground font-semibold"
                  : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              )}
            >
              Ops Console ({allScreens.filter((s) => s.app === "admin").length})
            </button>
            <button
              type="button"
              onClick={() => setGalleryFilter("rider")}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                galleryFilter === "rider"
                  ? "bg-primary text-primary-foreground font-semibold"
                  : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              )}
            >
              Rider Web ({allScreens.filter((s) => s.app === "rider").length})
            </button>
            <button
              type="button"
              onClick={() => setGalleryFilter("driver")}
              className={cn(
                "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
                galleryFilter === "driver"
                  ? "bg-primary text-primary-foreground font-semibold"
                  : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground"
              )}
            >
              Driver PWA ({allScreens.filter((s) => s.app === "driver").length})
            </button>
          </div>
        </div>

        {/* Gallery Grid */}
        <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 mt-6">
          {filteredGalleryScreens.map((screen) => {
            const isScreenPhone = screen.device === "mobile" || screen.app === "driver";
            return (
              <div
                key={screen.image}
                onClick={() => openLightbox(screen)}
                className="group relative flex flex-col overflow-hidden rounded-xl border border-border/60 bg-card transition-all duration-200 hover:-translate-y-1 hover:border-foreground/30 hover:shadow-lg cursor-pointer"
              >
                <div className={cn("relative overflow-hidden bg-muted", isScreenPhone ? "aspect-[9/16]" : "aspect-[16/10]")}>
                  {/* eslint-disable-next-line @next/next/no-img-element -- relayed as-is */}
                  <img
                    src={templateAssetUrl(template.slug, screen.image)}
                    alt={screen.title}
                    loading="lazy"
                    className="size-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                  />
                  <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 transition-opacity group-hover:opacity-100 backdrop-blur-xs">
                    <span className="rounded-full bg-white/20 p-2 text-white shadow-sm backdrop-blur-md">
                      <Maximize2 className="size-4" aria-hidden="true" />
                    </span>
                  </div>
                  <Badge variant="secondary" className="absolute left-2.5 top-2.5 bg-background/85 text-[10px] uppercase font-semibold backdrop-blur">
                    {screen.app}
                  </Badge>
                </div>

                <div className="flex flex-1 flex-col p-3">
                  <h3 className="font-semibold text-sm tracking-tight text-foreground group-hover:text-brand transition-colors">
                    {screen.title}
                  </h3>
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                    {screen.description}
                  </p>
                  <p className="mt-auto pt-2 font-mono text-[11px] text-muted-foreground/70">
                    {screen.route}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 3. LIGHTBOX DIALOG FOR HIGH-RES FULLSCREEN INSPECTION         */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={lightboxIndex !== null} onOpenChange={(open) => !open && closeLightbox()}>
        <DialogContent className="max-w-5xl p-0 overflow-hidden bg-background/95 backdrop-blur border-border/80">
          {lightboxIndex !== null && allScreens[lightboxIndex] && (
            <div className="flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="uppercase text-[11px] font-semibold">
                    {allScreens[lightboxIndex].app}
                  </Badge>
                  <h3 className="font-semibold text-base">
                    {allScreens[lightboxIndex].title}
                  </h3>
                  <span className="font-mono text-xs text-muted-foreground">
                    {allScreens[lightboxIndex].route}
                  </span>
                </div>
                <div className="flex items-center gap-2 pr-8">
                  <span className="text-xs text-muted-foreground font-mono tabular-nums">
                    {lightboxIndex + 1} of {allScreens.length}
                  </span>
                </div>
              </div>

              {/* Image View Area */}
              <div className="relative grid place-items-center bg-black/90 p-4 sm:p-8 min-h-[460px] max-h-[75vh] overflow-auto">
                {/* eslint-disable-next-line @next/next/no-img-element -- relayed as-is */}
                <img
                  src={templateAssetUrl(template.slug, allScreens[lightboxIndex].image)}
                  alt={allScreens[lightboxIndex].title}
                  className={cn(
                    "max-h-[65vh] object-contain rounded-lg shadow-2xl",
                    (allScreens[lightboxIndex].device === "mobile" || allScreens[lightboxIndex].app === "driver") && "max-w-[340px]"
                  )}
                />

                {/* Left/Right controls */}
                <button
                  type="button"
                  onClick={prevLightbox}
                  className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-white/20 p-2 text-white hover:bg-white/40 transition-colors backdrop-blur-md"
                  aria-label="Previous screen"
                >
                  <ChevronLeft className="size-6" aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={nextLightbox}
                  className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-white/20 p-2 text-white hover:bg-white/40 transition-colors backdrop-blur-md"
                  aria-label="Next screen"
                >
                  <ChevronRight className="size-6" aria-hidden="true" />
                </button>
              </div>

              {/* Caption Footer */}
              <div className="border-t border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground">
                <p>{allScreens[lightboxIndex].description}</p>
                <p className="mt-1 text-xs text-muted-foreground/70">
                  Tip: Use Left and Right arrow keys on your keyboard to navigate through all {allScreens.length} screens.
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* ------------------------------------------------------------- */}
      {/* 4. COMPANION PWA QR CODE MODAL                                */}
      {/* ------------------------------------------------------------- */}
      <Dialog open={qrModalOpen} onOpenChange={setQrModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrIcon className="size-5 text-brand" aria-hidden="true" />
              Test on Your Mobile Device
            </DialogTitle>
            <DialogDescription>
              Scan with your iPhone or Android camera to experience {selectedApp?.name || "this app"} directly on your physical phone as an installable PWA.
            </DialogDescription>
          </DialogHeader>

          <div className="grid place-items-center py-4">
            <div className="rounded-2xl border border-border/60 bg-white p-4 shadow-md dark:bg-neutral-900">
              <QrCode
                value={mobileDemoUrl}
                size={220}
                level="M"
                fgColor="#000000"
                bgColor="#ffffff"
                className="rounded-lg"
              />
            </div>
            <p className="mt-3 text-center font-mono text-xs text-muted-foreground">
              {mobileDemoUrl}
            </p>
          </div>

          <div className="grid gap-2 rounded-xl bg-muted/60 p-3 text-xs text-muted-foreground">
            <p className="font-semibold text-foreground">Zero App Store Installation Needed:</p>
            <p>• <strong>iPhone / iOS:</strong> Open Camera &rarr; Scan QR &rarr; Open in Safari &rarr; Tap Share &rarr; &ldquo;Add to Home Screen&rdquo;.</p>
            <p>• <strong>Android:</strong> Open Camera / Google Lens &rarr; Open in Chrome &rarr; Tap &ldquo;Install App&rdquo;.</p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default TemplateShowcaseInteractive;
