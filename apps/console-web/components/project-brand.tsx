"use client";

import { useEffect, useState } from "react";
import { ImageUp, LoaderCircle, Palette, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type Brand = {
  name: string;
  primary_color: string;
  accent_color: string;
  font: string;
  heading_font: string;
  radius: string;
  style: string;
  logo: string;
  apps: string[];
  choices: { fonts: string[]; radii: string[]; styles: string[] };
};

const RADIUS_LABELS: Record<string, string> = { none: "Square", sm: "Slight", md: "Rounded", lg: "Soft", xl: "Very round" };
const MAX_LOGO = 512 * 1024;

/**
 * PC-020: the brand kit - one place to change a built product's look. Name, logo, colours, fonts,
 * corners and style are saved to the project's brand.json, which every app (web, admin, phone)
 * derives from; the preview follows without a rebuild.
 */
export function ProjectBrand({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [brand, setBrand] = useState<Brand | null>(null);
  const [draft, setDraft] = useState<Partial<Brand> & { logoData?: string; removeLogo?: boolean }>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const url = `/api/projects/${encodeURIComponent(projectId)}/brand`;

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    fetch(url, { cache: "no-store" })
      .then(async (res) => {
        const data = (await res.json()) as Brand & { error?: string };
        if (cancelled) return;
        if (!res.ok) setMessage({ kind: "error", text: data.error || "Could not load the brand." });
        else {
          setBrand(data);
          setDraft({});
        }
      })
      .catch(() => !cancelled && setMessage({ kind: "error", text: "Could not load the brand." }));
    return () => {
      cancelled = true;
    };
  }, [open, url]);

  const value = <K extends keyof Brand>(key: K): Brand[K] | undefined => (key in draft ? (draft[key] as Brand[K]) : brand?.[key]);

  function pickLogo(file: File | undefined) {
    if (!file) return;
    if (!/^image\/(png|svg\+xml)$/.test(file.type)) {
      setMessage({ kind: "error", text: "The logo must be a PNG or SVG image." });
      return;
    }
    if (file.size > MAX_LOGO) {
      setMessage({ kind: "error", text: "The logo must be at most 512 KB." });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setDraft((d) => ({ ...d, logoData: String(reader.result), removeLogo: false }));
    reader.readAsDataURL(file);
  }

  async function post(changes: Record<string, unknown>, attempt = 0): Promise<void> {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(changes) });
    const data = (await res.json().catch(() => ({}))) as { brand?: Brand; error?: string; renamed_files?: number };
    if (res.status === 409 && attempt < 90) {
      // Found live: page design holds the project for minutes after a build. The change is kept and
      // saved the moment the project is free, rather than refused.
      setMessage({ kind: "ok", text: "The pages are still being designed. Your brand change is kept and will be saved as soon as that finishes…" });
      await new Promise((resolve) => setTimeout(resolve, 10_000));
      return post(changes, attempt + 1);
    }
    if (!res.ok || !data.brand) {
      setMessage({ kind: "error", text: data.error || `Saving failed (${res.status}).` });
      return;
    }
    setBrand(data.brand);
    setDraft({});
    setMessage({ kind: "ok", text: `Saved. Every app now uses the new brand${data.renamed_files ? `, renamed in ${data.renamed_files} files` : ""}.` });
  }

  async function save() {
    if (!brand) return;
    const changes: Record<string, unknown> = {};
    for (const key of ["name", "primary_color", "accent_color", "font", "heading_font", "radius", "style"] as const) {
      if (key in draft && draft[key] !== brand[key]) changes[key] = draft[key];
    }
    if (draft.logoData) changes.logo = draft.logoData;
    if (draft.removeLogo) changes.remove_logo = true;
    if (Object.keys(changes).length === 0) {
      setMessage({ kind: "ok", text: "Nothing changed." });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await post(changes);
    } catch {
      setMessage({ kind: "error", text: "Saving failed: the platform could not be reached." });
    } finally {
      setBusy(false);
    }
  }

  const logo = draft.removeLogo ? "" : draft.logoData || (brand?.logo ? "set" : "");
  const field = "w-full rounded-md border border-border/70 bg-background px-2 py-1.5 text-sm";
  return (
    <>
      <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs" onClick={() => {
        setMessage(null);
        setOpen(true);
      }}>
        <Palette className="size-3.5" />
        Brand
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Brand</DialogTitle>
            <DialogDescription>
              One place for the product&apos;s look. Every app{brand ? ` (${brand.apps.join(", ")})` : ""} follows it.
            </DialogDescription>
          </DialogHeader>
          {!brand ? (
            <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
              {message ? message.text : <><LoaderCircle className="size-4 animate-spin" /> Loading…</>}
            </div>
          ) : (
            <div className="space-y-4">
              <label className="block space-y-1">
                <span className="text-xs font-medium">Name</span>
                <input className={field} maxLength={60} value={value("name") ?? ""}
                  onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))} />
              </label>
              <div className="space-y-1">
                <span className="text-xs font-medium">Logo</span>
                <div className="flex items-center gap-3">
                  <div className="flex size-14 items-center justify-center overflow-hidden rounded-lg border border-border/70 text-white"
                    style={{ background: value("primary_color") || "#4f46e5" }}>
                    {draft.logoData ? (
                      // eslint-disable-next-line @next/next/no-img-element -- a local preview of the chosen file
                      <img src={draft.logoData} alt="" className="size-full object-cover" />
                    ) : (
                      <span className="text-xl font-bold">{(value("name") || "A").slice(0, 1).toUpperCase()}</span>
                    )}
                  </div>
                  <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border/70 px-2.5 py-1.5 text-xs hover:bg-muted/40">
                    <ImageUp className="size-3.5" /> {logo ? "Replace" : "Upload"} PNG or SVG
                    <input type="file" accept="image/png,image/svg+xml" className="sr-only"
                      onChange={(e) => pickLogo(e.target.files?.[0])} />
                  </label>
                  {logo ? (
                    <Button type="button" variant="ghost" size="sm" className="h-8 gap-1 text-xs"
                      onClick={() => setDraft((d) => ({ ...d, logoData: undefined, removeLogo: Boolean(brand.logo) }))}>
                      <Trash2 className="size-3.5" /> Remove
                    </Button>
                  ) : null}
                </div>
                <p className="text-xs text-muted-foreground">Used in every app&apos;s header, the browser tab and the phone&apos;s home screen.</p>
              </div>
              <div className="flex flex-wrap gap-4">
                {(["primary_color", "accent_color"] as const).map((key) => (
                  <label key={key} className="flex items-center gap-2 text-xs">
                    <input type="color" className="size-8 cursor-pointer rounded border border-border/70 bg-transparent"
                      value={value(key) || "#4f46e5"} onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))} />
                    {key === "primary_color" ? "Main colour" : "Accent colour"}
                  </label>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-3">
                {(["font", "heading_font"] as const).map((key) => (
                  <label key={key} className="block space-y-1">
                    <span className="text-xs font-medium">{key === "font" ? "Text font" : "Heading font"}</span>
                    <select className={field} value={value(key) || brand.choices.fonts[0]}
                      onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))}>
                      {[...new Set([value(key) || "", ...brand.choices.fonts])].filter(Boolean).map((font) => (
                        <option key={font} value={font}>{font}</option>
                      ))}
                    </select>
                  </label>
                ))}
                <label className="block space-y-1">
                  <span className="text-xs font-medium">Corners</span>
                  <select className={field} value={value("radius") || "md"}
                    onChange={(e) => setDraft((d) => ({ ...d, radius: e.target.value }))}>
                    {brand.choices.radii.map((r) => <option key={r} value={r}>{RADIUS_LABELS[r] ?? r}</option>)}
                  </select>
                </label>
                <label className="block space-y-1">
                  <span className="text-xs font-medium">Style</span>
                  <select className={field} value={value("style") || ""}
                    onChange={(e) => setDraft((d) => ({ ...d, style: e.target.value }))}>
                    {!value("style") ? <option value="">Not set</option> : null}
                    {brand.choices.styles.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </label>
              </div>
              {message ? (
                <p role={message.kind === "error" ? "alert" : "status"}
                  className={message.kind === "error" ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
                  {message.text}
                </p>
              ) : null}
            </div>
          )}
          <DialogFooter>
            <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>Close</Button>
            <Button size="sm" disabled={!brand || busy} onClick={() => void save()}>
              {busy ? <LoaderCircle className="size-3.5 animate-spin" /> : null} Save brand
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
