"use client";

import { useMemo, useState } from "react";
import { Search, ShieldAlert } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, DataState, Stat, inputClass } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { useSession } from "../../lib/session";
import { count, stamp, titleCase } from "../../lib/format";

const ACTION_TONES: Record<string, string> = {
  cancel_order: "danger",
  delete_review: "danger",
  update_kyc: "signal",
  update_commission: "alert",
  generate_settlement_batch: "signal",
  approve_settlement: "good",
  create_coupon: "neutral",
  toggle_coupon: "neutral",
  update_settings: "alert",
};

export default function AuditTrail() {
  const { pulse } = useSession();
  const [search, setSearch] = useState("");
  const logs = useApi(() => api.getAdminAuditLogs(), [pulse]);

  const rows = logs.data?.auditLogs ?? [];
  const shown = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return rows;
    return rows.filter(
      (row: any) =>
        (row.actor_name ?? "").toLowerCase().includes(term) ||
        (row.action ?? "").toLowerCase().includes(term) ||
        (row.entity_type ?? "").toLowerCase().includes(term)
    );
  }, [rows, search]);

  const actors = new Set(rows.map((row: any) => row.actor_id)).size;
  const destructive = rows.filter((row: any) =>
    ["cancel_order", "delete_review"].includes(row.action)
  ).length;

  return (
    <Shell
      title="Audit trail"
      subtitle="What operators did, in order. Nothing here can be edited or removed."
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Entries" value={count(rows.length)} icon={<ShieldAlert size={15} />} />
        <Stat label="Operators involved" value={count(actors)} hint="Distinct accounts in this view" />
        <Stat
          label="Destructive actions"
          value={count(destructive)}
          tone={destructive > 0 ? "alert" : "plain"}
          hint="Cancellations and removals"
        />
      </div>

      <Panel
        className="mt-3"
        padded={false}
        title="Operator actions"
        actions={
          <div className="relative w-64">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Operator, action or entity"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        }
      >
        <DataState state={logs}>
          {() =>
            shown.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--muted-light)]">
                Nothing recorded for that search.
              </p>
            ) : (
              <Table head={["When", "Operator", "Action", "Entity", "Detail"]}>
                {shown.map((entry: any) => (
                  <Row key={entry.id}>
                    <Cell mono muted>{stamp(entry.created_at)}</Cell>
                    <Cell>{entry.actor_name ?? entry.actor_email ?? entry.actor_id?.slice(0, 8)}</Cell>
                    <Cell>
                      <Badge tone={ACTION_TONES[entry.action] ?? "neutral"}>{titleCase(entry.action)}</Badge>
                    </Cell>
                    <Cell mono muted>
                      {entry.entity_type} {String(entry.entity_id ?? "").slice(0, 8)}
                    </Cell>
                    <Cell muted>
                      {entry.metadata_json
                        ? Object.entries(
                            typeof entry.metadata_json === "string"
                              ? JSON.parse(entry.metadata_json)
                              : entry.metadata_json
                          )
                            .map(([key, value]) => `${key}: ${value}`)
                            .join(" · ")
                            .slice(0, 90)
                        : "—"}
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
