import { CircleAlert, CircleCheck, CircleHelp } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/time";

/** PC-013: a health test's answer, exactly as the provider gave it. "unchecked" is neither a pass
 * nor a failure: the provider could not be asked, or offers no free way to check. */
export type HealthStatus = "ok" | "failed" | "unchecked";

export interface HealthAnswer {
  status: HealthStatus;
  message: string;
  checked_at?: string;
}

const STYLE: Record<HealthStatus, { box: string; Icon: typeof CircleCheck; label: string }> = {
  ok: {
    box: "border-emerald-500/25 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    Icon: CircleCheck,
    label: "Working",
  },
  failed: { box: "border-destructive/25 bg-destructive/10 text-destructive", Icon: CircleAlert, label: "Not working" },
  unchecked: { box: "border-border bg-muted/50 text-muted-foreground", Icon: CircleHelp, label: "Not confirmed" },
};

export function HealthResult({ answer, className }: Readonly<{ answer: HealthAnswer; className?: string }>) {
  const style = STYLE[answer.status] ?? STYLE.unchecked;
  return (
    <div role="status" className={cn("flex items-start gap-2 rounded-lg border px-3 py-2 text-xs", style.box, className)}>
      <style.Icon className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
      <div className="grid gap-0.5">
        <span>
          <span className="font-medium">{style.label}.</span> {answer.message}
        </span>
        {answer.checked_at ? (
          <span className="opacity-75">Checked {formatRelativeTime(answer.checked_at)}</span>
        ) : null}
      </div>
    </div>
  );
}

export function HealthBadge({ answer }: Readonly<{ answer?: HealthAnswer }>) {
  if (!answer) return null;
  const style = STYLE[answer.status] ?? STYLE.unchecked;
  return (
    <span
      title={answer.message}
      className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium", style.box)}
    >
      <style.Icon className="size-3" aria-hidden="true" />
      {style.label}
    </span>
  );
}
