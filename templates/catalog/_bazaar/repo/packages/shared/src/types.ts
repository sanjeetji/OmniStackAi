/** Domain types and API response interfaces for Bazaar Multi-Vendor Commerce Platform. */

export type UserRole = "shopper" | "vendor" | "admin";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  name: string;
  phone?: string | null;
  avatarUrl?: string | null;
  createdAt?: string;
}

export interface UserAddress {
  id: string;
  user_id: string;
  label: string;
  recipient_name: string;
  phone: string;
  street: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  is_default: boolean;
  created_at?: string;
}

export type KycStatus = "pending" | "verified" | "rejected" | "suspended";

export interface Shop {
  id: string;
  user_id: string;
  slug: string;
  name: string;
  tagline?: string | null;
  description?: string | null;
  logo_url?: string | null;
  banner_url?: string | null;
  kyc_status: KycStatus;
  commission_rate_basis_points: number;
  bank_name?: string | null;
  bank_account_last4?: string | null;
  bank_ifsc_code?: string | null;
  rating_avg: number;
  rating_count: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Category {
  id: string;
  slug: string;
  name: string;
  description?: string | null;
  parent_id?: string | null;
  image_url?: string | null;
  sort_order: number;
}

export interface ProductVariant {
  id: string;
  product_id: string;
  sku: string;
  title: string;
  option_color?: string | null;
  option_size?: string | null;
  price_cents: number;
  compare_price_cents?: number | null;
  stock_quantity: number;
  reserved_quantity: number;
  weight_grams?: number;
  image_url?: string | null;
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
  details_json?: Record<string, any>;
  base_price_cents: number;
  compare_price_cents?: number | null;
  is_published: boolean;
  is_featured: boolean;
  rating_avg: number;
  rating_count: number;
  created_at: string;
  updated_at: string;
  shop_name?: string;
  shop_slug?: string;
  shop_logo?: string;
  category_name?: string;
  category_slug?: string;
  variants?: ProductVariant[];
}

export interface CartItem {
  id: string;
  cart_id: string;
  variant_id: string;
  shop_id: string;
  quantity: number;
  price_cents: number;
  sku: string;
  product_title: string;
  variant_title: string;
  option_color?: string | null;
  option_size?: string | null;
  image_url?: string | null;
  shop_name: string;
  shop_slug: string;
}

export interface Cart {
  id: string;
  user_id: string | null;
  session_token: string | null;
  items: CartItem[];
  subtotal_cents: number;
}

export type OrderStatus =
  | "pending_payment"
  | "processing"
  | "partially_shipped"
  | "completed"
  | "cancelled";

export type PaymentMethod = "mock_card" | "mock_upi" | "cod";
export type PaymentStatus = "pending" | "paid" | "failed" | "refunded";

export interface Order {
  id: string;
  order_number: string;
  user_id: string;
  status: OrderStatus;
  total_cents: number;
  subtotal_cents: number;
  discount_cents: number;
  shipping_cents: number;
  tax_cents: number;
  shipping_address_json: {
    recipientName: string;
    phone: string;
    street: string;
    city: string;
    state: string;
    postalCode: string;
    country: string;
  };
  billing_address_json?: Record<string, any>;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  payment_reference?: string;
  coupon_code?: string | null;
  notes?: string | null;
  created_at: string;
  shipments?: Shipment[];
}

export type ShipmentStatus =
  | "placed"
  | "accepted"
  | "packed"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "returned";

export interface ShipmentItem {
  id: string;
  shipment_id: string;
  variant_id: string;
  product_id: string;
  product_title: string;
  variant_title: string;
  sku: string;
  unit_price_cents: number;
  quantity: number;
  total_price_cents: number;
  image_url?: string | null;
}

export interface ShipmentTrackingEvent {
  id: string;
  shipment_id: string;
  status: string;
  location: string;
  message: string;
  occurred_at: string;
}

export interface Shipment {
  id: string;
  order_id: string;
  shop_id: string;
  shipment_number: string;
  status: ShipmentStatus;
  subtotal_cents: number;
  commission_cents: number;
  vendor_payout_cents: number;
  shipping_fee_cents: number;
  courier_name?: string | null;
  tracking_number?: string | null;
  placed_at: string;
  accepted_at?: string | null;
  packed_at?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  cancelled_at?: string | null;
  cancel_reason?: string | null;
  created_at: string;
  shop_name?: string;
  shop_slug?: string;
  shop_logo?: string;
  items?: ShipmentItem[];
  tracking?: ShipmentTrackingEvent[];
}

export interface Review {
  id: string;
  product_id: string;
  shop_id: string;
  user_id: string;
  rating: number;
  title?: string | null;
  comment: string;
  verified_purchase: boolean;
  vendor_reply?: string | null;
  vendor_replied_at?: string | null;
  created_at: string;
  user_name?: string;
}

export interface Coupon {
  id: string;
  code: string;
  description?: string;
  discount_type: "percentage" | "flat";
  discount_value: number;
  min_order_cents: number;
  max_discount_cents?: number | null;
  is_active: boolean;
  expires_at?: string | null;
}

export interface LedgerAccount {
  id: string;
  holder_type: "platform" | "vendor" | "shopper";
  holder_id: string | null;
  currency: string;
  balance_cents: number;
}

export interface LedgerEntry {
  id: string;
  journal_id: string;
  debit_account_id: string;
  credit_account_id: string;
  amount_cents: number;
  entry_type: string;
  reference_type: string;
  reference_id: string;
  description: string;
  created_at: string;
}

export interface SettlementBatch {
  id: string;
  shop_id: string;
  batch_number: string;
  status: "draft" | "approved" | "processed";
  gross_sales_cents: number;
  commission_cents: number;
  refund_deductions_cents: number;
  net_payout_cents: number;
  period_start: string;
  period_end: string;
  payout_reference?: string;
  processed_at?: string;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  user: User;
  shop?: Shop | null;
}
