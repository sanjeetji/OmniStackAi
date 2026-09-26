"use client";

import { useCallback, useSyncExternalStore } from "react";
import { Cpu, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

/** PC-005: the two ways to use the Studio.
 *
 * Vibe: prompt -> running app -> live URL, with the machinery hidden — chat, the live preview,
 * Publish, and plain-language notes about anything that is not real yet.
 * Engineering: everything Vibe shows, plus the files, the code, the problems, the entities, the
 * commit and the usage — what an engineer needs to review and own the result.
 *
 * Remembered per project (a project you engineer stays in Engineering), with the last choice as the
 * default for projects you have not opened yet. Kept in this browser: a per-person convenience, so a
 * failure to read or write it only means starting in Vibe.
 */
export type StudioMode = "vibe" | "engineering";

const DEFAULT_KEY = "omnistack.studio.mode";
const projectKey = (projectId: string) => `omnistack.studio.mode.${projectId}`;

// The switch must work even where storage is blocked, so every write also lands here.
const memory = new Map<string, StudioMode>();
const listeners = new Set<() => void>();

function read(key: string): StudioMode | null {
  try {
    const value = window.localStorage.getItem(key);
    if (value === "vibe" || value === "engineering") return value;
  } catch {
    // Private windows and blocked storage: fall back to this tab's memory.
  }
  return memory.get(key) ?? null;
}

function write(key: string, value: StudioMode) {
  memory.set(key, value);
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Not remembered across visits; still switches for this visit.
  }
}

function subscribe(onChange: () => void) {
  listeners.add(onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

export function useStudioMode(projectId: string | null | undefined): [StudioMode, (mode: StudioMode) => void] {
  const getSnapshot = useCallback(
    (): StudioMode => (projectId ? read(projectKey(projectId)) : null) ?? read(DEFAULT_KEY) ?? "vibe",
    [projectId],
  );
  // The server renders Vibe; the browser then shows the remembered mode.
  const mode = useSyncExternalStore(subscribe, getSnapshot, () => "vibe" as StudioMode);

  const setMode = useCallback(
    (next: StudioMode) => {
      write(DEFAULT_KEY, next);
      if (projectId) write(projectKey(projectId), next);
      listeners.forEach((notify) => notify());
    },
    [projectId],
  );

  return [mode, setMode];
}

const OPTIONS: { value: StudioMode; label: string; hint: string; icon: typeof Sparkles }[] = [
  { value: "vibe", label: "Vibe", hint: "Describe it, see it running, publish it", icon: Sparkles },
  { value: "engineering", label: "Engineering", hint: "Review the files, code, problems and plan", icon: Cpu },
];

export function ModeSwitcher({ mode, onChange }: { mode: StudioMode; onChange: (mode: StudioMode) => void }) {
  return (
    <div role="radiogroup" aria-label="Studio mode" className="inline-flex rounded-lg border bg-muted/40 p-0.5">
      {OPTIONS.map(({ value, label, hint, icon: Icon }) => {
        const selected = mode === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={selected}
            title={hint}
            onClick={() => onChange(value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              selected ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-3.5" aria-hidden="true" />
            {label} Mode
          </button>
        );
      })}
    </div>
  );
}
