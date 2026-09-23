/** Universal API client for Bazaar services. */

import type {
  Category,
  Product,
  Cart,
  Order,
  Shipment,
  Review,
  User,
  UserAddress,
  Shop,
  AuthResponse,
  AdminMetrics,
  PlatformFinancials,
  LedgerEntryRow,
  AdminOrderRow,
} from "./types";

export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = "ApiError";
  }
}

export class BazaarApiClient {
  private baseUrl: string;
  private getToken: () => string | null;

  constructor(options: {
    baseUrl?: string;
    getToken?: () => string | null;
  } = {}) {
    // NEXT_PUBLIC_API_URL is inlined at build time and is what the OmniStack preview sets, so it
    // must win in the browser too: every app there is served on its own port.
    this.baseUrl =
      options.baseUrl ||
      (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
      (typeof window !== "undefined" ? (window as any).__BAZAAR_API_URL__ : null) ||
      "http://127.0.0.1:4000";

    this.getToken =
      options.getToken ||
      (() => {
        if (typeof window !== "undefined") {
          const direct = localStorage.getItem("bazaar_token");
          if (direct) return direct;
          const session =
            localStorage.getItem("bazaar.buyer.session") ||
            localStorage.getItem("bazaar.seller.session") ||
            localStorage.getItem("bazaar.admin.session");
          if (session) {
            try {
              const parsed = JSON.parse(session);
              return parsed.access_token || parsed.token || null;
            } catch {
              return null;
            }
          }
        }
        return null;
      });
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    const contentType = response.headers.get("content-type");
    const isJson = contentType && contentType.includes("application/json");
    const data = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      const message =
        (typeof data === "object" && data?.error) ||
        (typeof data === "string" && data) ||
        `Request failed with status ${response.status}`;
      throw new ApiError(response.status, message, data);
    }

    return data as T;
  }

  // --- Public APIs ---
  async getCategories(): Promise<Category[]> {
    const res = await this.request<{ categories: Category[] }>("/api/public/categories");
    return res.categories;
  }

  async getProducts(params: {
    category?: string;
    shop?: string;
    q?: string;
    minPrice?: number;
    maxPrice?: number;
    sort?: string;
    limit?: number;
    offset?: number;
    featured?: boolean;
  } = {}): Promise<{ products: Product[]; total: number }> {
    const query = new URLSearchParams();
    if (params.category) query.set("category", params.category);
    if (params.shop) query.set("shop", params.shop);
    if (params.q) query.set("q", params.q);
    if (params.minPrice != null) query.set("minPrice", String(params.minPrice));
    if (params.maxPrice != null) query.set("maxPrice", String(params.maxPrice));
    if (params.sort) query.set("sort", params.sort);
    if (params.limit != null) query.set("limit", String(params.limit));
    if (params.offset != null) query.set("offset", String(params.offset));
    if (params.featured) query.set("featured", "true");

    const qs = query.toString();
    return this.request<{ products: Product[]; total: number }>(
      `/api/public/products${qs ? `?${qs}` : ""}`
    );
  }

  async getFeatured(): Promise<Product[]> {
    const res = await this.request<{ products: Product[] }>("/api/public/featured");
    return res.products;
  }

  async getProduct(shopSlug: string, productSlug: string): Promise<Product> {
    const res = await this.request<{ product: Product }>(
      `/api/public/products/${encodeURIComponent(shopSlug)}/${encodeURIComponent(productSlug)}`
    );
    return res.product;
  }

  async getShops(): Promise<Shop[]> {
    const res = await this.request<{ shops: Shop[] }>("/api/public/shops");
    return res.shops;
  }

  async getShop(slug: string): Promise<Shop> {
    const res = await this.request<{ shop: Shop }>(
      `/api/public/shops/${encodeURIComponent(slug)}`
    );
    return res.shop;
  }

  async validateCoupon(code: string, subtotalCents: number): Promise<{
    valid: boolean;
    discountCents: number;
    description?: string;
  }> {
    return this.request("/api/public/coupons/validate", {
      method: "POST",
      body: JSON.stringify({ code, subtotalCents }),
    });
  }

  async login(
    emailOrCreds: string | { email: string; password: string },
    maybePassword?: string
  ): Promise<AuthResponse> {
    const payload =
      typeof emailOrCreds === "string"
        ? { email: emailOrCreds, password: maybePassword || "" }
        : emailOrCreds;
    const res = await this.request<AuthResponse>("/api/public/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (typeof window !== "undefined" && res.token) {
      localStorage.setItem("bazaar_token", res.token);
      localStorage.setItem("bazaar_user", JSON.stringify(res.user));
      if (res.shop) localStorage.setItem("bazaar_shop", JSON.stringify(res.shop));
    }
    return res;
  }

  async getPublicShipmentTrack(id: string): Promise<Shipment> {
    const res = await this.request<{ shipment: Shipment }>(`/api/public/shipments/${id}/track`);
    return res.shipment;
  }

  async register(data: {
    email: string;
    password: string;
    name: string;
    role?: "shopper" | "vendor";
    phone?: string;
    shopName?: string;
  }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>("/api/public/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (typeof window !== "undefined" && res.token) {
      localStorage.setItem("bazaar_token", res.token);
      localStorage.setItem("bazaar_user", JSON.stringify(res.user));
      if (res.shop) localStorage.setItem("bazaar_shop", JSON.stringify(res.shop));
    }
    return res;
  }

  logout() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("bazaar_token");
      localStorage.removeItem("bazaar_user");
      localStorage.removeItem("bazaar_shop");
    }
  }

  // --- Shopper APIs ---
  async getMe(): Promise<{ user: User }> {
    return this.request("/api/shopper/me");
  }

  async getProfile(): Promise<User> {
    const res = await this.request<{ user: User }>("/api/shopper/me");
    return res.user;
  }

  async getAddresses(): Promise<UserAddress[]> {
    const res = await this.request<{ addresses: UserAddress[] }>("/api/shopper/addresses");
    return res.addresses;
  }

  async addAddress(data: {
    label?: string;
    recipientName?: string;
    recipient_name?: string;
    phone: string;
    street: string;
    city: string;
    state: string;
    postalCode?: string;
    postal_code?: string;
    country?: string;
    isDefault?: boolean;
    is_default?: boolean;
  }): Promise<UserAddress> {
    const payload = {
      label: data.label || "home",
      recipientName: data.recipientName || data.recipient_name,
      phone: data.phone,
      street: data.street,
      city: data.city,
      state: data.state,
      postalCode: data.postalCode || data.postal_code,
      country: data.country || "India",
      isDefault: data.isDefault ?? data.is_default ?? false,
    };
    const res = await this.request<{ address: UserAddress }>("/api/shopper/addresses", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return res.address;
  }

  async getCart(): Promise<Cart> {
    const res = await this.request<{ cart: Cart }>("/api/shopper/cart");
    return res.cart;
  }

  async addToCart(variantId: string, quantity = 1): Promise<Cart> {
    const res = await this.request<{ cart: Cart }>("/api/shopper/cart/items", {
      method: "POST",
      body: JSON.stringify({ variantId, quantity }),
    });
    return res.cart;
  }

  async updateCartItem(id: string, quantity: number): Promise<Cart> {
    const res = await this.request<{ cart: Cart }>(`/api/shopper/cart/items/${id}`, {
      method: "PUT",
      body: JSON.stringify({ quantity }),
    });
    return res.cart;
  }

  async removeCartItem(id: string): Promise<Cart> {
    const res = await this.request<{ cart: Cart }>(`/api/shopper/cart/items/${id}`, {
      method: "DELETE",
    });
    return res.cart;
  }

  async checkout(params: {
    shippingAddress: Record<string, any>;
    billingAddress?: Record<string, any>;
    paymentMethod?: "mock_card" | "mock_upi" | "cod";
    couponCode?: string;
    notes?: string;
  }): Promise<{ order: Order }> {
    return this.request("/api/shopper/checkout", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getOrders(): Promise<Order[]> {
    const res = await this.request<{ orders: Order[] }>("/api/shopper/orders");
    return res.orders;
  }

  async getOrder(id: string): Promise<Order> {
    const res = await this.request<{ order: Order }>(`/api/shopper/orders/${id}`);
    return res.order;
  }

  async requestReturn(shipmentId: string, reason: string): Promise<any> {
    return this.request(`/api/shopper/shipments/${shipmentId}/return`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  async getMyReviews(): Promise<{ reviews: any[]; awaitingReview: any[] }> {
    return this.request("/api/shopper/reviews");
  }

  async submitReview(data: {
    productId: string;
    rating: number;
    title?: string;
    comment: string;
  }): Promise<Review> {
    const res = await this.request<{ review: Review }>("/api/shopper/reviews", {
      method: "POST",
      body: JSON.stringify(data),
    });
    return res.review;
  }

  // --- Vendor APIs ---
  async getVendorShop(): Promise<Shop> {
    const res = await this.request<{ shop: Shop }>("/api/vendor/shop");
    return res.shop;
  }

  async updateShop(data: {
    name?: string;
    tagline?: string;
    description?: string;
    logoUrl?: string;
    bannerUrl?: string;
    bankName?: string;
    bankAccountLast4?: string;
    bankIfscCode?: string;
  }): Promise<{ shop: Shop }> {
    return this.request("/api/vendor/shop", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async getVendorDashboard(): Promise<{ metrics: Record<string, any> }> {
    return this.request("/api/vendor/dashboard");
  }

  async getVendorProducts(): Promise<{ products: Product[]; total: number }> {
    return this.request("/api/vendor/products");
  }

  async createVendorProduct(data: any): Promise<{ product: Product }> {
    return this.request("/api/vendor/products", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getVendorProduct(id: string): Promise<{ product: Product; variants: any[] }> {
    return this.request(`/api/vendor/products/${id}`);
  }

  async updateVendorProduct(
    id: string,
    data: {
      title?: string;
      description?: string;
      basePriceCents?: number;
      comparePriceCents?: number;
      isPublished?: boolean;
      tags?: string[];
    }
  ): Promise<{ product: Product }> {
    return this.request(`/api/vendor/products/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async getVendorReviews(): Promise<{ reviews: any[] }> {
    return this.request("/api/vendor/reviews");
  }

  async replyToReview(reviewId: string, reply: string): Promise<{ review: Review }> {
    return this.request(`/api/vendor/reviews/${reviewId}/reply`, {
      method: "POST",
      body: JSON.stringify({ reply }),
    });
  }

  async getVendorShipments(status?: string): Promise<{ shipments: Shipment[]; total: number }> {
    const qs = status ? `?status=${status}` : "";
    return this.request(`/api/vendor/shipments${qs}`);
  }

  async getVendorShipment(id: string): Promise<Shipment> {
    const res = await this.request<{ shipment: Shipment }>(`/api/vendor/shipments/${id}`);
    return res.shipment;
  }

  async acceptShipment(id: string): Promise<any> {
    return this.request(`/api/vendor/shipments/${id}/accept`, { method: "POST" });
  }

  async packShipment(id: string): Promise<any> {
    return this.request(`/api/vendor/shipments/${id}/pack`, { method: "POST" });
  }

  async shipShipment(id: string, courierName?: string, trackingNumber?: string): Promise<any> {
    return this.request(`/api/vendor/shipments/${id}/ship`, {
      method: "POST",
      body: JSON.stringify({ courierName, trackingNumber }),
    });
  }

  async deliverShipment(id: string): Promise<any> {
    return this.request(`/api/vendor/shipments/${id}/deliver`, { method: "POST" });
  }

  async getVendorLedger(): Promise<{ account: any; entries: any[] }> {
    return this.request("/api/vendor/ledger");
  }

  async requestSettlement(): Promise<any> {
    return this.request("/api/vendor/settlements/request", { method: "POST" });
  }

  // --- Admin APIs ---
  async getAdminMetrics(): Promise<{ metrics: AdminMetrics }> {
    return this.request("/api/admin/metrics");
  }

  async getAdminShops(kycStatus?: string): Promise<{ shops: Shop[] }> {
    const qs = kycStatus ? `?kycStatus=${kycStatus}` : "";
    return this.request(`/api/admin/shops${qs}`);
  }

  async getAdminShop(id: string): Promise<{ shop: Shop; products: any[]; shipments: any[] }> {
    return this.request(`/api/admin/shops/${id}`);
  }

  async updateShopKyc(shopId: string, kycStatus: string): Promise<{ shop: Shop }> {
    return this.request(`/api/admin/shops/${shopId}/kyc`, {
      method: "POST",
      body: JSON.stringify({ kycStatus }),
    });
  }

  async updateShopCommission(shopId: string, commissionRateBasisPoints: number): Promise<{ shop: Shop }> {
    return this.request(`/api/admin/shops/${shopId}/commission`, {
      method: "POST",
      body: JSON.stringify({ commissionRateBasisPoints }),
    });
  }

  async getAdminOrders(
    params: { status?: string; limit?: number; offset?: number } = {}
  ): Promise<{ orders: AdminOrderRow[] }> {
    const search = new URLSearchParams();
    if (params.status) search.set("status", params.status);
    if (params.limit !== undefined) search.set("limit", String(params.limit));
    if (params.offset !== undefined) search.set("offset", String(params.offset));
    const qs = search.toString();
    return this.request(`/api/admin/orders${qs ? `?${qs}` : ""}`);
  }

  async getAdminOrder(id: string): Promise<{
    order: AdminOrderRow;
    items: any[];
    shipments: any[];
    ledgerEntries: any[];
  }> {
    return this.request(`/api/admin/orders/${id}`);
  }

  async cancelAdminOrder(id: string, reason?: string): Promise<{ order: Order; refundedCents: number }> {
    return this.request(`/api/admin/orders/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  async getAdminShipments(status?: string): Promise<{ shipments: any[] }> {
    const qs = status ? `?status=${status}` : "";
    return this.request(`/api/admin/shipments${qs}`);
  }

  async getAdminFinance(): Promise<{ summary: PlatformFinancials; recentEntries: LedgerEntryRow[] }> {
    return this.request("/api/admin/finance");
  }

  async getAdminLedger(entryType?: string): Promise<{ entries: any[] }> {
    const qs = entryType ? `?entryType=${entryType}` : "";
    return this.request(`/api/admin/finance/ledger${qs}`);
  }

  async getAdminSettlements(): Promise<{ settlements: any[] }> {
    return this.request("/api/admin/settlements");
  }

  async getAdminSettlement(id: string): Promise<{ settlement: any }> {
    return this.request(`/api/admin/settlements/${id}`);
  }

  async approveAdminSettlement(id: string): Promise<{ settlement: any }> {
    return this.request(`/api/admin/settlements/${id}/approve`, { method: "POST" });
  }

  async generateAdminSettlement(shopId: string): Promise<{ settlement: any }> {
    return this.request("/api/admin/settlements/generate", {
      method: "POST",
      body: JSON.stringify({ shopId }),
    });
  }

  async getAdminCoupons(): Promise<{ coupons: any[] }> {
    return this.request("/api/admin/coupons");
  }

  async createAdminCoupon(data: {
    code: string;
    description?: string;
    discountType: "percentage" | "fixed";
    discountValue: number;
    minOrderCents?: number;
    maxDiscountCents?: number;
    usageLimit?: number;
    expiresAt?: string;
  }): Promise<{ coupon: any }> {
    return this.request("/api/admin/coupons", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async toggleAdminCoupon(id: string): Promise<{ coupon: any }> {
    return this.request(`/api/admin/coupons/${id}/toggle`, { method: "POST" });
  }

  async getAdminReviews(): Promise<{ reviews: any[] }> {
    return this.request("/api/admin/reviews");
  }

  async deleteAdminReview(id: string): Promise<{ success: boolean }> {
    return this.request(`/api/admin/reviews/${id}/delete`, { method: "POST" });
  }

  async getAdminAuditLogs(): Promise<{ auditLogs: any[] }> {
    return this.request("/api/admin/audit-logs");
  }

  async getAdminSettings(): Promise<{ settings: any }> {
    return this.request("/api/admin/settings");
  }

  async saveAdminSettings(settings: any): Promise<{ success: boolean; settings: any }> {
    return this.request("/api/admin/settings", {
      method: "POST",
      body: JSON.stringify(settings),
    });
  }
}

export const api = new BazaarApiClient();
