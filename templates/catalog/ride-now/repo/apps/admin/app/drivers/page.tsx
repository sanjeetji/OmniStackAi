"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Car, FileWarning, Star } from "lucide-react";
import { inr } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { DriverStatusBadge } from "@/components/status";
import { Badge, Empty, ErrorState, LoadingRows, PageHeader, Pager, Panel, Person, SearchBox, Segmented, Table, td, th } from "@/components/ui";
import type { DriverRow, DriverStatus } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const LIMIT = 25;
type Filter = "all" | DriverStatus;

export default function DriversPage() {
  return (
    <Shell>
      <Suspense fallback={<LoadingRows />}>
        <DriversView />
      </Suspense>
    </Shell>
  );
}

function DriversView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const raw = params.get("status");
  const status: Filter = raw === "pending" || raw === "approved" || raw === "suspended" ? raw : "all";
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      setQ(search.trim());
      setOffset(0);
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  const query = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
  if (status !== "all") query.set("status", status);
  if (q) query.set("q", q);
  const { data, error, loading, reload } = useApi<{ drivers: DriverRow[]; total: number }>(`/admin/drivers?${query.toString()}`);

  return (
    <>
      <PageHeader title="Drivers" description="Approve new drivers, review documents and keep an eye on quality." />
      <Panel>
        <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
          <Segmented
            label="Driver status"
            value={status}
            onChange={(next) => {
              setOffset(0);
              router.replace(next === "all" ? pathname : `${pathname}?status=${next}`, { scroll: false });
            }}
            options={[
              { value: "all", label: "All" },
              { value: "pending", label: "Pending review" },
              { value: "approved", label: "Approved" },
              { value: "suspended", label: "Suspended" },
            ]}
          />
          <div className="ml-auto w-full sm:w-auto">
            <SearchBox value={search} onChange={setSearch} placeholder="Name, plate or phone" label="Search drivers" />
          </div>
        </div>
        {error && !data ? (
          <div className="p-4"><ErrorState message={error} onRetry={reload} /></div>
        ) : !data ? (
          <LoadingRows label="Loading drivers" />
        ) : data.drivers.length === 0 ? (
          <Empty
            icon={<Car className="size-5" />}
            title={status === "pending" ? "No one is waiting for review" : "No drivers match"}
            body={status === "pending" ? "New applications from the driver app appear here with their documents." : "Try another status or search."}
          />
        ) : (
          <>
            <Table label="Drivers" className={loading ? "opacity-60" : undefined}>
              <thead>
                <tr>
                  <th className={th}>Driver</th>
                  <th className={th}>Vehicle</th>
                  <th className={th}>Status</th>
                  <th className={th}>Now</th>
                  <th className={`${th} text-right`}>Rating</th>
                  <th className={`${th} text-right`}>Acceptance</th>
                  <th className={`${th} text-right`}>Trips</th>
                  <th className={`${th} text-right`}>Wallet</th>
                </tr>
              </thead>
              <tbody>
                {data.drivers.map((d) => (
                  <tr key={d.id} className="hover:bg-sunken">
                    <td className={td}>
                      <Link href={`/drivers/${d.id}`} className="block"><Person name={d.full_name} color={d.avatar_color} sub={d.phone ?? d.email ?? undefined} /></Link>
                    </td>
                    <td className={td}>
                      <span className="block whitespace-nowrap">{d.vehicle_color} {d.vehicle_make} {d.vehicle_model}</span>
                      <span className="block font-mono text-xs text-muted">{d.plate} · {d.vehicle_type}</span>
                    </td>
                    <td className={td}>
                      <span className="flex flex-wrap items-center gap-1.5">
                        <DriverStatusBadge status={d.status} />
                        {d.docs_pending > 0 ? (
                          <Badge tone="warn"><FileWarning className="size-3" aria-hidden="true" />{d.docs_pending} docs</Badge>
                        ) : null}
                        {d.account_status === "suspended" ? <Badge tone="bad">Account suspended</Badge> : null}
                      </span>
                    </td>
                    <td className={td}>{d.online ? <Badge tone="ok" dot>Online</Badge> : <Badge>Offline</Badge>}{d.simulated ? <span className="ml-1.5 text-xs text-muted">sim</span> : null}</td>
                    <td className={`${td} num whitespace-nowrap text-right`}>
                      <Star className="mr-1 inline size-3.5 fill-brand text-brand" aria-hidden="true" />
                      {d.rating_avg.toFixed(2)} <span className="text-xs text-muted">({d.rating_count})</span>
                    </td>
                    <td className={`${td} num text-right ${d.acceptance_rate < 70 ? "text-bad" : ""}`}>{d.acceptance_rate}%</td>
                    <td className={`${td} num text-right`}>{d.trips}</td>
                    <td className={`${td} num text-right font-medium`}>{inr(d.balance)}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <Pager offset={offset} limit={LIMIT} total={data.total} onChange={setOffset} />
          </>
        )}
      </Panel>
    </>
  );
}
