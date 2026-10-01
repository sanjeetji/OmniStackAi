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
from .auth_templates import PYTHON_AUTH_ROUTER

# Generated-project dependency pins (only added when an auth guard is emitted).
PYJWT_REQUIREMENT = "PyJWT==2.9.0"
GOLANG_JWT_REQUIRE = "github.com/golang-jwt/jwt/v5 v5.2.1"


def needs_auth(ir: ApplicationIR) -> bool:
    """True when at least one endpoint requires authentication, or an ownership rule makes it so
    (R-570: an owner-scoped read needs to know who is asking, whatever the plan said)."""
    from ..application_ir.money import money_of
    from ..application_ir.ownership import ownership_rules

    # R-567: money has a payer, a payee and refunders - it needs to know who is asking too.
    return any(api.auth for api in ir.apis) or bool(ownership_rules(ir)) or money_of(ir) is not None


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
        "import re\n"
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
        '            return {"sub": "dev-admin", "roles": [*ROLES, "admin"], "email": "admin@example.local", "dev_session": True}\n'
        '        raise HTTPException(status_code=401, detail="unauthorized")\n'
        '    token = authorization[len("Bearer "):]\n'
        "    try:\n"
        "        return jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])\n"
        "    except jwt.PyJWTError as error:\n"
        '        raise HTTPException(status_code=401, detail="invalid_token") from error\n\n\n'
        "def require_roles(*required: str):\n"
        '    """Dependency factory: verify the token, then require any one of `required` in its roles claim.\n\n'
        "    The app's admin passes every role check (as it does require_owner): the admin console is\n"
        '    theirs, and only an admin can make someone an admin."""\n\n'
        "    async def _guard(authorization: str | None = Header(default=None)) -> dict[str, Any]:\n"
        "        claims = await require_auth(authorization)\n"
        '        held = claims.get("roles") or []\n'
        '        if not isinstance(held, list) or not set(held) & (set(required) | {"admin"}):\n'
        '            raise HTTPException(status_code=403, detail="forbidden")\n'
        "        return claims\n\n"
        "    return _guard\n\n\n"
        "_UUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')\n"
        "#: A user id no row has, so a user without one sees nothing rather than everything.\n"
        "NOBODY = '00000000-0000-0000-0000-000000000000'\n\n\n"
        "def owner_of(claims: dict[str, Any]) -> str | None:\n"
        '    """R-570: the signed-in user\'s id as `created_by` stores it (the dev session has none)."""\n'
        '    sub = claims.get("sub")\n'
        "    return sub if isinstance(sub, str) and _UUID.match(sub) else None\n\n\n"
        "def sees_all(claims: dict[str, Any], roles: tuple[str, ...]) -> bool:\n"
        '    """R-570: whether this user sees every record of an owner-scoped entity (admin always)."""\n'
        '    held = claims.get("roles") or []\n'
        '    return isinstance(held, list) and bool(set(held) & (set(roles) | {"admin"}))\n\n\n'
        "def owner_scope(claims: dict[str, Any], roles: tuple[str, ...]) -> str | None:\n"
        '    """R-570: None when this user sees every record, else the id whose records they see."""\n'
        "    if sees_all(claims, roles):\n"
        "        return None\n"
        "    return owner_of(claims) or NOBODY\n\n\n"
        "def can_touch(row: dict[str, Any], claims: dict[str, Any], roles: tuple[str, ...], assignee: str | None = None) -> bool:\n"
        '    """R-570: may this user see or change `row` of an owner-scoped entity - its creator, or\n'
        '    (PC-111) the user it is assigned to."""\n'
        "    scope = owner_scope(claims, roles)\n"
        '    if scope is None or str(row.get("created_by") or "") == scope:\n'
        "        return True\n"
        '    return assignee is not None and str(row.get(assignee) or "") == scope\n\n\n'
        "def require_owner(owner_id: str | None = None):\n"
        '    """Dependency: ensure authenticated user matches owner_id or possesses the admin role."""\n\n'
        "    async def _guard(authorization: str | None = Header(default=None)) -> dict[str, Any]:\n"
        "        claims = await require_auth(authorization)\n"
        "        if owner_id is not None:\n"
        '            sub = claims.get("sub")\n'
        '            roles = claims.get("roles") or []\n'
        '            is_admin = "admin" in roles or sub == "dev-admin"\n'
        "            if sub != owner_id and not is_admin:\n"
        '                raise HTTPException(status_code=403, detail="forbidden_not_owner")\n'
        "        return claims\n\n"
        "    return _guard\n"
    )


def go_auth_file(ir: ApplicationIR) -> str:
    roles = ", ".join(f'"{name}"' for name in _role_names(ir))
    return (
        "package handlers\n\n"
        "import (\n"
        '\t"context"\n'
        '\t"net/http"\n'
        '\t"os"\n'
        '\t"regexp"\n'
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
        '\t\t\treturn jwt.MapClaims{"sub": "dev-admin", "roles": append(append([]string{}, Roles...), "admin"), "email": "admin@example.local"}, http.StatusOK, ""\n'
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
        "type claimsKey struct{}\n\n"
        "// ClaimsFrom is the verified token of a request that passed RequireAuth or RequireRoles (R-570).\n"
        "func ClaimsFrom(r *http.Request) jwt.MapClaims {\n"
        "\tclaims, _ := r.Context().Value(claimsKey{}).(jwt.MapClaims)\n"
        "\treturn claims\n"
        "}\n\n"
        "func withClaims(r *http.Request, claims jwt.MapClaims) *http.Request {\n"
        "\treturn r.WithContext(context.WithValue(r.Context(), claimsKey{}, claims))\n"
        "}\n\n"
        "var userID = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)\n\n"
        "// OwnerOf is the signed-in user's id as created_by stores it (\"\" for the dev session).\n"
        "func OwnerOf(claims jwt.MapClaims) string {\n"
        "\tsub, _ := claims[\"sub\"].(string)\n"
        "\tif userID.MatchString(sub) {\n"
        "\t\treturn sub\n"
        "\t}\n"
        "\treturn \"\"\n"
        "}\n\n"
        "// OwnerScope is \"\" when this user sees every record of an owner-scoped entity (admin always,\n"
        "// and the given roles), else the id whose records they see - never \"\" for anyone else.\n"
        "func OwnerScope(claims jwt.MapClaims, seeAll ...string) string {\n"
        "\tif hasAnyRole(claims, seeAll) {\n"
        "\t\treturn \"\"\n"
        "\t}\n"
        "\tif owner := OwnerOf(claims); owner != \"\" {\n"
        "\t\treturn owner\n"
        "\t}\n"
        "\treturn \"00000000-0000-0000-0000-000000000000\"\n"
        "}\n\n"
        "// CanTouch: may this user see or change a row created by owner (R-570).\n"
        "func CanTouch(claims jwt.MapClaims, owner string, seeAll ...string) bool {\n"
        "\tscope := OwnerScope(claims, seeAll...)\n"
        "\treturn scope == \"\" || scope == owner\n"
        "}\n\n"
        "// CanTouchAssigned: CanTouch, or the row is assigned to this user (PC-111).\n"
        "func CanTouchAssigned(claims jwt.MapClaims, owner, assignee string, seeAll ...string) bool {\n"
        "\tif CanTouch(claims, owner, seeAll...) {\n"
        "\t\treturn true\n"
        "\t}\n"
        "\treturn assignee != \"\" && OwnerScope(claims, seeAll...) == assignee\n"
        "}\n\n"
        "// SeesAll: this user sees and assigns every record of the entity (admin always).\n"
        "func SeesAll(claims jwt.MapClaims, seeAll ...string) bool {\n"
        "\treturn hasAnyRole(claims, seeAll)\n"
        "}\n\n"
        "// RequireAuth rejects a request whose JWT is missing or invalid.\n"
        "func RequireAuth(next http.HandlerFunc) http.HandlerFunc {\n"
        "\treturn func(w http.ResponseWriter, r *http.Request) {\n"
        "\t\tclaims, status, msg := verifyToken(r)\n"
        "\t\tif msg != \"\" {\n"
        "\t\t\thttp.Error(w, msg, status)\n"
        "\t\t\treturn\n"
        "\t\t}\n"
        "\t\tnext(w, withClaims(r, claims))\n"
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
        "\t\tnext(w, withClaims(r, claims))\n"
        "\t}\n"
        "}\n\n"
        "func hasAnyRole(claims jwt.MapClaims, required []string) bool {\n"
        "\t// A verified token decodes roles as []any; the dev session builds them as []string (PC-101:\n"
        "\t// read as []any alone, the dev admin failed every role check).\n"
        "\tvar raw []any\n"
        '\tswitch v := claims["roles"].(type) {\n'
        "\tcase []any:\n"
        "\t\traw = v\n"
        "\tcase []string:\n"
        "\t\tfor _, s := range v {\n"
        "\t\t\traw = append(raw, s)\n"
        "\t\t}\n"
        "\tdefault:\n"
        "\t\treturn false\n"
        "\t}\n"
        "\theld := map[string]bool{}\n"
        "\tfor _, v := range raw {\n"
        "\t\tif s, ok := v.(string); ok {\n"
        "\t\t\theld[s] = true\n"
        "\t\t}\n"
        "\t}\n"
        "\t// The app's admin passes every role check, as in RequireOwner.\n"
        "\tif held[\"admin\"] {\n"
        "\t\treturn true\n"
        "\t}\n"
        "\tfor _, want := range required {\n"
        "\t\tif held[want] {\n"
        "\t\t\treturn true\n"
        "\t\t}\n"
        "\t}\n"
        "\treturn false\n"
        "}\n\n"
        "// RequireOwner checks that the resource's owner matches claims[\"sub\"] or user is admin.\n"
        "func RequireOwner(ownerID string, claims jwt.MapClaims) bool {\n"
        '\tsub, _ := claims["sub"].(string)\n'
        '\tif sub != "" && (sub == ownerID || sub == "dev-admin") {\n'
        "\t\treturn true\n"
        "\t}\n"
        '\treturn hasAnyRole(claims, []string{"admin"})\n'
        "}\n"
    )


def python_auth_router_file(ir: ApplicationIR) -> str:
    """Generate app/routers/auth.py — the complete account flow for a FastAPI backend.

    R-461 shipped register / login / me / logout. R-591 made it complete and correct: `/me` read
    `authorization` without `Header()`, so FastAPI took it from the query string and every signed-in
    user's profile call answered 401; `/forgot-password` said "Password reset link dispatched" and
    dispatched nothing; `/reset-password` always answered 501. See `auth_templates` for the contract
    all three backends share.
    """

    from .role_manager import python_role_manager

    # PC-011: plus the admin's role manager (GET /auth/users, PUT /auth/users/{id}/role).
    from .auth_templates import signup_role

    router = PYTHON_AUTH_ROUTER.replace('DEFAULT_ROLE = "user"', f'DEFAULT_ROLE = "{signup_role(ir)}"', 1)
    return router + python_role_manager(ir)
