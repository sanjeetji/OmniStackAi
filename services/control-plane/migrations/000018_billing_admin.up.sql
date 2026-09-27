-- PC-011: platform billing (credit top-ups and plans through Stripe and Razorpay) and the
-- super_admin console.

-- Every checkout the platform created, so a payment can be matched to what was bought.
CREATE TABLE IF NOT EXISTS billing_orders (
    id TEXT PRIMARY KEY,                       -- provider's session / order / subscription id
    provider TEXT NOT NULL CHECK (provider IN ('stripe', 'razorpay')),
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('credits', 'plan')),
    item_id TEXT NOT NULL,                     -- credit pack id or plan id
    credits BIGINT NOT NULL DEFAULT 0,
    amount_minor BIGINT NOT NULL,              -- cents / paise
    currency TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'paid', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS billing_orders_user_idx ON billing_orders (user_id, created_at);

-- Every payment event acted on, once: a provider that delivers an event twice grants nothing twice.
CREATE TABLE IF NOT EXISTS billing_events (
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    user_id UUID REFERENCES users (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (provider, event_id)
);

-- A user's paid plan, as the provider reports it.
CREATE TABLE IF NOT EXISTS billing_subscriptions (
    user_id UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    subscription_id TEXT NOT NULL,
    customer_id TEXT NOT NULL DEFAULT '',
    plan TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Platform-wide switches the super_admin console changes live (the paid-work kill switch).
CREATE TABLE IF NOT EXISTS platform_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_by UUID REFERENCES users (id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every super_admin action, for accountability.
CREATE TABLE IF NOT EXISTS admin_audit (
    id BIGSERIAL PRIMARY KEY,
    actor_id UUID REFERENCES users (id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    target_user_id UUID REFERENCES users (id) ON DELETE SET NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS admin_audit_created_idx ON admin_audit (created_at DESC);
