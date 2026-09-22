"use client";

import { useState } from "react";
import { BadgePercent, Plus } from "lucide-react";
import { dateLabel, inr } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Badge, Button, Empty, ErrorState, Field, LoadingRows, Modal, Notice, PageHeader, Panel, Segmented, Table, Toggle, td, th } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin } from "@/lib/session";
import type { PromoRow } from "@/lib/types";
import { errorText, useApi } from "@/lib/use-api";

export default function PromosPage() {
  return (
    <Shell>
      <PromosView />
    </Shell>
  );
}

function describe(p: PromoRow): string {
  const value = p.kind === "percent" ? `${p.value}% off` : `${inr(p.value)} off`;
  const cap = p.kind === "percent" && p.max_discount ? `, up to ${inr(p.max_discount)}` : "";
  const min = p.min_fare > 0 ? ` on fares over ${inr(p.min_fare)}` : "";
  return `${value}${cap}${min}`;
}

function PromosView() {
  const { toast } = useAdmin();
  const { data, error, reload } = useApi<{ promos: PromoRow[] }>("/admin/promos");
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  async function setActive(promo: PromoRow, active: boolean) {
    setBusy(promo.code);
    try {
      await api.patch(`/admin/promos/${encodeURIComponent(promo.code)}`, { active });
      toast(`${promo.code} ${active ? "resumed" : "paused"}`);
      reload();
    } catch (err) {
      toast(errorText(err), "bad");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Promo codes"
        description="Discounts riders enter at booking. The platform funds the discount; drivers are paid on the full fare."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus className="size-4" aria-hidden="true" />
            New promo code
          </Button>
        }
      />
      <Panel>
        {error && !data ? (
          <div className="p-4"><ErrorState message={error} onRetry={reload} /></div>
        ) : !data ? (
          <LoadingRows label="Loading promo codes" />
        ) : data.promos.length === 0 ? (
          <Empty icon={<BadgePercent className="size-5" />} title="No promo codes" body="Create one to run a campaign, for example 50% off the first ride." action={<Button size="sm" onClick={() => setCreating(true)}>New promo code</Button>} />
        ) : (
          <Table label="Promo codes">
            <thead>
              <tr>
                <th className={th}>Code</th>
                <th className={th}>Offer</th>
                <th className={`${th} text-right`}>Used</th>
                <th className={`${th} text-right`}>Discount given</th>
                <th className={th}>Valid until</th>
                <th className={th}>Status</th>
                <th className={`${th} text-right`}>Live</th>
              </tr>
            </thead>
            <tbody>
              {data.promos.map((p) => {
                const expired = p.valid_until !== null && new Date(p.valid_until).getTime() < Date.now();
                const exhausted = p.usage_limit !== null && p.used_count >= p.usage_limit;
                return (
                  <tr key={p.code} className="hover:bg-sunken">
                    <td className={td}>
                      <span className="font-mono text-[13px] font-semibold">{p.code}</span>
                      <span className="block max-w-56 truncate text-xs text-muted">{p.description}</span>
                    </td>
                    <td className={`${td} text-ink-2`}>{describe(p)}<span className="block text-xs text-muted">{p.per_user_limit} per rider</span></td>
                    <td className={`${td} num text-right`}>{p.used_count}{p.usage_limit !== null ? <span className="text-muted"> / {p.usage_limit}</span> : null}</td>
                    <td className={`${td} num text-right font-medium`}>{inr(p.total_discount)}</td>
                    <td className={`${td} whitespace-nowrap text-ink-2`}>{p.valid_until ? dateLabel(p.valid_until) : "No end date"}</td>
                    <td className={td}>
                      {expired ? <Badge tone="neutral">Expired</Badge> : exhausted ? <Badge tone="neutral">Used up</Badge> : p.active ? <Badge tone="ok" dot>Live</Badge> : <Badge tone="warn" dot>Paused</Badge>}
                    </td>
                    <td className={`${td} text-right`}>
                      <Toggle checked={p.active} disabled={busy === p.code} onChange={(next) => void setActive(p, next)} label={`${p.code} live`} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Panel>
      <CreatePromo open={creating} onClose={() => setCreating(false)} onCreated={() => { setCreating(false); reload(); }} />
    </>
  );
}

function CreatePromo({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const { toast } = useAdmin();
  const [kind, setKind] = useState<"percent" | "flat">("percent");
  const [form, setForm] = useState({ code: "", description: "", value: "", max_discount: "", min_fare: "", valid_until: "", usage_limit: "", per_user_limit: "1" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });
  const code = form.code.trim().toUpperCase();
  const value = Number(form.value);
  const valid = /^[A-Z0-9]{3,20}$/.test(code) && form.description.trim().length > 0 && value >= 1 && value <= (kind === "percent" ? 100 : 1000);
  const optional = (v: string) => (v.trim() === "" ? undefined : Number(v));

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/admin/promos", {
        code,
        description: form.description.trim(),
        kind,
        value,
        max_discount: kind === "percent" ? optional(form.max_discount) : undefined,
        min_fare: optional(form.min_fare),
        valid_until: form.valid_until ? new Date(`${form.valid_until}T23:59:59`).toISOString() : undefined,
        usage_limit: optional(form.usage_limit),
        per_user_limit: optional(form.per_user_limit) ?? 1,
      });
      toast(`${code} is live`);
      setForm({ code: "", description: "", value: "", max_discount: "", min_fare: "", valid_until: "", usage_limit: "", per_user_limit: "1" });
      onCreated();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New promo code"
      description="It goes live as soon as you create it. You can pause it at any time."
      width="max-w-lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button busy={busy} disabled={!valid} onClick={() => void submit()}>Create code</Button>
        </>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Code" value={form.code} onChange={set("code")} placeholder="MONSOON25" hint="3–20 letters and digits" className="sm:col-span-1" autoCapitalize="characters" />
        <div className="grid gap-1">
          <span className="text-xs font-semibold text-ink-2">Type</span>
          <Segmented label="Discount type" value={kind} onChange={setKind} options={[{ value: "percent", label: "Percent" }, { value: "flat", label: "Flat ₹" }]} />
        </div>
        <Field label="Description (riders see it)" value={form.description} onChange={set("description")} placeholder="25% off rides this monsoon" className="sm:col-span-2" maxLength={120} />
        <Field label={kind === "percent" ? "Percent off" : "Amount off"} type="number" min={1} max={kind === "percent" ? 100 : 1000} suffix={kind === "percent" ? "%" : "₹"} value={form.value} onChange={set("value")} />
        {kind === "percent" ? <Field label="Maximum discount" type="number" min={1} suffix="₹" value={form.max_discount} onChange={set("max_discount")} hint="Optional" /> : <div />}
        <Field label="Minimum fare" type="number" min={0} suffix="₹" value={form.min_fare} onChange={set("min_fare")} hint="Optional" />
        <Field label="Valid until" type="date" value={form.valid_until} onChange={set("valid_until")} hint="Optional" />
        <Field label="Total uses" type="number" min={1} value={form.usage_limit} onChange={set("usage_limit")} hint="Optional; blank means unlimited" />
        <Field label="Uses per rider" type="number" min={1} value={form.per_user_limit} onChange={set("per_user_limit")} />
      </div>
      {error ? <div className="mt-4"><Notice tone="bad">{error}</Notice></div> : null}
    </Modal>
  );
}
