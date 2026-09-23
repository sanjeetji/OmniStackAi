import assert from "node:assert/strict";
import { test } from "node:test";
import { calculateCommission } from "../src/lib/money.ts";
import {
  canTransition,
  assertValidTransition,
  type ShipmentStatus,
} from "../src/lib/shipment-state.ts";

interface CartLine {
  shopId: string;
  shopName: string;
  commissionRateBp: number;
  variantId: string;
  title: string;
  priceCents: number;
  quantity: number;
}

interface SimulatedShipment {
  shopId: string;
  subtotalCents: number;
  commissionCents: number;
  vendorPayoutCents: number;
  items: CartLine[];
  status: ShipmentStatus;
  tracking: Array<{ status: string; message: string }>;
}

test("multi-vendor split-order partitioning and accounting conservation", () => {
  // Shopper cart with items from two distinct vendors
  const cart: CartLine[] = [
    {
      shopId: "shop_craftloom",
      shopName: "Craftloom Studio",
      commissionRateBp: 1000, // 10%
      variantId: "v_saree_amber",
      title: "Chanderi Handloom Silk Saree",
      priceCents: 499900,
      quantity: 1,
    },
    {
      shopId: "shop_brassbloom",
      shopName: "Brass & Bloom",
      commissionRateBp: 1200, // 12%
      variantId: "v_urli_12in",
      title: "Antique Engraved Brass Urli",
      priceCents: 349900,
      quantity: 1,
    },
    {
      shopId: "shop_brassbloom",
      shopName: "Brass & Bloom",
      commissionRateBp: 1200, // 12%
      variantId: "v_brass_diya",
      title: "Hand-Carved Peacock Diya",
      priceCents: 150000,
      quantity: 1,
    },
  ];

  // 1. Group items by vendor
  const grouped = new Map<string, CartLine[]>();
  for (const item of cart) {
    if (!grouped.has(item.shopId)) grouped.set(item.shopId, []);
    grouped.get(item.shopId)!.push(item);
  }

  assert.equal(grouped.size, 2, "Cart must be partitioned into exactly 2 vendor shipments");

  // 2. Build shipments
  const shipments: SimulatedShipment[] = [];
  let orderSubtotal = 0;
  let totalCommission = 0;
  let totalVendorPayout = 0;

  for (const [shopId, items] of grouped.entries()) {
    let shopSubtotal = 0;
    for (const it of items) {
      shopSubtotal += it.priceCents * it.quantity;
    }
    orderSubtotal += shopSubtotal;

    const rate = items[0].commissionRateBp;
    const { commissionCents, vendorPayoutCents } = calculateCommission(shopSubtotal, rate);

    totalCommission += commissionCents;
    totalVendorPayout += vendorPayoutCents;

    shipments.push({
      shopId,
      subtotalCents: shopSubtotal,
      commissionCents,
      vendorPayoutCents,
      items,
      status: "placed",
      tracking: [{ status: "placed", message: "Order placed with vendor" }],
    });
  }

  // 3. Mathematical conservation
  assert.equal(orderSubtotal, 499900 + 349900 + 150000); // ₹9,998.00
  assert.equal(
    totalCommission + totalVendorPayout,
    orderSubtotal,
    "Marketplace accounting balance: commission + vendor payouts must exactly equal gross subtotal"
  );

  // 4. Verify Vendor 1 (Craftloom: 10% on 499900)
  const ship1 = shipments.find((s) => s.shopId === "shop_craftloom")!;
  assert.equal(ship1.subtotalCents, 499900);
  assert.equal(ship1.commissionCents, 49990); // ₹499.90
  assert.equal(ship1.vendorPayoutCents, 449910); // ₹4,499.10
  assert.equal(ship1.items.length, 1);

  // 5. Verify Vendor 2 (Brass & Bloom: 12% on 499900)
  const ship2 = shipments.find((s) => s.shopId === "shop_brassbloom")!;
  assert.equal(ship2.subtotalCents, 499900); // 349900 + 150000
  assert.equal(ship2.commissionCents, 59988); // 12% of 499900 = 59988
  assert.equal(ship2.vendorPayoutCents, 439912);
  assert.equal(ship2.items.length, 2);

  // 6. Test independent fulfillment lifecycle on Shipment 1
  const steps: ShipmentStatus[] = ["accepted", "packed", "shipped", "delivered"];
  for (const nextStep of steps) {
    assertValidTransition(ship1.status, nextStep);
    ship1.status = nextStep;
    ship1.tracking.push({ status: nextStep, message: `Transitioned to ${nextStep}` });
  }

  assert.equal(ship1.status, "delivered");
  assert.equal(ship1.tracking.length, 5); // placed + 4 transitions

  // Shipment 2 remains independent
  assert.equal(ship2.status, "placed");
});
