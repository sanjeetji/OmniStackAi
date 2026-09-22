"use client";

import Link from "next/link";
import { useState } from "react";
import { LifeBuoy, MessageSquare } from "lucide-react";
import { relativeTime } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { PriorityBadge, TICKET_CATEGORY, TicketStatusBadge } from "@/components/status";
import { Badge, Empty, ErrorState, LoadingRows, PageHeader, Panel, Person, Segmented, Table, td, th } from "@/components/ui";
import { useAdminEvent } from "@/lib/session";
import type { TicketRow, TicketStatus } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type Filter = "all" | TicketStatus;

export default function TicketsPage() {
  return (
    <Shell>
      <TicketsView />
    </Shell>
  );
}

function TicketsView() {
  const [filter, setFilter] = useState<Filter>("open");
  const { data, error, loading, reload } = useApi<{ tickets: TicketRow[] }>(filter === "all" ? "/admin/tickets" : `/admin/tickets?status=${filter}`);
  useAdminEvent(["ticket.created", "ticket.updated"], reload);

  return (
    <>
      <PageHeader title="Support" description="Questions and complaints from riders and drivers, most urgent first. Safety reports are always urgent." />
      <Panel>
        <div className="border-b border-line p-3">
          <Segmented
            label="Ticket status"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "open", label: "Needs reply" },
              { value: "pending", label: "Waiting on user" },
              { value: "resolved", label: "Resolved" },
              { value: "all", label: "All" },
            ]}
          />
        </div>
        {error && !data ? (
          <div className="p-4"><ErrorState message={error} onRetry={reload} /></div>
        ) : !data || loading ? (
          <LoadingRows label="Loading tickets" />
        ) : data.tickets.length === 0 ? (
          <Empty icon={<LifeBuoy className="size-5" />} title={filter === "open" ? "Inbox zero" : "No tickets here"} body={filter === "open" ? "Every rider and driver has an answer. New tickets appear here instantly." : "Try another status."} />
        ) : (
          <Table label="Support tickets">
            <thead>
              <tr>
                <th className={th}>Ticket</th>
                <th className={th}>From</th>
                <th className={th}>Category</th>
                <th className={th}>Priority</th>
                <th className={th}>Status</th>
                <th className={`${th} text-right`}>Messages</th>
                <th className={`${th} text-right`}>Updated</th>
              </tr>
            </thead>
            <tbody>
              {data.tickets.map((t) => (
                <tr key={t.id} className="hover:bg-sunken">
                  <td className={`${td} max-w-80`}>
                    <Link href={`/tickets/${t.id}`} className="block">
                      <span className="font-mono text-xs font-semibold text-signal">{t.code}</span>
                      {t.trip_code ? <span className="ml-2 font-mono text-xs text-muted">trip {t.trip_code}</span> : null}
                      <span className="block truncate text-[13px] font-medium text-ink hover:underline">{t.subject}</span>
                    </Link>
                  </td>
                  <td className={td}><Person name={t.user_name} color={t.avatar_color} sub={<span className="capitalize">{t.user_role}</span>} /></td>
                  <td className={td}><Badge>{TICKET_CATEGORY[t.category] ?? t.category}</Badge></td>
                  <td className={td}><PriorityBadge priority={t.priority} /></td>
                  <td className={td}><TicketStatusBadge status={t.status} /></td>
                  <td className={`${td} num text-right`}><span className="inline-flex items-center gap-1"><MessageSquare className="size-3.5 text-muted" aria-hidden="true" />{t.messages}</span></td>
                  <td className={`${td} whitespace-nowrap text-right text-muted`}>{relativeTime(t.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Panel>
    </>
  );
}
