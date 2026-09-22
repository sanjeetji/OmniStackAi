import { badRequest } from "./errors.ts";

/** Small, explicit request validation (no dependency): each helper returns a typed value or throws 400. */
export function str(body: Record<string, unknown>, key: string, opts: { min?: number; max?: number; optional?: boolean } = {}): string {
  const value = body[key];
  if (value === undefined || value === null || value === "") {
    if (opts.optional) return "";
    throw badRequest(`${key} is required.`);
  }
  if (typeof value !== "string") throw badRequest(`${key} must be text.`);
  const trimmed = value.trim();
  if (trimmed.length < (opts.min ?? 1)) throw badRequest(`${key} is too short.`);
  if (trimmed.length > (opts.max ?? 500)) throw badRequest(`${key} is too long.`);
  return trimmed;
}

export function numberIn(body: Record<string, unknown>, key: string, min: number, max: number): number {
  const value = body[key];
  if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max) {
    throw badRequest(`${key} must be a number between ${min} and ${max}.`);
  }
  return value;
}

export function oneOf<T extends string>(body: Record<string, unknown>, key: string, allowed: readonly T[], fallback?: T): T {
  const value = body[key] ?? fallback;
  if (typeof value !== "string" || !(allowed as readonly string[]).includes(value)) {
    throw badRequest(`${key} must be one of: ${allowed.join(", ")}.`);
  }
  return value as T;
}

export function email(body: Record<string, unknown>, key = "email"): string {
  const value = str(body, key, { max: 200 }).toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)) throw badRequest("Enter a valid email address.");
  return value;
}

export function phone(body: Record<string, unknown>, key = "phone"): string {
  const digits = str(body, key, { max: 20 }).replace(/[^\d+]/g, "");
  if (!/^\+?\d{10,13}$/.test(digits)) throw badRequest("Enter a valid phone number.");
  return digits.startsWith("+") ? digits : `+91${digits.slice(-10)}`;
}

export function pageParams(url: URL, maxLimit = 100): { limit: number; offset: number } {
  const limit = Math.min(maxLimit, Math.max(1, Number(url.searchParams.get("limit") ?? 20) || 20));
  const offset = Math.max(0, Number(url.searchParams.get("offset") ?? 0) || 0);
  return { limit, offset };
}
