"""DaytonaSandboxProvider - a real SandboxLifecycleProvider driver for Daytona (R-488).

Verified against Daytona's own documented REST API (daytona.io/docs, fetched directly - not
assumed from training data): `POST/GET/DELETE https://api.daytona.io/sandbox[/{id}]`,
`Authorization: Bearer <key>` auth. Unlike E2B (a URL pattern) and Vercel Sandbox (a `routes[]`
array in the create response), Daytona's create response carries no URL at all - a separate call,
`GET /sandbox/{id}/ports/{port}/preview-url`, is required. No Daytona SDK is used - stdlib-only
HTTP via the same shared `sandbox_http.py` R-486 introduced for E2B, unchanged.
"""

from __future__ import annotations

import os
from urllib.request import OpenerDirector

from .contracts import SandboxHandle
from .errors import RuntimeProviderError
from .local import LocalRuntimeProvider
from .providers import RUNTIME_SPECS
from .sandbox_http import request_json

_API_BASE = "https://api.daytona.io"


class MissingSandboxCredentialError(RuntimeProviderError):
    code = "missing_sandbox_credential"


def _port_for_target(app_dir: str, target: str) -> int:
    """Reuses `LocalRuntimeProvider`'s own target->port mapping - the same helper shape R-486/
    R-487 already use, kept identical rather than duplicated a third time."""
    local_plan = LocalRuntimeProvider().preview_plan(app_dir, target)
    return int(local_plan.url.rsplit(":", 1)[1])


class DaytonaSandboxProvider:
    """Creates, checks, and kills a real Daytona sandbox. Activated by `DAYTONA_API_KEY`
    (`RUNTIME_SPECS["daytona"]`'s existing key env, declared since an earlier task, unused until
    now)."""

    def __init__(self, *, opener: OpenerDirector | None = None) -> None:
        self._spec = RUNTIME_SPECS["daytona"]
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
        return {"Authorization": f"Bearer {self._api_key()}"}

    def create(self, app_dir: str, target: str) -> SandboxHandle:
        port = _port_for_target(app_dir, target)

        _create_status, create_body = request_json(
            "POST",
            f"{_API_BASE}/sandbox",
            headers=self._headers(),
            # `public: true` is required so this contract's single `SandboxHandle.url` string can
            # be loaded directly (a plain iframe/browser fetch) - a non-public sandbox's preview
            # URL needs a companion X-Daytona-Preview-Token header this contract has no room for.
            # Every other field (snapshot, target/region, cpu, memory, disk, ...) is left unset -
            # Daytona's own docs confirm each has a real platform default, so this task does not
            # guess values for fields whose exact required/optional status wasn't independently
            # confirmable from the fetched documentation (the same conservative approach R-486
            # took for E2B's templateID default).
            body={"public": True, "labels": {"source": "omnistackai"}},
            opener=self._opener,
        )
        sandbox_id = create_body.get("id")
        if not isinstance(sandbox_id, str) or not sandbox_id:
            raise RuntimeProviderError("Daytona did not return a sandbox id")

        _preview_status, preview_body = request_json(
            "GET",
            f"{_API_BASE}/sandbox/{sandbox_id}/ports/{port}/preview-url",
            headers=self._headers(),
            opener=self._opener,
        )
        url = preview_body.get("url")
        if not isinstance(url, str) or not url:
            raise RuntimeProviderError("Daytona did not return a preview url")

        status = create_body.get("state")
        return SandboxHandle(
            provider_id=self.id,
            sandbox_id=sandbox_id,
            url=url,
            status=status if isinstance(status, str) and status else "started",
        )

    def status(self, handle: SandboxHandle) -> SandboxHandle:
        _status, response_body = request_json(
            "GET",
            f"{_API_BASE}/sandbox/{handle.sandbox_id}",
            headers=self._headers(),
            opener=self._opener,
        )
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
            f"{_API_BASE}/sandbox/{handle.sandbox_id}",
            headers=self._headers(),
            opener=self._opener,
        )
