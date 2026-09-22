"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { dateLabel, dateTimeLabel, inr, relativeTime, signedInr } from "@ridenow/shared";
import { AccountStatusButton, WalletAdjustButton } from "@/components/account-actions";
import { Shell } from "@/components/shell";
import { LEDGER_KIND, TripStatusBadge } from "@/components/status";
import { Avatar, Badge, ErrorState, KeyValues, LoadingPage, PageHeader, Panel, Stat, Table, td, th } from "@/components/ui";
import type { RiderDetail } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function RiderPage() {
  return (
    <Shell>
      <RiderView />
    </Shell>
  );
}

function RiderView() {
  const { id } = useParams<{ id: string }>();
  const { data: rider, error, reload } = useApi<RiderDetail>(`/admin/riders/${id}`);

  if (error && !rider) return <ErrorState message={error} onRetry={reload} />;
  if (!rider) return <LoadingPage label="Loading the rider" />;

  const completed = rider.trips.filter((t) => t.status === "completed");
  const spent = completed.reduce((sum, t) => sum + (t.fare_final ?? 0), 0);
  const cancelled = rider.trips.filter((t) => t.status === "cancelled" && t.cancelled_by === "rider").length;

  return (
    <>
      <PageHeader
        back={{ href: "/riders", label: "All riders" }}
        title={
          <span className="flex flex-wrap items-center gap-3">
            <Avatar name={rider.full_name} color={rider.avatar_color} size={34} />
            {rider.full_name}
            {rider.status === "active" ? <Badge tone="ok" dot>Active</Badge> : <Badge tone="bad" dot>Suspended</Badge>}
          </span>
        }
        description={`Rider since ${dateLabel(rider.created_at)}`}
        actions={
          <>
            <WalletAdjustButton userId={rider.id} name={rider.full_name} balance={rider.balance} onDone={reload} />
            <AccountStatusButton userId={rider.id} name={rider.full_name} status={rider.status} onDone={reload} />
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Wallet balance" value={inr(rider.balance)} />
        <Stat label="Recent trips" value={rider.trips.length} hint={`${completed.length} completed`} />
        <Stat label="Spent on recent trips" value={inr(spent)} />
        <Stat label="Rider cancellations" value={cancelled} hint="In the recent trips" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_340px]">
        <div className="grid content-start gap-5">
          <Panel title="Recent trips" description="The latest 20">
            {rider.trips.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-muted">No trips yet.</p>
            ) : (
              <Table label="Recent trips">
                <thead>
                  <tr>
                    <th className={th}>Trip</th>
                    <th className={th}>When</th>
                    <th className={th}>Route</th>
                    <th className={th}>Driver</th>
                    <th className={th}>Status</th>
                    <th className={`${th} text-right`}>Fare</th>
                  </tr>
                </thead>
                <tbody>
                  {rider.trips.map((t) => (
                    <tr key={t.id} className="hover:bg-sunken">
                      <td className={td}><Link href={`/trips/${t.id}`} className="font-mono text-xs font-semibold text-signal hover:underline">{t.code}</Link></td>
                      <td className={`${td} whitespace-nowrap text-ink-2`}>{dateTimeLabel(t.requested_at)}</td>
                      <td className={`${td} max-w-60 truncate`}>{t.pickup.name} → {t.drop.name}</td>
                      <td className={`${td} whitespace-nowrap`}>{t.driver?.name ?? "–"}</td>
                      <td className={td}><TripStatusBadge status={t.status} /></td>
                      <td className={`${td} num text-right`}>{inr(t.fare_final ?? t.fare_estimate)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Panel>
          <Panel title="Wallet ledger" description="The latest 20 lines">
            {rider.ledger.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-muted">No wallet activity yet.</p>
            ) : (
              <Table label="Wallet ledger">
                <thead>
                  <tr>
                    <th className={th}>When</th>
                    <th className={th}>Kind</th>
                    <th className={th}>Reference</th>
                    <th className={th}>Note</th>
                    <th className={`${th} text-right`}>Amount</th>
                    <th className={`${th} text-right`}>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {rider.ledger.map((line) => (
                    <tr key={line.id}>
                      <td className={`${td} whitespace-nowrap text-ink-2`}>{dateTimeLabel(line.created_at)}</td>
                      <td className={td}>{LEDGER_KIND[line.kind] ?? line.kind}</td>
                      <td className={`${td} font-mono text-xs`}>{line.reference || "–"}</td>
                      <td className={`${td} max-w-56 truncate text-ink-2`}>{line.note || "–"}</td>
                      <td className={`${td} num text-right font-medium ${line.amount < 0 ? "text-bad" : "text-ok"}`}>{signedInr(line.amount)}</td>
                      <td className={`${td} num text-right`}>{inr(line.balance_after)}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Panel>
        </div>
        <div className="grid content-start gap-5">
          <Panel title="Contact" bodyClassName="p-4">
            <KeyValues
              items={[
                ["Email", rider.email ?? "–"],
                ["Phone", rider.phone ?? "–"],
                ["Joined", dateLabel(rider.created_at)],
                ["Last sign-in", rider.last_login_at ? relativeTime(rider.last_login_at) : "Never"],
              ]}
            />
          </Panel>
          <Panel title="Support tickets">
            {rider.tickets.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-muted">No tickets.</p>
            ) : (
              <ul className="divide-y divide-line">
                {rider.tickets.map((t) => (
                  <li key={t.id}>
                    <Link href={`/tickets/${t.id}`} className="block px-4 py-2.5 hover:bg-sunken">
                      <span className="flex items-center justify-between gap-2">
                        <span className="font-mono text-xs font-semibold">{t.code}</span>
                        <Badge tone={t.status === "resolved" ? "ok" : t.status === "pending" ? "warn" : "bad"} className="capitalize">{t.status}</Badge>
                      </span>
                      <span className="mt-0.5 block truncate text-[13px]">{t.subject}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </>
  );
}
