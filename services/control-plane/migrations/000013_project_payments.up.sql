ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS payment_gateway TEXT NOT NULL DEFAULT ''
        CHECK (payment_gateway IN ('', 'stripe', 'razorpay'));
