import assert from "node:assert/strict";
import { test } from "node:test";
import { hashPassword, passwordProblem, verifyPassword } from "../src/auth/password.ts";
import { hashToken, newRefreshToken, signJwt, verifyJwt } from "../src/auth/tokens.ts";

const secret = "test-secret-that-is-long-enough-123456";

test("JWT round trip, expiry, tampering and wrong secret", () => {
  const now = Date.UTC(2026, 0, 1);
  const token = signJwt({ sub: "u1", role: "rider", name: "Asha" }, secret, 60, now);
  assert.equal(verifyJwt(token, secret, now + 1000)?.sub, "u1");
  assert.equal(verifyJwt(token, secret, now + 61_000), null);
  assert.equal(verifyJwt(token, "another-secret-that-is-long-enough", now), null);
  const [h, p, s] = token.split(".");
  const forged = Buffer.from(JSON.stringify({ sub: "u1", role: "admin", name: "x", iat: 0, exp: 9e9 })).toString("base64url");
  assert.equal(verifyJwt(`${h}.${forged}.${s}`, secret, now), null);
  assert.equal(verifyJwt(`${h}.${p}`, secret, now), null);
});

test("refresh tokens are random and stored only as a hash", () => {
  const a = newRefreshToken();
  const b = newRefreshToken();
  assert.notEqual(a.token, b.token);
  assert.equal(a.hash, hashToken(a.token));
  assert.notEqual(a.hash, a.token);
});

test("scrypt password hashing", () => {
  const stored = hashPassword("Ride2026!");
  assert.ok(verifyPassword("Ride2026!", stored));
  assert.equal(verifyPassword("ride2026!", stored), false);
  assert.equal(verifyPassword("anything", null), false);
  assert.equal(passwordProblem("short1"), "Use at least 8 characters.");
  assert.equal(passwordProblem("onlyletters"), "Use letters and numbers.");
  assert.equal(passwordProblem("letters123"), null);
});
