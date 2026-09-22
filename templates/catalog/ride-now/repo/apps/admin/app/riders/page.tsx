"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { dateLabel, inr, relativeTime } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Badge, Empty, ErrorState, LoadingRows, PageHeader, Pager, Panel, Person, SearchBox, Table, td, th } from "@/components/ui";
import type { RiderRow } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const LIMIT = 25;

export default function RidersPage() {
  return (
    <Shell>
      <RidersView />
    </Shell>
  );
}

function RidersView() {
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

  const { data, error, loading, reload } = useApi<{ riders: RiderRow[]; total: number }>(
    `/admin/riders?limit=${LIMIT}&offset=${offset}${q ? `&q=${encodeURIComponent(q)}` : ""}`,
  );

  return (
    <>
      <PageHeader title="Riders" description="Everyone who books rides, with their wallet, trips and spend." />
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line p-3">
          <p className="num text-[13px] text-muted">{data ? `${data.total} riders` : " "}</p>
          <SearchBox value={search} onChange={setSearch} placeholder="Name, email or phone" label="Search riders" />
        </div>
        {error && !data ? (
          <div className="p-4"><ErrorState message={error} onRetry={reload} /></div>
        ) : !data ? (
          <LoadingRows label="Loading riders" />
        ) : data.riders.length === 0 ? (
          <Empty icon={<Users className="size-5" />} title={q ? "No riders match" : "No riders yet"} body={q ? "Try a different name, email or phone number." : "Riders appear here when they sign up in the rider app."} />
        ) : (
          <>
            <Table label="Riders" className={loading ? "opacity-60" : undefined}>
              <thead>
                <tr>
                  <th className={th}>Rider</th>
                  <th className={th}>Phone</th>
                  <th className={th}>Status</th>
                  <th className={`${th} text-right`}>Trips</th>
                  <th className={`${th} text-right`}>Spent</th>
                  <th className={`${th} text-right`}>Rating</th>
                  <th className={`${th} text-right`}>Wallet</th>
                  <th className={th}>Joined</th>
                  <th className={th}>Last seen</th>
                </tr>
              </thead>
              <tbody>
                {data.riders.map((r) => (
                  <tr key={r.id} className="hover:bg-sunken">
                    <td className={td}>
                      <Link href={`/riders/${r.id}`} className="block"><Person name={r.full_name} color={r.avatar_color} sub={r.email ?? undefined} /></Link>
                    </td>
                    <td className={`${td} whitespace-nowrap text-ink-2`}>{r.phone ?? "–"}</td>
                    <td className={td}>{r.status === "active" ? <Badge tone="ok" dot>Active</Badge> : <Badge tone="bad" dot>Suspended</Badge>}</td>
                    <td className={`${td} num text-right`}>{r.trips}</td>
                    <td className={`${td} num text-right`}>{inr(r.spent)}</td>
                    <td className={`${td} num text-right`}>{r.rating === null ? "–" : r.rating.toFixed(2)}</td>
                    <td className={`${td} num text-right font-medium`}>{inr(r.balance)}</td>
                    <td className={`${td} whitespace-nowrap text-ink-2`}>{dateLabel(r.created_at)}</td>
                    <td className={`${td} whitespace-nowrap text-muted`}>{r.last_login_at ? relativeTime(r.last_login_at) : "Never"}</td>
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
