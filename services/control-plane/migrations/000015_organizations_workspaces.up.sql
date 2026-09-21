CREATE TABLE IF NOT EXISTS organizations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT NOT NULL,
    slug       TEXT NOT NULL UNIQUE,
    owner_id   UUID NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspaces (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    slug       TEXT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, slug)
);

CREATE INDEX IF NOT EXISTS workspaces_org_id_idx ON workspaces (org_id);

CREATE TABLE IF NOT EXISTS workspace_members (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role         TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workspace_id, user_id)
);

CREATE INDEX IF NOT EXISTS workspace_members_user_id_idx ON workspace_members (user_id);
CREATE INDEX IF NOT EXISTS workspace_members_workspace_id_idx ON workspace_members (workspace_id);

CREATE TABLE IF NOT EXISTS workspace_invites (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
    inviter_id   UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    email        TEXT NOT NULL,
    role         TEXT NOT NULL CHECK (role IN ('admin', 'member', 'viewer')),
    token        TEXT NOT NULL UNIQUE,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'revoked', 'expired')),
    expires_at   TIMESTAMPTZ NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS workspace_invites_workspace_id_idx ON workspace_invites (workspace_id);
CREATE INDEX IF NOT EXISTS workspace_invites_token_idx ON workspace_invites (token);
CREATE INDEX IF NOT EXISTS workspace_invites_email_idx ON workspace_invites (email);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS workspace_id UUID REFERENCES workspaces (id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS projects_workspace_id_idx ON projects (workspace_id);

-- Backfill: Create organization for any existing users. The users column is full_name (added in
-- 000003). This read `name`, which does not exist, so the control-plane could not start on any
-- database that already had users (found in R-518). Note: never put a semicolon in a comment
-- here, the migration runner splits statements on every semicolon.
INSERT INTO organizations (id, name, slug, owner_id)
SELECT gen_random_uuid(),
       COALESCE(NULLIF(TRIM(u.full_name), ''), 'Personal') || ' Org',
       'org-' || SUBSTRING(u.id::text, 1, 8) || '-' || SUBSTRING(gen_random_uuid()::text, 1, 4),
       u.id
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM organizations o WHERE o.owner_id = u.id
);

-- Backfill: Create default workspace for each organization
INSERT INTO workspaces (id, org_id, name, slug, is_default)
SELECT gen_random_uuid(),
       o.id,
       'Personal Workspace',
       'default',
       true
FROM organizations o
WHERE NOT EXISTS (
    SELECT 1 FROM workspaces w WHERE w.org_id = o.id AND w.is_default = true
);

-- Backfill: Add owners to workspace_members
INSERT INTO workspace_members (workspace_id, user_id, role)
SELECT w.id, o.owner_id, 'owner'
FROM workspaces w
JOIN organizations o ON w.org_id = o.id
WHERE NOT EXISTS (
    SELECT 1 FROM workspace_members wm WHERE wm.workspace_id = w.id AND wm.user_id = o.owner_id
);

-- Backfill: Assign workspace_id to existing projects created by the owner
UPDATE projects p
SET workspace_id = w.id
FROM organizations o
JOIN workspaces w ON w.org_id = o.id AND w.is_default = true
WHERE p.workspace_id IS NULL AND o.owner_id = p.user_id;
