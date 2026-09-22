"use client";

import Link from "next/link";
import { useRef } from "react";
import { ArrowRight, Banknote, Car, CheckCircle2, LifeBuoy, Radar, Star } from "lucide-react";
import { inr, relativeTime } from "@ridenow/shared";
import { DailyChart, ShareBars } from "@/components/charts";
import { Shell } from "@/components/shell";
import { TripStatusBadge } from "@/components/status";
import { ErrorState, LinkButton, LoadingPage, Panel, Person, Stat, Table, change, td, th } from "@/components/ui";
import { useAdmin, useAdminEvent } from "@/lib/session";
import type { Dashboard } from "@/lib/types";
import { useApi, useInterval } from "@/lib/use-api";

export default function DashboardPage() {
  return (
    <Shell>
      <DashboardView />
    </Shell>
  );
}

function greeting(): string {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

function DashboardView() {
  const { user } = useAdmin();
  const { data, error, reload } = useApi<Dashboard>("/admin/dashboard");
  const pending = useRef<ReturnType<typeof setTimeout> | null>(null);
  useInterval(reload, 30_000);
  useAdminEvent(["trip.updated", "payout.requested", "ticket.created"], () => {
    if (pending.current) clearTimeout(pending.current);
    pending.current = setTimeout(reload, 2500);
  });

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  if (!data) return <LoadingPage label="Loading the dashboard" />;
  const { kpis } = data;
  const firstName = user?.full_name.split(" ")[0] ?? "";
  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });

  const queues = [
    { href: "/drivers?status=pending", icon: Car, label: "Drivers to review", value: kpis.drivers_pending, sub: "Documents waiting for approval" },
    { href: "/payouts", icon: Banknote, label: "Payouts due", value: kpis.payouts_due.count, sub: `${inr(kpis.payouts_due.amount)} requested` },
    { href: "/tickets", icon: LifeBuoy, label: "Open tickets", value: kpis.open_tickets, sub: "Riders and drivers waiting" },
  ];

  return (
    <div className="grid gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">{greeting()}, {firstName}</h1>
          <p className="text-[13px] text-muted">Bengaluru · {today}</p>
        </div>
        <LinkButton href="/live" variant="primary">
          <Radar className="size-4" aria-hidden="true" />
          Open live map
        </LinkButton>
      </header>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Trips today" value={kpis.trips_today} delta={deltaOf(kpis.trips_today, kpis.trips_yesterday, "vs yesterday")} />
        <Stat label="Gross bookings, 7 days" value={inr(Math.round(kpis.gmv_7d))} delta={deltaOf(kpis.gmv_7d, kpis.gmv_prev_7d, "vs previous 7 days")} />
        <Stat label="Platform revenue, 7 days" value={inr(Math.round(kpis.revenue_7d))} hint="Commission after promo discounts" />
        <Stat label="Completion rate, 7 days" value={`${kpis.completion_rate_7d}%`} hint="Requests that became trips" icon={<CheckCircle2 className="size-4" aria-hidden="true" />} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <Panel title="Last 14 days" description="Completed trips per day, with gross bookings and platform revenue" bodyClassName="p-4">
          <DailyChart
            caption="Completed trips, gross bookings and revenue per day for the last 14 days"
            labels={data.series.map((s) => s.day)}
            bars={{ name: "Trips", color: "var(--color-signal)", values: data.series.map((s) => s.trips) }}
            lines={[
              { name: "Gross bookings", color: "#d98a00", values: data.series.map((s) => s.gmv) },
              { name: "Revenue", color: "var(--color-ok)", values: data.series.map((s) => s.revenue) },
            ]}
            format={(v) => String(Math.round(v))}
            lineFormat={(v) => (v >= 1000 ? `₹${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : `₹${Math.round(v)}`)}
          />
        </Panel>
        <div className="grid content-start gap-5">
          <Panel title="Right now" bodyClassName="grid grid-cols-2 gap-px bg-line">
            {[
              ["Active trips", kpis.active_trips, "/trips?status=active"],
              ["Drivers online", kpis.drivers_online, "/live"],
              ["Riders, 7 days", kpis.active_riders_7d, "/riders"],
              ["Driver rating", kpis.avg_driver_rating === null ? "–" : kpis.avg_driver_rating.toFixed(2), "/drivers"],
            ].map(([label, value, href]) => (
              <Link key={String(label)} href={String(href)} className="bg-panel p-4 hover:bg-sunken">
                <p className="text-xs text-muted">{label}</p>
                <p className="num mt-1 flex items-center gap-1 text-xl font-semibold">
                  {label === "Driver rating" ? <Star className="size-4 fill-brand text-brand" aria-hidden="true" /> : null}
                  {value}
                </p>
              </Link>
            ))}
          </Panel>
          <Panel title="Needs attention">
            <ul className="divide-y divide-line">
              {queues.map(({ href, icon: Icon, label, value, sub }) => (
                <li key={href}>
                  <Link href={href} className="flex items-center gap-3 px-4 py-3 hover:bg-sunken">
                    <span className={value > 0 ? "grid size-8 place-items-center rounded-md bg-warn-soft text-warn" : "grid size-8 place-items-center rounded-md bg-ink/5 text-muted"}>
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[13px] font-medium">{label}</span>
                      <span className="block truncate text-xs text-muted">{sub}</span>
                    </span>
                    <span className="num text-lg font-semibold">{value}</span>
                    <ArrowRight className="size-4 text-muted" aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Vehicle mix" description="Completed trips in the last 30 days" bodyClassName="p-4">
          <ShareBars
            items={data.vehicle_mix.map((m) => ({ id: m.id, label: m.name, value: m.trips, sub: `${inr(Math.round(m.gmv))} gross bookings` }))}
            format={(v) => `${v} trips`}
          />
        </Panel>
        <Panel title="Top drivers this week" description="By earnings" actions={<LinkButton href="/drivers" size="sm">All drivers</LinkButton>}>
          <Table label="Top drivers this week">
            <thead>
              <tr>
                <th className={th}>Driver</th>
                <th className={`${th} text-right`}>Trips</th>
                <th className={`${th} text-right`}>Rating</th>
                <th className={`${th} text-right`}>Earnings</th>
              </tr>
            </thead>
            <tbody>
              {data.top_drivers.length === 0 ? (
                <tr><td className={`${td} text-muted`} colSpan={4}>No completed trips this week yet.</td></tr>
              ) : (
                data.top_drivers.map((d) => (
                  <tr key={d.id} className="hover:bg-sunken">
                    <td className={td}>
                      <Link href={`/drivers/${d.id}`} className="block"><Person name={d.name} color={d.avatar_color} sub={d.vehicle_type} /></Link>
                    </td>
                    <td className={`${td} num text-right`}>{d.trips}</td>
                    <td className={`${td} num text-right`}>{d.rating.toFixed(2)}</td>
                    <td className={`${td} num text-right font-semibold`}>{inr(d.earnings)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </Table>
        </Panel>
      </div>

      <Panel title="Latest requests" actions={<LinkButton href="/trips" size="sm">All trips</LinkButton>}>
        <Table label="Latest ride requests">
          <thead>
            <tr>
              <th className={th}>Trip</th>
              <th className={th}>Rider</th>
              <th className={th}>Route</th>
              <th className={th}>Status</th>
              <th className={`${th} text-right`}>Fare</th>
              <th className={`${th} text-right`}>Requested</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_trips.map((trip) => (
              <tr key={trip.id} className="hover:bg-sunken">
                <td className={td}><Link href={`/trips/${trip.id}`} className="font-mono text-xs font-semibold text-signal hover:underline">{trip.code}</Link></td>
                <td className={td}>{trip.rider?.name ?? "–"}</td>
                <td className={`${td} max-w-72 truncate text-ink-2`}>{trip.pickup.name} → {trip.drop.name}</td>
                <td className={td}><TripStatusBadge status={trip.status} /></td>
                <td className={`${td} num text-right`}>{inr(trip.fare_final ?? trip.fare_estimate)}</td>
                <td className={`${td} whitespace-nowrap text-right text-muted`}>{relativeTime(trip.requested_at)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Panel>
    </div>
  );
}

function deltaOf(current: number, previous: number, label: string) {
  const value = change(current, previous);
  return value === null ? null : { value, label };
}
