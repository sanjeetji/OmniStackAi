"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search, ShieldCheck, Star, Store } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, Stat, inputClass } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, day, percent, titleCase, tone } from "../../lib/format";

const FILTERS = [
  { id: "", label: "Every workshop" },
  { id: "pending", label: "Awaiting KYC" },
  { id: "verified", label: "Verified" },
  { id: "rejected", label: "Rejected" },
  { id: "suspended", label: "Suspended" },
];

export default function Workshops() {
  const { pulse } = useSession();
  const [kyc, setKyc] = useState("");
  const [search, setSearch] = useState("");
  const shops = useApi(() => api.getAdminShops(kyc || undefined), [kyc, pulse]);

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase();
    const list = shops.data?.shops ?? [];
    if (!term) return list;
    return list.filter(
      (shop) => shop.name.toLowerCase().includes(term) || shop.slug.toLowerCase().includes(term)
    );
  }, [shops.data, search]);

  const all = shops.data?.shops ?? [];
  const pending = all.filter((shop) => shop.kyc_status === "pending").length;

  return (
    <Shell title="Workshops" subtitle="Artisan vendors, their credentials and their commission">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Workshops listed" value={count(rows.length)} icon={<Store size={15} />} />
        <Stat
          label="Awaiting KYC"
          value={count(pending)}
          tone={pending > 0 ? "alert" : "good"}
          hint={pending > 0 ? "Blocked from selling until verified" : "Everyone is verified"}
          icon={<ShieldCheck size={15} />}
        />
        <Stat
          label="Active"
          value={percent(all.filter((shop) => shop.is_active).length, all.length)}
          hint="Of every workshop on the platform"
        />
      </div>

      <Panel className="mt-3" padded={false}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--surface-border)] px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((option) => (
              <button
                key={option.id || "all"}
                onClick={() => setKyc(option.id)}
                className={
                  kyc === option.id
                    ? "rounded-lg bg-[var(--accent)] px-2.5 py-1 text-[12px] font-semibold text-slate-950"
                    : "rounded-lg border border-[var(--surface-border)] bg-[var(--surface-elevated)] px-2.5 py-1 text-[12px] font-medium text-[var(--muted-light)] hover:bg-slate-700"
                }
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="relative w-full max-w-xs">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Workshop name or handle"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        <DataState state={shops}>
          {() =>
            rows.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                No workshop matches that filter.
              </p>
            ) : (
              <Table head={["Workshop", "Handle", "KYC", "Commission", "Rating", "Joined", ""]}>
                {rows.map((shop) => (
                  <Row key={shop.id}>
                    <Cell>
                      <Link href={`/shops/${shop.id}`} className="font-medium text-slate-100 hover:text-[var(--accent-light)]">
                        {shop.name}
                      </Link>
                      {shop.tagline && <p className="truncate text-[11px] text-[var(--muted)]">{shop.tagline}</p>}
                    </Cell>
                    <Cell mono muted>{shop.slug}</Cell>
                    <Cell>
                      <Badge tone={tone.kyc(shop.kyc_status)}>{titleCase(shop.kyc_status)}</Badge>
                    </Cell>
                    <Cell align="right" muted>{(shop.commission_rate_basis_points / 100).toFixed(1)}%</Cell>
                    <Cell align="right">
                      <span className="inline-flex items-center gap-1 tabular">
                        <Star size={12} className="fill-amber-400 text-amber-400" />
                        {Number(shop.rating_avg).toFixed(1)}
                        <span className="text-[11px] text-[var(--muted)]">({shop.rating_count})</span>
                      </span>
                    </Cell>
                    <Cell mono muted>{day(shop.created_at)}</Cell>
                    <Cell align="right">
                      {shop.kyc_status === "pending" ? (
                        <Button size="sm" href={`/shops/${shop.id}/kyc`}>
                          Review KYC
                        </Button>
                      ) : (
                        <Link href={`/shops/${shop.id}`} className="text-[12px] font-semibold text-[var(--accent-light)] hover:underline">
                          Open
                        </Link>
                      )}
                    </Cell>
                  </Row>
                ))}
              </Table>
            )
          }
        </DataState>
      </Panel>
    </Shell>
  );
}
