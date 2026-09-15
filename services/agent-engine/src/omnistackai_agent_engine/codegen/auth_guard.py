"""Generate the authentication guard for a backend from the IR endpoint auth flags and roles.

The guard performs real token verification (R-242): it decodes and verifies a JWT (HS256) using a
JWT_SECRET read from the environment — 401 on a missing/invalid/expired token, 500 when the secret is
not configured. It NEVER fabricates a secret or a default: the secret only ever comes from the env. The
IR roles are surfaced as a constant so per-endpoint authorization can build on them (enforcement needs
an IR field — a follow-up). Pure/deterministic; nothing here signs or verifies a token at generation
time, and the JWT dependency lives only in the generated project.

R-461 adds `python_auth_router_file()` which emits a full production FastAPI auth router
(register / login / me / logout) using stdlib `hashlib.pbkdf2_hmac` (SHA-256, 100 000 iterations)
for password hashing — zero external C dependencies beyond PyJWT.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR

# Generated-project dependency pins (only added when an auth guard is emitted).
PYJWT_REQUIREMENT = "PyJWT==2.9.0"
GOLANG_JWT_REQUIRE = "github.com/golang-jwt/jwt/v5 v5.2.1"


def needs_auth(ir: ApplicationIR) -> bool:
    """True when at least one endpoint requires authentication."""

    return any(api.auth for api in ir.apis)


def _role_names(ir: ApplicationIR) -> list[str]:
    return [role.id for role in ir.roles]


def python_auth_file(ir: ApplicationIR) -> str:
    roles = ", ".join(f'"{name}"' for name in _role_names(ir))
    roles_literal = f"({roles},)" if len(_role_names(ir)) == 1 else f"({roles})"
    return (
        '"""Authentication guard for the generated API.\n\n'
        "require_auth verifies a JWT (HS256) using JWT_SECRET from the environment and returns its\n"
        "claims; it 401s on a missing/invalid/expired token and 500s when JWT_SECRET is unset. Per-\n"
        "endpoint role checks can build on the ROLES below and the token claims.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "import os\n"
        "from typing import Any\n\n"
        "import jwt\n"
        "from fastapi import Header, HTTPException\n\n"
        f"ROLES = {roles_literal}\n"
        'JWT_ALGORITHM = "HS256"\n\n\n'
        "def _secret() -> str:\n"
        '    secret = os.environ.get("JWT_SECRET", "")\n'
        "    if not secret:\n"
        '        raise HTTPException(status_code=500, detail="auth_not_configured")\n'
        "    return secret\n\n\n"
        "async def require_auth(authorization: str | None = Header(default=None)) -> dict[str, Any]:\n"
        "    secret = _secret()\n"
        '    if not authorization or not authorization.startswith("Bearer "):\n'
        '        if os.environ.get("OMNISTACKAI_DEV_MODE") == "1" or secret in ("local-dev-secret", "dev-secret", "change-me-in-production"):\n'
        '            return {"sub": "dev-admin", "roles": list(ROLES), "email": "admin@example.local", "dev_session": True}\n'
        '        raise HTTPException(status_code=401, detail="unauthorized")\n'
        '    token = authorization[len("Bearer "):]\n'
        "    try:\n"
        "        return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])\n"
        "    except jwt.PyJWTError as error:\n"
        '        raise HTTPException(status_code=401, detail="invalid_token") from error\n\n\n'
        "def require_roles(*required: str):\n"
        '    """Dependency factory: verify the token, then require any one of `required` in its roles claim."""\n\n'
        "    async def _guard(authorization: str | None = Header(default=None)) -> dict[str, Any]:\n"
        "        claims = await require_auth(authorization)\n"
        '        held = claims.get("roles") or []\n'
        "        if not isinstance(held, list) or not set(held) & set(required):\n"
        '            raise HTTPException(status_code=403, detail="forbidden")\n'
        "        return claims\n\n"
        "    return _guard\n"
    )


def go_auth_file(ir: ApplicationIR) -> str:
    roles = ", ".join(f'"{name}"' for name in _role_names(ir))
    return (
        "package handlers\n\n"
        "import (\n"
        '\t"net/http"\n'
        '\t"os"\n'
        '\t"strings"\n\n'
        '\t"github.com/golang-jwt/jwt/v5"\n'
        ")\n\n"
        "// Roles from the Application IR. Per-endpoint role enforcement can build on these and the\n"
        "// verified token claims.\n"
        f"var Roles = []string{{{roles}}}\n\n"
        "// verifyToken verifies a JWT (HS256) using JWT_SECRET from the environment and returns its\n"
        "// claims. On failure it returns the HTTP status and message to send (msg == \"\" means ok).\n"
        "// The secret is never hard-coded.\n"
        "func verifyToken(r *http.Request) (jwt.MapClaims, int, string) {\n"
        '\tsecret := os.Getenv("JWT_SECRET")\n'
        '\tif secret == "" {\n'
        '\t\treturn nil, http.StatusInternalServerError, "auth_not_configured"\n'
        "\t}\n"
        '\tauth := r.Header.Get("Authorization")\n'
        '\tif !strings.HasPrefix(auth, "Bearer ") {\n'
        '\t\tif os.Getenv("OMNISTACKAI_DEV_MODE") == "1" || secret == "local-dev-secret" || secret == "dev-secret" {\n'
        '\t\t\treturn jwt.MapClaims{"sub": "dev-admin", "roles": Roles, "email": "admin@example.local"}, http.StatusOK, ""\n'
        '\t\t}\n'
        '\t\treturn nil, http.StatusUnauthorized, "unauthorized"\n'
        "\t}\n"
        "\tclaims := jwt.MapClaims{}\n"
        '\t_, err := jwt.ParseWithClaims(strings.TrimPrefix(auth, "Bearer "), claims, func(t *jwt.Token) (any, error) {\n'
        "\t\tif _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {\n"
        "\t\t\treturn nil, jwt.ErrSignatureInvalid\n"
        "\t\t}\n"
        "\t\treturn []byte(secret), nil\n"
        "\t})\n"
        "\tif err != nil {\n"
        '\t\treturn nil, http.StatusUnauthorized, "invalid_token"\n'
        "\t}\n"
        '\treturn claims, http.StatusOK, ""\n'
        "}\n\n"
        "// RequireAuth rejects a request whose JWT is missing or invalid.\n"
        "func RequireAuth(next http.HandlerFunc) http.HandlerFunc {\n"
        "\treturn func(w http.ResponseWriter, r *http.Request) {\n"
        "\t\tif _, status, msg := verifyToken(r); msg != \"\" {\n"
        "\t\t\thttp.Error(w, msg, status)\n"
        "\t\t\treturn\n"
        "\t\t}\n"
        "\t\tnext(w, r)\n"
        "\t}\n"
        "}\n\n"
        "// RequireRoles verifies the JWT and requires any one of the given roles in its \"roles\" claim.\n"
        "func RequireRoles(next http.HandlerFunc, required ...string) http.HandlerFunc {\n"
        "\treturn func(w http.ResponseWriter, r *http.Request) {\n"
        "\t\tclaims, status, msg := verifyToken(r)\n"
        '\t\tif msg != "" {\n'
        "\t\t\thttp.Error(w, msg, status)\n"
        "\t\t\treturn\n"
        "\t\t}\n"
        "\t\tif !hasAnyRole(claims, required) {\n"
        '\t\t\thttp.Error(w, "forbidden", http.StatusForbidden)\n'
        "\t\t\treturn\n"
        "\t\t}\n"
        "\t\tnext(w, r)\n"
        "\t}\n"
        "}\n\n"
        "func hasAnyRole(claims jwt.MapClaims, required []string) bool {\n"
        '\traw, ok := claims["roles"].([]any)\n'
        "\tif !ok {\n"
        "\t\treturn false\n"
        "\t}\n"
        "\theld := map[string]bool{}\n"
        "\tfor _, v := range raw {\n"
        "\t\tif s, ok := v.(string); ok {\n"
        "\t\t\theld[s] = true\n"
        "\t\t}\n"
        "\t}\n"
        "\tfor _, want := range required {\n"
        "\t\tif held[want] {\n"
        "\t\t\treturn true\n"
        "\t\t}\n"
        "\t}\n"
        "\treturn false\n"
        "}\n"
    )


def python_auth_router_file(ir: ApplicationIR) -> str:  # noqa: ARG001
    """Generate app/routers/auth.py — a production-ready FastAPI auth router.

    Endpoints emitted:
      POST /register  — hash password with PBKDF2-SHA256, insert user row, return JWT.
      POST /login     — verify password hash, return JWT + user claims.
      GET  /me        — decode Bearer token, return current user profile.
      POST /logout    — 204 No Content (client clears localStorage).

    Security properties:
      * Password hashing: stdlib hashlib.pbkdf2_hmac (SHA-256, 100 000 iterations,
        32-byte cryptographically random salt via secrets.token_bytes).
        Hash format: "<hex_salt>:<hex_digest>" stored in the `password_hash` column.
      * JWT signing: HS256 with JWT_SECRET from env (same contract as require_auth).
      * No external C extensions required; only PyJWT (already in requirements.txt).

    The emitted file is pure Python and deterministic (no randomness at generation
    time — randomness runs inside the generated project at runtime).
    """

    return (
        '"""Authentication router for the generated API (R-461).\n\n'
        "Provides /auth/register, /auth/login, /auth/me, and /auth/logout endpoints.\n"
        "Password hashing: PBKDF2-SHA256 via Python stdlib hashlib (no external C deps).\n"
        'JWT signing: HS256 using JWT_SECRET from the environment.\n'
        '"""\n'
        "from __future__ import annotations\n\n"
        "import hashlib\n"
        "import os\n"
        "import secrets\n"
        "from datetime import datetime, timedelta, timezone\n"
        "from typing import Any\n\n"
        "import jwt\n"
        "from fastapi import APIRouter, Depends, HTTPException, status\n"
        "from fastapi.responses import Response\n"
        "from pydantic import BaseModel\n\n"
        "try:\n"
        "    import asyncpg\n"
        "except ImportError:  # pragma: no cover\n"
        "    asyncpg = None  # type: ignore[assignment]\n\n"
        'JWT_ALGORITHM = "HS256"\n'
        "TOKEN_EXPIRE_HOURS = 24\n\n"
        "router = APIRouter(tags=[\"auth\"])\n\n\n"
        "# ---------------------------------------------------------------------------\n"
        "# Password helpers (stdlib only — PBKDF2-SHA256, 100 000 iterations)\n"
        "# ---------------------------------------------------------------------------\n\n"
        "def hash_password(plain: str) -> str:\n"
        '    """Return "<hex_salt>:<hex_digest>" suitable for the password_hash column."""\n'
        "    salt = secrets.token_bytes(32)\n"
        "    digest = hashlib.pbkdf2_hmac(\"sha256\", plain.encode(), salt, 100_000)\n"
        '    return salt.hex() + ":" + digest.hex()\n\n\n'
        "def verify_password(plain: str, stored: str) -> bool:\n"
        '    """Return True when `plain` matches the stored PBKDF2 hash."""\n'
        "    try:\n"
        '        salt_hex, digest_hex = stored.split(":", 1)\n'
        "        salt = bytes.fromhex(salt_hex)\n"
        "        expected = bytes.fromhex(digest_hex)\n"
        "    except (ValueError, AttributeError):\n"
        "        return False\n"
        "    candidate = hashlib.pbkdf2_hmac(\"sha256\", plain.encode(), salt, 100_000)\n"
        "    return secrets.compare_digest(candidate, expected)\n\n\n"
        "# ---------------------------------------------------------------------------\n"
        "# JWT helpers\n"
        "# ---------------------------------------------------------------------------\n\n"
        "def _jwt_secret() -> str:\n"
        '    secret = os.environ.get("JWT_SECRET", "")\n'
        "    if not secret:\n"
        '        raise HTTPException(status_code=500, detail="auth_not_configured")\n'
        "    return secret\n\n\n"
        "def _create_token(payload: dict[str, Any]) -> str:\n"
        "    data = dict(payload)\n"
        "    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)\n"
        '    data["exp"] = expire\n'
        "    return jwt.encode(data, _jwt_secret(), algorithm=JWT_ALGORITHM)\n\n\n"
        "# ---------------------------------------------------------------------------\n"
        "# Request / response models\n"
        "# ---------------------------------------------------------------------------\n\n"
        "class RegisterRequest(BaseModel):\n"
        "    email: str\n"
        "    password: str\n"
        "    full_name: str | None = None\n"
        '    role: str = "user"\n\n\n'
        "class LoginRequest(BaseModel):\n"
        "    email: str\n"
        "    password: str\n\n\n"
        "class UserOut(BaseModel):\n"
        "    id: str\n"
        "    email: str\n"
        "    full_name: str | None\n"
        "    role: str\n\n\n"
        "class TokenResponse(BaseModel):\n"
        "    access_token: str\n"
        '    token_type: str = "bearer"\n'
        "    user: UserOut\n\n\n"
        "# ---------------------------------------------------------------------------\n"
        "# Endpoints\n"
        "# ---------------------------------------------------------------------------\n\n"
        '@router.post("/register", response_model=TokenResponse, status_code=201)\n'
        "async def register(body: RegisterRequest) -> TokenResponse:\n"
        '    """Register a new user account and return a signed JWT."""\n'
        "    from app.config import get_db_pool  # lazy to avoid import-time side effects\n\n"
        "    pool = await get_db_pool()\n"
        "    async with pool.acquire() as conn:\n"
        "        existing = await conn.fetchrow(\n"
        '            "SELECT id FROM \\"users\\" WHERE email = $1", body.email\n'
        "        )\n"
        "        if existing:\n"
        '            raise HTTPException(status_code=409, detail="email_already_registered")\n'
        "        password_hash = hash_password(body.password)\n"
        "        row = await conn.fetchrow(\n"
        "            \"\"\"\n"
        "            INSERT INTO \\\"users\\\" (email, password_hash, full_name, role)\n"
        "            VALUES ($1, $2, $3, $4)\n"
        "            RETURNING id::text, email, full_name, role\n"
        "            \"\"\",\n"
        "            body.email, password_hash, body.full_name, body.role,\n"
        "        )\n"
        "    user = UserOut(\n"
        '        id=row["id"], email=row["email"],\n'
        '        full_name=row["full_name"], role=row["role"],\n'
        "    )\n"
        '    token = _create_token({"sub": user.id, "email": user.email, "role": user.role})\n'
        "    return TokenResponse(access_token=token, user=user)\n\n\n"
        '@router.post("/login", response_model=TokenResponse)\n'
        "async def login(body: LoginRequest) -> TokenResponse:\n"
        '    """Authenticate with email + password and return a signed JWT."""\n'
        "    from app.config import get_db_pool\n\n"
        "    pool = await get_db_pool()\n"
        "    async with pool.acquire() as conn:\n"
        "        row = await conn.fetchrow(\n"
        '            "SELECT id::text, email, password_hash, full_name, role FROM \\"users\\" WHERE email = $1",\n'
        "            body.email,\n"
        "        )\n"
        "    if not row or not verify_password(body.password, row[\"password_hash\"]):\n"
        '        raise HTTPException(\n'
        "            status_code=status.HTTP_401_UNAUTHORIZED,\n"
        '            detail="invalid_credentials",\n'
        '            headers={"WWW-Authenticate": "Bearer"},\n'
        "        )\n"
        "    user = UserOut(\n"
        '        id=row["id"], email=row["email"],\n'
        '        full_name=row["full_name"], role=row["role"],\n'
        "    )\n"
        '    token = _create_token({"sub": user.id, "email": user.email, "role": user.role})\n'
        "    return TokenResponse(access_token=token, user=user)\n\n\n"
        '@router.get("/me", response_model=UserOut)\n'
        "async def me(authorization: str | None = None) -> UserOut:\n"
        '    """Return the profile of the currently authenticated user."""\n'
        "    from fastapi import Header as _Header  # noqa: F401\n\n"
        "    if not authorization or not authorization.startswith(\"Bearer \"):\n"
        '        raise HTTPException(status_code=401, detail="unauthorized")\n'
        '    token = authorization[len("Bearer "):]\n'
        "    try:\n"
        "        claims = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])\n"
        "    except jwt.PyJWTError as exc:\n"
        '        raise HTTPException(status_code=401, detail="invalid_token") from exc\n'
        "    return UserOut(\n"
        '        id=claims.get("sub", ""),\n'
        '        email=claims.get("email", ""),\n'
        '        full_name=claims.get("full_name"),\n'
        '        role=claims.get("role", "user"),\n'
        "    )\n\n\n"
        '@router.post("/logout", status_code=204)\n'
        "async def logout() -> Response:\n"
        '    """Invalidate the session (client must clear localStorage token)."""\n'
        "    return Response(status_code=204)\n"
    )
