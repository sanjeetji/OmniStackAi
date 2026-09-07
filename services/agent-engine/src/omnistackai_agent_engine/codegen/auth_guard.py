"""Generate the authentication guard for a backend from the IR endpoint auth flags and roles.

The guard is honest: it enforces that a bearer credential is *present* (HTTP 401 otherwise) and marks
real token verification (signature, expiry, roles) as a TODO — it never fabricates a secret or claims
verification it does not do. The IR roles are surfaced as a constant so per-endpoint authorization can
build on them later. Pure/deterministic; nothing here runs or verifies a token at generation time.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR


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
        "require_auth enforces that a bearer credential is present; verifying the token (signature,\n"
        "expiry, and the ROLES below) is a deliberate TODO — wire it to your identity provider.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "from fastapi import Header, HTTPException\n\n"
        f"ROLES = {roles_literal}\n\n\n"
        "async def require_auth(authorization: str | None = Header(default=None)) -> str:\n"
        "    if not authorization or not authorization.startswith(\"Bearer \"):\n"
        '        raise HTTPException(status_code=401, detail="unauthorized")\n'
        '    token = authorization[len("Bearer "):]\n'
        "    # TODO: verify the token (signature, expiry) and authorize against ROLES.\n"
        "    return token\n"
    )


def go_auth_file(ir: ApplicationIR) -> str:
    roles = ", ".join(f'"{name}"' for name in _role_names(ir))
    return (
        "package handlers\n\n"
        "import (\n"
        '\t"net/http"\n'
        '\t"strings"\n'
        ")\n\n"
        "// Roles from the Application IR. Per-endpoint role enforcement is a TODO; RequireAuth below\n"
        "// only checks that a bearer credential is present.\n"
        f"var Roles = []string{{{roles}}}\n\n"
        "// RequireAuth rejects a request without an Authorization: Bearer <token> header (401).\n"
        "// TODO: verify the token (signature, expiry) and authorize against Roles.\n"
        "func RequireAuth(next http.HandlerFunc) http.HandlerFunc {\n"
        "\treturn func(w http.ResponseWriter, r *http.Request) {\n"
        '\t\tauth := r.Header.Get("Authorization")\n'
        '\t\tif !strings.HasPrefix(auth, "Bearer ") {\n'
        '\t\t\thttp.Error(w, "unauthorized", http.StatusUnauthorized)\n'
        "\t\t\treturn\n"
        "\t\t}\n"
        "\t\tnext(w, r)\n"
        "\t}\n"
        "}\n"
    )
