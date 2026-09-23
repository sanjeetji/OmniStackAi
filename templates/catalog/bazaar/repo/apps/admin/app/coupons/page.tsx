"use client";

import Link from "next/link";
import { Plus, Tag, ToggleLeft, ToggleRight } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Stat } from "../../components/ui";
import { useApi, useAction } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, day, inr, num, percent } from "../../lib/format";

export default function Coupons() {
  const { pulse, notify } = useSession();
  const coupons = useApi(() => api.getAdminCoupons(), [pulse]);
  const { run, busy, error } = useAction();

  const rows = coupons.data?.coupons ?? [];
  const live = rows.filter((row: any) => row.is_active).length;
  const given = rows.reduce((sum: number, row: any) => sum + num(row.total_discount_cents), 0);

  async function toggle(id: string, active: boolean) {
    const ok = await run(() => api.toggleAdminCoupon(id));
    if (ok) {
      notify({ title: active ? "Coupon paused" : "Coupon resumed", tone: "info" });
      coupons.refresh();
    }
  }

  return (
    <Shell
      title="Coupons"
      subtitle="Promotions shoppers can apply at checkout"
      actions={
        <Button href="/coupons/new" size="sm">
          <Plus size={13} /> New coupon
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Coupons" value={count(rows.length)} icon={<Tag size={15} />} />
        <Stat label="Live now" value={count(live)} tone="good" hint={`${percent(live, rows.length)} of all`} />
        <Stat label="Discount given" value={inr(given)} tone="alert" hint="Across every redemption" />
      </div>

      <Panel className="mt-3" padded={false}>
        <DataState state={coupons}>
          {() =>
            rows.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                No coupon yet. Create one to run a promotion.
              </p>
            ) : (
              <Table head={["Code", "Discount", "Minimum order", "Used", "Valid until", "Status", ""]}>
                {rows.map((coupon: any) => (
                  <Row key={coupon.id}>
                    <Cell mono>
                      <span className="font-semibold text-slate-100">{coupon.code}</span>
                      {coupon.description && (
                        <p className="text-[11px] font-normal text-[var(--muted)]">{coupon.description}</p>
                      )}
                    </Cell>
                    <Cell>
                      {coupon.discount_type === "percentage"
                        ? `${coupon.discount_value}%`
                        : inr(coupon.discount_value_cents ?? coupon.discount_value)}
                      {coupon.max_discount_cents ? (
                        <span className="block text-[11px] text-[var(--muted)]">
                          capped at {inr(coupon.max_discount_cents)}
                        </span>
                      ) : null}
                    </Cell>
                    <Cell align="right" muted>{coupon.min_order_cents ? inr(coupon.min_order_cents) : "—"}</Cell>
                    <Cell align="right" muted>
                      {count(coupon.usage_count ?? 0)}
                      {coupon.usage_limit ? ` / ${count(coupon.usage_limit)}` : ""}
                    </Cell>
                    <Cell mono muted>{coupon.expires_at ? day(coupon.expires_at) : "No end date"}</Cell>
                    <Cell>
                      <Badge tone={coupon.is_active ? "good" : "neutral"}>
                        {coupon.is_active ? "Live" : "Paused"}
                      </Badge>
                    </Cell>
                    <Cell align="right">
                      <Button
                        size="sm"
                        variant="quiet"
                        disabled={busy}
                        onClick={() => void toggle(coupon.id, coupon.is_active)}
                      >
                        {coupon.is_active ? <ToggleRight size={13} /> : <ToggleLeft size={13} />}
                        {coupon.is_active ? "Pause" : "Resume"}
                      </Button>
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
