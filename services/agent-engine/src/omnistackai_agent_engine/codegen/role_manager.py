"""PC-011 (from R-590): an app's admin can give people their roles.

Everyone who signs up to a generated app gets the role ``user`` — nobody may sign themselves up as
an admin — but the plan's own roles (``author``, ``courier``, ``doctor`` …) guard what people can
do, so without a way to assign them every role-guarded action needed someone with database access.
Every backend now serves the same two account endpoints, and the admin console gets a page for them:

* ``GET  /auth/users``            — every account with its role, and the roles that can be given;
* ``PUT  /auth/users/{id}/role``  — ``{"role": "..."}``; one of the plan's roles, ``admin`` or ``user``.

Only the ``admin`` role may use them. The last admin cannot be demoted (409 ``last_admin``), so an
app cannot lock itself out. A new role applies from the person's next sign-in, when their token is
issued with it.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR

USERS_PATH = "/auth/users"
ROLE_PATH = "/auth/users/{id}/role"


def assignable_roles(ir: ApplicationIR) -> list[str]:
    """The plan's roles, then ``admin`` and ``user``, each once."""
    out: list[str] = []
    for role in [r.id for r in ir.roles] + ["admin", "user"]:
        if role not in out:
            out.append(role)
    return out


# ── Python (FastAPI): appended to app/routers/auth.py, mounted at /auth ─────────────────────────

def python_role_manager(ir: ApplicationIR) -> str:
    roles = ", ".join(repr(r) for r in assignable_roles(ir))
    return f'''

# ── PC-011: roles, given by the app's admin ─────────────────────────────────────────────────────

ASSIGNABLE_ROLES = ({roles},)


class RoleChange(BaseModel):
    role: str


async def _require_admin(authorization: str | None) -> dict[str, Any]:
    from app.auth import require_auth

    claims = await require_auth(authorization)
    if "admin" not in (claims.get("roles") or []):
        raise HTTPException(status_code=403, detail="forbidden")
    return claims


@router.get("/users")
async def list_users(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Every account and its role, for the admin console's Users page."""
    from app.db import connect

    await _require_admin(authorization)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(
            'SELECT id::text AS id, email, full_name, role, created_at FROM "users" ORDER BY created_at DESC LIMIT 500'
        )
        rows = await cur.fetchall()
    return {{"users": [dict(row) for row in rows], "roles": list(ASSIGNABLE_ROLES)}}


@router.put("/users/{{user_id}}/role", response_model=UserOut)
async def set_user_role(user_id: str, body: RoleChange, authorization: str | None = Header(default=None)) -> UserOut:
    """Give one account a role. The last admin cannot be demoted."""
    from app.db import connect

    await _require_admin(authorization)
    if body.role not in ASSIGNABLE_ROLES:
        raise HTTPException(status_code=422, detail="unknown_role")
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute('SELECT role FROM "users" WHERE id::text = %s', (user_id,))
        current = await cur.fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="not_found")
        if current["role"] == "admin" and body.role != "admin":
            await cur.execute('SELECT count(*) AS n FROM "users" WHERE role = %s AND id::text <> %s', ("admin", user_id))
            if (await cur.fetchone())["n"] == 0:
                raise HTTPException(status_code=409, detail="last_admin")
        await cur.execute(
            'UPDATE "users" SET role = %s WHERE id::text = %s RETURNING id::text AS id, email, full_name, role',
            (body.role, user_id),
        )
        return _user(await cur.fetchone())
'''


# ── Go (net/http): internal/handlers/auth_roles.go ──────────────────────────────────────────────

GO_ROLE_MANAGER = '''package handlers

// PC-011: roles, given by the app's admin. GET /auth/users and PUT /auth/users/{id}/role.

import (
	"database/sql"
	"errors"
	"net/http"
	"time"
)

// assignableRoles are the plan's roles, then admin and user, each once.
func assignableRoles() []string {
	seen := map[string]bool{}
	out := []string{}
	for _, role := range append(append([]string{}, Roles...), "admin", "user") {
		if !seen[role] {
			seen[role] = true
			out = append(out, role)
		}
	}
	return out
}

func requireAdmin(w http.ResponseWriter, r *http.Request) bool {
	claims, status, code := verifyToken(r)
	if status != http.StatusOK {
		authError(w, status, code)
		return false
	}
	if !hasAnyRole(claims, []string{"admin"}) {
		authError(w, http.StatusForbidden, "forbidden")
		return false
	}
	return true
}

type accountRow struct {
	ID        string    `json:"id"`
	Email     string    `json:"email"`
	FullName  string    `json:"full_name"`
	Role      string    `json:"role"`
	CreatedAt time.Time `json:"created_at"`
}

// AuthListUsers answers every account and its role, for the admin console.
func (h *Handlers) AuthListUsers(w http.ResponseWriter, r *http.Request) {
	if !requireAdmin(w, r) {
		return
	}
	rows, err := h.DB.QueryContext(r.Context(),
		`SELECT id::text, email, COALESCE(full_name, ''), role, created_at FROM "users" ORDER BY created_at DESC LIMIT 500`)
	if err != nil {
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	defer rows.Close()
	users := []accountRow{}
	for rows.Next() {
		var u accountRow
		if rows.Scan(&u.ID, &u.Email, &u.FullName, &u.Role, &u.CreatedAt) == nil {
			users = append(users, u)
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{"users": users, "roles": assignableRoles()})
}

// AuthSetUserRole gives one account a role. The last admin cannot be demoted.
func (h *Handlers) AuthSetUserRole(w http.ResponseWriter, r *http.Request) {
	if !requireAdmin(w, r) {
		return
	}
	var body struct {
		Role string `json:"role"`
	}
	if !decodeAuthBody(w, r, &body) {
		return
	}
	valid := false
	for _, role := range assignableRoles() {
		valid = valid || role == body.Role
	}
	if !valid {
		authError(w, http.StatusUnprocessableEntity, "unknown_role")
		return
	}
	id := r.PathValue("id")
	var current string
	err := h.DB.QueryRowContext(r.Context(), `SELECT role FROM "users" WHERE id::text = $1`, id).Scan(&current)
	if errors.Is(err, sql.ErrNoRows) {
		authError(w, http.StatusNotFound, "not_found")
		return
	}
	if err != nil {
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	if current == "admin" && body.Role != "admin" {
		var others int
		_ = h.DB.QueryRowContext(r.Context(), `SELECT count(*) FROM "users" WHERE role = 'admin' AND id::text <> $1`, id).Scan(&others)
		if others == 0 {
			authError(w, http.StatusConflict, "last_admin")
			return
		}
	}
	var u accountRow
	err = h.DB.QueryRowContext(r.Context(),
		`UPDATE "users" SET role = $2 WHERE id::text = $1 RETURNING id::text, email, COALESCE(full_name, ''), role, created_at`,
		id, body.Role).Scan(&u.ID, &u.Email, &u.FullName, &u.Role, &u.CreatedAt)
	if err != nil {
		authError(w, http.StatusInternalServerError, "internal_error")
		return
	}
	writeJSON(w, http.StatusOK, u)
}
'''


# ── Node: appended to src/auth/core.ts; routes appended to both routers ─────────────────────────

def node_role_manager_core(ir: ApplicationIR) -> str:
    roles = ", ".join(f"'{r}'" for r in assignable_roles(ir))
    return f'''

// ── PC-011: roles, given by the app's admin ────────────────────────────────────────────────────

export const ASSIGNABLE_ROLES: readonly string[] = [{roles}];

function adminClaims(authorization: string | undefined): AuthClaims | Result {{
  if (!authorization || !authorization.startsWith('Bearer ')) return fail(401, 'unauthorized');
  const claims = verifyToken(authorization.slice(7).trim(), config.jwtSecret);
  if (!claims) return fail(401, 'invalid_token');
  const roles = Array.isArray(claims.roles) ? claims.roles : [claims.role];
  if (!roles.includes('admin')) return fail(403, 'forbidden');
  return claims;
}}

// PC-103, found live: `'status' in claims` does not narrow - AuthClaims takes any key - so the
// Node API failed `tsc` (npm run build) wherever it had accounts. An explicit guard does.
function isFailure(value: AuthClaims | Result): value is Result {{
  return typeof (value as Result).status === 'number';
}}

export async function listUsers(authorization: string | undefined): Promise<Result> {{
  const claims = adminClaims(authorization);
  if (isFailure(claims)) return claims;
  const result = await pool.query(
    'SELECT id::text AS id, email, full_name, role, created_at FROM "users" ORDER BY created_at DESC LIMIT 500',
  );
  return {{ status: 200, body: {{ users: result.rows, roles: ASSIGNABLE_ROLES }} }};
}}

export async function setUserRole(authorization: string | undefined, id: string, body: any): Promise<Result> {{
  const claims = adminClaims(authorization);
  if (isFailure(claims)) return claims;
  const role = String(body?.role ?? '');
  if (!ASSIGNABLE_ROLES.includes(role)) return fail(422, 'unknown_role');
  const current = await pool.query('SELECT role FROM "users" WHERE id::text = $1', [id]);
  if (current.rows.length === 0) return fail(404, 'not_found');
  if (current.rows[0].role === 'admin' && role !== 'admin') {{
    const others = await pool.query('SELECT count(*)::int AS n FROM "users" WHERE role = $1 AND id::text <> $2', ['admin', id]);
    if (others.rows[0].n === 0) return fail(409, 'last_admin');
  }}
  const updated = await pool.query(
    'UPDATE "users" SET role = $2 WHERE id::text = $1 RETURNING id::text AS id, email, full_name, role',
    [id, role],
  );
  return {{ status: 200, body: updated.rows[0] }};
}}
'''


NODE_ROLE_ROUTES_EXPRESS = '''
// PC-011: roles, given by the app's admin.
router.get('/users', handle((req) => auth.listUsers(req.headers.authorization)));
router.put('/users/:id/role', handle((req) => auth.setUserRole(req.headers.authorization, String(req.params.id), req.body)));
'''

NODE_ROLE_ROUTES_HONO = '''
// PC-011: roles, given by the app's admin.
router.get('/users', async (c) => handle(c, () => auth.listUsers(c.req.header('Authorization'))));
router.put('/users/:id/role', async (c) => handle(c, async () => auth.setUserRole(c.req.header('Authorization'), c.req.param('id') ?? '', await body(c))));
'''


# ── the admin console's Users page ──────────────────────────────────────────────────────────────

ADMIN_USERS_PAGE = '''"use client";

// PC-011: give people their roles. Everyone who signs up starts as "user"; this is where an admin
// makes someone an author, a courier, a doctor … A new role applies from their next sign-in.
import { useEffect, useState } from "react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = typeof localStorage !== "undefined" ? localStorage.getItem("auth_token") : null;
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { detail?: string }).detail || `status ${res.status}`);
  return data as T;
}

type Account = { id: string; email: string; full_name: string | null; role: string };

export default function UsersPage() {
  const [users, setUsers] = useState<Account[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    call<{ users: Account[]; roles: string[] }>("GET", "/auth/users")
      .then((data) => {
        if (cancelled) return;
        setUsers(data.users);
        setRoles(data.roles);
      })
      .catch(() => {
        if (!cancelled) setMessage("Only an admin can manage roles. Sign in with an admin account.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const change = async (account: Account, role: string) => {
    setMessage(null);
    try {
      const updated = await call<Account>("PUT", `/auth/users/${encodeURIComponent(account.id)}/role`, { role });
      setUsers((list) => list.map((u) => (u.id === updated.id ? { ...u, role: updated.role } : u)));
      setMessage(`${account.email} is now ${role}. It applies from their next sign-in.`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "";
      setMessage(detail.includes("last_admin") ? "The app must keep at least one admin." : "The role could not be changed.");
    }
  };

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-semibold tracking-tight">Users and roles</h1>
      <p className="mt-1 text-sm text-muted-foreground">Everyone who signs up starts as a user. Give people the roles they need here.</p>
      {message && <p role="status" className="mt-4 text-sm">{message}</p>}
      {loading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading…</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
              <tr><th className="px-4 py-2 font-medium">Account</th><th className="px-4 py-2 font-medium">Role</th></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t">
                  <td className="px-4 py-2">
                    <div className="font-medium">{u.email}</div>
                    {u.full_name && <div className="text-xs text-muted-foreground">{u.full_name}</div>}
                  </td>
                  <td className="px-4 py-2">
                    <select aria-label={`Role for ${u.email}`} value={u.role} onChange={(e) => change(u, e.target.value)}
                      className="rounded-md border bg-background px-2 py-1">
                      {(roles.includes(u.role) ? roles : [u.role, ...roles]).map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
'''
