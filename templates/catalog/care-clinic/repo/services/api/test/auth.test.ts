import assert from "node:assert/strict";
import { test } from "node:test";
import { hashPassword, verifyPassword } from "../src/auth/password.ts";
import { generateToken, verifyToken } from "../src/auth/tokens.ts";
import { UnauthorizedError } from "../src/lib/errors.ts";

test("scrypt password hashing and verification", async () => {
  const hash = await hashPassword("Patient@2026");
  assert.ok(hash.includes(":"));

  const matches = await verifyPassword("Patient@2026", hash);
  assert.equal(matches, true);

  const wrong = await verifyPassword("WrongPassword", hash);
  assert.equal(wrong, false);
});

test("JWT token generation and verification for patient", () => {
  const token = generateToken({
    userId: "pat-123",
    email: "ananya@careclinic.test",
    role: "patient",
  });

  const payload = verifyToken(token);
  assert.equal(payload.userId, "pat-123");
  assert.equal(payload.email, "ananya@careclinic.test");
  assert.equal(payload.role, "patient");
  assert.ok(payload.exp && payload.exp > payload.iat!);
});

test("JWT token generation and verification for doctor", () => {
  const token = generateToken({
    userId: "doc-456",
    email: "dr.rajesh@careclinic.test",
    role: "doctor",
    doctorId: "doc-456",
    clinicId: "clinic-1",
  });

  const payload = verifyToken(token);
  assert.equal(payload.userId, "doc-456");
  assert.equal(payload.role, "doctor");
  assert.equal(payload.doctorId, "doc-456");
  assert.equal(payload.clinicId, "clinic-1");
});

test("rejects tampered or forged JWT tokens", () => {
  const token = generateToken({
    userId: "pat-123",
    email: "ananya@careclinic.test",
    role: "patient",
  });

  const parts = token.split(".");
  // Tamper with payload (elevate role to admin)
  const fakePayload = Buffer.from(
    JSON.stringify({ userId: "pat-123", email: "ananya@careclinic.test", role: "admin" })
  ).toString("base64url");
  const tamperedToken = `${parts[0]}.${fakePayload}.${parts[2]}`;

  assert.throws(() => verifyToken(tamperedToken), UnauthorizedError);
});

test("rejects expired tokens", () => {
  const expiredToken = generateToken(
    {
      userId: "pat-123",
      email: "ananya@careclinic.test",
      role: "patient",
    },
    -10
  );

  assert.throws(() => verifyToken(expiredToken), UnauthorizedError);
});
