"""PC-009: the only way out of a multi-tenant preview — an allowlist proxy (R-071).

A preview runs code the model wrote. On a shared host it must not reach the platform's services,
the host, another user's app, or a cloud metadata endpoint, and it must not be a free relay to the
internet. Its network has no route out at all; this proxy is the one door, and it opens only to:

* hosts on the allowlist (package registries by default, plus ``OMNISTACKAI_EGRESS_ALLOW``);
* ports 80 and 443;
* public addresses — a name that resolves to a private, loopback, link-local (169.254.x.x, the
  metadata service), multicast or reserved address is refused even when the name is allowed, so a
  DNS answer cannot turn an allowed name into a way in.

HTTPS goes through CONNECT (the proxy never sees inside it); plain HTTP is forwarded. Standard
library only, so it runs from a bare Python image. Each decision is logged by host, never by path.
"""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
import sys

DEFAULT_ALLOW = (
    "registry.npmjs.org", "registry.yarnpkg.com", "pypi.org", "files.pythonhosted.org",
    "proxy.golang.org", "sum.golang.org", "storage.googleapis.com",
)
PORTS = (80, 443)


def allowlist() -> tuple[str, ...]:
    extra = [h.strip().lower() for h in os.environ.get("OMNISTACKAI_EGRESS_ALLOW", "").split(",") if h.strip()]
    return tuple(DEFAULT_ALLOW) + tuple(extra)


def host_allowed(host: str, allowed: tuple[str, ...]) -> bool:
    """Exact names, or ``.example.com`` entries for any subdomain."""
    host = host.lower().rstrip(".")
    for entry in allowed:
        if entry.startswith(".") and (host.endswith(entry) or host == entry[1:]):
            return True
        if host == entry:
            return True
    return False


def public_address(ip: str) -> bool:
    address = ipaddress.ip_address(ip)
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_multicast
                or address.is_reserved or address.is_unspecified)


def decide(host: str, port: int, allowed: tuple[str, ...], resolve=socket.getaddrinfo) -> tuple[str | None, str]:
    """(address to connect to, or None) and the reason, for one request."""
    if port not in PORTS:
        return None, f"port {port} is not allowed"
    if not host_allowed(host, allowed):
        return None, "host is not on the allowlist"
    try:
        infos = resolve(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return None, "host does not resolve"
    addresses = [info[4][0] for info in infos]
    if not addresses or not all(public_address(a) for a in addresses):
        return None, "host resolves to a non-public address"
    return addresses[0], "allowed"


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()


async def _handle(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
    allowed = allowlist()
    try:
        head = await asyncio.wait_for(client_reader.readuntil(b"\r\n\r\n"), timeout=15)
    except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        client_writer.close()
        return
    request_line = head.split(b"\r\n", 1)[0].decode("latin-1")
    parts = request_line.split(" ")
    if len(parts) != 3:
        client_writer.close()
        return
    method, target, _ = parts
    if method == "CONNECT":
        host, _, port_text = target.rpartition(":")
        port = int(port_text) if port_text.isdigit() else 443
        rest = b""
    else:
        if not target.startswith("http://"):
            client_writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            client_writer.close()
            return
        authority = target[len("http://"):].split("/", 1)[0]
        host, _, port_text = authority.partition(":")
        port = int(port_text) if port_text.isdigit() else 80
        path = "/" + target[len("http://"):].split("/", 1)[1] if "/" in target[len("http://"):] else "/"
        rest = head.replace(target.encode("latin-1"), path.encode("latin-1"), 1)
    host = host.strip("[]")
    address, reason = decide(host, port, allowed)
    print(f"egress {'ALLOW' if address else 'DENY '} {host}:{port} ({reason})", flush=True)
    if address is None:
        client_writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
        await client_writer.drain()
        client_writer.close()
        return
    try:
        upstream_reader, upstream_writer = await asyncio.wait_for(asyncio.open_connection(address, port), timeout=15)
    except (OSError, asyncio.TimeoutError):
        client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
        client_writer.close()
        return
    if method == "CONNECT":
        client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await client_writer.drain()
    else:
        upstream_writer.write(rest)
    await asyncio.gather(_pipe(client_reader, upstream_writer), _pipe(upstream_reader, client_writer))


async def _forward(listen: int, host: str, port: int) -> None:
    """Inbound only: a preview's published port, relayed to the preview on the private network."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            up_reader, up_writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=10)
        except (OSError, asyncio.TimeoutError):
            writer.close()
            return
        await asyncio.gather(_pipe(reader, up_writer), _pipe(up_reader, writer))

    server = await asyncio.start_server(handle, "0.0.0.0", listen)
    async with server:
        await server.serve_forever()


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "forward":
        # forward <port>:<host>:<port> ...  (the preview gateway)
        routes = [(int(a), h, int(b)) for a, h, b in (spec.split(":") for spec in sys.argv[2:])]

        async def relay() -> None:
            await asyncio.gather(*(_forward(*route) for route in routes))

        asyncio.run(relay())
        return
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3128

    async def serve() -> None:
        server = await asyncio.start_server(_handle, "0.0.0.0", port)
        print(f"egress proxy on :{port}, allowing {', '.join(allowlist())}", flush=True)
        async with server:
            await server.serve_forever()

    asyncio.run(serve())


if __name__ == "__main__":
    main()
