"use client";

import { useState } from "react";
import { CalendarRange, Download, TrendingUp } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Button, DataState, Stat } from "../../components/ui";
import { TrendChart, ShareBars } from "../../components/charts";
import { useApi } from "../../lib/use-api";
import { count, dayShort, money, num, percent, titleCase } from "../../lib/format";

const RANGES = [7, 30, 90];

export default function Reports() {
  const [days, setDays] = useState(30);
  const reports = useApi(() => defaultApiClient.getClinicReports(days), [days]);

  function exportCsv(rows: { scheduled_date: string; booked: string; completed: string; no_show: string; cancelled: string; revenue: string }[]) {
    const header = "Date,Booked,Completed,No show,Cancelled,Revenue";
    const body = rows
      .map((row) =>
        [String(row.scheduled_date).slice(0, 10), row.booked, row.completed, row.no_show, row.cancelled, row.revenue].join(",")
      )
      .join("\n");
    const blob = new Blob([`${header}\n${body}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `careclinic-footfall-${days}d.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Shell
      title="Reports"
      subtitle="Footfall, specialty mix, no-shows and how the money came in"
      actions={
        <div className="flex gap-1.5">
          {RANGES.map((range) => (
            <button
              key={range}
              onClick={() => setDays(range)}
              className={
                days === range
                  ? "rounded-md bg-[var(--color-signal)] px-2.5 py-1 text-[12px] font-semibold text-white"
                  : "rounded-md border border-[var(--color-border-strong)] bg-white px-2.5 py-1 text-[12px] font-medium text-[var(--color-ink-muted)] hover:bg-slate-50"
              }
            >
              {range} days
            </button>
          ))}
        </div>
      }
    >
      <DataState state={reports}>
        {(data) => {
          const total = num(data.totals.total);
          const noShow = num(data.totals.no_show);
          const revenue = data.daily.reduce((sum, row) => sum + num(row.revenue), 0);

          return (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Stat label={`Visits in ${days} days`} value={count(total)} hint={`${count(data.totals.unique_patients)} distinct patients`} icon={<CalendarRange size={15} />} />
                <Stat label="Revenue billed" value={money(revenue)} tone="good" icon={<TrendingUp size={15} />} />
                <Stat
                  label="Did not arrive"
                  value={percent(noShow, total)}
                  tone={noShow / Math.max(total, 1) > 0.05 ? "alert" : "plain"}
                  hint={`${count(noShow)} no-shows, ${count(data.totals.cancelled)} cancellations`}
                />
                <Stat
                  label="Seen by video"
                  value={percent(num(data.totals.video), total)}
                  tone="signal"
                  hint={`${count(data.totals.video)} video, ${count(data.totals.in_clinic)} in clinic`}
                />
              </div>

              <Panel
                className="mt-3"
                title="Daily footfall"
                subtitle="Bars are visits booked; the amber tick is the revenue in thousands"
                actions={
                  <Button variant="quiet" size="sm" onClick={() => exportCsv(data.daily)}>
                    <Download size={13} /> CSV
                  </Button>
                }
              >
                <TrendChart
                  series={data.daily.map((row) => ({
                    label: dayShort(row.scheduled_date),
                    value: num(row.booked),
                    secondary: num(row.revenue) / 1000,
                  }))}
                  height={190}
                />
              </Panel>

              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                <Panel title="Where the visits went" subtitle="By specialty">
                  <ShareBars
                    rows={data.specialties.map((row) => ({
                      label: row.specialty,
                      value: num(row.visits),
                      note: `${money(row.revenue)} billed`,
                    }))}
                  />
                </Panel>

                <Panel title="How patients paid" subtitle="Invoices raised in the window">
                  <ShareBars
                    rows={data.payments.map((row) => ({
                      label: titleCase(row.payment_method),
                      value: num(row.collected),
                      note: `${count(row.invoices)} invoices`,
                    }))}
                    format={(value) => money(value)}
                  />
                </Panel>
              </div>

              <Panel className="mt-3" title="By doctor" subtitle="Busiest first" padded={false}>
                <Table head={["Doctor", "Room", "Visits", "No-shows", "No-show rate", "Revenue", "Rating"]}>
                  {data.doctors.map((row) => (
                    <Row key={row.doctor_name}>
                      <Cell>{row.doctor_name}</Cell>
                      <Cell muted>{row.room_number ?? "—"}</Cell>
                      <Cell align="right">{count(row.visits)}</Cell>
                      <Cell align="right" muted>{count(row.no_show)}</Cell>
                      <Cell align="right" muted>{percent(num(row.no_show), num(row.visits))}</Cell>
                      <Cell align="right">{money(row.revenue)}</Cell>
                      <Cell align="right" muted>{Number(row.rating_avg).toFixed(2)}</Cell>
                    </Row>
                  ))}
                </Table>
              </Panel>
            </>
          );
        }}
      </DataState>
    </Shell>
  );
}
