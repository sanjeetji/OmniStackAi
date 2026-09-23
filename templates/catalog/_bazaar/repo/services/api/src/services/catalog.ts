/** Catalog service: categories, products, variant matrix, and inventory checks. */

import { query, withTransaction } from "../db.ts";
import { NotFoundError, BadRequestError } from "../lib/errors.ts";

export interface Category {
  id: string;
  slug: string;
  name: string;
  description?: string;
  parent_id?: string;
  image_url?: string;
  sort_order: number;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  sku: string;
  title: string;
  option_color?: string;
  option_size?: string;
  price_cents: number;
  compare_price_cents?: number;
  stock_quantity: number;
  reserved_quantity: number;
  weight_grams: number;
  image_url?: string;
  is_active: boolean;
}

export interface Product {
  id: string;
  shop_id: string;
  category_id: string;
  title: string;
  slug: string;
  description: string;
  tags: string[];
  details_json: Record<string, any>;
  base_price_cents: number;
  compare_price_cents?: number;
  is_published: boolean;
  is_featured: boolean;
  rating_avg: number;
  rating_count: number;
  created_at: string;
  updated_at: string;
  shop_name?: string;
  shop_slug?: string;
  category_name?: string;
  category_slug?: string;
  variants?: ProductVariant[];
}

export class CatalogService {
  async listCategories(): Promise<Category[]> {
    const res = await query<Category>(
      `SELECT id, slug, name, description, parent_id, image_url, sort_order
       FROM categories
       WHERE is_active = TRUE
       ORDER BY sort_order ASC, name ASC`
    );
    return res.rows;
  }

  async listProducts(filters: {
    categorySlug?: string;
    shopSlug?: string;
    shopId?: string;
    queryStr?: string;
    minPriceCents?: number;
    maxPriceCents?: number;
    featured?: boolean;
    sort?: "popular" | "price_asc" | "price_desc" | "rating" | "newest";
    limit?: number;
    offset?: number;
  }): Promise<{ products: Product[]; total: number }> {
    const conditions: string[] = ["p.is_published = TRUE"];
    const params: any[] = [];
    let pIdx = 1;

    if (filters.categorySlug) {
      conditions.push(`c.slug = $${pIdx++}`);
      params.push(filters.categorySlug);
    }

    if (filters.shopSlug) {
      conditions.push(`s.slug = $${pIdx++}`);
      params.push(filters.shopSlug);
    }

    if (filters.shopId) {
      conditions.push(`p.shop_id = $${pIdx++}`);
      params.push(filters.shopId);
    }

    if (filters.featured) {
      conditions.push(`p.is_featured = TRUE`);
    }

    if (filters.minPriceCents != null) {
      conditions.push(`p.base_price_cents >= $${pIdx++}`);
      params.push(filters.minPriceCents);
    }

    if (filters.maxPriceCents != null) {
      conditions.push(`p.base_price_cents <= $${pIdx++}`);
      params.push(filters.maxPriceCents);
    }

    if (filters.queryStr) {
      conditions.push(
        `(p.title ILIKE $${pIdx} OR p.description ILIKE $${pIdx} OR s.name ILIKE $${pIdx})`
      );
      params.push(`%${filters.queryStr}%`);
      pIdx++;
    }

    const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

    let orderBy = "p.created_at DESC";
    if (filters.sort === "price_asc") orderBy = "p.base_price_cents ASC";
    if (filters.sort === "price_desc") orderBy = "p.base_price_cents DESC";
    if (filters.sort === "rating") orderBy = "p.rating_avg DESC, p.rating_count DESC";
    if (filters.sort === "popular") orderBy = "p.rating_count DESC, p.created_at DESC";

    const countRes = await query<{ count: string }>(
      `SELECT COUNT(*)::text as count
       FROM products p
       JOIN shops s ON s.id = p.shop_id
       JOIN categories c ON c.id = p.category_id
       ${whereClause}`,
      params
    );
    const total = parseInt(countRes.rows[0]?.count || "0", 10);

    const limit = Math.min(Math.max(filters.limit || 20, 1), 100);
    const offset = Math.max(filters.offset || 0, 0);

    const dataRes = await query<Product>(
      `SELECT p.id, p.shop_id, p.category_id, p.title, p.slug, p.description,
              p.tags, p.details_json, p.base_price_cents, p.compare_price_cents,
              p.is_published, p.is_featured, p.rating_avg, p.rating_count,
              p.created_at, p.updated_at,
              s.name AS shop_name, s.slug AS shop_slug,
              c.name AS category_name, c.slug AS category_slug
       FROM products p
       JOIN shops s ON s.id = p.shop_id
       JOIN categories c ON c.id = p.category_id
       ${whereClause}
       ORDER BY ${orderBy}
       LIMIT $${pIdx++} OFFSET $${pIdx++}`,
      [...params, limit, offset]
    );

    const productIds = dataRes.rows.map((p) => p.id);
    if (productIds.length > 0) {
      const varRes = await query<ProductVariant>(
        `SELECT id, product_id, sku, title, option_color, option_size,
                price_cents, compare_price_cents, stock_quantity, reserved_quantity,
                weight_grams, image_url, is_active
         FROM product_variants
         WHERE product_id = ANY($1::uuid[]) AND is_active = TRUE
         ORDER BY price_cents ASC`,
        [productIds]
      );
      const varMap = new Map<string, ProductVariant[]>();
      for (const v of varRes.rows) {
        if (!varMap.has(v.product_id)) varMap.set(v.product_id, []);
        varMap.get(v.product_id)!.push(v);
      }
      for (const prod of dataRes.rows) {
        prod.variants = varMap.get(prod.id) || [];
      }
    }

    return { products: dataRes.rows, total };
  }

  async getProductBySlug(shopSlug: string, productSlug: string): Promise<Product> {
    const res = await query<Product>(
      `SELECT p.id, p.shop_id, p.category_id, p.title, p.slug, p.description,
              p.tags, p.details_json, p.base_price_cents, p.compare_price_cents,
              p.is_published, p.is_featured, p.rating_avg, p.rating_count,
              p.created_at, p.updated_at,
              s.name AS shop_name, s.slug AS shop_slug,
              c.name AS category_name, c.slug AS category_slug
       FROM products p
       JOIN shops s ON s.id = p.shop_id
       JOIN categories c ON c.id = p.category_id
       WHERE s.slug = $1 AND p.slug = $2 AND p.is_published = TRUE`,
      [shopSlug, productSlug]
    );

    if (res.rows.length === 0) {
      throw new NotFoundError(`Product '${shopSlug}/${productSlug}' not found`);
    }

    const product = res.rows[0];
    const varRes = await query<ProductVariant>(
      `SELECT id, product_id, sku, title, option_color, option_size,
              price_cents, compare_price_cents, stock_quantity, reserved_quantity,
              weight_grams, image_url, is_active
       FROM product_variants
       WHERE product_id = $1 AND is_active = TRUE
       ORDER BY price_cents ASC`,
      [product.id]
    );
    product.variants = varRes.rows;
    return product;
  }

  async getProductById(id: string): Promise<Product> {
    const res = await query<Product>(
      `SELECT p.id, p.shop_id, p.category_id, p.title, p.slug, p.description,
              p.tags, p.details_json, p.base_price_cents, p.compare_price_cents,
              p.is_published, p.is_featured, p.rating_avg, p.rating_count,
              p.created_at, p.updated_at,
              s.name AS shop_name, s.slug AS shop_slug,
              c.name AS category_name, c.slug AS category_slug
       FROM products p
       JOIN shops s ON s.id = p.shop_id
       JOIN categories c ON c.id = p.category_id
       WHERE p.id = $1`,
      [id]
    );

    if (res.rows.length === 0) {
      throw new NotFoundError(`Product '${id}' not found`);
    }

    const product = res.rows[0];
    const varRes = await query<ProductVariant>(
      `SELECT id, product_id, sku, title, option_color, option_size,
              price_cents, compare_price_cents, stock_quantity, reserved_quantity,
              weight_grams, image_url, is_active
       FROM product_variants
       WHERE product_id = $1
       ORDER BY price_cents ASC`,
      [product.id]
    );
    product.variants = varRes.rows;
    return product;
  }

  async createProduct(
    shopId: string,
    data: {
      categoryId: string;
      title: string;
      slug: string;
      description: string;
      tags?: string[];
      detailsJson?: Record<string, any>;
      basePriceCents: number;
      comparePriceCents?: number;
      variants: Array<{
        sku: string;
        title: string;
        optionColor?: string;
        optionSize?: string;
        priceCents: number;
        comparePriceCents?: number;
        stockQuantity: number;
        imageUrl?: string;
      }>;
    }
  ): Promise<Product> {
    if (!data.variants || data.variants.length === 0) {
      throw new BadRequestError("At least one product variant is required");
    }

    return withTransaction(async (client) => {
      const prodRes = await client.query<Product>(
        `INSERT INTO products (
           shop_id, category_id, title, slug, description,
           tags, details_json, base_price_cents, compare_price_cents
         )
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
         RETURNING *`,
        [
          shopId,
          data.categoryId,
          data.title,
          data.slug,
          data.description,
          data.tags || [],
          JSON.stringify(data.detailsJson || {}),
          data.basePriceCents,
          data.comparePriceCents || null,
        ]
      );

      const product = prodRes.rows[0];
      const createdVariants: ProductVariant[] = [];

      for (const v of data.variants) {
        const vRes = await client.query<ProductVariant>(
          `INSERT INTO product_variants (
             product_id, sku, title, option_color, option_size,
             price_cents, compare_price_cents, stock_quantity, image_url
           )
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
           RETURNING *`,
          [
            product.id,
            v.sku,
            v.title,
            v.optionColor || null,
            v.optionSize || null,
            v.priceCents,
            v.comparePriceCents || null,
            v.stockQuantity,
            v.imageUrl || null,
          ]
        );
        const variant = vRes.rows[0];
        createdVariants.push(variant);

        // Record initial inventory log
        await client.query(
          `INSERT INTO inventory_logs (
             variant_id, delta_quantity, balance_after, reason, notes
           )
           VALUES ($1, $2, $3, 'initial', 'Product variant created')`,
          [variant.id, v.stockQuantity, v.stockQuantity]
        );
      }

      product.variants = createdVariants;
      return product;
    });
  }
}

export const catalogService = new CatalogService();
