"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Pause, Play, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

/** PC-011: the super_admin console — overview, the paid-work switch, accounts and the audit log. */
type Overview = {
  users_total: number; users_by_plan: Record<string, number>; credits_spent_24h: number; credits_spent_7d: number;
  credits_granted_7d: number; top_spenders_24h: { email: string; spent: number }[]; paid_model_work: "running" | "paused";
};
type Account = { id: string; email: string; name: string; role: string; plan: string; credit_balance: number; spent_24h: number };
type AuditEntry = { id: number; actor: string; action: string; target: string; detail: Record<string, unknown>; at: string };
const PLANS = ["free", "developer", "pro", "agency", "enterprise"];

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/admin/${path}`, { cache: "no-store", headers: { "Content-Type": "application/json" }, ...init });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((body as { error?: string }).error || `Request failed (${res.status})`);
  return body as T;
}

export function AdminConsole({ selfId }: { selfId: string }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [query, setQuery] = useState("");
  const [note, setNote] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api<Overview>("overview"),
      api<{ users: Account[] }>(`users?q=${encodeURIComponent(query)}`),
      api<{ entries: AuditEntry[] }>("audit"),
    ])
      .then(([o, u, a]) => {
        if (cancelled) return;
        setOverview(o);
        setAccounts(u.users);
        setAudit(a.entries);
      })
      .catch((error: Error) => {
        if (!cancelled) setNote({ tone: "error", text: error.message });
      });
    return () => {
      cancelled = true;
    };
  }, [query, refresh]);

  const act = useCallback(async (label: string, run: () => Promise<unknown>) => {
    setNote(null);
    try {
      await run();
      setNote({ tone: "ok", text: label });
      setRefresh((n) => n + 1);
    } catch (error) {
      setNote({ tone: "error", text: error instanceof Error ? error.message : "That did not work." });
    }
  }, []);

  const grant = (account: Account) => {
    const amount = Number(window.prompt(`Credits to add for ${account.email} (negative to deduct):`, "1000"));
    if (!amount) return;
    const reason = window.prompt("Reason (kept in the audit log):", "beta credit");
    if (!reason) return;
    void act(`${amount > 0 ? "Added" : "Deducted"} ${Math.abs(amount)} credits for ${account.email}.`, () =>
      api(`users/${account.id}/credits`, { method: "POST", body: JSON.stringify({ amount, reason }) }));
  };

  if (!overview) {
    return <p className="mt-8 flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" /> Loading…</p>;
  }
  const paused = overview.paid_model_work === "paused";

  return (
    <div className="mt-6 space-y-6">
      {note && (
        <p role={note.tone === "error" ? "alert" : "status"}
           className={note.tone === "error" ? "text-sm text-destructive" : "text-sm text-emerald-600 dark:text-emerald-400"}>{note.text}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card><CardHeader><CardDescription>Accounts</CardDescription><CardTitle className="text-2xl tabular-nums">{overview.users_total}</CardTitle></CardHeader>
          <CardContent className="text-xs text-muted-foreground">{Object.entries(overview.users_by_plan).map(([p, n]) => `${p} ${n}`).join(" · ")}</CardContent></Card>
        <Card><CardHeader><CardDescription>Credits spent, 24 h</CardDescription><CardTitle className="text-2xl tabular-nums">{overview.credits_spent_24h.toLocaleString("en-US")}</CardTitle></CardHeader>
          <CardContent className="text-xs text-muted-foreground">7 days: {overview.credits_spent_7d.toLocaleString("en-US")}</CardContent></Card>
        <Card><CardHeader><CardDescription>Credits added, 7 days</CardDescription><CardTitle className="text-2xl tabular-nums">{overview.credits_granted_7d.toLocaleString("en-US")}</CardTitle></CardHeader></Card>
        <Card className={paused ? "border-destructive" : undefined}>
          <CardHeader><CardDescription>Paid model work</CardDescription>
            <CardTitle className="flex items-center gap-2 text-2xl">{paused ? "Paused" : "Running"}</CardTitle></CardHeader>
          <CardContent>
            <Button size="sm" variant={paused ? "default" : "destructive"}
              onClick={() => { if (paused || window.confirm("Pause all paid model work for every user?")) void act(paused ? "Paid model work resumed." : "Paid model work paused.", () => api("settings/paid-model-work", { method: "PUT", body: JSON.stringify({ paused: !paused }) })); }}>
              {paused ? <Play className="size-3.5" aria-hidden="true" /> : <Pause className="size-3.5" aria-hidden="true" />} {paused ? "Resume" : "Pause"}
            </Button>
          </CardContent>
        </Card>
      </div>

      {overview.top_spenders_24h.length > 0 && (
        <p className="text-sm text-muted-foreground">Top spenders today: {overview.top_spenders_24h.map((s) => `${s.email} (${s.spent})`).join(", ")}</p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Accounts</CardTitle>
          <div className="relative mt-2 max-w-sm">
            <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" aria-hidden="true" />
            <Input aria-label="Search accounts" placeholder="Search by email or name" className="pl-8"
              onKeyDown={(e) => { if (e.key === "Enter") setQuery((e.target as HTMLInputElement).value); }} />
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="text-left text-xs text-muted-foreground">
              <tr><th className="py-2 font-medium">Account</th><th className="font-medium">Plan</th><th className="font-medium">Role</th>
                <th className="text-right font-medium">Credits</th><th className="text-right font-medium">Spent 24 h</th><th /></tr>
            </thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="py-2"><div className="font-medium">{a.email}</div><div className="text-xs text-muted-foreground">{a.name}</div></td>
                  <td>
                    <select aria-label={`Plan for ${a.email}`} className="rounded-md border bg-background px-2 py-1 text-sm" value={a.plan}
                      onChange={(e) => void act(`${a.email} is now on ${e.target.value}.`, () => api(`users/${a.id}/plan`, { method: "PUT", body: JSON.stringify({ plan: e.target.value }) }))}>
                      {PLANS.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </td>
                  <td>
                    <select aria-label={`Role for ${a.email}`} className="rounded-md border bg-background px-2 py-1 text-sm" value={a.role} disabled={a.id === selfId}
                      onChange={(e) => void act(`${a.email} is now ${e.target.value}.`, () => api(`users/${a.id}/role`, { method: "PUT", body: JSON.stringify({ role: e.target.value }) }))}>
                      <option value="user">user</option><option value="super_admin">super_admin</option>
                    </select>
                  </td>
                  <td className="text-right tabular-nums">{a.credit_balance.toLocaleString("en-US")}</td>
                  <td className="text-right tabular-nums">{a.spent_24h.toLocaleString("en-US")}</td>
                  <td className="text-right"><Button size="sm" variant="outline" onClick={() => grant(a)}>Credits…</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Audit log</CardTitle><CardDescription>The last 100 admin actions.</CardDescription></CardHeader>
        <CardContent>
          <ul className="space-y-1 text-xs">
            {audit.length === 0 && <li className="text-muted-foreground">Nothing yet.</li>}
            {audit.map((e) => (
              <li key={e.id} className="flex flex-wrap gap-x-2">
                <span className="tabular-nums text-muted-foreground">{new Date(e.at).toLocaleString()}</span>
                <span className="font-medium">{e.actor}</span>
                <Badge variant="outline">{e.action}</Badge>
                {e.target && <span>{e.target}</span>}
                <span className="text-muted-foreground">{JSON.stringify(e.detail)}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
