/** Authentication and role authorization middleware for Hono routes. */

import type { MiddlewareHandler } from "hono";
import { verifyToken, type TokenPayload } from "./tokens.ts";
import { UnauthorizedError, ForbiddenError } from "../lib/errors.ts";
import { query } from "../db.ts";

export type AuthContext = {
  user: TokenPayload;
  shopId?: string;
};

declare module "hono" {
  interface ContextVariableMap {
    user: TokenPayload;
    shopId?: string;
  }
}

export function authenticate(options: { optional?: boolean } = {}): MiddlewareHandler {
  return async (c, next) => {
    const authHeader = c.req.header("Authorization") || c.req.header("authorization");
    let token: string | undefined;

    if (authHeader && authHeader.startsWith("Bearer ")) {
      token = authHeader.slice(7).trim();
    } else {
      // Also support query param for EventSource / SSE connections
      token = c.req.query("token");
    }

    if (!token) {
      if (options.optional) {
        return next();
      }
      throw new UnauthorizedError("Authentication token is required");
    }

    try {
      const payload = verifyToken(token);
      c.set("user", payload);

      // If user is a vendor, resolve and attach shopId if not already in payload
      if (payload.role === "vendor") {
        let shopId = payload.shopId;
        if (!shopId) {
          const res = await query<{ id: string }>(
            "SELECT id FROM shops WHERE user_id = $1 LIMIT 1",
            [payload.userId]
          );
          if (res.rows.length > 0) {
            shopId = res.rows[0].id;
          }
        }
        if (shopId) {
          c.set("shopId", shopId);
        }
      }

      await next();
    } catch (err) {
      if (options.optional) {
        return next();
      }
      throw err;
    }
  };
}

export function requireRole(...roles: Array<"shopper" | "vendor" | "admin">): MiddlewareHandler {
  return async (c, next) => {
    const user = c.get("user");
    if (!user) {
      throw new UnauthorizedError("Authentication required");
    }
    if (!roles.includes(user.role)) {
      throw new ForbiddenError(
        `Access denied: requires one of [${roles.join(", ")}], but user has role '${user.role}'`
      );
    }
    await next();
  };
}
