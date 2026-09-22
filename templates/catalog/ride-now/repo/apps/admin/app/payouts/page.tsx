"use client";

import Link from "next/link";
import { useState } from "react";
import { Banknote, Check, X } from "lucide-react";
import { dateTimeLabel, inr, relativeTime } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { PayoutStatusBadge } from "@/components/status";
import { Button, Empty, ErrorState, LoadingRows, Modal, Notice, PageHeader, Panel, Person, Segmented, Stat, Table, td, th } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin, useAdminEvent } from "@/lib/session";
import type { PayoutRow } from "@/lib/types";
import { errorText, useApi } from "@/lib/use-api";

type Filter = "requested" | "paid" | "rejected" | "all";

export default function PayoutsPage() {
  return (
    <Shell>
      <PayoutsView />
    </Shell>
  );
}

function PayoutsView() {
  const { toast, refreshQueues } = useAdmin();
  const [filter, setFilter] = useState<Filter>("requested");
  const { data, error, loading, reload } = useApi<{ payouts: PayoutRow[] }>(filter === "all" ? "/admin/payouts" : `/admin/payouts?status=${filter}`);
  const [confirm, setConfirm] = useState<{ payout: PayoutRow; decision: "paid" | "rejected" } | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  useAdminEvent(["payout.requested"], reload);

  const due = filter === "requested" ? data?.payouts ?? [] : [];
  const dueTotal = due.reduce((sum, p) => sum + p.amount, 0);

  async function decide() {
    if (!confirm) return;
    setBusy(true);
    setActionError(null);
    try {
      await api.post(`/admin/payouts/${confirm.payout.id}/decision`, { decision: confirm.decision });
      toast(confirm.decision === "paid" ? `${inr(confirm.payout.amount)} sent to ${confirm.payout.driver_name}` : `Payout rejected; ${inr(confirm.payout.amount)} is back in ${confirm.payout.driver_name}'s wallet`);
      setConfirm(null);
      refreshQueues();
      reload();
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Payouts" description="Drivers withdraw their wallet balance to their bank. Pay or reject each request; a rejection returns the money to the wallet." />
      {filter === "requested" && data ? (
        <div className="mb-5 grid gap-3 sm:grid-cols-3">
          <Stat label="Waiting" value={due.length} />
          <Stat label="Amount requested" value={inr(dueTotal)} />
          <Stat label="Oldest request" value={due.length ? relativeTime(due[due.length - 1]!.requested_at) : "–"} />
        </div>
      ) : null}
      <Panel>
        <div className="border-b border-line p-3">
          <Segmented
            label="Payout status"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "requested", label: "To pay" },
              { value: "paid", label: "Paid" },
              { value: "rejected", label: "Rejected" },
              { value: "all", label: "All" },
            ]}
          />
        </div>
        {error && !data ? (
          <div className="p-4"><ErrorState message={error} onRetry={reload} /></div>
        ) : !data || loading ? (
          <LoadingRows label="Loading payouts" />
        ) : data.payouts.length === 0 ? (
          <Empty icon={<Banknote className="size-5" />} title={filter === "requested" ? "Nothing to pay" : "No payouts here"} body={filter === "requested" ? "Withdrawal requests from the driver app appear here." : "Try another status."} />
        ) : (
          <Table label="Payouts">
            <thead>
              <tr>
                <th className={th}>Driver</th>
                <th className={th}>Requested</th>
                <th className={th}>Bank</th>
                <th className={th}>Status</th>
                <th className={th}>Reference</th>
                <th className={`${th} text-right`}>Amount</th>
                <th className={`${th} text-right`}>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.payouts.map((p) => (
                <tr key={p.id} className="hover:bg-sunken">
                  <td className={td}><Link href={`/drivers/${p.driver_id}`} className="block"><Person name={p.driver_name} color={p.avatar_color} sub={p.plate} /></Link></td>
                  <td className={`${td} whitespace-nowrap text-ink-2`}>{dateTimeLabel(p.requested_at)}</td>
                  <td className={`${td} font-mono text-xs`}>{p.bank_last4 ? `•••• ${p.bank_last4}` : "–"}</td>
                  <td className={td}><PayoutStatusBadge status={p.status} /></td>
                  <td className={`${td} font-mono text-xs`}>{p.reference || "–"}</td>
                  <td className={`${td} num text-right font-semibold`}>{inr(p.amount)}</td>
                  <td className={`${td} text-right`}>
                    {p.status === "requested" ? (
                      <span className="inline-flex gap-1.5">
                        <Button size="sm" variant="ok" onClick={() => { setActionError(null); setConfirm({ payout: p, decision: "paid" }); }}>
                          <Check className="size-3.5" aria-hidden="true" />
                          Mark paid
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => { setActionError(null); setConfirm({ payout: p, decision: "rejected" }); }} aria-label={`Reject payout to ${p.driver_name}`}>
                          <X className="size-3.5" aria-hidden="true" />
                        </Button>
                      </span>
                    ) : (
                      <span className="text-xs text-muted">{p.processed_at ? relativeTime(p.processed_at) : ""}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Panel>
      <Modal
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={confirm?.decision === "paid" ? `Pay ${confirm ? inr(confirm.payout.amount) : ""} to ${confirm?.payout.driver_name}?` : `Reject ${confirm?.payout.driver_name}'s payout?`}
        description={
          confirm?.decision === "paid"
            ? "In this demo the bank transfer is simulated: a NEFT reference is generated and the driver is notified."
            : "The amount goes back to the driver's RideNow wallet and they are notified."
        }
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirm(null)}>Cancel</Button>
            <Button variant={confirm?.decision === "paid" ? "ok" : "danger"} busy={busy} onClick={() => void decide()}>
              {confirm?.decision === "paid" ? "Mark paid" : "Reject payout"}
            </Button>
          </>
        }
      >
        {actionError ? <Notice tone="bad">{actionError}</Notice> : <p className="text-[13px] text-muted">This is recorded in the audit log.</p>}
      </Modal>
    </>
  );
}
