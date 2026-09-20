"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Code2,
  Copy,
  CreditCard,
  ExternalLink,
  FileCode,
  Globe,
  HelpCircle,
  Key,
  Layers,
  Loader2,
  Lock,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Zap,
} from "lucide-react";
import type { ProjectPaymentsResponse, PaymentKeyStatus } from "@/lib/control-plane";
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
import { cn } from "@/lib/utils";

interface ProjectPaymentsManageProps {
  projectId: string;
  projectName: string;
}

interface GatewayMeta {
  id: "stripe" | "razorpay";
  name: string;
  badge: string;
  badgeVariant: "default" | "secondary" | "outline";
  description: string;
  region: string;
  methods: string[];
  docsUrl: string;
  dashboardUrl: string;
  testCardOrVpa: string;
  files: { path: string; desc: string }[];
}

const GATEWAYS: GatewayMeta[] = [
  {
    id: "stripe",
    name: "Stripe",
    badge: "Global Standard",
    badgeVariant: "default",
    description:
      "Accept credit cards, Apple Pay, Google Pay, and localized payment methods across 135+ currencies with world-class fraud prevention.",
    region: "Global (135+ currencies)",
    methods: ["Cards (Visa, MC, Amex)", "Apple Pay / Google Pay", "iDEAL / SEPA", "Alipay / WeChat"],
    docsUrl: "https://stripe.com/docs",
    dashboardUrl: "https://dashboard.stripe.com/apikeys",
    testCardOrVpa: "Use 4242 4242 4242 4242 (any CVV / date in future) with test API keys.",
    files: [
      { path: "lib/payments/stripe.ts", desc: "Typed Stripe client, checkout & webhook verification (zero npm deps)" },
      { path: "app/api/checkout/route.ts", desc: "Checkout session creation API endpoint" },
      { path: "app/api/webhooks/stripe/route.ts", desc: "Webhook signature verification & event idempotency handler" },
      { path: "app/checkout/success/page.tsx", desc: "Payment completion & receipt page" },
      { path: "app/checkout/cancel/page.tsx", desc: "Payment cancellation & retry page" },
      { path: "tests/payments/test_stripe_webhook.js", desc: "Deterministic signature & idempotency test suite" },
    ],
  },
  {
    id: "razorpay",
    name: "Razorpay",
    badge: "India Standard",
    badgeVariant: "secondary",
    description:
      "The premier payment gateway for India & South Asia. Accept UPI, Netbanking from 50+ banks, credit & debit cards, and QR codes.",
    region: "India & South Asia (INR & multi-currency)",
    methods: ["UPI (GPay, PhonePe, Paytm)", "Credit & Debit Cards", "50+ Netbanking Banks", "PayLater & Wallets"],
    docsUrl: "https://razorpay.com/docs",
    dashboardUrl: "https://dashboard.razorpay.com/app/keys",
    testCardOrVpa: "Use UPI ID 'success@razorpay' or test card numbers in test mode.",
    files: [
      { path: "lib/payments/razorpay.ts", desc: "Typed Razorpay client, order creation & signature verification" },
      { path: "app/api/checkout/route.ts", desc: "Razorpay order creation API endpoint" },
      { path: "app/api/webhooks/razorpay/route.ts", desc: "HMAC-SHA256 signature verification & event idempotency handler" },
      { path: "app/checkout/success/page.tsx", desc: "Payment completion & receipt page" },
      { path: "app/checkout/cancel/page.tsx", desc: "Payment cancellation & retry page" },
      { path: "tests/payments/test_razorpay_webhook.js", desc: "Deterministic signature & idempotency test suite" },
    ],
  },
];

export function ProjectPaymentsManage({
  projectId,
  projectName,
}: ProjectPaymentsManageProps) {
  const [data, setData] = useState<ProjectPaymentsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Enabling / Disabling state
  const [actionGateway, setActionGateway] = useState<"stripe" | "razorpay" | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Disconnect confirmation modal
  const [confirmDisconnectOpen, setConfirmDisconnectOpen] = useState(false);

  // Copied webhook indicator
  const [copiedWebhook, setCopiedWebhook] = useState(false);

  const fetchPayments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`/api/projects/${projectId}/payments`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "Failed to load payments configuration");
      }
      const json: ProjectPaymentsResponse = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || "Failed to communicate with payments API");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`/api/projects/${projectId}/payments`);
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || "Failed to load payments configuration");
        }
        const json: ProjectPaymentsResponse = await res.json();
        if (active) {
          setData(json);
        }
      } catch (err: any) {
        if (active) {
          setError(err.message || "Failed to communicate with payments API");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    })();

    return () => {
      active = false;
    };
  }, [projectId]);

  const handleEnableGateway = async (gateway: "stripe" | "razorpay") => {
    setActionGateway(gateway);
    setActionLoading(true);
    setActionSuccess(null);
    setError(null);

    try {
      const res = await fetch(`/api/projects/${projectId}/payments`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payment_gateway: gateway }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Failed to enable ${gateway}`);
      }

      const updated = await res.json();
      setData(updated);
      setActionSuccess(`${gateway.charAt(0).toUpperCase() + gateway.slice(1)} payment gateway enabled!`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message || `Failed to enable ${gateway}`);
    } finally {
      setActionLoading(false);
      setActionGateway(null);
    }
  };

  const handleDisconnectGateway = async () => {
    if (!data?.payment_gateway) return;
    setActionLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/projects/${projectId}/payments`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "Failed to disconnect payment gateway");
      }

      setConfirmDisconnectOpen(false);
      await fetchPayments();
      setActionSuccess("Payment gateway disconnected.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to disconnect payment gateway");
    } finally {
      setActionLoading(false);
    }
  };

  const copyWebhookUrl = () => {
    if (!data?.webhook_url) return;
    navigator.clipboard.writeText(data.webhook_url);
    setCopiedWebhook(true);
    setTimeout(() => setCopiedWebhook(false), 2000);
  };

  const activeGateway = data?.payment_gateway || "";
  const keyStatuses = data?.key_statuses || [];
  const allKeysConfigured =
    keyStatuses.length > 0 &&
    keyStatuses.filter((k) => k.required).every((k) => k.status === "set");

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-gradient-to-r from-card to-muted/40 rounded-xl border border-border/80 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-primary" />
              Payment Gateways
            </h2>
            <Badge variant="outline" className="text-xs bg-primary/5 border-primary/20 text-primary">
              Generated App Payments
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Empower your generated app ({projectName}) to accept real customer payments. OmniStackAI
            generates production-grade checkout routes, webhook verification handlers, and status pages.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchPayments}
            disabled={loading || actionLoading}
            className="h-8 gap-1.5"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {/* PCI Isolation Notice */}
      <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
        <div className="text-xs space-y-1 text-emerald-950 dark:text-emerald-200">
          <p className="font-semibold">Zero PCI Scope & Complete Security Isolation</p>
          <p className="text-emerald-800 dark:text-emerald-300/90 leading-relaxed">
            OmniStackAI never handles, routes, or stores cardholder numbers or customer credentials.
            All checkout flows execute securely through Stripe / Razorpay hosted sessions or embedded modal SDKs,
            and webhooks are cryptographically validated with HMAC-SHA256 signatures.
          </p>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionSuccess && (
        <div className="p-4 bg-emerald-500/15 border border-emerald-500/30 rounded-lg flex items-center gap-3 animate-in fade-in duration-200">
          <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <p className="text-sm font-medium text-emerald-900 dark:text-emerald-200">{actionSuccess}</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-destructive/15 border border-destructive/30 rounded-lg flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
          <p className="text-sm text-destructive font-medium">{error}</p>
        </div>
      )}

      {/* Active Gateway Webhook & Keys Panel (if a gateway is active) */}
      {activeGateway && (
        <Card className="border-primary/30 shadow-sm bg-card/60">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </span>
                <CardTitle className="text-base font-semibold">
                  Active Gateway: {activeGateway.charAt(0).toUpperCase() + activeGateway.slice(1)}
                </CardTitle>
                <Badge
                  variant={allKeysConfigured ? "default" : "secondary"}
                  className={cn("text-xs font-mono", allKeysConfigured ? "bg-emerald-600 text-white" : "bg-amber-500/10 text-amber-600 border border-amber-500/30")}
                >
                  {allKeysConfigured ? "All Keys Configured" : "Keys Pending"}
                </Badge>
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConfirmDisconnectOpen(true)}
                className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 gap-1 text-xs"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Disconnect
              </Button>
            </div>
            <CardDescription className="text-xs">
              Review your live webhook endpoint and required secret keys checklist below.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4 pt-1">
            {/* Live Webhook URL Box */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Globe className="h-3.5 w-3.5 text-primary" />
                  Live Webhook URL (for {activeGateway.charAt(0).toUpperCase() + activeGateway.slice(1)} Dashboard)
                </label>
                <span className="text-[11px] text-muted-foreground">POST endpoint</span>
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 text-xs font-mono bg-muted/60 border border-border/80 rounded-md text-foreground select-all break-all">
                  {data?.webhook_url || `https://${projectName.toLowerCase().replace(/[^a-z0-9]/g, "-")}.omnistack.app/api/webhooks/${activeGateway}`}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={copyWebhookUrl}
                  className="shrink-0 h-9 gap-1.5"
                >
                  {copiedWebhook ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                      <span className="text-xs text-emerald-600">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span className="text-xs">Copy</span>
                    </>
                  )}
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {activeGateway === "stripe"
                  ? "Register this URL in Stripe Dashboard → Developers → Webhooks and listen for 'checkout.session.completed'."
                  : "Register this URL in Razorpay Dashboard → Settings → Webhooks and listen for 'order.paid' and 'payment.captured'."}
              </p>
            </div>

            {/* Required Secrets Checklist */}
            <div className="space-y-2 pt-2 border-t border-border/60">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Key className="h-3.5 w-3.5 text-primary" />
                  Required Secrets Checklist
                </span>
                <Link
                  href={`/studio/${projectId}/manage?tab=secrets`}
                  className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
                >
                  Manage Secrets
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                {keyStatuses.map((k) => (
                  <div
                    key={k.key}
                    className={cn(
                      "p-3 rounded-lg border text-xs flex flex-col justify-between gap-1.5",
                      k.status === "set"
                        ? "bg-emerald-500/5 border-emerald-500/20"
                        : "bg-amber-500/5 border-amber-500/20"
                    )}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono font-semibold text-foreground truncate" title={k.key}>
                        {k.key}
                      </span>
                      {k.status === "set" ? (
                        <Badge variant="outline" className="text-[10px] h-5 bg-emerald-500/10 text-emerald-600 border-emerald-500/30 gap-1">
                          <Check className="h-2.5 w-2.5" />
                          Configured
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] h-5 bg-amber-500/10 text-amber-600 border-amber-500/30 gap-1">
                          Missing
                        </Badge>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground leading-snug">{k.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Gateway Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {GATEWAYS.map((gw) => {
          const isActive = activeGateway === gw.id;
          const isOtherActive = activeGateway !== "" && !isActive;

          return (
            <Card
              key={gw.id}
              className={cn(
                "flex flex-col justify-between transition-all duration-200",
                isActive
                  ? "border-primary shadow-md bg-card ring-1 ring-primary/20"
                  : "border-border hover:border-primary/40 bg-card/50"
              )}
            >
              <div>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle className="text-lg font-bold text-foreground">
                          {gw.name}
                        </CardTitle>
                        <Badge variant={gw.badgeVariant} className="text-xs">
                          {gw.badge}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 font-medium">{gw.region}</p>
                    </div>

                    {isActive && (
                      <Badge className="bg-emerald-600 text-white text-xs gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Active
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs mt-2 leading-relaxed">
                    {gw.description}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-4 pt-0">
                  {/* Supported Methods */}
                  <div className="space-y-1.5">
                    <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                      Supported Payment Methods
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {gw.methods.map((method) => (
                        <span
                          key={method}
                          className="px-2 py-0.5 rounded-md bg-muted text-foreground text-xs font-medium"
                        >
                          {method}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Generated Files Breakdown */}
                  <div className="space-y-2 p-3 bg-muted/30 rounded-lg border border-border/60">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-foreground flex items-center gap-1.5">
                        <Code2 className="h-3.5 w-3.5 text-primary" />
                        Generated Next.js App Code
                      </span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {gw.files.length} files
                      </span>
                    </div>

                    <div className="space-y-1 text-xs font-mono">
                      {gw.files.slice(0, 3).map((f) => (
                        <div key={f.path} className="flex items-center gap-1.5 text-muted-foreground">
                          <FileCode className="h-3 w-3 shrink-0 text-primary/70" />
                          <span className="truncate text-[11px] text-foreground font-medium">{f.path}</span>
                        </div>
                      ))}
                      {gw.files.length > 3 && (
                        <p className="text-[10px] text-muted-foreground font-sans pl-4">
                          + {gw.files.length - 3} more files (success/cancel pages, verification tests)
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Test Mode Guidance */}
                  <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-amber-900 dark:text-amber-200">
                      <Zap className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                      Test Mode Sandbox
                    </div>
                    <p className="text-[11px] text-amber-800 dark:text-amber-300/90 leading-snug">
                      {gw.testCardOrVpa}
                    </p>
                  </div>
                </CardContent>
              </div>

              <CardFooter className="pt-2 pb-5 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-border/50">
                <a
                  href={gw.docsUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 order-2 sm:order-1"
                >
                  Gateway Docs
                  <ExternalLink className="h-3 w-3" />
                </a>

                <div className="order-1 sm:order-2 w-full sm:w-auto">
                  {isActive ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setConfirmDisconnectOpen(true)}
                      disabled={actionLoading}
                      className="w-full sm:w-auto text-destructive border-destructive/30 hover:bg-destructive/10 text-xs h-8"
                    >
                      Disconnect {gw.name}
                    </Button>
                  ) : (
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => handleEnableGateway(gw.id)}
                      disabled={actionLoading || loading}
                      className="w-full sm:w-auto text-xs h-8 gap-1.5"
                    >
                      {actionLoading && actionGateway === gw.id ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Injecting Code...
                        </>
                      ) : isOtherActive ? (
                        <>Switch to {gw.name}</>
                      ) : (
                        <>Enable {gw.name}</>
                      )}
                    </Button>
                  )}
                </div>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      {/* Disconnect Confirmation Dialog */}
      <Dialog open={confirmDisconnectOpen} onOpenChange={setConfirmDisconnectOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <Trash2 className="h-5 w-5" />
              Disconnect Payment Gateway
            </DialogTitle>
            <DialogDescription className="pt-2 text-sm leading-relaxed">
              Are you sure you want to disconnect {activeGateway ? activeGateway.toUpperCase() : "the payment gateway"}?
              This will safely clear the payment configuration and unmount generated checkout and webhook routes.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setConfirmDisconnectOpen(false)}
              disabled={actionLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisconnectGateway}
              disabled={actionLoading}
              className="gap-1.5"
            >
              {actionLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              Yes, Disconnect Gateway
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
