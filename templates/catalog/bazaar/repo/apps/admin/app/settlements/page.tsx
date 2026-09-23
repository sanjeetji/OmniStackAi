"use client";

import { useState } from "react";
import Link from "next/link";
import { FileCheck2, Plus } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, Button, DataState, ErrorNote, Stat, inputClass } from "../../components/ui";
import { useApi, useAction } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, inr, num, stamp, titleCase, tone } from "../../lib/format";

export default function Settlements() {
  const { pulse, notify } = useSession();
  const settlements = useApi(() => api.getAdminSettlements(), [pulse]);
  const shops = useApi(() => api.getAdminShops("verified"), []);
  const { run, busy, error } = useAction();
  const [shopId, setShopId] = useState("");

  const rows = settlements.data?.settlements ?? [];
  const pending = rows.filter((row: any) => row.status !== "processed");
  const owed = pending.reduce((sum: number, row: any) => sum + num(row.net_payout_cents), 0);

  async function generate() {
    const ok = await run(() => api.generateAdminSettlement(shopId));
    if (ok) {
      notify({ title: "Batch generated", detail: "Review it before approving", tone: "good" });
      setShopId("");
      settlements.refresh();
    }
  }

  async function approve(id: string) {
    const ok = await run(() => api.approveAdminSettlement(id));
    if (ok) {
      notify({ title: "Batch approved", detail: "The payout is posted to the ledger", tone: "good" });
      settlements.refresh();
    }
  }

  return (
    <Shell title="Settlements" subtitle="Batched payouts to workshops, approved by a person">
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Batches" value={count(rows.length)} icon={<FileCheck2 size={15} />} />
        <Stat label="Awaiting approval" value={count(pending.length)} tone={pending.length ? "alert" : "good"} />
        <Stat label="Value waiting" value={inr(owed)} tone="signal" hint="Across unapproved batches" />
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1.6fr_1fr]">
        <Panel title="Batches" subtitle="Newest first" padded={false}>
          <DataState state={settlements}>
            {() =>
              rows.length === 0 ? (
                <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                  No batch yet. Generate one for a verified workshop.
                </p>
              ) : (
                <Table head={["Batch", "Workshop", "Gross", "Commission", "Net payout", "Status", ""]}>
                  {rows.map((batch: any) => (
                    <Row key={batch.id}>
                      <Cell>
                        <Link href={`/settlements/${batch.id}`} className="tabular font-medium text-[var(--accent-light)] hover:underline">
                          {batch.batch_number ?? batch.id.slice(0, 8)}
                        </Link>
                        <p className="text-[11px] text-[var(--muted)]">{stamp(batch.created_at)}</p>
                      </Cell>
                      <Cell>{batch.shop_name ?? "—"}</Cell>
                      <Cell align="right" muted>{inr(batch.gross_amount_cents)}</Cell>
                      <Cell align="right" muted>− {inr(batch.commission_cents)}</Cell>
                      <Cell align="right">{inr(batch.net_payout_cents)}</Cell>
                      <Cell>
                        <Badge tone={tone.settlement(batch.status)}>{titleCase(batch.status)}</Badge>
                      </Cell>
                      <Cell align="right">
                        {batch.status !== "processed" && (
                          <Button size="sm" disabled={busy} onClick={() => void approve(batch.id)}>
                            Approve
                          </Button>
                        )}
                      </Cell>
                    </Row>
                  ))}
                </Table>
              )
            }
          </DataState>
        </Panel>

        <Panel title="Generate a batch" subtitle="Sweeps everything a workshop has earned and not been paid">
          <DataState state={shops}>
            {(data) => (
              <>
                <select className={inputClass} value={shopId} onChange={(event) => setShopId(event.target.value)}>
                  <option value="">Choose a workshop</option>
                  {data.shops.map((shop) => (
                    <option key={shop.id} value={shop.id}>
                      {shop.name}
                    </option>
                  ))}
                </select>
                <div className="mt-2">
                  <Button disabled={busy || !shopId} onClick={() => void generate()}>
                    <Plus size={13} /> Generate
                  </Button>
                </div>
              </>
            )}
          </DataState>
          <p className="mt-3 border-t border-[var(--surface-border)] pt-2.5 text-[11.5px] leading-relaxed text-[var(--muted)]">
            Generating a batch does not move money. Approving it posts the payout to the ledger and
            writes the operator's name to the audit trail.
          </p>
        </Panel>
      </div>
    </Shell>
  );
}
