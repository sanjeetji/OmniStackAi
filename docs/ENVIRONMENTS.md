# Environments

Canonical promotion order:

`local -> test -> preview -> staging -> production`

R-002 adds only a local PostgreSQL+pgvector dependency. It binds to `127.0.0.1`, reads credentials
from ignored `.env`, and stores data in a named Docker volume. The exact image is pinned in
`infra/environments/local/compose.yaml`; no cloud database or remote infrastructure is provisioned.

R-004 adds the Go control-plane as the second local Compose service. Its host port is bound to
`127.0.0.1`, its container runs as a non-root user, and readiness depends on a bounded PostgreSQL
ping. The Stage 0 HTTP surface contains only `/healthz` and `/readyz`.

Each future deployable must add typed configuration, fail-fast validation, isolated credentials,
and documented parity checks before it can advance beyond local.
