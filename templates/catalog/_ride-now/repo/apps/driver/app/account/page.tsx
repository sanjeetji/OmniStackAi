"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Bell, CarFront, ChevronRight, FileCheck2, LifeBuoy, LogOut, MapPin, Star, Wallet } from "lucide-react";
import { ApiError, dateLabel } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Avatar, Button, Field, Notice, Panel, Sheet, Tag, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { useDriver } from "@/lib/driver";

const DOC_LABEL: Record<string, string> = {
  license: "Driving licence",
  registration: "Vehicle registration (RC)",
  insurance: "Insurance",
  permit: "Commercial permit",
  photo: "Profile photo",
};

export default function AccountPage() {
  return (
    <Shell title="Account">
      <Suspense>
        <Account />
      </Suspense>
    </Shell>
  );
}

function Account() {
  const router = useRouter();
  const params = useSearchParams();
  const { profile, mode, setMode, signOut, refresh, online } = useDriver();
  const [editing, setEditing] = useState(false);
  if (!profile) return null;
  const pendingDocs = profile.documents.filter((d) => d.status !== "approved" || expiresSoon(d.expires_on)).length;

  return (
    <div className="grid gap-4">
      {params.get("welcome") ? <Notice tone="go">Application received. We're checking your documents; most drivers are approved within a day.</Notice> : null}
      {profile.status === "pending" ? <Notice tone="warn">Your account is waiting for approval. You can go online once an admin approves your documents.</Notice> : null}
      {profile.status === "suspended" ? <Notice>Your account is suspended. Contact support to find out why.</Notice> : null}

      <Panel className="flex items-center gap-4 p-5">
        <Avatar name={profile.full_name} color={profile.avatar_color} size={60} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-lg font-extrabold">{profile.full_name}</p>
          <p className="truncate text-sm text-fg-muted">{profile.phone ?? profile.email}</p>
          <p className="mt-1 flex items-center gap-1 text-sm"><Star className="size-4 fill-warn text-warn" aria-hidden="true" /> {profile.rating.toFixed(2)} · {profile.acceptance_rate}% accepted · since {dateLabel(profile.joined_at)}</p>
        </div>
        <Button size="sm" variant="outline" onClick={() => setEditing(true)}>Edit</Button>
      </Panel>

      <Panel className="p-5">
        <div className="mb-3 flex items-center gap-2">
          <CarFront className="size-5 text-go" aria-hidden="true" />
          <h2 className="flex-1 font-bold">Vehicle</h2>
          <Tag>{profile.vehicle.type_name}</Tag>
        </div>
        <p className="font-semibold">{profile.vehicle.color} {profile.vehicle.make} {profile.vehicle.model}</p>
        <p className="mt-1 inline-block rounded-lg border border-line px-2 py-0.5 font-mono text-sm tracking-wider">{profile.vehicle.plate}</p>
        <p className="mt-2 text-xs text-fg-muted">Licence {profile.license_no} · commission {profile.commission_pct}% per trip. To change vehicles, contact support.</p>
      </Panel>

      <Panel className="p-5">
        <div className="mb-3 flex items-center gap-2">
          <FileCheck2 className="size-5 text-go" aria-hidden="true" />
          <h2 className="flex-1 font-bold">Documents</h2>
          {pendingDocs > 0 ? <Tag tone="warn">{pendingDocs} need attention</Tag> : <Tag tone="go">All verified</Tag>}
        </div>
        <ul className="grid gap-2">
          {profile.documents.map((doc) => (
            <li key={doc.id} className="flex items-center justify-between gap-3 text-sm">
              <span>
                <span className="block font-semibold">{DOC_LABEL[doc.kind] ?? doc.kind}</span>
                <span className="text-xs text-fg-muted">{doc.number || "Number not added"}{doc.expires_on ? ` · expires ${dateLabel(doc.expires_on)}` : ""}{doc.note ? ` · ${doc.note}` : ""}</span>
              </span>
              {expiresSoon(doc.expires_on) ? (
                <Tag tone="danger">{daysLeft(doc.expires_on!) < 0 ? "Expired" : `Expires in ${daysLeft(doc.expires_on!)}d`}</Tag>
              ) : (
                <Tag tone={doc.status === "approved" ? "go" : doc.status === "rejected" ? "danger" : "warn"}>{doc.status === "approved" ? "Verified" : doc.status === "rejected" ? "Rejected" : "In review"}</Tag>
              )}
            </li>
          ))}
        </ul>
      </Panel>

      <Panel className="p-5">
        <div className="mb-3 flex items-center gap-2">
          <MapPin className="size-5 text-go" aria-hidden="true" />
          <h2 className="font-bold">Location</h2>
        </div>
        <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Location source">
          {([["simulated", "Simulated", "Drives along the route by itself, for demos"], ["gps", "Device GPS", "Uses this phone's real location"]] as const).map(([value, label, hint]) => (
            <button key={value} type="button" role="radio" aria-checked={mode === value} onClick={() => setMode(value)} className={cx("rounded-2xl border p-3 text-left", mode === value ? "border-go bg-go-soft" : "border-line")}>
              <span className="block text-sm font-bold">{label}</span>
              <span className="block text-xs text-fg-muted">{hint}</span>
            </button>
          ))}
        </div>
      </Panel>

      <Panel className="divide-y divide-line/60">
        <Row href="/ratings" icon={<Star className="size-5" />} label="Ratings & feedback" />
        <Row href="/wallet" icon={<Wallet className="size-5" />} label="Wallet & payouts" />
        <Row href="/notifications" icon={<Bell className="size-5" />} label="Notifications" />
        <Row href="/help" icon={<LifeBuoy className="size-5" />} label="Help & support" />
      </Panel>

      <Button variant="ghost" size="lg" onClick={async () => { await signOut(); router.replace("/login"); }}>
        <LogOut className="size-4" aria-hidden="true" /> Sign out{online ? " (goes offline)" : ""}
      </Button>

      <EditProfile open={editing} onClose={() => setEditing(false)} name={profile.full_name} phone={profile.phone ?? ""} onSaved={() => void refresh()} />
    </div>
  );
}

const daysLeft = (iso: string) => Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000);
/** Flag documents a month before they expire so the driver can renew in time. */
const expiresSoon = (iso: string | null) => iso !== null && daysLeft(iso) <= 30;

function Row({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="flex items-center gap-3 px-5 py-4 font-semibold hover:bg-white/3">
      <span className="text-fg-muted" aria-hidden="true">{icon}</span>
      <span className="flex-1">{label}</span>
      <ChevronRight className="size-4 text-fg-muted" aria-hidden="true" />
    </Link>
  );
}

function EditProfile({ open, onClose, name, phone, onSaved }: { open: boolean; onClose: () => void; name: string; phone: string; onSaved: () => void }) {
  const [fullName, setFullName] = useState(name);
  const [tel, setTel] = useState(phone);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (open) {
      setFullName(name);
      setTel(phone);
      setPassword("");
      setError(null);
    }
  }, [open, name, phone]);

  return (
    <Sheet open={open} onClose={onClose} title="Edit profile">
      <form
        className="grid gap-4"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError(null);
          const changes: Record<string, string> = {};
          if (fullName !== name) changes.full_name = fullName;
          if (tel !== phone) changes.phone = tel;
          if (password) changes.password = password;
          try {
            if (Object.keys(changes).length) await api.patch("/auth/me", changes);
            onSaved();
            onClose();
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Couldn't save your changes.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} minLength={2} maxLength={80} required />
        <Field label="Mobile number" type="tel" value={tel} onChange={(e) => setTel(e.target.value)} required />
        <Field label="New password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} hint="Leave empty to keep your current password." />
        {error ? <Notice>{error}</Notice> : null}
        <Button type="submit" size="lg" busy={busy}>Save</Button>
      </form>
    </Sheet>
  );
}
