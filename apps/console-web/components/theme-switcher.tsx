"use client";

import { useSyncExternalStore } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "system", label: "System", icon: Monitor },
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
] as const;

/* A hydration-safe "has this mounted on the client?" flag without setState-in-effect: the server
 * snapshot is false, the client snapshot is true, and there is nothing to subscribe to. */
const subscribeNoop = () => () => {};
function useMounted(): boolean {
  return useSyncExternalStore(
    subscribeNoop,
    () => true,
    () => false,
  );
}

/** Three-way theme control on next-themes (class strategy, dark default). Lives in Settings, not
 * as a sun/moon switch in the header. The server cannot know the stored preference, so the
 * control renders disabled until mounted and then reflects the real value. */
export default function ThemeSwitcher() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const mounted = useMounted();
  const current = mounted ? (theme ?? "system") : null;

  return (
    <div className="grid gap-2">
      <div
        role="group"
        aria-label="Theme"
        className="inline-flex w-fit items-center gap-0.5 rounded-lg bg-muted p-0.5"
      >
        {OPTIONS.map(({ value, label, icon: Icon }) => {
          const active = current === value;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={mounted ? active : undefined}
              disabled={!mounted}
              onClick={() => setTheme(value)}
              className={cn(
                "inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium outline-none transition-colors select-none focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px disabled:opacity-60",
                active
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </div>
      <p className="text-xs text-muted-foreground" aria-live="polite">
        {!mounted
          ? "Loading your preference…"
          : theme === "system" || !theme
            ? `Following your system setting (${resolvedTheme ?? "dark"} right now). Saved in this browser.`
            : `${theme === "dark" ? "Dark" : "Light"} theme. Saved in this browser.`}
      </p>
    </div>
  );
}
