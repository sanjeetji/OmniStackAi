"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ScrollText } from "lucide-react";
import { dateTimeLabel } from "@ridenow/shared";
import { Shell } from "@/components/shell";
import { Badge, Button, Empty, ErrorState, LoadingRows, PageHeader, Panel, SearchBox, Table, type Tone, td, th } from "@/components/ui";
import { api } from "@/lib/api";
import type { AuditEntry } from "@/lib/types";
import { errorText } from "@/lib/use-api";

const PAGE = 50;

const ACTION: Record<string, { label: string; tone: Tone }> = {
  "trip.cancel": { label: "Cancelled a trip", tone: "bad" },
  "trip.refund": { label: "Refunded a trip", tone: "warn" },
  "user.suspended": { label: "Suspended an account", tone: "bad" },
  "user.active": { label: "Reactivated an account", tone: "ok" },
  "driver.approved": { label: "Approved a driver", tone: "ok" },
  "driver.suspended": { label: "Paused a driver", tone: "bad" },
  "driver.pending": { label: "Sent a driver back to review", tone: "warn" },
  "document.approved": { label: "Approved a document", tone: "ok" },
  "document.rejected": { label: "Rejected a document", tone: "bad" },
  "pricing.update": { label: "Changed pricing", tone: "info" },
  "zone.update": { label: "Changed a surge zone", tone: "info" },
  "promo.create": { label: "Created a promo code", tone: "signal" },
  "promo.pause": { label: "Paused a promo code", tone: "warn" },
  "promo.resume": { label: "Resumed a promo code", tone: "ok" },
  "payout.paid": { label: "Paid a payout", tone: "ok" },
  "payout.rejected": { label: "Rejected a payout", tone: "bad" },
  "ticket.update": { label: "Updated a ticket", tone: "neutral" },
  "wallet.adjust": { label: "Adjusted a wallet", tone: "warn" },
};

function entityLink(entry: AuditEntry): string | null {
  switch (entry.entity) {
    case "trip": return `/trips/${entry.entity_id}`;
    case "rider": return `/riders/${entry.entity_id}`;
    case "driver": return `/drivers/${entry.entity_id}`;
    case "ticket": return `/tickets/${entry.entity_id}`;
    case "payout": return "/payouts";
    case "promo": return "/promos";
    case "zone": return "/zones";
    case "vehicle_type": return "/pricing";
    default: return null;
  }
}

function summary(detail: Record<string, unknown>): string {
  return Object.entries(detail ?? {})
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`)
    .join(" · ");
}

export default function AuditPage() {
  return (
    <Shell>
      <AuditView />
    </Shell>
  );
}

function AuditView() {
  const [entries, setEntries] = useState<AuditEntry[] | null>(null);
  const [more, setMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  async function load(offset: number) {
    const result = await api.get<{ entries: AuditEntry[] }>(`/admin/audit?limit=${PAGE}&offset=${offset}`);
    setMore(result.entries.length === PAGE);
    return result.entries;
  }

  const first = () => {
    setError(null);
    load(0).then(setEntries).catch((err) => setError(errorText(err, "Couldn't load the audit log.")));
  };
  useEffect(first, []);

  const shown = (entries ?? []).filter((e) => {
    if (!q.trim()) return true;
    const hay = `${e.action} ${ACTION[e.action]?.label ?? ""} ${e.actor_name ?? ""} ${e.entity} ${e.entity_id} ${summary(e.detail)}`.toLowerCase();
    return hay.includes(q.trim().toLowerCase());
  });

  return (
    <>
      <PageHeader title="Audit log" description="Every operator action that changes money, accounts, pricing or tickets, with who did it and when. Entries cannot be edited." />
      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line p-3">
          <p className="num text-[13px] text-muted">{entries ? `${entries.length} entries loaded` : " "}</p>
          <SearchBox value={q} onChange={setQ} placeholder="Filter by action, operator or detail" label="Filter the audit log" />
        </div>
        {error && !entries ? (
          <div className="p-4"><ErrorState message={error} onRetry={first} /></div>
        ) : !entries ? (
          <LoadingRows label="Loading the audit log" />
        ) : shown.length === 0 ? (
          <Empty icon={<ScrollText className="size-5" />} title={q ? "Nothing matches" : "No operator actions yet"} body={q ? "Try another word." : "Refunds, approvals, pricing changes and payouts are recorded here."} />
        ) : (
          <>
            <Table label="Audit log">
              <thead>
                <tr>
                  <th className={th}>When</th>
                  <th className={th}>Operator</th>
                  <th className={th}>Action</th>
                  <th className={th}>On</th>
                  <th className={th}>Detail</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((e) => {
                  const meta = ACTION[e.action] ?? { label: e.action, tone: "neutral" as Tone };
                  const href = entityLink(e);
                  return (
                    <tr key={e.id}>
                      <td className={`${td} whitespace-nowrap text-ink-2`}>{dateTimeLabel(e.at)}</td>
                      <td className={`${td} whitespace-nowrap`}>{e.actor_name ?? "System"}</td>
                      <td className={td}><Badge tone={meta.tone}>{meta.label}</Badge></td>
                      <td className={`${td} whitespace-nowrap`}>
                        {href ? <Link href={href} className="text-signal hover:underline">{e.entity.replace("_", " ")}</Link> : e.entity.replace("_", " ")}
                        <span className="ml-1.5 font-mono text-xs text-muted">{e.entity_id.length > 12 ? `${e.entity_id.slice(0, 8)}…` : e.entity_id}</span>
                      </td>
                      <td className={`${td} max-w-96 truncate text-ink-2`} title={summary(e.detail)}>{summary(e.detail) || "–"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
            {more ? (
              <div className="p-3">
                <Button
                  variant="secondary"
                  busy={loadingMore}
                  onClick={async () => {
                    setLoadingMore(true);
                    try {
                      const next = await load(entries.length);
                      setEntries([...entries, ...next]);
                    } catch (err) {
                      setError(errorText(err));
                    } finally {
                      setLoadingMore(false);
                    }
                  }}
                >
                  Load older entries
                </Button>
              </div>
            ) : null}
          </>
        )}
      </Panel>
    </>
  );
}
