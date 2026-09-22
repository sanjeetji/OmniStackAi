"use client";

import { useState } from "react";
import { IndianRupee, PauseCircle, PlayCircle } from "lucide-react";
import { inr } from "@ridenow/shared";
import { api } from "@/lib/api";
import { useAdmin } from "@/lib/session";
import { errorText } from "@/lib/use-api";
import { Button, Field, Modal, Notice, Segmented, TextArea } from "./ui";

/** Suspend or reactivate a rider or driver account (signs them out everywhere when suspended). */
export function AccountStatusButton({ userId, name, status, onDone }: { userId: string; name: string; status: "active" | "suspended"; onDone: () => void }) {
  const { toast } = useAdmin();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suspend = status === "active";

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/admin/users/${userId}/status`, { status: suspend ? "suspended" : "active" });
      toast(suspend ? `${name} is suspended` : `${name} is active again`);
      setOpen(false);
      onDone();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant={suspend ? "danger" : "ok"} onClick={() => setOpen(true)}>
        {suspend ? <PauseCircle className="size-4" aria-hidden="true" /> : <PlayCircle className="size-4" aria-hidden="true" />}
        {suspend ? "Suspend account" : "Reactivate"}
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={suspend ? `Suspend ${name}?` : `Reactivate ${name}?`}
        description={suspend ? "They are signed out on every device at once and cannot sign in until you reactivate them. Drivers also go offline." : "They can sign in again straight away. They get a notification."}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant={suspend ? "danger" : "ok"} busy={busy} onClick={() => void confirm()}>{suspend ? "Suspend" : "Reactivate"}</Button>
          </>
        }
      >
        {error ? <Notice tone="bad">{error}</Notice> : <p className="text-[13px] text-muted">This is recorded in the audit log with your name.</p>}
      </Modal>
    </>
  );
}

/** Credit or debit a wallet with a reason, e.g. a goodwill credit. */
export function WalletAdjustButton({ userId, name, balance, onDone }: { userId: string; name: string; balance: number; onDone: () => void }) {
  const { toast } = useAdmin();
  const [open, setOpen] = useState(false);
  const [direction, setDirection] = useState<"credit" | "debit">("credit");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const value = Number(amount);
  const valid = Number.isFinite(value) && value > 0 && value <= 10000 && note.trim().length >= 3;

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      const signed = direction === "credit" ? value : -value;
      const result = await api.post<{ balance: number }>(`/admin/wallets/${userId}/adjust`, { amount: signed, note: note.trim() });
      toast(`${direction === "credit" ? "Credited" : "Debited"} ${inr(value)}. New balance ${inr(result.balance)}`);
      setOpen(false);
      setAmount("");
      setNote("");
      onDone();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        <IndianRupee className="size-4" aria-hidden="true" />
        Adjust wallet
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={`Adjust ${name}'s wallet`}
        description={`Current balance ${inr(balance)}. The change is a ledger line with your note, and they are notified.`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button busy={busy} disabled={!valid} onClick={() => void confirm()}>
              {direction === "credit" ? "Credit" : "Debit"} {value > 0 ? inr(value) : ""}
            </Button>
          </>
        }
      >
        <div className="grid gap-4">
          <Segmented
            label="Direction"
            value={direction}
            onChange={setDirection}
            options={[
              { value: "credit", label: "Credit (add money)" },
              { value: "debit", label: "Debit (take money)" },
            ]}
          />
          <Field label="Amount" type="number" inputMode="decimal" min={1} max={10000} step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} suffix="₹" hint="Up to ₹10,000 per adjustment." />
          <TextArea label="Note (the account holder sees it)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} placeholder="For example: goodwill credit for a late pickup" />
          {error ? <Notice tone="bad">{error}</Notice> : null}
        </div>
      </Modal>
    </>
  );
}
