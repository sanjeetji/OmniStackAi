"use client";

import { useEffect, useState } from "react";
import { Coins } from "lucide-react";
import type { CostEstimate } from "@/lib/control-plane";

/** PC-010: what the next build or edit will likely cost, and what is left — before it starts.
 *
 * Re-read after every turn (``refreshKey``). When work cannot start (no credits, a cap, a pause)
 * it says why instead, so the user is never surprised by a refusal after typing.
 */
export function CostHint({ kind, projectId, refreshKey }: { kind: "build" | "edit"; projectId?: string | null; refreshKey?: number }) {
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);

  useEffect(() => {
    let cancelled = false;
    const query = new URLSearchParams({ kind });
    if (projectId) query.set("project", projectId);
    fetch(`/api/estimate?${query}`, { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled) setEstimate(data as CostEstimate | null);
      })
      .catch(() => {
        if (!cancelled) setEstimate(null);
      });
    return () => {
      cancelled = true;
    };
  }, [kind, projectId, refreshKey]);

  if (!estimate) return null;
  if (!estimate.can_start) {
    return (
      <p role="status" className="mt-2 flex items-start gap-1.5 text-xs text-destructive">
        <Coins className="mt-px size-3.5 shrink-0" aria-hidden="true" />
        <span className="text-pretty">{estimate.reason ?? "Building is not available right now."}</span>
      </p>
    );
  }
  const range =
    estimate.billed_to !== "platform" || estimate.priced === false
      ? "no credits"
      : estimate.credits_low === estimate.credits_high
        ? `about ${estimate.credits_low} credit${estimate.credits_low === 1 ? "" : "s"}`
        : `about ${estimate.credits_low}–${estimate.credits_high} credits`;
  return (
    <p className="mt-2 flex items-start gap-1.5 text-xs text-muted-foreground" title={estimate.basis ? `Based on ${estimate.basis}` : undefined}>
      <Coins className="mt-px size-3.5 shrink-0" aria-hidden="true" />
      <span className="text-pretty">
        This {kind}{estimate.includes_page_design ? " (with its pages designed by the model)" : ""} will use {range} · {estimate.credit_balance} left
        {estimate.budget_credits !== undefined && estimate.billed_to === "platform" && (
          <> · never more than {estimate.budget_credits}</>
        )}
      </span>
    </p>
  );
}
