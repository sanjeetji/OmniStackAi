import type { Context, MiddlewareHandler } from "hono";
import { config } from "../config.ts";
import { forbidden, unauthorized } from "../lib/errors.ts";
import { type AccessClaims, verifyJwt } from "./tokens.ts";

export type Role = AccessClaims["role"];
export type AppEnv = { Variables: { user: AccessClaims } };

export function bearer(c: Context): string | null {
  const header = c.req.header("authorization") ?? "";
  return header.startsWith("Bearer ") ? header.slice(7) : null;
}

/** Require a valid access token, and optionally one of `roles`. */
export function requireAuth(...roles: Role[]): MiddlewareHandler<AppEnv> {
  return async (c, next) => {
    const token = bearer(c);
    const claims = token ? verifyJwt(token, config.jwtSecret) : null;
    if (!claims) throw unauthorized();
    if (roles.length > 0 && !roles.includes(claims.role)) throw forbidden();
    c.set("user", claims);
    await next();
  };
}
