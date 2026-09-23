# Bazaar — Multi-Vendor Commerce Platform

A complete multi-vendor commerce platform with an editorial storefront, vendor portal, super-admin control room, and high-performance TypeScript API.

## Architecture

- **`apps/buyer`** — Editorial retail storefront (shoppers search products with facets, select variants, add to cart split by vendor, checkout, and track shipments).
- **`apps/seller`** — Merchant portal (vendors manage product variant catalog, inventory stock levels, order packing, shipping labels, and payout settlements).
- **`apps/admin`** — Marketplace ops console (GMV KPIs, vendor onboarding verification, catalog moderation, dispute resolution, and weekly ledger payouts).
- **`services/api`** — Shared TypeScript API powered by Hono and PostgreSQL 16.
- **`packages/shared`** — Typed API client and currency/date formatters.

## Key Domain Concepts

- **Multi-Vendor Split Orders:** One customer checkout creates sub-shipments per vendor. Each shipment runs an independent state machine (`placed → accepted → packed → shipped → delivered`).
- **Inventory Reservation:** Stock is reserved at checkout and released if payment times out or order is cancelled.
- **Multi-Party Ledger:** Double-entry ledger tracking shopper refunds, vendor receivables, platform commission, and weekly settlement payout batches.
- **Zero-Credential Testing:** Self-contained mock providers for payments, logistics tracking, and SMS/email notifications.
