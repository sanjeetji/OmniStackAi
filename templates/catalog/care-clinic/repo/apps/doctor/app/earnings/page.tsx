"use client";

import { useState } from "react";
import { Download, IndianRupee, TrendingUp, UserMinus } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, Stat } from "../../components/ui";
import { TrendChart, ShareBars } from "../../components/charts";
import { useApi } from "../../lib/use-api";
import { count, day, dayShort, money, num, percent, titleCase, tone } from "../../lib/format";

const RANGES = [7, 30, 90];

export default function Earnings() {
  const [days, setDays] = useState(30);
  const earnings = useApi(() => defaultApiClient.getDoctorEarnings(days), [days]);

  function exportCsv(rows: { scheduled_date: string; consultations: string; earned: string }[]) {
    const body = rows
      .map((row) => [String(row.scheduled_date).slice(0, 10), row.consultations, row.earned].join(","))
      .join("\n");
    const blob = new Blob([`Date,Consultations,Earned\n${body}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `careclinic-earnings-${days}d.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Shell
      title="Earnings"
      subtitle="What you billed, and what the clinic has collected"
      actions={
        <div className="flex gap-1.5">
          {RANGES.map((range) => (
            <button
              key={range}
              onClick={() => setDays(range)}
              className={
                days === range
                  ? "rounded-lg bg-[var(--color-emerald-brand)] px-2.5 py-1 text-[12px] font-semibold text-white"
                  : "rounded-lg border border-[var(--color-border)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)] hover:bg-slate-50"
              }
            >
              {range} days
            </button>
          ))}
        </div>
      }
    >
      <DataState state={earnings}>
        {(data) => {
          const totals = data.totals;
          const consultations = num(totals.consultations);

          return (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Stat label="Billed" value={money(totals.gross)} tone="good" hint={`${count(consultations)} consultations`} icon={<IndianRupee size={15} />} />
                <Stat label="Collected" value={money(totals.settled)} hint="Settled by the clinic" icon={<TrendingUp size={15} />} />
                <Stat
                  label="Still at the desk"
                  value={money(totals.outstanding)}
                  tone={num(totals.outstanding) > 0 ? "alert" : "plain"}
                  hint="Patients yet to pay"
                />
                <Stat
                  label="Did not arrive"
                  value={count(totals.no_show)}
                  tone={num(totals.no_show) > 0 ? "danger" : "plain"}
                  hint={`${count(totals.cancelled)} cancelled`}
                  icon={<UserMinus size={15} />}
                />
              </div>

              <Panel
                className="mt-3"
                title="Day by day"
                subtitle="Bars are consultations; the amber tick is what you billed, in hundreds"
                actions={
                  <Button variant="quiet" size="sm" onClick={() => exportCsv(data.daily)}>
                    <Download size={13} /> CSV
                  </Button>
                }
              >
                <TrendChart
                  series={data.daily.map((row) => ({
                    label: dayShort(row.scheduled_date),
                    value: num(row.consultations),
                    secondary: num(row.earned) / 100,
                  }))}
                  height={180}
                />
              </Panel>

              <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1.6fr]">
                <Panel title="In clinic or by video" subtitle="Where the money came from">
                  <ShareBars
                    rows={data.byType.map((row) => ({
                      label: row.appointment_type === "video" ? "Video visits" : "In clinic",
                      value: num(row.earned),
                      note: `${count(row.consultations)} consultations`,
                    }))}
                    format={(value) => money(value)}
                  />
                  <dl className="mt-4 space-y-1.5 border-t border-[var(--color-border)] pt-3 text-[12.5px]">
                    <div className="flex justify-between">
                      <dt className="text-[var(--color-ink-muted)]">Average per consultation</dt>
                      <dd className="tabular font-semibold">
                        {consultations > 0 ? money(Math.round(num(totals.gross) / consultations)) : "—"}
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-[var(--color-ink-muted)]">Collected of billed</dt>
                      <dd className="tabular font-semibold">{percent(num(totals.settled), num(totals.gross))}</dd>
                    </div>
                  </dl>
                </Panel>

                <Panel title="Recent consultations" subtitle="Newest first" padded={false}>
                  {data.recent.length === 0 ? (
                    <p className="px-4 py-10 text-center text-[13px] text-[var(--color-ink-muted)]">
                      No completed consultation yet.
                    </p>
                  ) : (
                    <Table head={["Date", "Patient", "Type", "Fee", "Invoice", "Payment"]}>
                      {data.recent.map((row) => (
                        <Row key={row.id}>
                          <Cell mono muted>{day(String(row.scheduled_date))}</Cell>
                          <Cell>{row.patient_name}</Cell>
                          <Cell>
                            <Badge tone={row.appointment_type === "video" ? "signal" : "neutral"}>
                              {row.appointment_type === "video" ? "Video" : "In clinic"}
                            </Badge>
                          </Cell>
                          <Cell align="right">{money(row.fee_amount)}</Cell>
                          <Cell mono muted>{row.invoice_number ?? "—"}</Cell>
                          <Cell>
                            <Badge tone={tone.payment(row.payment_status)}>
                              {titleCase(row.payment_status ?? "none")}
                            </Badge>
                          </Cell>
                        </Row>
                      ))}
                    </Table>
                  )}
                </Panel>
              </div>
            </>
          );
        }}
      </DataState>
    </Shell>
  );
}
