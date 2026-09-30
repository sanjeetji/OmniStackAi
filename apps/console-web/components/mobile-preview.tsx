"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import {
  ArrowLeft,
  Check,
  Circle,
  Copy,
  Download,
  LoaderCircle,
  Play,
  Send,
  Smartphone,
  Square,
} from "lucide-react";
import type { AndroidInput, AndroidStatus, PreviewApp } from "@/lib/control-plane";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/**
 * PC-063: a project's mobile (Expo) app in the preview. A native app cannot run in an iframe, so
 * it opens two ways: on the owner's own phone (Expo Go scans the QR, R-545) and on the Android
 * emulator this machine runs for the Studio, shown here and driven with the mouse. The emulator is
 * set up only when the owner asks - it is a one-time download of about 1.5 GB.
 */
export function MobilePreview({ projectId, app }: { projectId: string; app: PreviewApp }) {
  return (
    <div className="grid gap-4 md:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
      <PhoneQr app={app} />
      <AndroidEmulator projectId={projectId} appId={app.id} ready={app.ready} />
    </div>
  );
}

function PhoneQr({ app }: { app: PreviewApp }) {
  const [qr, setQr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const draw = async () => {
      if (!app.scan) return;
      const url = await QRCode.toDataURL(app.scan, { margin: 1, width: 360 });
      if (!cancelled) setQr(url);
    };
    void draw();
    return () => {
      cancelled = true;
    };
  }, [app.scan]);

  return (
    <section aria-labelledby="phone-qr-title" className="space-y-2 rounded-lg border border-border/60 bg-background p-3">
      <h3 id="phone-qr-title" className="flex items-center gap-1.5 text-sm font-medium">
        <Smartphone className="size-4 text-muted-foreground" aria-hidden="true" />
        On your phone
      </h3>
      {qr ? (
        // eslint-disable-next-line @next/next/no-img-element -- a generated data URL
        <img src={qr} alt={`QR code for ${app.scan}`} className="mx-auto aspect-square w-full max-w-48 rounded-md bg-white p-1" />
      ) : (
        <div className="mx-auto aspect-square w-full max-w-48 animate-pulse rounded-md bg-muted" aria-hidden="true" />
      )}
      <p className="text-pretty text-xs text-muted-foreground">
        Install Expo Go, then scan this with the phone&apos;s camera. The phone must be on the same Wi-Fi as this computer.
      </p>
      {app.scan ? (
        <div className="flex items-center gap-1 rounded-md bg-muted px-2 py-1">
          <code className="min-w-0 flex-1 truncate text-xs">{app.scan}</code>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Copy the Expo link"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(app.scan ?? "");
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
              } catch {
                // clipboard blocked: the link is still visible
              }
            }}
          >
            {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
          </Button>
        </div>
      ) : null}
    </section>
  );
}

async function readJson<T>(res: Response): Promise<T> {
  const data = (await res.json().catch(() => ({}))) as T & { error?: string };
  if (!res.ok) throw new Error(data.error || `The request failed (${res.status})`);
  return data;
}

const MOVING = new Set(["setting_up", "booting", "stopping"]);

function AndroidEmulator({ projectId, appId, ready }: { projectId: string; appId: string; ready: boolean }) {
  const [status, setStatus] = useState<AndroidStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState(false);
  const [frame, setFrame] = useState<string | null>(null);
  const [text, setText] = useState("");
  const nudge = useRef(0);
  const image = useRef<HTMLImageElement | null>(null);
  const press = useRef<{ x: number; y: number } | null>(null);
  const state = status?.state;

  // The emulator's state: often while it is changing, rarely otherwise.
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const next = await readJson<AndroidStatus>(await fetch("/api/device/android", { cache: "no-store" }));
        if (cancelled) return;
        setStatus(next);
        timer = setTimeout(poll, MOVING.has(next.state) ? 2000 : 10000);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        timer = setTimeout(poll, 10000);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  // The screen, refreshed while the emulator runs and this tab is visible.
  useEffect(() => {
    if (state !== "running") return;
    let cancelled = false;
    let current: string | null = null;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      if (cancelled) return;
      if (document.visibilityState === "visible") {
        try {
          const res = await fetch(`/api/device/android/screen?n=${nudge.current}`, { cache: "no-store" });
          if (res.ok && !cancelled) {
            const url = URL.createObjectURL(await res.blob());
            setFrame(url);
            if (current) URL.revokeObjectURL(current);
            current = url;
          }
        } catch {
          // a missed frame: the next one follows
        }
      }
      if (!cancelled) timer = setTimeout(refresh, 700);
    };
    void refresh();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      if (current) URL.revokeObjectURL(current);
    };
  }, [state]);

  const act = async (action: "setup" | "boot" | "stop") => {
    setError(null);
    try {
      setStatus(
        await readJson<AndroidStatus>(
          await fetch("/api/device/android", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action }),
          }),
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const send = useCallback(async (input: AndroidInput) => {
    try {
      await readJson(
        await fetch("/api/device/android/input", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(input),
        }),
      );
      nudge.current += 1;
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  const openApp = async () => {
    setOpening(true);
    setError(null);
    try {
      await readJson(
        await fetch(`/api/projects/${encodeURIComponent(projectId)}/device`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ app: appId }),
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setOpening(false);
    }
  };

  // Screen coordinates -> device pixels (the image is scaled to fit).
  const toDevice = (clientX: number, clientY: number) => {
    const img = image.current;
    if (!img || !img.naturalWidth) return null;
    const box = img.getBoundingClientRect();
    return {
      x: Math.round(((clientX - box.left) / box.width) * img.naturalWidth),
      y: Math.round(((clientY - box.top) / box.height) * img.naturalHeight),
    };
  };

  return (
    <section aria-labelledby="emulator-title" className="space-y-3 rounded-lg border border-border/60 bg-background p-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 id="emulator-title" className="flex items-center gap-1.5 text-sm font-medium">
          <Circle
            className={cn("size-2.5", state === "running" ? "fill-brand text-brand" : "fill-muted-foreground/40 text-muted-foreground/40")}
            aria-hidden="true"
          />
          Android emulator
        </h3>
        <span className="min-w-0 flex-1" />
        {state === "running" ? (
          <>
            <Button type="button" size="sm" onClick={openApp} disabled={opening || !ready}>
              {opening ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
              {opening ? "Opening…" : "Open this app"}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => act("stop")}>
              <Square aria-hidden="true" />
              Stop
            </Button>
          </>
        ) : null}
      </div>

      {error ? (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : null}

      {!status ? (
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <LoaderCircle className="size-3.5 animate-spin" aria-hidden="true" /> Checking the emulator…
        </p>
      ) : state === "in_use" ? (
        <p className="text-sm text-muted-foreground">{status.error || "Another account is using the emulator on this machine."}</p>
      ) : state === "not_set_up" ? (
        <div className="space-y-2">
          <p className="text-pretty text-sm text-muted-foreground">
            Run the app on an Android phone right here, without Android Studio. Setting it up downloads Google&apos;s
            emulator tools and an Android 14 image once ({status.setup_size || "about 1.5 GB"}).
          </p>
          <Button type="button" size="sm" onClick={() => act("setup")}>
            <Download aria-hidden="true" />
            Set up the emulator
          </Button>
        </div>
      ) : state === "stopped" ? (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">The emulator is set up. Starting it takes under a minute.</p>
          <Button type="button" size="sm" onClick={() => act("boot")}>
            <Play aria-hidden="true" />
            Start the emulator
          </Button>
        </div>
      ) : state && MOVING.has(state) ? (
        <div className="space-y-1" role="status" aria-live="polite">
          <p className="flex items-center gap-2 text-sm">
            <LoaderCircle className="size-4 animate-spin text-muted-foreground" aria-hidden="true" />
            {state === "setting_up" ? "Setting up the emulator…" : state === "booting" ? "Starting Android…" : "Stopping…"}
          </p>
          {(status.log ?? []).slice(-3).map((line) => (
            <p key={line} className="truncate text-xs text-muted-foreground">
              {line}
            </p>
          ))}
        </div>
      ) : null}

      {state && !MOVING.has(state) && status?.error && state !== "in_use" ? (
        <p className="text-xs text-destructive">{status.error}</p>
      ) : null}

      {state === "running" ? (
        <div className="flex flex-col items-center gap-2">
          <div className="w-[300px] max-w-full rounded-[2rem] border-8 border-neutral-900 bg-neutral-900 shadow-xl dark:border-neutral-700">
            {frame ? (
              // eslint-disable-next-line @next/next/no-img-element -- a live frame from the emulator
              <img
                ref={image}
                src={frame}
                alt="The Android emulator's screen. Click to tap, drag to swipe."
                draggable={false}
                className="block w-full cursor-pointer touch-none select-none rounded-[1.5rem]"
                onPointerDown={(e) => {
                  press.current = toDevice(e.clientX, e.clientY);
                }}
                onPointerUp={(e) => {
                  const from = press.current;
                  const to = toDevice(e.clientX, e.clientY);
                  press.current = null;
                  if (!from || !to) return;
                  const moved = Math.hypot(to.x - from.x, to.y - from.y);
                  void send(moved > 24 ? { kind: "swipe", x: from.x, y: from.y, x2: to.x, y2: to.y } : { kind: "tap", ...to });
                }}
              />
            ) : (
              <div className="flex aspect-[9/19.5] w-full items-center justify-center rounded-[1.5rem] bg-neutral-800">
                <LoaderCircle className="size-5 animate-spin text-neutral-400" aria-hidden="true" />
              </div>
            )}
          </div>
          <div className="flex w-[300px] max-w-full items-center gap-1">
            <Button type="button" variant="outline" size="icon-sm" aria-label="Back" onClick={() => send({ kind: "key", key: "back" })}>
              <ArrowLeft aria-hidden="true" />
            </Button>
            <Button type="button" variant="outline" size="icon-sm" aria-label="Home" onClick={() => send({ kind: "key", key: "home" })}>
              <Circle aria-hidden="true" />
            </Button>
            <form
              className="flex min-w-0 flex-1 items-center gap-1"
              onSubmit={(e) => {
                e.preventDefault();
                if (!text) return;
                void send({ kind: "text", text });
                setText("");
              }}
            >
              <Input
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Type into the app"
                aria-label="Text to type into the app"
                className="h-8 min-w-0 flex-1 text-xs"
              />
              <Button type="submit" variant="outline" size="icon-sm" aria-label="Send the text">
                <Send aria-hidden="true" />
              </Button>
            </form>
          </div>
          {!ready ? <p className="text-xs text-muted-foreground">The app is still starting; open it when it is ready.</p> : null}
        </div>
      ) : null}
    </section>
  );
}
