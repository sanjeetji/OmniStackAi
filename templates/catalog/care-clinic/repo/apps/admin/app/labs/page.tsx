"use client";

import { useState } from "react";
import { FlaskConical, Send, X } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Stat, inputClass, Loading } from "../../components/ui";
import { useApi, useAction, useInterval } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { day, money, stamp, titleCase, tone } from "../../lib/format";

const TABS = [
  { id: "", label: "Everything" },
  { id: "ordered", label: "Ordered" },
  { id: "sample_collected", label: "Sample taken" },
  { id: "processing", label: "On the bench" },
  { id: "completed", label: "Reported" },
];

const FLAGS = ["normal", "high", "low", "critical"] as const;

export default function Diagnostics() {
  const { pulse, prefs, notify } = useSession();
  const [status, setStatus] = useState("");
  const [openOrder, setOpenOrder] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, { resultValue: string; flag: string }>>({});

  const orders = useApi(() => defaultApiClient.getAdminLabOrders(status || undefined), [status, pulse]);
  const detail = useApi(
    () => (openOrder ? defaultApiClient.getAdminLabOrder(openOrder) : Promise.resolve(null)),
    [openOrder]
  );
  const { run, busy, error } = useAction();

  useInterval(orders.refresh, prefs.refreshSeconds * 1000);

  const rows = orders.data?.orders ?? [];
  const bench = rows.filter((order) => order.status !== "completed" && order.status !== "cancelled");

  async function advance(orderId: string, next: string) {
    const ok = await run(() => defaultApiClient.setLabOrderStatus(orderId, next));
    if (ok) {
      notify({ title: `Order marked ${titleCase(next).toLowerCase()}`, tone: "info" });
      orders.refresh();
      if (openOrder === orderId) detail.refresh();
    }
  }

  async function publish(orderId: string) {
    const items = Object.entries(results)
      .filter(([, value]) => value.resultValue.trim())
      .map(([itemId, value]) => ({ itemId, resultValue: value.resultValue.trim(), flag: value.flag }));
    if (items.length === 0) return;

    const ok = await run(() => defaultApiClient.uploadLabResults(orderId, items));
    if (ok) {
      notify({ title: "Report published", detail: "The patient and the doctor can see it now", tone: "good" });
      setResults({});
      setOpenOrder(null);
      orders.refresh();
    }
  }

  return (
    <Shell title="Diagnostics" subtitle="The lab bench: orders, samples and reported results">
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Open on the bench" value={bench.length} tone={bench.length > 0 ? "alert" : "plain"} icon={<FlaskConical size={15} />} />
        <Stat label="Awaiting a sample" value={rows.filter((order) => order.status === "ordered").length} />
        <Stat label="Reported in this view" value={rows.filter((order) => order.status === "completed").length} tone="good" />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1.5fr_1fr]">
        <Panel padded={false}>
          <div className="flex flex-wrap gap-1.5 border-b border-[var(--color-border)] px-4 py-3">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatus(tab.id)}
                className={
                  status === tab.id
                    ? "rounded-md bg-[var(--color-signal)] px-2.5 py-1 text-[12px] font-semibold text-white"
                    : "rounded-md border border-[var(--color-border-strong)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)] hover:bg-slate-50"
                }
              >
                {tab.label}
              </button>
            ))}
          </div>

          <DataState state={orders}>
            {(data) =>
              data.orders.length === 0 ? (
                <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">No lab order in this list.</p>
              ) : (
                <Table head={["Order", "Patient", "Requested by", "Raised", "Status", ""]}>
                  {data.orders.map((order) => (
                    <Row key={order.id} onClick={() => setOpenOrder(order.id)}>
                      <Cell mono>{order.order_number}</Cell>
                      <Cell>{order.patient_name}</Cell>
                      <Cell muted>{order.doctor_name}</Cell>
                      <Cell mono muted>{stamp(order.created_at)}</Cell>
                      <Cell>
                        <Badge tone={tone.lab(order.status)}>{titleCase(order.status)}</Badge>
                      </Cell>
                      <Cell align="right">
                        {order.status === "ordered" && (
                          <Button size="sm" variant="quiet" disabled={busy} onClick={() => void advance(order.id, "sample_collected")}>
                            Sample taken
                          </Button>
                        )}
                        {order.status === "sample_collected" && (
                          <Button size="sm" variant="quiet" disabled={busy} onClick={() => void advance(order.id, "processing")}>
                            Start processing
                          </Button>
                        )}
                        {order.status === "processing" && (
                          <Button size="sm" onClick={() => setOpenOrder(order.id)}>
                            Enter results
                          </Button>
                        )}
                      </Cell>
                    </Row>
                  ))}
                </Table>
              )
            }
          </DataState>
        </Panel>

        <Panel
          title={openOrder ? "Result entry" : "Pick an order"}
          subtitle={openOrder ? "Values are checked against the reference range" : "Choose a row to see its tests"}
          padded={false}
          actions={
            openOrder && (
              <button onClick={() => setOpenOrder(null)} aria-label="Close" className="text-[var(--color-ink-subtle)] hover:text-[var(--color-ink)]">
                <X size={14} />
              </button>
            )
          }
        >
          {!openOrder ? (
            <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
              Select a lab order from the bench to enter or review its results.
            </p>
          ) : detail.loading && !detail.data ? (
            <Loading label="Opening the order" />
          ) : detail.data ? (
            <div>
              <div className="border-b border-[var(--color-border)] px-4 py-3">
                <p className="tabular text-[13px] font-semibold text-[var(--color-ink)]">{detail.data.order.order_number}</p>
                <p className="text-[12px] text-[var(--color-ink-muted)]">
                  {detail.data.order.patient_name}
                  {detail.data.order.dob ? ` · born ${day(String(detail.data.order.dob))}` : ""}
                </p>
                <p className="text-[12px] text-[var(--color-ink-muted)]">Requested by {detail.data.order.doctor_name}</p>
              </div>

              <ul className="divide-y divide-[var(--color-border)]">
                {detail.data.items.map((item) => (
                  <li key={item.id} className="px-4 py-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-[12.5px] font-medium text-[var(--color-ink)]">{item.name}</p>
                        <p className="tabular text-[11px] text-[var(--color-ink-subtle)]">
                          {item.code} · {item.sample_type} · {money(item.standard_fee_inr)}
                        </p>
                      </div>
                      {item.result_value ? (
                        <Badge tone={tone.flag(item.flag)}>
                          {item.result_value} {item.unit}
                        </Badge>
                      ) : (
                        <Badge tone="alert">Pending</Badge>
                      )}
                    </div>
                    <p className="mt-1 text-[11px] text-[var(--color-ink-muted)]">Reference {item.reference_range}</p>

                    {detail.data!.order.status !== "completed" && (
                      <div className="mt-2 flex gap-2">
                        <input
                          className={`${inputClass} flex-1`}
                          placeholder={`Value in ${item.unit}`}
                          value={results[item.id]?.resultValue ?? ""}
                          onChange={(event) =>
                            setResults((current) => ({
                              ...current,
                              [item.id]: { resultValue: event.target.value, flag: current[item.id]?.flag ?? "normal" },
                            }))
                          }
                        />
                        <select
                          className={`${inputClass} w-32`}
                          value={results[item.id]?.flag ?? "normal"}
                          onChange={(event) =>
                            setResults((current) => ({
                              ...current,
                              [item.id]: { resultValue: current[item.id]?.resultValue ?? "", flag: event.target.value },
                            }))
                          }
                        >
                          {FLAGS.map((flag) => (
                            <option key={flag} value={flag}>
                              {titleCase(flag)}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </li>
                ))}
              </ul>

              {detail.data.order.status !== "completed" && (
                <div className="border-t border-[var(--color-border)] px-4 py-3">
                  <Button disabled={busy || Object.keys(results).length === 0} onClick={() => void publish(openOrder)}>
                    <Send size={13} /> Publish the report
                  </Button>
                  <p className="mt-1.5 text-[11px] text-[var(--color-ink-muted)]">
                    Publishing marks the order complete and releases it to the patient and the requesting doctor.
                  </p>
                </div>
              )}
            </div>
          ) : null}
        </Panel>
      </div>
    </Shell>
  );
}
