"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, CreditCard, Plus, Wallet as WalletIcon } from "lucide-react";
import { ApiError, dateTimeLabel, inr, signedInr, useStream, type LedgerEntry } from "@ridenow/shared";
import { AppShell } from "@/components/app-shell";
import { Alert, Button, Card, EmptyState, Input, Sheet, Skeleton, cx } from "@/components/ui";
import { api } from "@/lib/api";

const KIND_LABEL: Record<string, string> = {
  topup: "Money added",
  trip_payment: "Ride payment",
  refund: "Refund",
  adjustment: "Adjustment",
};
const PAGE = 20;

export default function WalletPage() {
  const [balance, setBalance] = useState<number | null>(null);
  const [entries, setEntries] = useState<LedgerEntry[] | null>(null);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(false);

  const load = useCallback(() => {
    api.get<{ balance: number }>("/rider/wallet").then((r) => setBalance(r.balance));
    api.get<{ transactions: LedgerEntry[]; total: number }>(`/rider/wallet/transactions?limit=${PAGE}`).then((r) => {
      setEntries(r.transactions);
      setTotal(r.total);
    });
  }, []);
  useEffect(() => load(), [load]);
  useStream(api, { "wallet.updated": () => load() });

  return (
    <AppShell>
      <div className="grid gap-5 md:grid-cols-[1fr_1.4fr]">
        <div className="grid content-start gap-4">
          <div className="relative overflow-hidden rounded-[28px] bg-ink p-6 text-white shadow-[var(--shadow-float)]">
            <div className="absolute -right-10 -top-10 size-40 rounded-full bg-amber/25 blur-2xl" aria-hidden="true" />
            <p className="flex items-center gap-2 text-sm text-white/70"><WalletIcon className="size-4" aria-hidden="true" /> RideNow wallet</p>
            <p className="mt-3 text-4xl font-extrabold tracking-tight" aria-live="polite">{balance === null ? "…" : inr(balance)}</p>
            <p className="mt-1 text-sm text-white/60">Pay for rides in one tap. Refunds land here instantly.</p>
            <Button className="mt-6" onClick={() => setOpen(true)}><Plus className="size-4" aria-hidden="true" /> Add money</Button>
          </div>
          <Card className="p-5 text-sm text-muted">
            <p className="font-semibold text-ink">Good to know</p>
            <ul className="mt-2 grid list-disc gap-1 pl-5">
              <li>Wallet rides need enough balance for the upfront fare.</li>
              <li>Promo discounts are applied before we charge you.</li>
              <li>Cancellation fees apply only after the driver waits 3+ minutes.</li>
            </ul>
          </Card>
        </div>
        <Card className="p-2">
          <p className="px-4 pb-2 pt-3 font-bold">Transactions</p>
          {entries === null ? (
            <div className="grid gap-2 p-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : entries.length === 0 ? (
            <EmptyState icon={<WalletIcon className="size-6" />} title="No transactions yet" body="Top up your wallet to ride without cash." />
          ) : (
            <ul className="divide-y divide-line">
              {entries.map((entry) => (
                <li key={entry.id} className="flex items-center gap-3 px-4 py-3">
                  <span className={cx("grid size-10 place-items-center rounded-full", entry.amount >= 0 ? "bg-success-soft text-success" : "bg-black/5 text-ink-soft")}>
                    {entry.amount >= 0 ? <ArrowDownLeft className="size-4" aria-hidden="true" /> : <ArrowUpRight className="size-4" aria-hidden="true" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{KIND_LABEL[entry.kind] ?? entry.kind}{entry.reference && entry.kind !== "topup" ? ` · ${entry.reference}` : ""}</p>
                    <p className="truncate text-xs text-muted">{entry.note || dateTimeLabel(entry.created_at)}</p>
                  </div>
                  <div className="text-right">
                    <p className={cx("text-sm font-bold", entry.amount >= 0 && "text-success")}>{signedInr(entry.amount)}</p>
                    <p className="text-xs text-muted">{dateTimeLabel(entry.created_at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {entries && entries.length < total ? (
            <button
              type="button"
              className="mx-auto mb-2 block rounded-full px-4 py-2 text-sm font-semibold text-teal hover:bg-teal-soft"
              onClick={async () => {
                const r = await api.get<{ transactions: LedgerEntry[] }>(`/rider/wallet/transactions?limit=${PAGE}&offset=${entries.length}`);
                setEntries([...entries, ...r.transactions]);
              }}
            >
              Show more
            </button>
          ) : null}
        </Card>
      </div>
      <TopUp open={open} onClose={() => setOpen(false)} onDone={(next) => { setBalance(next); setOpen(false); load(); }} />
    </AppShell>
  );
}

function TopUp({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: (balance: number) => void }) {
  const [amount, setAmount] = useState(500);
  const [card, setCard] = useState("4242 4242 4242 4242");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <Sheet open={open} onClose={onClose} title="Add money">
      <form
        className="grid gap-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError(null);
          try {
            const r = await api.post<{ balance: number }>("/rider/wallet/topup", { amount, card_number: card });
            onDone(r.balance);
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Payment failed.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="grid grid-cols-4 gap-2">
          {[200, 500, 1000, 2000].map((value) => (
            <button key={value} type="button" onClick={() => setAmount(value)} aria-pressed={amount === value} className={cx("h-11 rounded-2xl border-2 text-sm font-bold", amount === value ? "border-ink" : "border-line")}>{inr(value)}</button>
          ))}
        </div>
        <Input label="Amount" type="number" min={50} max={20000} value={amount} onChange={(e) => setAmount(Number(e.target.value))} hint="Between ₹50 and ₹20,000." />
        <Input label="Card number" inputMode="numeric" value={card} onChange={(e) => setCard(e.target.value)} leading={<CreditCard className="size-4 text-muted" aria-hidden="true" />} hint="Demo payments: any card works except 4000 0000 0000 0002, which is declined." />
        {error ? <Alert>{error}</Alert> : null}
        <Button type="submit" size="lg" busy={busy}>Pay {inr(amount || 0)}</Button>
      </form>
    </Sheet>
  );
}
