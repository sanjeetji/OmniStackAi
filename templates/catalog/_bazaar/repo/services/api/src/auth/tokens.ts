/** Zero-dependency HS256 JWT token generation and verification using node:crypto. */

import { createHmac, timingSafeEqual } from "node:crypto";
import { config } from "../config.ts";
import { UnauthorizedError } from "../lib/errors.ts";

export interface TokenPayload {
  userId: string;
  email: string;
  role: "shopper" | "vendor" | "admin";
  shopId?: string;
  iat?: number;
  exp?: number;
}

function base64UrlEncode(str: string): string {
  return Buffer.from(str)
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function base64UrlDecode(str: string): string {
  let base64 = str.replace(/-/g, "+").replace(/_/g, "/");
  while (base64.length % 4) {
    base64 += "=";
  }
  return Buffer.from(base64, "base64").toString("utf8");
}

function sign(content: string, secret: string): string {
  const hmac = createHmac("sha256", secret);
  hmac.update(content);
  return hmac
    .digest("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

export function generateToken(
  payload: Omit<TokenPayload, "iat" | "exp">,
  expiresInSeconds = 7 * 24 * 60 * 60 // 7 days default
): string {
  const header = { alg: "HS256", typ: "JWT" };
  const now = Math.floor(Date.now() / 1000);
  const fullPayload: TokenPayload = {
    ...payload,
    iat: now,
    exp: now + expiresInSeconds,
  };

  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedPayload = base64UrlEncode(JSON.stringify(fullPayload));
  const message = `${encodedHeader}.${encodedPayload}`;
  const signature = sign(message, config.jwtSecret);

  return `${message}.${signature}`;
}

export function verifyToken(token: string): TokenPayload {
  const parts = token.split(".");
  if (parts.length !== 3) {
    throw new UnauthorizedError("Invalid token format");
  }

  const [encodedHeader, encodedPayload, signature] = parts;
  const message = `${encodedHeader}.${encodedPayload}`;
  const expectedSignature = sign(message, config.jwtSecret);

  if (signature !== expectedSignature) {
    throw new UnauthorizedError("Invalid token signature");
  }

  try {
    const payload = JSON.parse(base64UrlDecode(encodedPayload)) as TokenPayload;
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) {
      throw new UnauthorizedError("Token has expired");
    }
    return payload;
  } catch (err: any) {
    if (err instanceof UnauthorizedError) throw err;
    throw new UnauthorizedError("Malformed token payload");
  }
}
