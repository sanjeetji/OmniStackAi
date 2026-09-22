"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ChevronRight, LifeBuoy, MessageSquarePlus, PhoneCall } from "lucide-react";
import { ApiError, relativeTime, type Ticket, type Trip } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Button, Empty, Field, Loading, Notice, Panel, Sheet, Tag, cx } from "@/components/ui";
import { api } from "@/lib/api";

const CATEGORIES = [
  { value: "payment", label: "Earnings & payouts" },
  { value: "safety", label: "Safety" },
  { value: "lost_item", label: "Rider left an item" },
  { value: "driver", label: "Account & documents" },
  { value: "app", label: "App problem" },
  { value: "other", label: "Something else" },
];

const FAQ = [
  ["When do I get paid?", "Wallet trips are credited the moment the ride completes. Withdraw to your bank any day once you have the minimum payout; it usually arrives within a day."],
  ["How does commission work on cash trips?", "You keep the cash. RideNow's commission is taken from your wallet, so your wallet can go below zero until your next online-paid trip."],
  ["Why am I not getting ride requests?", "Check you're online and your documents are verified. Requests go to the nearest drivers first, so head towards a surge zone on the Home map."],
  ["The rider doesn't know their PIN", "The PIN is shown on the rider's trip screen. Don't start the ride without it; it confirms you picked up the right person."],
  ["Can I cancel after accepting?", "Yes, but cancellations lower your acceptance score. If the rider doesn't turn up, wait at the pickup before cancelling."],
];

export default function HelpPage() {
  return (
    <Shell title="Help">
      <Suspense fallback={<Loading />}>
        <HelpCentre />
      </Suspense>
    </Shell>
  );
}

function HelpCentre() {
  const params = useSearchParams();
  const tripId = params.get("trip");
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [open, setOpen] = useState(Boolean(tripId));
  useEffect(() => {
    api.get<{ tickets: Ticket[] }>("/support/tickets").then((r) => setTickets(r.tickets)).catch(() => setTickets([]));
  }, []);

  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-3">
        <Button size="lg" onClick={() => setOpen(true)}><MessageSquarePlus className="size-4" aria-hidden="true" /> New request</Button>
        <a href="tel:112" className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-danger-soft px-4 text-sm font-bold text-danger"><PhoneCall className="size-4" aria-hidden="true" /> Emergency 112</a>
      </div>

      <section>
        <h2 className="mb-2 px-1 text-sm font-bold text-fg-muted">Your requests</h2>
        <Panel>
          {tickets === null ? <Loading /> : tickets.length === 0 ? (
            <Empty icon={<LifeBuoy className="size-6" />} title="No requests" body="If anything goes wrong on a trip or with a payout, we're one message away." />
          ) : (
            <ul className="divide-y divide-line/60">
              {tickets.map((ticket) => (
                <li key={ticket.id}>
                  <Link href={`/help/${ticket.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-white/3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{ticket.subject}</p>
                      <p className="truncate text-xs text-fg-muted">{ticket.code} · {relativeTime(ticket.updated_at)}{ticket.trip_code ? ` · ${ticket.trip_code}` : ""}</p>
                    </div>
                    <Tag tone={ticket.status === "resolved" ? "go" : ticket.status === "pending" ? "info" : "warn"}>{ticket.status === "pending" ? "Replied" : ticket.status === "resolved" ? "Resolved" : "Open"}</Tag>
                    <ChevronRight className="size-4 text-fg-muted" aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </section>

      <section>
        <h2 className="mb-2 px-1 text-sm font-bold text-fg-muted">Common questions</h2>
        <Panel className="divide-y divide-line/60">
          {FAQ.map(([question, answer]) => (
            <details key={question} className="group px-4 py-3.5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold">
                {question}
                <ChevronRight className="size-4 shrink-0 text-fg-muted transition group-open:rotate-90" aria-hidden="true" />
              </summary>
              <p className="mt-2 text-sm text-fg-muted">{answer}</p>
            </details>
          ))}
        </Panel>
      </section>

      <NewTicket open={open} onClose={() => setOpen(false)} tripId={tripId} onCreated={(ticket) => setTickets([ticket, ...(tickets ?? [])])} />
    </div>
  );
}

function NewTicket({ open, onClose, tripId, onCreated }: { open: boolean; onClose: () => void; tripId: string | null; onCreated: (ticket: Ticket) => void }) {
  const [category, setCategory] = useState("payment");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [trip, setTrip] = useState<Trip | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  useEffect(() => {
    if (tripId) api.get<Trip>(`/driver/trips/${tripId}`).then(setTrip).catch(() => setTrip(null));
  }, [tripId]);

  return (
    <Sheet open={open} onClose={onClose} title="Contact support">
      {sent ? (
        <div className="grid gap-4">
          <Notice tone="go">We've got your request ({sent}). We usually reply within a few hours.</Notice>
          <Button onClick={() => { setSent(null); onClose(); }}>Done</Button>
        </div>
      ) : (
        <form
          className="grid gap-4"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError(null);
            try {
              const created = await api.post<{ id: string; code: string }>("/support/tickets", { category, subject, message, trip_id: trip?.id });
              const now = new Date().toISOString();
              onCreated({ id: created.id, code: created.code, category, subject, status: "open", priority: category === "safety" ? "urgent" : "normal", created_at: now, updated_at: now, trip_code: trip?.code ?? null });
              setSent(created.code);
              setSubject("");
              setMessage("");
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Couldn't send your request.");
            } finally {
              setBusy(false);
            }
          }}
        >
          {trip ? <p className="rounded-2xl bg-raised px-4 py-3 text-sm">About trip <b>{trip.code}</b>: {trip.pickup.name} → {trip.drop.name}</p> : null}
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button key={c.value} type="button" aria-pressed={category === c.value} onClick={() => setCategory(c.value)} className={cx("rounded-full border px-3 py-1.5 text-sm font-semibold", category === c.value ? "border-go bg-go-soft text-go" : "border-line text-fg-muted")}>{c.label}</button>
            ))}
          </div>
          {category === "safety" ? <Notice tone="info">Safety requests are marked urgent. In an emergency, call 112 first.</Notice> : null}
          <Field label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} minLength={4} maxLength={120} required />
          <div className="grid gap-1.5">
            <label htmlFor="ticket-message" className="text-sm font-semibold text-fg-muted">What happened?</label>
            <textarea id="ticket-message" value={message} onChange={(e) => setMessage(e.target.value)} rows={4} minLength={5} maxLength={2000} required className="rounded-2xl border border-line bg-raised p-3 text-base outline-none focus:border-go focus:ring-4 focus:ring-go/20" />
          </div>
          {error ? <Notice>{error}</Notice> : null}
          <Button type="submit" size="lg" busy={busy} disabled={subject.trim().length < 4 || message.trim().length < 5}>Send</Button>
        </form>
      )}
    </Sheet>
  );
}
