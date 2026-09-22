import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

export interface AccessClaims {
  sub: string;
  role: "rider" | "driver" | "admin";
  name: string;
  iat: number;
  exp: number;
}

const b64url = (input: Buffer | string) => Buffer.from(input).toString("base64url");

/** HS256 JWT with node:crypto only. */
export function signJwt(claims: Omit<AccessClaims, "iat" | "exp">, secret: string, ttlSeconds: number, now = Date.now()): string {
  const iat = Math.floor(now / 1000);
  const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = b64url(JSON.stringify({ ...claims, iat, exp: iat + ttlSeconds }));
  const signature = createHmac("sha256", secret).update(`${header}.${payload}`).digest("base64url");
  return `${header}.${payload}.${signature}`;
}

export function verifyJwt(token: string, secret: string, now = Date.now()): AccessClaims | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [header, payload, signature] = parts;
  const expected = createHmac("sha256", secret).update(`${header}.${payload}`).digest();
  const given = Buffer.from(signature, "base64url");
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) return null;
  try {
    const head = JSON.parse(Buffer.from(header, "base64url").toString("utf8"));
    if (head.alg !== "HS256") return null;
    const claims = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as AccessClaims;
    if (typeof claims.exp !== "number" || claims.exp * 1000 <= now) return null;
    if (!["rider", "driver", "admin"].includes(claims.role) || typeof claims.sub !== "string") return null;
    return claims;
  } catch {
    return null;
  }
}

/** Opaque refresh token; only its SHA-256 is stored. */
export function newRefreshToken(): { token: string; hash: string } {
  const token = randomBytes(32).toString("base64url");
  return { token, hash: hashToken(token) };
}

export function hashToken(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}
