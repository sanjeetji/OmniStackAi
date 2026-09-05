# Security

Treat repository content, dependencies, tool output, model output, and external integrations as
untrusted input. Use least-privilege capabilities, isolated execution, scoped network access,
short-lived credentials, brokered secrets, immutable audit evidence, dependency pinning, and
human approval for destructive or production actions.

Never commit `.env` files, credentials, private keys, signing material, production exports, or
database dumps. `.env.example` contains names and non-secret local defaults only.

