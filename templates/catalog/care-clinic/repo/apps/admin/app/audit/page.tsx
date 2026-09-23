"use client";

import { useMemo, useState } from "react";
import { Search, ShieldAlert } from "lucide-react";
import { defaultApiClient } from "@careclinic/shared";
import { Shell } from "../../components/shell";
import { Panel, Table, Row, Cell, Badge, DataState, Stat, inputClass } from "../../components/ui";
import { useApi } from "../../lib/use-api";
import { stamp, titleCase } from "../../lib/format";

const ACCESS_TONES: Record<string, string> = {
  view_chart: "neutral",
  view_soap: "neutral",
  view_prescription: "neutral",
  view_labs: "neutral",
  edit_soap: "alert",
  issue_prescription: "signal",
  order_labs: "signal",
};

export default function AuditTrail() {
  const [search, setSearch] = useState("");
  const logs = useApi(() => defaultApiClient.getAuditLogs(search || undefined), [search]);

  const rows = logs.data?.auditLogs ?? [];
  const actors = useMemo(() => new Set(rows.map((row) => row.accessed_by_user_id)).size, [rows]);
  const writes = rows.filter((row) => row.access_type === "edit_soap" || row.access_type === "issue_prescription").length;

  return (
    <Shell
      title="Chart access audit"
      subtitle="Every electronic record opened, by whom and when. The log is append-only."
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Entries shown" value={rows.length} hint="Most recent 100" icon={<ShieldAlert size={15} />} />
        <Stat label="Staff involved" value={actors} hint="Distinct accounts in this view" />
        <Stat label="Changes to a record" value={writes} tone={writes > 0 ? "alert" : "plain"} hint="SOAP edits and prescriptions issued" />
      </div>

      <Panel
        className="mt-3"
        padded={false}
        title="Access log"
        subtitle="Nothing in this list can be edited or removed from the console"
        actions={
          <div className="relative w-64">
            <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-ink-subtle)]" />
            <input
              className={`${inputClass} pl-8`}
              placeholder="Staff or patient name"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        }
      >
        <DataState state={logs}>
          {(data) =>
            data.auditLogs.length === 0 ? (
              <p className="px-4 py-12 text-center text-[13px] text-[var(--color-ink-muted)]">
                No access recorded for that search.
              </p>
            ) : (
              <Table head={["When", "Who", "Role", "Action", "Patient", "Record", "From"]}>
                {data.auditLogs.map((entry) => (
                  <Row key={entry.id}>
                    <Cell mono muted>{stamp(entry.accessed_at)}</Cell>
                    <Cell>{entry.actor_name}</Cell>
                    <Cell muted>{titleCase(entry.actor_role)}</Cell>
                    <Cell>
                      <Badge tone={ACCESS_TONES[entry.access_type] ?? "neutral"}>{titleCase(entry.access_type)}</Badge>
                    </Cell>
                    <Cell>{entry.patient_name}</Cell>
                    <Cell mono muted>{entry.resource_id ? `${entry.resource_id.slice(0, 8)}…` : "—"}</Cell>
                    <Cell mono muted>{entry.ip_address ?? "—"}</Cell>
                  </Row>
                ))}
              </Table>
            )
          }
        </DataState>
      </Panel>

      <p className="mt-3 text-[11.5px] leading-relaxed text-[var(--color-ink-muted)]">
        The API writes a row here inside the same transaction that reads a chart, so an access cannot happen
        without being recorded. Retention and export policy live with the clinic's compliance officer.
      </p>
    </Shell>
  );
}
