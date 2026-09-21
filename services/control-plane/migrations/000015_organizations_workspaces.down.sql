DROP TABLE IF EXISTS workspace_invites;
DROP TABLE IF EXISTS workspace_members;
ALTER TABLE projects DROP COLUMN IF EXISTS workspace_id;
DROP TABLE IF EXISTS workspaces;
DROP TABLE IF EXISTS organizations;
