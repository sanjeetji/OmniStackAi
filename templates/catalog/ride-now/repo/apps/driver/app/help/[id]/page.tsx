"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Send } from "lucide-react";
import { ApiError, dateTimeLabel, type Ticket } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Avatar, Button, Loading, Notice, Panel, Tag, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useDriver } from "@/lib/driver";

export default function TicketPage() {
  const { id } = useParams<{ id: string }>();
  const { profile } = useDriver();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api.get<Ticket>(`/support/tickets/${id}`).then(setTicket).catch(() => setError("This request was not found.")), [id]);
  useEffect(() => void load(), [load]);

  return (
    <Shell title="Support request">
      <Link href="/help" className="mb-3 inline-flex items-center gap-1 text-sm font-semibold text-fg-muted hover:text-fg"><ArrowLeft className="size-4" aria-hidden="true" /> Help</Link>
      {error && !ticket ? <Notice>{error}</Notice> : !ticket ? <Loading /> : (
        <Panel className="p-4">
          <div className="flex items-start justify-between gap-3 border-b border-line/60 pb-3">
            <div className="min-w-0">
              <p className="text-xs text-fg-muted">{ticket.code}{ticket.trip_code ? ` · trip ${ticket.trip_code}` : ""}</p>
              <h2 className="text-lg font-extrabold">{ticket.subject}</h2>
            </div>
            <Tag tone={ticket.status === "resolved" ? "go" : ticket.status === "pending" ? "info" : "warn"}>{ticket.status === "pending" ? "Your reply" : ticket.status === "resolved" ? "Resolved" : "With support"}</Tag>
          </div>
          <ol className="grid gap-3 py-4">
            {ticket.messages?.map((message) => {
              const mine = message.author_role !== "admin";
              return (
                <li key={message.id} className={cx("flex gap-2", mine && "flex-row-reverse")}>
                  <Avatar name={mine ? profile?.full_name ?? "You" : "RideNow Support"} color={mine ? message.avatar_color : "#1f2937"} size={30} />
                  <div className={cx("max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm", mine ? "rounded-tr-sm bg-go-soft" : "rounded-tl-sm bg-raised")}>
                    <p className="text-[11px] font-semibold text-fg-muted">{mine ? "You" : "RideNow Support"} · {dateTimeLabel(message.created_at)}</p>
                    <p className="mt-1 whitespace-pre-line">{message.body}</p>
                  </div>
                </li>
              );
            })}
          </ol>
          <form
            className="flex items-end gap-2 border-t border-line/60 pt-3"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!reply.trim()) return;
              setBusy(true);
              setError(null);
              try {
                await api.post(`/support/tickets/${id}/messages`, { body: reply });
                setReply("");
                await load();
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Couldn't send.");
              } finally {
                setBusy(false);
              }
            }}
          >
            <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={2} aria-label="Reply" placeholder={ticket.status === "resolved" ? "Reply to reopen this request" : "Write a reply"} className="min-h-12 flex-1 rounded-2xl border border-line bg-raised p-3 text-base outline-none focus:border-go" />
            <Button type="submit" busy={busy} disabled={!reply.trim()} aria-label="Send reply"><Send className="size-4" aria-hidden="true" /></Button>
          </form>
          {error ? <div className="mt-3"><Notice>{error}</Notice></div> : null}
        </Panel>
      )}
    </Shell>
  );
}
