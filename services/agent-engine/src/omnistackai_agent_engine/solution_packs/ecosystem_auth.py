"""Solution Pack Ecosystem Cross-App Authentication and Role Matrix (R-447).

Provides standard-library-only JWT token minting and verification (HS256 HMAC-SHA256),
canonical EcosystemAuthContract definitions, CrossAppAuthMatrix access control enforcement,
and automated cross-surface auth synthesis with 0 external dependencies (100% offline).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


def _b64url_encode(data: bytes) -> str:
    """Encode bytes into base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Decode base64url string with padding restoration."""
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("ascii"))


@dataclass(frozen=True)
class EcosystemRoleBinding:
    """One role bound to a specific surface in an ecosystem."""

    surface_slug: str
    role_id: str
    display_name: str
    allowed_surfaces: tuple[str, ...]
    authorized_actions: tuple[str, ...] = ("read", "write")
    scope_permissions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "role_id": self.role_id,
            "display_name": self.display_name,
            "allowed_surfaces": list(self.allowed_surfaces),
            "authorized_actions": list(self.authorized_actions),
            "scope_permissions": list(self.scope_permissions),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemRoleBinding:
        return cls(
            surface_slug=str(data["surface_slug"]),
            role_id=str(data["role_id"]),
            display_name=str(data.get("display_name", data["role_id"])),
            allowed_surfaces=tuple(data.get("allowed_surfaces", ())),
            authorized_actions=tuple(data.get("authorized_actions", ("read", "write"))),
            scope_permissions=tuple(data.get("scope_permissions", ())),
        )


@dataclass(frozen=True)
class EcosystemAuthContract:
    """Shared cross-app authentication specification for an ecosystem."""

    ecosystem_id: str
    jwt_algorithm: str = "HS256"
    jwt_secret: str = "local-dev-secret"
    issuer: str = ""
    audience: str = ""
    token_ttl_seconds: int = 86400
    roles: tuple[EcosystemRoleBinding, ...] = ()

    def __post_init__(self) -> None:
        if not self.issuer:
            object.__setattr__(self, "issuer", f"omnistackai:{self.ecosystem_id}")
        if not self.audience:
            object.__setattr__(self, "audience", f"omnistackai:{self.ecosystem_id}:api")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "jwt_algorithm": self.jwt_algorithm,
            "jwt_secret": self.jwt_secret,
            "issuer": self.issuer,
            "audience": self.audience,
            "token_ttl_seconds": self.token_ttl_seconds,
            "roles": [r.to_dict() for r in self.roles],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemAuthContract:
        roles_data = data.get("roles", ())
        roles = tuple(EcosystemRoleBinding.from_dict(r) for r in roles_data)
        return cls(
            ecosystem_id=str(data["ecosystem_id"]),
            jwt_algorithm=str(data.get("jwt_algorithm", "HS256")),
            jwt_secret=str(data.get("jwt_secret", "local-dev-secret")),
            issuer=str(data.get("issuer", "")),
            audience=str(data.get("audience", "")),
            token_ttl_seconds=int(data.get("token_ttl_seconds", 86400)),
            roles=roles,
        )


@dataclass(frozen=True)
class CrossAppAuthMatrix:
    """Access control matrix evaluating permissions and surface accessibility."""

    surface_access: tuple[tuple[str, tuple[str, ...]], ...]
    permissions: tuple[tuple[str, tuple[str, ...]], ...]

    @classmethod
    def from_contract(cls, contract: EcosystemAuthContract) -> CrossAppAuthMatrix:
        surf_acc: list[tuple[str, tuple[str, ...]]] = []
        perms: list[tuple[str, tuple[str, ...]]] = []
        for role in contract.roles:
            surf_acc.append((role.role_id, tuple(role.allowed_surfaces)))
            perms.append((role.role_id, tuple(role.scope_permissions)))
        return cls(
            surface_access=tuple(surf_acc),
            permissions=tuple(perms),
        )

    def can_access_surface(self, role_id: str, surface_slug: str) -> bool:
        for r_id, surfaces in self.surface_access:
            if r_id == role_id:
                return surface_slug in surfaces
        return False

    def has_permission(self, role_id: str, permission: str) -> bool:
        for r_id, perms in self.permissions:
            if r_id == role_id:
                return permission in perms
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_access": {r: list(s) for r, s in self.surface_access},
            "permissions": {r: list(p) for r, p in self.permissions},
        }


def mint_ecosystem_token(
    contract: EcosystemAuthContract,
    role_id: str,
    subject: str | None = None,
    extra_claims: Mapping[str, Any] | None = None,
    expires_in: int | None = None,
    surface_slug: str | None = None,
) -> str:
    """Mint a standard-compliant JWT token signed with HMAC-SHA256 (HS256)."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    ttl = expires_in if expires_in is not None else contract.token_ttl_seconds
    exp = now + ttl

    # Find matching surface slug for role if not explicitly provided
    resolved_surface_slug = surface_slug
    if resolved_surface_slug is None:
        for r in contract.roles:
            if r.role_id == role_id:
                resolved_surface_slug = r.surface_slug
                break
    if resolved_surface_slug is None:
        resolved_surface_slug = ""

    payload: dict[str, Any] = {
        "sub": subject or f"{role_id}-demo-user",
        "iss": contract.issuer,
        "aud": contract.audience,
        "roles": [role_id],
        "surface_slug": resolved_surface_slug,
        "iat": now,
        "exp": exp,
    }
    if extra_claims:
        payload.update(extra_claims)

    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = _b64url_encode(header_bytes)
    payload_b64 = _b64url_encode(payload_bytes)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    sig = hmac.new(contract.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_ecosystem_token(contract: EcosystemAuthContract, token: str) -> dict[str, Any]:
    """Verify an ecosystem JWT token signature, structure, and expiration."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format: token must contain 3 period-separated parts")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    try:
        expected_sig = hmac.new(contract.jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig_b64)
    except Exception as e:
        raise ValueError(f"Failed to decode token signature: {e}") from e

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid token signature: secret or payload mismatch")

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to decode token payload: {e}") from e

    if "exp" in payload and isinstance(payload["exp"], (int, float)):
        if payload["exp"] < time.time():
            raise ValueError(f"Token has expired (exp={payload['exp']}, now={int(time.time())})")

    return payload


def generate_surface_tokens(contract: EcosystemAuthContract) -> dict[str, str]:
    """Generate demonstration/seed JWT tokens for all surfaces in the contract."""
    tokens: dict[str, str] = {}
    for role in contract.roles:
        token = mint_ecosystem_token(
            contract=contract,
            role_id=role.role_id,
            subject=f"demo-{role.role_id}-001",
            surface_slug=role.surface_slug,
        )
        tokens[role.surface_slug] = token
    return tokens


def synthesize_ecosystem_auth(ecosystem_id: str, surfaces: Sequence[Any]) -> EcosystemAuthContract:
    """Deterministically derive an EcosystemAuthContract from an ecosystem's surfaces."""
    roles: list[EcosystemRoleBinding] = []
    all_surface_slugs = tuple(
        getattr(s, "slug", s.get("slug", "") if isinstance(s, dict) else "")
        for s in surfaces
    )

    for s in surfaces:
        slug = getattr(s, "slug", s.get("slug", "") if isinstance(s, dict) else "")
        app_name = getattr(s, "app_name", s.get("app_name", "") if isinstance(s, dict) else "")
        surface_kind = getattr(s, "surface_kind", s.get("surface_kind", "") if isinstance(s, dict) else "")

        # Extract roles from IR
        ir_dict = getattr(s, "ir_dict", s.get("ir_dict") if isinstance(s, dict) else None)
        ir_roles = []
        if ir_dict and isinstance(ir_dict, dict) and "roles" in ir_dict:
            for r in ir_dict["roles"]:
                if isinstance(r, dict) and "id" in r:
                    ir_roles.append(r["id"])
                elif isinstance(r, str):
                    ir_roles.append(r)
        elif hasattr(s, "ir") and getattr(s.ir, "roles", None):
            ir_roles = [r.id for r in s.ir.roles]

        # Select role based on surface_kind affinity
        role_id = ""
        if surface_kind in ("public_web", "customer_web", "customer_pwa"):
            for candidate in ("reader", "customer", "viewer", "guest", "client", "user"):
                if candidate in ir_roles:
                    role_id = candidate
                    break
        elif "admin" in surface_kind:
            for candidate in ("admin", "super_admin", "manager", "operator"):
                if candidate in ir_roles:
                    role_id = candidate
                    break

        if not role_id:
            role_id = ir_roles[0] if ir_roles else (slug.replace("-", "_") or "user")

        is_admin = "admin" in surface_kind or "admin" in role_id.lower()
        allowed_surfaces = all_surface_slugs if is_admin else (slug,)
        authorized_actions = ("read", "write", "admin") if is_admin else ("read", "write")

        # Collect entity permissions from IR
        permissions: list[str] = []
        entities = []
        if ir_dict and isinstance(ir_dict, dict) and "entities" in ir_dict:
            entities = [e["name"] for e in ir_dict["entities"] if isinstance(e, dict) and "name" in e]
        elif hasattr(s, "ir") and getattr(s.ir, "entities", None):
            entities = [e.name for e in s.ir.entities]

        for ent in sorted(entities):
            permissions.append(f"{ent}:read")
            if is_admin or not ("read_only" in surface_kind):
                permissions.append(f"{ent}:write")

        roles.append(
            EcosystemRoleBinding(
                surface_slug=slug,
                role_id=role_id,
                display_name=app_name or role_id.capitalize(),
                allowed_surfaces=allowed_surfaces,
                authorized_actions=authorized_actions,
                scope_permissions=tuple(permissions),
            )
        )

    return EcosystemAuthContract(
        ecosystem_id=ecosystem_id,
        jwt_algorithm="HS256",
        jwt_secret="local-dev-secret",
        issuer=f"omnistackai:{ecosystem_id}",
        audience=f"omnistackai:{ecosystem_id}:api",
        token_ttl_seconds=86400,
        roles=tuple(roles),
    )
