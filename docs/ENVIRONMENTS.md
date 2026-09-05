# Environments

Canonical promotion order:

`local -> test -> preview -> staging -> production`

R-001 defines names and placeholder configuration only. It does not provision environments.
Each future deployable must add typed configuration, fail-fast validation, isolated credentials,
and documented parity checks before it can advance through the environments.

