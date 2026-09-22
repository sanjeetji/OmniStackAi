import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";

const KEY_LENGTH = 32;
const COST = 16384;

/** "scrypt$<N>$<salt-hex>$<hash-hex>" */
export function hashPassword(password: string, salt = randomBytes(16)): string {
  const hash = scryptSync(password, salt, KEY_LENGTH, { N: COST });
  return `scrypt$${COST}$${salt.toString("hex")}$${hash.toString("hex")}`;
}

export function verifyPassword(password: string, stored: string | null): boolean {
  if (!stored) return false;
  const [scheme, cost, saltHex, hashHex] = stored.split("$");
  if (scheme !== "scrypt" || !saltHex || !hashHex) return false;
  const expected = Buffer.from(hashHex, "hex");
  const actual = scryptSync(password, Buffer.from(saltHex, "hex"), expected.length, { N: Number(cost) });
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

export function passwordProblem(password: unknown): string | null {
  if (typeof password !== "string" || password.length < 8) return "Use at least 8 characters.";
  if (password.length > 128) return "Use at most 128 characters.";
  if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) return "Use letters and numbers.";
  return null;
}
