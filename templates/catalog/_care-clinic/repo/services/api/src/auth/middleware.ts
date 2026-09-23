/** Authentication and role authorization middleware for CareClinic API. */

import type { Context, Next } from "hono";
import { verifyToken, type TokenPayload } from "./tokens.ts";
import { ForbiddenError, UnauthorizedError } from "../lib/errors.ts";

export type AuthContext = Context<{
  Variables: {
    user: TokenPayload;
  };
}>;

export async function requireAuth(c: Context, next: Next) {
  const authHeader = c.req.header("Authorization");
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    throw new UnauthorizedError("Missing or malformed Authorization header");
  }

  const token = authHeader.substring(7);
  const payload = verifyToken(token);
  c.set("user", payload);
  await next();
}

export function requireRole(...allowedRoles: Array<"patient" | "doctor" | "receptionist" | "admin">) {
  return async (c: Context, next: Next) => {
    const user = c.get("user") as TokenPayload | undefined;
    if (!user) {
      throw new UnauthorizedError("Authentication required");
    }

    if (!allowedRoles.includes(user.role)) {
      throw new ForbiddenError(
        `Access denied. Allowed roles: ${allowedRoles.join(", ")}. Provided: ${user.role}`
      );
    }

    await next();
  };
}

export async function optionalAuth(c: Context, next: Next) {
  const authHeader = c.req.header("Authorization");
  if (authHeader && authHeader.startsWith("Bearer ")) {
    try {
      const token = authHeader.substring(7);
      const payload = verifyToken(token);
      c.set("user", payload);
    } catch {
      // Ignore token errors for optional auth
    }
  }
  await next();
}
