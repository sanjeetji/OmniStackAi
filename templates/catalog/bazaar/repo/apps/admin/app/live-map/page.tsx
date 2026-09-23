"use client";

import { useMemo } from "react";
import Link from "next/link";
import { MapPin, Truck } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Badge, DataState, Stat } from "../../components/ui";
import { useApi, useInterval } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, inr, stamp, titleCase, tone } from "../../lib/format";

/**
 * A schematic map of India. Consignments are placed by the state on their delivery address, so the
 * board is drawn from live rows rather than invented coordinates.
 */
const REGIONS: { state: string; label: string; x: number; y: number }[] = [
  { state: "Jammu and Kashmir", label: "Srinagar", x: 27, y: 8 },
  { state: "Punjab", label: "Punjab", x: 26, y: 18 },
  { state: "Delhi", label: "Delhi", x: 31, y: 24 },
  { state: "Rajasthan", label: "Rajasthan", x: 20, y: 31 },
  { state: "Uttar Pradesh", label: "Uttar Pradesh", x: 41, y: 30 },
  { state: "Bihar", label: "Bihar", x: 55, y: 33 },
  { state: "West Bengal", label: "Kolkata", x: 63, y: 40 },
  { state: "Assam", label: "Assam", x: 76, y: 32 },
  { state: "Gujarat", label: "Gujarat", x: 15, y: 42 },
  { state: "Madhya Pradesh", label: "Madhya Pradesh", x: 35, y: 41 },
  { state: "Odisha", label: "Odisha", x: 56, y: 48 },
  { state: "Maharashtra", label: "Maharashtra", x: 25, y: 53 },
  { state: "Telangana", label: "Telangana", x: 35, y: 59 },
  { state: "Karnataka", label: "Karnataka", x: 28, y: 68 },
  { state: "Tamil Nadu", label: "Tamil Nadu", x: 36, y: 79 },
  { state: "Kerala", label: "Kerala", x: 28, y: 82 },
];

export default function LiveLogistics() {
  const { pulse } = useSession();
  const shipments = useApi(() => api.getAdminShipments(), [pulse]);

  useInterval(shipments.refresh, 15_000);

  const all = shipments.data?.shipments ?? [];
  const moving = useMemo(
    () => all.filter((s: any) => ["accepted", "packed", "shipped"].includes(s.status)),
    [all]
  );

  const byRegion = useMemo(() => {
    const counts = new Map<string, number>();
    for (const shipment of moving) {
      const state: string = shipment.delivery_state ?? shipment.state ?? "";
      const region = REGIONS.find((r) => state && r.state.toLowerCase() === state.toLowerCase());
      if (region) counts.set(region.state, (counts.get(region.state) ?? 0) + 1);
    }
    return counts;
  }, [moving]);

  const placed = [...byRegion.values()].reduce((sum, n) => sum + n, 0);

  return (
    <Shell title="Live logistics" subtitle="Consignments on the move across the country, right now">
      <div className="grid gap-3 sm:grid-cols-4">
        <Stat label="On the move" value={count(moving.length)} tone="signal" icon={<Truck size={15} />} />
        <Stat label="Awaiting pickup" value={count(all.filter((s: any) => s.status === "packed").length)} />
        <Stat label="Out for delivery" value={count(all.filter((s: any) => s.status === "shipped").length)} tone="alert" />
        <Stat label="Delivered today" value={count(all.filter((s: any) => s.status === "delivered").length)} tone="good" />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1.3fr_1fr]">
        <Panel title="Where they are" subtitle="Placed by the delivery state on each consignment">
          <DataState state={shipments}>
            {() => (
              <div className="relative mx-auto aspect-[4/5] w-full max-w-md rounded-xl border border-[var(--surface-border)] bg-[var(--background)]">
                {REGIONS.map((region) => {
                  const n = byRegion.get(region.state) ?? 0;
                  return (
                    <div
                      key={region.state}
                      className="absolute -translate-x-1/2 -translate-y-1/2"
                      style={{ left: `${region.x + 18}%`, top: `${region.y}%` }}
                      title={`${region.label}: ${n} on the move`}
                    >
                      <span
                        className={
                          n > 0
                            ? "grid place-items-center rounded-full bg-[var(--accent)] text-[10px] font-bold text-slate-950"
                            : "block rounded-full bg-slate-700"
                        }
                        style={{
                          width: n > 0 ? `${Math.min(14 + n * 3, 30)}px` : "6px",
                          height: n > 0 ? `${Math.min(14 + n * 3, 30)}px` : "6px",
                        }}
                      >
                        {n > 0 ? n : ""}
                      </span>
                    </div>
                  );
                })}
                {placed === 0 && (
                  <p className="absolute inset-0 grid place-items-center px-6 text-center text-[12.5px] text-[var(--muted)]">
                    Nothing is on the move, or no consignment carries a delivery state.
                  </p>
                )}
              </div>
            )}
          </DataState>
        </Panel>

        <Panel title="In flight" subtitle="Newest movement first" padded={false}>
          <DataState state={shipments}>
            {() =>
              moving.length === 0 ? (
                <p className="px-4 py-10 text-center text-[13px] text-[var(--muted-light)]">
                  Every consignment is either waiting on a workshop or already delivered.
                </p>
              ) : (
                <ul className="max-h-[520px] divide-y divide-[var(--surface-border)] overflow-y-auto">
                  {moving.slice(0, 40).map((shipment: any) => (
                    <li key={shipment.id} className="px-4 py-2.5">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-[12.5px] font-medium text-slate-200">
                            {shipment.shop_name ?? "Workshop"}
                          </p>
                          <p className="tabular truncate text-[11px] text-[var(--muted)]">
                            {shipment.carrier ?? "Carrier to be assigned"}
                            {shipment.tracking_number ? ` · ${shipment.tracking_number}` : ""}
                          </p>
                        </div>
                        <Badge tone={tone.shipment(shipment.status)}>{titleCase(shipment.status)}</Badge>
                      </div>
                      <p className="mt-0.5 flex items-center gap-1 text-[11px] text-[var(--muted)]">
                        <MapPin size={11} />
                        {shipment.delivery_city ?? shipment.delivery_state ?? "Destination not recorded"} ·{" "}
                        {stamp(shipment.updated_at ?? shipment.created_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              )
            }
          </DataState>
        </Panel>
      </div>
    </Shell>
  );
}
