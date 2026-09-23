/** Public storefront and authentication routes. */

import { Hono } from "hono";
import { query } from "../db.ts";
import { catalogService } from "../services/catalog.ts";
import { orderService } from "../services/orders.ts";
import { fulfillmentService } from "../services/fulfillment.ts";
import { hashPassword, verifyPassword } from "../auth/password.ts";
import { generateToken } from "../auth/tokens.ts";
import { BadRequestError, UnauthorizedError, ConflictError, NotFoundError } from "../lib/errors.ts";

export const publicRoutes = new Hono();

// List Categories
publicRoutes.get("/categories", async (c) => {
  const categories = await catalogService.listCategories();
  return c.json({ categories });
});

// Search & Filter Products
publicRoutes.get("/products", async (c) => {
  const categorySlug = c.req.query("category");
  const shopSlug = c.req.query("shop");
  const queryStr = c.req.query("q");
  const featured = c.req.query("featured") === "true";
  const minPrice = c.req.query("minPrice") ? parseInt(c.req.query("minPrice")!, 10) : undefined;
  const maxPrice = c.req.query("maxPrice") ? parseInt(c.req.query("maxPrice")!, 10) : undefined;
  const sort = c.req.query("sort") as any;
  const limit = c.req.query("limit") ? parseInt(c.req.query("limit")!, 10) : 20;
  const offset = c.req.query("offset") ? parseInt(c.req.query("offset")!, 10) : 0;

  const result = await catalogService.listProducts({
    categorySlug,
    shopSlug,
    queryStr,
    featured,
    minPriceCents: minPrice,
    maxPriceCents: maxPrice,
    sort,
    limit,
    offset,
  });

  return c.json(result);
});

// Featured Products
publicRoutes.get("/featured", async (c) => {
  const result = await catalogService.listProducts({ featured: true, limit: 8 });
  return c.json({ products: result.products });
});

// Single Product Detail
publicRoutes.get("/products/:shopSlug/:productSlug", async (c) => {
  const shopSlug = c.req.param("shopSlug");
  const productSlug = c.req.param("productSlug");
  const product = await catalogService.getProductBySlug(shopSlug, productSlug);
  return c.json({ product });
});

// Public Shops List
publicRoutes.get("/shops", async (c) => {
  const res = await query(
    `SELECT id, slug, name, tagline, description, logo_url, banner_url, rating_avg, rating_count
     FROM shops
     WHERE kyc_status = 'verified' AND is_active = TRUE
     ORDER BY rating_avg DESC, name ASC`
  );
  return c.json({ shops: res.rows });
});

// Single Shop Profile
publicRoutes.get("/shops/:slug", async (c) => {
  const slug = c.req.param("slug");
  const res = await query(
    `SELECT id, slug, name, tagline, description, logo_url, banner_url, rating_avg, rating_count, created_at
     FROM shops
     WHERE slug = $1 AND is_active = TRUE`,
    [slug]
  );
  if (res.rows.length === 0) {
    throw new NotFoundError(`Shop '${slug}' not found`);
  }
  return c.json({ shop: res.rows[0] });
});

// Validate Coupon
publicRoutes.post("/coupons/validate", async (c) => {
  const body = await c.req.json();
  const { code, subtotalCents } = body;
  if (!code) {
    throw new BadRequestError("Coupon code is required");
  }

  const result = await orderService.validateCoupon(code, subtotalCents || 0);
  return c.json(result);
});

// Track Shipment (Public by shipment ID)
publicRoutes.get("/shipments/:id/track", async (c) => {
  const shipmentId = c.req.param("id");
  const shipment = await fulfillmentService.getShipmentDetail(shipmentId);
  return c.json({ shipment });
});

// Auth: Login
publicRoutes.post("/auth/login", async (c) => {
  const { email, password } = await c.req.json();
  if (!email || !password) {
    throw new BadRequestError("Email and password are required");
  }

  const res = await query<{
    id: string;
    email: string;
    password_hash: string;
    role: "shopper" | "vendor" | "admin";
    name: string;
    phone: string | null;
    avatar_url: string | null;
    is_active: boolean;
  }>(`SELECT * FROM users WHERE email = $1`, [email.toLowerCase().trim()]);

  if (res.rows.length === 0) {
    throw new UnauthorizedError("Invalid email or password");
  }

  const user = res.rows[0];
  if (!user.is_active) {
    throw new UnauthorizedError("Account is inactive. Please contact support");
  }

  const isValid = await verifyPassword(password, user.password_hash);
  if (!isValid) {
    throw new UnauthorizedError("Invalid email or password");
  }

  let shop: any = null;
  if (user.role === "vendor") {
    const shopRes = await query(`SELECT * FROM shops WHERE user_id = $1 LIMIT 1`, [user.id]);
    if (shopRes.rows.length > 0) {
      shop = shopRes.rows[0];
    }
  }

  const token = generateToken({
    userId: user.id,
    email: user.email,
    role: user.role,
    shopId: shop?.id,
  });

  return c.json({
    token,
    access_token: token,
    user: {
      id: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      phone: user.phone,
      avatarUrl: user.avatar_url,
    },
    shop,
  });
});

// Auth: Register (Shopper or Vendor)
publicRoutes.post("/auth/register", async (c) => {
  const { email, password, name, role = "shopper", phone, shopName } = await c.req.json();
  if (!email || !password || !name) {
    throw new BadRequestError("Email, password, and name are required");
  }

  if (!["shopper", "vendor"].includes(role)) {
    throw new BadRequestError("Role must be 'shopper' or 'vendor'");
  }

  const existing = await query(`SELECT id FROM users WHERE email = $1`, [email.toLowerCase().trim()]);
  if (existing.rows.length > 0) {
    throw new ConflictError("An account with this email already exists");
  }

  const passwordHash = await hashPassword(password);

  const userRes = await query<{
    id: string;
    email: string;
    role: "shopper" | "vendor" | "admin";
    name: string;
    phone: string | null;
  }>(
    `INSERT INTO users (email, password_hash, role, name, phone)
     VALUES ($1, $2, $3, $4, $5)
     RETURNING id, email, role, name, phone`,
    [email.toLowerCase().trim(), passwordHash, role, name, phone || null]
  );
  const newUser = userRes.rows[0];

  let newShop: any = null;
  if (role === "vendor") {
    const sName = shopName || `${name}'s Shop`;
    const sSlug = sName
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");

    const shopRes = await query(
      `INSERT INTO shops (user_id, slug, name, tagline, description)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [newUser.id, sSlug, sName, "Handcrafted & authentic goods", "Welcome to our shop on Bazaar."]
    );
    newShop = shopRes.rows[0];
  }

  const token = generateToken({
    userId: newUser.id,
    email: newUser.email,
    role: newUser.role,
    shopId: newShop?.id,
  });

  return c.json(
    {
      token,
      user: newUser,
      shop: newShop,
    },
    201
  );
});
