"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { BadgeCheck, CalendarClock, CheckCircle2, PauseCircle, Star, XCircle } from "lucide-react";
import { dateLabel, dateTimeLabel, inr, relativeTime } from "@ridenow/shared";
import { AccountStatusButton, WalletAdjustButton } from "@/components/account-actions";
import { Shell } from "@/components/shell";
import { DOC_KIND, DriverStatusBadge, TripStatusBadge } from "@/components/status";
import { Avatar, Badge, Button, ErrorState, KeyValues, LoadingPage, Modal, Notice, PageHeader, Panel, Stat, Table, TextArea, td, th } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin } from "@/lib/session";
import type { DriverDetail, DriverDocument } from "@/lib/types";
import { errorText, useApi } from "@/lib/use-api";

export default function DriverPage() {
  return (
    <Shell>
      <DriverView />
    </Shell>
  );
}

function daysUntil(date: string): number {
  return Math.floor((new Date(date).getTime() - Date.now()) / 86_400_000);
}

function DriverView() {
  const { id } = useParams<{ id: string }>();
  const { toast, refreshQueues } = useAdmin();
  const { data: driver, error, reload } = useApi<DriverDetail>(`/admin/drivers/${id}`);
  const [busy, setBusy] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<DriverDocument | null>(null);
  const [note, setNote] = useState("");
  const [rejectError, setRejectError] = useState<string | null>(null);

  if (error && !driver) return <ErrorState message={error} onRetry={reload} />;
  if (!driver) return <LoadingPage label="Loading the driver" />;

  const docsOutstanding = driver.documents.filter((d) => d.status !== "approved").length;

  async function setDriverStatus(status: "approved" | "suspended") {
    setBusy(status);
    try {
      await api.post(`/admin/drivers/${id}/status`, { status });
      toast(status === "approved" ? `${driver!.full_name} can drive now` : `${driver!.full_name}'s driving is paused`);
      refreshQueues();
      reload();
    } catch (err) {
      toast(errorText(err), "bad");
    } finally {
      setBusy(null);
    }
  }

  async function review(doc: DriverDocument, status: "approved" | "rejected", reason = "") {
    setBusy(doc.id);
    try {
      await api.post(`/admin/documents/${doc.id}/review`, { status, note: reason });
      toast(`${DOC_KIND[doc.kind] ?? doc.kind} ${status}`);
      setRejecting(null);
      setNote("");
      reload();
    } catch (err) {
      if (status === "rejected") setRejectError(errorText(err));
      else toast(errorText(err), "bad");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        back={{ href: "/drivers", label: "All drivers" }}
        title={
          <span className="flex flex-wrap items-center gap-3">
            <Avatar name={driver.full_name} color={driver.avatar_color} size={34} />
            {driver.full_name}
            <DriverStatusBadge status={driver.status} />
            {driver.online ? <Badge tone="ok" dot>Online</Badge> : <Badge>Offline</Badge>}
            {driver.simulated ? <Badge tone="info">Simulated demo driver</Badge> : null}
          </span>
        }
        description={`${driver.vehicle_color} ${driver.vehicle_make} ${driver.vehicle_model} · ${driver.plate} · joined ${dateLabel(driver.joined_at)}`}
        actions={
          <>
            {driver.status !== "approved" ? (
              <Button variant="ok" busy={busy === "approved"} disabled={docsOutstanding > 0} title={docsOutstanding > 0 ? "Approve every document first" : undefined} onClick={() => void setDriverStatus("approved")}>
                <BadgeCheck className="size-4" aria-hidden="true" />
                Approve to drive
              </Button>
            ) : (
              <Button variant="danger" busy={busy === "suspended"} onClick={() => void setDriverStatus("suspended")}>
                <PauseCircle className="size-4" aria-hidden="true" />
                Pause driving
              </Button>
            )}
            <WalletAdjustButton userId={driver.id} name={driver.full_name} balance={driver.balance} onDone={reload} />
            <AccountStatusButton userId={driver.id} name={driver.full_name} status={driver.account_status} onDone={reload} />
          </>
        }
      />

      {driver.status !== "approved" && docsOutstanding > 0 ? (
        <div className="mb-5">
          <Notice tone="warn">
            {docsOutstanding} {docsOutstanding === 1 ? "document needs" : "documents need"} review before {driver.full_name.split(" ")[0]} can be approved to drive.
          </Notice>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Stat label="Earnings, 30 days" value={inr(driver.earnings_30d)} />
        <Stat label="Trips, 30 days" value={driver.trips_30d} />
        <Stat label="Rating" value={<span className="flex items-center gap-1"><Star className="size-5 fill-brand text-brand" aria-hidden="true" />{driver.rating_avg.toFixed(2)}</span>} hint={`${driver.rating_count} ratings`} />
        <Stat label="Acceptance rate" value={`${driver.acceptance_rate}%`} hint={`${driver.offers_accepted} of ${driver.offers_received} offers`} />
        <Stat label="Wallet balance" value={inr(driver.balance)} hint="Earnings not yet paid out" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="grid content-start gap-5">
          <Panel title="Documents" description="Every document must be approved before the driver can go online">
            <ul className="divide-y divide-line">
              {driver.documents.map((doc) => {
                const days = doc.expires_on ? daysUntil(doc.expires_on) : null;
                return (
                  <li key={doc.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="flex flex-wrap items-center gap-2 text-[13px] font-medium">
                        {DOC_KIND[doc.kind] ?? doc.kind}
                        <Badge tone={doc.status === "approved" ? "ok" : doc.status === "rejected" ? "bad" : "warn"} dot className="capitalize">{doc.status}</Badge>
                        {days !== null && days < 0 ? <Badge tone="bad">Expired</Badge> : days !== null && days <= 30 ? <Badge tone="warn">Expires in {days} days</Badge> : null}
                      </p>
                      <p className="mt-0.5 flex flex-wrap gap-x-3 text-xs text-muted">
                        <span className="font-mono">{doc.number || "No number"}</span>
                        {doc.expires_on ? <span className="inline-flex items-center gap-1"><CalendarClock className="size-3" aria-hidden="true" />Valid to {dateLabel(doc.expires_on)}</span> : null}
                        {doc.note ? <span>Note: {doc.note}</span> : null}
                      </p>
                    </div>
                    {doc.status !== "approved" ? (
                      <Button size="sm" variant="ok" busy={busy === doc.id} onClick={() => void review(doc, "approved")}>
                        <CheckCircle2 className="size-3.5" aria-hidden="true" />
                        Approve
                      </Button>
                    ) : null}
                    {doc.status !== "rejected" ? (
                      <Button size="sm" variant="secondary" onClick={() => { setNote(""); setRejectError(null); setRejecting(doc); }}>
                        <XCircle className="size-3.5" aria-hidden="true" />
                        Reject
                      </Button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </Panel>

          <Panel title="Recent trips" description="The latest 20">
            {driver.trips.length === 0 ? (
              <p className="px-4 py-3 text-[13px] text-muted">No trips yet.</p>
            ) : (
              <Table label="Recent trips">
                <thead>
                  <tr>
                    <th className={th}>Trip</th>
                    <th className={th}>When</th>
                    <th className={th}>Route</th>
                    <th className={th}>Status</th>
                    <th className={`${th} text-right`}>Fare</th>
                    <th className={`${th} text-right`}>Earning</th>
                  </tr>
                </thead>
                <tbody>
                  {driver.trips.map((t) => (
                    <tr key={t.id} className="hover:bg-sunken">
                      <td className={td}><Link href={`/trips/${t.id}`} className="font-mono text-xs font-semibold text-signal hover:underline">{t.code}</Link></td>
                      <td className={`${td} whitespace-nowrap text-ink-2`}>{dateTimeLabel(t.requested_at)}</td>
                      <td className={`${td} max-w-60 truncate`}>{t.pickup.name} → {t.drop.name}</td>
                      <td className={td}><TripStatusBadge status={t.status} /></td>
                      <td className={`${td} num text-right`}>{inr(t.fare_final ?? t.fare_estimate)}</td>
                      <td className={`${td} num text-right font-medium`}>{t.driver_earning ? inr(t.driver_earning) : "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Panel>
        </div>

        <div className="grid content-start gap-5">
          <Panel title="Vehicle and licence" bodyClassName="p-4">
            <KeyValues
              items={[
                ["Type", driver.vehicle_type],
                ["Vehicle", `${driver.vehicle_color} ${driver.vehicle_make} ${driver.vehicle_model}`],
                ["Plate", <span key="plate" className="font-mono">{driver.plate}</span>],
                ["Licence", <span key="lic" className="font-mono">{driver.license_no}</span>],
              ]}
            />
          </Panel>
          <Panel title="Contact and activity" bodyClassName="p-4">
            <KeyValues
              items={[
                ["Phone", driver.phone ?? "–"],
                ["Email", driver.email ?? "–"],
                ["Account", driver.account_status === "active" ? "Active" : "Suspended"],
                ["Last seen", driver.last_seen_at ? relativeTime(driver.last_seen_at) : "Never"],
              ]}
            />
          </Panel>
          <Panel title="Latest ratings" bodyClassName="grid gap-3 p-4">
            {driver.ratings.length === 0 ? (
              <p className="text-[13px] text-muted">No ratings yet.</p>
            ) : (
              driver.ratings.map((r, index) => (
                <div key={index} className="border-b border-line pb-3 last:border-0 last:pb-0">
                  <p className="flex items-center justify-between text-[13px]">
                    <span className="num inline-flex items-center gap-1 font-semibold">
                      <Star className="size-3.5 fill-brand text-brand" aria-hidden="true" />
                      {r.stars}
                    </span>
                    <span className="text-xs text-muted">{relativeTime(r.created_at)}</span>
                  </p>
                  {r.tags.length ? <p className="mt-1 flex flex-wrap gap-1">{r.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)}</p> : null}
                  {r.comment ? <p className="mt-1 text-[13px] text-ink-2">“{r.comment}”</p> : null}
                </div>
              ))
            )}
          </Panel>
        </div>
      </div>

      <Modal
        open={rejecting !== null}
        onClose={() => setRejecting(null)}
        title={`Reject ${rejecting ? DOC_KIND[rejecting.kind] ?? rejecting.kind : ""}?`}
        description="The driver is notified with your note and asked to upload it again."
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejecting(null)}>Cancel</Button>
            <Button variant="danger" busy={busy === rejecting?.id} disabled={note.trim().length < 3} onClick={() => rejecting && void review(rejecting, "rejected", note.trim())}>Reject document</Button>
          </>
        }
      >
        <div className="grid gap-3">
          <TextArea label="What is wrong with it?" value={note} onChange={(e) => setNote(e.target.value)} maxLength={200} placeholder="For example: the photo is blurred, the number is unreadable" />
          {rejectError ? <Notice tone="bad">{rejectError}</Notice> : null}
        </div>
      </Modal>
    </>
  );
}
