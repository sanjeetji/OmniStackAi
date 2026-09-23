"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Ban, Package, Receipt, Truck } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Field, inputClass } from "../../../components/ui";
import { useApi, useAction } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { count, inr, num, stamp, titleCase, tone } from "../../../lib/format";

export default function OrderInvestigation({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { notify } = useSession();
  const order = useApi(() => api.getAdminOrder(id), [id]);
  const { run, busy, error } = useAction();
  const [reason, setReason] = useState("");
  const [cancelling, setCancelling] = useState(false);

  async function cancel() {
    const ok = await run(() => api.cancelAdminOrder(id, reason.trim()));
    if (ok) {
      notify({ title: "Order cancelled", detail: "The ledger has been reversed", tone: "alert" });
      setCancelling(false);
      setReason("");
      order.refresh();
    }
  }

  return (
    <Shell
      title="Order"
      subtitle="The whole trail: what was bought, who ships it, and where the money went"
      actions={
        <Button href="/orders" variant="quiet" size="sm">
          <ArrowLeft size={13} /> Orders
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={order}>
        {(data) => {
          const closed = ["cancelled", "completed"].includes(data.order.status);
          return (
            <div className="grid gap-3 lg:grid-cols-[1.5fr_1fr]">
              <div className="space-y-3">
                <Panel>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="tabular text-[12px] text-[var(--muted)]">{data.order.order_number}</p>
                      <h2 className="mt-0.5 text-[18px] font-semibold tracking-tight text-slate-100">
                        {inr(data.order.total_cents)}
                      </h2>
                      <p className="text-[12.5px] text-[var(--muted-light)]">Placed {stamp(data.order.created_at)}</p>
                    </div>
                    <Badge tone={tone.order(data.order.status)}>{titleCase(data.order.status)}</Badge>
                  </div>

                  <dl className="mt-4 grid gap-3 sm:grid-cols-3">
                    {[
                      ["Items", inr(data.order.subtotal_cents)],
                      ["Delivery", inr(data.order.shipping_cents)],
                      ["Discount", data.order.discount_cents ? `− ${inr(data.order.discount_cents)}` : "—"],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">{label}</dt>
                        <dd className="tabular mt-0.5 text-[13px] text-slate-200">{value}</dd>
                      </div>
                    ))}
                  </dl>
                </Panel>

                <Panel title="What was bought" padded={false}>
                  <Table head={["Item", "Workshop", "Qty", "Unit", "Line"]}>
                    {(data.items ?? []).map((item: any) => (
                      <Row key={item.id}>
                        <Cell>
                          <p className="text-slate-200">{item.product_title ?? item.title}</p>
                          {item.variant_label && (
                            <p className="text-[11px] text-[var(--muted)]">{item.variant_label}</p>
                          )}
                        </Cell>
                        <Cell muted>{item.shop_name ?? "—"}</Cell>
                        <Cell align="right" muted>{count(item.quantity)}</Cell>
                        <Cell align="right" muted>{inr(item.unit_price_cents)}</Cell>
                        <Cell align="right">{inr(num(item.unit_price_cents) * num(item.quantity))}</Cell>
                      </Row>
                    ))}
                  </Table>
                </Panel>

                <Panel
                  title="Consignments"
                  subtitle="One order splits into one consignment per workshop"
                  padded={false}
                >
                  {(data.shipments ?? []).length === 0 ? (
                    <p className="px-4 py-8 text-center text-[13px] text-[var(--muted-light)]">
                      No consignment has been raised yet.
                    </p>
                  ) : (
                    <ul className="divide-y divide-[var(--surface-border)]">
                      {(data.shipments ?? []).map((shipment: any) => (
                        <li key={shipment.id} className="px-4 py-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="text-[13px] font-medium text-slate-200">
                                {shipment.shop_name ?? "Workshop"}
                              </p>
                              <p className="tabular text-[11.5px] text-[var(--muted)]">
                                {shipment.shipment_number ?? shipment.id.slice(0, 8)}
                                {shipment.tracking_number ? ` · AWB ${shipment.tracking_number}` : ""}
                                {shipment.carrier ? ` · ${shipment.carrier}` : ""}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="tabular text-[12.5px] text-slate-200">
                                {inr(shipment.subtotal_cents ?? shipment.total_cents)}
                              </span>
                              <Badge tone={tone.shipment(shipment.status)}>{titleCase(shipment.status)}</Badge>
                            </div>
                          </div>

                          {(shipment.trackingEvents ?? []).length > 0 && (
                            <ol className="mt-2 space-y-1 border-l border-[var(--surface-border)] pl-3">
                              {shipment.trackingEvents.map((event: any) => (
                                <li key={event.id} className="text-[11.5px] text-[var(--muted-light)]">
                                  <span className="text-slate-300">{titleCase(event.status)}</span>
                                  {event.location ? ` · ${event.location}` : ""} · {stamp(event.created_at)}
                                </li>
                              ))}
                            </ol>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </Panel>
              </div>

              <div className="space-y-3">
                <Panel title="Shopper">
                  <p className="text-[13px] font-medium text-slate-200">{data.order.shopper_name ?? "—"}</p>
                  <p className="text-[12px] text-[var(--muted-light)]">{data.order.shopper_email ?? ""}</p>
                  {data.order.shipping_address_json && (
                    <p className="mt-2 rounded-lg bg-[var(--background)] p-2.5 text-[12px] leading-relaxed text-[var(--muted-light)]">
                      {typeof data.order.shipping_address_json === "string"
                        ? data.order.shipping_address_json
                        : [
                            data.order.shipping_address_json.recipientName,
                            data.order.shipping_address_json.street,
                            data.order.shipping_address_json.city,
                            data.order.shipping_address_json.state,
                            data.order.shipping_address_json.postalCode,
                          ]
                            .filter(Boolean)
                            .join(", ")}
                    </p>
                  )}
                </Panel>

                <Panel title="Where the money went" subtitle="Postings from the double-entry ledger" padded={false}>
                  {(data.ledgerEntries ?? []).length === 0 ? (
                    <p className="px-4 py-6 text-center text-[12.5px] text-[var(--muted-light)]">
                      No posting recorded against this order.
                    </p>
                  ) : (
                    <ul className="divide-y divide-[var(--surface-border)]">
                      {(data.ledgerEntries ?? []).map((entry: any) => (
                        <li key={entry.id} className="flex items-start justify-between gap-2 px-4 py-2.5">
                          <div className="min-w-0">
                            <p className="text-[12.5px] text-slate-200">{titleCase(entry.entry_type)}</p>
                            <p className="text-[11px] text-[var(--muted)]">
                              {titleCase(entry.debit_holder)} → {titleCase(entry.credit_holder)}
                            </p>
                          </div>
                          <span className="tabular shrink-0 text-[12.5px] text-slate-200">
                            {inr(entry.amount_cents)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="border-t border-[var(--surface-border)] px-4 py-2.5">
                    <Link href="/finance/ledger" className="text-[12px] font-semibold text-[var(--accent-light)] hover:underline">
                      Open the full ledger
                    </Link>
                  </div>
                </Panel>

                {!closed && (
                  <Panel title="Cancel this order" subtitle="Reverses every posting and releases the stock">
                    {cancelling ? (
                      <div className="space-y-2">
                        <Field label="Reason">
                          <textarea
                            className={`${inputClass} min-h-16`}
                            value={reason}
                            onChange={(event) => setReason(event.target.value)}
                            placeholder="Why is the order being cancelled?"
                          />
                        </Field>
                        <div className="flex gap-2">
                          <Button variant="danger" size="sm" disabled={busy || !reason.trim()} onClick={() => void cancel()}>
                            Confirm cancellation
                          </Button>
                          <Button variant="quiet" size="sm" onClick={() => setCancelling(false)}>
                            Keep it
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button variant="quiet" size="sm" onClick={() => setCancelling(true)}>
                        <Ban size={13} /> Cancel and refund
                      </Button>
                    )}
                  </Panel>
                )}
              </div>
            </div>
          );
        }}
      </DataState>
    </Shell>
  );
}
