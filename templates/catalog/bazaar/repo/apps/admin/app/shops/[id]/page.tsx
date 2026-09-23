"use client";

import { use, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Percent, ShieldCheck, Star, Truck } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Field, inputClass } from "../../../components/ui";
import { useApi, useAction } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { count, day, inr, stamp, titleCase, tone } from "../../../lib/format";

export default function WorkshopProfile({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { notify } = useSession();
  const shop = useApi(() => api.getAdminShop(id), [id]);
  const { run, busy, error } = useAction();
  const [commission, setCommission] = useState("");

  async function saveCommission() {
    const basisPoints = Math.round(Number(commission) * 100);
    const ok = await run(() => api.updateShopCommission(id, basisPoints));
    if (ok) {
      notify({ title: "Commission updated", detail: `${commission}% on every order`, tone: "good" });
      setCommission("");
      shop.refresh();
    }
  }

  return (
    <Shell
      title="Workshop"
      subtitle="Credentials, catalogue and the consignments it has shipped"
      actions={
        <Button href="/shops" variant="quiet" size="sm">
          <ArrowLeft size={13} /> Workshops
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={shop}>
        {(data) => (
          <div className="grid gap-3 lg:grid-cols-[1fr_1.6fr]">
            <div className="space-y-3">
              <Panel>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-[19px] font-semibold tracking-tight text-slate-100">{data.shop.name}</h2>
                    <p className="tabular text-[12px] text-[var(--muted)]">{data.shop.slug}</p>
                  </div>
                  <Badge tone={tone.kyc(data.shop.kyc_status)}>{titleCase(data.shop.kyc_status)}</Badge>
                </div>
                {data.shop.tagline && (
                  <p className="mt-2 text-[12.5px] text-[var(--muted-light)]">{data.shop.tagline}</p>
                )}
                {data.shop.description && (
                  <p className="mt-2 text-[12.5px] leading-relaxed text-[var(--muted-light)]">
                    {data.shop.description}
                  </p>
                )}

                <dl className="mt-4 space-y-2 text-[12.5px]">
                  {[
                    ["Commission", `${(data.shop.commission_rate_basis_points / 100).toFixed(1)}%`],
                    ["Rating", `${Number(data.shop.rating_avg).toFixed(1)} from ${data.shop.rating_count}`],
                    ["Bank", data.shop.bank_name ?? "Not on file"],
                    ["Account", data.shop.bank_account_last4 ? `•••• ${data.shop.bank_account_last4}` : "—"],
                    ["IFSC", data.shop.bank_ifsc_code ?? "—"],
                    ["Joined", day(data.shop.created_at)],
                    ["Selling", data.shop.is_active ? "Yes" : "Suspended"],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between gap-4">
                      <dt className="shrink-0 text-[var(--muted-light)]">{label}</dt>
                      <dd className="text-right text-slate-200">{value}</dd>
                    </div>
                  ))}
                </dl>

                {data.shop.kyc_status === "pending" && (
                  <div className="mt-3">
                    <Button href={`/shops/${id}/kyc`} size="sm">
                      <ShieldCheck size={13} /> Review KYC
                    </Button>
                  </div>
                )}
              </Panel>

              <Panel title="Commission" subtitle="What the platform keeps from each order">
                <Field label="Rate (%)" hint="Applied to new orders; existing consignments keep their rate.">
                  <input
                    className={inputClass}
                    type="number"
                    step="0.5"
                    min="0"
                    max="50"
                    value={commission}
                    placeholder={(data.shop.commission_rate_basis_points / 100).toFixed(1)}
                    onChange={(event) => setCommission(event.target.value)}
                  />
                </Field>
                <div className="mt-2">
                  <Button size="sm" disabled={busy || !commission} onClick={() => void saveCommission()}>
                    <Percent size={13} /> Save
                  </Button>
                </div>
              </Panel>
            </div>

            <div className="space-y-3">
              <Panel title="Catalogue" subtitle={`${data.products.length} listings`} padded={false}>
                {data.products.length === 0 ? (
                  <p className="px-4 py-8 text-center text-[13px] text-[var(--muted-light)]">
                    This workshop has not listed anything yet.
                  </p>
                ) : (
                  <Table head={["Product", "Price", "Stock", "Status"]}>
                    {data.products.slice(0, 12).map((product: any) => (
                      <Row key={product.id}>
                        <Cell>{product.title ?? product.name}</Cell>
                        <Cell align="right">{inr(product.price_cents ?? product.base_price_cents)}</Cell>
                        <Cell align="right" muted>{count(product.stock ?? product.total_stock)}</Cell>
                        <Cell>
                          <Badge tone={product.is_active === false ? "danger" : "good"}>
                            {product.is_active === false ? "Hidden" : "Live"}
                          </Badge>
                        </Cell>
                      </Row>
                    ))}
                  </Table>
                )}
              </Panel>

              <Panel title="Consignments" subtitle="What this workshop has shipped" padded={false}>
                {data.shipments.length === 0 ? (
                  <p className="px-4 py-8 text-center text-[13px] text-[var(--muted-light)]">
                    Nothing shipped yet.
                  </p>
                ) : (
                  <Table head={["Consignment", "Order", "Value", "Status", "Raised"]}>
                    {data.shipments.slice(0, 12).map((shipment: any) => (
                      <Row key={shipment.id}>
                        <Cell mono>{shipment.shipment_number ?? shipment.id.slice(0, 8)}</Cell>
                        <Cell>
                          {shipment.order_id ? (
                            <Link href={`/orders/${shipment.order_id}`} className="text-[var(--accent-light)] hover:underline">
                              {shipment.order_number ?? "Open"}
                            </Link>
                          ) : (
                            "—"
                          )}
                        </Cell>
                        <Cell align="right">{inr(shipment.subtotal_cents ?? shipment.total_cents)}</Cell>
                        <Cell>
                          <Badge tone={tone.shipment(shipment.status)}>{titleCase(shipment.status)}</Badge>
                        </Cell>
                        <Cell mono muted>{stamp(shipment.created_at)}</Cell>
                      </Row>
                    ))}
                  </Table>
                )}
              </Panel>
            </div>
          </div>
        )}
      </DataState>
    </Shell>
  );
}
