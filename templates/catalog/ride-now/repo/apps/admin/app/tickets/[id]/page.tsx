"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Send } from "lucide-react";
import { dateTimeLabel, relativeTime } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { PriorityBadge, TICKET_CATEGORY, TicketStatusBadge } from "@/components/status";
import { Avatar, Badge, Button, ErrorState, KeyValues, LoadingPage, Notice, PageHeader, Panel, Select, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin, useAdminEvent } from "@/lib/session";
import type { TicketDetail, TicketPriority, TicketStatus } from "@/lib/types";
import { errorText, useApi } from "@/lib/use-api";

export default function TicketPage() {
  return (
    <Shell>
      <TicketView />
    </Shell>
  );
}

const CANNED = [
  { label: "Looking into it", text: "Thanks for letting us know. I'm looking into this now and will update you shortly." },
  { label: "Refund issued", text: "I've refunded the fare to your RideNow wallet. It should show in your wallet right away." },
  { label: "Lost item", text: "We've contacted the driver about your item and will share their reply here as soon as we hear back." },
  { label: "Driver feedback", text: "Thank you for the feedback. We've shared it with the driver and our quality team will follow up." },
];

function TicketView() {
  const { id } = useParams<{ id: string }>();
  const { toast, refreshQueues } = useAdmin();
  const { data: ticket, error, reload } = useApi<TicketDetail>(`/support/tickets/${id}`);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const thread = useRef<HTMLOListElement>(null);
  useAdminEvent(["ticket.updated"], (_type, data: { id: string }) => {
    if (data.id === id) reload();
  });
  // Keep the newest message in view inside the thread, without scrolling the page.
  useEffect(() => {
    const el = thread.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [ticket?.messages.length]);

  if (error && !ticket) return <ErrorState message={error} onRetry={reload} />;
  if (!ticket) return <LoadingPage label="Loading the ticket" />;

  const profile = ticket.user_role === "driver" ? `/drivers/${ticket.user_id}` : ticket.user_role === "rider" ? `/riders/${ticket.user_id}` : null;

  async function send() {
    setSending(true);
    setActionError(null);
    try {
      await api.post(`/support/tickets/${id}/messages`, { body: reply.trim() });
      setReply("");
      toast(`Reply sent to ${ticket!.user_name}`);
      refreshQueues();
      reload();
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setSending(false);
    }
  }

  async function update(status: TicketStatus, priority: TicketPriority) {
    setSaving(true);
    setActionError(null);
    try {
      await api.patch(`/admin/tickets/${id}`, { status, priority });
      toast(status === "resolved" && ticket!.status !== "resolved" ? `${ticket!.code} resolved` : `${ticket!.code} updated`);
      refreshQueues();
      reload();
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        back={{ href: "/tickets", label: "Support" }}
        title={ticket.subject}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono">{ticket.code}</span>
            <TicketStatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
            <Badge>{TICKET_CATEGORY[ticket.category] ?? ticket.category}</Badge>
          </span>
        }
        actions={
          ticket.status !== "resolved" ? (
            <Button variant="ok" busy={saving} onClick={() => void update("resolved", ticket.priority)}>
              <CheckCircle2 className="size-4" aria-hidden="true" />
              Resolve
            </Button>
          ) : (
            <Button variant="secondary" busy={saving} onClick={() => void update("open", ticket.priority)}>Reopen</Button>
          )
        }
      />
      <div className="grid gap-5 xl:grid-cols-[1fr_320px]">
        <Panel title="Conversation" description={`${ticket.messages.length} messages`}>
          <ol ref={thread} className="grid max-h-[55vh] gap-4 overflow-y-auto px-4 py-4">
            {ticket.messages.map((m) => {
              const ops = m.author_role === "admin";
              return (
                <li key={m.id} className={cx("flex gap-2.5", ops && "flex-row-reverse")}>
                  <Avatar name={m.author_name} color={m.avatar_color} size={28} />
                  <div className={cx("max-w-[75%] rounded-box px-3.5 py-2.5 text-[13px] leading-relaxed", ops ? "bg-signal text-white" : "bg-sunken text-ink")}>
                    <p className={cx("mb-0.5 text-xs font-semibold", ops ? "text-white/80" : "text-muted")}>
                      {m.author_name}{ops ? " · RideNow support" : ""} · {relativeTime(m.created_at)}
                    </p>
                    <p className="whitespace-pre-line">{m.body}</p>
                  </div>
                </li>
              );
            })}
          </ol>
          <div className="grid gap-2 border-t border-line p-4">
            <div className="flex flex-wrap gap-1.5" aria-label="Canned replies">
              {CANNED.map((c) => (
                <button key={c.label} type="button" onClick={() => setReply(c.text)} className="rounded-full border border-line-strong px-2.5 py-1 text-xs text-ink-2 hover:border-signal hover:text-signal">
                  {c.label}
                </button>
              ))}
            </div>
            <label htmlFor="reply" className="sr-only">Reply to {ticket.user_name}</label>
            <textarea
              id="reply"
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && reply.trim()) void send();
              }}
              rows={3}
              maxLength={2000}
              placeholder={`Reply to ${ticket.user_name}. They are notified in the app.`}
              className="w-full rounded-box border border-line-strong bg-panel px-3 py-2 text-[13px] outline-none focus:border-signal focus:ring-3 focus:ring-signal/20"
            />
            {actionError ? <Notice tone="bad">{actionError}</Notice> : null}
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-muted">Sending a reply marks the ticket “waiting on user”. ⌘/Ctrl + Enter sends.</p>
              <Button busy={sending} disabled={!reply.trim()} onClick={() => void send()}>
                <Send className="size-4" aria-hidden="true" />
                Send reply
              </Button>
            </div>
          </div>
        </Panel>
        <div className="grid content-start gap-5">
          <Panel title="Details" bodyClassName="grid gap-4 p-4">
            <KeyValues
              items={[
                ["From", profile ? <Link key="u" href={profile} className="text-signal hover:underline">{ticket.user_name}</Link> : ticket.user_name],
                ["Role", <span key="r" className="capitalize">{ticket.user_role}</span>],
                ["Trip", ticket.trip_id && ticket.trip_code ? <Link key="t" href={`/trips/${ticket.trip_id}`} className="font-mono text-signal hover:underline">{ticket.trip_code}</Link> : "–"],
                ["Opened", dateTimeLabel(ticket.created_at)],
                ["Updated", relativeTime(ticket.updated_at)],
              ]}
            />
            <Select
              label="Priority"
              value={ticket.priority}
              disabled={saving}
              onChange={(e) => void update(ticket.status, e.target.value as TicketPriority)}
              options={[
                { value: "urgent", label: "Urgent" },
                { value: "high", label: "High" },
                { value: "normal", label: "Normal" },
                { value: "low", label: "Low" },
              ]}
            />
            <Select
              label="Status"
              value={ticket.status}
              disabled={saving}
              onChange={(e) => void update(e.target.value as TicketStatus, ticket.priority)}
              options={[
                { value: "open", label: "Open, needs a reply" },
                { value: "pending", label: "Waiting on user" },
                { value: "resolved", label: "Resolved" },
              ]}
            />
          </Panel>
        </div>
      </div>
    </>
  );
}
