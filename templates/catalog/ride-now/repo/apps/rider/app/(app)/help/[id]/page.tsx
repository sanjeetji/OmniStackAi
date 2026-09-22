"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Send } from "lucide-react";
import { ApiError, dateTimeLabel, type Ticket } from "@ridenow/shared";
import { AppShell } from "@/components/app-shell";
import { Alert, Avatar, Badge, Button, Card, Spinner, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function TicketPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useSession();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api.get<Ticket>(`/support/tickets/${id}`).then(setTicket).catch(() => setError("This request was not found.")), [id]);
  useEffect(() => void load(), [load]);

  return (
    <AppShell>
      <Link href="/help" className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-muted hover:text-ink"><ArrowLeft className="size-4" aria-hidden="true" /> Help centre</Link>
      {error && !ticket ? <Alert>{error}</Alert> : !ticket ? <Spinner /> : (
        <Card className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-4">
            <div>
              <p className="text-sm text-muted">{ticket.code}{ticket.trip_code ? ` · trip ${ticket.trip_code}` : ""}</p>
              <h1 className="text-2xl font-extrabold">{ticket.subject}</h1>
            </div>
            <Badge tone={ticket.status === "resolved" ? "success" : ticket.status === "pending" ? "teal" : "amber"}>{ticket.status === "pending" ? "Awaiting your reply" : ticket.status === "resolved" ? "Resolved" : "With our team"}</Badge>
          </div>
          <ol className="grid gap-4 py-5">
            {ticket.messages?.map((message) => {
              const mine = message.author_role !== "admin";
              return (
                <li key={message.id} className={cx("flex gap-3", mine && "flex-row-reverse")}>
                  <Avatar name={mine ? user?.full_name ?? "You" : "RideNow Support"} color={mine ? message.avatar_color : "#0B1B2B"} size={34} />
                  <div className={cx("max-w-[80%] rounded-3xl px-4 py-3 text-sm", mine ? "rounded-tr-md bg-amber-soft" : "rounded-tl-md bg-canvas")}>
                    <p className="text-xs font-semibold text-muted">{mine ? "You" : "RideNow Support"} · {dateTimeLabel(message.created_at)}</p>
                    <p className="mt-1 whitespace-pre-line">{message.body}</p>
                  </div>
                </li>
              );
            })}
          </ol>
          <form
            className="flex items-end gap-2 border-t border-line pt-4"
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
            <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={2} placeholder={ticket.status === "resolved" ? "Reply to reopen this request" : "Write a reply"} aria-label="Reply" className="min-h-12 flex-1 rounded-2xl border border-line p-3 text-sm outline-none focus:border-ink" />
            <Button type="submit" busy={busy} disabled={!reply.trim()} aria-label="Send reply"><Send className="size-4" aria-hidden="true" /></Button>
          </form>
          {error ? <div className="mt-3"><Alert>{error}</Alert></div> : null}
        </Card>
      )}
    </AppShell>
  );
}
