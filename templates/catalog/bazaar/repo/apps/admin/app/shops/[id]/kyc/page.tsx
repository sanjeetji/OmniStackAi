"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Ban, CheckCircle2, FileText, ShieldCheck } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../../../components/shell";
import { Panel, Badge, Button, DataState, ErrorNote } from "../../../../components/ui";
import { useApi, useAction } from "../../../../lib/use-api";
import { useSession } from "../../../../lib/session";
import { day, titleCase, tone } from "../../../../lib/format";

/** The checks an operator confirms before a workshop may sell. */
const CHECKLIST = [
  { key: "identity", label: "Artisan identity", detail: "Name on the account matches the document on file." },
  { key: "address", label: "Workshop address", detail: "A real, reachable address for pickups and returns." },
  { key: "bank", label: "Bank account", detail: "The settlement account belongs to the workshop." },
  { key: "gi", label: "Craft provenance", detail: "GI tag or cluster membership, where the craft claims one." },
];

export default function KycReview({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { notify } = useSession();
  const shop = useApi(() => api.getAdminShop(id), [id]);
  const { run, busy, error } = useAction();
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  const allChecked = CHECKLIST.every((item) => checked[item.key]);

  async function decide(status: "verified" | "rejected") {
    const ok = await run(() => api.updateShopKyc(id, status));
    if (ok) {
      notify({
        title: status === "verified" ? "Workshop verified" : "Workshop rejected",
        detail: status === "verified" ? "It may start selling" : "It cannot list until resubmitted",
        tone: status === "verified" ? "good" : "alert",
      });
      router.push(`/shops/${id}`);
    }
  }

  return (
    <Shell
      title="KYC review"
      subtitle="A workshop cannot sell until an operator has verified it"
      actions={
        <Button href={`/shops/${id}`} variant="quiet" size="sm">
          <ArrowLeft size={13} /> Workshop
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <DataState state={shop}>
        {(data) => (
          <div className="mx-auto grid max-w-4xl gap-3 lg:grid-cols-[1fr_1fr]">
            <Panel title="Who is applying">
              <h2 className="text-[18px] font-semibold tracking-tight text-slate-100">{data.shop.name}</h2>
              <p className="tabular text-[12px] text-[var(--muted)]">{data.shop.slug}</p>
              <div className="mt-2">
                <Badge tone={tone.kyc(data.shop.kyc_status)}>{titleCase(data.shop.kyc_status)}</Badge>
              </div>

              <dl className="mt-4 space-y-2 text-[12.5px]">
                {[
                  ["Applied", day(data.shop.created_at)],
                  ["Bank", data.shop.bank_name ?? "Not on file"],
                  ["Account", data.shop.bank_account_last4 ? `•••• ${data.shop.bank_account_last4}` : "Not on file"],
                  ["IFSC", data.shop.bank_ifsc_code ?? "Not on file"],
                  ["Listings prepared", String(data.products.length)],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-4">
                    <dt className="shrink-0 text-[var(--muted-light)]">{label}</dt>
                    <dd className="text-right text-slate-200">{value}</dd>
                  </div>
                ))}
              </dl>

              {data.shop.description && (
                <p className="mt-3 rounded-lg bg-[var(--background)] p-2.5 text-[12px] leading-relaxed text-[var(--muted-light)]">
                  {data.shop.description}
                </p>
              )}
            </Panel>

            <Panel title="What you are confirming" subtitle="Tick each before deciding">
              <ul className="space-y-2.5">
                {CHECKLIST.map((item) => (
                  <li key={item.key}>
                    <label className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-[var(--surface-border)] p-2.5 hover:bg-slate-800/40">
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 accent-[var(--accent)]"
                        checked={Boolean(checked[item.key])}
                        onChange={(event) => setChecked({ ...checked, [item.key]: event.target.checked })}
                      />
                      <span>
                        <span className="block text-[12.5px] font-medium text-slate-200">{item.label}</span>
                        <span className="block text-[11.5px] text-[var(--muted-light)]">{item.detail}</span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>

              <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--surface-border)] pt-3">
                <Button disabled={busy || !allChecked} onClick={() => void decide("verified")}>
                  <CheckCircle2 size={13} /> Verify and allow selling
                </Button>
                <Button variant="danger" disabled={busy} onClick={() => void decide("rejected")}>
                  <Ban size={13} /> Reject
                </Button>
              </div>
              <p className="mt-2 flex items-start gap-1.5 text-[11.5px] text-[var(--muted)]">
                <FileText size={12} className="mt-0.5 shrink-0" />
                Your decision is written to the audit trail with your operator account against it.
              </p>
            </Panel>
          </div>
        )}
      </DataState>
    </Shell>
  );
}
