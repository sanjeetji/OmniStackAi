"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Landmark, ReceiptText } from "lucide-react";
import { ApiError, dateLabel, inr, relativeTime, signedInr, type LedgerEntry } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Button, Empty, Field, Loading, Notice, Panel, Sheet, Tag } from "@/components/ui";
import { api } from "@/lib/api";

interface Payout {
  id: string;
  amount: number;
  status: "requested" | "paid" | "rejected";
  bank_last4: string;
  reference: string | null;
  requested_at: string;
  processed_at: string | null;
}

interface WalletData {
  balance: number;
  min_payout: number;
  transactions: LedgerEntry[];
  payouts: Payout[];
}

const KIND_LABEL: Record<string, string> = {
  trip_earning: "Trip earning",
  cash_commission: "Commission on cash trip",
  payout: "Payout",
  refund: "Refund",
  adjustment: "Adjustment",
};

export default function WalletPage() {
  const [data, setData] = useState<WalletData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const load = useCallback(() => api.get<WalletData>("/driver/wallet?limit=50").then(setData).catch(() => setError("Couldn't load your wallet.")), []);
  useEffect(() => void load(), [load]);

  const pending = data?.payouts.find((p) => p.status === "requested");

  return (
    <Shell title="Wallet">
      {!data ? (error ? <Notice>{error}</Notice> : <Loading label="Loading wallet" />) : (
        <div className="grid gap-4">
          <Panel className="p-5">
            <p className="text-sm font-semibold text-fg-muted">Available to withdraw</p>
            <p className="mt-1 text-4xl font-extrabold tabular-nums">{inr(data.balance)}</p>
            <p className="mt-1 text-xs text-fg-muted">Bank account ending 4417 · minimum payout {inr(data.min_payout)}</p>
            <Button className="mt-4 w-full" size="lg" disabled={Boolean(pending) || data.balance < data.min_payout} onClick={() => setOpen(true)}>
              <Landmark className="size-4" aria-hidden="true" /> Withdraw to bank
            </Button>
            {pending ? <p className="mt-2 text-center text-xs text-warn">{inr(pending.amount)} payout in progress since {relativeTime(pending.requested_at)}.</p> : null}
            {!pending && data.balance < data.min_payout ? <p className="mt-2 text-center text-xs text-fg-muted">Earn {inr(data.min_payout - data.balance)} more to withdraw.</p> : null}
          </Panel>

          {data.payouts.length > 0 ? (
            <section>
              <h2 className="mb-2 px-1 text-sm font-bold text-fg-muted">Payouts</h2>
              <Panel className="divide-y divide-line/60">
                {data.payouts.slice(0, 5).map((p) => (
                  <div key={p.id} className="flex items-center gap-3 px-4 py-3">
                    <Landmark className="size-5 text-fg-muted" aria-hidden="true" />
                    <div className="flex-1">
                      <p className="font-semibold tabular-nums">{inr(p.amount)}</p>
                      <p className="text-xs text-fg-muted">{dateLabel(p.requested_at)} · to ••{p.bank_last4}</p>
                    </div>
                    <Tag tone={p.status === "paid" ? "go" : p.status === "rejected" ? "danger" : "warn"}>{p.status === "requested" ? "Processing" : p.status === "paid" ? "Paid" : "Returned"}</Tag>
                  </div>
                ))}
              </Panel>
            </section>
          ) : null}

          <section>
            <h2 className="mb-2 px-1 text-sm font-bold text-fg-muted">Activity</h2>
            {data.transactions.length === 0 ? (
              <Panel><Empty icon={<ReceiptText className="size-6" />} title="No activity yet" body="Your trip earnings and payouts will show up here." /></Panel>
            ) : (
              <Panel className="divide-y divide-line/60">
                {data.transactions.map((t) => (
                  <div key={t.id} className="flex items-center gap-3 px-4 py-3">
                    <span className={t.amount >= 0 ? "grid size-9 place-items-center rounded-xl bg-go-soft text-go" : "grid size-9 place-items-center rounded-xl bg-white/8 text-fg-muted"}>
                      {t.amount >= 0 ? <ArrowDownLeft className="size-4" aria-hidden="true" /> : <ArrowUpRight className="size-4" aria-hidden="true" />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{KIND_LABEL[t.kind] ?? t.kind}</p>
                      <p className="truncate text-xs text-fg-muted">{t.note || t.reference} · {relativeTime(t.created_at)}</p>
                    </div>
                    <div className="text-right">
                      <p className={t.amount >= 0 ? "font-bold tabular-nums text-go" : "font-bold tabular-nums"}>{signedInr(t.amount)}</p>
                      <p className="text-xs tabular-nums text-fg-muted">{inr(t.balance_after)}</p>
                    </div>
                  </div>
                ))}
              </Panel>
            )}
          </section>
          <WithdrawSheet open={open} onClose={() => setOpen(false)} balance={data.balance} min={data.min_payout} onDone={() => void load()} />
        </div>
      )}
    </Shell>
  );
}

function WithdrawSheet({ open, onClose, balance, min, onDone }: { open: boolean; onClose: () => void; balance: number; min: number; onDone: () => void }) {
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (open) {
      setAmount(String(Math.floor(balance)));
      setError(null);
    }
  }, [open, balance]);
  const value = Number(amount);

  return (
    <Sheet open={open} onClose={onClose} title="Withdraw to bank">
      <form
        className="grid gap-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await api.post("/driver/payouts", { amount: value });
            onDone();
            onClose();
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Couldn't request the payout.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="Amount (₹)" type="number" inputMode="decimal" min={min} max={balance} step="1" value={amount} onChange={(e) => setAmount(e.target.value)} hint={`Between ${inr(min)} and ${inr(balance)}. Usually reaches your bank within a day.`} required />
        {error ? <Notice>{error}</Notice> : null}
        <Button type="submit" size="lg" busy={busy} disabled={!(value >= min && value <= balance)}>Withdraw {value > 0 ? inr(value) : ""}</Button>
      </form>
    </Sheet>
  );
}
