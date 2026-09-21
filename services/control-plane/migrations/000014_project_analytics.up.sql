ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS analytics_provider    TEXT NOT NULL DEFAULT ''
        CHECK (analytics_provider IN ('', 'ga4')),
    ADD COLUMN IF NOT EXISTS analytics_property_id TEXT NOT NULL DEFAULT '';
