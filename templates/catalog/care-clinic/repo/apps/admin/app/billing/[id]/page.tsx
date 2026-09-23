"use client";

import { use } from "react";
import { ArrowLeft, Printer } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState } from "../../../components/ui";
import { useApi } from "../../../lib/use-api";
import { clock, day, money, num, stamp, titleCase, tone } from "../../../lib/format";

export default function InvoiceReceipt({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const receipt = useApi(() => defaultApiClient.getAdminInvoice(id), [id]);

  return (
    <Shell
      title="Receipt"
      subtitle="The itemised bill as the patient receives it"
      actions={
        <>
          <Button href="/billing" variant="quiet" size="sm">
            <ArrowLeft size={13} /> Cashier
          </Button>
          <Button size="sm" onClick={() => window.print()}>
            <Printer size={13} /> Print
          </Button>
        </>
      }
    >
      <DataState state={receipt}>
        {(data) => {
          const invoice = data.invoice;
          const refunded = data.refunds.reduce((sum, refund) => sum + num(refund.amount), 0);

          return (
            <div className="mx-auto max-w-3xl">
              <Panel>
                <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--color-border)] pb-4">
                  <div>
                    <p className="text-[15px] font-semibold tracking-tight text-[var(--color-ink)]">
                      {data.clinic?.name ?? "CareClinic"}
                    </p>
                    <p className="max-w-xs text-[11.5px] leading-relaxed text-[var(--color-ink-muted)]">
                      {data.clinic?.address}
                      {data.clinic?.city ? `, ${data.clinic.city} ${data.clinic.pincode ?? ""}` : ""}
                    </p>
                    <p className="text-[11.5px] text-[var(--color-ink-muted)]">
                      {data.clinic?.phone} · {data.clinic?.email}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">
                      Tax invoice
                    </p>
                    <p className="tabular text-[15px] font-semibold text-[var(--color-ink)]">{invoice.invoice_number}</p>
                    <p className="tabular text-[11.5px] text-[var(--color-ink-muted)]">Raised {stamp(invoice.created_at)}</p>
                    <div className="mt-1.5">
                      <Badge tone={tone.payment(invoice.payment_status)}>{titleCase(invoice.payment_status)}</Badge>
                    </div>
                  </div>
                </header>

                <div className="grid gap-4 border-b border-[var(--color-border)] py-4 sm:grid-cols-2">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">Billed to</p>
                    <p className="mt-1 text-[13px] font-medium text-[var(--color-ink)]">{invoice.patient_name}</p>
                    <p className="text-[12px] text-[var(--color-ink-muted)]">{invoice.patient_email}</p>
                    <p className="tabular text-[12px] text-[var(--color-ink-muted)]">{invoice.patient_phone ?? "—"}</p>
                    {invoice.blood_group && (
                      <p className="text-[11.5px] text-[var(--color-ink-subtle)]">
                        {titleCase(invoice.gender ?? "")} · Blood group {invoice.blood_group}
                      </p>
                    )}
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-ink-subtle)]">Visit</p>
                    <p className="tabular mt-1 text-[13px] text-[var(--color-ink)]">{invoice.appointment_number ?? "—"}</p>
                    <p className="text-[12px] text-[var(--color-ink-muted)]">
                      {invoice.scheduled_date ? day(String(invoice.scheduled_date)) : "—"}
                      {invoice.start_time ? ` · ${clock(invoice.start_time)}` : ""}
                    </p>
                    <p className="text-[12px] text-[var(--color-ink-muted)]">
                      {invoice.doctor_name ?? "—"}
                      {invoice.room_number ? ` · ${invoice.room_number}` : ""}
                    </p>
                  </div>
                </div>

                <Table head={["Description", "Type", "Qty", "Unit", "Amount"]}>
                  {data.items.map((item) => (
                    <Row key={item.id}>
                      <Cell>{item.description}</Cell>
                      <Cell muted>{titleCase(item.item_type)}</Cell>
                      <Cell align="right" muted>{item.quantity}</Cell>
                      <Cell align="right" muted>{money(item.unit_price)}</Cell>
                      <Cell align="right">{money(item.amount)}</Cell>
                    </Row>
                  ))}
                </Table>

                <dl className="ml-auto mt-4 w-full max-w-xs space-y-1.5 text-[13px]">
                  <div className="flex justify-between">
                    <dt className="text-[var(--color-ink-muted)]">Subtotal</dt>
                    <dd className="tabular">{money(invoice.total_amount)}</dd>
                  </div>
                  {num(invoice.discount_amount) > 0 && (
                    <div className="flex justify-between">
                      <dt className="text-[var(--color-ink-muted)]">Discount</dt>
                      <dd className="tabular text-[var(--color-good)]">− {money(invoice.discount_amount)}</dd>
                    </div>
                  )}
                  <div className="flex justify-between border-t border-[var(--color-border)] pt-1.5 text-[15px] font-semibold">
                    <dt>Net payable</dt>
                    <dd className="tabular">{money(invoice.net_payable)}</dd>
                  </div>
                  {refunded > 0 && (
                    <div className="flex justify-between text-[var(--color-danger)]">
                      <dt>Refunded</dt>
                      <dd className="tabular">− {money(refunded)}</dd>
                    </div>
                  )}
                </dl>

                <footer className="mt-4 border-t border-[var(--color-border)] pt-3 text-[11.5px] leading-relaxed text-[var(--color-ink-muted)]">
                  <p>
                    {invoice.payment_status === "paid"
                      ? `Paid by ${titleCase(invoice.payment_method ?? "—")}${
                          invoice.transaction_ref ? ` · reference ${invoice.transaction_ref}` : ""
                        }${invoice.paid_at ? ` on ${stamp(invoice.paid_at)}` : ""}.`
                      : "Payment is still to be collected at the counter."}
                  </p>
                  <p className="mt-1">
                    This receipt is generated by the clinic system. The payment gateway in this deployment is a
                    mock; swap it for a real provider in <code>services/api/src/services/billing.ts</code>.
                  </p>
                </footer>
              </Panel>

              {data.refunds.length > 0 && (
                <Panel className="mt-3" title="Refunds against this invoice" padded={false}>
                  <Table head={["Refund", "Amount", "Retained", "Reason", "Processed"]}>
                    {data.refunds.map((refund) => (
                      <Row key={refund.id}>
                        <Cell mono>{refund.refund_number}</Cell>
                        <Cell align="right">{money(refund.amount)}</Cell>
                        <Cell align="right" muted>{money(refund.cancellation_fee)}</Cell>
                        <Cell muted>{refund.reason}</Cell>
                        <Cell mono muted>{stamp(refund.processed_at)}</Cell>
                      </Row>
                    ))}
                  </Table>
                </Panel>
              )}
            </div>
          );
        }}
      </DataState>
    </Shell>
  );
}
