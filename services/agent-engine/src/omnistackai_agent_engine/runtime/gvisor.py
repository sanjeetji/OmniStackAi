"""GVisorSandboxProvider - a real, free, self-hosted SandboxLifecycleProvider driver using gVisor
(R-489), the founder's requested free/open-source alternative to the three paid managed providers
(E2B/Vercel Sandbox/Daytona, R-486..R-488).

Positioned explicitly as a free/dev tier, not a production replacement: a self-hosted sandbox's
loopback URL only works for a same-machine viewer. The managed providers bundle real isolation
*plus* a globally-distributed public routing/proxy layer, auto-scaling, and reliability guarantees
- self-hosting gVisor gives you the isolation half for free, not the rest.

Unlike those three, this driver has no third-party account or API key at all - it talks directly
to the LOCAL Docker Engine API over its Unix socket (`docker_socket.py`, a new stdlib-only
transport; none of `sandbox_http.py`'s `urllib`-based HTTPS transport applies to a Unix socket),
running containers under gVisor's `runsc` runtime for real, standard, production-grade
kernel-level sandbox isolation (the same isolation Google Cloud Run itself uses) rather than a
bare, unsandboxed container.

Real prerequisite this driver cannot satisfy itself: gVisor's `runsc` binary must already be
installed and registered as a Docker runtime on the host (`runsc install`, or a manual
`/etc/docker/daemon.json` "runtimes" entry plus a daemon restart - see
gvisor.dev/docs/user_guide/quick_start/docker/). `active` verifies this for real by querying the
daemon's own `/info` endpoint rather than assuming.
"""

from __future__ import annotations

from typing import Any

from .contracts import SandboxHandle
from .docker_socket import DockerUnreachableError, request_json
from .errors import RuntimeProviderError, UnsupportedRuntimeTargetError

_RUNTIME_NAME = "runsc"
_DEFAULT_DOCKER_SOCKET = "/var/run/docker.sock"

# target -> (docker image, container port). Docker's own image ecosystem covers every target this
# platform generates, including Go (unlike Vercel Sandbox's runtime enum, which has no Go at all -
# see R-487) - a genuine, real advantage of this driver over the paid managed alternatives.
_TARGET_IMAGES: dict[str, tuple[str, int]] = {
    "nextjs-web": ("node:22-slim", 3000),
    "nextjs-admin": ("node:22-slim", 3001),
    "backend-python": ("python:3.13-slim", 8000),
    "backend-go": ("golang:1.23-alpine", 8080),
}


def _host_port(inspect_body: dict[str, Any], container_port_key: str) -> str | None:
    network_settings = inspect_body.get("NetworkSettings")
    if not isinstance(network_settings, dict):
        return None
    ports = network_settings.get("Ports")
    if not isinstance(ports, dict):
        return None
    bindings = ports.get(container_port_key)
    if not isinstance(bindings, list) or not bindings:
        return None
    first = bindings[0]
    host_port = first.get("HostPort") if isinstance(first, dict) else None
    return host_port if isinstance(host_port, str) and host_port else None


class GVisorSandboxProvider:
    """Creates, checks, and kills a real, gVisor-isolated local Docker container. Free and
    self-hosted - no API key, no third-party billing. `active` reflects whether the local Docker
    daemon is reachable *and* has the `runsc` runtime registered, verified live rather than
    assumed (this provider has no credential env var to check, unlike E2B/Vercel/Daytona)."""

    def __init__(self, *, socket_path: str = _DEFAULT_DOCKER_SOCKET, connection: Any | None = None) -> None:
        self._socket_path = socket_path
        self._connection = connection

    @property
    def id(self) -> str:
        return "gvisor"

    @property
    def active(self) -> bool:
        try:
            _status, info = request_json(
                "GET", "/v1.44/info", socket_path=self._socket_path, connection=self._connection
            )
        except DockerUnreachableError:
            return False
        runtimes = info.get("Runtimes")
        return isinstance(runtimes, dict) and _RUNTIME_NAME in runtimes

    def create(self, app_dir: str, target: str) -> SandboxHandle:
        del app_dir  # this task proves lifecycle management, not code sync - see R-489's contract
        spec = _TARGET_IMAGES.get(target)
        if spec is None:
            raise UnsupportedRuntimeTargetError(
                f"gVisor sandbox has no image mapping for target {target!r} "
                f"(supported: {', '.join(sorted(_TARGET_IMAGES))})"
            )
        image, container_port = spec
        container_port_key = f"{container_port}/tcp"

        _create_status, create_body = request_json(
            "POST",
            "/v1.44/containers/create",
            socket_path=self._socket_path,
            body={
                "Image": image,
                "ExposedPorts": {container_port_key: {}},
                "HostConfig": {
                    "Runtime": _RUNTIME_NAME,
                    # An empty HostPort tells Docker to auto-assign a free host port - never
                    # guessed, read back from the real inspect response below.
                    "PortBindings": {container_port_key: [{"HostPort": ""}]},
                },
                "Labels": {"source": "omnistackai"},
            },
            connection=self._connection,
        )
        container_id = create_body.get("Id")
        if not isinstance(container_id, str) or not container_id:
            raise RuntimeProviderError("Docker did not return a container Id")

        request_json(
            "POST",
            f"/v1.44/containers/{container_id}/start",
            socket_path=self._socket_path,
            connection=self._connection,
        )

        _inspect_status, inspect_body = request_json(
            "GET",
            f"/v1.44/containers/{container_id}/json",
            socket_path=self._socket_path,
            connection=self._connection,
        )
        host_port = _host_port(inspect_body, container_port_key)
        if host_port is None:
            raise RuntimeProviderError("Docker did not assign a host port for the exposed container port")

        state = inspect_body.get("State")
        status = state.get("Status") if isinstance(state, dict) else None
        return SandboxHandle(
            provider_id=self.id,
            sandbox_id=container_id,
            url=f"http://127.0.0.1:{host_port}",
            status=status if isinstance(status, str) and status else "running",
        )

    def status(self, handle: SandboxHandle) -> SandboxHandle:
        _status, inspect_body = request_json(
            "GET",
            f"/v1.44/containers/{handle.sandbox_id}/json",
            socket_path=self._socket_path,
            connection=self._connection,
        )
        state = inspect_body.get("State")
        current_status = state.get("Status") if isinstance(state, dict) else None
        return SandboxHandle(
            provider_id=handle.provider_id,
            sandbox_id=handle.sandbox_id,
            url=handle.url,
            status=current_status if isinstance(current_status, str) and current_status else handle.status,
        )

    def kill(self, handle: SandboxHandle) -> None:
        request_json(
            "POST",
            f"/v1.44/containers/{handle.sandbox_id}/kill",
            socket_path=self._socket_path,
            connection=self._connection,
        )
        request_json(
            "DELETE",
            f"/v1.44/containers/{handle.sandbox_id}",
            socket_path=self._socket_path,
            connection=self._connection,
        )
