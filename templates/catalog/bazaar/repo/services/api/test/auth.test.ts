import assert from "node:assert/strict";
import { test } from "node:test";
import { hashPassword, verifyPassword } from "../src/auth/password.ts";
import { generateToken, verifyToken } from "../src/auth/tokens.ts";
import { UnauthorizedError } from "../src/lib/errors.ts";

test("scrypt password hashing and verification", async () => {
  const hash = await hashPassword("Shopper@2026");
  assert.ok(hash.includes(":"));

  const matches = await verifyPassword("Shopper@2026", hash);
  assert.equal(matches, true);

  const wrong = await verifyPassword("WrongPassword", hash);
  assert.equal(wrong, false);
});

test("JWT token generation and successful verification", () => {
  const token = generateToken({
    userId: "u123",
    email: "priya@bazaar.test",
    role: "shopper",
  });

  const payload = verifyToken(token);
  assert.equal(payload.userId, "u123");
  assert.equal(payload.email, "priya@bazaar.test");
  assert.equal(payload.role, "shopper");
  assert.ok(payload.exp && payload.exp > payload.iat!);
});

test("JWT token verifies vendor with shopId", () => {
  const token = generateToken({
    userId: "v456",
    email: "aryan@bazaar.test",
    role: "vendor",
    shopId: "s789",
  });

  const payload = verifyToken(token);
  assert.equal(payload.userId, "v456");
  assert.equal(payload.role, "vendor");
  assert.equal(payload.shopId, "s789");
});

test("rejects tampered or forged JWT tokens", () => {
  const token = generateToken({
    userId: "u123",
    email: "priya@bazaar.test",
    role: "shopper",
  });

  const parts = token.split(".");
  // Tamper with payload (elevate role to admin)
  const fakePayload = Buffer.from(
    JSON.stringify({ userId: "u123", email: "priya@bazaar.test", role: "admin" })
  ).toString("base64url");
  const tamperedToken = `${parts[0]}.${fakePayload}.${parts[2]}`;

  assert.throws(() => verifyToken(tamperedToken), UnauthorizedError);
});

test("rejects expired tokens", () => {
  // Generate token that expired 10 seconds ago
  const expiredToken = generateToken(
    {
      userId: "u123",
      email: "priya@bazaar.test",
      role: "shopper",
    },
    -10
  );

  assert.throws(() => verifyToken(expiredToken), UnauthorizedError);
});
