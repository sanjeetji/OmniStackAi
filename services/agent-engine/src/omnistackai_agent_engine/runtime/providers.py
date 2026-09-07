"""Declared cloud sandbox (runtime) and deployment providers — activated by key presence.

These describe the Tier 2/3 options. They carry no secret: only a name, kind, the env var that holds
the key, and a home URL. Adding the key (and selecting the provider) is all that is needed to light one
up — the same add-a-key pattern as the cloud model adapters.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    name: str
    kind: str  # "sandbox" (run untrusted generated code) or "deploy" (host it)
    key_env: str
    home_url: str


# Sandbox/runtime providers for running generated apps off the local machine (Tier 2/3).
RUNTIME_SPECS: dict[str, ProviderSpec] = {
    "e2b": ProviderSpec("e2b", "sandbox", "E2B_API_KEY", "https://e2b.dev"),
    "daytona": ProviderSpec("daytona", "sandbox", "DAYTONA_API_KEY", "https://daytona.io"),
    "fly-machines": ProviderSpec("fly-machines", "sandbox", "FLY_API_TOKEN", "https://fly.io"),
}

# Deployment/hosting providers (Tier 2/3).
DEPLOY_SPECS: dict[str, ProviderSpec] = {
    "vercel": ProviderSpec("vercel", "deploy", "VERCEL_TOKEN", "https://vercel.com"),
    "fly": ProviderSpec("fly", "deploy", "FLY_API_TOKEN", "https://fly.io"),
    "render": ProviderSpec("render", "deploy", "RENDER_API_KEY", "https://render.com"),
    "netlify": ProviderSpec("netlify", "deploy", "NETLIFY_AUTH_TOKEN", "https://netlify.com"),
}
