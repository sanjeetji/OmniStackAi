"use client";

import { use, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, FlaskConical, Search, Send } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../../../components/shell";
import { ConsultFrame, BackToQueue } from "../../../../components/consult-frame";
import { Panel, Badge, Button, DataState, ErrorNote, inputClass } from "../../../../components/ui";
import { useApi, useAction } from "../../../../lib/use-api";
import { useSession } from "../../../../lib/session";
import { money, stamp, titleCase, tone } from "../../../../lib/format";

export default function LabOrders({ params }: { params: Promise<{ appointmentId: string }> }) {
  const { appointmentId } = use(params);
  const router = useRouter();
  const { notify } = useSession();
  const context = useApi(() => defaultApiClient.getConsultContext(appointmentId), [appointmentId]);
  const catalog = useApi(() => defaultApiClient.getLabTests(), []);
  const { run, busy, error } = useAction();

  const [picked, setPicked] = useState<string[]>([]);
  const [search, setSearch] = useState("");

  const tests = catalog.data?.tests ?? [];
  const shown = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return tests;
    return tests.filter(
      (test) =>
        test.name.toLowerCase().includes(term) ||
        test.code.toLowerCase().includes(term) ||
        test.category.toLowerCase().includes(term)
    );
  }, [tests, search]);

  const byCategory = useMemo(() => {
    const groups = new Map<string, typeof tests>();
    for (const test of shown) {
      const list = groups.get(test.category) ?? [];
      list.push(test);
      groups.set(test.category, list);
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [shown]);

  const total = tests.filter((t) => picked.includes(t.code)).reduce((sum, t) => sum + t.standard_fee_inr, 0);

  function toggle(code: string) {
    setPicked((current) => (current.includes(code) ? current.filter((c) => c !== code) : [...current, code]));
  }

  async function order() {
    const ok = await run(async () => {
      await defaultApiClient.orderLabs(appointmentId, picked);
      context.refresh();
    });
    if (ok) {
      notify({ title: "Lab order raised", detail: "The bench will collect the sample", tone: "good" });
      setPicked([]);
      router.push(`/consult/${appointmentId}`);
    }
  }

  return (
    <Shell title="Lab orders" subtitle="Investigations for this visit" actions={<BackToQueue />}>
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={context}>
        {(data) => (
          <ConsultFrame context={data} appointmentId={appointmentId}>
            <div className="grid gap-3 lg:grid-cols-[1.5fr_1fr]">
              <Panel
                title="Test catalogue"
                subtitle="Prices and turnaround are the clinic's own"
                padded={false}
                actions={
                  <div className="relative w-56">
                    <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      className={`${inputClass} pl-8`}
                      placeholder="Find a test"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                    />
                  </div>
                }
              >
                <DataState state={catalog}>
                  {() =>
                    byCategory.length === 0 ? (
                      <p className="px-4 py-10 text-center text-[13px] text-[var(--color-ink-muted)]">
                        No test matches that search.
                      </p>
                    ) : (
                      <div>
                        {byCategory.map(([category, list]) => (
                          <section key={category}>
                            <p className="border-b border-[var(--color-border)] bg-slate-50 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                              {titleCase(category)}
                            </p>
                            <ul className="divide-y divide-[var(--color-border)]">
                              {list.map((test) => {
                                const chosen = picked.includes(test.code);
                                return (
                                  <li key={test.id}>
                                    <button
                                      onClick={() => toggle(test.code)}
                                      className={
                                        chosen
                                          ? "flex w-full items-center justify-between gap-3 bg-emerald-50 px-4 py-2.5 text-left"
                                          : "flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left hover:bg-slate-50"
                                      }
                                    >
                                      <div className="min-w-0">
                                        <p className="truncate text-[12.5px] font-medium text-[var(--color-ink)]">
                                          {test.name}
                                        </p>
                                        <p className="tabular text-[11px] text-[var(--color-ink-subtle)]">
                                          {test.code} · {test.sample_type} · reported in {test.turnaround_hours}h
                                          {test.fasting_required ? " · fasting" : ""}
                                        </p>
                                      </div>
                                      <div className="flex shrink-0 items-center gap-2">
                                        <span className="tabular text-[12px] text-[var(--color-ink)]">
                                          {money(test.standard_fee_inr)}
                                        </span>
                                        {chosen && <Check size={14} className="text-emerald-600" />}
                                      </div>
                                    </button>
                                  </li>
                                );
                              })}
                            </ul>
                          </section>
                        ))}
                      </div>
                    )
                  }
                </DataState>
              </Panel>

              <div className="space-y-3">
                <Panel title="This order" subtitle={`${picked.length} test${picked.length === 1 ? "" : "s"} selected`}>
                  {picked.length === 0 ? (
                    <p className="flex items-center gap-2 py-8 text-[12.5px] text-[var(--color-ink-muted)]">
                      <FlaskConical size={15} className="text-slate-400" /> Choose tests from the catalogue.
                    </p>
                  ) : (
                    <>
                      <ul className="space-y-1.5">
                        {tests
                          .filter((test) => picked.includes(test.code))
                          .map((test) => (
                            <li key={test.code} className="flex items-baseline justify-between gap-2 text-[12.5px]">
                              <span className="truncate text-[var(--color-ink)]">{test.name}</span>
                              <span className="tabular shrink-0 text-[var(--color-ink-muted)]">
                                {money(test.standard_fee_inr)}
                              </span>
                            </li>
                          ))}
                      </ul>
                      <div className="mt-3 flex items-baseline justify-between border-t border-[var(--color-border)] pt-2 text-[13px] font-semibold">
                        <span>Billed to the patient</span>
                        <span className="tabular">{money(total)}</span>
                      </div>
                    </>
                  )}

                  <div className="mt-4">
                    <Button disabled={busy || picked.length === 0 || !data.consultation} onClick={() => void order()}>
                      <Send size={13} /> {busy ? "Raising" : "Raise the order"}
                    </Button>
                    <p className="mt-1.5 text-[11.5px] text-[var(--color-ink-muted)]">
                      The diagnostics bench collects the sample and publishes the report, which lands in the
                      patient's records and yours.
                    </p>
                  </div>
                </Panel>

                <Panel title="Already ordered this visit" padded={false}>
                  {data.labOrders.length === 0 ? (
                    <p className="px-4 py-6 text-center text-[12.5px] text-[var(--color-ink-muted)]">Nothing yet.</p>
                  ) : (
                    <ul className="divide-y divide-[var(--color-border)]">
                      {data.labOrders.map((order) => (
                        <li key={order.id} className="flex items-center justify-between gap-2 px-4 py-2.5">
                          <div className="min-w-0">
                            <p className="tabular text-[12.5px] font-medium text-[var(--color-ink)]">
                              {order.order_number}
                            </p>
                            <p className="text-[11px] text-[var(--color-ink-subtle)]">
                              {order.test_count} test{Number(order.test_count) === 1 ? "" : "s"} ·{" "}
                              {stamp(order.created_at)}
                            </p>
                          </div>
                          <Badge tone={tone.lab(order.status)}>{titleCase(order.status)}</Badge>
                        </li>
                      ))}
                    </ul>
                  )}
                </Panel>
              </div>
            </div>
          </ConsultFrame>
        )}
      </DataState>
    </Shell>
  );
}
