-- 003_orders.sql: Carts, multi-vendor split orders, per-vendor shipments, tracking, and returns

CREATE TABLE IF NOT EXISTS carts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  session_token VARCHAR(120),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_carts_user ON carts(user_id);
CREATE INDEX IF NOT EXISTS idx_carts_session ON carts(session_token);

CREATE TABLE IF NOT EXISTS cart_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
  shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
  quantity INT NOT NULL CHECK (quantity > 0),
  price_cents BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_cart_variant UNIQUE (cart_id, variant_id)
);

CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_shop ON cart_items(shop_id);

CREATE TABLE IF NOT EXISTS orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_number VARCHAR(64) NOT NULL UNIQUE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status VARCHAR(32) NOT NULL DEFAULT 'processing' CHECK (status IN ('pending_payment', 'processing', 'partially_shipped', 'completed', 'cancelled')),
  total_cents BIGINT NOT NULL,
  subtotal_cents BIGINT NOT NULL,
  discount_cents BIGINT NOT NULL DEFAULT 0,
  shipping_cents BIGINT NOT NULL DEFAULT 0,
  tax_cents BIGINT NOT NULL DEFAULT 0,
  shipping_address_json JSONB NOT NULL,
  billing_address_json JSONB,
  payment_method VARCHAR(32) NOT NULL CHECK (payment_method IN ('mock_card', 'mock_upi', 'cod')),
  payment_status VARCHAR(32) NOT NULL DEFAULT 'paid' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')),
  payment_reference VARCHAR(120),
  coupon_code VARCHAR(32),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);

-- Per-Vendor Shipments (Sub-orders)
CREATE TABLE IF NOT EXISTS shipments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE RESTRICT,
  shipment_number VARCHAR(64) NOT NULL UNIQUE,
  status VARCHAR(32) NOT NULL DEFAULT 'placed' CHECK (status IN ('placed', 'accepted', 'packed', 'shipped', 'delivered', 'cancelled', 'returned')),
  subtotal_cents BIGINT NOT NULL,
  commission_cents BIGINT NOT NULL DEFAULT 0,
  vendor_payout_cents BIGINT NOT NULL DEFAULT 0,
  shipping_fee_cents BIGINT NOT NULL DEFAULT 0,
  courier_name VARCHAR(64),
  tracking_number VARCHAR(64),
  placed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  accepted_at TIMESTAMPTZ,
  packed_at TIMESTAMPTZ,
  shipped_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ,
  cancel_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_order ON shipments(order_id);
CREATE INDEX IF NOT EXISTS idx_shipments_shop ON shipments(shop_id);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);

CREATE TABLE IF NOT EXISTS shipment_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
  variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT,
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
  product_title VARCHAR(200) NOT NULL,
  variant_title VARCHAR(120) NOT NULL,
  sku VARCHAR(64) NOT NULL,
  unit_price_cents BIGINT NOT NULL,
  quantity INT NOT NULL CHECK (quantity > 0),
  total_price_cents BIGINT NOT NULL,
  image_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_shipment_items_shipment ON shipment_items(shipment_id);

CREATE TABLE IF NOT EXISTS shipment_tracking_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
  status VARCHAR(32) NOT NULL,
  location VARCHAR(120) NOT NULL,
  message TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracking_shipment ON shipment_tracking_events(shipment_id);

CREATE TABLE IF NOT EXISTS order_returns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id UUID NOT NULL REFERENCES shipments(id) ON DELETE RESTRICT,
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE RESTRICT,
  reason VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'requested' CHECK (status IN ('requested', 'approved', 'rejected', 'completed')),
  refund_amount_cents BIGINT NOT NULL,
  vendor_note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_returns_shipment ON order_returns(shipment_id);
CREATE INDEX IF NOT EXISTS idx_returns_shop ON order_returns(shop_id);
