"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Coins, CreditCard, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** PC-011: the user's plan, what it includes, and buying credits or a plan.
 *
 * Stripe checkouts are hosted (a redirect); Razorpay opens its own checkout on this page and the
 * payment is then verified by the control plane. Until keys are supplied (PC-070) the buttons say
 * payments are not set up, and a super_admin can add credits instead.
 */
type Plan = {
  id: string; name: string; monthly_credits: number; max_projects: number; max_published_apps: number;
  previews_per_user: number; builds_per_hour: number; task_budget_credits: number; team_members: number;
  custom_domains: boolean; own_model_keys: boolean; price_usd_monthly: number; price_inr_monthly: number;
};
type Pack = { id: string; name: string; credits: number; price_usd: number; price_inr: number };
type Billing = {
  plan: Plan; plans: Plan[]; packs: Pack[];
  usage: { projects: number; credit_balance: number };
  providers: { stripe: boolean; razorpay: boolean };
};

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

const limit = (n: number) => (n === 0 ? "Unlimited" : n.toLocaleString("en-US"));

function loadRazorpay(): Promise<boolean> {
  if (window.Razorpay) return Promise.resolve(true);
  return new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export function BillingPanel() {
  const [data, setData] = useState<Billing | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{ tone: "error" | "ok"; text: string } | null>(null);

  const load = useCallback(async () => {
    const res = await fetch("/api/billing/plan", { cache: "no-store" });
    if (res.ok) setData((await res.json()) as Billing);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/billing/plan", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : null))
      .then((body) => {
        if (!cancelled && body) setData(body as Billing);
      });
    const params = new URLSearchParams(window.location.search);
    if (params.get("paid")) setTimeout(() => setMessage({ tone: "ok", text: "Payment received. Thank you!" }), 0);
    return () => {
      cancelled = true;
    };
  }, []);

  const buy = async (kind: "credits" | "plan", id: string, provider: "stripe" | "razorpay") => {
    setBusy(`${kind}:${id}:${provider}`);
    setMessage(null);
    try {
      const res = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, id, provider }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || "The checkout could not start.");
      if (body.provider === "stripe") {
        window.location.assign(body.redirect_url);
        return;
      }
      if (!(await loadRazorpay()) || !window.Razorpay) throw new Error("Razorpay's checkout could not load.");
      new window.Razorpay({
        key: body.key_id,
        order_id: body.order_id,
        subscription_id: body.subscription_id,
        amount: body.amount,
        currency: body.currency,
        name: "OmniStackAI",
        description: body.name,
        handler: async (payment: Record<string, string>) => {
          const verify = await fetch("/api/billing/razorpay/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payment),
          });
          const result = await verify.json();
          setMessage(verify.ok ? { tone: "ok", text: "Payment received. Thank you!" } : { tone: "error", text: result.error });
          void load();
        },
      }).open();
    } catch (error) {
      setMessage({ tone: "error", text: error instanceof Error ? error.message : "The checkout could not start." });
    } finally {
      setBusy(null);
    }
  };

  if (!data) {
    return <p className="mt-8 flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Loading…</p>;
  }
  const payments = data.providers.stripe || data.providers.razorpay;

  return (
    <div className="mt-6 space-y-6">
      {message && (
        <p role={message.tone === "error" ? "alert" : "status"}
           className={message.tone === "error" ? "text-sm text-destructive" : "text-sm text-emerald-600 dark:text-emerald-400"}>
          {message.text}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {data.plan.name} plan <Badge variant="secondary">current</Badge>
          </CardTitle>
          <CardDescription>
            {data.usage.projects} of {limit(data.plan.max_projects)} projects ·{" "}
            <span className="inline-flex items-center gap-1"><Coins className="size-3.5" aria-hidden="true" />
              {data.usage.credit_balance.toLocaleString("en-US")} credits</span>
          </CardDescription>
        </CardHeader>
      </Card>

      <section aria-labelledby="plans-heading">
        <h2 id="plans-heading" className="mb-3 text-lg font-semibold">Plans</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.plans.map((plan) => {
            const current = plan.id === data.plan.id;
            const forSale = plan.price_usd_monthly > 0 || plan.price_inr_monthly > 0;
            return (
              <Card key={plan.id} className={current ? "border-primary" : undefined}>
                <CardHeader>
                  <CardTitle className="text-base">{plan.name}</CardTitle>
                  <CardDescription>
                    {forSale ? `$${plan.price_usd_monthly}/month · ₹${plan.price_inr_monthly}/month` : plan.id === "free" ? "Free" : "Not on sale yet"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <ul className="space-y-1 text-muted-foreground">
                    {plan.monthly_credits > 0 && <li>{plan.monthly_credits.toLocaleString("en-US")} credits a month</li>}
                    <li>{limit(plan.max_projects)} projects · {limit(plan.max_published_apps)} published apps</li>
                    <li>{limit(plan.builds_per_hour)} builds an hour · {limit(plan.previews_per_user)} running previews</li>
                    <li>{limit(plan.team_members)} {plan.team_members === 1 ? "person" : "people"} per workspace</li>
                    {plan.custom_domains && <li className="flex items-center gap-1"><Check className="size-3.5" aria-hidden="true" /> Custom domains</li>}
                    {plan.own_model_keys && <li className="flex items-center gap-1"><Check className="size-3.5" aria-hidden="true" /> Your own model keys</li>}
                  </ul>
                  {!current && forSale && (
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" disabled={busy !== null} onClick={() => buy("plan", plan.id, "stripe")}>Choose (card)</Button>
                      <Button size="sm" variant="outline" disabled={busy !== null} onClick={() => buy("plan", plan.id, "razorpay")}>Choose (UPI / India)</Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="credits-heading">
        <h2 id="credits-heading" className="mb-1 text-lg font-semibold">Add credits</h2>
        {!payments && (
          <p className="mb-3 text-sm text-muted-foreground">Payments are not set up yet. The platform owner can add credits to your account.</p>
        )}
        <div className="grid gap-4 sm:grid-cols-3">
          {data.packs.map((pack) => (
            <Card key={pack.id}>
              <CardHeader>
                <CardTitle className="text-base">{pack.name}</CardTitle>
                <CardDescription>${pack.price_usd} · ₹{pack.price_inr}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                <Button size="sm" disabled={!data.providers.stripe || busy !== null} onClick={() => buy("credits", pack.id, "stripe")}>
                  {busy === `credits:${pack.id}:stripe` ? <Loader2 className="size-3.5 animate-spin" /> : <CreditCard className="size-3.5" aria-hidden="true" />} Card
                </Button>
                <Button size="sm" variant="outline" disabled={!data.providers.razorpay || busy !== null} onClick={() => buy("credits", pack.id, "razorpay")}>
                  UPI / India
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
