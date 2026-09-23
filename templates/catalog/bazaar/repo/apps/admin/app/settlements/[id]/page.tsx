"use client";

import { use } from "react";
import { ArrowLeft, CheckCircle2, Landmark } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../../components/shell";
import { Panel, Badge, Button, DataState, ErrorNote } from "../../../components/ui";
import { useApi, useAction } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { inr, num, stamp, titleCase, tone } from "../../../lib/format";

export default function SettlementBatch({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { notify } = useSession();
  const batch = useApi(() => api.getAdminSettlement(id), [id]);
  const { run, busy, error } = useAction();

  async function approve() {
    const ok = await run(() => api.approveAdminSettlement(id));
    if (ok) {
      notify({ title: "Batch approved", detail: "The payout is posted to the ledger", tone: "good" });
      batch.refresh();
    }
  }

  return (
    <Shell
      title="Settlement batch"
      subtitle="What a workshop earned, what the platform kept, and what it will be paid"
      actions={
        <Button href="/settlements" variant="quiet" size="sm">
          <ArrowLeft size={13} /> Settlements
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={batch}>
        {(data) => {
          const s = data.settlement;
          const approved = s.status === "processed";

          return (
            <div className="mx-auto max-w-2xl">
              <Panel>
                <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--surface-border)] pb-4">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">
                      Settlement batch
                    </p>
                    <p className="tabular text-[16px] font-semibold text-slate-100">
                      {s.batch_number ?? s.id?.slice(0, 8)}
                    </p>
                    <p className="text-[12px] text-[var(--muted-light)]">Raised {stamp(s.created_at)}</p>
                  </div>
                  <Badge tone={tone.settlement(s.status)}>{titleCase(s.status)}</Badge>
                </header>

                <div className="grid gap-4 border-b border-[var(--surface-border)] py-4 sm:grid-cols-2">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">Paying</p>
                    <p className="mt-1 text-[13px] font-medium text-slate-200">{s.shop_name ?? "Workshop"}</p>
                    <p className="tabular text-[12px] text-[var(--muted-light)]">
                      {s.bank_name ?? "Bank not on file"}
                      {s.bank_account_last4 ? ` · •••• ${s.bank_account_last4}` : ""}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">Covers</p>
                    <p className="tabular mt-1 text-[13px] text-slate-200">
                      {s.shipment_count ?? "—"} delivered consignment{Number(s.shipment_count) === 1 ? "" : "s"}
                    </p>
                    {s.period_start && (
                      <p className="text-[12px] text-[var(--muted-light)]">
                        {stamp(s.period_start)} – {stamp(s.period_end)}
                      </p>
                    )}
                  </div>
                </div>

                <dl className="ml-auto mt-4 w-full max-w-xs space-y-1.5 text-[13px]">
                  <div className="flex justify-between">
                    <dt className="text-[var(--muted-light)]">Gross sales</dt>
                    <dd className="tabular text-slate-200">{inr(s.gross_amount_cents)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-[var(--muted-light)]">Platform commission</dt>
                    <dd className="tabular text-[var(--rose)]">− {inr(s.commission_cents)}</dd>
                  </div>
                  {num(s.adjustment_cents) !== 0 && (
                    <div className="flex justify-between">
                      <dt className="text-[var(--muted-light)]">Adjustments</dt>
                      <dd className="tabular text-slate-200">{inr(s.adjustment_cents)}</dd>
                    </div>
                  )}
                  <div className="flex justify-between border-t border-[var(--surface-border)] pt-1.5 text-[15px] font-semibold">
                    <dt className="text-slate-100">Net payout</dt>
                    <dd className="tabular text-[var(--emerald)]">{inr(s.net_payout_cents)}</dd>
                  </div>
                </dl>

                <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--surface-border)] pt-4">
                  <p className="flex items-start gap-1.5 text-[11.5px] leading-relaxed text-[var(--muted)]">
                    <Landmark size={12} className="mt-0.5 shrink-0" />
                    {approved
                      ? "Approved and posted. The bank transfer itself is a mock in this deployment."
                      : "Approving posts the payout to the ledger and records your account against it."}
                  </p>
                  {approved ? (
                    <span className="flex items-center gap-1.5 text-[12.5px] font-semibold text-[var(--emerald)]">
                      <CheckCircle2 size={14} /> Approved
                    </span>
                  ) : (
                    <Button disabled={busy} onClick={() => void approve()}>
                      <CheckCircle2 size={13} /> Approve the payout
                    </Button>
                  )}
                </footer>
              </Panel>
            </div>
          );
        }}
      </DataState>
    </Shell>
  );
}
