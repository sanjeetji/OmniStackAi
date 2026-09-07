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
        '\tauth := r.Header.Get("Authorization")\n'
        '\tif !strings.HasPrefix(auth, "Bearer ") {\n'
        '\t\treturn nil, http.StatusUnauthorized, "unauthorized"\n'
        "\t}\n"
        '\tsecret := os.Getenv("JWT_SECRET")\n'
        '\tif secret == "" {\n'
        '\t\treturn nil, http.StatusInternalServerError, "auth_not_configured"\n'
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
