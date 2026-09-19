"""E2BSandboxProvider - a real SandboxLifecycleProvider driver for E2B (R-486).

Verified against E2B's own documented REST API (docs.e2b.dev, fetched directly - not assumed from
training data): `POST`/`DELETE https://api.e2b.app/sandboxes[/{id}]`, `X-API-Key` header auth, a
`sandboxID` in the create response, and the public URL pattern `https://{port}-{sandboxID}.e2b.app`.
No E2B SDK is used - stdlib-only HTTP via `sandbox_http.py`, matching this codebase's existing
no-vendor-SDK discipline for every other cloud provider (`model_gateway/cloud.py`'s LLM adapters).
"""

from __future__ import annotations

import os
from urllib.request import OpenerDirector

from .contracts import SandboxHandle
from .errors import RuntimeProviderError
from .local import LocalRuntimeProvider
from .providers import RUNTIME_SPECS
from .sandbox_http import request_json

_API_BASE = "https://api.e2b.app"

# E2B's own documented generic default template (docs.e2b.dev/sandbox-template) - a real generated
# OmniStackAI app needs a custom template with the right toolchain pre-installed, which is a
# separate, later concern once a real account exists to build one against (see R-486's contract's
# scope boundary). Overridable so that later work doesn't need to touch this driver's code.
_DEFAULT_TEMPLATE_ID = "base"
_DEFAULT_SANDBOX_TIMEOUT_SECONDS = 300  # 5 minutes - enough for an install + preview session


class MissingSandboxCredentialError(RuntimeProviderError):
    code = "missing_sandbox_credential"


def _port_for_target(app_dir: str, target: str) -> int:
    """The local port a target listens on, per `LocalRuntimeProvider`'s own target->port mapping
    (the single source of truth for this already, reused rather than duplicated) - raises
    `UnsupportedRuntimeTargetError` for an unknown target, the same error the local provider
    already raises for the same case."""
    local_plan = LocalRuntimeProvider().preview_plan(app_dir, target)
    return int(local_plan.url.rsplit(":", 1)[1])


class E2BSandboxProvider:
    """Creates, checks, and kills a real E2B sandbox - a Firecracker microVM the provider
    provisions on request. Activated by `E2B_API_KEY` (`RUNTIME_SPECS["e2b"]`'s existing key env,
    declared but unused until this task)."""

    def __init__(self, *, opener: OpenerDirector | None = None) -> None:
        self._spec = RUNTIME_SPECS["e2b"]
        self._opener = opener

    @property
    def id(self) -> str:
        return self._spec.name

    @property
    def active(self) -> bool:
        return bool(os.environ.get(self._spec.key_env, "").strip())

    def _api_key(self) -> str:
        key = os.environ.get(self._spec.key_env, "").strip()
        if not key:
            raise MissingSandboxCredentialError(f"{self._spec.key_env} is not set")
        return key

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key()}

    def create(self, app_dir: str, target: str) -> SandboxHandle:
        port = _port_for_target(app_dir, target)
        template_id = os.environ.get("E2B_TEMPLATE_ID", "").strip() or _DEFAULT_TEMPLATE_ID
        _status, response_body = request_json(
            "POST",
            f"{_API_BASE}/sandboxes",
            headers=self._headers(),
            body={"templateID": template_id, "timeout": _DEFAULT_SANDBOX_TIMEOUT_SECONDS},
            opener=self._opener,
        )
        sandbox_id = response_body.get("sandboxID")
        if not isinstance(sandbox_id, str) or not sandbox_id:
            raise RuntimeProviderError("E2B did not return a sandboxID")
        return SandboxHandle(
            provider_id=self.id,
            sandbox_id=sandbox_id,
            url=f"https://{port}-{sandbox_id}.e2b.app",
            status="running",
        )

    def status(self, handle: SandboxHandle) -> SandboxHandle:
        _status, response_body = request_json(
            "GET",
            f"{_API_BASE}/sandboxes/{handle.sandbox_id}",
            headers=self._headers(),
            opener=self._opener,
        )
        # E2B's GET-by-id response shape was not directly verifiable without a real account
        # (undocumented in the pages fetched for this task) - defensively keep the handle's own
        # status when the response carries no recognizable state field, rather than guessing.
        state = response_body.get("state")
        return SandboxHandle(
            provider_id=handle.provider_id,
            sandbox_id=handle.sandbox_id,
            url=handle.url,
            status=state if isinstance(state, str) and state else handle.status,
        )

    def kill(self, handle: SandboxHandle) -> None:
        request_json(
            "DELETE",
            f"{_API_BASE}/sandboxes/{handle.sandbox_id}",
            headers=self._headers(),
            opener=self._opener,
        )
