ALTER TABLE projects
    DROP COLUMN IF EXISTS analytics_property_id,
    DROP COLUMN IF EXISTS analytics_provider;
