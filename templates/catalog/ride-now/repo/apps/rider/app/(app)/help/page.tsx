"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ChevronRight, LifeBuoy, MessageSquarePlus } from "lucide-react";
import { ApiError, relativeTime, type Ticket, type Trip } from "@ridenow/shared";
import { AppShell } from "@/components/app-shell";
import { Alert, Badge, Button, Card, EmptyState, Input, PageHeader, Sheet, cx } from "@/components/ui";
import { api } from "@/lib/api";

const CATEGORIES = [
  { value: "payment", label: "Payments & refunds" },
  { value: "safety", label: "Safety" },
  { value: "lost_item", label: "Lost item" },
  { value: "driver", label: "Driver behaviour" },
  { value: "app", label: "App problem" },
  { value: "other", label: "Something else" },
];
const FAQ = [
  ["I was charged twice", "Pending charges from a cancelled ride drop off automatically. If you still see two charges after a few minutes, raise a payment ticket and we'll refund you."],
  ["My driver didn't come", "If your driver doesn't move towards you, cancel for free before they arrive and book again. Tell us about it so we can follow up with the driver."],
  ["How do refunds work?", "Refunds go to your RideNow wallet instantly, and you can use them on your next ride."],
  ["I feel unsafe during a ride", "Share your trip with someone you trust and raise a safety ticket. Safety tickets are marked urgent and answered first."],
];

export default function HelpPage() {
  return (
    <AppShell>
      <Suspense>
        <HelpCentre />
      </Suspense>
    </AppShell>
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
    <>
      <PageHeader title="Help centre" subtitle="Answers first. Our team is here 24×7 if you need more." action={<Button onClick={() => setOpen(true)}><MessageSquarePlus className="size-4" aria-hidden="true" /> Contact support</Button>} />
      <div className="grid gap-5 md:grid-cols-[1.2fr_1fr]">
        <Card className="divide-y divide-line">
          {FAQ.map(([question, answer]) => (
            <details key={question} className="group px-5 py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-semibold">
                {question}
                <ChevronRight className="size-4 text-muted transition group-open:rotate-90" aria-hidden="true" />
              </summary>
              <p className="mt-2 text-sm text-muted">{answer}</p>
            </details>
          ))}
        </Card>
        <Card className="p-2">
          <p className="px-4 pb-2 pt-3 font-bold">Your requests</p>
          {tickets === null ? <p className="px-4 pb-4 text-sm text-muted">Loading…</p> : tickets.length === 0 ? (
            <EmptyState icon={<LifeBuoy className="size-6" />} title="No requests" body="If something goes wrong, we're one message away." />
          ) : (
            <ul className="grid">
              {tickets.map((ticket) => (
                <li key={ticket.id}>
                  <Link href={`/help/${ticket.id}`} className="flex items-center gap-3 rounded-2xl px-4 py-3 hover:bg-canvas">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{ticket.subject}</p>
                      <p className="truncate text-xs text-muted">{ticket.code} · {relativeTime(ticket.updated_at)}{ticket.trip_code ? ` · ${ticket.trip_code}` : ""}</p>
                    </div>
                    <Badge tone={ticket.status === "resolved" ? "success" : ticket.status === "pending" ? "teal" : "amber"}>{ticket.status === "pending" ? "Replied" : ticket.status === "resolved" ? "Resolved" : "Open"}</Badge>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
      <NewTicket open={open} onClose={() => setOpen(false)} tripId={tripId} onCreated={(ticket) => setTickets([ticket, ...(tickets ?? [])])} />
    </>
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
    if (tripId) api.get<Trip>(`/rider/trips/${tripId}`).then(setTrip).catch(() => setTrip(null));
  }, [tripId]);

  return (
    <Sheet open={open} onClose={onClose} title="Contact support">
      {sent ? (
        <div className="grid gap-4">
          <Alert tone="success">We've got your request ({sent}). We usually reply within a few hours.</Alert>
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
              onCreated({ id: created.id, code: created.code, category, subject, status: "open", priority: category === "safety" ? "urgent" : "normal", created_at: new Date().toISOString(), updated_at: new Date().toISOString(), trip_code: trip?.code ?? null });
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
          {trip ? <p className="rounded-2xl bg-canvas px-4 py-3 text-sm">About trip <b>{trip.code}</b>: {trip.pickup.name} → {trip.drop.name}</p> : null}
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button key={c.value} type="button" aria-pressed={category === c.value} onClick={() => setCategory(c.value)} className={cx("rounded-full border px-3 py-1.5 text-sm font-semibold", category === c.value ? "border-ink bg-ink text-white" : "border-line")}>{c.label}</button>
            ))}
          </div>
          {category === "safety" ? <Alert tone="info">Safety requests are marked urgent. In an emergency, call 112.</Alert> : null}
          <Input label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} minLength={4} maxLength={120} required />
          <div className="grid gap-1.5">
            <label htmlFor="ticket-message" className="text-sm font-semibold text-ink-soft">What happened?</label>
            <textarea id="ticket-message" value={message} onChange={(e) => setMessage(e.target.value)} rows={4} minLength={5} maxLength={2000} required className="rounded-2xl border border-line p-3 text-sm outline-none focus:border-ink" />
          </div>
          {error ? <Alert>{error}</Alert> : null}
          <Button type="submit" size="lg" busy={busy} disabled={subject.trim().length < 4 || message.trim().length < 5}>Send</Button>
        </form>
      )}
    </Sheet>
  );
}
