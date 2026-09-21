"use client";

import { useEffect, useState } from "react";
import { Check, Copy, TicketPercent } from "lucide-react";
import { dateLabel, inr, type Promo } from "@ridenow/shared";
import { AppShell } from "@/components/app-shell";
import { Badge, ButtonLink, Card, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";

export default function PromosPage() {
  const [promos, setPromos] = useState<Promo[] | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  useEffect(() => {
    api.get<{ promos: Promo[] }>("/rider/promos").then((r) => setPromos(r.promos)).catch(() => setPromos([]));
  }, []);

  return (
    <AppShell>
      <PageHeader title="Promotions" subtitle="Apply a code when you book. Discounts are shown before you pay." />
      {promos === null ? (
        <div className="grid gap-3 sm:grid-cols-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-40" />)}</div>
      ) : promos.length === 0 ? (
        <Card><EmptyState icon={<TicketPercent className="size-6" />} title="No offers right now" body="We'll let you know when a new offer goes live." /></Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {promos.map((promo) => (
            <Card key={promo.code} as="article" className="relative overflow-hidden p-5">
              <div className="absolute -right-6 -top-6 size-24 rounded-full bg-amber-soft" aria-hidden="true" />
              <p className="relative text-3xl font-extrabold text-amber-deep">{promo.kind === "percent" ? `${promo.value}% off` : `${inr(promo.value)} off`}</p>
              <p className="relative mt-1 font-semibold">{promo.description}</p>
              <p className="relative mt-2 text-xs text-muted">
                {promo.max_discount ? `Up to ${inr(promo.max_discount)}. ` : ""}
                {promo.min_fare > 0 ? `On rides above ${inr(promo.min_fare)}. ` : ""}
                {promo.valid_until ? `Valid till ${dateLabel(promo.valid_until)}.` : ""}
              </p>
              <div className="relative mt-4 flex items-center gap-2">
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(promo.code);
                      setCopied(promo.code);
                      setTimeout(() => setCopied(null), 1600);
                    } catch {
                      setCopied(null);
                    }
                  }}
                  className="inline-flex items-center gap-2 rounded-xl border-2 border-dashed border-amber px-3 py-1.5 font-mono font-bold"
                  aria-label={`Copy code ${promo.code}`}
                >
                  {promo.code} {copied === promo.code ? <Check className="size-4 text-success" aria-hidden="true" /> : <Copy className="size-4 text-muted" aria-hidden="true" />}
                </button>
                {promo.uses_left === 0 ? <Badge>Used</Badge> : <Badge tone="teal">{promo.uses_left} use{promo.uses_left === 1 ? "" : "s"} left</Badge>}
              </div>
            </Card>
          ))}
        </div>
      )}
      <div className="mt-6"><ButtonLink href="/ride" variant="dark">Book a ride</ButtonLink></div>
    </AppShell>
  );
}
