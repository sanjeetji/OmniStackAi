"use client";

import Link from "next/link";
import { RotateCcw } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, DataState, Stat } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { money, num, stamp, titleCase } from "../../lib/format";

/** The bands the API applies in services/api/src/lib/money.ts. Shown so the desk can explain them. */
const POLICY = [
  { window: "More than 24 hours before", refund: "100%", retained: "Nothing" },
  { window: "Between 4 and 24 hours", refund: "70%", retained: "30% processing fee" },
  { window: "Under 4 hours", refund: "Nothing", retained: "The whole fee" },
];

export default function Refunds() {
  const refunds = useApi(() => defaultApiClient.getRefunds(), []);
  const rows = refunds.data?.refunds ?? [];
  const returned = rows.reduce((sum, row) => sum + num(row.amount), 0);
  const retained = rows.reduce((sum, row) => sum + num(row.cancellation_fee), 0);

  return (
    <Shell title="Refunds" subtitle="Cancellations settled under the clinic policy">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Refunds processed" value={rows.length} icon={<RotateCcw size={15} />} />
        <Stat label="Returned to patients" value={money(returned)} tone="danger" />
        <Stat label="Retained by the clinic" value={money(retained)} tone="good" hint="Late-cancellation fees" />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1.6fr_1fr]">
        <Panel title="Processed refunds" padded={false}>
          <DataState state={refunds}>
            {(data) =>
              data.refunds.length === 0 ? (
                <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                  No cancellation has needed a refund yet.
                </p>
              ) : (
                <Table head={["Refund", "Patient", "Invoice", "Returned", "Retained", "Status", "Processed"]}>
                  {data.refunds.map((refund) => (
                    <Row key={refund.id}>
                      <Cell mono>{refund.refund_number}</Cell>
                      <Cell>{refund.patient_name ?? "—"}</Cell>
                      <Cell>
                        <Link href={`/billing/${refund.invoice_id}`} className="tabular text-[var(--color-signal)] hover:underline">
                          {refund.invoice_number ?? "Open"}
                        </Link>
                      </Cell>
                      <Cell align="right">{money(refund.amount)}</Cell>
                      <Cell align="right" muted>{money(refund.cancellation_fee)}</Cell>
                      <Cell>
                        <Badge tone={refund.refund_status === "processed" ? "good" : refund.refund_status === "failed" ? "danger" : "alert"}>
                          {titleCase(refund.refund_status)}
                        </Badge>
                      </Cell>
                      <Cell mono muted>{stamp(refund.processed_at)}</Cell>
                    </Row>
                  ))}
                </Table>
              )
            }
          </DataState>
        </Panel>

        <Panel title="Cancellation policy" subtitle="Applied automatically when a visit is cancelled">
          <ul className="space-y-3">
            {POLICY.map((band) => (
              <li key={band.window} className="rounded-md border border-[var(--color-border)] p-3">
                <p className="text-[12.5px] font-semibold text-[var(--color-ink)]">{band.window}</p>
                <dl className="mt-1 flex gap-6 text-[12px]">
                  <div>
                    <dt className="text-[var(--color-ink-subtle)]">Refunded</dt>
                    <dd className="font-semibold text-[var(--color-good)]">{band.refund}</dd>
                  </div>
                  <div>
                    <dt className="text-[var(--color-ink-subtle)]">Retained</dt>
                    <dd className="font-semibold text-[var(--color-ink)]">{band.retained}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-ink-muted)]">
            A refund is raised from the appointment screen. The money is returned to the original payment
            method; in this deployment that is a mock gateway.
          </p>
        </Panel>
      </div>
    </Shell>
  );
}
