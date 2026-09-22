import assert from "node:assert/strict";
import { test } from "node:test";
import { evaluatePromo, type Promo } from "../src/lib/promo.ts";

const base: Promo = { code: "RIDE50", kind: "percent", value: 50, max_discount: 75, min_fare: 100, valid_until: null, usage_limit: null, per_user_limit: 2, used_count: 0, active: true };

test("percent promos are capped", () => {
  assert.deepEqual(evaluatePromo(base, 400, 0), { ok: true, discount: 75 });
  assert.deepEqual(evaluatePromo(base, 120, 0), { ok: true, discount: 60 });
});

test("flat promos never exceed the fare", () => {
  assert.deepEqual(evaluatePromo({ ...base, kind: "flat", value: 500, max_discount: null, min_fare: 0 }, 90, 0), { ok: true, discount: 90 });
});

test("rules: active, expiry, global limit, per-rider limit, minimum fare", () => {
  const cases: [Partial<Promo>, number, number, RegExp][] = [
    [{ active: false }, 200, 0, /no longer active/],
    [{ valid_until: new Date("2020-01-01") }, 200, 0, /expired/],
    [{ usage_limit: 10, used_count: 10 }, 200, 0, /fully used/],
    [{}, 200, 2, /already used/],
    [{}, 50, 0, /at least/],
  ];
  for (const [change, fare, used, reason] of cases) {
    const result = evaluatePromo({ ...base, ...change }, fare, used);
    assert.equal(result.ok, false);
    assert.match((result as { reason: string }).reason, reason);
  }
});
