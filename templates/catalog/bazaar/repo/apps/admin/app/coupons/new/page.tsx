"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Tag } from "lucide-react";
import { api } from "@bazaar/shared";
import { Shell } from "../../../components/shell";
import { Panel, Button, ErrorNote, Field, inputClass } from "../../../components/ui";
import { useAction } from "../../../lib/use-api";
import { useSession } from "../../../lib/session";
import { inr } from "../../../lib/format";

export default function NewCoupon() {
  const router = useRouter();
  const { notify } = useSession();
  const { run, busy, error } = useAction();

  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [discountType, setDiscountType] = useState<"percentage" | "fixed">("percentage");
  const [value, setValue] = useState("10");
  const [minOrder, setMinOrder] = useState("");
  const [maxDiscount, setMaxDiscount] = useState("");
  const [usageLimit, setUsageLimit] = useState("");
  const [validUntil, setValidUntil] = useState("");

  async function create() {
    const ok = await run(() =>
      api.createAdminCoupon({
        code: code.trim().toUpperCase(),
        description: description.trim() || undefined,
        discountType,
        discountValue: Number(value),
        minOrderCents: minOrder ? Math.round(Number(minOrder) * 100) : undefined,
        maxDiscountCents: maxDiscount ? Math.round(Number(maxDiscount) * 100) : undefined,
        usageLimit: usageLimit ? Number(usageLimit) : undefined,
        expiresAt: validUntil || undefined,
      })
    );
    if (ok) {
      notify({ title: "Coupon created", detail: code.trim().toUpperCase(), tone: "good" });
      router.push("/coupons");
    }
  }

  const example = 250000; // ₹2,500 basket
  const preview =
    discountType === "percentage"
      ? Math.min(
          Math.round((example * Number(value || 0)) / 100),
          maxDiscount ? Math.round(Number(maxDiscount) * 100) : Number.MAX_SAFE_INTEGER
        )
      : Math.round(Number(value || 0) * 100);

  return (
    <Shell
      title="New coupon"
      subtitle="Shoppers apply it at checkout; the API validates it before the order is priced"
      actions={
        <Button href="/coupons" variant="quiet" size="sm">
          <ArrowLeft size={13} /> Coupons
        </Button>
      }
    >
      {error && <div className="mb-3"><ErrorNote message={error} /></div>}

      <div className="mx-auto grid max-w-3xl gap-3 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="The coupon">
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              void create();
            }}
          >
            <Field label="Code" hint="What the shopper types. Upper case, no spaces.">
              <input
                className={`${inputClass} uppercase`}
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\s/g, ""))}
                placeholder="FESTIVE25"
                required
              />
            </Field>

            <Field label="Description" hint="Shown in the coupon list, not to shoppers.">
              <input
                className={inputClass}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Diwali campaign"
              />
            </Field>

            <div className="grid grid-cols-2 gap-2">
              <Field label="Kind">
                <select
                  className={inputClass}
                  value={discountType}
                  onChange={(event) => setDiscountType(event.target.value as "percentage" | "fixed")}
                >
                  <option value="percentage">Percentage off</option>
                  <option value="fixed">Fixed amount off</option>
                </select>
              </Field>
              <Field label={discountType === "percentage" ? "Percent" : "Rupees"}>
                <input
                  className={inputClass}
                  type="number"
                  min="1"
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  required
                />
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Field label="Minimum order (₹)" hint="Leave blank for no minimum.">
                <input className={inputClass} type="number" min="0" value={minOrder} onChange={(event) => setMinOrder(event.target.value)} />
              </Field>
              {discountType === "percentage" && (
                <Field label="Cap the discount at (₹)">
                  <input className={inputClass} type="number" min="0" value={maxDiscount} onChange={(event) => setMaxDiscount(event.target.value)} />
                </Field>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Field label="Total redemptions" hint="Blank means unlimited.">
                <input className={inputClass} type="number" min="1" value={usageLimit} onChange={(event) => setUsageLimit(event.target.value)} />
              </Field>
              <Field label="Valid until">
                <input className={inputClass} type="date" value={validUntil} onChange={(event) => setValidUntil(event.target.value)} />
              </Field>
            </div>

            <Button type="submit" disabled={busy || !code.trim() || !value}>
              <Tag size={13} /> {busy ? "Creating" : "Create the coupon"}
            </Button>
          </form>
        </Panel>

        <Panel title="On a ₹2,500 basket" subtitle="What a shopper would see">
          <div className="space-y-2 text-[13px]">
            <div className="flex justify-between">
              <span className="text-[var(--muted-light)]">Basket</span>
              <span className="tabular text-slate-200">{inr(example)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--muted-light)]">{code.trim().toUpperCase() || "COUPON"}</span>
              <span className="tabular text-[var(--rose)]">− {inr(preview)}</span>
            </div>
            <div className="flex justify-between border-t border-[var(--surface-border)] pt-2 font-semibold">
              <span className="text-slate-100">They pay</span>
              <span className="tabular text-slate-100">{inr(Math.max(0, example - preview))}</span>
            </div>
          </div>
          {minOrder && Number(minOrder) * 100 > example && (
            <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1.5 text-[11.5px] text-amber-300">
              This basket is below the ₹{minOrder} minimum, so the coupon would be refused.
            </p>
          )}
        </Panel>
      </div>
    </Shell>
  );
}
