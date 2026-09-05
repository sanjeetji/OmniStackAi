# Environments

Canonical promotion order:

`local -> test -> preview -> staging -> production`

R-002 adds only a local PostgreSQL+pgvector dependency. It binds to `127.0.0.1`, reads credentials
from ignored `.env`, and stores data in a named Docker volume. The exact image is pinned in
`infra/environments/local/compose.yaml`; no cloud database or remote infrastructure is provisioned.

Each future deployable must add typed configuration, fail-fast validation, isolated credentials,
and documented parity checks before it can advance beyond local.
