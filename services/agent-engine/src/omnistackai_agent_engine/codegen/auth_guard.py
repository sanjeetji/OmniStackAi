"""Generate the authentication guard for a backend from the IR endpoint auth flags and roles.

The guard performs real token verification (R-242): it decodes and verifies a JWT (HS256) using a
JWT_SECRET read from the environment — 401 on a missing/invalid/expired token, 500 when the secret is
not configured. It NEVER fabricates a secret or a default: the secret only ever comes from the env. The
IR roles are surfaced as a constant so per-endpoint authorization can build on them (enforcement needs
an IR field — a follow-up). Pure/deterministic; nothing here signs or verifies a token at generation
time, and the JWT dependency lives only in the generated project.
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
        '    if not authorization or not authorization.startswith("Bearer "):\n'
        '        raise HTTPException(status_code=401, detail="unauthorized")\n'
        '    token = authorization[len("Bearer "):]\n'
        "    try:\n"
        "        return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])\n"
        "    except jwt.PyJWTError as error:\n"
        '        raise HTTPException(status_code=401, detail="invalid_token") from error\n'
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
        "// RequireAuth verifies a JWT (HS256) using JWT_SECRET from the environment: 401 on a missing\n"
        "// or invalid token, 500 when JWT_SECRET is unset. The secret is never hard-coded.\n"
        "func RequireAuth(next http.HandlerFunc) http.HandlerFunc {\n"
        "\treturn func(w http.ResponseWriter, r *http.Request) {\n"
        '\t\tauth := r.Header.Get("Authorization")\n'
        '\t\tif !strings.HasPrefix(auth, "Bearer ") {\n'
        '\t\t\thttp.Error(w, "unauthorized", http.StatusUnauthorized)\n'
        "\t\t\treturn\n"
        "\t\t}\n"
        '\t\tsecret := os.Getenv("JWT_SECRET")\n'
        '\t\tif secret == "" {\n'
        '\t\t\thttp.Error(w, "auth_not_configured", http.StatusInternalServerError)\n'
        "\t\t\treturn\n"
        "\t\t}\n"
        '\t\ttokenStr := strings.TrimPrefix(auth, "Bearer ")\n'
        "\t\t_, err := jwt.Parse(tokenStr, func(t *jwt.Token) (any, error) {\n"
        "\t\t\tif _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {\n"
        "\t\t\t\treturn nil, jwt.ErrSignatureInvalid\n"
        "\t\t\t}\n"
        "\t\t\treturn []byte(secret), nil\n"
        "\t\t})\n"
        "\t\tif err != nil {\n"
        '\t\t\thttp.Error(w, "invalid_token", http.StatusUnauthorized)\n'
        "\t\t\treturn\n"
        "\t\t}\n"
        "\t\tnext(w, r)\n"
        "\t}\n"
        "}\n"
    )
