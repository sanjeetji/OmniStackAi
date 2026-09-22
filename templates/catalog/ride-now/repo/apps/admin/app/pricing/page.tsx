"use client";

import { useEffect, useState } from "react";
import { Save, Users } from "lucide-react";
import { inr } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Badge, Button, ErrorState, Field, LoadingRows, Notice, PageHeader, Panel, Toggle } from "@/components/ui";
import { api } from "@/lib/api";
import { useAdmin } from "@/lib/session";
import type { VehicleTypeRow } from "@/lib/types";
import { errorText, useApi } from "@/lib/use-api";

export default function PricingPage() {
  return (
    <Shell>
      <PricingView />
    </Shell>
  );
}

// A typical city ride, used to preview what a rider would pay.
const SAMPLE = { km: 8, min: 26 };

function PricingView() {
  const { data, error, reload } = useApi<{ vehicle_types: VehicleTypeRow[] }>("/admin/vehicle-types");
  return (
    <>
      <PageHeader
        title="Pricing"
        description={`Fares are upfront: the larger of the minimum fare and base + per km + per minute, times surge, plus the booking fee, minus any promo. The sample shows a ${SAMPLE.km} km, ${SAMPLE.min}-minute ride without surge.`}
      />
      {error && !data ? (
        <ErrorState message={error} onRetry={reload} />
      ) : !data ? (
        <Panel><LoadingRows label="Loading vehicle types" /></Panel>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.vehicle_types.map((type) => (
            <PriceCard key={type.id} type={type} onSaved={reload} />
          ))}
        </div>
      )}
    </>
  );
}

type Form = Record<"base_fare" | "per_km" | "per_min" | "min_fare" | "booking_fee" | "commission_pct", string>;

function toForm(type: VehicleTypeRow): Form {
  return {
    base_fare: String(type.base_fare),
    per_km: String(type.per_km),
    per_min: String(type.per_min),
    min_fare: String(type.min_fare),
    booking_fee: String(type.booking_fee),
    commission_pct: String(type.commission_pct),
  };
}

const LIMITS: Record<keyof Form, { label: string; max: number; suffix: string }> = {
  base_fare: { label: "Base fare", max: 1000, suffix: "₹" },
  per_km: { label: "Per km", max: 200, suffix: "₹" },
  per_min: { label: "Per minute", max: 50, suffix: "₹" },
  min_fare: { label: "Minimum fare", max: 2000, suffix: "₹" },
  booking_fee: { label: "Booking fee", max: 200, suffix: "₹" },
  commission_pct: { label: "Commission", max: 50, suffix: "%" },
};

function PriceCard({ type, onSaved }: { type: VehicleTypeRow; onSaved: () => void }) {
  const { toast } = useAdmin();
  const [form, setForm] = useState<Form>(() => toForm(type));
  const [active, setActive] = useState(type.active);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setForm(toForm(type));
    setActive(type.active);
  }, [type]);

  const n = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, Number(v)])) as Record<keyof Form, number>;
  const invalid = (Object.keys(LIMITS) as (keyof Form)[]).find((k) => !Number.isFinite(n[k]) || n[k] < 0 || n[k] > LIMITS[k].max || form[k].trim() === "");
  const dirty = active !== type.active || (Object.keys(form) as (keyof Form)[]).some((k) => n[k] !== type[k]);
  const subtotal = Math.max(n.min_fare, n.base_fare + n.per_km * SAMPLE.km + n.per_min * SAMPLE.min);
  const sampleFare = subtotal + n.booking_fee;
  const commission = (subtotal * n.commission_pct) / 100;

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await api.put(`/admin/vehicle-types/${type.id}`, { ...n, active });
      toast(`${type.name} pricing saved`);
      onSaved();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          {type.name}
          <span className="inline-flex items-center gap-1 text-xs font-normal text-muted"><Users className="size-3" aria-hidden="true" />{type.seats}</span>
          {active ? <Badge tone="ok" dot>Bookable</Badge> : <Badge dot>Hidden from riders</Badge>}
        </span>
      }
      description={type.description}
      actions={
        <label className="flex items-center gap-2 text-xs text-ink-2">
          <Toggle checked={active} onChange={setActive} label={`${type.name} is bookable`} />
          Bookable
        </label>
      }
      bodyClassName="grid gap-4 p-4"
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {(Object.keys(LIMITS) as (keyof Form)[]).map((key) => (
          <Field
            key={key}
            label={LIMITS[key].label}
            type="number"
            inputMode="decimal"
            min={0}
            max={LIMITS[key].max}
            step="0.5"
            suffix={LIMITS[key].suffix}
            value={form[key]}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            error={invalid === key ? `0 to ${LIMITS[key].max}` : null}
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-box bg-sunken px-3.5 py-2.5 text-[13px]">
        <span className="text-ink-2">
          Sample ride: <span className="num font-semibold text-ink">{invalid ? "–" : inr(Math.round(sampleFare))}</span>
          <span className="text-muted"> · platform keeps </span>
          <span className="num font-semibold text-ink">{invalid ? "–" : inr(Math.round(commission))}</span>
        </span>
        <Button busy={busy} disabled={!dirty || Boolean(invalid)} onClick={() => void save()}>
          <Save className="size-4" aria-hidden="true" />
          Save
        </Button>
      </div>
      {error ? <Notice tone="bad">{error}</Notice> : null}
    </Panel>
  );
}
