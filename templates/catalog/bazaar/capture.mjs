// Bazaar screenshot plan for scripts/capture-template-screens.mjs (R-534, corrected in R-540).
// Captures all 48 screens across the storefront (buyer), the vendor portal (seller) and the
// marketplace operations console (admin), plus a composed cover image.
//
// Every route that takes an id resolves it from the running API first, so the shots are of real
// records in the seeded marketplace rather than placeholders.

export const users = {
  buyer: { email: "priya@bazaar.test", password: "Shopper@2026", role: "shopper" },
  seller: { email: "aryan@bazaar.test", password: "Vendor@2026", role: "vendor" },
  admin: { email: "admin@bazaar.test", password: "Admin@2026", role: "admin" },
};

/**
 * The apps keep the bearer token under `bazaar_token`, with the signed-in user beside it, which is
 * what packages/shared/src/api.ts reads on start-up.
 */
export function storage(_app, session) {
  const token = session.token ?? session.access_token;
  return [
    ["bazaar_token", token],
    ["bazaar_user", JSON.stringify(session.user)],
  ];
}

export default async function capture({ api, shot: rawShot, render, image }) {
  // Every screen is captured as that app's demo user. The sign-in pages and the public storefront
  // are the exceptions: they are what a signed-out visitor sees.
  const SIGNED_OUT = new Set(["login", "signup"]);
  const shot = (options) =>
    rawShot({ as: SIGNED_OUT.has(options.name) ? null : options.app, ...options });

  // Real records from the seeded marketplace, so no screen shows a placeholder id.
  const [adminOrders, adminShops, settlements, vendorProducts, vendorShipments, buyerOrders, categories, publicProducts] =
    await Promise.all([
      api("admin", "GET", "/api/admin/orders?limit=20"),
      api("admin", "GET", "/api/admin/shops"),
      api("admin", "GET", "/api/admin/settlements"),
      api("seller", "GET", "/api/vendor/products"),
      api("seller", "GET", "/api/vendor/shipments"),
      api("buyer", "GET", "/api/shopper/orders"),
      api(null, "GET", "/api/public/categories"),
      api(null, "GET", "/api/public/products"),
    ]);

  const shop = adminShops.shops.find((s) => s.kyc_status === "pending") ?? adminShops.shops[0];
  const deliveredOrder =
    adminOrders.orders.find((o) => o.status === "completed") ?? adminOrders.orders[0];
  const buyerOrder = (buyerOrders.orders ?? buyerOrders)[0];
  const shipment =
    vendorShipments.shipments.find((s) => s.status === "shipped") ?? vendorShipments.shipments[0];
  const product = publicProducts.products[0];

  const id = {
    order: deliveredOrder.id,
    buyerOrder: buyerOrder?.id ?? deliveredOrder.id,
    shop: shop.id,
    shopSlug: adminShops.shops[0].slug,
    settlement: settlements.settlements[0]?.id,
    vendorProduct: vendorProducts.products[0].id,
    shipment: shipment?.id,
    category: categories.categories[0].slug,
    productPath: `${product.shop_slug ?? adminShops.shops[0].slug}/${product.slug}`,
  };

  // --- Buyer Storefront (16 screens) -------------------------------------------------------------
  await shot({
    app: "buyer",
    name: "home",
    route: "/",
    title: "Marketplace Home",
    description: "Curated heritage hero banner, craft category highlights, artisan shop spotlight, and verified authentic masterpieces.",
    highlight: true,
  });

  await shot({
    app: "buyer",
    name: "category",
    route: `/category/${id.category}`,
    displayRoute: "/category/[slug]",
    title: "Category Catalog",
    description: "Category craft collection with price filtering, artisan workshop provenance, and sort facets.",
  });

  await shot({
    app: "buyer",
    name: "product-detail",
    route: `/products/${id.productPath}`,
    displayRoute: "/products/[shopSlug]/[productSlug]",
    title: "Product Details",
    description: "High-resolution craft gallery, variant selector, real-time inventory badge, atelier story, and verified reviews.",
    highlight: true,
  });

  await shot({
    app: "buyer",
    name: "shop-profile",
    route: `/shops/${id.shopSlug}`,
    displayRoute: "/shops/[slug]",
    title: "Artisan Shop Storefront",
    description: "Dedicated seller page featuring brand bio, GI-tag accreditation badge, and curated store catalog.",
    highlight: true,
  });

  await shot({
    app: "buyer",
    name: "cart",
    route: "/cart",
    title: "Multi-Vendor Shopping Cart",
    description: "Shared cart partitioned by independent artisan workshops with dynamic coupon discount calculation.",
    highlight: true,
  });

  await shot({
    app: "buyer",
    name: "checkout",
    route: "/checkout",
    title: "Checkout",
    description: "Delivery address selection, delivery fee estimation, and mock card, instant UPI, or cash payment options.",
  });

  await shot({
    app: "buyer",
    name: "order-confirmation",
    route: `/orders/${id.buyerOrder}/confirmation`,
    displayRoute: "/orders/[id]/confirmation",
    title: "Order Placed Confirmation",
    description: "Receipt detailing split shipments across independent artisan ateliers with estimated dispatch dates.",
  });

  await shot({
    app: "buyer",
    name: "orders",
    route: "/orders",
    as: "buyer",
    title: "Orders History",
    description: "Patron purchase timeline with split consignment badges and instant access to package tracking.",
  });

  await shot({
    app: "buyer",
    name: "order-detail",
    route: `/orders/${id.buyerOrder}`,
    displayRoute: "/orders/[id]",
    as: "buyer",
    title: "Order Breakdown",
    description: "Deep order inspection showing separate courier tracking AWBs, 5-stage shipment progress bars, and return request modal.",
  });

  await shot({
    app: "buyer",
    name: "live-tracking",
    route: `/orders/${id.buyerOrder}/live`,
    displayRoute: "/orders/[id]/live",
    title: "Live Courier Tracking",
    description: "Real-time SSE tracking map displaying simulated courier van movement towards delivery point.",
    highlight: true,
  });

  await shot({
    app: "buyer",
    name: "shipment-tracking",
    route: `/shipments/${id.shipment}/track`,
    displayRoute: "/shipments/[id]/track",
    title: "Shipment Tracking Timeline",
    description: "Milestone timeline verifying courier transit checkpoints from Jaipur workshop to Bengaluru delivery hub.",
  });

  await shot({
    app: "buyer",
    name: "reviews",
    route: "/reviews",
    title: "Customer Reviews",
    description: "Verified customer testimonials with artisan replies and craft quality ratings.",
  });

  await shot({
    app: "buyer",
    name: "account",
    route: "/account",
    as: "buyer",
    title: "Customer Account",
    description: "Patron profile, heritage order statistics, dispatch alert preferences, and account sign-out.",
  });

  await shot({
    app: "buyer",
    name: "addresses",
    route: "/addresses",
    as: "buyer",
    title: "Saved Addresses",
    description: "Saved delivery address book with default residence and workshop delivery switches.",
  });

  await shot({
    app: "buyer",
    name: "login",
    route: "/login",
    title: "Shopper Sign In",
    description: "Authentication with 1-click Priya Sharma demo credentials or phone OTP.",
  });

  await shot({
    app: "buyer",
    name: "signup",
    route: "/signup",
    title: "Shopper Registration",
    description: "New patron registration with instant welcome craft voucher.",
  });

  // --- Seller Vendor Portal (14 screens) ---------------------------------------------------------
  await shot({
    app: "seller",
    name: "login",
    route: "/login",
    title: "Vendor Sign In",
    description: "Artisan merchant authentication with 1-click Master Craftsman Kripal Singh credentials.",
  });

  await shot({
    app: "seller",
    name: "dashboard",
    route: "/",
    as: "seller",
    title: "Vendor Dashboard",
    description: "Workshop operations overview: gross sales, net payout balance, urgent packing alerts, and recent consignments.",
    highlight: true,
  });

  await shot({
    app: "seller",
    name: "products",
    route: "/products",
    as: "seller",
    title: "Product Catalog",
    description: "Artisan craft listings with category filters, stock level indicators, and storefront links.",
  });

  await shot({
    app: "seller",
    name: "product-create",
    route: "/products/new",
    as: "seller",
    title: "Add New Product",
    description: "Craft listing creation form with multi-variant matrix (SKU, color, dimensions, price, and stock units).",
  });

  await shot({
    app: "seller",
    name: "inventory",
    route: "/products",
    as: "seller",
    title: "Inventory Management",
    description: "Stock adjustment table with instant availability threshold alerts and low-stock warnings.",
  });

  await shot({
    app: "seller",
    name: "orders",
    route: "/shipments",
    as: "seller",
    title: "Orders & Shipments Queue",
    description: "Multi-stage fulfillment board with status tabs: placed, accepted, packed, shipped, and delivered.",
  });

  await shot({
    app: "seller",
    name: "shipment-detail",
    route: `/shipments/${id.shipment}`,
    displayRoute: "/shipments/[id]",
    as: "seller",
    title: "Shipment Detail & Packing",
    description: "Consignment lifecycle controller with 5-stage progress tracker, item verification, and packaging notes.",
    highlight: true,
  });

  await shot({
    app: "seller",
    name: "shipping-label",
    route: `/shipments/${id.shipment}`,
    displayRoute: "/shipments/[id]",
    as: "seller",
    title: "Shipping Label & Slip",
    description: "Standard Blue Dart / India Post packing slip and thermal courier barcode preview.",
  });

  await shot({
    app: "seller",
    name: "courier-dispatch",
    route: `/shipments/${id.shipment}`,
    displayRoute: "/shipments/[id]",
    as: "seller",
    title: "Courier Dispatch Handover",
    description: "Generate carrier tracking number and mark consignment as dispatched to air cargo.",
  });

  await shot({
    app: "seller",
    name: "returns",
    route: "/shipments",
    as: "seller",
    title: "Return Requests",
    description: "Customer return inspection queue with reason audit and replacement dispatch controls.",
  });

  await shot({
    app: "seller",
    name: "ledger",
    route: "/payouts",
    as: "seller",
    title: "Vendor Financial Ledger",
    description: "Double-entry bookkeeping journal showing order credits, platform commission deductions, and net balances.",
  });

  await shot({
    app: "seller",
    name: "payouts",
    route: "/payouts",
    as: "seller",
    title: "Payout Settlements",
    description: "Escrow settlement dashboard with 1-click 'Withdraw to Bank (RTGS)' transfer trigger.",
    highlight: true,
  });

  await shot({
    app: "seller",
    name: "store-settings",
    route: "/settings",
    as: "seller",
    title: "Shop Profile Settings",
    description: "Workshop banner, atelier biography, and Geographical Indication accreditation credentials.",
  });

  await shot({
    app: "seller",
    name: "bank-settings",
    route: "/settings",
    as: "seller",
    title: "Bank Account Details",
    description: "Direct NEFT/RTGS settlement bank account configuration and IFSC verification.",
  });

  // --- Admin Marketplace Console (18 screens) ----------------------------------------------------
  await shot({
    app: "admin",
    name: "login",
    route: "/login",
    title: "Operator Sign In",
    description: "Marketplace administrator authentication.",
  });

  await shot({
    app: "admin",
    name: "dashboard",
    route: "/",
    as: "admin",
    title: "Marketplace Overview",
    description: "Total GMV, marketplace net commissions, active vendor count, total orders, and financial summaries.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "shops",
    route: "/shops",
    as: "admin",
    title: "Vendor Directory",
    description: "List of all onboarded shops with KYC verification badges, rating averages, and product counts.",
  });

  await shot({
    app: "admin",
    name: "shop-review",
    route: `/shops/${id.shop}`,
    displayRoute: "/shops/[id]",
    as: "admin",
    title: "Vendor Profile Review",
    description: "Deep dive into a merchant: sales history, active listings, bank info, and dispute rate.",
  });

  await shot({
    app: "admin",
    name: "kyc-approval",
    route: `/shops/${id.shop}/kyc`,
    displayRoute: "/shops/[id]/kyc",
    as: "admin",
    title: "KYC Verification & Approval",
    description: "Approve, suspend, or reject vendor seller licenses with audit logging.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "orders",
    route: "/orders",
    as: "admin",
    title: "Global Orders List",
    description: "Platform-wide order registry with multi-status filters, date pickers, and split shipment indicators.",
  });

  await shot({
    app: "admin",
    name: "order-detail",
    route: `/orders/${id.order}`,
    displayRoute: "/orders/[id]",
    as: "admin",
    title: "Order Investigation",
    description: "Examine buyer payment status, split shipments across multiple vendors, and ledger fee breakdown.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "shipments",
    route: "/shipments",
    as: "admin",
    title: "Global Shipments Monitor",
    description: "Cross-vendor logistics view tracking dispatch delays and courier bottlenecks.",
  });

  await shot({
    app: "admin",
    name: "finance",
    route: "/finance",
    as: "admin",
    title: "Platform Financials",
    description: "Marketplace cash balance in escrow, earned commission revenues, and unpaid vendor payables.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "ledger-audit",
    route: "/finance/ledger",
    as: "admin",
    title: "Double-Entry Ledger Audit",
    description: "Complete double-entry journal trail verifying that debits and credits balance across all accounts.",
  });

  await shot({
    app: "admin",
    name: "settlements",
    route: "/settlements",
    as: "admin",
    title: "Settlement Batches",
    description: "Pending and completed vendor payout batches waiting for bank transfer disbursement.",
  });

  await shot({
    app: "admin",
    name: "payout-approval",
    route: `/settlements/${id.settlement}`,
    displayRoute: "/settlements/[id]",
    as: "admin",
    title: "Approve Payout Batch",
    description: "Review net payout calculations, deduct refund clawbacks, and approve settlement batch for payment.",
    highlight: true,
  });

  await shot({
    app: "admin",
    name: "coupons",
    route: "/coupons",
    as: "admin",
    title: "Promotional Coupons",
    description: "Manage active marketplace promo discount codes with redemption metrics.",
  });

  await shot({
    app: "admin",
    name: "coupon-create",
    route: "/coupons/new",
    as: "admin",
    title: "Create Coupon",
    description: "Create new percentage or flat discount coupon with spending minimums and caps.",
  });

  await shot({
    app: "admin",
    name: "reviews-moderation",
    route: "/reviews",
    as: "admin",
    title: "Review Moderation",
    description: "Audit customer product feedback and flag fraudulent ratings.",
  });

  await shot({
    app: "admin",
    name: "audit-logs",
    route: "/audit",
    as: "admin",
    title: "Audit Logs",
    description: "Tamper-evident record of all operator actions: KYC status changes, payouts, and commission adjustments.",
  });

  await shot({
    app: "admin",
    name: "system-settings",
    route: "/settings",
    as: "admin",
    title: "Platform Settings",
    description: "Default marketplace commission rates, tax rates, and mock/production integration toggles.",
  });

  await shot({
    app: "admin",
    name: "live-shipments-map",
    route: "/live-map",
    as: "admin",
    title: "Live Logistics Map",
    description: "Nationwide shipment dispatch map showing live fulfillment density across vendor hubs.",
    highlight: true,
  });

  // --- Composed Marketing Cover -------------------------------------------------------------------
  const [adminDash, buyerProduct, sellerDash] = await Promise.all([
    image("media/admin/dashboard.jpg"),
    image("media/buyer/product-detail.jpg"),
    image("media/seller/dashboard.jpg"),
  ]);

  await render(coverHtml(adminDash, buyerProduct, sellerDash), {
    file: "cover.jpg",
    width: 1600,
    height: 1000,
  });
}

export function coverHtml(adminShot, buyerShot, sellerShot) {
  return `<!doctype html><html><head><style>
    * { box-sizing: border-box; margin: 0; }
    body {
      width: 1600px;
      height: 1000px;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      background: radial-gradient(1200px 700px at 85% -10%, #d97706 0%, rgba(217,119,6,0.25) 35%, transparent 60%), #090d16;
      color: #fff;
    }
    .title { position: absolute; left: 80px; top: 68px; }
    .title h1 { font-size: 64px; font-weight: 800; letter-spacing: -0.02em; }
    .title h1 span { color: #f59e0b; }
    .title p { margin-top: 10px; font-size: 22px; color: #94a3b8; max-width: 900px; }
    .chips { position: absolute; left: 80px; top: 215px; display: flex; gap: 10px; }
    .chips b {
      font-size: 14px;
      font-weight: 600;
      padding: 7px 14px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.15);
      color: #f1f5f9;
    }
    .win {
      position: absolute;
      border-radius: 14px;
      overflow: hidden;
      background: #0f172a;
      box-shadow: 0 40px 90px -20px rgba(0,0,0,0.8);
      border: 1px solid rgba(255,255,255,0.12);
    }
    .win .bar {
      height: 30px;
      background: #1e293b;
      display: flex;
      align-items: center;
      gap: 7px;
      padding-left: 14px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .win .bar i { width: 11px; height: 11px; border-radius: 50%; background: #475569; }
    .win img { display: block; width: 100%; height: calc(100% - 30px); object-fit: cover; object-position: top; }
    .admin { left: 520px; top: 290px; width: 1010px; height: 650px; z-index: 1; }
    .buyer { left: 80px; top: 410px; width: 630px; height: 480px; z-index: 2; }
    .seller { left: 1150px; top: 120px; width: 380px; height: 320px; z-index: 3; }
    .label {
      position: absolute;
      font-size: 14px;
      font-weight: 700;
      color: #090d16;
      background: #f59e0b;
      padding: 5px 12px;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
  </style></head><body>
    <div class="title">
      <h1>Bazaar <span>Marketplace</span></h1>
      <p>Multi-vendor heritage commerce platform: Storefront, Vendor Atelier, and Ops Console on one API.</p>
    </div>
    <div class="chips">
      <b>Split Order Fulfillment</b>
      <b>5-Stage Shipment Machine</b>
      <b>Double-Entry Escrow Ledger</b>
      <b>Artisan GI Verification</b>
    </div>
    <div class="win admin"><div class="bar"><i></i><i></i><i></i></div><img src="${adminShot}"></div>
    <div class="win buyer"><div class="bar"><i></i><i></i><i></i></div><img src="${buyerShot}"></div>
    <div class="win seller"><div class="bar"><i></i><i></i><i></i></div><img src="${sellerShot}"></div>
    <div class="label" style="left:96px;top:382px;z-index:10;">Buyer Storefront</div>
    <div class="label" style="left:536px;top:260px;z-index:10;">Marketplace Console</div>
    <div class="label" style="left:1166px;top:92px;z-index:10;">Vendor Atelier Portal</div>
  </body></html>`;
}
